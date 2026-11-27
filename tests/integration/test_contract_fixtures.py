"""The shared, versioned contract fixtures in tests/fixtures/contracts (GitHub issue #10) on real PostgreSQL.

Every payload goes byte for byte through the real device route (signed operator JWTs, a device bearer from a real
enrollment, no dependency override) and must get the decision expectations.json gives it. An accepted payload's
golden responses (the device's timeline and the device detail, read through the operator API afterwards) are
compared with the stored goldens. SP_REGENERATE_CONTRACT_GOLDENS=1 rewrites the goldens and the manifest instead;
the decisions are checked in both modes and never rewritten. The manifest test checks that manifest.json lists
every file of the tree with its sha256, kind, version and expected decision.

The services take the clock as `now`; the routes pass none, so the module fixes every services module's utc_now at
NOW. The README in the fixture tree documents the clock and the two id placeholders.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import time
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest

from security_platform.app import create_app
from security_platform.contracts import PRODUCT_IDS
from security_platform.services import administration, common
from security_platform.settings import Settings
from test_services import pg_service_databases  # noqa: F401  (shared real-database fixture)


pytestmark = pytest.mark.integration
FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "contracts"
REGENERATE = os.environ.get("SP_REGENERATE_CONTRACT_GOLDENS") == "1"
NOW = datetime(2030, 1, 2, 3, 4, 5, tzinfo=timezone.utc)
NOW_TEXT = "2030-01-02T03:04:05Z"
TENANT_PLACEHOLDER = "11111111-1111-4111-8111-111111111111"
DEVICE_PLACEHOLDER = "22222222-2222-4222-8222-222222222222"
DEVICE_LABEL = "Contract fixture device"
ROUTES = {"events": ("POST", "/api/v1/device/events"), "snapshots": ("PUT", "/api/v1/device/snapshot")}
KINDS = {"events": "event_batch", "snapshots": "snapshot"}
VERSIONS = {"events": (1, 2), "snapshots": (1, 2, 3)}
MANIFEST_SCHEMA = "termivar-contract-fixtures/v1"
EXPECTATIONS = json.loads((FIXTURES / "expectations.json").read_text(encoding="utf-8"))["payloads"]
PAYLOADS = sorted(EXPECTATIONS)


def describe(path):
    """(family, version, validity, name) of a payload path such as events/v2/valid/scan_detected.json."""
    family, version, validity, name = path.split("/")
    assert family in ROUTES and validity in ("valid", "invalid") and name.endswith(".json"), path
    number = int(version.removeprefix("v"))
    assert version == f"v{number}" and number in VERSIONS[family], path
    return family, number, validity, name


def golden_path(path):
    family, version, _, name = describe(path)
    return f"goldens/{family}/v{version}/{name}"


def payload_bytes(path):
    return (FIXTURES / path).read_bytes()


def encoded(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


@pytest.fixture(scope="module")
def contract_app(pg_service_databases, tmp_path_factory):
    owner, runtime = pg_service_databases
    original = common.utc_now

    def fixed(now=None):
        return original(NOW if now is None else now)

    issuer = "https://contract-fixtures.example.test"
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public.update(kid="contract-fixtures", alg="RS256", use="sig")
    jwks = tmp_path_factory.mktemp("contract-jwks") / "public-jwks.json"
    jwks.write_text(json.dumps({"keys": [public]}))
    subject = str(uuid4())
    with owner.session() as session:
        tenant = UUID(administration.create_tenant(session, "Contract fixtures", now=NOW)["id"])
        administration.set_membership(session, tenant, issuer, subject, "tenant_admin", now=NOW)

    def token():
        # The JWT checks use the real clock (operator_oidc), not the services' utc_now.
        issued = int(time.time())
        claims = {"iss": issuer, "aud": "security-platform", "sub": subject, "client_id": "contract-fixtures",
                  "iat": issued, "exp": issued + 300, "jti": str(uuid4())}
        return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "contract-fixtures", "typ": "at+jwt"})

    # The runtime URL that pg_service_databases chose (the shared file, or the SP_* override); never printed.
    settings = Settings(database_url=runtime.engine.url.render_as_string(hide_password=False), operator_issuer=issuer,
                        operator_audience="security-platform", jwks_file=jwks,
                        allowed_hosts=("platform.example.test",), requests_per_minute=10000)
    with pytest.MonkeyPatch.context() as patch:
        # Every services module imported utc_now by name; fix each copy, and the one common's own helpers call.
        for name, module in sorted(sys.modules.items()):
            if name.startswith("security_platform.") and getattr(module, "utc_now", None) is original:
                patch.setattr(module, "utc_now", fixed)
        with TestClient(create_app(settings), base_url="https://platform.example.test") as client:
            yield {"client": client, "tenant": tenant, "token": token}


def auth(value):
    return {"Authorization": "Bearer " + value}


def enroll(ctx):
    grant = ctx["client"].post(f"/api/v1/tenants/{ctx['tenant']}/enrollment-grants", json={},
                               headers=auth(ctx["token"]()))
    assert grant.status_code == 201, grant.text
    device = ctx["client"].post("/api/v1/enroll", json={"label": DEVICE_LABEL},
                                headers=auth(grant.json()["enrollment_token"]))
    assert device.status_code == 201, device.text
    return device.json()


def send(ctx, device, path):
    method, route = ROUTES[describe(path)[0]]
    return ctx["client"].request(method, route, content=payload_bytes(path), headers={
        **auth(device["credential_secret"]), "Content-Type": "application/json"})


def read_state(ctx, device):
    base = f"/api/v1/tenants/{ctx['tenant']}/devices/{device['device_id']}"
    timeline = ctx["client"].get(base + "/events", headers=auth(ctx["token"]()))
    detail = ctx["client"].get(base, headers=auth(ctx["token"]()))
    assert timeline.status_code == 200 and detail.status_code == 200, (timeline.text, detail.text)
    return timeline.json(), detail.json()


def with_placeholders(value, replacements):
    if isinstance(value, dict):
        return {key: with_placeholders(item, replacements) for key, item in value.items()}
    if isinstance(value, list):
        return [with_placeholders(item, replacements) for item in value]
    return replacements.get(value, value) if isinstance(value, str) else value


def strings(value):
    if isinstance(value, dict):
        return [text for item in value.values() for text in strings(item)]
    if isinstance(value, list):
        return [text for item in value for text in strings(item)]
    return [value] if isinstance(value, str) else []


def test_expectations_are_well_formed():
    for path, expected in EXPECTATIONS.items():
        family, version, validity, _ = describe(path)
        assert (FIXTURES / path).is_file(), path
        assert expected["decision"] == ("accepted" if validity == "valid" else "rejected"), path
        assert isinstance(expected["note"], str) and expected["note"], path
        if expected["decision"] == "accepted":
            assert set(expected) == {"decision", "note"}, path
            # A valid payload names its own version and is sent to a fresh device.
            assert json.loads(payload_bytes(path))["schema_version"] == version, path
            continue
        assert set(expected) <= {"decision", "status", "error", "note", "cursor", "after"}, path
        assert expected["status"] in (400, 409, 413, 422) and isinstance(expected["error"], str), path
        assert ("cursor" in expected) == (expected["status"] == 409 and family == "events"), path
        assert ("after" in expected) == (expected["status"] == 409), path
        for prior in expected.get("after", ()):
            assert EXPECTATIONS[prior]["decision"] == "accepted" and describe(prior)[0] == family, (path, prior)


@pytest.mark.parametrize("path", PAYLOADS)
def test_payload_gets_its_expected_decision(contract_app, path):
    ctx = contract_app
    expected = EXPECTATIONS[path]
    family = describe(path)[0]
    device = enroll(ctx)
    for prior in expected.get("after", ()):
        assert send(ctx, device, prior).status_code == 200, prior
    before = read_state(ctx, device)
    response = send(ctx, device, path)
    if expected["decision"] == "rejected":
        body = {"detail": expected["error"], **expected.get("cursor", {})}
        assert (response.status_code, response.json()) == (expected["status"], body), response.text
        # A refused payload writes nothing: the device's timeline and detail are as before it.
        assert read_state(ctx, device) == before
        return
    assert response.status_code == 200, response.text
    ack = response.json()
    payload = json.loads(payload_bytes(path))
    if family == "events":
        assert ack == {"accepted": True, "batch_id": payload["batch_id"], "batch_sequence": payload["batch_sequence"],
                       "last_event_seq": payload["events"][-1]["event_seq"], "received_at": NOW_TEXT}
    else:
        assert ack == {"accepted": True, "message_id": payload["message_id"], "sequence": payload["sequence"],
                       "received_at": NOW_TEXT}
    # The exact retry of the last accepted payload returns the stored acceptance.
    replay = send(ctx, device, path)
    assert (replay.status_code, replay.json()) == (200, ack)
    timeline, detail = read_state(ctx, device)
    if family == "events":
        assert [item["event_seq"] for item in timeline["items"]] == [event["event_seq"]
                                                                     for event in reversed(payload["events"])]
        # Events never refresh the device's heartbeat: an events-only device stays never_seen.
        assert (detail["connection_status"], detail["products"]) == ("never_seen", [])
    else:
        sent = sorted(product["product_id"] for product in payload["products"])
        assert timeline["items"] == [] and [product["product_id"] for product in detail["products"]] == sent
        assert detail["missing_products"] == sorted(set(PRODUCT_IDS) - set(sent))
        assert (detail["connection_status"], detail["last_sequence"]) == ("recent", payload["sequence"])
    replacements = {str(ctx["tenant"]): TENANT_PLACEHOLDER, device["device_id"]: DEVICE_PLACEHOLDER}
    golden = with_placeholders({"payload": path, "ack": ack, "timeline": timeline, "device": detail}, replacements)
    # No run-specific identifier survives the placeholders.
    assert not any(real in text for text in strings(golden) for real in replacements)
    target = FIXTURES / golden_path(path)
    if REGENERATE:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(encoded(golden))
        return
    assert target.is_file(), f"{golden_path(path)} is missing; run with SP_REGENERATE_CONTRACT_GOLDENS=1"
    assert json.loads(target.read_text(encoding="utf-8")) == golden


def build_manifest():
    accepted = {golden_path(path): path for path, expected in EXPECTATIONS.items() if expected["decision"] == "accepted"}
    files = []
    # Sorted by path parts as strings, so the order is the same on every OS: Windows paths compare without case
    # (README.md after goldens/), POSIX paths with it (README.md first), and CI runs on Linux.
    for file in sorted(FIXTURES.rglob("*"), key=lambda item: item.relative_to(FIXTURES).parts):
        if not file.is_file():
            continue
        path = file.relative_to(FIXTURES).as_posix()
        if path == "manifest.json":
            continue
        entry = {"path": path, "sha256": hashlib.sha256(file.read_bytes()).hexdigest()}
        if path in EXPECTATIONS:
            family, version, _, _ = describe(path)
            method, route = ROUTES[family]
            expected = {key: value for key, value in EXPECTATIONS[path].items() if key != "note"}
            entry.update(kind=KINDS[family], version=version, route=f"{method} {route}", expected=expected)
            if expected["decision"] == "accepted":
                entry["golden"] = golden_path(path)
        elif path in accepted:
            entry.update(kind="golden", version=describe(accepted[path])[1], payload=accepted[path])
        elif path == "expectations.json":
            entry["kind"] = "expectations"
        elif path == "README.md":
            entry["kind"] = "readme"
        else:
            entry["kind"] = "unlisted"
        files.append(entry)
    return {"schema": MANIFEST_SCHEMA,
            "about": "Every file of tests/fixtures/contracts but this one, with its sha256. Payloads carry their "
                     "contract version, route and expected decision; goldens name their payload. Written by "
                     "tests/integration/test_contract_fixtures.py with SP_REGENERATE_CONTRACT_GOLDENS=1.",
            "files": files}


def test_manifest_lists_every_file_with_its_hash():
    # Runs after the decision tests (definition order), so a regeneration writes the manifest of the new goldens.
    accepted = {golden_path(path) for path, expected in EXPECTATIONS.items() if expected["decision"] == "accepted"}
    if REGENERATE:
        for stale in sorted((FIXTURES / "goldens").rglob("*.json")):
            if stale.relative_to(FIXTURES).as_posix() not in accepted:
                stale.unlink()
        (FIXTURES / "manifest.json").write_bytes(encoded(build_manifest()))
    manifest = build_manifest()
    assert [entry["path"] for entry in manifest["files"] if entry["kind"] == "unlisted"] == []
    assert {entry["path"] for entry in manifest["files"] if entry["kind"] == "golden"} == accepted
    assert {entry["path"] for entry in manifest["files"] if entry["kind"] in KINDS.values()} == set(EXPECTATIONS)
    stored = json.loads((FIXTURES / "manifest.json").read_text(encoding="utf-8"))
    # Equal lists: no file unlisted, none listed twice or missing, every hash and decision as on disk.
    assert stored == manifest
