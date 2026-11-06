"""Actual loopback TCP/TLS client checks; these do not claim database acceptance."""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import socket
import ssl
import tempfile
import threading
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import NameOID
import pytest

from security_platform.connectors.hostbased_firewall.client import (STATE_FILENAME, SnapshotClientError,
    initialize_client_state, read_credentials, send_once)
from security_platform.connectors.hostbased_firewall.private_files import (create_private_directory,
    read_private_json, write_private_json)


@contextmanager
def private_fixture_root(tmp_path):
    if os.name != "nt":
        yield tmp_path
        return
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0
    with tempfile.TemporaryDirectory(prefix=".security-platform-transport-test-", dir=buffer.value) as directory:
        yield Path(directory)


def write_inputs(directory, base_url):
    credentials_directory = create_private_directory(directory / "credentials")
    credential_file = credentials_directory / "device.json"
    write_private_json(credential_file, {"schema_version": 1, "base_url": base_url,
        "device_id": str(uuid4()), "credential_secret": "spd_" + "t" * 43})
    state_dir = directory / "state"
    initialize_client_state(state_dir, read_credentials(credential_file, allow_test_http=True))
    export = directory / "overview.json"
    export.write_text(json.dumps({"schema_version": 1, "products": [{"id": "antivirus", "status": "planned",
        "available": False, "management": "unavailable", "execution_available": False}], "reports": []}), encoding="utf-8")
    return credential_file, state_dir, export


@contextmanager
def server_fixture(*, mode="success", ssl_context=None):
    bodies, acknowledgments = [], []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def do_PUT(self):
            assert self.path == "/api/v1/device/snapshot"
            body = self.rfile.read(int(self.headers["Content-Length"]))
            assert len(body) <= 16 * 1024
            bodies.append(body)
            if mode == "redirect":
                self.send_response(307)
                self.send_header("Location", "https://unrelated.invalid/secret")
                self.end_headers()
                return
            parsed = json.loads(body)
            ack = {"accepted": True, "message_id": parsed["message_id"], "sequence": parsed["sequence"],
                   "received_at": "2026-11-07T10:00:00Z"}
            if mode == "lose_first_response" and len(bodies) == 1:
                acknowledgments.append(ack)
                self.close_connection = True
                self.connection.shutdown(socket.SHUT_RDWR)
                self.connection.close()
                return
            if mode == "lose_first_response":
                assert body == bodies[0]
                ack = acknowledgments[0]
            payload = b"x" * 4097 if mode == "oversized" else json.dumps(ack).encode()
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    if ssl_context is not None:
        server.socket = ssl_context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        scheme = "https" if ssl_context is not None else "http"
        yield f"{scheme}://127.0.0.1:{server.server_port}", bodies
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def test_actual_loopback_transport_lost_response_retries_exact_pending(tmp_path):
    with private_fixture_root(tmp_path) as directory, server_fixture(mode="lose_first_response") as (origin, bodies):
        credential_file, state_dir, export = write_inputs(directory, origin)
        original = export.read_bytes()
        with pytest.raises(SnapshotClientError, match="snapshot_delivery_failed"):
            send_once(export, credential_file, state_dir, allow_test_http=True)
        first = read_private_json(state_dir / STATE_FILENAME)["pending"]
        accepted = send_once(None, credential_file, state_dir, allow_test_http=True)
        assert accepted["message_id"] == first["message_id"] and accepted["sequence"] == 1
        assert len(bodies) == 2 and bodies[0] == bodies[1]
        assert read_private_json(state_dir / STATE_FILENAME)["next_sequence"] == 2
        assert export.read_bytes() == original


@pytest.mark.parametrize("mode", ["redirect", "oversized"])
def test_actual_transport_rejections_keep_pending(tmp_path, mode):
    with private_fixture_root(tmp_path) as directory, server_fixture(mode=mode) as (origin, bodies):
        credential_file, state_dir, export = write_inputs(directory, origin)
        with pytest.raises(SnapshotClientError):
            send_once(export, credential_file, state_dir, allow_test_http=True)
        assert len(bodies) == 1 and read_private_json(state_dir / STATE_FILENAME)["pending"] is not None


def test_actual_tls_rejects_untrusted_server_certificate(tmp_path):
    with private_fixture_root(tmp_path) as directory:
        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        subject = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "localhost")])
        now = datetime.now(timezone.utc)
        certificate = (x509.CertificateBuilder().subject_name(subject).issuer_name(subject).public_key(key.public_key())
            .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
            .not_valid_after(now + timedelta(hours=1)).add_extension(x509.SubjectAlternativeName([
                x509.DNSName("localhost"), x509.IPAddress(ipaddress.ip_address("127.0.0.1"))]), critical=False)
            .sign(key, hashes.SHA256()))
        cert_file, key_file = directory / "test-cert.pem", directory / "test-key.pem"
        cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
        key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                               serialization.NoEncryption()))
        context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
        context.load_cert_chain(cert_file, key_file)
        with server_fixture(ssl_context=context) as (origin, bodies):
            credential_file, state_dir, export = write_inputs(directory, origin)
            with pytest.raises(SnapshotClientError, match="snapshot_delivery_failed"):
                send_once(export, credential_file, state_dir)
            assert bodies == [] and read_private_json(state_dir / STATE_FILENAME)["pending"] is not None
