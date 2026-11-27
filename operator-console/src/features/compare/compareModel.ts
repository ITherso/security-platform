/** Closed frontend copies. No authority, configuration or protection equivalence. */
import { CAPABILITY_STATES, EDR_SENSOR_STATES, ISOLATION_STATES, PREVIOUS_RUN_ENDS, RESPONSE_CHANNEL_STATES,
  RULE_SET_STATES, SENSOR_ERROR_CODES, SERVICE_CONFIG_STATES } from "../../data/contracts";

export type CompareMode = "example" | "api";
export type CompareSide = "left" | "right";
export type CompareSection = "device" | "hbf" | "termivar" | "edr_agent" | "antivirus";
/** "text": a string by its Platform pattern; "number": a bounded integer compared by value, unlike a count. */
export type CompareFieldKind = "enum" | "boolean" | "version" | "timestamp" | "count" | "text" | "number";
export type CompareValue = string | number | boolean | null;
/** The agent's Snapshot version: V2 (contracts.EdrAgentStatus) or V3 (contracts.EdrAgentStatusV3). */
export type AgentFormat = "v2" | "v3";
export const MAX_COMPARABLE_BYTES = 32 * 1024;
export const MAX_COMPARE_BYTES = 64 * 1024;
interface FieldSpec {
  readonly key: string; readonly section: CompareSection; readonly kind: CompareFieldKind;
  readonly values?: readonly string[]; readonly required?: boolean; readonly minimum?: number; readonly maximum?: number;
  readonly pattern?: RegExp; readonly maxLength?: number;
  /** An agent field that only this Snapshot version has. */
  readonly format?: AgentFormat;
  /** A device time: also within the normalizer's window, the years 1970 to 9998 (normalize.ts windowTime). */
  readonly deviceTime?: true;
}
/** An agent counter, action sequence or quarantine item count goes up to the largest safe integer. */
const SAFE = Number.MAX_SAFE_INTEGER;
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
  // The Altay EDR agent's own state: "edr." and its Platform field name, in the device-detail card's order. A field of
  // one Snapshot version only is marked with that version.
  { key: "edr.status", section: "edr_agent", kind: "enum", values: ["running", "unknown"] },
  { key: "edr.version", section: "edr_agent", kind: "version" },
  { key: "edr.agent_started_at", section: "edr_agent", kind: "timestamp" },
  { key: "edr.engine_id", section: "edr_agent", kind: "text", pattern: /^[A-Za-z0-9][A-Za-z0-9._+\/ -]*$/, maxLength: 128 },
  { key: "edr.rule_file_present", section: "edr_agent", kind: "boolean", format: "v2" },
  { key: "edr.rule_set_state", section: "edr_agent", kind: "enum", values: RULE_SET_STATES, format: "v3" },
  { key: "edr.rule_set_id", section: "edr_agent", kind: "text", pattern: /^[a-f0-9]{64}$/, maxLength: 64, format: "v3" },
  { key: "edr.behavior_rules_version", section: "edr_agent", kind: "text", pattern: /^altay-behavior\/v[1-9][0-9]{0,5}$/,
    maxLength: 22, format: "v3" },
  { key: "edr.sensor_state", section: "edr_agent", kind: "enum", values: EDR_SENSOR_STATES },
  { key: "edr.sensor_error_code", section: "edr_agent", kind: "enum", values: SENSOR_ERROR_CODES },
  { key: "edr.service_config_state", section: "edr_agent", kind: "enum", values: SERVICE_CONFIG_STATES, format: "v3" },
  { key: "edr.previous_run_end", section: "edr_agent", kind: "enum", values: PREVIOUS_RUN_ENDS, format: "v3" },
  { key: "edr.heartbeat_interval_seconds", section: "edr_agent", kind: "number", minimum: 30, maximum: 3600, format: "v3" },
  { key: "edr.realtime_scan_state", section: "edr_agent", kind: "enum", values: CAPABILITY_STATES, format: "v3" },
  { key: "edr.file_change_sensor_state", section: "edr_agent", kind: "enum", values: CAPABILITY_STATES, format: "v3" },
  { key: "edr.command_line_sensor_state", section: "edr_agent", kind: "enum", values: CAPABILITY_STATES, format: "v3" },
  { key: "edr.persistence_watch_state", section: "edr_agent", kind: "enum", values: CAPABILITY_STATES, format: "v3" },
  { key: "edr.response_channel_state", section: "edr_agent", kind: "enum", values: RESPONSE_CHANNEL_STATES, format: "v3" },
  { key: "edr.last_action_seq", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.isolation_state", section: "edr_agent", kind: "enum", values: ISOLATION_STATES, format: "v3" },
  { key: "edr.isolation_until", section: "edr_agent", kind: "timestamp", deviceTime: true, format: "v3" },
  { key: "edr.isolation_checked_at", section: "edr_agent", kind: "timestamp", deviceTime: true, format: "v3" },
  { key: "edr.quarantine_items", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.events_queue_dropped", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.events_write_failed", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.events_unmapped", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.events_skipped", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.events_evicted", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.events_discarded", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.events_degraded", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.outbox_backlog", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE },
  { key: "edr.scans_completed", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.scans_detected", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.scans_no_verdict", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.scan_jobs_dropped", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.scan_cache_hits", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.etw_events_lost", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.file_change_gaps", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.cmdline_unavailable", section: "edr_agent", kind: "count", minimum: 0, maximum: SAFE, format: "v3" },
  { key: "edr.received_at", section: "edr_agent", kind: "timestamp" },
  { key: "edr.observed_at", section: "edr_agent", kind: "timestamp" },
  { key: "edr.source", section: "edr_agent", kind: "enum", values: ["self_reported"] },
  { key: "edr.verification", section: "edr_agent", kind: "enum", values: ["not_verified"] },
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
    case "number": return typeof value === "number" && Number.isSafeInteger(value) && value >= (spec.minimum ?? 0) && value <= (spec.maximum ?? 4096);
    case "text": return typeof value === "string" && spec.pattern !== undefined && value.length <= (spec.maxLength ?? 0) && spec.pattern.test(value);
    case "timestamp": try { const time = compareTimestamp(value); return spec.deviceTime !== true || inDeviceTimeWindow(time); } catch { return false; }
  }
}
/** The normalizer's window for a device time (normalize.ts windowTime): the years 1970 to 9998. */
function inDeviceTimeWindow(value: string): boolean {
  const year = Number(value.slice(0, 4));
  return year >= 1970 && year <= 9998;
}
/** The agent's Snapshot version as the console tells it (normalize.ts isEdrAgentStateV3): only V3 has a rule set state. */
export function agentFormat(fields: CompareFieldValues): AgentFormat | null {
  return fields["edr.status"] === null ? null : fields["edr.rule_set_state"] === null ? "v2" : "v3";
}
/** The Snapshot version that alone has this agent field; null for every other field. */
export function agentFieldFormat(key: CompareFieldKey): AgentFormat | null {
  const field: FieldSpec | undefined = COMPARE_FIELDS.find((item) => item.key === key);
  return field?.format ?? null;
}
/** The closed agent states each Snapshot version always reports (contracts.EdrAgentStatus, EdrAgentStatusV3). */
const AGENT_STATES: Readonly<Record<AgentFormat, readonly CompareFieldKey[]>> = {
  v2: ["edr.sensor_state"],
  v3: ["edr.sensor_state", "edr.rule_set_state", "edr.service_config_state", "edr.previous_run_end",
    "edr.realtime_scan_state", "edr.file_change_sensor_state", "edr.command_line_sensor_state",
    "edr.persistence_watch_state", "edr.response_channel_state", "edr.isolation_state"],
};
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
  for (const product of ["hbf", "termivar", "edr", "av"] as const) {
    if (fields[`${product}.status`] === null) compareRequire(COMPARE_FIELDS.filter((field) => field.key.startsWith(product + "."))
      .every((field) => fields[field.key] === null));
    else compareRequire(fields[`${product}.source`] === "self_reported" && fields[`${product}.verification`] === "not_verified"
      && fields[`${product}.received_at`] !== null && fields[`${product}.received_at`] === fields["device.received_at"]);
  }
  const format = agentFormat(fields);
  if (format !== null) {
    // The other Snapshot version's fields are absent, and a sensor error code comes only with a lost or failed sensor.
    compareRequire(COMPARE_FIELDS.every((field) => [null, format].includes(agentFieldFormat(field.key)) || fields[field.key] === null)
      && AGENT_STATES[format].every((key) => fields[key] !== null)
      && (fields["edr.sensor_error_code"] === null || fields["edr.sensor_state"] === "lost" || fields["edr.sensor_state"] === "failed"));
  }
  // Termivar's summary counts only; the agent's counters have their own rules above.
  const countKeys = COMPARE_FIELDS.filter((field) => field.section === "termivar" && field.kind === "count");
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
