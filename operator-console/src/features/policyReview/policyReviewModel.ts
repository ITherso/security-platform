/** Display-only copies of an existing CLI preview. No evaluator or authority. */
export const MAX_POLICY_REVIEW_BYTES = 512 * 1024;
export const POLICY_PREVIEW_CONTRACT = "sp-hbf-preview/v1";
export const POLICY_REVIEW_FILTERS = ["all", "changed", "unchanged", "allow_to_deny", "deny_to_allow", "other_changed"] as const;
export type PolicyReviewFilter = typeof POLICY_REVIEW_FILTERS[number];
export type PolicyReviewSource = "file" | "example";
export type PolicyReviewAction = "ALLOW" | "DENY" | "DENY_TEMP";
export type PolicyReviewChange = "unchanged" | "allow_to_deny" | "deny_to_allow" | "other_changed" | "policy_only_changed";
export type PolicyReviewErrorCode = "file_too_large" | "invalid_utf8" | "invalid_json"
  | "unsupported_artifact" | "unsupported_version" | "invalid_artifact";
export const POLICY_REVIEW_ERROR_CODES: readonly PolicyReviewErrorCode[] = ["file_too_large", "invalid_utf8", "invalid_json",
  "unsupported_artifact", "unsupported_version", "invalid_artifact"];

export class PolicyReviewError extends Error {
  readonly code: PolicyReviewErrorCode;
  constructor(code: PolicyReviewErrorCode) { super(code); this.name = "PolicyReviewError"; this.code = code; }
}
export function policyReviewRequire(ok: unknown, code: PolicyReviewErrorCode = "invalid_artifact"): asserts ok {
  if (!ok) throw new PolicyReviewError(code);
}
export function freezePolicyReview<T>(value: T): T {
  if (value !== null && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach(freezePolicyReview);
    Object.freeze(value);
  }
  return value;
}

export interface PolicyReviewContext {
  readonly sourceIp: string;
  readonly destinationIp: string;
  readonly protocol: "TCP" | "UDP";
  readonly destinationPort: number;
  readonly networkProfile: "HOME" | "WORK" | "PUBLIC" | null;
  readonly localTime: string | null;
  readonly sourceCountry: string | null;
}
export interface PolicyReviewDecision {
  readonly action: PolicyReviewAction;
  readonly policyId: number | null;
  readonly policyName: string | null;
  readonly reason: string;
  readonly tempBlockSeconds: number | null;
  readonly natIntent: boolean;
  readonly logIntent: boolean;
}
export interface PolicyReviewTrace {
  readonly policyId: number;
  readonly policyName: string;
  readonly matched: boolean;
  readonly selected: boolean;
  readonly reasons: readonly string[];
}
export interface PolicyReviewEvaluation {
  readonly decision: PolicyReviewDecision;
  readonly trace: readonly PolicyReviewTrace[];
  readonly traceTotal: number;
  readonly traceComplete: boolean;
}
export interface PolicyReviewScenario {
  /** Treat every free identifier and explanation as sensitive presentation data. */
  readonly scenarioId: string;
  readonly context: PolicyReviewContext;
  readonly base: PolicyReviewEvaluation;
  readonly candidate: PolicyReviewEvaluation;
  readonly decisionChanged: boolean;
  readonly matchedPolicyChanged: boolean;
  /** Classification of supplied decisions, never a new policy evaluation. */
  readonly changeType: PolicyReviewChange;
}
export interface PolicyReviewDocument {
  readonly source: PolicyReviewSource;
  readonly artifactType: "preview";
  readonly contractVersion: typeof POLICY_PREVIEW_CONTRACT;
  readonly status: "ok" | "blocked";
  readonly blockerCodes: readonly string[];
  readonly legacyBaseVersion: string | null;
  readonly baseFingerprint: string | null;
  readonly candidateFingerprint: string | null;
  readonly adapterFingerprint: string | null;
  readonly previewFingerprint: string | null;
  readonly scenarios: readonly PolicyReviewScenario[];
  readonly authorization: "not_evaluated";
  readonly executionAuthorized: false;
  readonly verification: "not_performed";
  readonly scope: "packet_policy_preview_only";
}
export interface PolicyReviewState {
  readonly document: PolicyReviewDocument | null;
  readonly status: "empty" | "loading" | "ready" | "error";
  readonly errorCode: PolicyReviewErrorCode | null;
  readonly selectedScenarioId: string | null;
  readonly query: string;
  readonly filter: PolicyReviewFilter;
  readonly showDetails: boolean;
}
