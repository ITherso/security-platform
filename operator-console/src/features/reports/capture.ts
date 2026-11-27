/** Capture only an already displayed detail; never fetch or accept session data. */
import { CAPABILITY_STATES, EDR_SENSOR_STATES, EDR_V3_COUNTER_KEYS, ISOLATION_STATES, PREVIOUS_RUN_ENDS,
  RESPONSE_CHANNEL_STATES, RULE_SET_STATES, SENSOR_ERROR_CODES, SERVICE_CONFIG_STATES } from "../../data/contracts";
import type { AgeObservation, DeviceDetail, EdrAgentState, EdrV3CounterKey, ProductRecord } from "../../data/contracts";
import { isEdrAgentStateV3, normalizeDeviceDetail } from "../../data/normalize";
import { copyContext, freezeReport, REPORT_AGENT_V2_KEYS, REPORT_AGENT_V3_KEYS, REPORT_PRODUCT_IDS, ReportError,
  reportObject, reportRequire, reportText, reportTimestamp } from "./reportModel";
import type { ReportAgentMetricKey, ReportCommonFields, ReportContext, ReportMetric, ReportMetricKey, ReportProduct,
  ReportProductId, ReportRecord } from "./reportModel";

export interface CaptureMetadata { readonly context: ReportContext; readonly tenantName: string; readonly readAt: string }
/** The agent's list depends on its Snapshot version: REPORT_AGENT_V2_KEYS or REPORT_AGENT_V3_KEYS. */
const KEYS: Readonly<Record<Exclude<ReportProductId, "edr_agent">, readonly ReportMetricKey[]>> = {
  hostbasedfirewall: ["installed", "reported_running", "reported_stale", "firewall_mode"],
  termivar: ["scanner_installed", "execution_available", "report_presence", "subject_count", "item_count", "informational",
    "needs_review", "confirmed", "unassigned", "info", "low", "medium", "high", "critical"],
  antivirus: ["availability", "execution_available"],
};
const STATUSES: Readonly<Record<ReportProductId, readonly string[]>> = {
  hostbasedfirewall: ["running", "observing", "degraded", "stopped", "unavailable", "unknown"],
  termivar: ["experimental", "unknown"], antivirus: ["planned", "unknown"], edr_agent: ["running", "unknown"],
};
type MetricCheck = (value: unknown) => boolean;
const optional = (check: MetricCheck): MetricCheck => (value) => value === null || check(value);
const member = (values: readonly string[]): MetricCheck => (value) => typeof value === "string" && values.includes(value);
const safeCount: MetricCheck = (value) => typeof value === "number" && Number.isSafeInteger(value) && value >= 0;
const time: MetricCheck = (value) => { try { reportTimestamp(value); return true; } catch { return false; } };
/** A device time in the normalizer's window (normalize.ts windowTime), the years 1970 to 9998: isolation_until and
 * isolation_checked_at. */
const deviceTime: MetricCheck = (value) => {
  try { const year = Number(reportTimestamp(value).slice(0, 4)); return year >= 1970 && year <= 9998; } catch { return false; }
};
const COUNTER_CHECKS = Object.fromEntries(EDR_V3_COUNTER_KEYS.map((key) => [key, optional(safeCount)])) as
  Readonly<Record<EdrV3CounterKey, MetricCheck>>;
/** The agent's values within the normalizer's bounds (normalize.ts edrAgentState and edrAgentStateV3): the closed
 * states never null, the engine and version texts by the Platform's patterns, counters as safe integers or null, and
 * the isolation times in its device-time window. */
const AGENT_CHECKS: Readonly<Record<ReportAgentMetricKey, MetricCheck>> = {
  ...COUNTER_CHECKS,
  agent_started_at: optional(time),
  engine_id: optional((value) => typeof value === "string" && value.length <= 128 && /^[A-Za-z0-9][A-Za-z0-9._+\/ -]*$/.test(value)),
  rule_file_present: optional((value) => typeof value === "boolean"),
  sensor_state: member(EDR_SENSOR_STATES),
  sensor_error_code: optional(member(SENSOR_ERROR_CODES)),
  rule_set_state: member(RULE_SET_STATES),
  rule_set_id: optional((value) => typeof value === "string" && /^[a-f0-9]{64}$/.test(value)),
  behavior_rules_version: optional((value) => typeof value === "string" && /^altay-behavior\/v[1-9][0-9]{0,5}$/.test(value)),
  service_config_state: member(SERVICE_CONFIG_STATES),
  previous_run_end: member(PREVIOUS_RUN_ENDS),
  heartbeat_interval_seconds: optional((value) => typeof value === "number" && Number.isSafeInteger(value)
    && value >= 30 && value <= 3600),
  realtime_scan_state: member(CAPABILITY_STATES), file_change_sensor_state: member(CAPABILITY_STATES),
  command_line_sensor_state: member(CAPABILITY_STATES), persistence_watch_state: member(CAPABILITY_STATES),
  response_channel_state: member(RESPONSE_CHANNEL_STATES),
  last_action_seq: optional(safeCount),
  isolation_state: member(ISOLATION_STATES),
  isolation_until: optional(deviceTime), isolation_checked_at: optional(deviceTime),
  quarantine_items: optional(safeCount),
};
function isAgentMetricKey(key: ReportMetricKey): key is ReportAgentMetricKey { return Object.hasOwn(AGENT_CHECKS, key); }
/** A missing agent has no metrics: which Snapshot version it would have reported is not known. */
function agentKeys(input: ReportProduct): readonly ReportMetricKey[] {
  if (input.presence !== "reported" || !Array.isArray(input.metrics)) return [];
  return input.metrics.length === REPORT_AGENT_V3_KEYS.length ? REPORT_AGENT_V3_KEYS : REPORT_AGENT_V2_KEYS;
}
const COMMON_KEYS = ["identityStatus", "connectionStatus", "revokedAt", "sourceObservedAt", "receivedAt", "readAt",
  "sourceObservation", "source", "producerVerification", "products"];
function metric(key: ReportMetricKey, value: ReportMetric["value"]): ReportMetric {
  return { key, value };
}
function copyAge(value: AgeObservation): AgeObservation {
  const age = reportObject(value, ["age_seconds", "clock_state"]);
  reportRequire(age.clock_state === "unknown" || age.clock_state === "future" || age.clock_state === "not_verified");
  reportRequire(age.clock_state === "not_verified" ? typeof age.age_seconds === "number"
    && Number.isSafeInteger(age.age_seconds) && age.age_seconds >= 0 : age.age_seconds === null);
  return { age_seconds: age.age_seconds as number | null, clock_state: age.clock_state };
}
function nullableTime(value: string | null): string | null { return value === null ? null : reportTimestamp(value); }
function productFromDetail(id: ReportProductId, entry: ProductRecord | undefined): ReportProduct {
  if (!entry) return { product: id, presence: "missing", status: null, version: null,
    sourceObservedAt: null, receivedAt: null, observation: null, reportImportedAt: null, reportImportAge: null,
    source: null, producerVerification: null, metrics: id === "edr_agent" ? [] : KEYS[id].map((key) => metric(key, null)) };
  const state = entry.state;
  const common = { product: id, presence: "reported" as const, status: state.status, version: state.version,
    sourceObservedAt: state.source_observed_at, receivedAt: entry.received_at, observation: copyAge(entry.observation),
    source: "self_reported" as const, producerVerification: "not_verified" as const };
  if (entry.product_id === "hostbasedfirewall") return { ...common, reportImportedAt: null, reportImportAge: null,
    metrics: [metric("installed", entry.state.installed), metric("reported_running", entry.state.reported_running),
      metric("reported_stale", entry.state.reported_stale), metric("firewall_mode", entry.state.firewall_mode)] };
  if (entry.product_id === "termivar") {
    const summary = entry.state.latest_report;
    return { ...common, reportImportedAt: summary?.imported_at ?? null, reportImportAge: copyAge(entry.report_import_age),
      metrics: [metric("scanner_installed", entry.state.scanner_installed), metric("execution_available", entry.state.execution_available),
        metric("report_presence", entry.state.report_presence), metric("subject_count", summary?.subject_count ?? null),
        metric("item_count", summary?.item_count ?? null), metric("informational", summary?.counts.informational ?? null),
        metric("needs_review", summary?.counts.needs_review ?? null), metric("confirmed", summary?.counts.confirmed ?? null),
        metric("unassigned", summary?.severity_counts.unassigned ?? null), metric("info", summary?.severity_counts.info ?? null),
        metric("low", summary?.severity_counts.low ?? null), metric("medium", summary?.severity_counts.medium ?? null),
        metric("high", summary?.severity_counts.high ?? null), metric("critical", summary?.severity_counts.critical ?? null)] };
  }
  if (entry.product_id === "edr_agent") {
    // Each value is the agent's own claim; V3 is told from V2 by its key set, as the device-detail card does.
    const agent = entry.state;
    if (isEdrAgentStateV3(agent)) return { ...common, reportImportedAt: null, reportImportAge: null,
      metrics: REPORT_AGENT_V3_KEYS.map((key) => metric(key, agent[key])) };
    const v2: EdrAgentState = agent;
    return { ...common, reportImportedAt: null, reportImportAge: null,
      metrics: REPORT_AGENT_V2_KEYS.map((key) => metric(key, v2[key])) };
  }
  reportRequire(entry.product_id === "antivirus");
  return { ...common, reportImportedAt: null, reportImportAge: null,
    metrics: [metric("availability", entry.state.availability), metric("execution_available", entry.state.execution_available)] };
}

/** Closed copy also used by pure draft mutations; no caller-owned references. */
function copyProduct(input: ReportProduct, expected: ReportProductId): ReportProduct {
  reportObject(input, ["product", "presence", "status", "version", "sourceObservedAt", "receivedAt", "observation",
    "reportImportedAt", "reportImportAge", "source", "producerVerification", "metrics"]);
  reportRequire(input.product === expected && (input.presence === "reported" || input.presence === "missing"));
  reportRequire(input.status === null || STATUSES[expected].includes(input.status));
  reportRequire(input.version === null || (typeof input.version === "string" && input.version.length <= 64
    && /^[A-Za-z0-9][A-Za-z0-9._+\-]*$/.test(input.version)));
  const keys = expected === "edr_agent" ? agentKeys(input) : KEYS[expected];
  reportRequire(Array.isArray(input.metrics) && input.metrics.length === keys.length);
  const metrics = input.metrics.map((row, index): ReportMetric => {
    reportObject(row, ["key", "value"]);
    const key = keys[index];
    reportRequire(key !== undefined && row.key === key);
    const value = row.value;
    if (isAgentMetricKey(key)) reportRequire(AGENT_CHECKS[key](value));
    else if (["installed", "reported_running", "reported_stale", "scanner_installed"].includes(key))
      reportRequire(value === null || typeof value === "boolean");
    else if (key === "execution_available") reportRequire(value === null || value === false);
    else if (key === "firewall_mode") reportRequire(value === null || (typeof value === "string" && ["enforce", "sniff", "unknown"].includes(value)));
    else if (key === "report_presence") reportRequire(value === null || (typeof value === "string" && ["present", "none", "unknown"].includes(value)));
    else if (key === "availability") reportRequire(value === null || (typeof value === "string" && ["unavailable", "unknown"].includes(value)));
    else reportRequire(value === null || (typeof value === "number" && Number.isSafeInteger(value)
      && value >= (key === "subject_count" ? 1 : 0) && value <= (key === "subject_count" ? 1024 : 4096)));
    return metric(key, value);
  });
  const missing = input.presence === "missing";
  reportRequire(missing ? input.status === null && input.version === null && input.source === null && input.producerVerification === null
    && input.sourceObservedAt === null && input.receivedAt === null && input.observation === null
    && input.reportImportedAt === null && input.reportImportAge === null && metrics.every((row) => row.value === null)
    : input.status !== null && input.source === "self_reported" && input.producerVerification === "not_verified"
      && input.receivedAt !== null && input.observation !== null);
  reportRequire(expected === "termivar" || (input.reportImportedAt === null && input.reportImportAge === null));
  reportRequire(expected !== "antivirus" || input.version === null);
  // As normalize.ts: a sensor error code only with a lost or failed sensor.
  const sensor = metrics.find((row) => row.key === "sensor_state")?.value;
  const code = metrics.find((row) => row.key === "sensor_error_code")?.value ?? null;
  reportRequire(code === null || sensor === "lost" || sensor === "failed");
  return { product: expected, presence: input.presence, status: input.status, version: input.version,
    sourceObservedAt: nullableTime(input.sourceObservedAt), receivedAt: nullableTime(input.receivedAt),
    observation: input.observation === null ? null : copyAge(input.observation), reportImportedAt: nullableTime(input.reportImportedAt),
    reportImportAge: input.reportImportAge === null ? null : copyAge(input.reportImportAge),
    source: missing ? null : "self_reported", producerVerification: missing ? null : "not_verified", metrics };
}
export function copyCommonFields(input: ReportCommonFields): ReportCommonFields {
  reportRequire((input.identityStatus === "active" || input.identityStatus === "revoked")
    && ["recent", "stale", "never_seen"].includes(input.connectionStatus)
    && input.source === "self_reported" && input.producerVerification === "not_verified"
    && (input.identityStatus === "revoked") === (input.revokedAt !== null)
    && (input.connectionStatus === "never_seen") === (input.receivedAt === null)
    && Array.isArray(input.products) && input.products.length === REPORT_PRODUCT_IDS.length);
  const products = REPORT_PRODUCT_IDS.map((id, index) => {
    const value = input.products[index]; reportRequire(value !== undefined);
    const product = copyProduct(value, id);
    reportRequire(product.presence === "missing" || product.receivedAt === input.receivedAt);
    return product;
  });
  return { identityStatus: input.identityStatus, connectionStatus: input.connectionStatus, revokedAt: nullableTime(input.revokedAt),
    sourceObservedAt: nullableTime(input.sourceObservedAt), receivedAt: nullableTime(input.receivedAt), readAt: reportTimestamp(input.readAt),
    sourceObservation: copyAge(input.sourceObservation), source: "self_reported", producerVerification: "not_verified", products };
}
export function copyReportRecord(input: ReportRecord): ReportRecord {
  reportObject(input, ["context", "tenantName", "deviceId", "deviceName", ...COMMON_KEYS]);
  const context = copyContext(input.context);
  reportRequire(typeof input.deviceId === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(input.deviceId));
  const fields = copyCommonFields(input);
  return freezeReport({ context, tenantName: reportText(input.tenantName, 120), deviceId: input.deviceId,
    deviceName: reportText(input.deviceName, 80), ...fields });
}

export function captureRecord(detail: DeviceDetail, metadata: CaptureMetadata): ReportRecord {
  try {
    reportObject(metadata, ["context", "tenantName", "readAt"]);
    const context = copyContext(metadata.context);
    // Reuse the actual runtime validator, not a TypeScript assertion of JSON.
    const source = normalizeDeviceDetail(detail, context.tenantId, detail.id);
    const record: ReportRecord = { context, tenantName: reportText(metadata.tenantName, 120), deviceId: source.id,
      deviceName: source.label, identityStatus: source.identity_status, connectionStatus: source.connection_status,
      revokedAt: source.revoked_at, sourceObservedAt: source.source_observed_at, receivedAt: source.last_received_at,
      readAt: reportTimestamp(metadata.readAt), sourceObservation: copyAge(source.source_observation),
      source: "self_reported", producerVerification: "not_verified",
      products: REPORT_PRODUCT_IDS.map((id) => productFromDetail(id, source.products.find((entry) => entry.product_id === id))) };
    return copyReportRecord(record);
  } catch { throw new ReportError("invalid_report"); }
}
