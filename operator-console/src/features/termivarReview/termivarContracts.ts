/** Native Termivar wire names, read from the existing renderer/CLI DTOs. */
export const TERMIVAR_RENDERED_SCHEMA = "venom-rendered-assessment/v1";
export const TERMIVAR_DIAGNOSTIC_SCHEMA = "web-assessment/v2";
export const TERMIVAR_MANIFEST_SCHEMA = "termivar-report-bundle/v1";
export const TERMIVAR_DISPOSITIONS = ["informational", "needs_review", "confirmed"] as const;
export type TermivarDisposition = typeof TERMIVAR_DISPOSITIONS[number];
export const TERMIVAR_SEVERITIES = ["info", "low", "medium", "high", "critical"] as const;
export type TermivarSeverity = typeof TERMIVAR_SEVERITIES[number];
export const TERMIVAR_CLAIM_BASES = ["observation", "differential", "verifier_transition"] as const;
export type TermivarClaimBasis = typeof TERMIVAR_CLAIM_BASES[number];
export const TERMIVAR_RENDERED_FIELDS = ["schema", "source_schema", "run_schema", "profile_schema", "profile", "status", "subject_count", "item_count", "items"] as const;
export const TERMIVAR_ITEM_FIELDS = ["schema", "capability_id", "subject_reference", "title", "disposition", "claim_basis", "severity", "confidence_ppm", "fingerprint", "evidence_count", "redacted_summary", "category", "cwe", "remediation", "evidence_references", "control_evidence_references", "candidate_evidence_references", "case_reference", "outcome_reference", "verification_stage"] as const;
/** These item capabilities require omitted audit sections in the native reader. */
export const TERMIVAR_AUDIT_BOUND_CAPABILITIES = [
  "api.rest-readonly-surface-observed@1", "technology.wordpress-surface-observed@1",
  "technology.wordpress-metadata-source-response-observed@1",
  "web.review.template-evaluation.jinja-compatible-semantics@1",
  "xml.external-entity.repeated-outbound-interaction@1", "exposure.response-private-key-material@1",
  "exposure.response-aws-access-key-pair@1", "exposure.response-stripe-live-secret@1", "exposure.response-bearer-authorization@1",
] as const;
export const TERMIVAR_DIAGNOSTIC_FIELDS = ["schema_version", "target_origin", "disposition", "incomplete_reasons", "profile_contract", "assessment"] as const;
export const TERMIVAR_DIAGNOSTIC_REPORT_FIELDS = ["subjects", "forms", "assessment_items", "semantics", "defense", "usage", "transport"] as const;
/** assessment_scan.rs incomplete_reason_code plus the two CLI-added codes. */
export const TERMIVAR_INCOMPLETE_REASONS = [
  "subject_limit", "discovery_depth_limit", "document_reference_limit", "canonical_url_bytes_limit", "retained_url_bytes_limit",
  "form_limit", "form_control_limit", "query_parameter_name_limit", "response_body_incomplete", "partial_representation", "invalid_utf8",
  "total_request_limit", "response_bytes_limit", "request_body_bytes_limit", "wall_time_limit", "active_verification_limit",
  "same_action_attempt_limit", "consecutive_no_progress_limit", "action_cycle_limit", "adaptation_limit", "human_review_required",
  "subject_execution_incomplete", "host_cancellation", "semantic_extraction_limit", "passive_response_projection_limit",
  "assessment_subject_identity_unavailable", "differential_review_incomplete", "api_visibility_review_incomplete", "graphql_review_incomplete",
  "openapi_review_incomplete", "rest_review_incomplete", "xml_external_entity_review_incomplete", "tls_negotiation_review_incomplete",
  "wordpress_review_incomplete", "authorization_review_incomplete", "other", "assessment_item_projection_incomplete", "started_runtime_failure",
] as const;
export const TERMIVAR_PROFILE_CAPABILITIES = ["standard_web_decision", "origin_discovery", "semantic_extraction", "defense_observation", "defense_shadow_planning", "passive_security_review", "low_risk_differential_review"] as const;
/** Native WebAssessmentLimits setters; an additional shared UI JSON budget applies. */
export const TERMIVAR_PROFILE_LIMITS = [
  ["max_subjects", 1, 1024], ["max_discovery_depth", 0, 16], ["max_references_per_document", 0, 2048],
  ["max_canonical_url_bytes", 1, 8192], ["max_retained_url_bytes", 1, 8388608], ["max_forms", 0, 1024],
  ["max_controls_per_form", 0, 256], ["max_query_parameter_names", 0, 256], ["max_total_requests", 0, 10000],
  ["max_response_body_bytes", 1, 16777216], ["max_total_response_bytes", 1, 268435456],
  ["max_wall_time_ms", 0, 3600000], ["max_active_verifications", 0, 64],
] as const;
