/** Pure local view actions. The caller owns File API sequencing/cancellation. */
import { freezePolicyReview, POLICY_PREVIEW_CONTRACT, POLICY_REVIEW_ERROR_CODES, POLICY_REVIEW_FILTERS, policyReviewRequire } from "./policyReviewModel";
import type { PolicyReviewDocument, PolicyReviewErrorCode, PolicyReviewFilter, PolicyReviewScenario, PolicyReviewState } from "./policyReviewModel";

export function createPolicyReviewState(): PolicyReviewState {
  return freezePolicyReview({ document: null, status: "empty", errorCode: null, selectedScenarioId: null,
    query: "", filter: "all", showDetails: false });
}
export function beginPolicyReviewImport(_state: PolicyReviewState): PolicyReviewState {
  return freezePolicyReview({ ...createPolicyReviewState(), status: "loading" });
}
/** Accept only the already-normalized immutable document returned by the adapter. */
export function completePolicyReviewImport(_state: PolicyReviewState, document: PolicyReviewDocument): PolicyReviewState {
  policyReviewRequire(Object.isFrozen(document) && document.contractVersion === POLICY_PREVIEW_CONTRACT
    && document.authorization === "not_evaluated" && document.executionAuthorized === false && document.verification === "not_performed"
    && document.scope === "packet_policy_preview_only" && Object.isFrozen(document.scenarios));
  return freezePolicyReview({ ...createPolicyReviewState(), document, status: "ready", selectedScenarioId: document.scenarios[0]?.scenarioId ?? null });
}
export function failPolicyReviewImport(_state: PolicyReviewState, code: PolicyReviewErrorCode): PolicyReviewState {
  const errorCode = POLICY_REVIEW_ERROR_CODES.includes(code) ? code : "invalid_artifact";
  return freezePolicyReview({ ...createPolicyReviewState(), status: "error", errorCode });
}
export function clearPolicyReview(_state: PolicyReviewState): PolicyReviewState { return createPolicyReviewState(); }
export function setPolicyReviewDetails(state: PolicyReviewState, showDetails: boolean): PolicyReviewState {
  policyReviewRequire(typeof showDetails === "boolean");
  // Clear a free-text search when hiding details; it must not remain a hidden-data match oracle.
  return freezePolicyReview({ ...state, showDetails: state.status === "ready" && showDetails, query: "" });
}
export function setPolicyReviewQuery(state: PolicyReviewState, query: string): PolicyReviewState {
  policyReviewRequire(typeof query === "string" && query.length <= 256 && !/[\u0000-\u001f]/.test(query));
  return freezePolicyReview({ ...state, query });
}
export function setPolicyReviewFilter(state: PolicyReviewState, filter: PolicyReviewFilter): PolicyReviewState {
  policyReviewRequire(POLICY_REVIEW_FILTERS.includes(filter));
  return freezePolicyReview({ ...state, filter });
}
export function selectPolicyReviewScenario(state: PolicyReviewState, scenarioId: string): PolicyReviewState {
  policyReviewRequire(state.status === "ready" && state.document?.scenarios.some((row) => row.scenarioId === scenarioId));
  return freezePolicyReview({ ...state, selectedScenarioId: scenarioId });
}
export function filteredPolicyReviewScenarios(state: PolicyReviewState): readonly PolicyReviewScenario[] {
  if (state.status !== "ready" || state.document === null) return Object.freeze([]);
  const query = state.query.trim().toLowerCase();
  return Object.freeze(state.document.scenarios.filter((scenario, index) => {
    const changed = scenario.decisionChanged || scenario.matchedPolicyChanged;
    if (state.filter === "changed" && !changed || state.filter === "unchanged" && changed) return false;
    if (state.filter === "allow_to_deny" || state.filter === "deny_to_allow") {
      if (scenario.changeType !== state.filter) return false;
    } else if (state.filter === "other_changed" && (!changed || scenario.changeType === "allow_to_deny" || scenario.changeType === "deny_to_allow")) return false;
    if (!query) return true;
    // No IP, port, profile, time, identifier, name, reason or trace enters hidden-mode search.
    const safe = [String(index + 1), scenario.base.decision.action, scenario.candidate.decision.action, scenario.changeType];
    const details = state.showDetails ? [scenario.scenarioId, scenario.context.sourceIp, scenario.context.destinationIp,
      scenario.context.protocol, String(scenario.context.destinationPort), scenario.context.networkProfile ?? "", scenario.context.localTime ?? "",
      scenario.context.sourceCountry ?? "", scenario.base.decision.policyName ?? "", scenario.candidate.decision.policyName ?? "",
      scenario.base.decision.reason, scenario.candidate.decision.reason] : [];
    return [...safe, ...details].join(" ").toLowerCase().includes(query);
  }));
}
