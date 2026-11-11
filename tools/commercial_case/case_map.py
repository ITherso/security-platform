"""Read the finite explicit demo map; never discover sources from artifacts."""
from __future__ import annotations

from dataclasses import dataclass, field
import os
from pathlib import Path
from types import MappingProxyType

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_traceability.contracts import read_metadata

from .case_contracts import (
    CASE_MAP_CONTRACT, MAX_ARTIFACTS, MAX_TOTAL_INPUT_BYTES, RELATIONSHIP_DEFINITIONS,
    RELATIONSHIP_IDS, ROLE_CONTRACTS, ROLE_LIMITS, SOURCE_ROLES, InputError,
    case_reference, digest, enum_value, integer, literal, object_fields,
)


MAX_CASE_MAP_BYTES = 64 * 1024
ROLE_MANIFESTS = MappingProxyType({
    "plan": "plan_manifest", "preflight": "plan_manifest", "catalog": "plan_manifest",
    "plan_manifest": None, "assessment": "assessment_manifest", "assessment_manifest": None,
    "handoff_input": "intake_manifest", "source_mapping": "intake_manifest", "intake_manifest": None,
    "review_packet": "review_packet_manifest", "review_packet_manifest": None,
    "overlay_template": "review_packet_manifest", "decision_overlay": None,
    "reconciled_handoff": "reconciliation_manifest", "reconciliation_manifest": None,
    "traceability_ledger": "traceability_manifest", "traceability_manifest": None,
    "handoff_internal_markdown": "handoff_manifest", "handoff_client_markdown": "handoff_manifest",
    "handoff_manifest": None,
})
ROLE_RELATIONSHIPS = MappingProxyType({
    "plan": "plan_files", "preflight": "plan_files", "catalog": "plan_files", "plan_manifest": "plan_files",
    "assessment": "assessment_file", "assessment_manifest": "assessment_file",
    "handoff_input": "intake_files", "source_mapping": "intake_files", "intake_manifest": "intake_files",
    "review_packet": "review_packet_files", "review_packet_manifest": "review_packet_files",
    "overlay_template": "review_packet_files", "decision_overlay": "review_binding",
    "reconciled_handoff": "reconciliation_files", "reconciliation_manifest": "reconciliation_files",
    "traceability_ledger": "traceability_files", "traceability_manifest": "traceability_files",
    "handoff_internal_markdown": "handoff_files", "handoff_client_markdown": "handoff_files",
    "handoff_manifest": "handoff_files",
})


@dataclass(frozen=True, slots=True)
class ArtifactSelection:
    role: str
    path: str | None
    expected_contract: str
    status: str
    source_manifest: str | None
    relationship_id: str


@dataclass(frozen=True, slots=True)
class SourceConstraints:
    max_artifacts: int
    max_total_input_bytes: int
    allow_symlinks: bool
    demo_only: bool


@dataclass(frozen=True, slots=True)
class ExpectedRelationship:
    relationship_id: str
    kind: str
    source_roles: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaseMap:
    case_reference: str
    artifact_roles: tuple[ArtifactSelection, ...]
    source_constraints: SourceConstraints
    expected_relationships: tuple[ExpectedRelationship, ...]
    sha256: str
    byte_length: int
    schema_version: str = field(default=CASE_MAP_CONTRACT, init=False)
    mode: str = field(default="demo", init=False)


def workspace_root_path(raw: str | Path = ".") -> Path:
    """Keep this version inside the explicitly selected current workspace."""
    value = os.fspath(raw)
    cwd = Path.cwd()
    if value != ".":
        candidate = Path(value)
        if (not candidate.is_absolute() or ".." in candidate.parts
                or candidate != cwd):
            raise InputError("case_workspace_root_must_be_current_directory")
    check_existing_path(cwd, directory=True)
    return cwd


def selected_path(selection: ArtifactSelection, workspace_root: str | Path = ".") -> Path:
    workspace_root_path(workspace_root)
    if (type(selection) is not ArtifactSelection or selection.status != "artifact_present"
            or type(selection.path) is not str):
        raise InputError("case_artifact_not_selected")
    return explicit_relative_path(selection.path)


def _selection(value: object) -> ArtifactSelection:
    row = object_fields(value, ("role", "path", "expected_contract", "status", "source_manifest", "relationship_id"))
    role = enum_value(row["role"], SOURCE_ROLES)
    literal(row["expected_contract"], ROLE_CONTRACTS[role])
    literal(row["source_manifest"], ROLE_MANIFESTS[role])
    literal(row["relationship_id"], ROLE_RELATIONSHIPS[role])
    status = enum_value(row["status"], ("artifact_present", "artifact_missing"))
    if status == "artifact_missing":
        literal(row["path"], None)
    else:
        path = explicit_relative_path(row["path"])
        info = check_existing_path(path, directory=False)
        if not 0 < info.st_size <= ROLE_LIMITS[role]:
            raise InputError("case_artifact_size_limit")
        required_suffix = ".md" if ROLE_CONTRACTS[role] == "text/markdown" else ".json"
        if path.suffix.lower() != required_suffix:
            raise InputError("case_artifact_file_type_mismatch")
    return ArtifactSelection(role, row["path"], row["expected_contract"], status,
                             row["source_manifest"], row["relationship_id"])


def validate_case_map(value: object, sha256: str, byte_length: int,
                      workspace_root: str | Path = ".") -> CaseMap:
    workspace_root_path(workspace_root)
    row = object_fields(value, ("schema_version", "mode", "case_reference", "artifact_roles", "source_constraints", "expected_relationships"))
    literal(row["schema_version"], CASE_MAP_CONTRACT)
    literal(row["mode"], "demo")
    reference = case_reference(row["case_reference"])
    constraints = object_fields(row["source_constraints"], ("max_artifacts", "max_total_input_bytes", "allow_symlinks", "demo_only"))
    literal(constraints["max_artifacts"], MAX_ARTIFACTS)
    literal(constraints["max_total_input_bytes"], MAX_TOTAL_INPUT_BYTES)
    literal(constraints["allow_symlinks"], False)
    literal(constraints["demo_only"], True)
    if type(row["artifact_roles"]) is not list or len(row["artifact_roles"]) != MAX_ARTIFACTS:
        raise InputError("case_invalid_map_inventory")
    selections = tuple(_selection(item) for item in row["artifact_roles"])
    if tuple(item.role for item in selections) != SOURCE_ROLES:
        raise InputError("case_map_role_inventory_mismatch")
    total_bytes = sum(check_existing_path(selected_path(item, workspace_root), directory=False).st_size
                      for item in selections if item.status == "artifact_present")
    if total_bytes > MAX_TOTAL_INPUT_BYTES:
        raise InputError("case_total_input_size_limit")
    raw_relationships = row["expected_relationships"]
    if type(raw_relationships) is not list or len(raw_relationships) != len(RELATIONSHIP_IDS):
        raise InputError("case_map_relationship_inventory_mismatch")
    relationships = []
    for expected_id, value in zip(RELATIONSHIP_IDS, raw_relationships):
        item = object_fields(value, ("relationship_id", "kind", "source_roles"))
        kind, roles = RELATIONSHIP_DEFINITIONS[expected_id]
        literal(item["relationship_id"], expected_id)
        literal(item["kind"], kind)
        if type(item["source_roles"]) is not list or tuple(item["source_roles"]) != roles:
            raise InputError("case_map_relationship_source_roles_mismatch")
        relationships.append(ExpectedRelationship(expected_id, kind, roles))
    # The caller provides measured metadata from the actual explicit map reader.
    digest(sha256)
    integer(byte_length, 1, MAX_CASE_MAP_BYTES)
    return CaseMap(reference, selections, SourceConstraints(MAX_ARTIFACTS, MAX_TOTAL_INPUT_BYTES, False, True),
                   tuple(relationships), sha256, byte_length)


def load_case_map(raw_path: str, workspace_root: str | Path = ".") -> CaseMap:
    workspace_root_path(workspace_root)
    selected = read_metadata(raw_path, MAX_CASE_MAP_BYTES)
    return validate_case_map(selected.data, selected.sha256, selected.byte_length, workspace_root)
