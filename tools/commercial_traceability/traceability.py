"""Closed immutable ledger for three distinct layers of offline evidence."""
from __future__ import annotations

from dataclasses import dataclass, field

from commercial_scope.scope_contracts import BUDGET_FIELDS, proposal_to_dict

from .assessment_reader import AssessmentBundle, validate_bundle
from .capability_mapping import CapabilityMapping, map_capabilities, mapping_to_dict
from .contracts import (
    ADAPTER_VERSION, DEMO_LABEL, SOURCE_ROLES, TRACEABILITY_CONTRACT, FileIdentity, InputError,
    file_identity_to_dict, json_bytes,
)
from .plan_reader import PlanBundle
from .source_binding import SourceBinding


COMPARISON_STATUSES = frozenset((
    "same_declared_value", "different_declared_value", "not_reported", "not_comparable",
))
MISSING_EVIDENCE = (
    "plan_assessment_execution_binding_not_established",
    "assessment_target_origin_not_reported", "assessment_run_identity_not_reported",
    "assessment_request_consumption_not_reported",
    "assessment_wall_time_consumption_not_reported",
    "assessment_budget_limits_not_reported", "native_producer_attestation_not_provided",
    "original_proposal_bytes_not_read", "plan_summary_payload_not_read",
    "assessment_html_payload_not_read", "native_binary_runtime_acceptance_not_performed",
    "real_authorization_not_provided", "human_review_not_performed",
    "data_handling_pending_decision",
)
HUMAN_REQUIREMENTS = (
    "scope_owner", "authorization", "data_handling", "human_expert_review",
    "producer_authenticity", "runtime_qualification", "customer_release_decision",
)
TRUST_LIMITATIONS = (
    "exact_capability_identity_overlap_is_not_execution_or_coverage",
    "assessment_complete_is_a_declared_artifact_status_not_plan_completion",
    "planned_limits_are_not_reported_consumption",
    "absence_of_observation_is_not_absence_of_vulnerability",
    "opaque_subject_reference_is_not_target_origin",
    "run_schema_is_a_contract_version_not_a_run_identifier",
    "fingerprints_are_reported_labels_not_producer_or_security_proof",
    "duplicate_fingerprints_remain_separate_source_positions",
    "assessment_to_mapping_file_binding_does_not_bind_plan_to_assessment",
    "manifest_checks_do_not_authenticate_a_producer_or_full_bundle",
    "native_source_pins_are_declared_phase20_metadata_not_current_binary_attestation",
    "original_proposal_and_unselected_summary_or_html_payloads_are_not_opened",
    "same_profile_origin_count_commit_or_folder_cannot_establish_same_run",
    "no_percentage_score_coverage_estimate_or_native_execution_configuration",
)
NOT_RUN = (
    "malformed_json", "duplicate_key", "hostile_unicode_or_encoding",
    "wrong_namespace", "modified_mapping_or_pointer", "missing_or_wrong_manifest",
    "unsupported_schema", "size_type_depth_or_node_limit_scenarios",
    "symlink_reparse_path_traversal", "filesystem_race_permission_or_crash",
    "repeat_run_determinism", "real_execution_binding",
    "real_producer_expert_organizational_or_customer_acceptance",
    "automatic_tests_runner_coverage", "native_cli_scanner_network_or_target_activity",
)
LINKAGE_EXPLANATION = (
    "Plan ve assessment arasında güvenilir bir yürütme/run bağı raporlanmıyor. "
    "Capability, profil, fingerprint veya dosya hash eşleşmesi bu bağı kurmaz. "
    "Phase17 dosya bağının tutarlı olması planın uygulandığını göstermez."
)


@dataclass(frozen=True, slots=True)
class ScopeComparison:
    field: str
    planned_value: str | int | None
    assessment_reported_value: str | int | None
    status: str
    explanation: str


@dataclass(frozen=True, slots=True)
class CatalogNamespaceBoundary:
    capability_id: str
    namespace: str
    kind: str
    selected_in_plan: bool
    explanation: str
    status: str = field(default="unmappable", init=False)


@dataclass(frozen=True, slots=True)
class TraceabilityLedger:
    plan: PlanBundle
    assessment: AssessmentBundle
    source_binding: SourceBinding
    source_files: tuple[FileIdentity, ...]
    capability_mappings: tuple[CapabilityMapping, ...]
    catalog_namespace_boundaries: tuple[CatalogNamespaceBoundary, ...]
    comparisons: tuple[ScopeComparison, ...]
    blockers: tuple[str, ...]
    schema_version: str = field(default=TRACEABILITY_CONTRACT, init=False)
    adapter_version: str = field(default=ADAPTER_VERSION, init=False)
    demo_label: str = field(default=DEMO_LABEL, init=False)
    execution_binding: str = field(default="not_established", init=False)
    demo_only: bool = field(default=True, init=False)
    plan_execution_verified: bool = field(default=False, init=False)
    scope_fulfillment_verified: bool = field(default=False, init=False)
    authorization_verified: bool = field(default=False, init=False)
    human_review_verified: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    release_authorized: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    production_ready: bool = field(default=False, init=False)


def _namespace_boundaries(plan: PlanBundle) -> tuple[CatalogNamespaceBoundary, ...]:
    return tuple(CatalogNamespaceBoundary(
        entry.capability_id, entry.namespace, entry.kind,
        entry.capability_id in plan.proposal.requested_capabilities,
        "Bu katalog kaydı assessment-item namespace'inde değildir ve bir observation karşılığına dönüştürülmez. "
        "Seçilmemiş kayıt, istenmiş kontrol veya başarısız tarama olarak sayılmaz.",
    ) for entry in plan.catalog_entries if entry.namespace != "assessment_item")


def _comparisons(plan: PlanBundle, assessment: AssessmentBundle) -> tuple[ScopeComparison, ...]:
    proposal = plan.proposal
    actual = assessment.assessment
    rows = [ScopeComparison(
        "assessment_profile", proposal.assessment_profile, actual.profile,
        "same_declared_value" if proposal.assessment_profile == actual.profile else "different_declared_value",
        "Bu yalnız bildirilen profil değerlerinin karşılaştırmasıdır; aynı run, hedef veya kapsam ilişkisini kurmaz.",
    )]
    for key, value in (
        ("exact_origin", proposal.scope.origin), ("root_url", proposal.scope.root_url),
        ("requested_methods", ", ".join(proposal.scope.requested_methods)),
    ):
        rows.append(ScopeComparison(
            key, value, None, "not_reported",
            "Assessment JSON bu kapsam alanını raporlamaz; opaque subject etiketi hedef veya origin yerine kullanılamaz.",
        ))
    for key in BUDGET_FIELDS:
        rows.append(ScopeComparison(
            key, getattr(proposal.budgets, key), None, "not_reported",
            "Planlanan limit gösterilir; assessment bu limiti veya gerçekleşmiş tüketimini bildirmez. Limit/tüketim eşitliği varsayılmaz.",
        ))
    for key in ("max_canonical_url_bytes", "request_consumption", "wall_time_consumption_ms", "run_identity", "incomplete_work_details"):
        rows.append(ScopeComparison(
            key, None, None, "not_reported",
            "Bu bilgi karşılaştırılan belgelerde raporlanmıyor; native default, run_schema veya plan kimliğinden türetilmez.",
        ))
    rows.extend((
        ScopeComparison(
            "assessment_subject_count", None, actual.subject_count, "not_comparable",
            "Bu raporlanan subject sayısıdır; planlanan üst sınırın veya request tüketiminin doğrulanması değildir.",
        ),
        ScopeComparison(
            "assessment_status", None, actual.status, "not_comparable",
            "Complete kaynak artefact'ın beyan ettiği durumdur; Phase20 planının tamamlandığını göstermez.",
        ),
    ))
    return tuple(rows)


def _bind_inputs(plan: PlanBundle, assessment: AssessmentBundle,
                 binding: SourceBinding) -> tuple[FileIdentity, ...]:
    if (type(plan) is not PlanBundle or type(assessment) is not AssessmentBundle
            or type(binding) is not SourceBinding):
        raise InputError("traceability_invalid_ledger_input")
    validate_bundle(assessment)
    actual = assessment.assessment
    if (binding.source_assessment_sha256 != actual.sha256
            or binding.source_assessment_byte_length != actual.byte_length
            or binding.source_binding_status != "assessment_mapping_byte_and_metadata_consistent"
            or type(binding.fingerprint_reuse_reported) is not bool
            or binding.fingerprint_reuse_reported != (
                len({item.fingerprint for item in actual.items}) != actual.item_count)
            or len(binding.observations) != actual.item_count):
        raise InputError("traceability_assessment_binding_mismatch")
    for position, (link, item) in enumerate(zip(binding.observations, actual.items)):
        if (link.source_pointer != "/items/" + str(position)
                or link.native_fingerprint != item.fingerprint
                or link.capability_id != item.capability_id
                or link.native_disposition != item.disposition
                or link.subject_ref != item.subject_reference
                or link.evidence_ref_count != item.evidence_count):
            raise InputError("traceability_observation_binding_mismatch")
    sources = plan.source_files + assessment.source_files + binding.source_files
    if (type(sources) is not tuple or len(sources) != len(SOURCE_ROLES)
            or any(type(item) is not FileIdentity for item in sources)
            or tuple(item.role for item in sources) != SOURCE_ROLES):
        raise InputError("traceability_invalid_source_inventory")
    for item in sources:
        file_identity_to_dict(item)
    selected = {item.role: item for item in sources}
    check = assessment.manifest_check
    if (selected["assessment"].sha256 != actual.sha256
            or selected["assessment"].byte_length != actual.byte_length
            or check.status != "partial_json_entry_match"
            or selected["assessment_manifest"].sha256 != check.sha256
            or selected["assessment_manifest"].byte_length != check.byte_length
            or check.json_entry_matches is not True or check.summary_matches is not True
            or check.html_payload_read is not False or check.full_bundle_verified is not False
            or check.producer_verified is not False):
        raise InputError("traceability_assessment_manifest_binding_mismatch")
    return sources


def build_ledger(plan: PlanBundle, assessment: AssessmentBundle,
                 binding: SourceBinding) -> TraceabilityLedger:
    sources = _bind_inputs(plan, assessment, binding)
    rows = map_capabilities(plan.proposal.requested_capabilities,
                            plan.catalog_entries, assessment.assessment.items)
    blockers = tuple(dict.fromkeys((*plan.execution_blockers,
        "plan_assessment_execution_binding_not_established",
        "scope_fulfillment_not_verified", "authorization_not_verified",
        "human_review_not_verified", "producer_not_verified", "release_not_authorized")))
    return TraceabilityLedger(plan, assessment, binding, sources, rows,
                              _namespace_boundaries(plan),
                              _comparisons(plan, assessment), blockers)


def _check_ledger(ledger: TraceabilityLedger) -> None:
    if (type(ledger) is not TraceabilityLedger
            or ledger.schema_version != TRACEABILITY_CONTRACT
            or ledger.adapter_version != ADAPTER_VERSION
            or ledger.demo_label != DEMO_LABEL
            or ledger.execution_binding != "not_established" or ledger.demo_only is not True
            or any(getattr(ledger, flag) is not False for flag in (
                "plan_execution_verified", "scope_fulfillment_verified", "authorization_verified",
                "human_review_verified", "producer_verified", "release_authorized",
                "execution_authorized", "production_ready"))):
        raise InputError("traceability_invalid_ledger")
    sources = _bind_inputs(ledger.plan, ledger.assessment, ledger.source_binding)
    expected = build_ledger(ledger.plan, ledger.assessment, ledger.source_binding)
    if (ledger.source_files != sources or ledger.capability_mappings != expected.capability_mappings
            or ledger.catalog_namespace_boundaries != expected.catalog_namespace_boundaries
            or ledger.comparisons != expected.comparisons or ledger.blockers != expected.blockers):
        raise InputError("traceability_ledger_metadata_mismatch")


def ledger_to_dict(ledger: TraceabilityLedger) -> dict:
    """Serialize only explicit bounded fields; never embed a raw source document."""
    _check_ledger(ledger)
    plan, bundle, binding = ledger.plan, ledger.assessment, ledger.source_binding
    proposal = proposal_to_dict(plan.proposal)
    actual = bundle.assessment
    manifest = bundle.manifest_check
    result = {
        "schema_version": ledger.schema_version, "adapter_version": ledger.adapter_version,
        "demo_label": ledger.demo_label, "demo_only": True,
        "source_files": [file_identity_to_dict(item) for item in ledger.source_files],
        "plan_intent": {
            "plan_id": plan.plan_id, "proposal_id": plan.proposal.proposal_id,
            "profile": plan.proposal.assessment_profile, "scope": proposal["scope"],
            "requested_capabilities": list(plan.proposal.requested_capabilities),
            "budgets": proposal["budgets"], "technical_status": plan.technical_status,
            "precondition_result": plan.precondition_result,
            "authorization_status": plan.proposal.authorization_status,
            "data_handling_status": plan.proposal.data_handling_status,
            "declared_proposal": {"sha256": plan.declared_proposal_sha256,
                                  "byte_length": plan.declared_proposal_byte_length,
                                  "original_payload_read": False},
            "declared_native_source": {
                "commit": plan.native_commit,
                "files": [{"source_id": item.id, "path": item.path,
                           "sha256": item.sha256, "byte_length": item.byte_length}
                          for item in plan.native_files],
                "current_checkout_or_binary_verified": False,
            },
        },
        "assessment_reported": {
            "schema": actual.schema, "source_schema": actual.source_schema,
            "run_schema": actual.run_schema, "profile_schema": actual.profile_schema,
            "profile": actual.profile, "status": actual.status,
            "subject_count": actual.subject_count, "item_count": actual.item_count,
            "run_identity_status": "not_reported", "target_origin_status": "not_reported",
            "items": [{
                "source_pointer": "/items/" + str(item.index),
                "capability_id": item.capability_id, "namespace": "assessment_item",
                "fingerprint": item.fingerprint, "disposition": item.disposition,
                "claim_basis": item.claim_basis, "subject_reference": item.subject_reference,
                "evidence_reference_count": item.evidence_count,
            } for item in actual.items],
        },
        "capability_mappings": [mapping_to_dict(row) for row in ledger.capability_mappings],
        "catalog_namespace_boundaries": [{
            "capability_id": row.capability_id, "namespace": row.namespace,
            "kind": row.kind, "selected_in_plan": row.selected_in_plan,
            "status": row.status, "explanation": row.explanation,
        } for row in ledger.catalog_namespace_boundaries],
        "scope_budget_comparison": [{
            "field": row.field, "planned_value": row.planned_value,
            "assessment_reported_value": row.assessment_reported_value,
            "status": row.status, "explanation": row.explanation,
        } for row in ledger.comparisons],
        "source_binding": {
            "status": binding.source_binding_status,
            "source_assessment_sha256": binding.source_assessment_sha256,
            "source_assessment_byte_length": binding.source_assessment_byte_length,
            "fingerprint_reuse_reported": binding.fingerprint_reuse_reported,
            "observation_links": [{
                "observation_id": row.observation_id, "source_pointer": row.source_pointer,
                "native_fingerprint": row.native_fingerprint,
                "capability_id": row.capability_id, "native_disposition": row.native_disposition,
                "subject_ref": row.subject_ref, "evidence_ref_count": row.evidence_ref_count,
            } for row in binding.observations],
            "plan_manifest_validation_scope": plan.manifest_validation_scope,
            "unread_plan_summary": {"name": plan.unread_summary.name,
                                    "sha256": plan.unread_summary.sha256,
                                    "byte_length": plan.unread_summary.byte_length,
                                    "status": plan.unread_summary.status},
            "assessment_manifest_status": manifest.status,
            "assessment_json_entry_matches": manifest.json_entry_matches,
            "assessment_manifest_summary_matches": manifest.summary_matches,
            "assessment_html_payload_read": False, "assessment_full_bundle_verified": False,
            "intake_manifest_scope": "selected_handoff_and_mapping_payload_entries",
        },
        "execution_binding": "not_established",
        "execution_linkage_explanation": LINKAGE_EXPLANATION,
        "missing_evidence": list(MISSING_EVIDENCE),
        "human_requirements": [{"requirement": item, "status": "pending_decision"}
                               for item in HUMAN_REQUIREMENTS],
        "blockers": list(ledger.blockers), "trust_limitations": list(TRUST_LIMITATIONS),
        "not_run": list(NOT_RUN),
        "plan_execution_verified": False, "scope_fulfillment_verified": False,
        "authorization_verified": False, "human_review_verified": False,
        "producer_verified": False, "release_authorized": False,
        "execution_authorized": False, "production_ready": False,
    }
    # Also apply the preserved JSON output's graph/text/number/byte bounds.
    json_bytes(result)
    return result


__all__ = (
    "TraceabilityLedger", "ScopeComparison", "CatalogNamespaceBoundary",
    "COMPARISON_STATUSES", "MISSING_EVIDENCE",
    "HUMAN_REQUIREMENTS", "TRUST_LIMITATIONS", "NOT_RUN", "build_ledger", "ledger_to_dict",
)
