"""Closed immutable metadata shared by the assembler and source-free ZIP reader."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re
from types import MappingProxyType

from commercial_handoff.input_loader import (
    _depth_check, _integer, _pairs, _reject_number, _tree_budget,
)
from commercial_handoff.schema import InputError
from commercial_review.review_contracts import (
    digest, enum_value, integer, json_bytes, literal, object_fields,
)


CASE_CONTRACT = "termivar-offline-case-bundle/v1"
CASE_MAP_CONTRACT = "termivar-offline-case-map/v1"
SOURCE_INDEX_CONTRACT = "termivar-offline-case-source-index/v1"
DEMO_LABEL = "DEMONSTRATION ONLY — NO REAL SYSTEM ASSESSED OR CLIENT DELIVERY AUTHORIZED"
MAX_JSON_BYTES = 256 * 1024
MAX_ARTIFACTS = 20
MAX_TOTAL_INPUT_BYTES = 16 * 1024 * 1024
FALSE_FLAGS = (
    "plan_execution_verified", "scope_fulfillment_verified",
    "authorization_verified", "human_review_verified", "producer_verified",
    "release_authorized", "execution_authorized", "production_ready",
)
ROLE_CONTRACTS = MappingProxyType({
    "plan": "termivar-assessment-plan-proposal/v1",
    "preflight": "termivar-assessment-scope-preflight/v1",
    "catalog": "termivar-assessment-capability-catalog/v1",
    "plan_manifest": "termivar-assessment-scope-output-manifest/v1",
    "assessment": "venom-rendered-assessment/v1",
    "assessment_manifest": "termivar-report-bundle/v1",
    "handoff_input": "termivar-handoff-draft/v1",
    "source_mapping": "termivar-assessment-intake/v1",
    "intake_manifest": "termivar-assessment-intake-manifest/v1",
    "review_packet": "termivar-analyst-review-packet/v1",
    "review_packet_manifest": "termivar-analyst-review-packet-manifest/v1",
    "overlay_template": "termivar-analyst-decision-overlay/v1",
    "decision_overlay": "termivar-analyst-decision-overlay/v1",
    "reconciled_handoff": "termivar-handoff-draft/v1",
    "reconciliation_manifest": "termivar-analyst-reconciliation-manifest/v1",
    "traceability_ledger": "termivar-assessment-traceability/v1",
    "traceability_manifest": "termivar-assessment-traceability-manifest/v1",
    "handoff_internal_markdown": "text/markdown",
    "handoff_client_markdown": "text/markdown",
    "handoff_manifest": "termivar-handoff-output-manifest/v1",
})
SOURCE_ROLES = tuple(ROLE_CONTRACTS)
ROLE_LIMITS = MappingProxyType({
    role: (1024 * 1024 if role == "assessment" else
           64 * 1024 if role.endswith("manifest") else
           128 * 1024 if role.endswith("markdown") else MAX_JSON_BYTES)
    for role in SOURCE_ROLES
})
RELATIONSHIP_DEFINITIONS = MappingProxyType({
    "plan_files": ("file_content_binding", ("plan", "preflight", "catalog", "plan_manifest")),
    "assessment_file": ("file_content_binding", ("assessment", "assessment_manifest")),
    "intake_files": ("file_content_binding", ("handoff_input", "source_mapping", "intake_manifest")),
    "observation_binding": ("assessment_observation_binding", ("assessment", "source_mapping", "handoff_input", "intake_manifest")),
    "review_packet_files": ("file_content_binding", ("review_packet", "review_packet_manifest", "overlay_template")),
    "review_binding": ("review_packet_binding", ("review_packet", "decision_overlay", "handoff_input")),
    "reconciliation_files": ("file_content_binding", ("reconciled_handoff", "reconciliation_manifest")),
    "reconciliation_binding": ("review_packet_binding", ("review_packet", "review_packet_manifest", "decision_overlay", "handoff_input", "reconciled_handoff", "reconciliation_manifest")),
    "traceability_files": ("file_content_binding", ("plan", "preflight", "catalog", "plan_manifest", "assessment", "assessment_manifest", "handoff_input", "source_mapping", "intake_manifest", "traceability_ledger", "traceability_manifest")),
    "handoff_files": ("file_content_binding", ("handoff_internal_markdown", "handoff_client_markdown", "handoff_manifest", "reconciled_handoff")),
    "plan_execution": ("plan_to_assessment_execution_binding", ("plan", "assessment")),
})
RELATIONSHIP_IDS = tuple(RELATIONSHIP_DEFINITIONS)
RELATIONSHIP_KINDS = frozenset(row[0] for row in RELATIONSHIP_DEFINITIONS.values())
ARTIFACT_STATUSES = frozenset(("artifact_present", "artifact_missing", "content_consistent", "content_inconsistent"))
RELATIONSHIP_STATUSES = frozenset(("content_consistent", "content_inconsistent", "artifact_missing", "not_established"))
STAGE_IDS = (
    "scope_planning", "assessment_reported", "observation_intake",
    "analyst_review", "client_handoff", "traceability",
)
STAGE_STATUSES = frozenset((
    "artifact_present", "artifact_missing", "content_consistent", "content_inconsistent",
    "relationship_not_established", "human_review_pending", "delivery_not_authorized",
))
BLOCKER_CODES = (
    "authorization_missing", "execution_binding_missing", "producer_not_verified",
    "human_review_pending", "data_handling_pending", "delivery_not_authorized",
    "runtime_acceptance_not_performed",
)
SUPPORTED_CAPABILITIES = frozenset((
    "web.passive.referrer-policy.missing@1",
    "web.passive.x-content-type-options.missing@1",
    "web.passive.permissions-policy.missing@1",
    "web.passive.csp.missing@1",
))
TRUST_LIMITATIONS = (
    "metadata_projection_not_full_evidence_archive",
    "original_sources_not_in_portable_bundle",
    "original_source_relationships_cannot_be_reverified_without_sources",
    "internal_content_integrity_is_not_producer_authentication",
    "observation_binding_is_not_plan_execution_binding",
    "empty_overlay_is_not_expert_review",
    "draft_handoff_is_not_client_delivery",
    "hashes_and_fingerprints_are_not_signatures_or_security_verdicts",
    "no_automatic_redaction_or_secret_detection_guarantee",
)
NOT_RUN = (
    "malformed_duplicate_or_hostile_json", "modified_mapping_pointer_or_manifest",
    "unsupported_schema", "zip_bomb_compression_abuse_or_path_traversal",
    "symlink_reparse_or_filesystem_race", "permission_partial_write_crash_or_power_loss",
    "repeat_run_determinism", "real_producer_expert_or_organizational_authentication",
    "real_assessment_execution_or_client_delivery", "automatic_tests_runner_or_coverage",
)


@dataclass(frozen=True, slots=True)
class ArtifactIdentity:
    role: str
    contract: str
    status: str
    sha256: str | None
    byte_length: int | None
    validation_scope: str


@dataclass(frozen=True, slots=True)
class CaseObservation:
    observation_id: str
    source_pointer: str
    assessment_sha256: str
    fingerprint: str
    capability_id: str
    disposition: str
    review_status: str
    scope_status: str
    client_inclusion: str


@dataclass(frozen=True, slots=True)
class Relationship:
    relationship_id: str
    kind: str
    status: str
    source_roles: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkflowFacts:
    plan_precondition: str
    assessment_status: str
    observation_count: int
    unreviewed_count: int
    unknown_scope_count: int
    pending_inclusion_count: int
    overlay_decision_count: int
    reconciled_observation_count: int
    handoff_input_binding: str
    handoff_manifest_scope: str


@dataclass(frozen=True, slots=True)
class CaseEvidence:
    artifacts: tuple[ArtifactIdentity, ...]
    relationships: tuple[Relationship, ...]
    observations: tuple[CaseObservation, ...]
    facts: WorkflowFacts


@dataclass(frozen=True, slots=True)
class StageStatus:
    stage: str
    status: str
    source_roles: tuple[str, ...]
    limitations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class CaseProjection:
    case_reference: str
    artifacts: tuple[ArtifactIdentity, ...]
    relationships: tuple[Relationship, ...]
    observations: tuple[CaseObservation, ...]
    facts: WorkflowFacts
    stages: tuple[StageStatus, ...]
    blockers: tuple[str, ...]
    schema_version: str = field(default=CASE_CONTRACT, init=False)
    demo_label: str = field(default=DEMO_LABEL, init=False)
    demo_only: bool = field(default=True, init=False)
    execution_binding: str = field(default="not_established", init=False)
    plan_execution_verified: bool = field(default=False, init=False)
    scope_fulfillment_verified: bool = field(default=False, init=False)
    authorization_verified: bool = field(default=False, init=False)
    human_review_verified: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    release_authorized: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    production_ready: bool = field(default=False, init=False)


def parse_json_bytes(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    """Parse bounded UTF-8 bytes without paths, imports or source access."""
    integer(maximum, 1, 1024 * 1024)
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise InputError("case_json_byte_limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("case_invalid_utf8") from None
    if text.startswith("\ufeff"):
        raise InputError("case_utf8_bom_not_supported")
    _depth_check(text)
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                           parse_float=_reject_number, parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError):
        raise InputError("case_invalid_json") from None
    _tree_budget(value)
    return value


def case_reference(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"DEMO-[A-Z0-9_-]{1,59}", value) is None:
        raise InputError("case_invalid_demo_reference")
    return value


def code(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[a-z][a-z0-9_:-]{0,95}", value) is None:
        raise InputError("case_invalid_metadata_code")
    return value


def _array(value: object, maximum: int, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise InputError("case_invalid_array")
    return value


def _codes(value: object) -> tuple[str, ...]:
    rows = tuple(code(item) for item in _array(value, 32))
    if len(set(rows)) != len(rows):
        raise InputError("case_duplicate_metadata_code")
    return rows


def _roles(value: object) -> tuple[str, ...]:
    rows = tuple(enum_value(item, SOURCE_ROLES) for item in _array(value, MAX_ARTIFACTS, 1))
    if len(set(rows)) != len(rows):
        raise InputError("case_duplicate_source_role")
    return rows


def _artifact(value: object) -> ArtifactIdentity:
    row = object_fields(value, ("role", "contract", "status", "sha256", "byte_length", "validation_scope"))
    role = enum_value(row["role"], SOURCE_ROLES)
    literal(row["contract"], ROLE_CONTRACTS[role])
    status = enum_value(row["status"], ARTIFACT_STATUSES)
    if status == "artifact_missing":
        literal(row["sha256"], None)
        literal(row["byte_length"], None)
    else:
        digest(row["sha256"])
        integer(row["byte_length"], 1, ROLE_LIMITS[role])
    return ArtifactIdentity(role, row["contract"], status, row["sha256"], row["byte_length"], code(row["validation_scope"]))


def _relationship(value: object) -> Relationship:
    row = object_fields(value, ("relationship_id", "kind", "status", "source_roles", "limitations"))
    name = enum_value(row["relationship_id"], RELATIONSHIP_IDS)
    kind, roles = RELATIONSHIP_DEFINITIONS[name]
    literal(row["kind"], kind)
    status = enum_value(row["status"], RELATIONSHIP_STATUSES)
    if name == "plan_execution":
        literal(status, "not_established")
    actual_roles = _roles(row["source_roles"])
    if actual_roles != roles:
        raise InputError("case_relationship_source_roles_mismatch")
    return Relationship(name, kind, status, actual_roles, _codes(row["limitations"]))


def _observation(value: object, position: int) -> CaseObservation:
    fields = ("observation_id", "source_pointer", "assessment_sha256", "fingerprint", "capability_id", "disposition", "review_status", "scope_status", "client_inclusion")
    row = object_fields(value, fields)
    literal(row["observation_id"], f"OBS-{position + 1:02d}")
    literal(row["source_pointer"], "/items/" + str(position))
    digest(row["assessment_sha256"])
    if type(row["fingerprint"]) is not str or re.fullmatch(r"sha256:[a-f0-9]{64}", row["fingerprint"]) is None:
        raise InputError("case_invalid_fingerprint")
    enum_value(row["capability_id"], SUPPORTED_CAPABILITIES)
    for name, expected in (("disposition", "informational"), ("review_status", "unreviewed"),
                           ("scope_status", "unknown"), ("client_inclusion", "pending_decision")):
        literal(row[name], expected)
    return CaseObservation(*(row[name] for name in fields))


def _facts(value: object) -> WorkflowFacts:
    fields = ("plan_precondition", "assessment_status", "observation_count", "unreviewed_count", "unknown_scope_count", "pending_inclusion_count", "overlay_decision_count", "reconciled_observation_count", "handoff_input_binding", "handoff_manifest_scope")
    row = object_fields(value, fields)
    enum_value(row["plan_precondition"], ("pending_authorization", "not_reported"))
    enum_value(row["assessment_status"], ("complete", "not_reported"))
    for name in fields[2:8]:
        integer(row[name], 0, 256)
    literal(row["overlay_decision_count"], 0)
    enum_value(row["handoff_input_binding"], ("same_input_bytes_only", "not_established", "not_reported"))
    enum_value(row["handoff_manifest_scope"], ("selected_markdown_entries_only", "not_reported"))
    return WorkflowFacts(*(row[name] for name in fields))


def _stage(value: object) -> StageStatus:
    row = object_fields(value, ("stage", "status", "source_roles", "limitations"))
    return StageStatus(enum_value(row["stage"], STAGE_IDS), enum_value(row["status"], STAGE_STATUSES),
                       _roles(row["source_roles"]), _codes(row["limitations"]))


def _artifact_dict(item: ArtifactIdentity) -> dict:
    return {"role": item.role, "contract": item.contract, "status": item.status,
            "sha256": item.sha256, "byte_length": item.byte_length, "validation_scope": item.validation_scope}


def _relationship_dict(item: Relationship) -> dict:
    return {"relationship_id": item.relationship_id, "kind": item.kind, "status": item.status,
            "source_roles": list(item.source_roles), "limitations": list(item.limitations)}


def _projection_dict(projection: CaseProjection) -> dict:
    if type(projection) is not CaseProjection or type(projection.facts) is not WorkflowFacts:
        raise InputError("case_invalid_projection")
    facts = projection.facts
    return {
        "schema_version": projection.schema_version, "case_reference": projection.case_reference,
        "demo_label": projection.demo_label, "demo_only": projection.demo_only,
        "execution_binding": projection.execution_binding,
        "artifacts": [_artifact_dict(item) for item in projection.artifacts],
        "relationships": [_relationship_dict(item) for item in projection.relationships],
        "observations": [{"observation_id": item.observation_id, "source_pointer": item.source_pointer,
                          "assessment_sha256": item.assessment_sha256, "fingerprint": item.fingerprint,
                          "capability_id": item.capability_id, "disposition": item.disposition,
                          "review_status": item.review_status, "scope_status": item.scope_status,
                          "client_inclusion": item.client_inclusion} for item in projection.observations],
        "workflow_facts": {name: getattr(facts, name) for name in WorkflowFacts.__dataclass_fields__},
        "stages": [{"stage": item.stage, "status": item.status, "source_roles": list(item.source_roles),
                    "limitations": list(item.limitations)} for item in projection.stages],
        "blockers": list(projection.blockers),
        "trust_limitations": list(TRUST_LIMITATIONS), "not_run": list(NOT_RUN),
        **{name: getattr(projection, name) for name in FALSE_FLAGS},
    }


def validate_projection(value: object) -> CaseProjection:
    fields = ("schema_version", "case_reference", "demo_label", "demo_only", "execution_binding",
              "artifacts", "relationships", "observations", "workflow_facts", "stages", "blockers",
              "trust_limitations", "not_run", *FALSE_FLAGS)
    row = object_fields(value, fields)
    literal(row["schema_version"], CASE_CONTRACT)
    reference = case_reference(row["case_reference"])
    literal(row["demo_label"], DEMO_LABEL)
    literal(row["demo_only"], True)
    literal(row["execution_binding"], "not_established")
    for name in FALSE_FLAGS:
        literal(row[name], False)
    artifacts = tuple(_artifact(item) for item in _array(row["artifacts"], MAX_ARTIFACTS, MAX_ARTIFACTS))
    if tuple(item.role for item in artifacts) != SOURCE_ROLES:
        raise InputError("case_invalid_artifact_inventory")
    relationships = tuple(_relationship(item) for item in _array(row["relationships"], len(RELATIONSHIP_IDS), len(RELATIONSHIP_IDS)))
    if tuple(item.relationship_id for item in relationships) != RELATIONSHIP_IDS:
        raise InputError("case_invalid_relationship_inventory")
    by_role = {item.role: item for item in artifacts}
    for relationship in relationships:
        if relationship.relationship_id == "plan_execution":
            continue
        referred = tuple(by_role[role] for role in relationship.source_roles)
        missing = any(item.status == "artifact_missing" for item in referred)
        inconsistent = any(item.status == "content_inconsistent" for item in referred)
        if (missing and relationship.status != "artifact_missing"
                or relationship.status == "content_consistent" and (missing or inconsistent)):
            raise InputError("case_relationship_artifact_status_mismatch")
    observations = tuple(_observation(item, i) for i, item in enumerate(_array(row["observations"], 256)))
    actual_assessment = next(item for item in artifacts if item.role == "assessment")
    if any(item.assessment_sha256 != actual_assessment.sha256 for item in observations):
        raise InputError("case_observation_assessment_identity_mismatch")
    facts = _facts(row["workflow_facts"])
    if (facts.observation_count != len(observations)
            or any(value != len(observations) for value in (facts.unreviewed_count, facts.unknown_scope_count, facts.pending_inclusion_count))
            or facts.reconciled_observation_count not in (0, len(observations))):
        raise InputError("case_observation_workflow_count_mismatch")
    stages = tuple(_stage(item) for item in _array(row["stages"], len(STAGE_IDS), len(STAGE_IDS)))
    if tuple(item.stage for item in stages) != STAGE_IDS:
        raise InputError("case_invalid_stage_inventory")
    if tuple(_array(row["blockers"], len(BLOCKER_CODES), len(BLOCKER_CODES))) != BLOCKER_CODES:
        raise InputError("case_required_blockers_changed")
    if (tuple(_array(row["trust_limitations"], len(TRUST_LIMITATIONS), len(TRUST_LIMITATIONS))) != TRUST_LIMITATIONS
            or tuple(_array(row["not_run"], len(NOT_RUN), len(NOT_RUN))) != NOT_RUN):
        raise InputError("case_trust_limitations_changed")
    return CaseProjection(reference, artifacts, relationships, observations, facts, stages, BLOCKER_CODES)


def projection_to_dict(projection: CaseProjection) -> dict:
    raw = _projection_dict(projection)
    if validate_projection(raw) != projection:
        raise InputError("case_projection_not_closed_immutable_model")
    json_bytes(raw)
    return raw


def source_index_dict(projection: CaseProjection) -> dict:
    row = projection_to_dict(projection)
    return {"schema_version": SOURCE_INDEX_CONTRACT, "case_reference": projection.case_reference,
            "demo_label": DEMO_LABEL, "demo_only": True, "execution_binding": "not_established",
            "artifacts": row["artifacts"], "relationships": row["relationships"],
            **{name: False for name in FALSE_FLAGS}}


def validate_source_index(value: object, projection: CaseProjection) -> None:
    if json_bytes(value) != json_bytes(source_index_dict(projection)):
        raise InputError("case_source_index_projection_mismatch")
