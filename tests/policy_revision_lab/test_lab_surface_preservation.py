"""Gate 12: the lab stays outside the committed application and HBF boundary.

The fixture was captured explicitly from 35f784b / 74a88ed before lab work.
Tests consume it; they never recapture a baseline from the working tree.
"""
import hashlib
import json
import os
from pathlib import Path
import tomllib

from alembic.config import Config
from alembic.script import ScriptDirectory
from cryptography.hazmat.primitives.asymmetric import rsa
import jwt
import pytest

from security_platform.app import create_app
from security_platform.db import Base
import security_platform.models  # noqa: F401
from security_platform.settings import Settings


PROJECT = Path(__file__).resolve().parents[2]
BASELINE = json.loads((PROJECT / "tests/fixtures/policy_revision_lab/surface_baseline.json").read_text(encoding="utf-8"))
PREVIEW_BASELINE = json.loads((PROJECT / "tests/fixtures/policy_surface_baseline_v1.json").read_text(encoding="utf-8"))


def digest(path):
    return hashlib.sha256(path.read_bytes().replace(b"\r\n", b"\n")).hexdigest()


@pytest.fixture(scope="module")
def inventory_app(tmp_path_factory):
    directory = tmp_path_factory.mktemp("revision-surface-public-jwks")
    public = jwt.algorithms.RSAAlgorithm.to_jwk(rsa.generate_private_key(public_exponent=65537, key_size=2048).public_key(), as_dict=True)
    public.update(kid="revision-surface-fixture", alg="RS256", use="sig")
    path = directory / "public-jwks.json"
    path.write_text(json.dumps({"keys": [public]}), encoding="utf-8")
    app = create_app(Settings(database_url="postgresql+psycopg://runtime@127.0.0.1:1/revision_surface_fixture",
        operator_issuer="https://revision-surface-fixture.example.test", operator_audience="security-platform",
        jwks_file=path, allowed_hosts=("revision-surface-fixture.example.test",)))
    try:
        # No lifespan, DB connection, mocked authorization or changed dependency.
        yield app
    finally:
        app.state.database.close()


def test_all_committed_application_policy_core_and_packaging_sources_are_unchanged():
    changed = [name for name, expected in BASELINE["platform_files"].items()
               if not (PROJECT / name).is_file() or digest(PROJECT / name) != expected]
    assert changed == [], "Production boundary changed: " + ", ".join(changed)


def test_no_application_module_or_migration_has_been_added():
    for directory, expected in BASELINE["production_directories"].items():
        actual = sorted(path.relative_to(PROJECT).as_posix() for path in (PROJECT / directory).rglob("*")
                        if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc")
        assert actual == expected, "Lab must stay outside " + directory


def test_twelve_http_paths_and_auth_security_schemas_are_identical(inventory_app):
    actual, expected = inventory_app.openapi(), PREVIEW_BASELINE["openapi"]
    assert len(actual["paths"]) == 12
    assert actual["paths"] == expected["paths"]
    assert actual.get("components") == expected.get("components")
    assert actual.get("security") == expected.get("security")


def test_hidden_http_routes_and_non_http_routes_have_not_expanded(inventory_app):
    methods = {"get", "put", "post", "delete", "options", "head", "patch", "trace"}
    expected = sorted((path, method.upper()) for path, operations in PREVIEW_BASELINE["openapi"]["paths"].items()
                      for method in operations if method in methods)
    routes = []
    for route in inventory_app.routes:
        if hasattr(route, "effective_route_contexts"):
            routes.extend(context.starlette_route or context for context in route.effective_route_contexts())
            routes.extend(route.effective_low_priority_routes())
        else:
            routes.append(route)
    actual = sorted((route.path, method) for route in routes
                    for method in (getattr(route, "methods", None) or {"WEBSOCKET_OR_MOUNT"}))
    assert actual == expected


def test_application_alembic_head_and_models_have_no_lab_storage():
    script = ScriptDirectory.from_config(Config(str(PROJECT / "alembic.ini")))
    assert sorted(script.get_heads()) == PREVIEW_BASELINE["alembic_heads"]
    assert sorted(Base.metadata.tables) == PREVIEW_BASELINE["database_tables"]


def test_lab_has_no_wheel_entrypoint_or_packaged_module():
    settings = tomllib.loads((PROJECT / "pyproject.toml").read_text(encoding="utf-8"))
    assert settings["project"]["scripts"] == {
        "security-platform": "security_platform.cli:main",
        "security-snapshot": "security_platform.connectors.hostbased_firewall.client:main",
        "security-policy": "security_platform.policy_contracts.cli:main",
    }
    assert settings["tool"]["setuptools"]["packages"]["find"]["where"] == ["src"]
    assert not (PROJECT / "src/security_platform/policy_revision_lab").exists()
    assert not any("policy_revision_lab" in str(value) for value in settings["tool"]["setuptools"].values())


def test_all_committed_hbf_files_remain_at_the_reviewed_baseline():
    explicit = os.environ.get("SP_HBF_SOURCE")
    candidates = [Path(explicit)] if explicit is not None else [PROJECT.parent / "HostBasedFirewall-main", PROJECT.parent / "HostBasedFirewall"]
    source = next((path for path in candidates if (path / "src/policy_engine.py").is_file()), None)
    if source is None and explicit is None:
        pytest.skip("Sibling HBF source absent; full HBF preservation is not checked in this standalone package")
    assert source is not None, "SP_HBF_SOURCE does not identify the explicit HBF source checkout"
    changed = [name for name, expected in BASELINE["hbf_files"].items()
               if not (source / name).is_file() or digest(source / name) != expected]
    assert changed == [], "HBF source changed: " + ", ".join(changed)
