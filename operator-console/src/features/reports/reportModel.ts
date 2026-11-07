/** Frontend presentation copies only; not a snapshot/revision/receipt protocol. */
import type { AgeObservation, Device, ProductId } from "../../data/contracts";
import type { Locale } from "../../i18n/types";

export const MAX_REPORT_RECORDS = 20;
export const MAX_REPORT_BYTES = 256 * 1024;
export type ReportMode = "example" | "api";
export type ReportErrorCode = "invalid_report" | "context_mismatch" | "duplicate_record" | "record_not_found"
  | "record_limit" | "size_limit" | "empty_report";
export class ReportError extends Error {
  readonly code: ReportErrorCode;
  constructor(code: ReportErrorCode) { super(code); this.name = "ReportError"; this.code = code; }
}
export interface ReportContext {
  readonly tenantId: string;
  readonly mode: ReportMode;
  /** Local UI session stamp; never a principal, revision or authority. */
  readonly generation: number;
}
export type ReportMetricKey = "installed" | "reported_running" | "reported_stale" | "firewall_mode" | "scanner_installed"
  | "execution_available" | "report_presence" | "subject_count" | "item_count" | "informational" | "needs_review"
  | "confirmed" | "unassigned" | "info" | "low" | "medium" | "high" | "critical" | "availability";
export interface ReportMetric {
  readonly key: ReportMetricKey;
  readonly value: string | number | boolean | null;
}
export interface ReportProduct {
  readonly product: ProductId;
  readonly presence: "reported" | "missing";
  readonly status: string | null;
  readonly version: string | null;
  readonly sourceObservedAt: string | null;
  readonly receivedAt: string | null;
  readonly observation: AgeObservation | null;
  readonly reportImportedAt: string | null;
  readonly reportImportAge: AgeObservation | null;
  readonly source: "self_reported" | null;
  readonly producerVerification: "not_verified" | null;
  readonly metrics: readonly ReportMetric[];
}
export interface ReportCommonFields {
  readonly identityStatus: Device["identity_status"];
  readonly connectionStatus: Device["connection_status"];
  readonly revokedAt: string | null;
  readonly sourceObservedAt: string | null;
  readonly receivedAt: string | null;
  readonly readAt: string;
  readonly sourceObservation: AgeObservation;
  readonly source: "self_reported";
  readonly producerVerification: "not_verified";
  readonly products: readonly ReportProduct[];
}
/** Private in-memory binding and identifying labels; never pass to print UI. */
export interface ReportRecord extends ReportCommonFields {
  readonly context: ReportContext;
  readonly tenantName: string;
  readonly deviceId: string;
  readonly deviceName: string;
}
export interface ReportDraft {
  readonly context: ReportContext;
  readonly records: readonly ReportRecord[];
  readonly revision: number;
  readonly bytes: number;
}
export type DraftSnapshot = ReportDraft;
export interface ReportDeviceSection extends ReportCommonFields {
  readonly label: string;
  /** Omitted completely when identifiers are disabled. */
  readonly identifier?: string;
}
/** The only model the preview/print component may receive. */
export interface ReportModel {
  readonly title: string;
  readonly locale: Locale;
  readonly mode: ReportMode;
  readonly generatedAt: string;
  readonly includeIdentifiers: boolean;
  readonly tenant: { readonly label: string; readonly identifier?: string };
  readonly selectedCount: number;
  readonly scopeNote: string;
  readonly exampleNotice: string | null;
  readonly records: readonly ReportDeviceSection[];
}

export function reportRequire(ok: unknown, code: ReportErrorCode = "invalid_report"): asserts ok {
  if (!ok) throw new ReportError(code);
}
export function reportObject(input: unknown, keys: readonly string[]): Record<string, unknown> {
  reportRequire(input !== null && typeof input === "object" && !Array.isArray(input));
  const value = input as Record<string, unknown>;
  const actual = Object.keys(value);
  reportRequire(actual.length === keys.length && actual.every((key) => keys.includes(key)));
  return value;
}
export function reportText(input: unknown, maximum: number): string {
  reportRequire(typeof input === "string" && input.trim().length > 0 && input.length <= maximum * 2
    && [...input].length <= maximum && !/[\u0000-\u001f]/.test(input));
  return input;
}
export function reportTimestamp(input: unknown): string {
  reportRequire(typeof input === "string" && input.length <= 32);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?Z$/.exec(input);
  reportRequire(match !== null);
  const y = Number(match[1]), m = Number(match[2]), d = Number(match[3]);
  const h = Number(match[4]), minute = Number(match[5]), s = Number(match[6]);
  const date = new Date(0); date.setUTCFullYear(y, m - 1, d); date.setUTCHours(h, minute, s, 0);
  reportRequire(y >= 1 && date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d
    && date.getUTCHours() === h && date.getUTCMinutes() === minute && date.getUTCSeconds() === s);
  return input;
}
export function copyContext(input: ReportContext): ReportContext {
  const value = reportObject(input, ["tenantId", "mode", "generation"]);
  reportRequire(typeof value.tenantId === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value.tenantId)
    && (value.mode === "example" || value.mode === "api") && typeof value.generation === "number"
    && Number.isSafeInteger(value.generation) && value.generation >= 0);
  return Object.freeze({ tenantId: value.tenantId, mode: value.mode, generation: value.generation });
}
export function sameContext(a: ReportContext, b: ReportContext): boolean {
  return a.tenantId === b.tenantId && a.mode === b.mode && a.generation === b.generation;
}
export function freezeReport<T>(value: T): T {
  if (value !== null && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach(freezeReport);
    Object.freeze(value);
  }
  return value;
}
export function reportBytes(value: unknown): number {
  return new TextEncoder().encode(JSON.stringify(value)).byteLength;
}
