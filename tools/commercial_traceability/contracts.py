"""Bounded local metadata and immutable identities shared by Phase21 readers."""
from __future__ import annotations

from dataclasses import dataclass
import json
import re
from types import MappingProxyType

from commercial_handoff.input_loader import _depth_check, _tree_budget
from commercial_handoff.schema import InputError
from commercial_intake.assessment_reader import JsonFile, read_json_file
from commercial_review.review_contracts import (
    array, digest, enum_value, identifier, integer, json_bytes, literal,
    object_fields, text,
)


TRACEABILITY_CONTRACT = "termivar-assessment-traceability/v1"
ADAPTER_VERSION = "phase21-source-traceability/v1"
DEMO_LABEL = "DEMONSTRATION ONLY — PLAN AND ASSESSMENT EXECUTION LINK NOT ESTABLISHED"
MAX_PLAN_BYTES = 512 * 1024
MAX_ASSESSMENT_BYTES = 1024 * 1024
MAX_MAPPING_BYTES = 256 * 1024
MAX_PREFLIGHT_BYTES = 256 * 1024
MAX_CATALOG_BYTES = 256 * 1024
MAX_HANDOFF_BYTES = 256 * 1024
MAX_MANIFEST_BYTES = 64 * 1024
MAX_OUTPUT_BYTES = 256 * 1024
SOURCE_ROLES = (
    "plan", "preflight", "catalog", "plan_manifest", "assessment",
    "assessment_manifest", "source_mapping", "handoff_input", "intake_manifest",
)
ROLE_LIMITS = MappingProxyType({
    "plan": MAX_PLAN_BYTES, "preflight": MAX_PREFLIGHT_BYTES,
    "catalog": MAX_CATALOG_BYTES, "plan_manifest": MAX_MANIFEST_BYTES,
    "assessment": MAX_ASSESSMENT_BYTES, "assessment_manifest": MAX_MANIFEST_BYTES,
    "source_mapping": MAX_MAPPING_BYTES, "handoff_input": MAX_HANDOFF_BYTES,
    "intake_manifest": MAX_MANIFEST_BYTES,
})
FALSE_TRUST_FLAGS = (
    "plan_execution_verified", "scope_fulfillment_verified",
    "authorization_verified", "human_review_verified", "producer_verified",
    "release_authorized",
)


@dataclass(frozen=True, slots=True)
class FileIdentity:
    """Identity of one explicitly selected, actually read file; no authenticity."""
    role: str
    sha256: str
    byte_length: int
    schema_version: str


@dataclass(frozen=True, slots=True)
class UnopenedArtifact:
    """Manifest-declared entry; its content has not been read or authenticated."""
    name: str
    sha256: str
    byte_length: int
    status: str = "not_read"


def _schema(value: object) -> str:
    if (type(value) is not str or not 1 <= len(value) <= 128
            or re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", value) is None):
        raise InputError("traceability_invalid_schema_identity")
    return value


def read_metadata(raw_path: str, maximum: int) -> JsonFile:
    """Read one explicit local JSON; apply preserved aggregate graph bounds.

    The Phase17 file reader supplies strict UTF-8, duplicate/number rejection,
    raw byte ceilings and component/reparse identity guards. The unchanged
    Phase16 graph/depth budgets also cover keys and values. Parsed generic data
    remains local to readers, which return closed immutable projections.
    """
    integer(maximum, 1, MAX_ASSESSMENT_BYTES)
    loaded = read_json_file(raw_path, maximum=maximum)
    _tree_budget(loaded.data)
    try:
        canonical = json.dumps(loaded.data, ensure_ascii=False, sort_keys=True,
                               indent=2, allow_nan=False).encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise InputError("traceability_invalid_json_value") from None
    _depth_check(canonical.decode("utf-8", "strict"))
    return loaded


def file_identity(role: str, loaded: JsonFile, schema_version: str) -> FileIdentity:
    enum_value(role, SOURCE_ROLES)
    if type(loaded) is not JsonFile:
        raise InputError("traceability_invalid_file_identity")
    return FileIdentity(role, digest(loaded.sha256),
                        integer(loaded.byte_length, 1, ROLE_LIMITS[role]),
                        _schema(schema_version))


def file_identity_to_dict(identity: FileIdentity) -> dict:
    if type(identity) is not FileIdentity:
        raise InputError("traceability_invalid_file_identity")
    role = enum_value(identity.role, SOURCE_ROLES)
    return {"role": role, "sha256": digest(identity.sha256),
            "byte_length": integer(identity.byte_length, 1, ROLE_LIMITS[role]),
            "schema_version": _schema(identity.schema_version)}


def fixed_flags() -> dict:
    return {"demo_only": True, **{flag: False for flag in FALSE_TRUST_FLAGS}}


__all__ = (
    "InputError", "JsonFile", "FileIdentity", "UnopenedArtifact",
    "TRACEABILITY_CONTRACT", "ADAPTER_VERSION", "DEMO_LABEL", "SOURCE_ROLES",
    "ROLE_LIMITS", "FALSE_TRUST_FLAGS", "MAX_PLAN_BYTES", "MAX_ASSESSMENT_BYTES",
    "MAX_MAPPING_BYTES", "MAX_PREFLIGHT_BYTES", "MAX_CATALOG_BYTES",
    "MAX_HANDOFF_BYTES", "MAX_MANIFEST_BYTES", "MAX_OUTPUT_BYTES",
    "read_metadata", "file_identity", "file_identity_to_dict", "fixed_flags",
    "object_fields", "literal", "integer", "identifier", "digest",
    "enum_value", "array", "text", "json_bytes",
)
