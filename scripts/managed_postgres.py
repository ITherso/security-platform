"""Own a portable, loopback-only PostgreSQL fixture without installing a service.

Credentials are generated into a private local file and never printed. This is
test infrastructure, not a production database installer or privilege broker.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import io
import json
import os
from pathlib import Path
import re
import secrets
import socket
import stat
import subprocess
import sys
import tempfile
import uuid
from urllib.parse import quote

import psycopg
from psycopg import sql

PROJECT = Path(__file__).resolve().parents[1]
WORKSPACE = PROJECT.parent
TOOLING = WORKSPACE / ".tooling"
PRIVATE = TOOLING / "platform-test-private"
CONFIG = TOOLING / "platform-test-env.json"
BIN = TOOLING / "postgresql-18.6" / "pgsql" / "bin"
MARKER = "security-platform-owned-postgres-v1"
DATABASE = "security_platform_test"
OWNER = "sp_migration"
RUNTIME = "sp_runtime"
BOOTSTRAP = "sp_test_bootstrap"
TABLE_GRANTS = {
    "tenants": ("SELECT",),
    "principals": ("SELECT",),
    "memberships": ("SELECT",),
    "enrollment_grants": ("SELECT", "INSERT", "UPDATE", "DELETE"),
    "devices": ("SELECT", "INSERT", "UPDATE"),
    "device_credentials": ("SELECT", "INSERT", "UPDATE", "DELETE"),
    "product_states": ("SELECT", "INSERT", "UPDATE", "DELETE"),
    # DELETE is used only for bounded per-tenant retention in application code.
    # A stolen runtime DB credential could delete audit; no immutability claim.
    "audit_events": ("SELECT", "INSERT", "DELETE"),
    # Event rows are never updated. DELETE serves only the per-device cap at
    # ingestion and the operator-scheduled `events prune` retention command.
    "endpoint_events": ("SELECT", "INSERT", "DELETE"),
    # One cursor per device, never deleted; UPDATE also covers SELECT FOR UPDATE.
    "device_event_cursors": ("SELECT", "INSERT", "UPDATE"),
    # Raised and updated at ingestion, acknowledged and closed by tenant admins
    # (UPDATE also covers SELECT FOR UPDATE). DELETE serves only the
    # operator-scheduled `alerts prune` retention of closed alerts. UPDATE
    # already let a stolen runtime credential rewrite any alert; DELETE adds
    # removal (an accepted risk, docs/THREAT_MODEL.tr.md).
    "alerts": ("SELECT", "INSERT", "UPDATE", "DELETE"),
}


class FixtureError(ValueError):
    pass


def no_links(path):
    value = Path(os.path.abspath(path))
    for candidate in (value, *value.parents):
        try:
            info = candidate.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
            raise FixtureError("Fixture paths must not contain symlinks or reparse points")
    return value


def _run(arguments, *, timeout=30):
    try:
        # pg_ctl's detached Windows child may retain a copy of its parent's
        # stdout handle. A PIPE would make communicate() wait for the server to
        # exit even after pg_ctl has returned. Use a file-backed bounded capture.
        with tempfile.TemporaryFile() as capture:
            result = subprocess.run([str(value) for value in arguments], cwd=WORKSPACE,
                stdin=subprocess.DEVNULL, stdout=capture, stderr=subprocess.STDOUT,
                timeout=timeout, creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            capture.seek(0, os.SEEK_END)
            capture.seek(max(0, capture.tell() - 65536))
            result.stdout = capture.read().decode("utf-8", "replace")
            result.stderr = ""
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise FixtureError(f"PostgreSQL fixture process failed: {type(exc).__name__}; winerror={getattr(exc, 'winerror', None)}") from None
    return result


def _checked(arguments, *, timeout=30):
    result = _run(arguments, timeout=timeout)
    if result.returncode:
        # Only fixed native startup commands use this helper; SQL/DSNs/passwords
        # are never arguments. Bound the native diagnostic and strip any URL.
        detail = re.sub(r"postgresql(?:\+psycopg)?://\S+", "[redacted connection]",
                        (result.stdout + result.stderr)[-2000:])
        raise FixtureError(f"PostgreSQL fixture command exited {result.returncode}: {detail}")
    return result


def _private_directory():
    no_links(TOOLING).mkdir(exist_ok=True)
    folder = no_links(PRIVATE)
    marker = folder / "owner.json"
    try:
        folder.mkdir(mode=0o700)
        created = True
    except FileExistsError:
        created = False
        if not marker.is_file() or json.loads(marker.read_text(encoding="utf-8")) != {"owner": MARKER}:
            raise FixtureError("Existing private fixture directory is not owned by this tool")
    _protect_directory(folder)
    if created:
        marker.write_text(json.dumps({"owner": MARKER}) + "\n", encoding="utf-8")
    return folder


def _protect_directory(folder):
    """Restrict only a directory created/validated as this fixture's property."""
    folder = no_links(folder)
    if folder != PRIVATE and (folder.parent != TOOLING
            or not re.fullmatch(r"test-pg-data-[a-f0-9]{32}", folder.name)):
        raise FixtureError("Directory ACL changes are limited to owned test fixture directories")
    if os.name == "nt":
        identity = _checked(["whoami.exe", "/user", "/fo", "csv", "/nh"])
        rows = list(csv.reader(io.StringIO(identity.stdout.strip())))
        if len(rows) != 1 or len(rows[0]) != 2 or not re.fullmatch(r"S-1-[0-9-]+", rows[0][1]):
            raise FixtureError("Current Windows user SID could not be determined")
        _checked(["icacls.exe", folder, "/inheritance:r", "/grant:r",
                  f"*{rows[0][1]}:(OI)(CI)F", "*S-1-5-18:(OI)(CI)F", "*S-1-5-32-544:(OI)(CI)F"])
    else:
        folder.chmod(0o700)


def _write_private(path, content):
    folder = _private_directory()
    target = no_links(path)
    if target.parent not in {TOOLING, folder}:
        raise FixtureError("Private fixture output must remain in the owned tooling directories")
    temporary = no_links(folder / ("private-" + uuid.uuid4().hex + ".tmp"))
    try:
        descriptor = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        # A move preserves the protected file DACL when the JSON is placed next
        # to the private directory. No secret is first written in an open parent.
        os.replace(temporary, target)
    finally:
        temporary.unlink(missing_ok=True)


def _read_config():
    path = no_links(CONFIG)
    if not path.is_file() or path.stat().st_size > 16384:
        raise FixtureError("Owned PostgreSQL fixture configuration is missing or oversized")
    def unique(pairs):
        row = {}
        for key, value in pairs:
            if key in row:
                raise FixtureError("Duplicate fixture metadata field")
            row[key] = value
        return row
    config = json.loads(path.read_text(encoding="utf-8"), object_pairs_hook=unique)
    _validate_config(config)
    return config


def _validate_config(config):
    if (not isinstance(config, dict) or config.get("owner") != MARKER
            or config.get("workspace") != str(WORKSPACE)
            or config.get("host") != "127.0.0.1" or type(config.get("port")) is not int
            or not 1024 <= config["port"] <= 65535
            or config.get("database") != DATABASE or config.get("migration_role") != OWNER
            or config.get("runtime_role") != RUNTIME or config.get("bin_dir") != str(BIN)):
        raise FixtureError("PostgreSQL fixture metadata does not belong to this workspace")
    cluster = no_links(config.get("cluster_dir", ""))
    if cluster.parent != TOOLING or not re.fullmatch(r"test-pg-data-[a-f0-9]{32}", cluster.name):
        raise FixtureError("PostgreSQL fixture cluster path is outside its owned directory")
    if config.get("bootstrap_password_file") != str(PRIVATE / (cluster.name + ".password")):
        raise FixtureError("PostgreSQL bootstrap password file is outside its owned directory")
    for purpose, role, alias in (("migration", OWNER, "SP_MIGRATION_DATABASE_URL"),
                                  ("runtime", RUNTIME, "SP_DATABASE_URL")):
        password = config.get(purpose + "_password")
        if (not isinstance(password, str) or not re.fullmatch(r"[A-Za-z0-9_-]{43}", password)
                or config.get(purpose + "_url") != _url(role, password, config["port"])
                or config.get(alias) != config[purpose + "_url"]):
            raise FixtureError("Fixture connection settings must refer only to the owned loopback server")
    if type(config.get("ready")) is not bool:
        raise FixtureError("Invalid fixture readiness metadata")
    return cluster


def _save_config(config):
    _validate_config(config)
    _write_private(CONFIG, json.dumps(config, indent=2) + "\n")


def _url(user, password, port):
    return f"postgresql+psycopg://{user}:{quote(password, safe='')}@127.0.0.1:{port}/{DATABASE}"


def _connection(url, **kwargs):
    return psycopg.connect(url.replace("postgresql+psycopg://", "postgresql://", 1),
                           connect_timeout=5, **kwargs)


def _admin_connection(config, *, dbname="postgres", **kwargs):
    password_file = no_links(config["bootstrap_password_file"])
    if password_file.stat().st_size > 128:
        raise FixtureError("Owned bootstrap credential exceeds its size limit")
    return psycopg.connect(host="127.0.0.1", port=config["port"], dbname=dbname, user=BOOTSTRAP,
        password=password_file.read_text(encoding="utf-8").strip(), connect_timeout=5, **kwargs)


def _free_port(requested=None):
    with socket.socket() as candidate:
        candidate.bind(("127.0.0.1", requested or 0))
        return candidate.getsockname()[1]


def _owned_server(config):
    cluster = _validate_config(config)
    # data_directory is intentionally not exposed to the least-privileged
    # application roles. Use only this owned fixture's private bootstrap role.
    with _admin_connection(config) as connection:
        observed = connection.execute("SELECT current_database(), current_user, host(inet_server_addr()), inet_server_port(), current_setting('data_directory')").fetchone()
    if (observed[:4] != ("postgres", BOOTSTRAP, "127.0.0.1", config["port"])
            or no_links(observed[4]) != cluster):
        raise FixtureError("The listening PostgreSQL server is not this owned fixture")
    return cluster


def _bootstrap(config):
    with _admin_connection(config, autocommit=True) as connection:
        for role, secret in ((OWNER, config["migration_password"]), (RUNTIME, config["runtime_password"])):
            if connection.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone() is None:
                connection.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(secret)))
            else:
                connection.execute(sql.SQL("ALTER ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}").format(sql.Identifier(role), sql.Literal(secret)))
        if connection.execute("SELECT 1 FROM pg_database WHERE datname=%s", (DATABASE,)).fetchone() is None:
            connection.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(DATABASE), sql.Identifier(OWNER)))
        connection.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(DATABASE)))
        connection.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(sql.Identifier(DATABASE), sql.Identifier(RUNTIME)))
    with _admin_connection(config, dbname=DATABASE, autocommit=True) as connection:
        connection.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        connection.execute(sql.SQL("ALTER SCHEMA public OWNER TO {}").format(sql.Identifier(OWNER)))
        connection.execute(sql.SQL("GRANT USAGE ON SCHEMA public TO {}").format(sql.Identifier(RUNTIME)))
    with _connection(config["migration_url"], autocommit=True) as connection:
        connection.execute("ALTER DEFAULT PRIVILEGES IN SCHEMA public REVOKE ALL ON TABLES FROM PUBLIC")


def start(port=None):
    if not (no_links(BIN) / "pg_ctl.exe").is_file():
        raise FixtureError("Verified portable PostgreSQL 18.6 binaries must be placed in .tooling/postgresql-18.6/pgsql")
    version = _checked([BIN / "postgres.exe", "--version"]).stdout.strip()
    if version != "postgres (PostgreSQL) 18.6":
        raise FixtureError("Unexpected portable PostgreSQL binary version")
    if CONFIG.exists():
        config = _read_config()
        cluster = _validate_config(config)
        if not config.get("ready"):
            # Incomplete setup credentials may have been consumed prematurely
            # by a failed test. Regenerate before publishing a ready fixture.
            for purpose, role in (("migration", OWNER), ("runtime", RUNTIME)):
                config[purpose + "_password"] = secrets.token_urlsafe(32)
                config[purpose + "_url"] = _url(role, config[purpose + "_password"], config["port"])
            config["SP_MIGRATION_DATABASE_URL"] = config["migration_url"]
            config["SP_DATABASE_URL"] = config["runtime_url"]
            _save_config(config)
    else:
        _private_directory()
        cluster = TOOLING / ("test-pg-data-" + uuid.uuid4().hex)
        migration_password, runtime_password = secrets.token_urlsafe(32), secrets.token_urlsafe(32)
        config = {"owner": MARKER, "workspace": str(WORKSPACE), "cluster_dir": str(cluster),
            "bin_dir": str(BIN), "host": "127.0.0.1", "port": _free_port(port), "database": DATABASE,
            "migration_role": OWNER, "runtime_role": RUNTIME, "migration_password": migration_password,
            "runtime_password": runtime_password, "bootstrap_password_file": str(PRIVATE / (cluster.name + ".password")),
            "created_at": datetime.now(timezone.utc).isoformat(), "ready": False}
        config["migration_url"] = _url(OWNER, migration_password, config["port"])
        config["runtime_url"] = _url(RUNTIME, runtime_password, config["port"])
        config["SP_MIGRATION_DATABASE_URL"] = config["migration_url"]
        config["SP_DATABASE_URL"] = config["runtime_url"]
        _write_private(Path(config["bootstrap_password_file"]), secrets.token_urlsafe(32) + "\n")
        _save_config(config)
    if not cluster.exists():
        cluster.mkdir(mode=0o700)
        _protect_directory(cluster)
        _checked([BIN / "initdb.exe", "-D", cluster, "--username", BOOTSTRAP,
                  "--pwfile", config["bootstrap_password_file"], "--auth-local=scram-sha-256",
                  "--auth-host=scram-sha-256", "--encoding=UTF8", "--locale=C"], timeout=60)
        with (cluster / "postgresql.conf").open("a", encoding="utf-8") as stream:
            stream.write(f"\nlisten_addresses='127.0.0.1'\nport={config['port']}\npassword_encryption='scram-sha-256'\n")
            stream.write("shared_buffers='32MB'\nmax_connections=50\nlogging_collector=off\nlog_statement='none'\nlog_min_error_statement='panic'\nlog_parameter_max_length=0\nlog_parameter_max_length_on_error=0\n")
        (cluster / "pg_hba.conf").write_text("host all all 127.0.0.1/32 scram-sha-256\nhost all all 0.0.0.0/0 reject\nhost all all ::0/0 reject\n", encoding="utf-8")
    if not (cluster / "PG_VERSION").is_file() or (cluster / "PG_VERSION").read_text().strip() != "18":
        raise FixtureError("The owned cluster is incomplete; inspect it before retrying")
    _protect_directory(cluster)
    status = _run([BIN / "pg_ctl.exe", "status", "-D", cluster])
    if status.returncode != 0:
        _checked([BIN / "pg_ctl.exe", "start", "-D", cluster, "-l", cluster / "server.log", "-w", "-t", "20"], timeout=30)
    _bootstrap(config)
    _owned_server(config)
    config["ready"] = True
    _save_config(config)
    return {"status": "running", "version": "18.6", "host": "127.0.0.1", "port": config["port"], "config_file": str(CONFIG)}


def grant_runtime():
    config = _read_config()
    _owned_server(config)
    with _connection(config["migration_url"]) as connection:
        tables = dict(connection.execute("SELECT tablename, tableowner FROM pg_tables WHERE schemaname='public'").fetchall())
        if not set(TABLE_GRANTS) <= set(tables) or any(owner != OWNER for owner in tables.values()):
            raise FixtureError("Run the owned migration account's Alembic upgrade before granting runtime tables")
        connection.execute(sql.SQL("REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {}").format(sql.Identifier(RUNTIME)))
        for table, privileges in TABLE_GRANTS.items():
            connection.execute(sql.SQL("GRANT {} ON TABLE {} TO {}").format(
                sql.SQL(", ").join(sql.SQL(value) for value in privileges), sql.Identifier(table), sql.Identifier(RUNTIME)))
        # SELECT FOR UPDATE requires UPDATE privilege; constrain it to the ID
        # column used for tenant quota serialization rather than broad UPDATE.
        connection.execute(sql.SQL("GRANT UPDATE (id) ON tenants TO {}").format(sql.Identifier(RUNTIME)))
        if "alembic_version" in tables:
            connection.execute(sql.SQL("GRANT SELECT ON alembic_version TO {}").format(sql.Identifier(RUNTIME)))
    return {"status": "granted", "runtime_role": RUNTIME, "table_count": len(TABLE_GRANTS),
            "audit_permissions": ["SELECT", "INSERT", "DELETE for bounded retention"]}


def status():
    config = _read_config()
    _owned_server(config)
    with _connection(config["runtime_url"]) as connection:
        row = connection.execute("SELECT rolname, rolsuper, rolcreatedb, rolcreaterole, rolbypassrls, rolreplication, rolinherit FROM pg_roles WHERE rolname=current_user").fetchone()
        if row != (RUNTIME, False, False, False, False, False, False):
            raise FixtureError("Runtime PostgreSQL role has unexpected privileges")
        if connection.execute("SELECT EXISTS (SELECT 1 FROM pg_auth_members WHERE member=(SELECT oid FROM pg_roles WHERE rolname=current_user))").fetchone()[0]:
            raise FixtureError("Runtime PostgreSQL role must not inherit or SET ROLE into another account")
        writable_schema = connection.execute("SELECT has_schema_privilege(current_user,'public','CREATE') OR has_database_privilege(current_user,current_database(),'CREATE')").fetchone()[0]
        if writable_schema:
            raise FixtureError("Runtime PostgreSQL role must not own or create application schema")
    return {"status": "running", "version": "18.6", "host": "127.0.0.1", "port": config["port"],
            "runtime_superuser": False, "runtime_schema_owner": False, "config_file": str(CONFIG)}


def stop():
    config = _read_config()
    cluster = _validate_config(config)
    # Authenticate and verify data_directory before issuing a signal to a server.
    native = _run([BIN / "pg_ctl.exe", "status", "-D", cluster])
    if native.returncode == 3:
        return {"status": "stopped", "cluster_preserved": True}
    _owned_server(config)
    _checked([BIN / "pg_ctl.exe", "stop", "-D", cluster, "-m", "fast", "-w", "-t", "20"], timeout=30)
    return {"status": "stopped", "cluster_preserved": True}


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["start", "status", "grant", "stop"])
    parser.add_argument("--port", type=int)
    args = parser.parse_args(argv)
    try:
        if args.port is not None and (args.action != "start" or not 1024 <= args.port <= 65535):
            raise FixtureError("A port between 1024 and 65535 is only valid with start")
        result = {"start": lambda: start(args.port), "status": status, "grant": grant_runtime, "stop": stop}[args.action]()
        print(json.dumps(result))
        return 0
    except (FixtureError, psycopg.Error, OSError, ValueError) as exc:
        if isinstance(exc, FixtureError):
            print(str(exc), file=sys.stderr)
        else:
            print(f"PostgreSQL fixture failed: {type(exc).__name__}; sqlstate={getattr(exc, 'sqlstate', None)}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
