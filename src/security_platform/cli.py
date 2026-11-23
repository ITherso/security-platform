"""Local administration requires the separate migration/owner DB credential.

No bootstrap or membership mutation is exposed by the HTTP service. Event
retention (`events prune`) is routine runtime work and, like `serve`, uses only
the unprivileged runtime credential.
"""
import argparse
import json
import os
from pathlib import Path
import sys
from uuid import UUID

from sqlalchemy.exc import SQLAlchemyError

from security_platform.db import Database
from security_platform.services import administration


def _owner_database():
    url = os.environ.get("SP_MIGRATION_DATABASE_URL")
    if not url or not url.startswith("postgresql+psycopg://"):
        raise ValueError("SP_MIGRATION_DATABASE_URL is required for local administration")
    # There is deliberately no fallback to the runtime credential.
    return Database(url)


def _runtime_database():
    url = os.environ.get("SP_DATABASE_URL")
    if not url or not url.startswith("postgresql+psycopg://"):
        raise ValueError("SP_DATABASE_URL is required for event retention")
    # There is deliberately no fallback to the migration/owner credential.
    return Database(url)


def _migration_root():
    source = Path(__file__).resolve().parents[2]
    installed = Path(sys.prefix) / "share/security-platform"
    for root in (source, installed):
        if (root / "alembic.ini").is_file() and (root / "migrations/versions").is_dir():
            return root
    raise ValueError("Migration resources are unavailable; reinstall the complete package")


def main(argv=None):
    parser = argparse.ArgumentParser(description="Security Platform local administration")
    commands = parser.add_subparsers(dest="command", required=True)
    tenant = commands.add_parser("create-tenant")
    tenant.add_argument("--name", required=True)
    member = commands.add_parser("set-membership")
    member.add_argument("--tenant-id", required=True, type=UUID)
    member.add_argument("--issuer", required=True)
    member.add_argument("--subject", required=True)
    member.add_argument("--role", choices=["tenant_admin", "viewer"], required=True)
    revoke = commands.add_parser("revoke-membership")
    revoke.add_argument("--tenant-id", required=True, type=UUID)
    revoke.add_argument("--issuer", required=True)
    revoke.add_argument("--subject", required=True)
    retention = commands.add_parser("set-event-retention")
    retention.add_argument("--tenant-id", required=True, type=UUID)
    retention.add_argument("--days", required=True, type=int)
    events = commands.add_parser("events")
    event_commands = events.add_subparsers(dest="events_command", required=True)
    event_commands.add_parser("prune")
    commands.add_parser("migrate")
    serve = commands.add_parser("serve")
    serve.add_argument("--host", default="127.0.0.1")
    serve.add_argument("--port", type=int, default=8081)
    serve.add_argument("--ssl-certfile", type=Path)
    serve.add_argument("--ssl-keyfile", type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == "serve":
            from security_platform.app import create_app
            from security_platform.settings import Settings
            import ipaddress
            import uvicorn
            settings = Settings.from_environment()
            if not (args.ssl_certfile and args.ssl_keyfile):
                try:
                    local_host = args.host == "localhost" or ipaddress.ip_address(args.host).is_loopback
                except ValueError:
                    local_host = False
                if not (settings.allow_loopback_http and local_host):
                    raise ValueError("TLS certificate/key are required; HTTP is only an explicit loopback test option")
            if bool(args.ssl_certfile) != bool(args.ssl_keyfile) or not 1 <= args.port <= 65535:
                raise ValueError("Invalid server arguments")
            uvicorn.run(create_app(settings), host=args.host, port=args.port, access_log=False,
                proxy_headers=False, ssl_certfile=str(args.ssl_certfile) if args.ssl_certfile else None,
                ssl_keyfile=str(args.ssl_keyfile) if args.ssl_keyfile else None)
            return 0
        if args.command == "migrate":
            if not os.environ.get("SP_MIGRATION_DATABASE_URL"):
                raise ValueError("SP_MIGRATION_DATABASE_URL is required")
            from alembic import command
            from alembic.config import Config
            root = _migration_root()
            config = Config(str(root / "alembic.ini"))
            config.set_main_option("script_location", str(root / "migrations"))
            command.upgrade(config, "head")
            return 0
        if args.command == "events":
            from security_platform.app import validate_runtime_role
            from security_platform.services.events import prune_expired_events
            database = _runtime_database()
            try:
                try:
                    validate_runtime_role(database)
                except ValueError:
                    raise ValueError("events prune requires the separate unprivileged runtime database role") from None
                result = prune_expired_events(database)
            finally:
                database.close()
            print(json.dumps(result))
            if result["failed_tenants"]:
                # Earlier chunks were committed, so "no success was recorded" would be false.
                print(f"events prune incomplete: {result['failed_tenants']} tenant(s) failed and were skipped; "
                      "deleted events stay deleted and the next run retries the rest.", file=sys.stderr)
                return 1
            return 0
        database = _owner_database()
        try:
            with database.session() as session:
                if args.command == "create-tenant":
                    result = administration.create_tenant(session, args.name)
                elif args.command == "set-membership":
                    result = administration.set_membership(session, args.tenant_id, args.issuer, args.subject, args.role)
                elif args.command == "set-event-retention":
                    result = administration.set_event_retention(session, args.tenant_id, args.days)
                else:
                    result = administration.revoke_membership(session, args.tenant_id, args.issuer, args.subject)
            print(json.dumps(result, ensure_ascii=False))
        finally:
            database.close()
        return 0
    except SQLAlchemyError:
        print("Database operation failed; no success was recorded.", file=sys.stderr)
        return 1
    except ValueError as exc:
        print(str(exc)[:300], file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
