/** Pure local comparison review lifecycle, independent of assessment/device state. */
import { COMPARISON_ERROR_CODES, COMPARISON_FILTERS, comparisonRequire, freezeComparisonReview } from "./comparisonModel";
import type { ComparisonErrorCode, ComparisonFilter, ComparisonRecord, TermivarComparisonDocument, TermivarComparisonState } from "./comparisonModel";
export function createComparisonState(): TermivarComparisonState {
  return freezeComparisonReview({ document: null, status: "empty", errorCode: null, selectedRecordKey: null, query: "", filter: "all", showDetails: false });
}
export function beginComparisonImport(_state: TermivarComparisonState): TermivarComparisonState { return freezeComparisonReview({ ...createComparisonState(), status: "loading" }); }
export function completeComparisonImport(_state: TermivarComparisonState, document: TermivarComparisonDocument): TermivarComparisonState {
  comparisonRequire(Object.isFrozen(document) && Object.isFrozen(document.records) && document.schema === "termivar-report-comparison/v1"
    && document.scopeAssurance === "operator-declared" && document.coverageEquivalence === "not-established" && document.sourceAuthenticity === "not-established-by-parsing");
  return freezeComparisonReview({ ...createComparisonState(), document, status: "ready", selectedRecordKey: document.records[0]?.key ?? null });
}
export function failComparisonImport(_state: TermivarComparisonState, error: ComparisonErrorCode): TermivarComparisonState {
  const errorCode = COMPARISON_ERROR_CODES.includes(error) ? error : "invalid_comparison";
  return freezeComparisonReview({ ...createComparisonState(), status: "error", errorCode });
}
export function clearComparisonReview(_state: TermivarComparisonState): TermivarComparisonState { return createComparisonState(); }
export function setComparisonDetails(state: TermivarComparisonState, showDetails: boolean): TermivarComparisonState {
  comparisonRequire(typeof showDetails === "boolean"); return freezeComparisonReview({ ...state, showDetails: state.status === "ready" && showDetails, query: "" });
}
export function setComparisonQuery(state: TermivarComparisonState, query: string): TermivarComparisonState {
  comparisonRequire(typeof query === "string" && query.length <= 256 && !/[\u0000-\u001f]/.test(query)); return freezeComparisonReview({ ...state, query });
}
export function setComparisonFilter(state: TermivarComparisonState, filter: ComparisonFilter): TermivarComparisonState {
  comparisonRequire(COMPARISON_FILTERS.includes(filter)); return freezeComparisonReview({ ...state, filter });
}
export function selectComparisonRecord(state: TermivarComparisonState, key: string): TermivarComparisonState {
  comparisonRequire(state.status === "ready" && state.document?.records.some((record) => record.key === key)); return freezeComparisonReview({ ...state, selectedRecordKey: key });
}
export function filteredComparisonRecords(state: TermivarComparisonState): readonly ComparisonRecord[] {
  if (state.status !== "ready" || state.document === null) return Object.freeze([]);
  const query = state.query.trim().toLowerCase();
  return Object.freeze(state.document.records.filter((record, index) => {
    if (state.filter !== "all" && state.filter !== record.group) return false;
    if (!query) return true;
    const safe = [String(index + 1), record.group, ...record.changedFields];
    for (const projection of [record.before, record.after]) if (projection) safe.push(projection.disposition, projection.severity ?? "unassigned", projection.claimBasis);
    const details = state.showDetails ? [record.capabilityId] : [];
    if (state.showDetails) for (const projection of [record.before, record.after]) if (projection) details.push(projection.title, projection.category,
      projection.cwe ?? "", projection.redactedSummary, projection.remediation.id, projection.remediation.summary);
    // Fingerprints and source digests never enter search, even when free metadata is open.
    return [...safe, ...details].join(" ").toLowerCase().includes(query);
  }));
}
