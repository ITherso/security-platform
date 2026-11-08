/** Actual native comparison.rs base JSON projection; optional audits are unsupported. */
export const TERMIVAR_COMPARISON_SCHEMA = "termivar-report-comparison/v1";
export const COMPARISON_GROUPS = ["only_in_after", "only_in_before", "changed", "unchanged"] as const;
export type ComparisonGroup = typeof COMPARISON_GROUPS[number];
export const COMPARISON_ROOT_FIELDS = ["schema", "scope_assurance", "coverage_equivalence", "source_authenticity", "interpretation_limits", "before", "after", ...COMPARISON_GROUPS] as const;
export const COMPARISON_SOURCE_FIELDS = ["sha256", "schema", "source_schema", "run_schema", "profile_schema", "profile", "status", "subject_count", "item_count", "optional_audits"] as const;
export const COMPARISON_RECORD_FIELDS = ["fingerprint", "capability_id", "before", "after", "changed_fields"] as const;
export const COMPARISON_CHANGED_FIELDS = ["title", "category", "disposition", "claim_basis", "severity", "cwe", "confidence_ppm", "redacted_summary", "remediation", "evidence"] as const;
export type ComparisonChangedField = typeof COMPARISON_CHANGED_FIELDS[number];
export const COMPARISON_INTERPRETATION_LIMITS = [
  "Imported dispositions and claim bases are untrusted source labels, not endorsed findings.",
  "Only in before does not mean fixed or resolved.",
  "Only in after does not establish when an observation first appeared.",
  "Unchanged means equal compared item projections, not equivalent coverage or security.",
] as const;
export const COMPARISON_DISPOSITIONS = ["informational", "needs_review", "confirmed"] as const;
export type ComparisonDisposition = typeof COMPARISON_DISPOSITIONS[number];
export const COMPARISON_CLAIM_BASES = ["observation", "differential", "verifier_transition"] as const;
export type ComparisonClaimBasis = typeof COMPARISON_CLAIM_BASES[number];
export const COMPARISON_SEVERITIES = ["info", "low", "medium", "high", "critical"] as const;
export type ComparisonSeverity = typeof COMPARISON_SEVERITIES[number];
export const COMPARISON_AUDIT_BOUND_CAPABILITIES = [
  "api.rest-readonly-surface-observed@1", "technology.wordpress-surface-observed@1", "technology.wordpress-metadata-source-response-observed@1",
  "web.review.template-evaluation.jinja-compatible-semantics@1", "xml.external-entity.repeated-outbound-interaction@1",
  "exposure.response-private-key-material@1", "exposure.response-aws-access-key-pair@1", "exposure.response-stripe-live-secret@1", "exposure.response-bearer-authorization@1",
] as const;
