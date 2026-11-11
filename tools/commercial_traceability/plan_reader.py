"""Read the existing Phase20 contract without inventing an execution link.

The fixed Phase20 catalog and preflight functions operate on declared metadata
only. No native source path, Git query, native evaluator or previous-phase
output generator is called by this reader.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import re

from commercial_scope import (
    DEMO_LABEL as PLAN_DEMO_LABEL, MAX_PROPOSAL_BYTES, PLAN_CONTRACT,
    PROPOSAL_CONTRACT,
)
from commercial_scope.capability_catalog import CATALOG_CONTRACT, build_catalog
from commercial_scope.plan_builder import (
    PLAN_ID_PREFIX, PLAN_ID_RECIPE, PROVENANCE_LIMITATIONS,
)
from commercial_scope.scope_contracts import ScopeProposal, validate_proposal
from commercial_scope.scope_validator import preflight_to_dict, validate_scope
from commercial_scope.source_manifest import (
    PINNED_COMMIT, SOURCE_FILES, SourceFile, SourceSnapshot, source_snapshot_to_dict,
)

from .contracts import (
    FileIdentity, InputError, MAX_CATALOG_BYTES, MAX_MANIFEST_BYTES,
    MAX_PLAN_BYTES, MAX_PREFLIGHT_BYTES, UnopenedArtifact, array, digest,
    file_identity, identifier, integer, json_bytes, literal, object_fields,
    read_metadata,
)


PLAN_MANIFEST_CONTRACT = "termivar-assessment-scope-output-manifest/v1"
MANIFEST_VALIDATION_SCOPE = "plan_preflight_catalog_entries_only"
PLAN_FIELDS = frozenset((
    "assessment_profile", "authorization_status", "authorization_verified",
    "budgets", "compatibility", "data_handling_status",
    "declared_review_requirements", "demo_label", "demo_only",
    "execution_authorized", "execution_blockers", "human_decisions",
    "limitations", "mode", "native_runtime_configuration", "plan_id",
    "plan_identity_recipe", "precondition_result", "production_ready",
    "proposed_scope", "provenance_limitations", "requested_capabilities",
    "schema_version", "scope_of_result", "source_catalog", "source_gaps",
    "source_proposal", "source_termivar",
))
MANIFEST_FIELDS = frozenset((
    "authorization_verified", "completion_marker", "demo_label", "demo_only",
    "execution_authorized", "files", "integrity_limit", "manifest_self_excluded",
    "native_source", "output_files", "production_ready", "proposal", "schema_version",
))
PLAN_OUTPUT_NAMES = (
    "capability-catalog.json", "scope-preflight.json",
    "assessment-plan-proposal.json", "assessment-plan-summary.md",
)
PLAN_MANIFEST_INTEGRITY_LIMIT = (
    "SHA256 binds selected bytes only; it authenticates neither producer, source history, authorization nor runtime success."
)
PLAN_MANIFEST_COMPLETION_MARKER = (
    "Published last. Compare every payload to its size and digest; a manifest alone is not authentication or runtime acceptance."
)


@dataclass(frozen=True, slots=True)
class CatalogCapability:
    capability_id: str
    namespace: str
    kind: str
    evidence_class: str
    planner_support: str


@dataclass(frozen=True, slots=True)
class PlanBundle:
    proposal: ScopeProposal
    plan_id: str
    native_commit: str
    catalog_entries: tuple[CatalogCapability, ...]
    technical_status: str
    precondition_result: str
    execution_blockers: tuple[str, ...]
    source_files: tuple[FileIdentity, ...]
    native_files: tuple[SourceFile, ...]
    declared_proposal_sha256: str
    declared_proposal_byte_length: int
    unread_summary: UnopenedArtifact
    manifest_validation_scope: str


def _same(value: object, expected: object, code: str) -> None:
    """Canonical equality also distinguishes JSON booleans from integer 0/1."""
    if json_bytes(value) != json_bytes(expected):
        raise InputError(code)


def _plan_flags(row: dict) -> None:
    literal(row["demo_label"], PLAN_DEMO_LABEL)
    literal(row["demo_only"], True)
    for name in ("execution_authorized", "authorization_verified", "production_ready"):
        literal(row[name], False)


def _proposal_from_plan(plan: dict) -> tuple[ScopeProposal, dict]:
    source = object_fields(plan["source_proposal"], (
        "schema_version", "proposal_id", "sha256", "byte_length",
    ))
    literal(source["schema_version"], PROPOSAL_CONTRACT)
    identifier(source["proposal_id"])
    digest(source["sha256"])
    integer(source["byte_length"], 1, MAX_PROPOSAL_BYTES)
    proposal = validate_proposal({
        "schema_version": source["schema_version"], "mode": plan["mode"],
        "proposal_id": source["proposal_id"],
        "assessment_profile": plan["assessment_profile"],
        "scope": plan["proposed_scope"],
        "requested_capabilities": plan["requested_capabilities"],
        "budgets": plan["budgets"],
        "authorization_status": plan["authorization_status"],
        "data_handling_status": plan["data_handling_status"],
        "review_requirements": plan["declared_review_requirements"],
    })
    return proposal, source


def _native_plan_identity(snapshot: SourceSnapshot) -> dict:
    return {"commit": snapshot.commit,
            "files": [{"source_id": item.id, "path": item.path,
                       "sha256": item.sha256, "byte_length": item.byte_length}
                      for item in snapshot.files]}


def _validate_plan(plan: dict, catalog: dict, catalog_sha256: str,
                   preflight: dict, snapshot: SourceSnapshot) -> tuple[ScopeProposal, dict]:
    object_fields(plan, PLAN_FIELDS)
    literal(plan["schema_version"], PLAN_CONTRACT)
    literal(plan["mode"], "demo")
    _plan_flags(plan)
    literal(plan["native_runtime_configuration"], False)
    literal(plan["scope_of_result"], "offline_declarative_source_compatibility_only")
    literal(plan["plan_identity_recipe"], PLAN_ID_RECIPE)
    _same(plan["provenance_limitations"], list(PROVENANCE_LIMITATIONS),
          "traceability_invalid_plan_provenance")
    proposal, source = _proposal_from_plan(plan)
    _same(plan["source_catalog"], {
        "schema_version": CATALOG_CONTRACT,
        "sha256": catalog_sha256, "source_commit": PINNED_COMMIT,
    }, "traceability_plan_catalog_identity_mismatch")
    _same(plan["source_termivar"], _native_plan_identity(snapshot),
          "source_version_mismatch")
    # This reuses the Phase20 metadata preflight, not a native policy/scanner
    # evaluator. It does not regenerate any previous-phase artifact on disk.
    expected = preflight_to_dict(validate_scope(proposal, catalog))
    _same(preflight, expected, "traceability_plan_preflight_mismatch")
    _same(plan["compatibility"], {
        "technical_status": expected["technical_status"], "checks": expected["checks"],
    }, "traceability_invalid_plan_compatibility")
    _same(plan["limitations"], expected["limitations"],
          "traceability_invalid_plan_limitations")
    _same(plan["execution_blockers"], expected["execution_blockers"],
          "traceability_invalid_plan_blockers")
    literal(plan["precondition_result"], expected["overall_status"])
    _same(plan["human_decisions"], [{
        "requirement": requirement,
        "declared_in_proposal": requirement in proposal.review_requirements,
        "status": "pending_authorization",
    } for requirement in expected["human_requirements"]],
          "traceability_invalid_plan_human_requirements")
    _same(plan["source_gaps"], [{
        "check_id": row["check_id"], "subject": row["subject"], "codes": row["codes"],
    } for row in expected["checks"] if row["status"] == "insufficient_source_evidence"],
          "traceability_invalid_plan_source_gaps")
    if (type(plan["plan_id"]) is not str
            or re.fullmatch(re.escape(PLAN_ID_PREFIX) + r"[a-f0-9]{64}", plan["plan_id"]) is None):
        raise InputError("traceability_invalid_plan_id")
    body = {key: value for key, value in plan.items() if key != "plan_id"}
    if plan["plan_id"] != PLAN_ID_PREFIX + hashlib.sha256(json_bytes(body)).hexdigest():
        raise InputError("traceability_plan_content_identity_mismatch")
    return proposal, source


def _validate_manifest(manifest: dict, source: dict, snapshot: SourceSnapshot,
                       selected: dict[str, object]) -> UnopenedArtifact:
    row = object_fields(manifest, MANIFEST_FIELDS)
    literal(row["schema_version"], PLAN_MANIFEST_CONTRACT)
    _plan_flags(row)
    literal(row["manifest_self_excluded"], True)
    literal(row["integrity_limit"], PLAN_MANIFEST_INTEGRITY_LIMIT)
    literal(row["completion_marker"], PLAN_MANIFEST_COMPLETION_MARKER)
    _same(row["output_files"], [*PLAN_OUTPUT_NAMES, "manifest.json"],
          "traceability_invalid_plan_output_inventory")
    _same(row["native_source"], source_snapshot_to_dict(snapshot),
          "source_version_mismatch")
    _same(row["proposal"], {
        "schema_version": source["schema_version"], "proposal_id": source["proposal_id"],
        "bytes": source["byte_length"], "sha256": source["sha256"],
    }, "traceability_plan_manifest_proposal_mismatch")
    entries = array(row["files"], len(PLAN_OUTPUT_NAMES), len(PLAN_OUTPUT_NAMES))
    summary = None
    for expected_name, entry in zip(PLAN_OUTPUT_NAMES, entries):
        entry = object_fields(entry, ("name", "bytes", "sha256"))
        literal(entry["name"], expected_name)
        maximum = 128 * 1024 if expected_name.endswith(".md") else 256 * 1024
        byte_length = integer(entry["bytes"], 1, maximum)
        sha256 = digest(entry["sha256"])
        if expected_name in selected:
            actual = selected[expected_name]
            if actual.byte_length != byte_length or actual.sha256 != sha256:
                raise InputError("traceability_plan_manifest_entry_mismatch")
        else:
            # Only the exact fixed summary metadata is retained; its declared
            # name never becomes a path, and its bytes are not opened.
            summary = UnopenedArtifact(expected_name, sha256, byte_length)
    if summary is None:
        raise InputError("traceability_plan_summary_metadata_missing")
    return summary


def load_plan_bundle(plan_path: str, preflight_path: str,
                     catalog_path: str, plan_manifest_path: str) -> PlanBundle:
    """Read exactly four explicit files and retain a closed immutable model.

    The original proposal and the summary are not read. Declared native pins
    are compared to the protected Phase20 metadata implementation only; current
    native source files, a binary, producer and legal authority are not checked.
    """
    plan_file = read_metadata(plan_path, MAX_PLAN_BYTES)
    preflight_file = read_metadata(preflight_path, MAX_PREFLIGHT_BYTES)
    catalog_file = read_metadata(catalog_path, MAX_CATALOG_BYTES)
    manifest_file = read_metadata(plan_manifest_path, MAX_MANIFEST_BYTES)
    snapshot = SourceSnapshot(PINNED_COMMIT, SOURCE_FILES)
    expected_catalog = build_catalog(snapshot)
    _same(catalog_file.data, expected_catalog, "source_version_mismatch")
    proposal, source = _validate_plan(plan_file.data, catalog_file.data,
                                      catalog_file.sha256, preflight_file.data, snapshot)
    summary = _validate_manifest(manifest_file.data, source, snapshot, {
        "assessment-plan-proposal.json": plan_file,
        "scope-preflight.json": preflight_file,
        "capability-catalog.json": catalog_file,
    })
    return PlanBundle(
        proposal, plan_file.data["plan_id"], snapshot.commit,
        tuple(CatalogCapability(row["capability_id"], row["namespace"], row["kind"],
                                row["evidence_class"], row["planner_support"])
              for row in expected_catalog["entries"]),
        preflight_file.data["technical_status"],
        preflight_file.data["overall_status"],
        tuple(preflight_file.data["execution_blockers"]),
        (file_identity("plan", plan_file, PLAN_CONTRACT),
         file_identity("preflight", preflight_file, preflight_file.data["schema_version"]),
         file_identity("catalog", catalog_file, CATALOG_CONTRACT),
         file_identity("plan_manifest", manifest_file, PLAN_MANIFEST_CONTRACT)),
        snapshot.files, source["sha256"], source["byte_length"], summary,
        MANIFEST_VALIDATION_SCOPE,
    )


__all__ = (
    "CatalogCapability", "PlanBundle", "PLAN_MANIFEST_CONTRACT",
    "MANIFEST_VALIDATION_SCOPE", "load_plan_bundle",
)
