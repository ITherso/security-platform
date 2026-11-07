/** Frontend presentation copies only; not a snapshot/revision/receipt protocol. */
import type { AgeObservation, Device, ProductId } from "../../data/contracts";

export const MAX_REPORT_RECORDS = 20;
export const MAX_REPORT_BYTES = 256 * 1024;
export const REPORT_TITLE = "Seçili cihazlar — ürün bildirim özeti" as const;
export const REPORT_SCOPE_NOTE = "Yalnız seçili cihazları kapsar; tüm kurum envanteri değildir. Kayıtlar farklı okuma zamanlarına ait olabilir." as const;
export const EXAMPLE_REPORT_NOTICE = "ÖRNEK VERİ — GERÇEK CİHAZ RAPORU DEĞİLDİR" as const;
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
export const METRIC_LABELS = {
  installed: "Kurulu bildirimi", reported_running: "Çalışıyor bildirimi", reported_stale: "Kaynağın eski veri bildirimi",
  firewall_mode: "Motor kipi", scanner_installed: "Tarayıcı kurulu bildirimi", execution_available: "Yürütme kullanılabilirliği",
  report_presence: "Rapor özeti durumu", subject_count: "Konu sayısı", item_count: "Özet kayıt sayısı",
  informational: "Bilgilendirme", needs_review: "İnceleme gerekiyor", confirmed: "Üreticinin confirmed bildirimi",
  unassigned: "Önem derecesi atanmamış", info: "Info", low: "Low", medium: "Medium", high: "High", critical: "Critical",
  availability: "Ürün kullanılabilirliği",
} as const;
export type ReportMetricKey = keyof typeof METRIC_LABELS;
export interface ReportMetric {
  readonly key: ReportMetricKey;
  readonly label: string;
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
  readonly title: typeof REPORT_TITLE;
  readonly mode: ReportMode;
  readonly generatedAt: string;
  readonly includeIdentifiers: boolean;
  readonly tenant: { readonly label: string; readonly identifier?: string };
  readonly selectedCount: number;
  readonly scopeNote: typeof REPORT_SCOPE_NOTE;
  readonly exampleNotice: typeof EXAMPLE_REPORT_NOTICE | null;
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
