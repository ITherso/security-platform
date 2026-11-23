"""Signed operator JWTs + real PostgreSQL; no auth dependency is overridden."""
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from dataclasses import replace
from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import tempfile
import time
from uuid import UUID, uuid4

from cryptography.hazmat.primitives.asymmetric import rsa
from fastapi.testclient import TestClient
import jwt
import pytest
from sqlalchemy import select

from security_platform.app import create_app
from security_platform.connectors.hostbased_firewall.client import read_credentials, rotate_credential_file
from security_platform.connectors.hostbased_firewall.private_files import create_private_directory, write_private_json
from security_platform.db import Database
from security_platform.models import AuditEvent, Device, DeviceCredential, Membership
from security_platform.services import administration
from security_platform.settings import Settings

pytestmark = pytest.mark.integration


@pytest.fixture(scope="module")
def api_database():
    file = Path(__file__).resolve().parents[3] / ".tooling/platform-test-env.json"
    if not file.exists():
        pytest.skip("Real PostgreSQL fixture is required")
    value = json.loads(file.read_text(encoding="utf-8"))
    if not value.get("ready"):
        pytest.skip("Real PostgreSQL fixture is not ready")
    owner = Database(value["migration_url"])
    yield owner, value["runtime_url"]
    owner.close()


@pytest.fixture
def api_context(api_database, tmp_path):
    owner, runtime_url = api_database
    issuer = "https://api-fixture.example.test"
    private = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    public = jwt.algorithms.RSAAlgorithm.to_jwk(private.public_key(), as_dict=True)
    public.update(kid="api-fixture", alg="RS256", use="sig")
    jwks = tmp_path / "public-jwks.json"
    jwks.write_text(json.dumps({"keys": [public]}))
    subjects = {name: str(uuid4()) for name in ("admin_a", "admin_b", "viewer", "both")}
    with owner.session() as session:
        a = UUID(administration.create_tenant(session, "API A")["id"])
        b = UUID(administration.create_tenant(session, "API B")["id"])
        for tenant, name, role in ((a, "admin_a", "tenant_admin"), (b, "admin_b", "tenant_admin"),
                                   (a, "viewer", "viewer"), (a, "both", "tenant_admin"), (b, "both", "viewer")):
            administration.set_membership(session, tenant, issuer, subjects[name], role)
    def token(name="admin_a", **changes):
        now = int(time.time())
        claims = {"iss": issuer, "aud": "security-platform", "sub": subjects[name], "client_id": "fixture-client",
                  "iat": now, "exp": now + 300, "jti": str(uuid4()), **changes}
        return jwt.encode(claims, private, algorithm="RS256", headers={"kid": "api-fixture", "typ": "at+jwt"})
    settings = Settings(database_url=runtime_url, operator_issuer=issuer, operator_audience="security-platform",
        jwks_file=jwks, allowed_hosts=("platform.example.test", "127.0.0.1", "localhost"), requests_per_minute=1000)
    app = create_app(settings)
    with TestClient(app, base_url="https://platform.example.test") as client:
        yield {"client": client, "app": app, "owner": owner, "a": a, "b": b,
               "token": token, "issuer": issuer, "subjects": subjects, "settings": settings}


def auth(value):
    return {"Authorization": "Bearer " + value}


def new_grant(ctx, tenant=None, operator=None):
    response = ctx["client"].post(f"/api/v1/tenants/{tenant or ctx['a']}/enrollment-grants", json={},
        headers=auth(operator or ctx["token"]()))
    assert response.status_code == 201, response.text
    assert response.headers["cache-control"] == "no-store"
    return response.json()


def enroll(ctx, tenant=None, operator=None):
    grant = new_grant(ctx, tenant, operator)
    response = ctx["client"].post("/api/v1/enroll", json={"label": "Fixture device"}, headers=auth(grant["enrollment_token"]))
    assert response.status_code == 201, response.text
    return response.json(), grant


def snapshot(sequence=1, **changes):
    return {"schema_version": 1, "message_id": str(uuid4()), "sequence": sequence, "products": [], **changes}


def test_real_jwt_tenant_isolation_all_object_and_list_routes(api_context):
    ctx = api_context; client = ctx["client"]
    a_device, _ = enroll(ctx)
    b_device, b_grant = enroll(ctx, ctx["b"], ctx["token"]("admin_b"))
    headers = auth(ctx["token"]())
    result = client.get("/api/v1/tenants", headers=headers)
    assert [row["id"] for row in result.json()["items"]] == [str(ctx["a"])]
    for method, path in (("GET", f"/tenants/{ctx['b']}/devices"),
        ("GET", f"/tenants/{ctx['b']}/devices/{b_device['device_id']}"),
        ("GET", f"/tenants/{ctx['b']}/audit"), ("POST", f"/tenants/{ctx['b']}/devices/{b_device['device_id']}/revoke"),
        ("POST", f"/tenants/{ctx['b']}/enrollment-grants"),
        ("POST", f"/tenants/{ctx['b']}/enrollment-grants/{b_grant['grant_id']}/revoke")):
        response = client.request(method, "/api/v1" + path, json={} if method == "POST" else None, headers=headers)
        assert response.status_code == 404, (method, path, response.text)
    assert client.get(f"/api/v1/tenants/{ctx['a']}/devices/{b_device['device_id']}", headers=headers).status_code == 404
    assert client.get(f"/api/v1/tenants/{ctx['a']}/devices?offset=1&limit=1", headers=headers).status_code == 200
    assert client.get(f"/api/v1/tenants/{ctx['b']}/devices?offset=1&limit=1", headers=headers).status_code == 404


def test_roles_come_from_current_tenant_membership_and_revocation(api_context):
    ctx = api_context; client = ctx["client"]
    forged = ctx["token"]("viewer", roles=["tenant_admin"], tenant=str(ctx["b"]), is_admin=True)
    assert client.post(f"/api/v1/tenants/{ctx['a']}/enrollment-grants", json={}, headers=auth(forged)).status_code == 403
    assert client.get(f"/api/v1/tenants/{ctx['a']}/devices", headers=auth(forged)).status_code == 200
    assert client.get(f"/api/v1/tenants/{ctx['b']}/devices", headers=auth(forged)).status_code == 404
    both = ctx["token"]("both")
    assert client.post(f"/api/v1/tenants/{ctx['b']}/enrollment-grants", json={}, headers=auth(both)).status_code == 403
    assert client.post(f"/api/v1/tenants/{ctx['a']}/enrollment-grants", json={}, headers=auth(both)).status_code == 201
    with ctx["owner"].session() as session:
        administration.revoke_membership(session, ctx["a"], ctx["issuer"], ctx["subjects"]["both"])
    assert client.get(f"/api/v1/tenants/{ctx['a']}/devices", headers=auth(both)).status_code == 404


def test_wrong_principal_kind_is_rejected_by_every_endpoint_family(api_context):
    ctx = api_context; client = ctx["client"]
    device, grant = enroll(ctx)
    for credential in (device["credential_secret"], grant["enrollment_token"]):
        assert client.get("/api/v1/tenants", headers=auth(credential)).status_code == 401
    assert client.post("/api/v1/enroll", json={"label": "wrong"}, headers=auth(ctx["token"]())).status_code == 401
    assert client.put("/api/v1/device/snapshot", json=snapshot(), headers=auth(ctx["token"]())).status_code == 401
    assert client.put("/api/v1/device/snapshot", json=snapshot(), headers=auth(grant["enrollment_token"])).status_code == 401
    assert client.post("/api/v1/enroll", json={"label": "wrong"}, headers=auth(device["credential_secret"])).status_code == 401


def test_single_use_enrollment_has_no_plaintext_secret_in_database_or_audit(api_context):
    ctx = api_context; client = ctx["client"]
    device, grant = enroll(ctx)
    assert client.post("/api/v1/enroll", json={"label": "retry lost reply"}, headers=auth(grant["enrollment_token"])).status_code == 401
    with ctx["owner"].session() as session:
        credential = session.scalar(select(DeviceCredential).where(DeviceCredential.id == UUID(device["credential_id"])))
        assert credential.token_digest != device["credential_secret"] and len(credential.token_digest) == 64
    audit = client.get(f"/api/v1/tenants/{ctx['a']}/audit", headers=auth(ctx["token"]())).text
    assert device["credential_secret"] not in audit and grant["enrollment_token"] not in audit


def test_snapshot_replay_has_no_freshness_or_counter_side_effects(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx); headers = auth(device["credential_secret"])
    message = snapshot()
    first = client.put("/api/v1/device/snapshot", json=message, headers=headers)
    assert first.status_code == 200, first.text
    repeated = client.put("/api/v1/device/snapshot", json=message, headers=headers)
    assert repeated.json() == first.json()
    assert client.put("/api/v1/device/snapshot", json={**message, "products": [{"product_id": "antivirus", "status": "planned"}]}, headers=headers).status_code == 409
    newer = snapshot(2)
    assert client.put("/api/v1/device/snapshot", json=newer, headers=headers).status_code == 200
    assert client.put("/api/v1/device/snapshot", json=message, headers=headers).status_code == 409


def test_rotation_revocation_and_expiry_survive_new_app_instance(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    assert client.put("/api/v1/device/snapshot", json=snapshot(1), headers=auth(device["credential_secret"])).status_code == 200
    rotated = client.post("/api/v1/device/credentials/rotate", json={}, headers=auth(device["credential_secret"]))
    assert rotated.status_code == 200, rotated.text
    secret = rotated.json()["credential_secret"]
    assert client.put("/api/v1/device/snapshot", json=snapshot(2), headers=auth(device["credential_secret"])).status_code == 401
    with TestClient(create_app(ctx["settings"]), base_url="https://platform.example.test") as restarted:
        assert restarted.put("/api/v1/device/snapshot", json=snapshot(2), headers=auth(secret)).status_code == 200
        response = restarted.post(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}/revoke", json={}, headers=auth(ctx["token"]()))
        assert response.status_code == 200
        assert restarted.put("/api/v1/device/snapshot", json=snapshot(3), headers=auth(secret)).status_code == 401


def test_invalid_snapshot_is_atomic_and_does_not_echo_private_input(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx); headers = auth(device["credential_secret"])
    private = "private-input-canary"
    for message in (snapshot(tenant_id=str(ctx["b"])), snapshot(sequence=True),
                    snapshot(products=[{"product_id": "antivirus", "metadata": private}])):
        result = client.put("/api/v1/device/snapshot", json=message, headers=headers)
        assert result.status_code == 422 and private not in result.text
    status = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}", headers=auth(ctx["token"]())).json()
    assert status["connection_status"] == "never_seen" and status["last_sequence"] is None


def test_future_device_clock_cannot_keep_connection_recent(api_context):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    result = client.put("/api/v1/device/snapshot", json=snapshot(source_observed_at="2099-01-01T00:00:00Z"), headers=auth(device["credential_secret"]))
    assert result.status_code == 200
    with ctx["owner"].session() as session:
        row = session.get(Device, UUID(device["device_id"]))
        row.last_received_at = datetime.now(timezone.utc) - timedelta(seconds=1000)
    data = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{device['device_id']}", headers=auth(ctx["token"]())).json()
    assert data["connection_status"] == "stale" and data["source_observation"]["clock_state"] == "future"


def test_parallel_enrollment_and_rotation_accept_at_most_one(api_context):
    ctx = api_context; client = ctx["client"]
    grant = new_grant(ctx)
    def enroll_request(_):
        return client.post("/api/v1/enroll", json={"label": "Race"}, headers=auth(grant["enrollment_token"]))
    with ThreadPoolExecutor(max_workers=2) as pool:
        replies = list(pool.map(enroll_request, range(2)))
    assert sorted(reply.status_code for reply in replies) == [201, 401]
    secret = next(reply.json()["credential_secret"] for reply in replies if reply.status_code == 201)
    def rotate_request(_):
        return client.post("/api/v1/device/credentials/rotate", json={}, headers=auth(secret)).status_code
    with ThreadPoolExecutor(max_workers=2) as pool:
        assert sorted(pool.map(rotate_request, range(2))) == [200, 401]


def test_no_remote_execution_or_public_signup_surface_exists(api_context):
    app = api_context["app"]
    actual = {(method, path) for path, operations in app.openapi()["paths"].items() for method in operations}
    expected = {("get", "/livez"), ("get", "/readyz"), ("get", "/api/v1/tenants"),
        ("post", "/api/v1/tenants/{tenant_id}/enrollment-grants"),
        ("post", "/api/v1/tenants/{tenant_id}/enrollment-grants/{grant_id}/revoke"),
        ("get", "/api/v1/tenants/{tenant_id}/devices"), ("get", "/api/v1/tenants/{tenant_id}/devices/{device_id}"),
        ("post", "/api/v1/tenants/{tenant_id}/devices/{device_id}/revoke"), ("get", "/api/v1/tenants/{tenant_id}/audit"),
        ("post", "/api/v1/enroll"), ("put", "/api/v1/device/snapshot"), ("post", "/api/v1/device/credentials/rotate"),
        ("post", "/api/v1/device/events"), ("get", "/api/v1/tenants/{tenant_id}/devices/{device_id}/events")}
    assert actual == expected
    spec = app.openapi()
    assert set(spec["components"]["securitySchemes"]) == {"OperatorAccessToken", "EnrollmentGrant", "DeviceCredential"}
    assert spec["paths"]["/api/v1/enroll"]["post"]["security"] == [{"EnrollmentGrant": []}]
    assert spec["paths"]["/api/v1/device/snapshot"]["put"]["security"] == [{"DeviceCredential": []}]
    assert spec["paths"]["/api/v1/device/events"]["post"]["security"] == [{"DeviceCredential": []}]
    assert spec["paths"]["/api/v1/tenants"]["get"]["security"] == [{"OperatorAccessToken": []}]
    assert spec["paths"]["/api/v1/tenants/{tenant_id}/devices/{device_id}/events"]["get"]["security"] == [
        {"OperatorAccessToken": []}]
    for route in ("/signup", "/api/v1/commands", "/api/v1/device/shell", "/api/v1/device/policy", "/api/v1/device/scan"):
        assert api_context["client"].post(route, json={}).status_code == 404


def test_device_identity_is_derived_from_bearer_not_headers_or_body(api_context):
    ctx = api_context; client = ctx["client"]
    first, _ = enroll(ctx)
    second, _ = enroll(ctx, ctx["b"], ctx["token"]("admin_b"))
    headers = {**auth(first["credential_secret"]), "X-Device-ID": second["device_id"], "X-Tenant-ID": str(ctx["b"])}
    assert client.put("/api/v1/device/snapshot", json=snapshot(), headers=headers).status_code == 200
    assert client.put("/api/v1/device/snapshot", json=snapshot(2, device_id=second["device_id"]), headers=headers).status_code == 422
    target = client.get(f"/api/v1/tenants/{ctx['b']}/devices/{second['device_id']}", headers=auth(ctx["token"]("admin_b"))).json()
    source = client.get(f"/api/v1/tenants/{ctx['a']}/devices/{first['device_id']}", headers=auth(ctx["token"]())).json()
    assert target["connection_status"] == "never_seen"
    assert source["last_sequence"] == 1


@contextmanager
def private_client_root(tmp_path):
    # Same trustworthy-ancestor rule as the client unit tests on this workstation.
    if os.name != "nt":
        yield tmp_path
        return
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0
    with tempfile.TemporaryDirectory(prefix=".security-platform-api-client-test-", dir=buffer.value) as directory:
        yield Path(directory)


def utc(value):
    return datetime.fromisoformat(value.replace("Z", "+00:00"))


def test_shipped_client_rotation_against_real_api_keeps_device_and_sequence(api_context, tmp_path):
    ctx = api_context; client = ctx["client"]
    device, _ = enroll(ctx)
    assert client.put("/api/v1/device/snapshot", json=snapshot(1), headers=auth(device["credential_secret"])).status_code == 200
    with private_client_root(tmp_path) as root:
        credential_file = create_private_directory(root / "credentials") / "device.json"
        write_private_json(credential_file, {"schema_version": 1, "base_url": "https://platform.example.test",
            "device_id": device["device_id"], "credential_secret": device["credential_secret"]})
        before = datetime.now(timezone.utc)
        # The in-process ASGI transport replaces only the network; the client's own request/reply checks run.
        result = rotate_credential_file(credential_file, transport=client._transport)
        after = datetime.now(timezone.utc)
        rotated = read_credentials(credential_file)
    assert set(result) == {"credential_rotated", "credential_expires_at"} and result["credential_rotated"] is True
    assert rotated["device_id"] == device["device_id"] and rotated["base_url"] == "https://platform.example.test"
    assert rotated["credential_secret"] != device["credential_secret"]
    assert rotated["credential_secret"] not in json.dumps(result)
    ttl = timedelta(seconds=ctx["settings"].credential_ttl_seconds)
    assert before + ttl <= utc(result["credential_expires_at"]) <= after + ttl
    assert client.put("/api/v1/device/snapshot", json=snapshot(2), headers=auth(device["credential_secret"])).status_code == 401
    accepted = client.put("/api/v1/device/snapshot", json=snapshot(2), headers=auth(rotated["credential_secret"]))
    assert accepted.status_code == 200 and accepted.json()["sequence"] == 2
    audit = client.get(f"/api/v1/tenants/{ctx['a']}/audit", headers=auth(ctx["token"]())).text
    assert rotated["credential_secret"] not in audit and "device_credential_rotated" in audit


def test_device_cannot_rotate_into_lifetime_longer_than_configured_ttl(api_context):
    ctx = api_context
    with TestClient(create_app(replace(ctx["settings"], credential_ttl_seconds=3600)),
                    base_url="https://platform.example.test") as client:
        device, _ = enroll({**ctx, "client": client})
        secret = device["credential_secret"]
        for requested, expected in ((2592000, 3600), (120, 120)):
            before = datetime.now(timezone.utc)
            reply = client.post("/api/v1/device/credentials/rotate", json={"ttl_seconds": requested}, headers=auth(secret))
            after = datetime.now(timezone.utc)
            assert reply.status_code == 200, reply.text
            expires = utc(reply.json()["credential_expires_at"])
            assert before + timedelta(seconds=expected) <= expires <= after + timedelta(seconds=expected)
            secret = reply.json()["credential_secret"]
        assert client.post("/api/v1/device/credentials/rotate", json={"ttl_seconds": 2592001},
                           headers=auth(secret)).status_code == 422


def test_revoked_devices_do_not_consume_tenant_capacity(api_context):
    ctx = api_context
    with TestClient(create_app(replace(ctx["settings"], max_devices_per_tenant=1)),
                    base_url="https://platform.example.test") as client:
        local = {**ctx, "client": client}
        first, _ = enroll(local)
        grant = new_grant(local)
        over = client.post("/api/v1/enroll", json={"label": "Over cap"}, headers=auth(grant["enrollment_token"]))
        assert over.status_code == 429 and over.json() == {"detail": "Device capacity reached"}
        revoked = client.post(f"/api/v1/tenants/{ctx['a']}/devices/{first['device_id']}/revoke", json={},
                              headers=auth(ctx["token"]()))
        assert revoked.status_code == 200
        replacement = client.post("/api/v1/enroll", json={"label": "Replacement"}, headers=auth(grant["enrollment_token"]))
        assert replacement.status_code == 201, replacement.text
        assert client.put("/api/v1/device/snapshot", json=snapshot(1),
                          headers=auth(first["credential_secret"])).status_code == 401


def test_device_rotations_cannot_push_operator_events_out_of_audit(api_context):
    ctx = api_context
    with TestClient(create_app(replace(ctx["settings"], max_audit_events_per_tenant=10)),
                    base_url="https://platform.example.test") as client:
        device, grant = enroll({**ctx, "client": client})
        secret = device["credential_secret"]
        for _ in range(12):
            reply = client.post("/api/v1/device/credentials/rotate", json={}, headers=auth(secret))
            assert reply.status_code == 200, reply.text
            secret = reply.json()["credential_secret"]
        items = client.get(f"/api/v1/tenants/{ctx['a']}/audit?limit=100", headers=auth(ctx["token"]())).json()["items"]
    assert len(items) == 10
    assert [item["action"] for item in items if item["actor_type"] == "local_admin"].count("membership_set") == 3
    assert any(item["action"] == "tenant_created" for item in items)
    assert [item["object_id"] for item in items if item["actor_type"] == "operator"] == [grant["grant_id"]]
    assert [item["action"] for item in items if item["actor_type"] == "device"] == ["device_credential_rotated"] * 5


def test_runtime_cannot_be_replaced_by_migration_owner_credentials(api_context, api_database):
    from dataclasses import replace
    ctx = api_context
    owner, _ = api_database
    # The owner URL comes only from an already-owned connection object; never
    # include it in an assertion message or endpoint response.
    privileged = replace(ctx["settings"], database_url=owner.engine.url.render_as_string(hide_password=False))
    with pytest.raises(ValueError, match="separate unprivileged runtime"):
        with TestClient(create_app(privileged), base_url="https://platform.example.test"):
            pass
