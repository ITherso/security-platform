"""Actual loopback TLS with a private CA for --ca-file and explicit --rotate-credential.

These fixtures do not claim database acceptance; the real API rotation path is
covered in test_api.py. Verification is never disabled here.
"""
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import ipaddress
import json
import os
from pathlib import Path
import ssl
import tempfile
import threading
from uuid import uuid4

from cryptography import x509
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID
import pytest

from security_platform.connectors.hostbased_firewall import client as client_module
from security_platform.connectors.hostbased_firewall.client import (STATE_FILENAME, SnapshotClientError,
    read_credentials, rotate_credential_file, send_once)
from security_platform.connectors.hostbased_firewall.private_files import (create_private_directory,
    read_private_json, write_private_json)

OLD_SECRET, NEW_SECRET = "spd_" + "o" * 43, "spd_" + "r" * 43


@contextmanager
def private_fixture_root(tmp_path):
    if os.name != "nt":
        yield tmp_path
        return
    import ctypes
    buffer = ctypes.create_unicode_buffer(32768)
    assert ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0
    with tempfile.TemporaryDirectory(prefix=".security-platform-ca-rotation-test-", dir=buffer.value) as directory:
        yield Path(directory)


def certificate_authority(directory, label, names):
    now = datetime.now(timezone.utc)
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    ca_name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, f"Fixture private CA {label}")])
    ca = (x509.CertificateBuilder().subject_name(ca_name).issuer_name(ca_name).public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()), critical=False)
        .sign(ca_key, hashes.SHA256()))
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    alternative = [x509.IPAddress(ipaddress.ip_address(name)) if name[0].isdigit() else x509.DNSName(name) for name in names]
    certificate = (x509.CertificateBuilder().subject_name(x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, names[0])]))
        .issuer_name(ca_name).public_key(key.public_key()).serial_number(x509.random_serial_number())
        .not_valid_before(now - timedelta(minutes=1)).not_valid_after(now + timedelta(hours=1))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(x509.SubjectAlternativeName(alternative), critical=False)
        .add_extension(x509.KeyUsage(digital_signature=True, content_commitment=False, key_encipherment=True,
            data_encipherment=False, key_agreement=False, key_cert_sign=False, crl_sign=False,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .add_extension(x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()), critical=False)
        .add_extension(x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]), critical=False)
        .sign(ca_key, hashes.SHA256()))
    ca_file, cert_file, key_file = (directory / f"ca-{label}.pem", directory / f"server-{label}.pem",
                                    directory / f"server-key-{label}.pem")
    ca_file.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    cert_file.write_bytes(certificate.public_bytes(serialization.Encoding.PEM))
    key_file.write_bytes(key.private_bytes(serialization.Encoding.PEM, serialization.PrivateFormat.PKCS8,
                                         serialization.NoEncryption()))
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    context.load_cert_chain(cert_file, key_file)
    return ca_file, context


@contextmanager
def tls_server(context, device_id):
    """Loopback fixture accepting only the current secret; rotation revokes the old one."""
    current, requests = {"secret": OLD_SECRET}, []
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass
        def reply(self, status, value):
            payload = json.dumps(value).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)
        def authorized(self):
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append((self.command, self.path))
            return body, self.headers["Authorization"] == "Bearer " + current["secret"]
        def do_POST(self):
            body, authorized = self.authorized()
            if self.path != "/api/v1/device/credentials/rotate" or body != b"{}" or not authorized:
                return self.reply(401, {"detail": "Invalid credential"})
            current["secret"] = NEW_SECRET
            self.reply(200, {"tenant_id": str(uuid4()), "device_id": device_id, "credential_id": str(uuid4()),
                             "credential_secret": NEW_SECRET, "credential_expires_at": "2030-01-02T03:04:05Z"})
        def do_PUT(self):
            body, authorized = self.authorized()
            if self.path != "/api/v1/device/snapshot" or not authorized:
                return self.reply(401, {"detail": "Invalid credential"})
            parsed = json.loads(body)
            self.reply(200, {"accepted": True, "message_id": parsed["message_id"], "sequence": parsed["sequence"],
                             "received_at": "2030-01-02T03:04:05Z"})
    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    server.socket = context.wrap_socket(server.socket, server_side=True)
    thread = threading.Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
    thread.start()
    try:
        yield f"https://127.0.0.1:{server.server_port}", requests, current
    finally:
        server.shutdown()
        server.server_close()
        thread.join(2)


def write_inputs(directory, origin, device_id):
    credential_file = create_private_directory(directory / "credentials") / "device.json"
    write_private_json(credential_file, {"schema_version": 1, "base_url": origin, "device_id": device_id,
                                         "credential_secret": OLD_SECRET})
    export = directory / "overview.json"
    export.write_text(json.dumps({"schema_version": 1, "products": [{"id": "antivirus", "status": "planned",
        "available": False, "management": "unavailable", "execution_available": False}], "reports": []}), encoding="utf-8")
    return credential_file, directory / "state", export


def test_cli_ca_file_trusts_private_ca_and_rotates_then_sends_over_real_tls(tmp_path, capsys):
    device_id = str(uuid4())
    with private_fixture_root(tmp_path) as directory:
        ca_file, context = certificate_authority(directory, "trusted", ["localhost", "127.0.0.1"])
        other_ca, _ = certificate_authority(directory, "other", ["localhost", "127.0.0.1"])
        with tls_server(context, device_id) as (origin, requests, current):
            credential_file, state_dir, export = write_inputs(directory, origin, device_id)
            base = ["--credential-file", str(credential_file)]
            # certifi default and a foreign CA both fail before any request reaches the server.
            assert client_module.main([*base, "--rotate-credential"]) == 1
            assert client_module.main([*base, "--rotate-credential", "--ca-file", str(other_ca)]) == 1
            assert capsys.readouterr().err.split() == ["credential_rotation_failed", "credential_rotation_failed"]
            assert requests == [] and read_credentials(credential_file)["credential_secret"] == OLD_SECRET
            assert client_module.main([*base, "--rotate-credential", "--ca-file", str(ca_file)]) == 0
            output = capsys.readouterr()
            assert json.loads(output.out) == {"credential_expires_at": "2030-01-02T03:04:05.000000Z", "credential_rotated": True}
            assert NEW_SECRET not in output.out + output.err and OLD_SECRET not in output.out + output.err
            rotated = read_credentials(credential_file)
            assert rotated == {"schema_version": 1, "base_url": origin, "device_id": device_id, "credential_secret": NEW_SECRET}
            # Old secret is revoked server-side; the rewritten file is what the sender uses.
            assert client_module.main([*base, "--state-dir", str(state_dir), "--initialize-state",
                                       "--snapshot-file", str(export), "--ca-file", str(ca_file)]) == 0
            assert json.loads(capsys.readouterr().out)["sequence"] == 1
            assert requests == [("POST", "/api/v1/device/credentials/rotate"), ("PUT", "/api/v1/device/snapshot")]
            assert read_private_json(state_dir / STATE_FILENAME)["next_sequence"] == 2


def test_ca_file_keeps_hostname_verification_on(tmp_path):
    device_id = str(uuid4())
    with private_fixture_root(tmp_path) as directory:
        ca_file, context = certificate_authority(directory, "mismatch", ["platform.example.test"])
        with tls_server(context, device_id) as (origin, requests, _):
            credential_file, state_dir, export = write_inputs(directory, origin, device_id)
            with pytest.raises(SnapshotClientError, match="^credential_rotation_failed$"):
                rotate_credential_file(credential_file, ca_file=ca_file)
            client_module.initialize_client_state(state_dir, read_credentials(credential_file))
            with pytest.raises(SnapshotClientError, match="^snapshot_delivery_failed$"):
                send_once(export, credential_file, state_dir, ca_file=ca_file)
            assert requests == [] and read_credentials(credential_file)["credential_secret"] == OLD_SECRET
            assert read_private_json(state_dir / STATE_FILENAME)["pending"] is not None
