/** Closed display copies. Never scan authority, raw transport data or device state. */
import type { TermivarClaimBasis, TermivarDisposition, TermivarSeverity } from "./termivarContracts";
export type { TermivarClaimBasis, TermivarDisposition, TermivarSeverity } from "./termivarContracts";
export const MAX_TERMIVAR_REVIEW_BYTES = 1024 * 1024;
export const MAX_TERMIVAR_MANIFEST_BYTES = 64 * 1024;
export const TERMIVAR_REVIEW_FILTERS = ["all", "informational", "needs_review", "confirmed"] as const;
export type TermivarReviewFilter = typeof TERMIVAR_REVIEW_FILTERS[number];
export const TERMIVAR_REVIEW_ERROR_CODES = ["file_too_large", "invalid_utf8", "invalid_json", "unsupported_artifact", "unsupported_version",
  "unsupported_extension", "invalid_artifact", "digest_unavailable", "unsupported_manifest"] as const;
export type TermivarReviewErrorCode = typeof TERMIVAR_REVIEW_ERROR_CODES[number];
export type TermivarReviewSource = "file" | "example";
export class TermivarReviewError extends Error {
  readonly code: TermivarReviewErrorCode;
  constructor(code: TermivarReviewErrorCode) { super(code); this.name = "TermivarReviewError"; this.code = code; }
}
export function termivarRequire(ok: unknown, code: TermivarReviewErrorCode = "invalid_artifact"): asserts ok {
  if (!ok) throw new TermivarReviewError(code);
}
export function freezeTermivar<T>(value: T): T {
  if (value !== null && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach(freezeTermivar); Object.freeze(value);
  }
  return value;
}
export interface TermivarFinding {
  /** Generated local ordinal key; not a native fingerprint or subject identity. */
  readonly key: string;
  readonly capabilityId: string;
  readonly title: string;
  readonly disposition: TermivarDisposition;
  readonly claimBasis: TermivarClaimBasis;
  readonly severity: TermivarSeverity | null;
  readonly confidencePpm: number;
  readonly evidenceCount: number;
  readonly directEvidenceCount: number;
  readonly controlEvidenceCount: number;
  readonly candidateEvidenceCount: number;
  readonly redactedSummary: string;
  readonly category: string;
  readonly cwe: string | null;
  readonly remediationId: string;
  readonly remediationSummary: string;
  readonly verificationStage: "passive" | "active" | null;
}
export interface TermivarCounts { readonly informational: number; readonly needs_review: number; readonly confirmed: number }
export interface TermivarSeverityCounts { readonly unassigned: number; readonly info: number; readonly low: number; readonly medium: number; readonly high: number; readonly critical: number }
export interface TermivarCoverage {
  readonly scope: "exact-origin" | null;
  readonly startedAt: null;
  readonly finishedAt: null;
  readonly requestLimit: number | null;
  readonly wallTimeLimitMs: number | null;
  readonly requestsUsed: number | null;
  readonly activeVerifications: number | null;
  readonly responseBytes: number | null;
  readonly elapsedMs: number | null;
  readonly projectionStatus: "available" | "unavailable";
  readonly projectionCode: string | null;
  readonly committedPassiveObservations: number | null;
  readonly semanticTruncated: boolean | null;
  readonly omittedDispatchReceipts: number | null;
  readonly inventoryConsistent: boolean | null;
  readonly unrepresentedLedgerSubjects: number | null;
}
export interface AssessmentDocument {
  readonly source: TermivarReviewSource;
  readonly artifactType: "rendered_assessment" | "web_assessment_diagnostic";
  readonly schema: "venom-rendered-assessment/v1" | "web-assessment/v2";
  readonly profile: "web-review";
  readonly status: "complete" | "incomplete" | "failed";
  readonly subjectCount: number;
  readonly itemCount: number | null;
  readonly findings: readonly TermivarFinding[];
  readonly counts: TermivarCounts | null;
  readonly severityCounts: TermivarSeverityCounts | null;
  readonly incompleteReasons: readonly string[];
  readonly coverage: TermivarCoverage;
  /** Exact selected file bytes, unrelated to the HBF canonical summary identity. */
  readonly selectedBytesSha256: string;
  readonly selectedByteLength: number;
  readonly sourceClaim: "self_reported";
  readonly producerVerification: "not_verified";
}
export interface ManifestReview {
  readonly status: "selected_json_matches" | "mismatch";
  readonly producerProduct: "Termivar";
  readonly producerVersion: string;
  readonly jsonHashMatches: boolean;
  readonly jsonLengthMatches: boolean;
  readonly summaryMatches: boolean;
  readonly htmlStatus: "not_selected_not_checked";
  readonly producerVerification: "not_verified";
  readonly bundleVerification: "not_performed";
}
export interface TermivarReviewState {
  readonly document: AssessmentDocument | null;
  readonly status: "empty" | "loading" | "ready" | "error";
  readonly errorCode: TermivarReviewErrorCode | null;
  readonly manifest: ManifestReview | null;
  readonly manifestStatus: "not_selected" | "loading" | "ready" | "error";
  readonly manifestErrorCode: TermivarReviewErrorCode | null;
  readonly selectedFindingKey: string | null;
  readonly query: string;
  readonly filter: TermivarReviewFilter;
  readonly showDetails: boolean;
}
