"""Separate API and device processes, real CA-verified TLS and PostgreSQL.

All identities and source summaries are fixtures. This exercises the independent
inventory service, not physical endpoint enforcement or a production deployment.
"""
from contextlib import contextmanager
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import subprocess
import sys
import tempfile
import time
from uuid import UUID, uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import httpx
import jwt
import pytest
from sqlalchemy import select

from security_platform.contracts import canonical_json, utc_text
from security_platform.connectors.hostbased_firewall.client import STATE_FILENAME
from security_platform.connectors.hostbased_firewall.private_files import (
    create_private_directory, read_private_json, write_private_json)
from security_platform.connectors.hostbased_firewall.snapshot_mapper import map_snapshot
from security_platform.db import Database
from security_platform.models import AuditEvent, DeviceCredential, EnrollmentGrant, ProductState
from security_platform.services import administration


pytestmark = pytest.mark.e2e
PROJECT = Path(__file__).resolve().parents[2]
PRIVATE_CANARY = "FIXTURE_PRIVATE_SOURCE_MUST_NOT_REACH_SERVER"

# Secrets stay in protected files, never in a process argument. This fixture
# runner calls the same production one-shot function with an explicit test CA.
CLIENT_RUNNER = r'''
import json,os,ssl,sys
from pathlib import Path
import httpx
from security_platform.connectors.hostbased_firewall.client import send_once,SnapshotClientError
config=json.loads(Path(os.environ["SP_FIXTURE_CLIENT_CONFIG"]).read_text(encoding="utf-8"))
transport=(httpx.HTTPTransport(verify=ssl.create_default_context(cafile=config["ca_file"]),trust_env=False)
           if config["trust_fixture_ca"] else None)
try:
    result=send_once(config["export_file"],config["credential_file"],config["state_dir"],transport=transport)
except SnapshotClientError as exc:
    print(json.dumps({"error":str(exc)}))
    raise SystemExit(2)
print(json.dumps(result,sort_keys=True))
'''


@contextmanager
def private_fixture_root(tmp_path):
    if os.name != "nt":
        yield create_private_directory(tmp_path / "fixture")
        return
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0
    with tempfile.TemporaryDirectory(prefix=".security-platform-e2e-", dir=buffer.value) as name:
        yield create_private_directory(Path(name) / "private")


def local_overview():
    """Static exported fields from the existing local product centre."""
    return {"schema_version": 1, "products": [
        {"id": "hostbasedfirewall", "version": "1.4.3", "available": True, "status": "running",
         "management": "local", "engine_status": {"running": True, "stale": False, "mode": "enforce", "errors": []},
         "description": PRIVATE_CANARY, "source_url": "https://fixture-private.invalid/target?secret=" + PRIVATE_CANARY},
        {"id": "termivar", "status": "experimental", "available": True, "management": "offline_report_import",
         "scanner_installed": None, "execution_available": False},
        {"id": "antivirus", "status": "planned", "available": False,
         "management": "unavailable", "execution_available": False}],
        "reports": [{"id": "b" * 64, "product_id": "termivar", "schema": "venom-rendered-assessment/v1",
            "profile": "web-review", "status": "complete", "imported_at": 1700000000.25, "subject_count": 1,
            "item_count": 4, "counts": {"informational": 4, "needs_review": 0, "confirmed": 0},
            "severity_counts": {"unassigned": 4, "info": 0, "low": 0, "medium": 0, "high": 0, "critical": 0},
            "source_claim": "self_reported", "producer_verification": "not_verified", "scope": "offline_report_summary"}],
        "limitations": ["Fixture export only"]}


def certificate_files(directory):
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Security Platform fixture CA")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
    certificate = (x509.CertificateBuilder().subject_name(name).issuer_name(ca_name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName([x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256()))
    ca_file, cert_file, key_file = directory / "ca.pem", directory / "server.pem", directory / "server-key.pem"
    ca_file.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    return ca_file, cert_file, key_file


class SeparateServer:
    def __init__(self, directory, environment, cert_file, key_file, tls_context):
        with socket.socket() as probe:
            probe.bind(("127.0.0.1", 0))
            self.port = probe.getsockname()[1]
        self.origin = f"https://127.0.0.1:{self.port}"
        self.directory, self.environment = directory, environment
        self.cert_file, self.key_file, self.tls_context = cert_file, key_file, tls_context
        self.process = None
        self.logs = []

    def start(self):
        log_file = self.directory / f"api-{len(self.logs)}.log"
        self.logs.append(log_file)
        with log_file.open("wb") as output:
            self.process = subprocess.Popen([sys.executable, "-m", "security_platform.cli", "serve", "--host", "127.0.0.1",
                "--port", str(self.port), "--ssl-certfile", str(self.cert_file), "--ssl-keyfile", str(self.key_file)],
                cwd=PROJECT, env=self.environment, stdin=subprocess.DEVNULL, stdout=output, stderr=subprocess.STDOUT,
                creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
        deadline = time.monotonic() + 12
        with httpx.Client(verify=self.tls_context, trust_env=False, timeout=0.5) as client:
            while time.monotonic() < deadline:
                if self.process.poll() is not None:
                    raise AssertionError("Fixture API failed to start; inspect its private log locally")
                try:
                    if client.get(self.origin + "/readyz").status_code == 200:
                        return
                except httpx.HTTPError:
                    pass
                time.sleep(0.03)
        self.stop()
        raise AssertionError("Fixture API startup timed out")

    def stop(self):
        if self.process is not None and self.process.poll() is None:
            if os.name == "nt":
                # Windows venv launchers can own a real Python child. Terminate
                # this owned process tree so TLS sockets/log handles also close.
                import ctypes
                buffer = ctypes.create_unicode_buffer(32768)
                length = ctypes.windll.kernel32.GetSystemDirectoryW(buffer, len(buffer))
                assert 0 < length < len(buffer)
                subprocess.run([str(Path(buffer.value) / "taskkill.exe"), "/PID", str(self.process.pid), "/T", "/F"],
                    stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=5,
                    creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
            else:
                self.process.terminate()
            try:
                self.process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self.process.kill()
                self.process.wait(timeout=3)


def test_real_tls_separate_api_and_three_fixture_clients(tmp_path):
    config_file = PROJECT.parent / ".tooling" / "platform-test-env.json"
    if not config_file.exists():
        pytest.skip("Real PostgreSQL fixture is required")
    saved = json.loads(config_file.read_text(encoding="utf-8"))
    if not saved.get("ready"):
        pytest.skip("Real PostgreSQL fixture is not ready")
    owner = Database(saved["migration_url"])
    server = None
    observed_secrets = []
    with private_fixture_root(tmp_path) as directory:
        ca_file, cert_file, key_file = certificate_files(directory)
        tls = ssl.create_default_context(cafile=str(ca_file))
        issuer, audience = "https://e2e-fixture.example.test", "security-platform"
        signing_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        public = jwt.algorithms.RSAAlgorithm.to_jwk(signing_key.public_key(), as_dict=True)
        public.update(kid="e2e-fixture", alg="RS256", use="sig")
        jwks_file = directory / "public-jwks.json"
        jwks_file.write_text(json.dumps({"keys": [public]}), encoding="utf-8")
        subjects = {name: str(uuid4()) for name in ("admin_a", "admin_b", "viewer_a")}
        with owner.session() as session:
            tenant_a = UUID(administration.create_tenant(session, "E2E fixture A")["id"])
            tenant_b = UUID(administration.create_tenant(session, "E2E fixture B")["id"])
            for tenant, name, role in ((tenant_a, "admin_a", "tenant_admin"), (tenant_b, "admin_b", "tenant_admin"),
                                       (tenant_a, "viewer_a", "viewer")):
                administration.set_membership(session, tenant, issuer, subjects[name], role)
        def operator(name):
            now = int(time.time())
            token = jwt.encode({"iss": issuer, "aud": audience, "sub": subjects[name], "client_id": "e2e-fixture",
                "iat": now, "exp": now + 300, "jti": str(uuid4())}, signing_key, algorithm="RS256",
                headers={"kid": "e2e-fixture", "typ": "at+jwt"})
            observed_secrets.append(token)
            return {"Authorization": "Bearer " + token}
        environment = dict(os.environ)
        environment.update(SP_DATABASE_URL=saved["runtime_url"], SP_OPERATOR_ISSUER=issuer, SP_OPERATOR_AUDIENCE=audience,
            SP_JWKS_FILE=str(jwks_file), SP_ALLOWED_HOSTS="127.0.0.1,localhost", SP_ALLOW_LOOPBACK_HTTP="false",
            SP_REQUESTS_PER_MINUTE="1000")
        environment.pop("SP_MIGRATION_DATABASE_URL", None)
        server = SeparateServer(directory, environment, cert_file, key_file, tls)
        try:
            server.start()
            clients = []
            with httpx.Client(base_url=server.origin, verify=tls, follow_redirects=False, trust_env=False, timeout=5) as api:
                admin_a, admin_b, viewer = operator("admin_a"), operator("admin_b"), operator("viewer_a")
                for index, tenant in enumerate((tenant_a, tenant_a, tenant_b)):
                    administrator = admin_a if tenant == tenant_a else admin_b
                    grant = api.post(f"/api/v1/tenants/{tenant}/enrollment-grants", headers=administrator, json={})
                    assert grant.status_code == 201 and grant.headers["cache-control"] == "no-store"
                    grant_value = grant.json()
                    observed_secrets.append(grant_value["enrollment_token"])
                    enrolled = api.post("/api/v1/enroll", headers={"Authorization": "Bearer " + grant_value["enrollment_token"]},
                                        json={"label": f"Independent fixture {index + 1}"})
                    assert enrolled.status_code == 201 and enrolled.headers["cache-control"] == "no-store"
                    device = enrolled.json()
                    observed_secrets.append(device["credential_secret"])
                    client_dir = create_private_directory(directory / f"client-{index}")
                    credential_file = client_dir / "device.json"
                    credentials = {"schema_version": 1, "base_url": server.origin, "device_id": device["device_id"],
                                   "credential_secret": device["credential_secret"]}
                    write_private_json(credential_file, credentials)
                    from security_platform.connectors.hostbased_firewall.client import initialize_client_state
                    state_dir = client_dir / "state"
                    initialize_client_state(state_dir, credentials)
                    export = client_dir / "local-export.json"
                    export.write_text(json.dumps(local_overview()), encoding="utf-8")
                    clients.append({"device": device, "tenant": tenant, "credentials": credentials,
                                    "credential_file": credential_file, "state_dir": state_dir, "export": export,
                                    "original_hash": hashlib.sha256(export.read_bytes()).hexdigest(), "directory": client_dir})
                def client_send(client, *, export=True, trust_ca=True, expected=0):
                    configuration = client["directory"] / "send-config.json"
                    write_private_json(configuration, {"credential_file": str(client["credential_file"]),
                        "state_dir": str(client["state_dir"]), "export_file": str(client["export"]) if export else None,
                        "ca_file": str(ca_file), "trust_fixture_ca": trust_ca})
                    child_environment = dict(os.environ)
                    child_environment["SP_FIXTURE_CLIENT_CONFIG"] = str(configuration)
                    child = subprocess.run([sys.executable, "-c", CLIENT_RUNNER], cwd=PROJECT, env=child_environment,
                        stdin=subprocess.DEVNULL, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=15,
                        creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0))
                    assert child.returncode == expected, "Independent fixture client failed"
                    assert len(child.stdout) <= 4096 and child.stderr == b""
                    return json.loads(child.stdout)
                first_client = clients[0]
                # The default sender must refuse this deliberately untrusted
                # fixture CA. Explicit test trust is used for subsequent sends.
                failure = client_send(first_client, trust_ca=False, expected=2)
                assert failure == {"error": "snapshot_delivery_failed"}
                assert read_private_json(first_client["state_dir"] / STATE_FILENAME)["pending"] is not None
                accepted = [client_send(client, export=index != 0) for index, client in enumerate(clients)]
                assert all(ack["sequence"] == 1 for ack in accepted)
                assert len({client["device"]["device_id"] for client in clients}) == 3
                assert len(api.get(f"/api/v1/tenants/{tenant_a}/devices", headers=viewer).json()["items"]) == 2
                assert len(api.get(f"/api/v1/tenants/{tenant_b}/devices", headers=admin_b).json()["items"]) == 1
                assert api.post(f"/api/v1/tenants/{tenant_a}/enrollment-grants", headers=viewer, json={}).status_code == 403
                assert api.get(f"/api/v1/tenants/{tenant_b}/devices", headers=admin_a).status_code == 404
                assert api.get(f"/api/v1/tenants/{tenant_a}/devices/{clients[2]['device']['device_id']}", headers=admin_a).status_code == 404
                path = f"/api/v1/tenants/{tenant_a}/devices/{first_client['device']['device_id']}"
                detail = api.get(path, headers=admin_a).json()
                states = {item["product_id"]: item["state"] for item in detail["products"]}
                assert detail["connection_status"] == "recent"
                assert all(state["source"] == "self_reported" and state["producer_verification"] == "not_verified" for state in states.values())
                assert states["termivar"]["scanner_installed"] is None and states["termivar"]["execution_available"] is False
                assert states["termivar"]["latest_report"]["severity_counts"]["unassigned"] == 4
                assert states["antivirus"]["status"] == "planned" and states["antivirus"]["availability"] == "unavailable"
                original_message = map_snapshot(local_overview(), sequence=1, message_id=accepted[0]["message_id"])
                device_auth = {"Authorization": "Bearer " + first_client["credentials"]["credential_secret"],
                               "Content-Type": "application/json"}
                audit_path = f"/api/v1/tenants/{tenant_a}/audit"
                audit_count = len(api.get(audit_path, headers=admin_a).json()["items"])
                retry = api.put("/api/v1/device/snapshot", headers=device_auth, content=canonical_json(original_message))
                assert retry.status_code == 200
                retry_ack = retry.json()
                retry_ack["received_at"] = utc_text(retry_ack["received_at"].replace("+00:00", "Z"))
                assert retry_ack == accepted[0]
                assert api.get(path, headers=admin_a).json()["last_received_at"] == detail["last_received_at"]
                assert len(api.get(audit_path, headers=admin_a).json()["items"]) == audit_count
                # A stopped centre cannot change the local export. The failed
                # client retains one durable exact message across API restart.
                server.stop()
                assert client_send(first_client, expected=2)["error"] == "snapshot_delivery_failed"
                pending = read_private_json(first_client["state_dir"] / STATE_FILENAME)["pending"]
                assert pending["sequence"] == 2
                server.start()
                resumed = client_send(first_client, export=False)
                assert resumed["sequence"] == 2 and resumed["message_id"] == pending["message_id"]
                assert api.put("/api/v1/device/snapshot", headers=device_auth, content=canonical_json(original_message)).status_code == 409
                rotated = api.post("/api/v1/device/credentials/rotate", headers=device_auth, json={})
                assert rotated.status_code == 200
                rotated_secret = rotated.json()["credential_secret"]
                observed_secrets.append(rotated_secret)
                first_client["credentials"]["credential_secret"] = rotated_secret
                write_private_json(first_client["credential_file"], first_client["credentials"])
                assert client_send(first_client)["sequence"] == 3
                assert api.put("/api/v1/device/snapshot", headers=device_auth, content=canonical_json(original_message)).status_code == 401
                invalid = api.put("/api/v1/device/snapshot", headers={"Authorization": "Bearer " + rotated_secret},
                    json={"schema_version": 1, "message_id": str(uuid4()), "sequence": 4, "products": [],
                          "tenant_id": str(tenant_b), "raw_report": PRIVATE_CANARY})
                assert invalid.status_code == 422 and PRIVATE_CANARY not in invalid.text and rotated_secret not in invalid.text
                assert api.get(path, headers=admin_a).json()["last_sequence"] == 3
                second = clients[1]
                reduced = {"schema_version": 1, "products": [{"id": "hostbasedfirewall", "available": True,
                    "status": "unavailable", "engine_status": {"running": False, "stale": True, "mode": None,
                        "errors": ["health_unavailable"]}}], "reports": []}
                second["export"].write_text(json.dumps(reduced), encoding="utf-8")
                second["original_hash"] = hashlib.sha256(second["export"].read_bytes()).hexdigest()
                assert client_send(second)["sequence"] == 2
                second_path = f"/api/v1/tenants/{tenant_a}/devices/{second['device']['device_id']}"
                omitted = api.get(second_path, headers=admin_a).json()
                assert omitted["missing_products"] == ["antivirus", "edr_agent", "termivar"]
                assert omitted["connection_status"] == "recent" and omitted["products"][0]["state"]["status"] == "unavailable"
                assert api.post(path + "/revoke", headers=admin_a, json={}).status_code == 200
                server.stop()
                server.start()
                assert client_send(first_client, expected=2) == {"error": "snapshot_delivery_rejected"}
                assert api.get(path, headers=admin_a).json()["identity_status"] == "revoked"
                assert client_send(clients[2])["sequence"] == 2
                third_path = f"/api/v1/tenants/{tenant_b}/devices/{clients[2]['device']['device_id']}"
                assert api.post(third_path + "/revoke", headers=admin_b, json={}).status_code == 200
                assert client_send(clients[2], expected=2) == {"error": "snapshot_delivery_rejected"}
                assert client_send(second)["sequence"] == 3
                # Current DB, audit and server logs retain neither raw source
                # fields nor any of the once-returned credentials.
                audit_document = api.get(audit_path, headers=admin_a).json()
                with owner.session() as session:
                    product_rows = session.scalars(select(ProductState).where(ProductState.tenant_id.in_([tenant_a, tenant_b]))).all()
                    grants = session.scalars(select(EnrollmentGrant).where(EnrollmentGrant.tenant_id.in_([tenant_a, tenant_b]))).all()
                    credentials = session.scalars(select(DeviceCredential).where(DeviceCredential.tenant_id.in_([tenant_a, tenant_b]))).all()
                    database_projection = json.dumps({"products": [row.payload for row in product_rows],
                        "grant_digests": [row.token_digest for row in grants], "credential_digests": [row.token_digest for row in credentials]})
                combined = database_projection + json.dumps(audit_document) + "".join(file.read_text(encoding="utf-8") for file in server.logs)
                assert PRIVATE_CANARY not in combined and "fixture-private.invalid" not in combined
                assert all(secret not in combined for secret in observed_secrets)
                for client in clients:
                    assert hashlib.sha256(client["export"].read_bytes()).hexdigest() == client["original_hash"]
                report = {"status": "passed", "executed_at": datetime.now(timezone.utc).isoformat(),
                    "run_id": os.environ.get("SP_ACCEPTANCE_RUN_ID"),
                    "database": "real PostgreSQL", "api_process": "separate process", "transport": "CA-verified TLS",
                    "tenant_count": 2, "device_count": 3, "independent_client_processes": 3,
                    "gates": {"tenant_isolation": "passed", "viewer_restriction": "passed", "enrollment": "passed",
                        "untrusted_certificate_rejected": "passed", "snapshot_retry_no_refresh": "passed",
                        "api_restart_pending_retry": "passed", "rotation_sequence_continuity": "passed",
                        "revocation_persists_restart": "passed", "old_sequence_conflict": "passed",
                        "omitted_products_cleared": "passed", "source_claims_preserved": "passed",
                        "secret_and_source_privacy": "passed", "local_export_unchanged": "passed"},
                    "physical_windows_devices": "not_run", "live_firewall_enforcement": "not_run",
                    "production_acceptance": "not_run"}
                output = Path(os.environ.get("SP_ACCEPTANCE_REPORT", str(PROJECT / "reports" / "e2e-inventory-flow.json")))
                output.parent.mkdir(parents=True, exist_ok=True)
                output.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
        finally:
            if server is not None:
                server.stop()
            owner.close()
