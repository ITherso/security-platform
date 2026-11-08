/** Closed immutable display state; no report pairing, scan or security verdict. */
import type { ComparisonChangedField, ComparisonClaimBasis, ComparisonDisposition, ComparisonGroup, ComparisonSeverity } from "./comparisonContracts";
export type { ComparisonChangedField, ComparisonClaimBasis, ComparisonDisposition, ComparisonGroup, ComparisonSeverity } from "./comparisonContracts";
export const MAX_COMPARISON_REVIEW_BYTES = 8 * 1024 * 1024;
export const COMPARISON_FILTERS = ["all", "only_in_after", "only_in_before", "changed", "unchanged"] as const;
export type ComparisonFilter = typeof COMPARISON_FILTERS[number];
export const COMPARISON_ERROR_CODES = ["file_too_large", "invalid_utf8", "invalid_json", "unsupported_artifact", "unsupported_version", "unsupported_section", "invalid_comparison", "reader_unavailable"] as const;
export type ComparisonErrorCode = typeof COMPARISON_ERROR_CODES[number];
export type ComparisonSource = "file" | "example";
export class TermivarComparisonError extends Error {
  readonly code: ComparisonErrorCode;
  constructor(code: ComparisonErrorCode) { super(code); this.name = "TermivarComparisonError"; this.code = code; }
}
export function comparisonRequire(ok: unknown, code: ComparisonErrorCode = "invalid_comparison"): asserts ok {
  if (!ok) throw new TermivarComparisonError(code);
}
export function freezeComparisonReview<T>(value: T): T {
  if (value !== null && typeof value === "object") { Object.values(value as Record<string, unknown>).forEach(freezeComparisonReview); Object.freeze(value); }
  return value;
}
export interface ComparisonSourceMetadata {
  readonly sha256: string;
  readonly schema: "venom-rendered-assessment/v1";
  readonly sourceSchema: "venom-assessment-run/v1";
  readonly runSchema: "venom-run/v1";
  readonly profileSchema: "venom.scan-profile/v1";
  readonly profile: "web-review";
  readonly status: "complete";
  readonly subjectCount: number;
  readonly itemCount: number;
}
export interface ComparisonEvidence {
  readonly evidenceCount: number;
  readonly directReferenceCount: number;
  readonly controlReferenceCount: number;
  readonly candidateReferenceCount: number;
  readonly casePresent: boolean;
  readonly outcomePresent: boolean;
  readonly verificationStage: "passive" | "active" | null;
}
export interface ComparisonProjection {
  readonly title: string;
  readonly category: string;
  readonly disposition: ComparisonDisposition;
  readonly claimBasis: ComparisonClaimBasis;
  readonly severity: ComparisonSeverity | null;
  readonly cwe: string | null;
  readonly confidencePpm: number;
  readonly redactedSummary: string;
  readonly remediation: { readonly id: string; readonly summary: string };
  readonly evidence: ComparisonEvidence;
}
export interface ComparisonRecord {
  /** Generated view key, unrelated to native fingerprint identity or source ordering. */
  readonly key: string;
  readonly group: ComparisonGroup;
  readonly fingerprint: string;
  readonly capabilityId: string;
  readonly before: ComparisonProjection | null;
  readonly after: ComparisonProjection | null;
  readonly changedFields: readonly ComparisonChangedField[];
}
export interface TermivarComparisonDocument {
  readonly source: ComparisonSource;
  readonly artifactType: "termivar_comparison";
  readonly schema: "termivar-report-comparison/v1";
  readonly scopeAssurance: "operator-declared";
  readonly coverageEquivalence: "not-established";
  readonly sourceAuthenticity: "not-established-by-parsing";
  readonly before: ComparisonSourceMetadata;
  readonly after: ComparisonSourceMetadata;
  readonly records: readonly ComparisonRecord[];
  /** Derived from fully validated arrays; not a claimed wire `counts` property. */
  readonly counts: Readonly<Record<ComparisonGroup, number>>;
}
export interface TermivarComparisonState {
  readonly document: TermivarComparisonDocument | null;
  readonly status: "empty" | "loading" | "ready" | "error";
  readonly errorCode: ComparisonErrorCode | null;
  readonly selectedRecordKey: string | null;
  readonly query: string;
  readonly filter: ComparisonFilter;
  readonly showDetails: boolean;
}
