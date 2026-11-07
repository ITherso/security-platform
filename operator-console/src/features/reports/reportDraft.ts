/** Pure bounded draft operations. No fetch, persistent state, timers or clocks. */
import { copyCommonFields, copyReportRecord } from "./capture";
import { copyContext, freezeReport, MAX_REPORT_BYTES, MAX_REPORT_RECORDS,
  reportBytes, reportObject, reportRequire, reportTimestamp, sameContext } from "./reportModel";
import type { ReportContext, ReportDeviceSection, ReportDraft, ReportModel, ReportRecord } from "./reportModel";
import { translate } from "../../i18n";
import type { Locale } from "../../i18n/types";

function finish(contextValue: ReportContext, source: readonly ReportRecord[], revision: number): ReportDraft {
  const context = copyContext(contextValue);
  reportRequire(Array.isArray(source) && source.length <= MAX_REPORT_RECORDS, "record_limit");
  reportRequire(Number.isSafeInteger(revision) && revision >= 0);
  const records = source.map(copyReportRecord);
  reportRequire(records.every((record) => sameContext(context, record.context)), "context_mismatch");
  reportRequire(new Set(records.map((record) => record.deviceId)).size === records.length, "duplicate_record");
  const result = { context, records, revision, bytes: 0 };
  // Include the bytes field itself. This fixed point is deterministic and tiny.
  for (let i = 0; i < 4; i++) {
    const measured = reportBytes(result);
    if (measured === result.bytes) break;
    result.bytes = measured;
  }
  reportRequire(result.bytes === reportBytes(result) && result.bytes <= MAX_REPORT_BYTES, "size_limit");
  return freezeReport(result);
}
function checked(input: ReportDraft): ReportDraft {
  reportObject(input, ["context", "records", "revision", "bytes"]);
  reportRequire(Number.isSafeInteger(input.bytes) && input.bytes >= 0 && input.bytes <= MAX_REPORT_BYTES, "size_limit");
  const copy = finish(input.context, input.records, input.revision);
  reportRequire(input.bytes === copy.bytes);
  return copy;
}
function next(draft: ReportDraft): number {
  reportRequire(draft.revision < Number.MAX_SAFE_INTEGER);
  return draft.revision + 1;
}
export function createDraft(context: ReportContext): ReportDraft { return finish(context, [], 0); }
export function addRecord(input: ReportDraft, recordValue: ReportRecord): ReportDraft {
  const draft = checked(input), record = copyReportRecord(recordValue);
  reportRequire(sameContext(draft.context, record.context), "context_mismatch");
  reportRequire(!draft.records.some((old) => old.deviceId === record.deviceId), "duplicate_record");
  reportRequire(draft.records.length < MAX_REPORT_RECORDS, "record_limit");
  return finish(draft.context, [...draft.records, record], next(draft));
}
export function updateRecord(input: ReportDraft, recordValue: ReportRecord): ReportDraft {
  const draft = checked(input), record = copyReportRecord(recordValue);
  reportRequire(sameContext(draft.context, record.context), "context_mismatch");
  reportRequire(draft.records.some((old) => old.deviceId === record.deviceId), "record_not_found");
  return finish(draft.context, draft.records.map((old) => old.deviceId === record.deviceId ? record : old), next(draft));
}
export function removeRecord(input: ReportDraft, deviceId: string): ReportDraft {
  const draft = checked(input);
  reportRequire(typeof deviceId === "string" && draft.records.some((record) => record.deviceId === deviceId), "record_not_found");
  return finish(draft.context, draft.records.filter((record) => record.deviceId !== deviceId), next(draft));
}
export function clearDraft(input: ReportDraft): ReportDraft {
  const draft = checked(input); return finish(draft.context, [], next(draft));
}
export interface PreviewOptions { readonly includeIdentifiers: boolean; readonly createdAt: string; readonly locale: Locale }

/** Construct a separate safe render model. Hidden identifiers do not exist in it. */
export function buildPreview(input: ReportDraft, options: PreviewOptions): ReportModel {
  const draft = checked(input);
  reportObject(options, ["includeIdentifiers", "createdAt", "locale"]);
  reportRequire(typeof options.includeIdentifiers === "boolean");
  reportRequire(options.locale === "tr" || options.locale === "en");
  const locale = options.locale;
  reportRequire(draft.records.length > 0, "empty_report");
  const generatedAt = reportTimestamp(options.createdAt);
  const first = draft.records[0]; reportRequire(first !== undefined);
  const records: ReportDeviceSection[] = draft.records.map((record, index) => {
    const common = copyCommonFields(record);
    // No context, tenantName, deviceName, deviceId, generation, or original DTO.
    return options.includeIdentifiers
      ? { label: record.deviceName, identifier: record.deviceId, ...common }
      : { label: translate(locale, "report.genericDevice", String(index + 1).padStart(2, "0")), ...common };
  });
  const result: ReportModel = { title: translate(locale, "report.title"), locale, mode: draft.context.mode, generatedAt,
    includeIdentifiers: options.includeIdentifiers,
    tenant: options.includeIdentifiers ? { label: first.tenantName, identifier: draft.context.tenantId }
      : { label: translate(locale, "report.genericOrganization") },
    selectedCount: records.length, scopeNote: translate(locale, "report.scopeNote"),
    exampleNotice: draft.context.mode === "example" ? translate(locale, "report.exampleNotice") : null, records };
  reportRequire(reportBytes(result) <= MAX_REPORT_BYTES, "size_limit");
  return freezeReport(result);
}
