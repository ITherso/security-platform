from datetime import datetime, timedelta, timezone
import json
import os
from pathlib import Path
import ssl
import tempfile
import subprocess
import sys
from uuid import uuid4

import httpx
import pytest

import security_platform.connectors.hostbased_firewall.client as client_module
from security_platform.connectors.hostbased_firewall.client import (MAX_CA_FILE_BYTES, STATE_FILENAME, SnapshotClientError,
    initialize_client_state, read_credentials, rotate_credential_file, send_once, tls_verification, validate_base_url)
from security_platform.connectors.hostbased_firewall.private_files import (ClientFileError, bounded_json,
    create_private_directory, read_private_json, validate_private_path, write_private_json)
from test_snapshot_contracts import local_overview


@pytest.fixture
def client_files(tmp_path):
    # This workstation deliberately grants sandbox accounts write access to
    # AppData/Temp. Native privacy tests must use a trustworthy ancestor chain.
    # Only this newly owned fixture directory is created and removed.
    temporary = None
    if os.name == "nt":
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        assert ctypes.windll.shell32.SHGetFolderPathW(None, 5, None, 0, buffer) == 0
        temporary = tempfile.TemporaryDirectory(prefix=".security-platform-client-test-", dir=buffer.value)
        fixture_root = Path(temporary.name)
    else:
        fixture_root = tmp_path
    private = create_private_directory(fixture_root / "credentials")
    credentials = {"schema_version": 1, "base_url": "https://platform.example.test",
                   "device_id": str(uuid4()), "credential_secret": "spd_" + "x" * 43}
    credential_file = private / "device.json"
    write_private_json(credential_file, credentials)
    state_dir = fixture_root / "state"
    initialize_client_state(state_dir, read_credentials(credential_file))
    export = tmp_path / "local-export.json"
    export.write_text(json.dumps(local_overview()), encoding="utf-8")
    try:
        yield credential_file, state_dir, export, credentials
    finally:
        if temporary is not None:
            temporary.cleanup()


def acknowledgment(request):
    pending = json.loads(request.content)
    return httpx.Response(200, json={"accepted": True, "message_id": pending["message_id"],
        "sequence": pending["sequence"], "received_at": "2026-11-07T10:00:00+00:00"})


def test_one_explicit_send_is_bounded_and_does_not_modify_local_export(client_files):
    credential_file, state_dir, export, credentials = client_files
    original = export.read_bytes()
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "PUT" and request.url.path == "/api/v1/device/snapshot"
        assert request.headers["authorization"] == "Bearer " + credentials["credential_secret"]
        assert len(request.content) < 16384
        return acknowledgment(request)
    result = send_once(export, credential_file, state_dir, transport=httpx.MockTransport(handler))
    assert len(calls) == 1 and result["sequence"] == 1
    assert result["received_at"] == "2026-11-07T10:00:00.000000Z"
    assert export.read_bytes() == original
    state = read_private_json(state_dir / STATE_FILENAME)
    assert state["next_sequence"] == 2 and state["pending"] is None
    assert credentials["credential_secret"] not in (state_dir / STATE_FILENAME).read_text()


def test_response_loss_restart_and_rotation_retry_exact_id_sequence_and_content(client_files):
    credential_file, state_dir, export, credentials = client_files
    bodies, authorizations = [], []
    def lose_response(request):
        bodies.append(request.content)
        authorizations.append(request.headers["authorization"])
        # Represents a committed server update followed by a lost response.
        raise httpx.ReadTimeout("SECRET exception details must not escape", request=request)
    with pytest.raises(SnapshotClientError, match="^snapshot_delivery_failed$"):
        send_once(export, credential_file, state_dir, transport=httpx.MockTransport(lose_response))
    pending = read_private_json(state_dir / STATE_FILENAME)
    assert pending["next_sequence"] == 1 and pending["pending"]["sequence"] == 1
    # Rotate the secret independently; device-wide sequence and pending survive.
    credentials["credential_secret"] = "spd_" + "y" * 43
    write_private_json(credential_file, credentials)
    export.write_text("{invalid newer export is deliberately not used for retry", encoding="utf-8")
    def retry(request):
        bodies.append(request.content)
        authorizations.append(request.headers["authorization"])
        return acknowledgment(request)
    result = send_once(export, credential_file, state_dir, transport=httpx.MockTransport(retry))
    assert result["sequence"] == 1 and bodies[0] == bodies[1]
    assert authorizations[0] != authorizations[1]
    export.write_text(json.dumps(local_overview()), encoding="utf-8")
    third = send_once(export, credential_file, state_dir, transport=httpx.MockTransport(acknowledgment))
    assert third["sequence"] == 2 and third["message_id"] != result["message_id"]


@pytest.mark.parametrize("status", [301, 302, 307, 308, 401, 409, 500])
def test_rejection_does_not_follow_redirects_or_destroy_pending(client_files, status):
    credential_file, state_dir, export, _ = client_files
    calls = []
    def handler(request):
        calls.append(str(request.url))
        return httpx.Response(status, headers={"location": "https://foreign.example/steal"},
                              content=b"SECRET_RESPONSE_MUST_NOT_LEAK")
    with pytest.raises(SnapshotClientError, match="^snapshot_delivery_rejected$"):
        send_once(export, credential_file, state_dir, transport=httpx.MockTransport(handler))
    assert len(calls) == 1 and "foreign" not in calls[0]
    assert read_private_json(state_dir / STATE_FILENAME)["pending"] is not None


@pytest.mark.parametrize("response", [
    b"x" * 4097, b"{not-json", b'{"accepted":true,"accepted":false}',
    json.dumps({"accepted": True, "message_id": str(uuid4()), "sequence": 1,
                "received_at": "2026-11-07T10:00:00Z"}).encode(),
])
def test_invalid_or_oversized_success_reply_retains_pending(client_files, response):
    credential_file, state_dir, export, _ = client_files
    with pytest.raises(SnapshotClientError):
        send_once(export, credential_file, state_dir,
                  transport=httpx.MockTransport(lambda request: httpx.Response(200, content=response)))
    state = read_private_json(state_dir / STATE_FILENAME)
    assert state["pending"] is not None and state["next_sequence"] == 1


def test_unexpected_compression_is_rejected_before_unbounded_decompression(client_files):
    credential_file, state_dir, export, _ = client_files
    class UnreadableStream(httpx.SyncByteStream):
        def __iter__(self):
            pytest.fail("Compressed response must not be read or decompressed")
            yield b""
    def handler(request):
        assert request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, headers={"content-encoding": "gzip"}, stream=UnreadableStream())
    with pytest.raises(SnapshotClientError, match="snapshot_response_encoding_unsupported"):
        send_once(export, credential_file, state_dir, transport=httpx.MockTransport(handler))
    assert read_private_json(state_dir / STATE_FILENAME)["pending"] is not None


def test_missing_restart_state_cannot_silently_reset_sequence(client_files):
    credential_file, state_dir, export, _ = client_files
    (state_dir / STATE_FILENAME).unlink()
    called = []
    with pytest.raises(SnapshotClientError, match="client_state_invalid_or_missing"):
        send_once(export, credential_file, state_dir, transport=httpx.MockTransport(lambda request: called.append(request)))
    assert called == [] and not (state_dir / STATE_FILENAME).exists()


def test_wrong_device_or_server_state_is_not_reused(client_files):
    credential_file, state_dir, export, credentials = client_files
    credentials["device_id"] = str(uuid4())
    write_private_json(credential_file, credentials)
    with pytest.raises(SnapshotClientError, match="client_state_invalid_or_missing"):
        send_once(export, credential_file, state_dir)


def test_explicit_initialization_refuses_existing_state(client_files):
    credential_file, state_dir, _, _ = client_files
    before = (state_dir / STATE_FILENAME).read_bytes()
    with pytest.raises(SnapshotClientError, match="client_state_already_exists"):
        initialize_client_state(state_dir, read_credentials(credential_file))
    assert (state_dir / STATE_FILENAME).read_bytes() == before


@pytest.mark.parametrize("url", ["http://example.com", "http://127.0.0.1", "https://name:secret@example.com",
    "https://example.com/path", "https://example.com?token=secret", "https://example.com/#token", "ftp://example.com"])
def test_https_origin_required_before_any_network(url):
    with pytest.raises(SnapshotClientError):
        validate_base_url(url)
    if "example" in url:
        with pytest.raises(SnapshotClientError):
            validate_base_url(url, allow_test_http=True)
    assert validate_base_url("http://127.0.0.1:8123", allow_test_http=True) == "http://127.0.0.1:8123"


@pytest.mark.parametrize("raw", [b'{"a":1,"a":2}', b'{"a":NaN}', b'{"a":Infinity}', b'{"a":' + b'['*20 + b'0' + b']'*20 + b'}'])
def test_private_json_duplicate_constants_and_depth_fail_closed(raw):
    with pytest.raises(ClientFileError):
        bounded_json(raw, 4096)


def test_client_credential_file_rejects_unknown_fields_without_echoing_secret(client_files):
    credential_file, _, _, credentials = client_files
    credentials["metadata"] = "DO_NOT_PRINT_SECRET"
    write_private_json(credential_file, credentials)
    with pytest.raises(SnapshotClientError, match="^credential_file_invalid$"):
        read_credentials(credential_file)


@pytest.mark.skipif(os.name == "nt", reason="POSIX mode check; Windows uses native owner/DACL checks")
def test_world_readable_credentials_are_refused(client_files):
    credential_file, _, _, _ = client_files
    credential_file.chmod(0o644)
    with pytest.raises(SnapshotClientError):
        read_credentials(credential_file)


def test_private_file_hardlinks_are_rejected(client_files, tmp_path):
    credential_file, _, _, _ = client_files
    os.link(credential_file, tmp_path / "hardlink")
    with pytest.raises(SnapshotClientError):
        read_credentials(credential_file)


def test_client_import_has_no_network_side_effect():
    result = subprocess.run([sys.executable, "-c", "import httpx; httpx.Client=lambda *a,**k:(_ for _ in ()).throw(RuntimeError('unexpected network')); import security_platform.connectors.hostbased_firewall.client; print('ok')"],
                            capture_output=True, text=True, timeout=10)
    assert result.returncode == 0 and result.stdout.strip() == "ok"


def test_trickled_response_cannot_reset_total_request_budget(client_files, monkeypatch):
    import security_platform.connectors.hostbased_firewall.client as module
    credential_file, state_dir, export, _ = client_files
    now = [100.0]
    monkeypatch.setattr(module.time, "monotonic", lambda: now[0])
    class Trickle(httpx.SyncByteStream):
        def __iter__(self):
            for part in (b"{", b'"accepted"', b":true}"):
                now[0] += 4
                yield part
    with pytest.raises(SnapshotClientError, match="snapshot_request_deadline_exceeded"):
        send_once(export, credential_file, state_dir,
                  transport=httpx.MockTransport(lambda request: httpx.Response(200, stream=Trickle())))
    assert read_private_json(state_dir / STATE_FILENAME)["pending"] is not None


@pytest.mark.parametrize("owner,aces,accepted", [
    ("current", [(0, 0, 0x1F01FF, "current")], True),
    ("current", [(0, 0, 0x1F01FF, "S-1-3-4")], True),
    ("current", [(0, 0, 0x1F01FF, "S-1-5-18")], True),
    ("foreign", [(0, 0, 0x1F01FF, "S-1-3-4")], False),
    ("current", [(0, 0, 1, "S-1-5-32-545")], False),
    ("current", [(0, 0, 0x40000, "foreign")], False),
])
def test_windows_private_acl_uses_validated_owner_and_never_trusts_broad_readers(monkeypatch, owner, aces, accepted):
    from security_platform.connectors.hostbased_firewall import private_files
    monkeypatch.setattr(private_files, "_current_windows_sid", lambda: "current")
    monkeypatch.setattr(private_files, "_windows_descriptor", lambda path: (owner, aces))
    if accepted:
        private_files._windows_private_acl(Path("unused-native-descriptor-fixture"))
    else:
        with pytest.raises(ClientFileError):
            private_files._windows_private_acl(Path("unused-native-descriptor-fixture"))


NEW_SECRET = "spd_" + "n" * 43


def rotation_reply(credentials, secret=NEW_SECRET, drop=(), **changes):
    value = {"tenant_id": str(uuid4()), "device_id": credentials["device_id"], "credential_id": str(uuid4()),
             "credential_secret": secret, "credential_expires_at": "2026-11-08T10:00:00Z", **changes}
    return {key: item for key, item in value.items() if key not in drop}


def inject_transport(monkeypatch, transport, seen=None):
    real = httpx.Client
    def client(**options):
        if seen is not None:
            seen.append(options["verify"])
        return real(**{**options, "transport": transport})
    monkeypatch.setattr(client_module.httpx, "Client", client)


def write_test_ca(path):
    from cryptography import x509
    from cryptography.hazmat.primitives import hashes, serialization
    from cryptography.hazmat.primitives.asymmetric import rsa
    from cryptography.x509.oid import NameOID
    key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    name = x509.Name([x509.NameAttribute(NameOID.COMMON_NAME, "Client unit test CA")])
    now = datetime.now(timezone.utc)
    ca = (x509.CertificateBuilder().subject_name(name).issuer_name(name).public_key(key.public_key())
        .serial_number(x509.random_serial_number()).not_valid_before(now - timedelta(minutes=1))
        .not_valid_after(now + timedelta(hours=1)).add_extension(x509.BasicConstraints(ca=True, path_length=0), critical=True)
        .add_extension(x509.KeyUsage(digital_signature=False, content_commitment=False, key_encipherment=False,
            data_encipherment=False, key_agreement=False, key_cert_sign=True, crl_sign=True,
            encipher_only=False, decipher_only=False), critical=True)
        .add_extension(x509.SubjectKeyIdentifier.from_public_key(key.public_key()), critical=False)
        .sign(key, hashes.SHA256()))
    path.write_bytes(ca.public_bytes(serialization.Encoding.PEM))
    return path


def test_explicit_rotation_rewrites_only_the_secret_and_returns_no_secret(client_files):
    credential_file, state_dir, _, credentials = client_files
    state_before = (state_dir / STATE_FILENAME).read_bytes()
    calls = []
    def handler(request):
        calls.append(request)
        assert request.method == "POST" and request.url.path == "/api/v1/device/credentials/rotate"
        assert request.headers["authorization"] == "Bearer " + credentials["credential_secret"]
        assert request.content == b"{}" and request.headers["accept-encoding"] == "identity"
        return httpx.Response(200, json=rotation_reply(credentials))
    result = rotate_credential_file(credential_file, transport=httpx.MockTransport(handler))
    assert len(calls) == 1
    assert result == {"credential_rotated": True, "credential_expires_at": "2026-11-08T10:00:00.000000Z"}
    assert NEW_SECRET not in json.dumps(result) and credentials["credential_secret"] not in json.dumps(result)
    assert read_credentials(credential_file) == {**credentials, "credential_secret": NEW_SECRET}
    validate_private_path(credential_file)
    assert (state_dir / STATE_FILENAME).read_bytes() == state_before
    assert not list(credential_file.parent.glob(".client-*.tmp"))


def test_rotation_reply_without_expiry_returns_fixed_status_only(client_files):
    credential_file, _, _, credentials = client_files
    reply = rotation_reply(credentials, drop=("credential_expires_at", "tenant_id", "credential_id"))
    result = rotate_credential_file(credential_file, transport=httpx.MockTransport(lambda request: httpx.Response(200, json=reply)))
    assert result == {"credential_rotated": True}
    assert read_credentials(credential_file)["credential_secret"] == NEW_SECRET


def test_rotate_cli_prints_fixed_json_status_and_never_a_secret(client_files, monkeypatch, capsys):
    credential_file, _, _, credentials = client_files
    inject_transport(monkeypatch, httpx.MockTransport(lambda request: httpx.Response(200, json=rotation_reply(credentials))))
    assert client_module.main(["--rotate-credential", "--credential-file", str(credential_file)]) == 0
    output = capsys.readouterr()
    assert json.loads(output.out) == {"credential_expires_at": "2026-11-08T10:00:00.000000Z", "credential_rotated": True}
    assert output.err == ""
    assert NEW_SECRET not in output.out and credentials["credential_secret"] not in output.out
    assert read_credentials(credential_file)["credential_secret"] == NEW_SECRET


@pytest.mark.parametrize("status", [200, 307, 401, 429, 500])
def test_rotation_rejection_keeps_credential_and_never_follows_redirects(client_files, status):
    credential_file, _, _, credentials = client_files
    calls = []
    class UnreadableStream(httpx.SyncByteStream):
        def __iter__(self):
            pytest.fail("Compressed rotation response must not be read or decompressed")
            yield b""
    def handler(request):
        calls.append(str(request.url))
        if status == 200:
            return httpx.Response(200, headers={"content-encoding": "gzip"}, stream=UnreadableStream())
        return httpx.Response(status, headers={"location": "https://foreign.example/steal"},
                              content=b"SECRET_RESPONSE_MUST_NOT_LEAK")
    expected = "credential_rotation_response_encoding_unsupported" if status == 200 else "credential_rotation_rejected"
    with pytest.raises(SnapshotClientError, match=f"^{expected}$"):
        rotate_credential_file(credential_file, transport=httpx.MockTransport(handler))
    assert len(calls) == 1 and "foreign" not in calls[0]
    assert read_credentials(credential_file) == credentials


@pytest.mark.parametrize("case", ["foreign_device", "malformed_secret", "same_secret", "extra_field", "bad_expiry",
                                  "missing_secret", "missing_device", "bad_credential_id", "not_json", "duplicate_key"])
def test_invalid_rotation_reply_never_overwrites_credential(client_files, case):
    credential_file, _, _, credentials = client_files
    replies = {"foreign_device": rotation_reply(credentials, device_id=str(uuid4())),
               "malformed_secret": rotation_reply(credentials, secret="spd_short"),
               "same_secret": rotation_reply(credentials, secret=credentials["credential_secret"]),
               "extra_field": rotation_reply(credentials, note="SECRET"),
               "bad_expiry": rotation_reply(credentials, credential_expires_at="tomorrow"),
               "missing_secret": rotation_reply(credentials, drop=("credential_secret",)),
               "missing_device": rotation_reply(credentials, drop=("device_id",)),
               "bad_credential_id": rotation_reply(credentials, credential_id="1")}
    raw = {"not_json": b"{not-json", "duplicate_key": b'{"credential_secret":"a","credential_secret":"b"}'}.get(case)
    raw = raw if raw is not None else json.dumps(replies[case]).encode()
    with pytest.raises(SnapshotClientError, match="^credential_rotation_response_invalid$"):
        rotate_credential_file(credential_file, transport=httpx.MockTransport(lambda request: httpx.Response(200, content=raw)))
    assert read_credentials(credential_file) == credentials


def test_oversized_or_lost_rotation_reply_fails_closed_without_detail(client_files):
    credential_file, _, _, credentials = client_files
    with pytest.raises(SnapshotClientError, match="^credential_rotation_response_too_large$"):
        rotate_credential_file(credential_file, transport=httpx.MockTransport(lambda request: httpx.Response(200, content=b"x" * 4097)))
    def lose(request):
        raise httpx.ReadTimeout("SECRET exception details must not escape", request=request)
    with pytest.raises(SnapshotClientError, match="^credential_rotation_failed$"):
        rotate_credential_file(credential_file, transport=httpx.MockTransport(lose))
    assert read_credentials(credential_file) == credentials


def test_unwritable_credential_file_fails_before_any_rotation_request(client_files, monkeypatch):
    credential_file, _, _, credentials = client_files
    calls = []
    def refuse(path, value):
        raise ClientFileError("private_client_file_unavailable")
    monkeypatch.setattr(client_module, "write_private_json", refuse)
    with pytest.raises(SnapshotClientError, match="^credential_file_not_writable$"):
        rotate_credential_file(credential_file, transport=httpx.MockTransport(lambda request: calls.append(request)))
    assert calls == [] and read_credentials(credential_file) == credentials


def test_write_failure_after_rotation_is_a_fixed_code_and_keeps_atomic_file(client_files, monkeypatch):
    credential_file, _, _, credentials = client_files
    real, writes = client_module.write_private_json, []
    def second_write_fails(path, value):
        writes.append(value["credential_secret"])
        if len(writes) == 2:
            raise OSError("SECRET disk details " + value["credential_secret"])
        real(path, value)
    monkeypatch.setattr(client_module, "write_private_json", second_write_fails)
    with pytest.raises(SnapshotClientError, match="^credential_file_write_failed$") as caught:
        rotate_credential_file(credential_file, transport=httpx.MockTransport(
            lambda request: httpx.Response(200, json=rotation_reply(credentials))))
    assert writes == [credentials["credential_secret"], NEW_SECRET] and "spd_" not in str(caught.value)
    assert read_credentials(credential_file) == credentials


@pytest.mark.parametrize("extra", [["--snapshot-file", "export.json"], ["--state-dir", "state"], ["--initialize-state"]])
def test_rotation_mode_is_mutually_exclusive_with_snapshot_sending(client_files, monkeypatch, capsys, extra):
    credential_file, _, _, credentials = client_files
    monkeypatch.setattr(client_module.httpx, "Client", lambda **options: pytest.fail("no network expected"))
    with pytest.raises(SystemExit) as exited:
        client_module.main(["--rotate-credential", "--credential-file", str(credential_file), *extra])
    assert exited.value.code == 2 and "--rotate-credential cannot be combined" in capsys.readouterr().err
    assert read_credentials(credential_file) == credentials


def test_snapshot_mode_still_requires_state_dir(client_files, capsys):
    credential_file, _, _, _ = client_files
    with pytest.raises(SystemExit) as exited:
        client_module.main(["--credential-file", str(credential_file)])
    assert exited.value.code == 2 and "--state-dir" in capsys.readouterr().err


def test_ca_file_builds_strict_context_and_certifi_stays_default(tmp_path):
    assert tls_verification(None) is True
    context = tls_verification(write_test_ca(tmp_path / "private-ca.pem"))
    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname is True
    assert context.cert_store_stats()["x509_ca"] == 1


@pytest.mark.parametrize("kind", ["missing", "garbage", "directory", "oversized"])
def test_unusable_ca_file_fails_closed_with_fixed_code(tmp_path, kind):
    path = tmp_path / "SECRET-ca.pem"
    if kind == "garbage":
        path.write_bytes(b"-----BEGIN CERTIFICATE-----\nnot a certificate\n-----END CERTIFICATE-----\n")
    elif kind == "directory":
        path.mkdir()
    elif kind == "oversized":
        path.write_bytes(b"#" * (MAX_CA_FILE_BYTES + 1))
    with pytest.raises(SnapshotClientError, match="^ca_file_invalid$"):
        tls_verification(path)


def test_ca_file_reaches_verified_client_for_send_and_rotation(client_files, tmp_path, monkeypatch):
    credential_file, state_dir, export, credentials = client_files
    ca_file = write_test_ca(tmp_path / "private-ca.pem")
    seen = []
    def handler(request):
        if request.method == "POST":
            return httpx.Response(200, json=rotation_reply(credentials))
        return acknowledgment(request)
    inject_transport(monkeypatch, httpx.MockTransport(handler), seen)
    send_once(export, credential_file, state_dir)
    send_once(export, credential_file, state_dir, ca_file=ca_file)
    rotate_credential_file(credential_file, ca_file=ca_file)
    assert len(seen) == 3 and seen[0] is True
    assert all(isinstance(value, ssl.SSLContext) and value.verify_mode == ssl.CERT_REQUIRED and value.check_hostname
               for value in seen[1:])


def test_cli_unusable_ca_file_fails_before_state_initialization(client_files, tmp_path, monkeypatch, capsys):
    credential_file, _, export, _ = client_files
    fresh_state = credential_file.parent.parent / "fresh-state"
    monkeypatch.setattr(client_module.httpx, "Client", lambda **options: pytest.fail("no network expected"))
    code = client_module.main(["--credential-file", str(credential_file), "--state-dir", str(fresh_state),
        "--initialize-state", "--snapshot-file", str(export), "--ca-file", str(tmp_path / "missing-ca.pem")])
    output = capsys.readouterr()
    assert code == 1 and output.err.strip() == "ca_file_invalid" and output.out == ""
    assert not fresh_state.exists()
