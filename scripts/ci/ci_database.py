"""Prepare a GitHub Actions PostgreSQL service container for the test suite.

CI only. scripts/managed_postgres.py starts portable Windows binaries; on a Linux
runner the workflow starts the official postgres:18 image as a service instead,
with sp_test_bootstrap as its superuser. This helper gives that server the same
accounts and privileges as the managed fixture:

  setup       as sp_test_bootstrap: managed_postgres's logging settings, then its
              _bootstrap() (sp_migration owns security_platform_test, sp_runtime
              may only connect and use the schema). Writes the configuration
              file that the tests read.
  migrations  as sp_migration: alembic upgrade head, downgrade base, upgrade
              head, with a schema check after each command.
  grant       as sp_migration: the runtime grants of managed_postgres's
              TABLE_GRANTS; then checks sp_runtime as managed_postgres status does.

The sp_migration and sp_runtime passwords are generated for each run. The
bootstrap password is the throwaway POSTGRES_PASSWORD of the service, which the
workflow defines. No secret is printed; setup only emits ::add-mask:: commands,
which the runner consumes, so the log hides these values. The JUnit artifact is
not masked; any value in it stops working when the job ends.

The configuration has no cluster_dir or bin_dir because no managed cluster
exists. managed_postgres's commands and the tests/policy_revision_lab fixture
therefore refuse it; docs/CI.tr.md lists the tests this affects.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import importlib.util
import json
import os
from pathlib import Path
import secrets
import subprocess
import sys
import time
from urllib.parse import urlsplit

from alembic.config import Config
from alembic.script import ScriptDirectory
import psycopg
from psycopg import sql

PROJECT = Path(__file__).resolve().parents[2]
_spec = importlib.util.spec_from_file_location("ci_managed_postgres", PROJECT / "scripts" / "managed_postgres.py")
managed = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(managed)

HOST = "127.0.0.1"
PRIVATE_DIRECTORY = "ci-postgres-private"
PASSWORD_FILE = "bootstrap.password"
# managed_postgres writes these into postgresql.conf. A service container gets
# them by ALTER SYSTEM, so a failing statement is not written to the server log.
LOGGING = {"log_statement": "none", "log_min_error_statement": "panic",
           "log_parameter_max_length": "0", "log_parameter_max_length_on_error": "0"}
TABLE_PRIVILEGES = ("SELECT", "INSERT", "UPDATE", "DELETE", "TRUNCATE", "REFERENCES", "TRIGGER")


class CiDatabaseError(ValueError):
    pass


def _mask(*values):
    # Workflow commands are read by the runner and never shown in the log.
    for value in values:
        print("::add-mask::" + value, flush=True)


def _write_new(path, text):
    """Create a new owner-only file; never replace an existing one."""
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
    with os.fdopen(os.open(path, flags, 0o600), "w", encoding="utf-8", newline="\n") as stream:
        stream.write(text)
        stream.flush()
        os.fsync(stream.fileno())


def _read_config(path):
    path = Path(path)
    if not path.is_file() or path.stat().st_size > 16384:
        raise CiDatabaseError("Test database configuration is missing or oversized")
    def unique(pairs):
        row = {}
        for key, value in pairs:
            if key in row:
                raise CiDatabaseError("Duplicate test database configuration field")
            row[key] = value
        return row
    config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    if not isinstance(config, dict) or config.get("ready") is not True:
        raise CiDatabaseError("Test database configuration is not ready")
    for key in ("migration_url", "runtime_url"):
        value = config.get(key)
        if not isinstance(value, str) or not value.startswith("postgresql+psycopg://") or urlsplit(value).hostname != HOST:
            raise CiDatabaseError("Test database configuration must name a loopback PostgreSQL server")
    return config


def _admin_when_ready(config, timeout=60):
    deadline = time.monotonic() + timeout
    while True:
        try:
            return managed._admin_connection(config, autocommit=True)
        except psycopg.OperationalError:
            if time.monotonic() > deadline:
                raise CiDatabaseError("The PostgreSQL service did not accept the bootstrap login in time") from None
            time.sleep(1)


def _require_fresh_service(admin):
    if admin.execute("SELECT current_user, rolsuper FROM pg_roles WHERE rolname=current_user").fetchone() != (managed.BOOTSTRAP, True):
        raise CiDatabaseError("The service superuser must be " + managed.BOOTSTRAP)
    # Never adopt, or reset the passwords of, accounts that another fixture uses.
    if admin.execute("SELECT 1 FROM pg_roles WHERE rolname = ANY(%s)", ([managed.OWNER, managed.RUNTIME],)).fetchone():
        raise CiDatabaseError("Refusing a server that already has the application roles")
    if admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (managed.DATABASE,)).fetchone():
        raise CiDatabaseError("Refusing a server that already has the test database")


def _wait_for_logging(config, timeout=10):
    # A reload reaches new sessions asynchronously; wait until one sees it.
    deadline = time.monotonic() + timeout
    while True:
        with managed._admin_connection(config) as admin:
            settings = dict(admin.execute("SELECT name, setting FROM pg_settings WHERE name = ANY(%s)",
                                          (list(LOGGING),)).fetchall())
        if settings == LOGGING:
            return
        if time.monotonic() > deadline:
            raise CiDatabaseError("The service did not apply the logging settings")
        time.sleep(0.2)


def new_config(port, password_file, passwords):
    """The fields that the tests read, in managed_postgres's format and names."""
    config = {"owner": managed.MARKER, "provisioner": "scripts/ci/ci_database.py", "workspace": str(managed.WORKSPACE),
              "host": HOST, "port": port, "database": managed.DATABASE, "migration_role": managed.OWNER,
              "runtime_role": managed.RUNTIME, "bootstrap_password_file": str(password_file),
              "created_at": datetime.now(timezone.utc).isoformat(), "ready": False}
    for purpose, role, alias in (("migration", managed.OWNER, "SP_MIGRATION_DATABASE_URL"),
                                 ("runtime", managed.RUNTIME, "SP_DATABASE_URL")):
        config[purpose + "_password"] = passwords[purpose]
        config[purpose + "_url"] = config[alias] = managed._url(role, passwords[purpose], port)
    return config


def setup(config_path, port):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        raise CiDatabaseError("setup creates roles on a fresh CI service and runs only in GitHub Actions")
    bootstrap = os.environ.get("SP_CI_BOOTSTRAP_PASSWORD", "")
    if not bootstrap or bootstrap != bootstrap.strip() or len(bootstrap.encode("utf-8")) > 120:
        raise CiDatabaseError("SP_CI_BOOTSTRAP_PASSWORD must hold the service's bootstrap password")
    config_path = Path(os.path.abspath(config_path))
    if config_path.exists():
        raise CiDatabaseError("Refusing to replace an existing test database configuration")
    passwords = {purpose: secrets.token_urlsafe(32) for purpose in ("migration", "runtime")}
    _mask(bootstrap, *passwords.values())
    config_path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
    private = config_path.parent / PRIVATE_DIRECTORY
    private.mkdir(mode=0o700)
    password_file = private / PASSWORD_FILE
    _write_new(password_file, bootstrap + "\n")
    config = new_config(port, password_file, passwords)
    with _admin_when_ready(config) as admin:
        _require_fresh_service(admin)
        for name, value in LOGGING.items():
            admin.execute(sql.SQL("ALTER SYSTEM SET {} = {}").format(sql.Identifier(name), sql.Literal(value)))
        admin.execute("SELECT pg_reload_conf()")
    _wait_for_logging(config)
    managed._bootstrap(config)
    for purpose, role in (("migration", managed.OWNER), ("runtime", managed.RUNTIME)):
        with managed._connection(config[purpose + "_url"]) as connection:
            if connection.execute("SELECT current_user, current_database()").fetchone() != (role, managed.DATABASE):
                raise CiDatabaseError("A new application login reached the wrong role or database")
    config["ready"] = True
    _write_new(config_path, json.dumps(config, indent=2) + "\n")
    return {"status": "ready", "host": HOST, "port": port, "database": managed.DATABASE,
            "config_file": str(config_path)}


def _alembic(config, arguments):
    environment = dict(os.environ, SP_MIGRATION_DATABASE_URL=config["migration_url"])
    environment.pop("SP_DATABASE_URL", None)
    # Alembic logs revision ids only; env.py hides SQL parameters.
    result = subprocess.run([sys.executable, "-m", "alembic", "-c", str(PROJECT / "alembic.ini"), *arguments],
                            cwd=PROJECT, env=environment, stdin=subprocess.DEVNULL, timeout=900)
    if result.returncode:
        raise CiDatabaseError(f"alembic {' '.join(arguments)} exited {result.returncode}")


def _check_schema(config, expected):
    with managed._connection(config["migration_url"]) as connection:
        relations = {name: owner for name, owner in connection.execute(
            "SELECT c.relname, pg_get_userbyid(c.relowner) FROM pg_class c "
            "JOIN pg_namespace n ON n.oid=c.relnamespace WHERE n.nspname='public'")}
        versions = ([row[0] for row in connection.execute("SELECT version_num FROM alembic_version")]
                    if "alembic_version" in relations else [])
        others = [row[0] for row in connection.execute(
            "SELECT p.proname FROM pg_proc p JOIN pg_namespace n ON n.oid=p.pronamespace WHERE n.nspname='public' "
            "UNION ALL SELECT t.typname FROM pg_type t JOIN pg_namespace n ON n.oid=t.typnamespace "
            "WHERE n.nspname='public' AND t.typrelid=0 AND t.typcategory<>'A'")]
    if expected is None:
        leftover = sorted(set(relations) - {"alembic_version", "alembic_version_pkc"}) + sorted(others)
        if leftover or versions:
            raise CiDatabaseError("downgrade base left schema objects: " + ", ".join(leftover or ["alembic_version row"]))
        return None
    if versions != [expected]:
        raise CiDatabaseError(f"Expected Alembic version {expected}, found {versions}")
    missing = sorted(set(managed.TABLE_GRANTS) - set(relations))
    if missing or any(owner != managed.OWNER for owner in relations.values()):
        raise CiDatabaseError("upgrade head did not leave every table owned by " + managed.OWNER
                              + (": missing " + ", ".join(missing) if missing else ""))
    return expected


def migrations(config_path):
    config = _read_config(config_path)
    heads = ScriptDirectory.from_config(Config(str(PROJECT / "alembic.ini"))).get_heads()
    if len(heads) != 1:
        raise CiDatabaseError("Expected exactly one Alembic head")
    steps = []
    for arguments, expected in ((["upgrade", "head"], heads[0]), (["downgrade", "base"], None),
                                (["upgrade", "head"], heads[0])):
        _alembic(config, arguments)
        steps.append({"command": " ".join(arguments), "version": _check_schema(config, expected)})
    return {"status": "migrated", "head": heads[0], "steps": steps}


def grant(config_path):
    """managed_postgres.grant_runtime() without its managed-cluster identity check."""
    config = _read_config(config_path)
    runtime = sql.Identifier(managed.RUNTIME)
    with managed._connection(config["migration_url"]) as connection:
        tables = dict(connection.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public'").fetchall())
        if not set(managed.TABLE_GRANTS) <= set(tables) or any(owner != managed.OWNER for owner in tables.values()):
            raise CiDatabaseError("Run the migrations before granting runtime tables")
        connection.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(runtime))
        for table, privileges in managed.TABLE_GRANTS.items():
            connection.execute(sql.SQL("GRANT {} ON TABLE {} TO {}").format(
                sql.SQL(", ").join(sql.SQL(value) for value in privileges), sql.Identifier(table), runtime))
        connection.execute(sql.SQL("GRANT UPDATE (id) ON tenants TO {}").format(runtime))
        if "alembic_version" in tables:
            connection.execute(sql.SQL("GRANT SELECT ON alembic_version TO {}").format(runtime))
    # The checks of managed_postgres.status(), plus the exact table privileges.
    with managed._connection(config["runtime_url"]) as connection:
        row = connection.execute("SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolreplication, "
                                 "rolinherit FROM pg_roles WHERE rolname=current_user").fetchone()
        if row != (managed.RUNTIME, False, False, False, False, False, False):
            raise CiDatabaseError("Runtime PostgreSQL role has unexpected privileges")
        if connection.execute("SELECT EXISTS (SELECT 1 FROM pg_auth_members WHERE member="
                              "(SELECT oid FROM pg_roles WHERE rolname=current_user))").fetchone()[0]:
            raise CiDatabaseError("Runtime PostgreSQL role must not inherit or SET ROLE into another account")
        if connection.execute("SELECT has_schema_privilege(current_user,'public','CREATE') "
                              "OR has_database_privilege(current_user,current_database(),'CREATE')").fetchone()[0]:
            raise CiDatabaseError("Runtime PostgreSQL role must not own or create application schema")
        for table, privileges in managed.TABLE_GRANTS.items():
            held = {privilege for privilege in TABLE_PRIVILEGES if connection.execute(
                "SELECT has_table_privilege(current_user, %s, %s)", ("public." + table, privilege)).fetchone()[0]}
            if held != set(privileges):
                raise CiDatabaseError(f"Runtime PostgreSQL role holds {sorted(held)} on {table}")
    return {"status": "granted", "runtime_role": managed.RUNTIME, "table_count": len(managed.TABLE_GRANTS)}


def main(argv=None):
    parser = argparse.ArgumentParser(description="Prepare the CI PostgreSQL service for the test suite")
    parser.add_argument("action", choices=["setup", "migrations", "grant"])
    parser.add_argument("--config", required=True, help="the test configuration (../.tooling/platform-test-env.json in CI)")
    parser.add_argument("--port", type=int, default=5432, help="the service port on 127.0.0.1 (setup only)")
    args = parser.parse_args(argv)
    try:
        if not 1024 <= args.port <= 65535:
            raise CiDatabaseError("The port must be between 1024 and 65535")
        action = {"setup": lambda: setup(args.config, args.port), "migrations": lambda: migrations(args.config),
                  "grant": lambda: grant(args.config)}[args.action]
        print(json.dumps(action()), flush=True)
        return 0
    except (CiDatabaseError, managed.FixtureError) as exc:
        print(str(exc), file=sys.stderr)
    except psycopg.Error as exc:
        # The server's primary message names objects, never passwords or URLs.
        print(f"CI database step failed: {type(exc).__name__}; sqlstate={exc.sqlstate}; "
              f"message={exc.diag.message_primary}", file=sys.stderr)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        print(f"CI database step failed: {type(exc).__name__}", file=sys.stderr)
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
