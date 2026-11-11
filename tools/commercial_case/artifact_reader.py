"""Read selected existing artifacts and return metadata-only case evidence.

All paths originate in the explicit case map. Existing readers are reused;
no old CLI, native runtime, source discovery, HTML or network operation occurs.
"""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_handoff.review_rules import build_models
from commercial_handoff.schema import validate as validate_handoff
from commercial_intake.assessment_reader import JsonFile
from commercial_review.decision_binding import bind_decisions
from commercial_review.decision_overlay import validate_overlay
from commercial_review.handoff_reconciler import reconcile_handoff
from commercial_review.manifest import validate_packet_manifest
from commercial_review.packet_builder import build_packet, load_prepare_sources
from commercial_review.review_contracts import (
    array, digest, integer, json_bytes, literal, object_fields, packet_to_dict,
    handoff_to_dict, validate_packet,
)
from commercial_traceability.assessment_reader import load_assessment_bundle
from commercial_traceability.contracts import (
    ADAPTER_VERSION as TRACE_ADAPTER, DEMO_LABEL as TRACE_LABEL,
    TRACEABILITY_CONTRACT, file_identity_to_dict, read_metadata,
)
from commercial_traceability.plan_reader import load_plan_bundle
from commercial_traceability.source_binding import bind_source_mapping
from commercial_traceability.traceability import build_ledger, ledger_to_dict

from .case_contracts import (
    ArtifactIdentity, CaseObservation, InputError, ROLE_CONTRACTS, ROLE_LIMITS,
    WorkflowFacts,
)
from .case_map import CaseMap


MAX_TOTAL_READ_BYTES = 16 * 1024 * 1024
MARKDOWN_ROLES = frozenset(("handoff_internal_markdown", "handoff_client_markdown"))
FALSE_FLAGS = (
    "plan_execution_verified", "scope_fulfillment_verified", "authorization_verified",
    "human_review_verified", "producer_verified", "release_authorized",
    "execution_authorized", "production_ready",
)
REVIEW_PAYLOAD_NAMES = (
    "review-packet.json", "decision-overlay.template.json", "review-worksheet.md",
)
RECONCILED_PAYLOAD_NAMES = ("handoff-input.json", "review-reconciliation.md")
HANDOFF_PAYLOAD_NAMES = (
    "internal-review-summary.md", "client-handoff-draft.md", "client-handoff-draft.html",
)
REVIEW_MANIFEST_LIMIT = (
    "Hashes identify selected input and generated payload bytes only. They do not "
    "authenticate a source, producer, reviewer, decision, authorized scope or release. "
    "Reconciliation compares only the explicitly supplied packet entry; worksheet "
    "and overlay-template entries are not opened or verified. An overlay is read "
    "only when separately and explicitly supplied."
)
DELIVERY_BLOCKERS = (
    "demo_only_not_for_delivery", "human_review_not_verified", "producer_not_verified",
    "authorization_not_verified", "data_handling_pending_decision", "release_not_authorized",
)


@dataclass(frozen=True, slots=True)
class CapturedArtifact:
    role: str
    sha256: str
    byte_length: int
    document: JsonFile | None


@dataclass(frozen=True, slots=True)
class ValidatedArtifacts:
    """Only approved metadata escapes the reader; no targets or local paths."""
    artifacts: tuple[ArtifactIdentity, ...]
    observations: tuple[CaseObservation, ...]
    facts: WorkflowFacts
    read_budget_charged: int


class _ReadBudget:
    def __init__(self, initial: int):
        self.used = 0
        self.charge(initial)

    def charge(self, byte_length: int) -> None:
        if type(byte_length) is not int or byte_length < 0 or self.used + byte_length > MAX_TOTAL_READ_BYTES:
            raise InputError("case_source_read_budget_exceeded")
        self.used += byte_length


def _same(value: object, expected: object, code: str) -> None:
    # Canonical JSON equality distinguishes false/true from numeric 0/1.
    if json_bytes(value) != json_bytes(expected):
        raise InputError(code)


def _workspace(workspace_root: str | Path) -> Path:
    root = Path(workspace_root).absolute()
    if any(part == ".." for part in root.parts):
        raise InputError("case_invalid_workspace_root")
    check_existing_path(root, directory=True)
    if root != Path.cwd():
        # Preserved helpers resolve explicit relative paths against CWD. Do not
        # silently change global process state or reinterpret selected paths.
        raise InputError("case_workspace_root_must_match_cwd")
    return root


def _capture(role: str, raw_path: str, budget: _ReadBudget) -> CapturedArtifact:
    path = explicit_relative_path(raw_path)
    info = check_existing_path(path, directory=False)
    # The extra byte used by bounded readers to detect an oversized input is
    # included in the remaining read allowance as well.
    maximum = min(ROLE_LIMITS[role], MAX_TOTAL_READ_BYTES - budget.used - 1)
    if not 0 < info.st_size <= maximum:
        raise InputError("case_artifact_size_limit")
    budget.charge(info.st_size)
    if role not in MARKDOWN_ROLES:
        document = read_metadata(raw_path, maximum)
        if document.byte_length != info.st_size:
            raise InputError("case_artifact_read_identity_changed")
        return CapturedArtifact(role, document.sha256, document.byte_length, document)
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (info.st_dev, info.st_ino)
                or getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("case_artifact_read_identity_changed")
        raw = stream.read(maximum + 1)
    if len(raw) != info.st_size or not 0 < len(raw) <= maximum:
        raise InputError("case_artifact_read_identity_changed")
    raw.decode("utf-8", "strict")
    return CapturedArtifact(role, hashlib.sha256(raw).hexdigest(), len(raw), None)


def _json(captured: dict[str, CapturedArtifact], role: str) -> JsonFile:
    document = captured[role].document
    if type(document) is not JsonFile:
        raise InputError("case_json_artifact_required")
    return document


def _identity(captured: dict[str, CapturedArtifact], role: str) -> dict:
    selected = captured[role]
    return {"sha256": selected.sha256, "byte_length": selected.byte_length}


def _rereads(budget: _ReadBudget, captured: dict[str, CapturedArtifact],
             roles: tuple[str, ...], repetitions: int = 1) -> None:
    # Reserve the preserved helpers' raw read ceilings before invoking them,
    # not merely the selected file's earlier size. The Phase18 helper reads its
    # intake manifest through a 256KiB generic reader. Reserve that wider cap.
    # Every returned identity is compared with the initially captured bytes.
    limits = {**ROLE_LIMITS, "plan": 512 * 1024, "intake_manifest": 256 * 1024}
    budget.charge(sum(limits[role] + 1 for role in roles) * repetitions)


def _check_identities(captured: dict[str, CapturedArtifact], identities) -> None:
    for identity in identities:
        actual = captured[identity.role]
        if actual.sha256 != identity.sha256 or actual.byte_length != identity.byte_length:
            raise InputError("case_helper_read_identity_changed")


def _entries(value: object, names: tuple[str, ...],
             selected: dict[str, str], captured: dict[str, CapturedArtifact],
             maximum: int = 256 * 1024,
             entry_limits: dict[str, int] | None = None) -> list[dict]:
    rows = array(value, len(names), len(names))
    result = []
    seen = set()
    for row in rows:
        row = object_fields(row, ("name", "bytes", "sha256"))
        name = row["name"]
        if type(name) is not str or name not in names or name in seen:
            raise InputError("case_invalid_manifest_inventory")
        seen.add(name)
        ceiling = entry_limits.get(name, maximum) if entry_limits else maximum
        size = integer(row["bytes"], 1, ceiling)
        sha256 = digest(row["sha256"])
        if name in selected:
            actual = captured[selected[name]]
            if actual.byte_length != size or actual.sha256 != sha256:
                raise InputError("case_manifest_payload_mismatch")
        result.append({"name": name, "bytes": size, "sha256": sha256})
    if seen != set(names):
        raise InputError("case_invalid_manifest_inventory")
    return result


def _validate_reconciliation_manifest(captured, assessment, packet) -> None:
    data = _json(captured, "reconciliation_manifest").data
    names = RECONCILED_PAYLOAD_NAMES
    rows = _entries(data.get("files") if type(data) is dict else None,
                    names, {"handoff-input.json": "reconciled_handoff"}, captured)
    expected = {
        "schema_version": "termivar-analyst-reconciliation-manifest/v1",
        "inputs": {key: _identity(captured, role) for key, role in (
            ("review_packet", "review_packet"), ("packet_manifest", "review_packet_manifest"),
            ("handoff_input", "handoff_input"), ("overlay", "decision_overlay"),
        )},
        "source_assessment_sha256": assessment.sha256,
        "source_observation_count": len(packet.observations),
        "output_files": [*names, "reconciliation-manifest.json"], "files": rows,
        "manifest_self_excluded": True, "demo_only": True,
        "demo_label": "DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED",
        "human_review_verified": False, "producer_verified": False,
        "release_authorized": False, "full_bundle_verified": False,
        "validation_scope": "generated_payload_byte_inventory_only",
        "delivery_blockers": list(DELIVERY_BLOCKERS), "integrity_limit": REVIEW_MANIFEST_LIMIT,
    }
    _same(data, expected, "case_reconciliation_manifest_mismatch")


def _validate_traceability_manifest(captured, source_files) -> None:
    data = _json(captured, "traceability_manifest").data
    names = ("traceability-ledger.json", "traceability-summary.md")
    rows = _entries(data.get("files") if type(data) is dict else None, names,
                    {"traceability-ledger.json": "traceability_ledger"}, captured,
                    entry_limits={"traceability-summary.md": 128 * 1024})
    expected = {
        "schema_version": "termivar-assessment-traceability-manifest/v1",
        "adapter_version": TRACE_ADAPTER, "ledger_contract": TRACEABILITY_CONTRACT,
        "sources": [file_identity_to_dict(item) for item in source_files],
        "files": rows, "output_files": [*names, "manifest.json"],
        "manifest_self_excluded": True, "execution_binding": "not_established",
        "demo_label": TRACE_LABEL, "demo_only": True,
        **{flag: False for flag in FALSE_FLAGS},
        "plan_manifest_validation_scope": "plan_preflight_catalog_entries_only; summary_payload_not_read",
        "assessment_manifest_validation_scope": "selected_json_entry_and_summary_only; html_payload_not_read",
        "phase17_manifest_validation_scope": "explicit_mapping_and_handoff_payload_bytes_only",
        "integrity_limit": "Hashes and pointers bind selected bytes and metadata only. They authenticate neither producer, authorized scope, execution, finding accuracy nor review.",
        "completion_marker": "Published last. Compare payload byte sizes and hashes; a manifest alone proves neither complete publication nor execution linkage.",
    }
    _same(data, expected, "case_traceability_manifest_mismatch")


def _validate_handoff_manifest(captured, reconciled_document) -> None:
    data = _json(captured, "handoff_manifest").data
    rows = _entries(data.get("files") if type(data) is dict else None,
                    HANDOFF_PAYLOAD_NAMES, {
                        "internal-review-summary.md": "handoff_internal_markdown",
                        "client-handoff-draft.md": "handoff_client_markdown",
                    }, captured, maximum=4 * 1024 * 1024)
    internal, _client = build_models(reconciled_document)
    original = captured["reconciled_handoff"]
    expected = {
        "schema_version": "termivar-handoff-output-manifest/v1",
        "tool_contract": "termivar-handoff-draft/v1",
        "input_sha256": original.sha256, "input_byte_length": original.byte_length,
        "files": rows, "demo_only": True, "release_authorized": False,
        "human_review_verified": False,
        "delivery_blockers": list(internal.delivery_blockers),
        "source_provenance_limitation": "Input metadata is an unverified assertion. Referenced source files were not opened; no native verifier, signature or source authentication was performed.",
        "integrity_limit": "SHA256 identifies these bytes only; it is not customer approval, a signature, a finding verdict or a certificate.",
        "completion_marker": "manifest.json is published last; its presence alone is not authentication. Check the declared file bytes before treating the set as complete.",
        "manifest_self_excluded": True,
    }
    _same(data, expected, "case_handoff_manifest_mismatch")


def load_case_artifacts(case_map: CaseMap, workspace_root: str | Path = ".") -> ValidatedArtifacts:
    """Read a complete demo map; any missing or inconsistent required role fails.

    Only source hashes, finite relationship metadata, observation identities and
    workflow facts are returned. Raw input dictionaries and Markdown are local.
    """
    _workspace(workspace_root)
    if type(case_map) is not CaseMap:
        raise InputError("case_invalid_map_model")
    selections = {item.role: item for item in case_map.artifact_roles}
    if len(selections) != 20 or set(selections) != set(ROLE_CONTRACTS):
        raise InputError("case_invalid_artifact_inventory")
    budget = _ReadBudget(case_map.byte_length)
    captured = {}
    paths = {}
    for role in ROLE_CONTRACTS:
        selected = selections[role]
        if selected.status != "artifact_present" or selected.path is None:
            raise InputError("case_required_artifact_missing")
        if selected.expected_contract != ROLE_CONTRACTS[role]:
            raise InputError("case_artifact_contract_mismatch")
        paths[role] = selected.path
        captured[role] = _capture(role, selected.path, budget)

    plan_roles = ("plan", "preflight", "catalog", "plan_manifest")
    _rereads(budget, captured, plan_roles)
    plan = load_plan_bundle(*(paths[role] for role in plan_roles))
    _check_identities(captured, plan.source_files)
    _rereads(budget, captured, ("assessment", "assessment_manifest"), 2)
    assessment = load_assessment_bundle(paths["assessment"], paths["assessment_manifest"])
    _check_identities(captured, assessment.source_files)
    intake_roles = ("source_mapping", "handoff_input", "intake_manifest")
    _rereads(budget, captured, intake_roles, 2)
    binding = bind_source_mapping(assessment, *(paths[role] for role in intake_roles))
    _check_identities(captured, binding.source_files)

    _rereads(budget, captured, intake_roles)
    prepared = load_prepare_sources(paths["handoff_input"], paths["source_mapping"], paths["intake_manifest"])
    for role in ("handoff_input", "source_mapping", "intake_manifest"):
        selected = captured[role]
        actual = getattr(prepared.phase17_inputs, role)
        if selected.sha256 != actual.sha256 or selected.byte_length != actual.byte_length:
            raise InputError("case_review_source_identity_changed")
    packet_file = _json(captured, "review_packet")
    packet = validate_packet(packet_file.data)
    _same(packet_to_dict(packet), packet_to_dict(build_packet(prepared)),
          "case_review_packet_source_mismatch")
    packet_manifest = _json(captured, "review_packet_manifest")
    validate_packet_manifest(packet_manifest, packet_file)
    _entries(packet_manifest.data["files"], REVIEW_PAYLOAD_NAMES, {
        "review-packet.json": "review_packet", "decision-overlay.template.json": "overlay_template",
    }, captured)
    template = validate_overlay(_json(captured, "overlay_template").data)
    overlay = validate_overlay(_json(captured, "decision_overlay").data)
    if template.decisions or overlay.decisions:
        raise InputError("case_nonempty_review_not_supported")
    for item in (template, overlay):
        if (item.review_packet_digest != packet_file.sha256
                or item.source_assessment_digest != assessment.assessment.sha256):
            raise InputError("case_overlay_source_mismatch")
        bind_decisions(packet, prepared.handoff, item, packet_digest=packet_file.sha256)

    reconciled = reconcile_handoff(packet, prepared.handoff, overlay, packet_digest=packet_file.sha256)
    selected_reconciled = validate_handoff(_json(captured, "reconciled_handoff").data)
    _same(handoff_to_dict(selected_reconciled), handoff_to_dict(reconciled.document),
          "case_reconciled_handoff_mismatch")
    _validate_reconciliation_manifest(captured, assessment.assessment, packet)

    expected_ledger = ledger_to_dict(build_ledger(plan, assessment, binding))
    _same(_json(captured, "traceability_ledger").data, expected_ledger,
          "case_traceability_ledger_mismatch")
    _validate_traceability_manifest(captured, plan.source_files + assessment.source_files + binding.source_files)
    _validate_handoff_manifest(captured, selected_reconciled)

    observations = tuple(CaseObservation(
        item.observation_id, item.source_json_pointer, item.source_assessment_sha256,
        item.fingerprint, item.capability_id, item.source_disposition,
        item.review_status, item.scope_status, item.client_inclusion,
    ) for item in packet.observations)
    facts = WorkflowFacts(
        plan.precondition_result, assessment.assessment.status, len(observations),
        sum(item.review_status == "unreviewed" for item in observations),
        sum(item.scope_status == "unknown" for item in observations),
        sum(item.client_inclusion == "pending_decision" for item in observations),
        len(overlay.decisions), len(selected_reconciled.observations),
        "same_input_bytes_only", "selected_markdown_entries_only",
    )
    artifacts = tuple(ArtifactIdentity(
        role, ROLE_CONTRACTS[role], "artifact_present", captured[role].sha256,
        captured[role].byte_length,
        "selected_markdown_file_bytes_only" if role in MARKDOWN_ROLES else
        "manifest_metadata_with_selected_entries" if role.endswith("manifest") else
        "closed_contract_and_bound_file_bytes",
    ) for role in ROLE_CONTRACTS)
    return ValidatedArtifacts(artifacts, observations, facts, budget.used)


__all__ = ("ValidatedArtifacts", "MAX_TOTAL_READ_BYTES", "load_case_artifacts")
