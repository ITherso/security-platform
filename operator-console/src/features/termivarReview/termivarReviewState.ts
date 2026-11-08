/** Pure local actions. Async read/digest ownership remains at the store boundary. */
import { freezeTermivar, TERMIVAR_REVIEW_ERROR_CODES, TERMIVAR_REVIEW_FILTERS, termivarRequire } from "./termivarModel";
import type { AssessmentDocument, ManifestReview, TermivarFinding, TermivarReviewErrorCode, TermivarReviewFilter, TermivarReviewState } from "./termivarModel";

export function createTermivarReviewState(): TermivarReviewState {
  return freezeTermivar({ document: null, status: "empty", errorCode: null, manifest: null, manifestStatus: "not_selected", manifestErrorCode: null,
    selectedFindingKey: null, query: "", filter: "all", showDetails: false });
}
export function beginTermivarImport(_state: TermivarReviewState): TermivarReviewState { return freezeTermivar({ ...createTermivarReviewState(), status: "loading" }); }
export function completeTermivarImport(_state: TermivarReviewState, document: AssessmentDocument): TermivarReviewState {
  termivarRequire(Object.isFrozen(document) && Object.isFrozen(document.findings) && document.sourceClaim === "self_reported" && document.producerVerification === "not_verified");
  return freezeTermivar({ ...createTermivarReviewState(), document, status: "ready", selectedFindingKey: document.findings[0]?.key ?? null });
}
function errorCode(code: TermivarReviewErrorCode): TermivarReviewErrorCode { return TERMIVAR_REVIEW_ERROR_CODES.includes(code) ? code : "invalid_artifact"; }
export function failTermivarImport(_state: TermivarReviewState, code: TermivarReviewErrorCode): TermivarReviewState {
  return freezeTermivar({ ...createTermivarReviewState(), status: "error", errorCode: errorCode(code) });
}
export function clearTermivarReview(_state: TermivarReviewState): TermivarReviewState { return createTermivarReviewState(); }
export function beginTermivarManifestImport(state: TermivarReviewState): TermivarReviewState {
  termivarRequire(state.status === "ready" && state.document !== null);
  return freezeTermivar({ ...state, manifest: null, manifestStatus: "loading", manifestErrorCode: null });
}
export function completeTermivarManifestImport(state: TermivarReviewState, manifest: ManifestReview): TermivarReviewState {
  termivarRequire(state.status === "ready" && state.document !== null && Object.isFrozen(manifest) && manifest.producerVerification === "not_verified"
    && manifest.bundleVerification === "not_performed" && manifest.htmlStatus === "not_selected_not_checked");
  return freezeTermivar({ ...state, manifest, manifestStatus: "ready", manifestErrorCode: null });
}
export function failTermivarManifestImport(state: TermivarReviewState, code: TermivarReviewErrorCode): TermivarReviewState {
  termivarRequire(state.status === "ready" && state.document !== null);
  return freezeTermivar({ ...state, manifest: null, manifestStatus: "error", manifestErrorCode: errorCode(code) });
}
export function setTermivarDetails(state: TermivarReviewState, showDetails: boolean): TermivarReviewState {
  termivarRequire(typeof showDetails === "boolean"); return freezeTermivar({ ...state, showDetails: state.status === "ready" && showDetails, query: "" });
}
export function setTermivarQuery(state: TermivarReviewState, query: string): TermivarReviewState {
  termivarRequire(typeof query === "string" && query.length <= 256 && !/[\u0000-\u001f]/.test(query)); return freezeTermivar({ ...state, query });
}
export function setTermivarFilter(state: TermivarReviewState, filter: TermivarReviewFilter): TermivarReviewState {
  termivarRequire(TERMIVAR_REVIEW_FILTERS.includes(filter)); return freezeTermivar({ ...state, filter });
}
export function selectTermivarFinding(state: TermivarReviewState, key: string): TermivarReviewState {
  termivarRequire(state.status === "ready" && state.document?.findings.some((finding) => finding.key === key)); return freezeTermivar({ ...state, selectedFindingKey: key });
}
export function filteredTermivarFindings(state: TermivarReviewState): readonly TermivarFinding[] {
  if (state.status !== "ready" || state.document === null) return Object.freeze([]);
  const query = state.query.trim().toLowerCase();
  return Object.freeze(state.document.findings.filter((finding, index) => {
    if (state.filter !== "all" && finding.disposition !== state.filter) return false;
    if (!query) return true;
    const safe = [String(index + 1), finding.disposition, finding.severity ?? "unassigned", finding.claimBasis];
    const details = state.showDetails ? [finding.capabilityId, finding.title, finding.redactedSummary, finding.category,
      finding.cwe ?? "", finding.remediationId, finding.remediationSummary] : [];
    return [...safe, ...details].join(" ").toLowerCase().includes(query);
  }));
}
