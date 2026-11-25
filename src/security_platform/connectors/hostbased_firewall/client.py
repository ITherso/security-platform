"""Explicit one-shot sender and explicit one-shot credential rotation.

No enrollment, automatic rotation, daemon, firewall writes or import-time HTTP.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import ssl
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from security_platform.contracts import (MAX_SEQUENCE, MAX_SNAPSHOT_SEQUENCE, SnapshotEnvelope, canonical_json,
                                         canonical_uuid, utc_text)
from .private_files import (ClientFileError, bounded_json, create_private_directory,
                           private_lock, read_private_json, validate_private_path, write_private_json)
from .snapshot_mapper import SnapshotMappingError, map_snapshot


MAX_RESPONSE_BYTES = 4096
MAX_LOCAL_EXPORT_BYTES = 256 * 1024
MAX_CA_FILE_BYTES = 1024 * 1024
STATE_FILENAME = "client_state.json"
ROTATE_PATH = "/api/v1/device/credentials/rotate"
ROTATION_REPLY_FIELDS = {"tenant_id", "device_id", "credential_id", "credential_secret", "credential_expires_at"}
# rejected, transport failure, deadline, encoding, size: fixed codes per exchange kind.
SNAPSHOT_CODES = ("snapshot_delivery_rejected", "snapshot_delivery_failed", "snapshot_request_deadline_exceeded",
                  "snapshot_response_encoding_unsupported", "snapshot_response_too_large")
ROTATION_CODES = ("credential_rotation_rejected", "credential_rotation_failed", "credential_rotation_deadline_exceeded",
                  "credential_rotation_response_encoding_unsupported", "credential_rotation_response_too_large")


class SnapshotClientError(ValueError):
    """Fixed reason codes only; never include bearer secrets or server bodies."""


def _require(condition, reason="client_input_invalid"):
    if not condition:
        raise SnapshotClientError(reason)


def validate_base_url(value, *, allow_test_http=False):
    _require(isinstance(value, str) and 0 < len(value) <= 2048)
    parsed = urlsplit(value)
    _require(bool(parsed.hostname) and parsed.username is None and parsed.password is None
             and not parsed.query and not parsed.fragment and parsed.path in ("", "/"))
    try:
        port = parsed.port
    except ValueError as exc:
        raise SnapshotClientError("client_input_invalid") from exc
    _require(port is None or 1 <= port <= 65535)
    if parsed.scheme != "https":
        try:
            loopback = ipaddress.ip_address(parsed.hostname).is_loopback
        except ValueError:
            loopback = parsed.hostname == "localhost"
        _require(allow_test_http and parsed.scheme == "http" and loopback, "https_required")
    _require(not any(ord(char) <= 32 or ord(char) == 127 for char in value))
    return value.rstrip("/")


def read_credentials(path, *, allow_test_http=False):
    try:
        value = read_private_json(path, maximum=4096)
        _require(set(value) == {"schema_version", "base_url", "device_id", "credential_secret"})
        _require(type(value["schema_version"]) is int and value["schema_version"] == 1)
        value["base_url"] = validate_base_url(value["base_url"], allow_test_http=allow_test_http)
        value["device_id"] = canonical_uuid(value["device_id"])
        secret = value["credential_secret"]
        _require(isinstance(secret, str) and re.fullmatch(r"spd_[A-Za-z0-9_-]{43}", secret) is not None)
        return value
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SnapshotClientError("credential_file_invalid") from exc


def tls_verification(ca_file=None):
    """certifi stays the default trust; an explicit CA bundle replaces it. Never disables verification."""
    if ca_file is None:
        return True
    try:
        path = Path(ca_file)
        _require(path.is_file() and path.stat().st_size <= MAX_CA_FILE_BYTES, "ca_file_invalid")
        context = ssl.create_default_context(cafile=str(path))
        _require(context.verify_mode == ssl.CERT_REQUIRED and context.check_hostname, "ca_file_invalid")
        return context
    except SnapshotClientError:
        raise
    except (OSError, ValueError, TypeError) as exc:
        raise SnapshotClientError("ca_file_invalid") from exc


def _bounded_exchange(method, url, secret, body, *, transport, verify, codes):
    """One bounded request: no redirects, environment proxies, compression or unbounded reads."""
    rejected, failed, deadline_exceeded, encoding_unsupported, too_large = codes
    timeout = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=3.0)
    deadline = time.monotonic() + 10.0
    try:
        with httpx.Client(verify=verify, follow_redirects=False, timeout=timeout,
                          trust_env=False, transport=transport) as client:
            with client.stream(method, url, headers={"Authorization": "Bearer " + secret,
                    "Content-Type": "application/json", "Accept-Encoding": "identity"}, content=body) as response:
                _require(time.monotonic() <= deadline, deadline_exceeded)
                _require(response.status_code == 200, rejected)
                _require(response.headers.get("content-encoding", "identity").lower() in ("", "identity"),
                         encoding_unsupported)
                chunks, size = [], 0
                for chunk in response.iter_bytes():
                    _require(time.monotonic() <= deadline, deadline_exceeded)
                    size += len(chunk)
                    _require(size <= MAX_RESPONSE_BYTES, too_large)
                    chunks.append(chunk)
                return b"".join(chunks)
    except SnapshotClientError:
        raise
    except (httpx.HTTPError, OSError) as exc:
        raise SnapshotClientError(failed) from exc


def initialize_client_state(state_dir, credentials):
    """Explicit new-device action; a missing state during a send never resets sequence."""
    try:
        directory = create_private_directory(state_dir)
        with private_lock(directory):
            target = directory / STATE_FILENAME
            _require(not target.exists(), "client_state_already_exists")
            state = {"schema_version": 1, "base_url": credentials["base_url"],
                     "device_id": credentials["device_id"], "next_sequence": 1, "pending": None}
            write_private_json(target, state)
    except SnapshotClientError:
        raise
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SnapshotClientError("client_state_initialization_failed") from exc


def _read_state(path, credentials):
    try:
        state = read_private_json(path)
        _require(set(state) == {"schema_version", "base_url", "device_id", "next_sequence", "pending"})
        _require(type(state["schema_version"]) is int and state["schema_version"] == 1)
        _require(state["base_url"] == credentials["base_url"] and state["device_id"] == credentials["device_id"])
        _require(type(state["next_sequence"]) is int and 1 <= state["next_sequence"] <= MAX_SEQUENCE + 1)
        if state["pending"] is not None:
            pending = SnapshotEnvelope.model_validate(state["pending"])
            _require(pending.sequence == state["next_sequence"])
            canonical_json(pending)
        return state
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SnapshotClientError("client_state_invalid_or_missing") from exc


def _read_export(path):
    _require(path is not None, "snapshot_export_required")
    try:
        with Path(path).open("rb") as stream:
            return bounded_json(stream.read(MAX_LOCAL_EXPORT_BYTES + 1), MAX_LOCAL_EXPORT_BYTES)
    except (OSError, ValueError, TypeError) as exc:
        raise SnapshotClientError("snapshot_export_invalid") from exc


def _acknowledgment(raw, pending):
    try:
        value = bounded_json(raw, MAX_RESPONSE_BYTES)
        _require(set(value) == {"accepted", "message_id", "sequence", "received_at"})
        _require(value["accepted"] is True and value["message_id"] == pending.message_id
                 and type(value["sequence"]) is int and value["sequence"] == pending.sequence)
        received = value["received_at"]
        _require(isinstance(received, str))
        value["received_at"] = utc_text(received[:-6] + "Z" if received.endswith("+00:00") else received)
        return value
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SnapshotClientError("snapshot_acknowledgment_invalid") from exc


def send_once(snapshot_file, credential_file, state_dir, *, transport=None, allow_test_http=False, ca_file=None):
    """Send one pending-or-new message; unsuccessful delivery retains exact retry content.

    State belongs to a server/device pair, not to one credential. Replacing the
    credential file after server-side rotation preserves pending ID and sequence.
    This function never enrolls, rotates credentials or changes local protection.
    """
    try:
        verify = tls_verification(ca_file)
        directory = validate_private_path(state_dir, directory=True)
        with private_lock(directory):
            # Read under the lock: a rotation sharing this directory's lock
            # (credential file inside the state directory) finishes first.
            credentials = read_credentials(credential_file, allow_test_http=allow_test_http)
            path = directory / STATE_FILENAME
            state = _read_state(path, credentials)
            if state["pending"] is None:
                # The contract's snapshot bound; a state file may still hold a larger next_sequence.
                _require(state["next_sequence"] <= MAX_SNAPSHOT_SEQUENCE, "device_sequence_exhausted")
                pending = map_snapshot(_read_export(snapshot_file), sequence=state["next_sequence"], message_id=str(uuid4()))
                state["pending"] = pending.model_dump(mode="json")
                # Durable pending content precedes HTTP. A lost response is
                # retried with the same sequence, UUID and canonical body.
                write_private_json(path, state)
            else:
                pending = SnapshotEnvelope.model_validate(state["pending"])
            raw = _bounded_exchange("PUT", credentials["base_url"] + "/api/v1/device/snapshot",
                credentials["credential_secret"], canonical_json(pending), transport=transport, verify=verify,
                codes=SNAPSHOT_CODES)
            acknowledgment = _acknowledgment(raw, pending)
            state.update(next_sequence=pending.sequence + 1, pending=None)
            write_private_json(path, state)
            return acknowledgment
    except SnapshotClientError:
        raise
    except (ClientFileError, SnapshotMappingError, OSError, ValueError, TypeError) as exc:
        raise SnapshotClientError("snapshot_client_failed") from exc


def _rotation_reply(raw, credentials):
    try:
        value = bounded_json(raw, MAX_RESPONSE_BYTES)
        _require(set(value) <= ROTATION_REPLY_FIELDS and {"device_id", "credential_secret"} <= set(value))
        _require(canonical_uuid(value["device_id"]) == credentials["device_id"])
        secret = value["credential_secret"]
        _require(isinstance(secret, str) and re.fullmatch(r"spd_[A-Za-z0-9_-]{43}", secret) is not None
                 and secret != credentials["credential_secret"])
        for key in ("tenant_id", "credential_id"):
            if key in value:
                canonical_uuid(value[key])
        expires = value.get("credential_expires_at")
        if expires is not None:
            _require(isinstance(expires, str))
            expires = utc_text(expires[:-6] + "Z" if expires.endswith("+00:00") else expires)
        return secret, expires
    except (OSError, ValueError, TypeError, KeyError) as exc:
        raise SnapshotClientError("credential_rotation_response_invalid") from exc


def rotate_credential_file(credential_file, *, transport=None, allow_test_http=False, ca_file=None):
    """Explicit operator action: rotate this device credential once and atomically rewrite the file.

    Base URL and device ID are kept; client state and sequence are untouched. The
    server revokes the old secret in the rotation transaction, so a lost or invalid
    reply, or a failed local write after a successful reply, cannot be recovered:
    the operator revokes the device and re-enrolls it. Nothing here runs automatically.
    """
    try:
        verify = tls_verification(ca_file)
        try:
            path = validate_private_path(credential_file)
        except (ClientFileError, OSError, ValueError) as exc:
            raise SnapshotClientError("credential_file_invalid") from exc
        # Serializes rotations sharing this credential file, and snapshot sends
        # when the credential file lives in the client state directory.
        with private_lock(path.parent):
            credentials = read_credentials(path, allow_test_http=allow_test_http)
            try:
                # Prove the same atomic private rewrite works before the
                # irreversible server-side revocation of the current secret.
                write_private_json(path, credentials)
            except (ClientFileError, OSError, ValueError, TypeError) as exc:
                raise SnapshotClientError("credential_file_not_writable") from exc
            raw = _bounded_exchange("POST", credentials["base_url"] + ROTATE_PATH, credentials["credential_secret"],
                                    b"{}", transport=transport, verify=verify, codes=ROTATION_CODES)
            secret, expires = _rotation_reply(raw, credentials)
            try:
                write_private_json(path, {**credentials, "credential_secret": secret})
            except (ClientFileError, OSError, ValueError, TypeError) as exc:
                raise SnapshotClientError("credential_file_write_failed") from exc
            result = {"credential_rotated": True}
            if expires is not None:
                result["credential_expires_at"] = expires
            return result
    except SnapshotClientError:
        raise
    except (ClientFileError, OSError, ValueError, TypeError) as exc:
        raise SnapshotClientError("credential_rotation_client_failed") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manually forward one exported local product summary, "
                                     "or explicitly rotate this device credential once.")
    parser.add_argument("--snapshot-file", type=Path)
    parser.add_argument("--credential-file", required=True, type=Path)
    parser.add_argument("--state-dir", type=Path, help="Client state directory; required when sending a snapshot.")
    parser.add_argument("--initialize-state", action="store_true", help="Explicitly initialize sequence 1 for a newly enrolled device.")
    parser.add_argument("--rotate-credential", action="store_true", help="Explicitly rotate the device credential once and "
        "atomically rewrite the credential file; sends no snapshot. A lost reply cannot be recovered (re-enroll).")
    parser.add_argument("--ca-file", type=Path, help="PEM CA bundle for a private/enterprise CA; replaces the default "
        "certifi bundle. Certificate and hostname verification stay on.")
    args = parser.parse_args(argv)
    if args.rotate_credential and (args.snapshot_file is not None or args.state_dir is not None or args.initialize_state):
        parser.error("--rotate-credential cannot be combined with --snapshot-file, --state-dir or --initialize-state")
    if not args.rotate_credential and args.state_dir is None:
        parser.error("the following arguments are required: --state-dir")
    try:
        if args.rotate_credential:
            result = rotate_credential_file(args.credential_file, ca_file=args.ca_file)
        else:
            if args.initialize_state:
                tls_verification(args.ca_file)  # An unusable CA file fails before any state exists.
                credentials = read_credentials(args.credential_file)
                initialize_client_state(args.state_dir, credentials)
            result = send_once(args.snapshot_file, args.credential_file, args.state_dir, ca_file=args.ca_file)
        print(json.dumps(result, sort_keys=True))
        return 0
    except SnapshotClientError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
