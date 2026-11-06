"""Independent trust-boundary regressions using the real fixture PostgreSQL."""
from contextlib import contextmanager
import json
from pathlib import Path
import re
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import text
from sqlalchemy.engine import URL

from security_platform.app import validate_runtime_role
from security_platform.auth.operator_oidc import OperatorVerifier
from security_platform.db import Database
from test_api import api_database


def test_jwks_actual_read_is_bounded_even_when_file_grows_after_stat(tmp_path, monkeypatch):
    target = tmp_path / "racing-public-jwks.json"
    target.write_bytes(b"x" * 100000)
    original_stat, original_open = Path.stat, Path.open
    reads = []
    def raced_stat(path, *args, **kwargs):
        actual = original_stat(path, *args, **kwargs)
        return SimpleNamespace(st_mode=actual.st_mode, st_size=1) if path == target else actual
    class Reader:
        def __enter__(self):
            self.stream = original_open(target, "rb")
            return self
        def __exit__(self, *args):
            self.stream.close()
        def read(self, maximum=-1):
            assert maximum == 65537, "Public JWKS must never be read without an allocation bound"
            reads.append(maximum)
            return self.stream.read(maximum)
    def guarded_open(path, *args, **kwargs):
        return Reader() if path == target else original_open(path, *args, **kwargs)
    monkeypatch.setattr(Path, "stat", raced_stat)
    monkeypatch.setattr(Path, "open", guarded_open)
    with pytest.raises(ValueError, match="Public JWKS exceeds"):
        OperatorVerifier(issuer="https://issuer.example.test", audience="platform", jwks_file=target)
    assert reads == [65537]


def _fixture_configuration():
    from scripts.managed_postgres import DATABASE, MARKER
    path = Path(__file__).resolve().parents[3] / ".tooling" / "platform-test-env.json"
    if not path.exists():
        pytest.skip("Real PostgreSQL fixture is required")
    value = json.loads(path.read_text(encoding="utf-8"))
    if not value.get("ready"):
        pytest.skip("Real PostgreSQL fixture is not ready")
    assert value["owner"] == MARKER and value["host"] == "127.0.0.1" and value["database"] == DATABASE
    return value


@pytest.mark.integration
def test_actual_runtime_is_unprivileged_and_cannot_bootstrap_memberships(api_database):
    _, runtime_url = api_database
    database = Database(runtime_url)
    try:
        validate_runtime_role(database)
        with database.session() as session:
            for table in ("tenants", "principals", "memberships"):
                prohibited = ["INSERT", "DELETE"] + (["UPDATE"] if table != "tenants" else [])
                for privilege in prohibited:
                    assert session.scalar(text("SELECT has_table_privilege(current_user,:table,:privilege)"),
                        {"table": table, "privilege": privilege}) is False
    finally:
        database.close()


@pytest.mark.integration
def test_inherited_table_owner_cannot_masquerade_as_runtime_role():
    from scripts.managed_postgres import BOOTSTRAP
    saved = _fixture_configuration()
    password = Path(saved["bootstrap_password_file"]).read_text(encoding="utf-8").strip()
    database = Database(URL.create("postgresql+psycopg", username=BOOTSTRAP, password=password,
        host=saved["host"], port=saved["port"], database=saved["database"]))
    role_name = "sp_review_" + uuid4().hex
    owner_role = saved["migration_role"]
    assert re.fullmatch(r"[A-Za-z_][A-Za-z0-9_]{0,62}", owner_role)
    try:
        with database.session() as session:
            # CREATE ROLE and GRANT are transactional in PostgreSQL. Roll back
            # the entire fixture, leaving no role or ownership changes behind.
            session.execute(text(f"CREATE ROLE {role_name} NOLOGIN NOSUPERUSER NOCREATEDB NOCREATEROLE INHERIT"))
            session.execute(text(f"GRANT {owner_role} TO {role_name}"))
            session.execute(text(f"SET LOCAL ROLE {role_name}"))
            flags = session.execute(text("SELECT rolsuper,rolcreatedb,rolcreaterole,rolbypassrls FROM pg_roles WHERE rolname=current_user")).one()
            assert not any(flags)
            assert session.scalar(text("SELECT EXISTS(SELECT 1 FROM pg_tables WHERE schemaname='public' AND tableowner=current_user)")) is False
            class SameTransaction:
                @contextmanager
                def session(self):
                    yield session
            with pytest.raises(ValueError, match="separate unprivileged"):
                validate_runtime_role(SameTransaction())
            session.rollback()
    finally:
        database.close()
