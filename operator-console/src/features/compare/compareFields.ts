/** Direct field semantics only. No score, rank, delta, risk or protection claim. */
import { receivedSortKey } from "../../data/viewModels";
import { allowedFieldValue, COMPARE_FIELDS, compareRequire, freezeComparison } from "./compareModel";
import type { ComparedField, CompareFieldKey, CompareState, CompareValue, ComparisonReason, ComparisonResult } from "./compareModel";
import { copyCompareState } from "./compareState";

export function compareField(key: CompareFieldKey, left: CompareValue, right: CompareValue): ComparedField {
  const field = COMPARE_FIELDS.find((item) => item.key === key); compareRequire(field !== undefined);
  let result: ComparisonResult, reason: ComparisonReason;
  if (left === null || right === null || (key === "termivar.report_presence" && (left === "none" || right === "none"))
    || (key === "device.connection" && (left === "never_seen" || right === "never_seen"))) {
    result = "missing"; reason = "missing_value";
  } else if (!allowedFieldValue(field, left) || !allowedFieldValue(field, right)) {
    result = "incomparable"; reason = "unsupported_value";
  } else if (left === "unknown" || right === "unknown") {
    result = "incomparable"; reason = "unknown_value";
  } else if (field.kind === "count") {
    // DTOs do not bind assessment targets/scopes or equivalent count windows.
    // Even equal known Termivar counts cannot establish comparable coverage.
    result = "incomparable"; reason = "scope_not_established";
  } else {
    const a = field.kind === "timestamp" ? receivedSortKey(left as string) : left;
    const b = field.kind === "timestamp" ? receivedSortKey(right as string) : right;
    result = a === b ? "same" : "different";
    reason = result === "same" ? "value_equal" : "value_different";
  }
  return Object.freeze({ key: field.key, section: field.section, kind: field.kind, left, right, result, reason });
}
export function compareFields(input: CompareState): readonly ComparedField[] {
  const state = copyCompareState(input);
  const rows = COMPARE_FIELDS.map((field) => compareField(field.key,
    state.slots[0]?.fields[field.key] ?? null, state.slots[1]?.fields[field.key] ?? null));
  return freezeComparison(rows);
}
