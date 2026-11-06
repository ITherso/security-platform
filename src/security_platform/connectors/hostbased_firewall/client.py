"""Explicit one-shot sender. No enrollment, daemon, firewall writes or import-time HTTP."""
import argparse
import ipaddress
import json
from pathlib import Path
import re
import sys
import time
from urllib.parse import urlsplit
from uuid import uuid4

import httpx

from security_platform.contracts import (MAX_SEQUENCE, SnapshotEnvelope, canonical_json, canonical_uuid, utc_text)
from .private_files import (ClientFileError, bounded_json, create_private_directory,
                           private_lock, read_private_json, validate_private_path, write_private_json)
from .snapshot_mapper import SnapshotMappingError, map_snapshot


MAX_RESPONSE_BYTES = 4096
MAX_LOCAL_EXPORT_BYTES = 256 * 1024
STATE_FILENAME = "client_state.json"


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


def send_once(snapshot_file, credential_file, state_dir, *, transport=None, allow_test_http=False):
    """Send one pending-or-new message; unsuccessful delivery retains exact retry content.

    State belongs to a server/device pair, not to one credential. Replacing the
    credential file after server-side rotation preserves pending ID and sequence.
    This function never enrolls, rotates credentials or changes local protection.
    """
    try:
        credentials = read_credentials(credential_file, allow_test_http=allow_test_http)
        directory = validate_private_path(state_dir, directory=True)
        with private_lock(directory):
            path = directory / STATE_FILENAME
            state = _read_state(path, credentials)
            if state["pending"] is None:
                _require(state["next_sequence"] <= MAX_SEQUENCE, "device_sequence_exhausted")
                pending = map_snapshot(_read_export(snapshot_file), sequence=state["next_sequence"], message_id=str(uuid4()))
                state["pending"] = pending.model_dump(mode="json")
                # Durable pending content precedes HTTP. A lost response is
                # retried with the same sequence, UUID and canonical body.
                write_private_json(path, state)
            else:
                pending = SnapshotEnvelope.model_validate(state["pending"])
            body = canonical_json(pending)
            timeout = httpx.Timeout(connect=3.0, read=5.0, write=5.0, pool=3.0)
            deadline = time.monotonic() + 10.0
            try:
                with httpx.Client(verify=True, follow_redirects=False, timeout=timeout,
                                  trust_env=False, transport=transport) as client:
                    with client.stream("PUT", credentials["base_url"] + "/api/v1/device/snapshot",
                            headers={"Authorization": "Bearer " + credentials["credential_secret"],
                                     "Content-Type": "application/json", "Accept-Encoding": "identity"}, content=body) as response:
                        _require(time.monotonic() <= deadline, "snapshot_request_deadline_exceeded")
                        _require(response.status_code == 200, "snapshot_delivery_rejected")
                        _require(response.headers.get("content-encoding", "identity").lower() in ("", "identity"),
                                 "snapshot_response_encoding_unsupported")
                        chunks, size = [], 0
                        for chunk in response.iter_bytes():
                            _require(time.monotonic() <= deadline, "snapshot_request_deadline_exceeded")
                            size += len(chunk)
                            _require(size <= MAX_RESPONSE_BYTES, "snapshot_response_too_large")
                            chunks.append(chunk)
                        acknowledgment = _acknowledgment(b"".join(chunks), pending)
            except SnapshotClientError:
                raise
            except (httpx.HTTPError, OSError) as exc:
                raise SnapshotClientError("snapshot_delivery_failed") from exc
            state.update(next_sequence=pending.sequence + 1, pending=None)
            write_private_json(path, state)
            return acknowledgment
    except SnapshotClientError:
        raise
    except (ClientFileError, SnapshotMappingError, OSError, ValueError, TypeError) as exc:
        raise SnapshotClientError("snapshot_client_failed") from exc


def main(argv=None):
    parser = argparse.ArgumentParser(description="Manually forward one exported local product summary.")
    parser.add_argument("--snapshot-file", type=Path)
    parser.add_argument("--credential-file", required=True, type=Path)
    parser.add_argument("--state-dir", required=True, type=Path)
    parser.add_argument("--initialize-state", action="store_true", help="Explicitly initialize sequence 1 for a newly enrolled device.")
    args = parser.parse_args(argv)
    try:
        if args.initialize_state:
            credentials = read_credentials(args.credential_file)
            initialize_client_state(args.state_dir, credentials)
        result = send_once(args.snapshot_file, args.credential_file, args.state_dir)
        print(json.dumps(result, sort_keys=True))
        return 0
    except SnapshotClientError as exc:
        print(str(exc), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
