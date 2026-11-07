/** Closed frontend copies. No authority, configuration or protection equivalence. */
export type CompareMode = "example" | "api";
export type CompareSide = "left" | "right";
export type CompareSection = "device" | "hbf" | "termivar" | "antivirus";
export type CompareFieldKind = "enum" | "boolean" | "version" | "timestamp" | "count";
export type CompareValue = string | number | boolean | null;
export const MAX_COMPARABLE_BYTES = 32 * 1024;
export const MAX_COMPARE_BYTES = 64 * 1024;
interface FieldSpec {
  readonly key: string; readonly section: CompareSection; readonly kind: CompareFieldKind;
  readonly values?: readonly string[]; readonly required?: boolean; readonly minimum?: number; readonly maximum?: number;
}
export const COMPARE_FIELDS = [
  { key: "device.registration", section: "device", kind: "enum", values: ["active", "revoked"], required: true },
  { key: "device.connection", section: "device", kind: "enum", values: ["recent", "stale", "never_seen"], required: true },
  { key: "device.received_at", section: "device", kind: "timestamp" },
  { key: "device.observed_at", section: "device", kind: "timestamp" },
  { key: "device.read_at", section: "device", kind: "timestamp", required: true },
  { key: "device.revoked_at", section: "device", kind: "timestamp" },
  { key: "hbf.status", section: "hbf", kind: "enum", values: ["running", "observing", "degraded", "stopped", "unavailable", "unknown"] },
  { key: "hbf.version", section: "hbf", kind: "version" },
  { key: "hbf.installed", section: "hbf", kind: "boolean" },
  { key: "hbf.running", section: "hbf", kind: "boolean" },
  { key: "hbf.stale", section: "hbf", kind: "boolean" },
  { key: "hbf.mode", section: "hbf", kind: "enum", values: ["enforce", "sniff", "unknown"] },
  { key: "hbf.received_at", section: "hbf", kind: "timestamp" },
  { key: "hbf.observed_at", section: "hbf", kind: "timestamp" },
  { key: "hbf.source", section: "hbf", kind: "enum", values: ["self_reported"] },
  { key: "hbf.verification", section: "hbf", kind: "enum", values: ["not_verified"] },
  { key: "termivar.status", section: "termivar", kind: "enum", values: ["experimental", "unknown"] },
  { key: "termivar.version", section: "termivar", kind: "version" },
  { key: "termivar.scanner_installed", section: "termivar", kind: "boolean" },
  { key: "termivar.execution_available", section: "termivar", kind: "boolean" },
  { key: "termivar.report_presence", section: "termivar", kind: "enum", values: ["present", "none", "unknown"] },
  { key: "termivar.subject_count", section: "termivar", kind: "count", minimum: 1, maximum: 1024 },
  { key: "termivar.item_count", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.informational", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.needs_review", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.confirmed", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.unassigned", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.info", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.low", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.medium", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.high", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.critical", section: "termivar", kind: "count", minimum: 0, maximum: 4096 },
  { key: "termivar.imported_at", section: "termivar", kind: "timestamp" },
  { key: "termivar.received_at", section: "termivar", kind: "timestamp" },
  { key: "termivar.observed_at", section: "termivar", kind: "timestamp" },
  { key: "termivar.source", section: "termivar", kind: "enum", values: ["self_reported"] },
  { key: "termivar.verification", section: "termivar", kind: "enum", values: ["not_verified"] },
  { key: "av.status", section: "antivirus", kind: "enum", values: ["planned", "unknown"] },
  { key: "av.availability", section: "antivirus", kind: "enum", values: ["unavailable", "unknown"] },
  { key: "av.execution_available", section: "antivirus", kind: "boolean" },
  { key: "av.received_at", section: "antivirus", kind: "timestamp" },
  { key: "av.observed_at", section: "antivirus", kind: "timestamp" },
  { key: "av.source", section: "antivirus", kind: "enum", values: ["self_reported"] },
  { key: "av.verification", section: "antivirus", kind: "enum", values: ["not_verified"] },
  { key: "device.source", section: "antivirus", kind: "enum", values: ["self_reported"], required: true },
  { key: "device.verification", section: "antivirus", kind: "enum", values: ["not_verified"], required: true },
] as const satisfies readonly FieldSpec[];
export type CompareFieldDefinition = typeof COMPARE_FIELDS[number];
export type CompareFieldKey = CompareFieldDefinition["key"];
export type CompareFieldValues = Readonly<Record<CompareFieldKey, CompareValue>>;
export interface CompareContext { readonly tenantId: string; readonly mode: CompareMode; readonly generation: number }
export interface ComparableDevice {
  readonly tenantId: string;
  readonly deviceId: string;
  readonly deviceName: string;
  readonly fields: CompareFieldValues;
}
export type CompareSlots = readonly [ComparableDevice | null, ComparableDevice | null];
export interface CompareState { readonly context: CompareContext; readonly slots: CompareSlots; readonly bytes: number }
export type ComparisonResult = "same" | "different" | "missing" | "incomparable";
export type ComparisonReason = "value_equal" | "value_different" | "missing_value" | "unknown_value" | "scope_not_established" | "unsupported_value";
export interface ComparedField {
  readonly key: CompareFieldKey; readonly section: CompareSection; readonly kind: CompareFieldKind;
  readonly left: CompareValue; readonly right: CompareValue; readonly result: ComparisonResult; readonly reason: ComparisonReason;
}
export type CompareErrorCode = "invalid_comparison" | "context_mismatch" | "duplicate_device" | "selection_full"
  | "device_not_found" | "record_size_limit" | "size_limit" | "invalid_slot";
export class CompareError extends Error {
  readonly code: CompareErrorCode;
  constructor(code: CompareErrorCode) { super(code); this.name = "CompareError"; this.code = code; }
}
export function compareRequire(value: unknown, code: CompareErrorCode = "invalid_comparison"): asserts value {
  if (!value) throw new CompareError(code);
}
export function compareObject(input: unknown, keys: readonly string[]): Record<string, unknown> {
  compareRequire(input !== null && typeof input === "object" && !Array.isArray(input));
  const value = input as Record<string, unknown>, actual = Object.keys(value);
  compareRequire(actual.length === keys.length && actual.every((key) => keys.includes(key)));
  return value;
}
export function compareId(input: unknown): string {
  compareRequire(typeof input === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(input));
  return input;
}
export function compareTimestamp(input: unknown): string {
  compareRequire(typeof input === "string" && input.length <= 32);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?Z$/.exec(input);
  compareRequire(match !== null);
  const y = Number(match[1]), m = Number(match[2]), d = Number(match[3]);
  const h = Number(match[4]), minute = Number(match[5]), s = Number(match[6]);
  const date = new Date(0); date.setUTCFullYear(y, m - 1, d); date.setUTCHours(h, minute, s, 0);
  compareRequire(y >= 1 && date.getUTCFullYear() === y && date.getUTCMonth() === m - 1 && date.getUTCDate() === d
    && date.getUTCHours() === h && date.getUTCMinutes() === minute && date.getUTCSeconds() === s);
  return input;
}
export function freezeComparison<T>(input: T): T {
  if (input !== null && typeof input === "object") {
    Object.values(input as Record<string, unknown>).forEach(freezeComparison); Object.freeze(input);
  }
  return input;
}
export function compareBytes(input: unknown): number { return new TextEncoder().encode(JSON.stringify(input)).byteLength; }
export function copyCompareContext(input: CompareContext): CompareContext {
  const value = compareObject(input, ["tenantId", "mode", "generation"]);
  const tenantId = compareId(value.tenantId);
  compareRequire((value.mode === "example" || value.mode === "api") && typeof value.generation === "number"
    && Number.isSafeInteger(value.generation) && value.generation >= 0);
  return Object.freeze({ tenantId, mode: value.mode, generation: value.generation });
}
export function allowedFieldValue(definition: CompareFieldDefinition, value: unknown): value is CompareValue {
  const spec: FieldSpec = definition;
  if (value === null) return !spec.required;
  switch (spec.kind) {
    case "enum": return typeof value === "string" && spec.values !== undefined && spec.values.includes(value);
    case "boolean": return typeof value === "boolean" && (!(spec.key === "termivar.execution_available" || spec.key === "av.execution_available") || value === false);
    case "version": return typeof value === "string" && value.length <= 64 && /^[A-Za-z0-9][A-Za-z0-9._+\-]*$/.test(value);
    case "count": return typeof value === "number" && Number.isSafeInteger(value) && value >= (spec.minimum ?? 0) && value <= (spec.maximum ?? 4096);
    case "timestamp": try { compareTimestamp(value); return true; } catch { return false; }
  }
}
export function copyComparableDevice(input: ComparableDevice): ComparableDevice {
  compareObject(input, ["tenantId", "deviceId", "deviceName", "fields"]);
  const tenantId = compareId(input.tenantId), deviceId = compareId(input.deviceId);
  compareRequire(typeof input.deviceName === "string" && input.deviceName.trim().length > 0 && input.deviceName.length <= 160
    && [...input.deviceName].length <= 80 && !/[\u0000-\u001f]/.test(input.deviceName));
  const source = compareObject(input.fields, COMPARE_FIELDS.map((field) => field.key));
  const pairs = COMPARE_FIELDS.map((definition): [CompareFieldKey, CompareValue] => {
    const value = source[definition.key]; compareRequire(allowedFieldValue(definition, value)); return [definition.key, value];
  });
  const fields = Object.fromEntries(pairs) as Record<CompareFieldKey, CompareValue>;
  compareRequire((fields["device.registration"] === "revoked") === (fields["device.revoked_at"] !== null)
    && (fields["device.connection"] === "never_seen") === (fields["device.received_at"] === null));
  for (const product of ["hbf", "termivar", "av"] as const) {
    if (fields[`${product}.status`] === null) compareRequire(COMPARE_FIELDS.filter((field) => field.key.startsWith(product + "."))
      .every((field) => fields[field.key] === null));
    else compareRequire(fields[`${product}.source`] === "self_reported" && fields[`${product}.verification`] === "not_verified"
      && fields[`${product}.received_at`] !== null && fields[`${product}.received_at`] === fields["device.received_at"]);
  }
  const countKeys = COMPARE_FIELDS.filter((field) => field.kind === "count");
  if (fields["termivar.report_presence"] === "present") {
    compareRequire(fields["termivar.imported_at"] !== null && countKeys.every((field) => fields[field.key] !== null));
    compareRequire(Number(fields["termivar.informational"]) + Number(fields["termivar.needs_review"]) + Number(fields["termivar.confirmed"]) === fields["termivar.item_count"]);
    compareRequire(["unassigned", "info", "low", "medium", "high", "critical"].reduce((sum, key) =>
      sum + Number(fields[`termivar.${key}` as CompareFieldKey]), 0) === fields["termivar.item_count"]);
  } else compareRequire(fields["termivar.imported_at"] === null && countKeys.every((field) => fields[field.key] === null));
  const result: ComparableDevice = { tenantId, deviceId, deviceName: input.deviceName, fields };
  compareRequire(compareBytes(result) <= MAX_COMPARABLE_BYTES, "record_size_limit");
  return freezeComparison(result);
}
