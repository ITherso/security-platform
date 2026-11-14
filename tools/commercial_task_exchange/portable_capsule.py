"""One canonical four-member task capsule; stdlib and local protocol only."""
from __future__ import annotations

import hashlib
import io
import stat
import zipfile

from exchange_contracts import (
    CAPSULE_SCHEMA, MAX_CAPSULE_BYTES, MAX_EXPANDED_BYTES, InputError,
    common, json_bytes, validate_portable_request, validate_response_contract,
)

ZIP_NAMES = ("task-request.json", "response-contract.json", "README.txt", "capsule-manifest.json")
PAYLOAD_NAMES = ZIP_NAMES[:3]
MEMBER_LIMITS = dict(zip(ZIP_NAMES, (64 * 1024, 32 * 1024, 4 * 1024, 32 * 1024)))
REGULAR_FILE_ATTRIBUTES = (stat.S_IFREG | 0o600) << 16
README_BYTES = (
    "OFFLINE TASK REQUEST ONLY\n"
    "This package contains a task request and future response field definitions.\n"
    "It contains no response, new observation, assignment or execution authority.\n"
    "Hashes establish internal byte correspondence, not producer authentication,\n"
    "recipient authorization, original source truth or task dispatch.\n"
    "A source locator is not supplied. An authorized person must provide it separately.\n"
    "The fixed ZIP date is format metadata, not an observation timestamp.\n"
).encode("utf-8")


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def capsule_manifest_data(envelope: dict, response_contract: dict, payloads: dict) -> dict:
    envelope = validate_portable_request(envelope)
    response_contract = validate_response_contract(response_contract)
    if type(payloads) is not dict or tuple(payloads) != PAYLOAD_NAMES:
        raise InputError("task_exchange_capsule_payload_inventory_invalid")
    expected = {
        "task-request.json": json_bytes(envelope, maximum=MEMBER_LIMITS[ZIP_NAMES[0]]),
        "response-contract.json": json_bytes(response_contract, maximum=MEMBER_LIMITS[ZIP_NAMES[1]]),
        "README.txt": README_BYTES,
    }
    files = []
    for name in PAYLOAD_NAMES:
        raw = payloads[name]
        if type(raw) is not bytes or not 0 < len(raw) <= MEMBER_LIMITS[name] or raw != expected[name]:
            raise InputError("task_exchange_capsule_payload_not_canonical")
        files.append({"name": name, **byte_identity(raw)})
    return {
        **common(CAPSULE_SCHEMA), "files": files, "manifest_self_excluded": True,
        "integrity_scope": "four_member_task_exchange_capsule_internal_correspondence_only",
    }


def build_task_exchange_capsule(envelope: dict, response_contract: dict) -> bytes:
    """Produce exactly one bounded STORED representation without source I/O."""
    envelope = validate_portable_request(envelope)
    response_contract = validate_response_contract(response_contract)
    payloads = {
        "task-request.json": json_bytes(envelope, maximum=MEMBER_LIMITS[ZIP_NAMES[0]]),
        "response-contract.json": json_bytes(response_contract, maximum=MEMBER_LIMITS[ZIP_NAMES[1]]),
        "README.txt": README_BYTES,
    }
    manifest = capsule_manifest_data(envelope, response_contract, payloads)
    documents = {**payloads, "capsule-manifest.json": json_bytes(manifest, maximum=MEMBER_LIMITS[ZIP_NAMES[3]])}
    if (any(not 0 < len(raw) <= MEMBER_LIMITS[name] for name, raw in documents.items())
            or sum(len(raw) for raw in documents.values()) > MAX_EXPANDED_BYTES):
        raise InputError("task_exchange_capsule_expanded_size_invalid")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        archive.comment = b""
        for name in ZIP_NAMES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.flag_bits = 0
            info.internal_attr = 0
            info.external_attr = REGULAR_FILE_ATTRIBUTES
            info.compress_type = zipfile.ZIP_STORED
            info.extra = b""
            info.comment = b""
            archive.writestr(info, documents[name])
    raw = buffer.getvalue()
    if not 0 < len(raw) <= MAX_CAPSULE_BYTES:
        raise InputError("task_exchange_capsule_archive_size_invalid")
    return raw


__all__ = ("ZIP_NAMES", "PAYLOAD_NAMES", "MEMBER_LIMITS", "REGULAR_FILE_ATTRIBUTES",
           "README_BYTES", "byte_identity", "capsule_manifest_data", "build_task_exchange_capsule")
