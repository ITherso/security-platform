"""Memory-only portable recipient validation, without producer workspace imports."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import io
import stat
import zipfile

from exchange_contracts import (
    CAPSULE_SCHEMA, PORTABLE_REQUEST_SCHEMA, RESPONSE_CONTRACT_SCHEMA,
    MAX_CAPSULE_BYTES, MAX_EXPANDED_BYTES, InputError, fixed, json_bytes,
    parse_json, validate_portable_request, validate_response_contract,
)
from portable_capsule import (
    ZIP_NAMES, PAYLOAD_NAMES, MEMBER_LIMITS, REGULAR_FILE_ATTRIBUTES,
    README_BYTES, build_task_exchange_capsule, byte_identity, capsule_manifest_data,
)


_SCHEMAS = dict(zip(ZIP_NAMES, (PORTABLE_REQUEST_SCHEMA, RESPONSE_CONTRACT_SCHEMA, None, CAPSULE_SCHEMA)))


def _read_members(capsule_bytes: bytes) -> dict[str, bytes]:
    if type(capsule_bytes) is not bytes or not 0 < len(capsule_bytes) <= MAX_CAPSULE_BYTES:
        raise InputError("task_exchange_exact_bounded_capsule_bytes_required")
    try:
        with zipfile.ZipFile(io.BytesIO(capsule_bytes), "r", allowZip64=False) as archive:
            infos = archive.infolist()
            if archive.comment or tuple(info.filename for info in infos) != ZIP_NAMES:
                raise InputError("task_exchange_exact_four_ordered_members_required")
            if len({info.filename for info in infos}) != len(ZIP_NAMES):
                raise InputError("task_exchange_duplicate_capsule_member")
            expanded = 0
            for info, name in zip(infos, ZIP_NAMES):
                if (info.orig_filename != name or info.filename != name
                        or "\x00" in info.orig_filename or info.is_dir()
                        or info.extra or info.comment or info.flag_bits != 0
                        or info.compress_type != zipfile.ZIP_STORED
                        or info.create_system != 3
                        or info.date_time != (1980, 1, 1, 0, 0, 0)
                        or info.external_attr != REGULAR_FILE_ATTRIBUTES
                        or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG
                        or info.external_attr & 0x10):
                    raise InputError("task_exchange_capsule_member_metadata_rejected")
                if (type(info.file_size) is not int or type(info.compress_size) is not int
                        or not 0 < info.file_size <= MEMBER_LIMITS[name]
                        or info.file_size != info.compress_size):
                    raise InputError("task_exchange_capsule_member_size_rejected")
                expanded += info.file_size
            if expanded > MAX_EXPANDED_BYTES:
                raise InputError("task_exchange_capsule_expanded_limit_rejected")
            members = {}
            for info, name in zip(infos, ZIP_NAMES):
                with archive.open(info, "r") as stream:
                    raw = stream.read(MEMBER_LIMITS[name] + 1)
                if not 0 < len(raw) <= MEMBER_LIMITS[name] or len(raw) != info.file_size:
                    raise InputError("task_exchange_capsule_actual_member_size_rejected")
                members[name] = raw
            return members
    except InputError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, OSError, UnicodeError,
            ValueError, RuntimeError, TypeError, KeyError, IndexError,
            RecursionError, EOFError, OverflowError, NotImplementedError):
        raise InputError("task_exchange_capsule_archive_rejected") from None


def _validated_memory(capsule_bytes: bytes) -> tuple[dict, dict, list]:
    members = _read_members(capsule_bytes)
    envelope = validate_portable_request(parse_json(members[ZIP_NAMES[0]], maximum=MEMBER_LIMITS[ZIP_NAMES[0]]))
    response_contract = validate_response_contract(parse_json(members[ZIP_NAMES[1]], maximum=MEMBER_LIMITS[ZIP_NAMES[1]]))
    if members[ZIP_NAMES[0]] != json_bytes(envelope, maximum=MEMBER_LIMITS[ZIP_NAMES[0]]):
        raise InputError("task_exchange_capsule_request_not_canonical")
    if members[ZIP_NAMES[1]] != json_bytes(response_contract, maximum=MEMBER_LIMITS[ZIP_NAMES[1]]):
        raise InputError("task_exchange_capsule_response_contract_not_canonical")
    if members["README.txt"] != README_BYTES:
        raise InputError("task_exchange_capsule_readme_mismatch")
    actual_manifest = parse_json(members[ZIP_NAMES[3]], maximum=MEMBER_LIMITS[ZIP_NAMES[3]])
    expected_manifest = capsule_manifest_data(envelope, response_contract,
                                              {name: members[name] for name in PAYLOAD_NAMES})
    fixed(actual_manifest, expected_manifest, "task_exchange_capsule_inner_manifest_mismatch")
    if members[ZIP_NAMES[3]] != json_bytes(expected_manifest, maximum=MEMBER_LIMITS[ZIP_NAMES[3]]):
        raise InputError("task_exchange_capsule_manifest_not_canonical")
    # The protocol permits one exact STORED representation. Comparing the
    # entire rebuilt archive also rejects alternate local headers, prefixes,
    # trailing bytes and ZIP64 metadata that a general ZIP parser can ignore.
    if capsule_bytes != build_task_exchange_capsule(envelope, response_contract):
        raise InputError("task_exchange_capsule_archive_not_canonical")
    artifacts = [{"name": name, **byte_identity(members[name]), "schema_version": _SCHEMAS[name]}
                 for name in ZIP_NAMES]
    return envelope, response_contract, artifacts


@dataclass(frozen=True, slots=True, repr=False)
class ValidatedPortableTaskRequest:
    """Exact immutable capsule bytes, never a producer or authorization token."""

    capsule_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_memory(self.capsule_bytes)


def inspect_task_exchange_capsule(capsule_bytes: bytes) -> ValidatedPortableTaskRequest:
    """Validate only the supplied in-memory capsule, opening no source paths."""
    return ValidatedPortableTaskRequest(capsule_bytes)


def read_portable_task_request(snapshot: ValidatedPortableTaskRequest) -> tuple[dict, dict, list]:
    if type(snapshot) is not ValidatedPortableTaskRequest:
        raise InputError("task_exchange_exact_validated_portable_request_required")
    envelope, response_contract, artifacts = _validated_memory(snapshot.capsule_bytes)
    return deepcopy(envelope), deepcopy(response_contract), deepcopy(artifacts)


__all__ = ("ValidatedPortableTaskRequest", "inspect_task_exchange_capsule", "read_portable_task_request")
