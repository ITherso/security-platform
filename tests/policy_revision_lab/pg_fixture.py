"""Explicit provisioning of a new lab-only DB on the already owned test cluster.

No arbitrary DSN, application account, existing database adoption or service is
accepted. Secrets are written only to the caller's protected configuration file.
This helper is test setup, never imported by the lab store or application.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
import ctypes
import json
import os
from pathlib import Path
import secrets
import stat
import sys
import tempfile
from uuid import uuid4

import psycopg
from psycopg import sql

PROJECT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(PROJECT))
sys.path.insert(0, str(PROJECT / "src"))

from scripts import managed_postgres as owned
from security_platform.connectors.hostbased_firewall.private_files import (
    _windows_private_acl, create_private_directory, validate_private_path, write_private_json)

MARKER = "security-platform-policy-revision-lab-target-v1"
_CREATED = {}


def _owned_metadata():
    # Existing fixture metadata predates the stronger client ancestor guard.
    # The developer workspace/source is trusted here; check each secret file's
    # own ACL/owner and every path for links without claiming ancestor safety.
    def check(path):
        path = owned.no_links(path)
        info = path.lstat()
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise owned.FixtureError("Owned fixture secret must be an ordinary private file")
        if os.name == "nt":
            _windows_private_acl(path)
        elif info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise owned.FixtureError("Owned fixture secret has unsafe file permissions")
    check(owned.CONFIG)
    config = owned._read_config()
    check(config["bootstrap_password_file"])
    return config


def ensure_owned_cluster_running():
    """Restart only an existing verified cluster; never bootstrap app roles."""
    config = _owned_metadata()
    cluster = owned._validate_config(config)
    if not config["ready"] or not (cluster / "PG_VERSION").is_file():
        raise owned.FixtureError("Owned existing PostgreSQL fixture is not ready")
    status = owned._run([owned.BIN / "pg_ctl.exe", "status", "-D", cluster])
    if status.returncode == 3:
        owned._checked([owned.BIN / "pg_ctl.exe", "start", "-D", cluster,
                        "-l", cluster / "server.log", "-w", "-t", "20"])
    elif status.returncode != 0:
        raise owned.FixtureError("Owned PostgreSQL fixture status is unavailable")
    owned._owned_server(config)
    return config


def restart_owned_cluster():
    config = ensure_owned_cluster_running()
    cluster = owned._owned_server(config)
    owned._checked([owned.BIN / "pg_ctl.exe", "stop", "-D", cluster,
                    "-m", "fast", "-w", "-t", "20"])
    owned._checked([owned.BIN / "pg_ctl.exe", "start", "-D", cluster,
                    "-l", cluster / "server.log", "-w", "-t", "20"])
    owned._owned_server(config)


def provision(config_path):
    target = Path(os.path.abspath(config_path))
    validate_private_path(target.parent, directory=True)
    if target.exists():
        raise owned.FixtureError("Lab configuration must be a new explicit file")
    fixture = ensure_owned_cluster_running()
    lab_id = uuid4()
    database, role = "sp_policy_lab_" + lab_id.hex, "spl_" + lab_id.hex
    secret = secrets.token_urlsafe(32)
    marker = {"owner": MARKER, "lab_id": str(lab_id), "database_name": database,
              "role": role, "cluster_dir": fixture["cluster_dir"]}
    # Only this fixture's verified bootstrap connection creates the new isolated
    # DB and login. Application migration/runtime credentials are never used.
    with owned._admin_connection(fixture, autocommit=True) as admin:
        if admin.execute("SELECT 1 FROM pg_database WHERE datname=%s", (database,)).fetchone():
            raise owned.FixtureError("Refusing an existing lab database")
        if admin.execute("SELECT 1 FROM pg_roles WHERE rolname=%s", (role,)).fetchone():
            raise owned.FixtureError("Refusing an existing lab role")
        admin.execute(sql.SQL("CREATE ROLE {} LOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE "
                              "NOINHERIT NOREPLICATION NOBYPASSRLS PASSWORD {}").format(
            sql.Identifier(role), sql.Literal(secret)))
        admin.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(
            sql.Identifier(database), sql.Identifier(owned.BOOTSTRAP)))
        admin.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(database)))
        admin.execute(sql.SQL("GRANT CONNECT ON DATABASE {} TO {}").format(
            sql.Identifier(database), sql.Identifier(role)))
    with owned._admin_connection(fixture, dbname=database) as admin:
        admin.execute("REVOKE ALL ON SCHEMA public FROM PUBLIC")
        admin.execute("CREATE SCHEMA lab_identity")
        admin.execute("CREATE TABLE lab_identity.area (singleton integer PRIMARY KEY CHECK (singleton=1), marker text NOT NULL)")
        admin.execute("INSERT INTO lab_identity.area VALUES (1,%s)",
                      (json.dumps(marker, sort_keys=True, separators=(",", ":")),))
        admin.execute(sql.SQL("GRANT USAGE ON SCHEMA lab_identity TO {}").format(sql.Identifier(role)))
        admin.execute(sql.SQL("GRANT SELECT ON lab_identity.area TO {}").format(sql.Identifier(role)))
        admin.execute(sql.SQL("CREATE SCHEMA lab AUTHORIZATION {}").format(sql.Identifier(role)))
    config = {"schema_version": 1, "owner": MARKER, "workspace": str(PROJECT.parent),
              "fixture_config": str(owned.CONFIG), "cluster_dir": fixture["cluster_dir"],
              "host": "127.0.0.1", "port": fixture["port"], "database_name": database,
              "role": role, "connection_secret": secret, "lab_id": str(lab_id)}
    write_private_json(target, config)
    _CREATED[target] = (database, role, marker)
    return target


def cleanup_created(config_path):
    """Drop only a DB/role created by this helper in this Python process."""
    target = Path(os.path.abspath(config_path))
    if target not in _CREATED:
        raise owned.FixtureError("Refusing cleanup of an unowned lab target")
    database, role, expected = _CREATED[target]
    fixture = _owned_metadata()
    owned._owned_server(fixture)
    with owned._admin_connection(fixture, dbname=database) as connection:
        marker = connection.execute("SELECT singleton,marker FROM lab_identity.area").fetchall()
        if marker != [(1, json.dumps(expected, sort_keys=True, separators=(",", ":")))]:
            raise owned.FixtureError("Refusing cleanup of a lab with changed ownership marker")
    with owned._admin_connection(fixture, autocommit=True) as connection:
        connection.execute(sql.SQL("DROP DATABASE {}").format(sql.Identifier(database)))
        connection.execute(sql.SQL("DROP ROLE {}").format(sql.Identifier(role)))
    del _CREATED[target]


@contextmanager
def private_root(tmp_path):
    if os.name != "nt":
        yield create_private_directory(tmp_path / "lab-fixture")
        return
    buffer = ctypes.create_unicode_buffer(32768)
    if ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) != 0:
        raise owned.FixtureError("Known private Documents fixture parent is unavailable")
    # Standard owned TemporaryDirectory cleanup only. The parent's full ACL
    # chain remains subject to the existing private-file guard.
    with tempfile.TemporaryDirectory(prefix=".policy-revision-lab-", dir=buffer.value) as folder:
        yield create_private_directory(Path(folder) / "private")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", required=True)
    args = parser.parse_args(argv)
    try:
        provision(args.config)
    except (ValueError, OSError, psycopg.Error):
        print("isolated_lab_provision_failed", file=sys.stderr)
        return 1
    print("isolated_lab_target_created")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
