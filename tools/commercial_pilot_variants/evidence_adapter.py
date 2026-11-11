"""Bind Phase25 metadata to the exact selected Phase24 records, never by name."""
from __future__ import annotations

from dataclasses import dataclass
import copy

from commercial_license_review.component_identity import build_subjects
from commercial_license_review.conflict_analysis import build_conflicts
from commercial_license_review.evidence_contracts import validate_documents
from commercial_license_review.evidence_manifest import manifest_data
from commercial_license_review.output_renderer import render_summary
from commercial_license_review.review_queue import build_queue
from .composition_adapter import EVIDENCE_SCHEMAS, ReadBudget, read_group
from .variant_contracts import InputError, json_bytes, validate_source_reference


@dataclass(frozen=True, slots=True)
class EvidenceContext:
    ledger: dict
    queue: dict
    conflicts: dict
    source_reference: dict


def load_evidence(scope: dict, paths: dict, composition, budget: ReadBudget) -> EvidenceContext:
    raw, docs = read_group(paths, scope["evidence_sources"], EVIDENCE_SCHEMAS, budget)
    ledger, queue, conflicts = (docs[key] for key in ("ledger", "queue", "conflicts"))
    validate_documents(ledger, queue, conflicts)
    if ledger["composition_reference"] != composition.reference:
        raise InputError("pilot_variant_cross_phase_source_identity_mismatch")
    expected_subjects = build_subjects(composition)
    if json_bytes(ledger["source_subjects"]) != json_bytes(expected_subjects):
        raise InputError("pilot_variant_cross_phase_subject_binding_mismatch")
    if json_bytes(conflicts) != json_bytes(build_conflicts(ledger)):
        raise InputError("pilot_variant_source_conflicts_projection_mismatch")
    if json_bytes(queue) != json_bytes(build_queue(ledger, conflicts)):
        raise InputError("pilot_variant_source_queue_projection_mismatch")
    if raw["summary"] != render_summary(ledger, queue, conflicts):
        raise InputError("pilot_variant_source_evidence_summary_mismatch")
    payloads = {"license-evidence-ledger.json": raw["ledger"], "review-queue.json": raw["queue"],
                "binding-conflicts.json": raw["conflicts"], "evidence-summary.md": raw["summary"]}
    if json_bytes(docs["manifest"]) != json_bytes(manifest_data(ledger, queue, conflicts, payloads)):
        raise InputError("pilot_variant_evidence_manifest_mismatch")
    source_reference = {"composition_candidate_reference": composition.reference["candidate_reference"],
                        "source_commits": copy.deepcopy(composition.reference["source_commits"]),
                        "composition_sources": copy.deepcopy(scope["composition_sources"]),
                        "evidence_sources": copy.deepcopy(scope["evidence_sources"])}
    return EvidenceContext(ledger, queue, conflicts, validate_source_reference(source_reference))
