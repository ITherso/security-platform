"""Policy-preview phase must not grow the shipped remote or mutation surface.

The checked-in baseline was captured from 2755336, with the independently
reviewed inventory read-coherence fix at 9c2ce8c explicitly listed. Source hashes
normalize CRLF to LF only. Tests consume the fixture; they never regenerate it.
"""
import hashlib
import json
import os
from pathlib import Path
import tomllib
from uuid import uuid4

from alembic.config import Config
from alembic.script import ScriptDirectory
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
from pydantic import ValidationError
import pytest

from security_platform.app import create_app
from security_platform.contracts import SnapshotEnvelope
from security_platform.db import Base
import security_platform.models  # noqa: F401
from security_platform.settings import Settings


PROJECT = Path(__file__).resolve().parents[2]
BASELINE = json.loads((PROJECT / "tests/fixtures/policy_surface_baseline_v1.json").read_text(encoding="utf-8"))
HTTP_METHODS = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}


def source_digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@pytest.fixture(scope="module")
def inventory_app(tmp_path_factory):
    directory = tmp_path_factory.mktemp("policy-surface-public-key")
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = jwt.algorithms.RSAAlgorithm.to_jwk(key.public_key(), as_dict=True)
    public.update(kid="surface-fixture", alg="RS256", use="sig")
    jwks = directory / "public-jwks.json"
    jwks.write_text(json.dumps({"keys": [public]}), encoding="utf-8")
    settings = Settings(database_url="postgresql+psycopg://runtime@127.0.0.1:1/surface_fixture",
        operator_issuer="https://surface-fixture.example.test", operator_audience="security-platform",
        jwks_file=jwks, allowed_hosts=("surface-fixture.example.test",))
    app = create_app(settings)
    try:
        # Only inspect the real application's router and schema. Its lifespan
        # never starts and no DB/auth dependency is substituted or bypassed.
        yield app
    finally:
        app.state.database.close()


def test_openapi_paths_methods_security_and_schemas_match_audited_baseline(inventory_app):
    actual = inventory_app.openapi()
    expected = BASELINE["openapi"]
    assert actual["openapi"] == expected["openapi"]
    assert actual["paths"] == expected["paths"]
    assert actual.get("components", {}) == expected.get("components", {})
    assert actual.get("security") == expected.get("security")
    # Include actual hidden HTTP routes and WebSocket routes, rather than
    # relying solely on endpoints that chose to appear in OpenAPI.
    expected_routes = sorted((path, method.upper()) for path, operations in expected["paths"].items()
                             for method in operations if method in HTTP_METHODS)
    resolved_routes = []
    for route in inventory_app.routes:
        if hasattr(route, "effective_route_contexts"):
            # FastAPI 0.141 keeps included routers lazy; inspect the effective
            # paths, including hidden HTTP/WebSocket/Starlette routes.
            resolved_routes.extend(context.starlette_route or context for context in route.effective_route_contexts())
            resolved_routes.extend(route.effective_low_priority_routes())
        else:
            resolved_routes.append(route)
    actual_routes = sorted((route.path, method) for route in resolved_routes
                           for method in (getattr(route, "methods", None) or {"WEBSOCKET_OR_MOUNT"}))
    assert actual_routes == expected_routes


def test_existing_auth_snapshot_sender_and_transaction_sources_are_unchanged():
    changed = [path for path, identity in BASELINE["platform_files"].items()
               if not (PROJECT / path).is_file() or source_digest(PROJECT / path) != identity["sha256"]]
    assert changed == [], "Protected inventory source changed: " + ", ".join(changed)


def test_no_additional_api_auth_or_migration_files_exist():
    for directory, expected in BASELINE["guarded_directories"].items():
        actual = sorted(path.relative_to(PROJECT).as_posix() for path in (PROJECT / directory).rglob("*")
                        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
        assert actual == expected, "Protected boundary gained or lost files: " + directory


def test_alembic_head_and_database_models_have_no_policy_storage():
    script = ScriptDirectory.from_config(Config(str(PROJECT / "alembic.ini")))
    assert sorted(script.get_heads()) == BASELINE["alembic_heads"]
    assert sorted(Base.metadata.tables) == BASELINE["database_tables"]


def test_existing_inventory_entrypoints_are_preserved_and_only_offline_policy_cli_can_be_added():
    settings = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))
    scripts = settings["project"]["scripts"]
    assert {name: scripts.get(name) for name in BASELINE["existing_scripts"]} == BASELINE["existing_scripts"]
    assert set(scripts) - set(BASELINE["existing_scripts"]) <= set(BASELINE["allowed_added_scripts"])


@pytest.mark.parametrize("field", ["desired_policy", "command", "policy", "apply", "execution_authorized"])
def test_inventory_snapshot_rejects_policy_or_execution_fields(field):
    with pytest.raises(ValidationError):
        SnapshotEnvelope.model_validate({"schema_version": 1, "message_id": str(uuid4()), "sequence": 1,
                                         "products": [], field: False})


def test_legacy_hbf_policy_hash_and_trial_backup_protocol_sources_are_preserved():
    explicit = os.environ.get("SP_HBF_SOURCE")
    candidates = [Path(explicit)] if explicit else [PROJECT.parent / "HostBasedFirewall-main", PROJECT.parent / "HostBasedFirewall"]
    source = next((path for path in candidates if (path / "src/policy_engine.py").is_file()), None)
    if source is None and not explicit:
        pytest.skip("Sibling HBF source unavailable; legacy preservation is not checked in this standalone package")
    assert source is not None, "SP_HBF_SOURCE does not identify the explicit HBF source checkout"
    changed = [path for path, expected in BASELINE["hbf_files"].items()
               if not (source / path).is_file() or source_digest(source / path) != expected]
    assert changed == [], "Legacy HBF policy/recovery source changed: " + ", ".join(changed)
