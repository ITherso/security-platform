# Client handoff draft — Termivar-supported assessment

This blank template is a **Client Handoff**, not a copy of the internal ledger. Include only explanations with a recorded `client_inclusion: include_with_limits` decision and an agreed sharing scope. Do not automatically copy notes or evidence from `pending_decision` or `exclude_with_reason` records. Do not insert credentials, tokens, cookies, raw HTTP, example payloads, unnecessary target details or private filesystem paths. Review explanations for sensitive content as well. This document does not provide access control or a secure sharing system.

The template is not an assessment result, delivery permission or evidence of completed expert review. Unfilled fields remain `not_provided` / `pending_decision`. `demo_only` is a separate marker; add **Demonstration only — No real system assessed.** to a demo copy. Do not invent people, dates, signatures or customer acceptance.

## 1. Assessment identity and scope

| Field | Value / reference suitable for sharing |
| --- | --- |
| case_id / handoff_document_ref / document_revision | not_provided / not_provided / not_provided |
| demo_only | pending_decision |
| customer_organization_ref | not_provided |
| assessment_purpose | not_provided |
| authorized_scope_summary / authorization_record_ref | not_provided / not_provided |
| exclusions / third_party_boundaries | not_provided / not_provided |
| operating_window | not_provided |

A scope description or source reference does not establish authorization by itself. Include precise target or identity details only when necessary and approved for sharing.

## 2. Method and assessment limits

| Field | Value |
| --- | --- |
| selected_source_or_binary_identity_ref | not_provided — separate historical generation from this review |
| actual_profile / selected_capabilities | not_provided / not_provided |
| permitted_actions / excluded_methods | not_provided / not_provided |
| approved_request_budget / approved_time_budget | not_provided / not_provided |
| actual_usage_record_ref / methodology_limits | not_provided / not_provided |

Source defaults are not accepted scope limits or measured usage. Budgets are not analyst effort estimates or guarantees of complete application coverage. Do not count unused or unsupported areas as included.

## 3. Completed and incomplete work

| Work / source reference | Actual source completion state | Bounded work completed | Missing or inaccessible area and its effect |
| --- | --- | --- | --- |
| not_provided | not_provided | not_provided | not_provided |

A complete assessment does not establish exhaustive coverage or a secure system. Show incomplete/failed diagnostics and unavailable item projections separately; an unavailable projection is not zero findings. Do not bind a pre-authored fixture or independent comparison to the same assessment run.

## 4. Expert-reviewed results, if any

Repeat this table only for records actually reviewed and approved for sharing as `include_with_limits`. If none exist, write `not_provided — no completed expert review results are presented`; do not promote automated observations to verified vulnerabilities.

| Field | Information selected for the client |
| --- | --- |
| handoff_item_ref / case_id | not_provided / not_provided |
| source_artifact_ref / observation_ref | not_provided / not_provided — the same source binding as section 6 |
| source_disposition / source_claim_basis | not_provided / not_provided — unchanged |
| source_severity / source_confidence_ppm | not_provided / not_provided — native null is unassigned; confidence is not accuracy |
| review_status / decision_record_ref | unreviewed / not_provided — do not copy internal notes |
| client_inclusion | pending_decision |
| approved_client_explanation / explicit_limits | not_provided / not_provided |

The human review_status vocabulary is `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery`. These are not native Termivar dispositions. `reviewed_for_delivery` does not establish independent vulnerability, impact or remediation verification, or overall delivery approval. `NeedsReview` is not a verified vulnerability; `KnowledgeOnly` is not a clean result or a new disposition.

## 5. Areas awaiting review or remaining inconclusive

| Reference suitable for sharing | Pending or inconclusive matter | Evidence or scope limitation | Required human decision or separate activity |
| --- | --- | --- | --- |
| not_provided | not_provided | not_provided | not_provided |

Do not automatically copy every pending or excluded internal note. Select an appropriate client explanation separately, while keeping coverage gaps material to interpretation visible. Insufficient evidence does not become a positive or clean result.

## 6. Source and evidence references

| Field | Shareable reference / actual existing value |
| --- | --- |
| case_id | not_provided |
| source_artifact_ref / source_artifact | not_provided / not_provided — no private path or secret |
| source_artifact_sha256 / byte_length | not_provided / not_provided — an actual existing measurement |
| source_schema / source_provenance_ref | not_provided / not_provided |
| observation_ref / source_json_pointer | not_provided / not_provided — existing fingerprint and source location |
| evidence_reference / evidence_access_limits | not_provided / not_provided — preserve direct/control/candidate distinctions |
| integrity_checks_actually_performed / unchecked_parts | not_provided / not_provided |

Repeat the table for each required item. An internal reference does not mean that raw evidence was copied to the client or reviewed. A hash, manifest or successful JSON parse does not authenticate a producer, authorization, finding accuracy or remediation. If only JSON and a manifest are supplied, state that HTML/full-bundle checks are missing; do not invent a verification result.

## 7. Technical follow-up recommendations

| Shareable item reference | Source recommendation | Separate human follow-up and rationale | Responsible role / separate authorization required | Actual completion evidence |
| --- | --- | --- | --- | --- |
| not_provided | not_provided | not_provided | not_provided | not_provided |

A recommendation is not an applied or effective fix. Live activity, a new test or reassessment is only a future separately authorized action; this document does not start it.

## 8. Comparison with a previous report, where supported

| Field | Value |
| --- | --- |
| comparison_artifact_ref / sha256 | not_provided / not_provided |
| before_artifact_ref / exact_byte_sha256 | not_provided / not_provided |
| after_artifact_ref / exact_byte_sha256 | not_provided / not_provided |
| relationship_to_this_assessment | not_provided — an independent fixture is not a real retest |
| operator_scope_statement_ref / coverage_limits | not_provided / not_provided |
| imported_groups / approved_explanation | not_provided / not_provided — retain existing groups; no recomputation |

Explain when suitable sources are unavailable. `only_in_before` does not mean fixed; `only_in_after` does not establish a newly appearing vulnerability. `changed` is not an automatic risk change, and `unchanged` does not establish unchanged security or equivalent coverage. Imported labels are not independently endorsed.

## 9. Data and interpretation limitations

| Field | Value |
| --- | --- |
| shared_data_categories / approved_redactions_ref | not_provided / not_provided |
| access_transfer_retention_deletion_decision_ref | not_provided |
| decision_owner / unresolved_data_decisions | not_provided / pending_decision |
| remaining_evidence_or_interpretation_limits | not_provided |

Do not invent a retention period, legal basis or sharing right. Source outcomes, human review, integrity and customer acceptance are separate matters. Internal notes, credentials and raw evidence are not shared automatically. The work does not provide protection against every vulnerability, exhaustive detection or a secure-system certificate.

## 10. Blank fields for actual delivery and approval records

| Field | Actual existing record only |
| --- | --- |
| manual_delivery_gate_ref / gate_status | not_provided / blocked |
| delivery_owner / intended_authorized_recipient_ref | not_provided / not_provided |
| actual_delivery_evidence_ref / delivered_at | not_provided / not_provided |
| customer_acceptance_evidence_ref / accepted_at | not_provided / not_provided |
| follow_up_agreement_ref / closure_evidence_ref | not_provided / not_provided |

Gate values are only `ready_for_manual_review`, `blocked`, `pending_decision`, `not_applicable`. Ready for manual review does not mean delivered or GO. Do not claim delivery or acceptance without actual evidence; the template does not create a signature or customer approval.

Preparation references: [delivery specification](../../DELIVERABLE_SPEC.tr.md), [review policy](../OBSERVATION_REVIEW_POLICY.tr.md), [manual delivery gate](../DELIVERY_GATE.tr.md). These are internal preparation references; the internal records are not automatically part of the client package.
