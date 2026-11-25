/** Closed runtime validation shared by fixtures and the real GET adapter. */
import { ALERT_RULES, ALERT_STATUSES, ClientError, EDR_COUNTER_KEYS, EDR_SENSOR_STATES, HBF_ERROR_CODES, PRODUCT_IDS,
  SENSOR_ERROR_CODES, SENSOR_STATES } from "./contracts";
import type { AgeObservation, Alert, AlertCursor, AlertPage, AlertRule, AlertSeverity, AlertStatus, AuditAction,
  AuditEvent, AuditObject, ClientErrorCode, Device, DeviceDetail, DispositionCounts, EdrAgentState, EdrCounterKey, Page,
  ProductId, ProductRecord, ProductState, SeverityCounts, SourceClaims, Tenant, TermivarSummary, TimelineEvent,
  TimelinePage } from "./contracts";

const CLAIM_KEYS = ["source", "producer_verification"];
const DEVICE_KEYS = ["id", "tenant_id", "label", "identity_status", "connection_status", "created_at", "revoked_at",
  "last_sequence", "last_received_at", "source_observed_at", "source_observation", ...CLAIM_KEYS];
const PRODUCT_KEYS = ["product_id", "catalog_available", ...CLAIM_KEYS, "version", "source_observed_at"];
/** The product-specific keys of each state; with PRODUCT_KEYS the exact key set of contracts.py's DTOs. */
const PRODUCT_STATE_KEYS: Readonly<Record<ProductId, readonly string[]>> = {
  hostbasedfirewall: ["status", "installed", "reported_running", "reported_stale", "firewall_mode", "error_codes"],
  termivar: ["status", "scanner_installed", "execution_available", "report_presence", "latest_report"],
  antivirus: ["status", "availability", "execution_available"],
  edr_agent: ["status", "agent_started_at", "engine_id", "rule_file_present", "sensor_state", "sensor_error_code",
    ...EDR_COUNTER_KEYS],
};
/** contracts.VersionText and contracts.EngineText (ASCII only). */
const VERSION_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._+\-]*$/;
const ENGINE_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._+\/ -]*$/;
const AUDIT_OBJECTS: Readonly<Record<AuditAction, AuditObject>> = {
  tenant_created: "tenant", membership_set: "membership", membership_revoked: "membership",
  enrollment_grant_created: "enrollment_grant", enrollment_grant_revoked: "enrollment_grant",
  device_enrolled: "device", device_revoked: "device", device_credential_rotated: "device_credential",
  tenant_event_retention_set: "tenant", alert_acknowledged: "alert", alert_closed: "alert",
};

export function requireValue(ok: unknown, code: ClientErrorCode = "malformed"): asserts ok {
  if (!ok) throw new ClientError(code);
}
function shape(input: unknown, keys: readonly string[]): Record<string, unknown> {
  requireValue(input !== null && typeof input === "object" && !Array.isArray(input));
  const value = input as Record<string, unknown>;
  const actual = Object.keys(value);
  requireValue(actual.length === keys.length && actual.every((key) => keys.includes(key))
    && keys.every((key) => Object.prototype.hasOwnProperty.call(value, key)));
  return value;
}
function text(value: unknown, maximum: number, minimum = 1): string {
  requireValue(typeof value === "string" && value.length <= maximum * 2 && [...value].length <= maximum
    && [...value].length >= minimum && !/[\u0000-\u001f]/.test(value));
  return value;
}
export function identifier(value: unknown, code: ClientErrorCode = "malformed"): string {
  requireValue(typeof value === "string" && /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(value), code);
  return value;
}
function integer(value: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): number {
  requireValue(typeof value === "number" && Number.isSafeInteger(value) && value >= minimum && value <= maximum);
  return value;
}
function choice<const T extends readonly string[]>(value: unknown, values: T): T[number] {
  requireValue(typeof value === "string" && values.some((allowed) => allowed === value));
  return value as T[number];
}
function nullableBoolean(value: unknown): boolean | null {
  requireValue(value === null || typeof value === "boolean");
  return value;
}
function unavailableExecution(value: unknown): false | null {
  requireValue(value === null || value === false);
  return value;
}
function timestamp(value: unknown): string;
function timestamp(value: unknown, nullable: true): string | null;
function timestamp(value: unknown, nullable = false): string | null {
  if (value === null && nullable) return null;
  requireValue(typeof value === "string" && value.length <= 32);
  const match = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.\d{1,6})?Z$/.exec(value);
  requireValue(match !== null);
  const year = Number(match[1]), month = Number(match[2]), day = Number(match[3]);
  const hour = Number(match[4]), minute = Number(match[5]), second = Number(match[6]);
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(hour, minute, second, 0);
  requireValue(year >= 1 && date.getUTCFullYear() === year && date.getUTCMonth() === month - 1
    && date.getUTCDate() === day && date.getUTCHours() === hour && date.getUTCMinutes() === minute && date.getUTCSeconds() === second);
  return value;
}
function claims(value: Record<string, unknown>): SourceClaims {
  requireValue(value.source === "self_reported" && value.producer_verification === "not_verified");
  return { source: "self_reported", producer_verification: "not_verified" };
}
function array<T>(value: unknown, maximum: number, map: (item: unknown) => T): T[] {
  requireValue(Array.isArray(value) && value.length <= maximum);
  return (value as unknown[]).map(map);
}
function unique<T>(values: T[]): T[] {
  requireValue(new Set(values).size === values.length);
  return values;
}
function age(input: unknown, observed?: string | null): AgeObservation {
  const value = shape(input, ["age_seconds", "clock_state"]);
  const state = choice(value.clock_state, ["unknown", "future", "not_verified"]);
  const seconds = value.age_seconds === null ? null : integer(value.age_seconds);
  requireValue(state === "not_verified" ? seconds !== null : seconds === null);
  if (observed !== undefined) requireValue(observed === null ? state === "unknown" : state !== "unknown");
  return { age_seconds: seconds, clock_state: state };
}
function tenant(input: unknown): Tenant {
  const value = shape(input, ["id", "name", "role"]);
  return { id: identifier(value.id), name: text(value.name, 120), role: choice(value.role, ["tenant_admin", "viewer"]) };
}
function device(input: unknown, tenantId: string, detail = false): Device {
  const value = shape(input, detail ? [...DEVICE_KEYS, "products", "missing_products"] : DEVICE_KEYS);
  const observed = timestamp(value.source_observed_at, true);
  const result: Device = { id: identifier(value.id), tenant_id: identifier(value.tenant_id), label: text(value.label, 80),
    identity_status: choice(value.identity_status, ["active", "revoked"]),
    connection_status: choice(value.connection_status, ["recent", "stale", "never_seen"]),
    created_at: timestamp(value.created_at), revoked_at: timestamp(value.revoked_at, true),
    last_sequence: value.last_sequence === null ? null : integer(value.last_sequence, 1),
    last_received_at: timestamp(value.last_received_at, true), source_observed_at: observed,
    source_observation: age(value.source_observation, observed), ...claims(value) };
  requireValue(result.tenant_id === tenantId && (result.identity_status === "revoked") === (result.revoked_at !== null)
    && (result.last_sequence === null) === (result.last_received_at === null)
    && (result.connection_status === "never_seen") === (result.last_received_at === null)
    && (result.last_sequence !== null || result.source_observed_at === null));
  return result;
}
function report(input: unknown): TermivarSummary {
  const value = shape(input, ["digest", "report_schema", "imported_at", "subject_count", "item_count", "counts",
    "severity_counts", ...CLAIM_KEYS, "scope"]);
  requireValue(typeof value.digest === "string" && /^[a-f0-9]{64}$/.test(value.digest)
    && value.report_schema === "venom-rendered-assessment/v1" && value.scope === "offline_report_summary");
  const rawCounts = shape(value.counts, ["informational", "needs_review", "confirmed"]);
  const rawSeverity = shape(value.severity_counts, ["unassigned", "info", "low", "medium", "high", "critical"]);
  const counts: DispositionCounts = { informational: integer(rawCounts.informational, 0, 4096),
    needs_review: integer(rawCounts.needs_review, 0, 4096), confirmed: integer(rawCounts.confirmed, 0, 4096) };
  const severities: SeverityCounts = { unassigned: integer(rawSeverity.unassigned, 0, 4096), info: integer(rawSeverity.info, 0, 4096),
    low: integer(rawSeverity.low, 0, 4096), medium: integer(rawSeverity.medium, 0, 4096),
    high: integer(rawSeverity.high, 0, 4096), critical: integer(rawSeverity.critical, 0, 4096) };
  const count = integer(value.item_count, 0, 4096);
  requireValue(Object.values(counts).reduce((a: number, b: number) => a + b, 0) === count
    && Object.values(severities).reduce((a: number, b: number) => a + b, 0) === count);
  return { digest: value.digest, report_schema: "venom-rendered-assessment/v1", imported_at: timestamp(value.imported_at),
    subject_count: integer(value.subject_count, 1, 1024), item_count: count, counts, severity_counts: severities,
    ...claims(value), scope: "offline_report_summary" };
}
/** The agent's own status: exact keys, nullability, safe integers, a code only with lost or failed. */
function edrAgentState(value: Record<string, unknown>, common: { readonly catalog_available: boolean | null;
  readonly source: "self_reported"; readonly producer_verification: "not_verified"; readonly version: string | null;
  readonly source_observed_at: string | null }): EdrAgentState {
  // The agent makes no catalog claim (contracts.EdrAgentStatus).
  requireValue(common.catalog_available === null);
  const engine = value.engine_id === null ? null : text(value.engine_id, 128);
  requireValue(engine === null || ENGINE_PATTERN.test(engine));
  const sensor = choice(value.sensor_state, EDR_SENSOR_STATES);
  const code = value.sensor_error_code === null ? null : choice(value.sensor_error_code, SENSOR_ERROR_CODES);
  requireValue(code === null || sensor === "lost" || sensor === "failed");
  const counters = Object.fromEntries(EDR_COUNTER_KEYS.map((key) =>
    [key, value[key] === null ? null : integer(value[key])])) as { readonly [K in EdrCounterKey]: number | null };
  return { ...common, ...counters, product_id: "edr_agent", catalog_available: null,
    status: choice(value.status, ["running", "unknown"]), agent_started_at: timestamp(value.agent_started_at, true),
    engine_id: engine, rule_file_present: nullableBoolean(value.rule_file_present), sensor_state: sensor,
    sensor_error_code: code };
}
function productState(input: unknown, id: ProductId): ProductState {
  const value = shape(input, [...PRODUCT_KEYS, ...PRODUCT_STATE_KEYS[id]]);
  requireValue(value.product_id === id);
  const version = value.version === null ? null : text(value.version, 64);
  requireValue(version === null || VERSION_PATTERN.test(version));
  const common = { catalog_available: nullableBoolean(value.catalog_available), ...claims(value),
    version, source_observed_at: timestamp(value.source_observed_at, true) };
  if (id === "edr_agent") return edrAgentState(value, common);
  if (id === "hostbasedfirewall") return { ...common, product_id: id,
    status: choice(value.status, ["running", "observing", "degraded", "stopped", "unavailable", "unknown"]),
    installed: nullableBoolean(value.installed), reported_running: nullableBoolean(value.reported_running),
    reported_stale: nullableBoolean(value.reported_stale), firewall_mode: choice(value.firewall_mode, ["enforce", "sniff", "unknown"]),
    error_codes: value.error_codes === null ? null : unique(array(value.error_codes, 16, (code) => choice(code, HBF_ERROR_CODES))) };
  if (id === "termivar") {
    const presence = choice(value.report_presence, ["present", "none", "unknown"]);
    const latest = value.latest_report === null ? null : report(value.latest_report);
    requireValue((presence === "present") === (latest !== null));
    return { ...common, product_id: id, status: choice(value.status, ["experimental", "unknown"]),
      scanner_installed: nullableBoolean(value.scanner_installed), execution_available: unavailableExecution(value.execution_available),
      report_presence: presence, latest_report: latest };
  }
  requireValue(common.catalog_available !== true && common.version === null);
  return { ...common, product_id: id, catalog_available: common.catalog_available, version: null,
    status: choice(value.status, ["planned", "unknown"]), availability: choice(value.availability, ["unavailable", "unknown"]),
    execution_available: unavailableExecution(value.execution_available) };
}
export function normalizeDeviceDetail(input: unknown, tenantId: string, deviceId: string): DeviceDetail {
  const base = device(input, tenantId, true);
  const value = input as Record<string, unknown>; // device() checked this exact shape above.
  requireValue(base.id === deviceId);
  const products = array<ProductRecord>(value.products, PRODUCT_IDS.length, (raw) => {
    requireValue(raw !== null && typeof raw === "object" && !Array.isArray(raw));
    const initial = raw as Record<string, unknown>;
    const id = choice(initial.product_id, PRODUCT_IDS);
    const entry = shape(raw, ["product_id", "snapshot_sequence", "received_at", "observation", "state",
      ...(id === "termivar" ? ["report_import_age"] : [])]);
    const state = productState(entry.state, id);
    const common = { snapshot_sequence: integer(entry.snapshot_sequence, 1), received_at: timestamp(entry.received_at),
      observation: age(entry.observation, state.source_observed_at) };
    requireValue(common.snapshot_sequence === base.last_sequence && common.received_at === base.last_received_at);
    if (state.product_id === "termivar") return { ...common, product_id: state.product_id, state,
      report_import_age: age(entry.report_import_age, state.latest_report?.imported_at ?? null) };
    if (state.product_id === "hostbasedfirewall") return { ...common, product_id: state.product_id, state };
    if (state.product_id === "edr_agent") return { ...common, product_id: state.product_id, state };
    return { ...common, product_id: state.product_id, state };
  });
  const present = unique(products.map((entry) => entry.product_id));
  const missing = unique(array(value.missing_products, PRODUCT_IDS.length, (id) => choice(id, PRODUCT_IDS)));
  requireValue(PRODUCT_IDS.every((id) => present.includes(id) !== missing.includes(id)));
  return { ...base, products, missing_products: missing };
}
function auditEvent(input: unknown, tenantId: string): AuditEvent {
  const value = shape(input, ["id", "tenant_id", "actor_type", "actor_id", "action", "object_type", "object_id", "outcome", "created_at"]);
  const action = choice(value.action, Object.keys(AUDIT_OBJECTS) as AuditAction[]);
  requireValue(value.tenant_id === tenantId && AUDIT_OBJECTS[action] === value.object_type && value.outcome === "success");
  return { id: identifier(value.id), tenant_id: identifier(value.tenant_id),
    actor_type: choice(value.actor_type, ["operator", "device", "local_admin"]),
    actor_id: value.actor_id === null ? null : identifier(value.actor_id), action, object_type: AUDIT_OBJECTS[action],
    object_id: identifier(value.object_id), outcome: "success", created_at: timestamp(value.created_at) };
}
interface Pagination { readonly limit: number; readonly offset: number }
function page<T extends { readonly id: string }>(input: unknown, options: Pagination, map: (item: unknown) => T): Page<T> {
  const value = shape(input, ["items", "next_offset"]);
  const items = array(value.items, options.limit, map);
  unique(items.map((item) => item.id));
  const next = value.next_offset === null ? null : integer(value.next_offset, 0, 10100);
  requireValue(next === null || (next === options.offset + options.limit && items.length === options.limit));
  return { items, next_offset: next };
}
export const normalizeTenantPage = (input: unknown, options: Pagination): Page<Tenant> => page(input, options, tenant);
export const normalizeDevicePage = (input: unknown, options: Pagination, tenantId: string): Page<Device> =>
  page(input, options, (value) => device(value, tenantId));
export const normalizeAuditPage = (input: unknown, options: Pagination, tenantId: string): Page<AuditEvent> =>
  page(input, options, (value) => auditEvent(value, tenantId));

const UINT32_MAX = 4294967295;
const EVENT_KINDS = ["process_started", "process_stopped", "sensor_state"] as const;
const EVENT_KEYS: Readonly<Record<TimelineEvent["kind"], readonly string[]>> = {
  process_started: ["pid", "parent_pid", "session_id", "image"],
  process_stopped: ["pid", "exit_code", "image"],
  sensor_state: ["state", "error_code"],
};
const ALERT_KEYS = ["id", "device_id", "rule", "severity", "status", "occurrences", "first_event_seq", "last_event_seq",
  "first_seen_at", "last_seen_at", "evidence", "acknowledged_at", "closed_at", ...CLAIM_KEYS];
/** Rule codes and severities are fixed together by the Platform. */
const ALERT_SEVERITY: Readonly<Record<AlertRule, AlertSeverity>> = {
  user_writable_launch: "low", office_browser_spawned_tool: "medium", sensor_unstable: "medium", event_loss: "medium",
};
// The Unicode 16.0.0 Cc/Cf code points the Platform refuses in event text, as inclusive ranges; the same
// numbers as event_contracts.REFUSED_TEXT_RANGES. Unpaired surrogates are refused too. Bidirectional
// overrides or zero-width marks never reach the screen.
const REFUSED_TEXT_RANGES: readonly (readonly [number, number])[] = [
  [0x0000, 0x001f], [0x007f, 0x009f], [0x00ad, 0x00ad], [0x0600, 0x0605], [0x061c, 0x061c], [0x06dd, 0x06dd],
  [0x070f, 0x070f], [0x0890, 0x0891], [0x08e2, 0x08e2], [0x180e, 0x180e], [0x200b, 0x200f], [0x202a, 0x202e],
  [0x2060, 0x2064], [0x2066, 0x206f], [0xfeff, 0xfeff], [0xfff9, 0xfffb], [0x110bd, 0x110bd], [0x110cd, 0x110cd],
  [0x13430, 0x1343f], [0x1bca0, 0x1bca3], [0x1d173, 0x1d17a], [0xe0001, 0xe0001], [0xe0020, 0xe007f],
];

function eventText(value: unknown, maximum: number): string {
  const result = text(value, maximum);
  for (const character of result) {
    const point = character.codePointAt(0) ?? 0;
    requireValue(!(point >= 0xd800 && point <= 0xdfff)
      && !REFUSED_TEXT_RANGES.some(([first, last]) => point >= first && point <= last));
  }
  return result;
}
/** event_contracts.masked_image_path: after every non-final `Users` component comes `*` (before its first `:`). */
function maskedImage(value: unknown): string {
  const image = eventText(value, 1024);
  const parts = image.replace(/\//g, "\\").split("\\");
  parts.slice(0, -1).forEach((part, index) => {
    if (/^[\x00-\x7f]*$/.test(part) && part.toLowerCase() === "users") {
      requireValue((parts[index + 1] ?? "").split(":")[0] === "*");
    }
  });
  return image;
}
/** process_stopped.image: the kernel's short name, never a path. */
function shortImage(value: unknown): string {
  const image = eventText(value, 260);
  requireValue(!image.includes("\\") && !image.includes("/"));
  return image;
}
function processId(value: unknown): number {
  return integer(value, 0, UINT32_MAX);
}
function timelineEvent(input: unknown): TimelineEvent {
  requireValue(input !== null && typeof input === "object" && !Array.isArray(input));
  const kind = choice((input as Record<string, unknown>).kind, EVENT_KINDS);
  const value = shape(input, ["event_seq", "kind", "observed_at", "received_at", ...EVENT_KEYS[kind], ...CLAIM_KEYS]);
  const common = { event_seq: integer(value.event_seq, 1), observed_at: timestamp(value.observed_at),
    received_at: timestamp(value.received_at), ...claims(value) };
  if (kind === "process_started") return { ...common, kind, pid: processId(value.pid), parent_pid: processId(value.parent_pid),
    session_id: processId(value.session_id), image: maskedImage(value.image) };
  if (kind === "process_stopped") return { ...common, kind, pid: processId(value.pid),
    exit_code: value.exit_code === null ? null : processId(value.exit_code),
    image: value.image === null ? null : shortImage(value.image) };
  const state = choice(value.state, SENSOR_STATES);
  const errorCode = value.error_code === null ? null : choice(value.error_code, SENSOR_ERROR_CODES);
  requireValue(errorCode === null || state === "lost" || state === "failed");
  return { ...common, kind, state, error_code: errorCode };
}
interface TimelineQuery { readonly limit: number; readonly beforeSeq: number | null }
/** Newest first, strictly below `before_seq`; next_before_seq is the last item's sequence on a full page. */
export function normalizeTimelinePage(input: unknown, query: TimelineQuery): TimelinePage {
  const value = shape(input, ["items", "next_before_seq", "cap_deleted_events", "suppressed_alerts"]);
  const items = array(value.items, query.limit, timelineEvent);
  let newer = query.beforeSeq;
  for (const item of items) {
    requireValue(newer === null || item.event_seq < newer);
    newer = item.event_seq;
  }
  const last = items[items.length - 1];
  const next = value.next_before_seq === null ? null : integer(value.next_before_seq, 1);
  requireValue(next === null || (items.length === query.limit && last !== undefined && next === last.event_seq));
  return { items, next_before_seq: next, cap_deleted_events: integer(value.cap_deleted_events),
    suppressed_alerts: integer(value.suppressed_alerts) };
}

/** Fixed-width UTC text with six fraction digits; string order equals instant order. */
export function utcSortKey(value: string): string {
  return value.replace(/(?:\.(\d{1,6}))?Z$/, (_match, fraction: string | undefined) => `.${(fraction ?? "").padEnd(6, "0")}Z`);
}
/** The list order (last_seen_at DESC, id DESC) as one comparable string. */
export function alertOrderKey(seenAt: string, id: string): string {
  return `${utcSortKey(seenAt)} ${id}`;
}
export function isAlertStatus(value: unknown): value is AlertStatus {
  return typeof value === "string" && ALERT_STATUSES.some((status) => status === value);
}
export function alertCursor(input: unknown, code: ClientErrorCode = "malformed"): AlertCursor {
  try {
    const value = shape(input, ["seen_at", "id"]);
    return { seen_at: timestamp(value.seen_at), id: identifier(value.id) };
  } catch { throw new ClientError(code); }
}
function alert(input: unknown): Alert {
  const value = shape(input, ALERT_KEYS);
  const rule = choice(value.rule, ALERT_RULES);
  requireValue(value.severity === ALERT_SEVERITY[rule]);
  const status = choice(value.status, ALERT_STATUSES);
  const acknowledgedAt = timestamp(value.acknowledged_at, true), closedAt = timestamp(value.closed_at, true);
  // open -> acknowledged -> closed, or open -> closed; a closed alert never reopens.
  requireValue((status === "closed") === (closedAt !== null) && (status !== "open" || acknowledgedAt === null)
    && (status !== "acknowledged" || acknowledgedAt !== null));
  const firstSeq = integer(value.first_event_seq, 1), lastSeq = integer(value.last_event_seq, 1);
  requireValue(firstSeq <= lastSeq);
  const common = { id: identifier(value.id), device_id: identifier(value.device_id), status,
    occurrences: integer(value.occurrences, 1), first_event_seq: firstSeq, last_event_seq: lastSeq,
    first_seen_at: timestamp(value.first_seen_at), last_seen_at: timestamp(value.last_seen_at),
    acknowledged_at: acknowledgedAt, closed_at: closedAt, ...claims(value) };
  if (rule === "user_writable_launch") {
    const evidence = shape(value.evidence, ["image", "pid"]);
    return { ...common, rule, severity: "low", evidence: { image: maskedImage(evidence.image), pid: processId(evidence.pid) } };
  }
  if (rule === "office_browser_spawned_tool") {
    const evidence = shape(value.evidence, ["image", "pid", "parent_image", "parent_pid"]);
    return { ...common, rule, severity: "medium", evidence: { image: maskedImage(evidence.image), pid: processId(evidence.pid),
      parent_image: maskedImage(evidence.parent_image), parent_pid: processId(evidence.parent_pid) } };
  }
  if (rule === "sensor_unstable") {
    const evidence = shape(value.evidence, ["state", "error_code"]);
    return { ...common, rule, severity: "medium", evidence: { state: choice(evidence.state, ["lost", "failed"]),
      error_code: evidence.error_code === null ? null : choice(evidence.error_code, SENSOR_ERROR_CODES) } };
  }
  const evidence = shape(value.evidence, ["missing_events"]);
  return { ...common, rule, severity: "medium", evidence: { missing_events: integer(evidence.missing_events, 1) } };
}
interface AlertQuery {
  readonly limit: number;
  readonly status: AlertStatus | null;
  readonly deviceId: string | null;
  readonly before: AlertCursor | null;
}
/** Newest activity first, strictly below the cursor; next_before is the last item's key on a full page. */
export function normalizeAlertPage(input: unknown, query: AlertQuery): AlertPage {
  const value = shape(input, ["items", "next_before"]);
  const items = array(value.items, query.limit, alert);
  unique(items.map((item) => item.id));
  let newer = query.before === null ? null : alertOrderKey(query.before.seen_at, query.before.id);
  for (const item of items) {
    const key = alertOrderKey(item.last_seen_at, item.id);
    requireValue((newer === null || key < newer) && (query.status === null || item.status === query.status)
      && (query.deviceId === null || item.device_id === query.deviceId));
    newer = key;
  }
  const next = value.next_before === null ? null : alertCursor(value.next_before);
  const last = items[items.length - 1];
  requireValue(next === null || (items.length === query.limit && last !== undefined && next.id === last.id
    && utcSortKey(next.seen_at) === utcSortKey(last.last_seen_at)));
  return { items, next_before: next };
}

const STRICT_JSON_BUDGETS = {
  default: { depth: 12, nodes: 12000, stringUnits: 1024, arrayItems: 100, objectKeys: 32, tokens: 60000 },
  "termivar-comparison-v1": { depth: 12, nodes: 250000, stringUnits: 1024, arrayItems: 4096, objectKeys: 32, tokens: 750000 },
  // Adapter maxima within the 1 MiB file cap: 4,096 items; densest diagnostic ~251k nodes / ~508k tokens.
  "termivar-assessment-v1": { depth: 12, nodes: 300000, stringUnits: 1024, arrayItems: 4096, objectKeys: 32, tokens: 600000 },
  // CLI maxima within 512 KiB: 32 scenarios x 2 x 64 trace rows ~42k nodes / ~128k tokens; 1,024 code points = 2,048 units.
  "sp-hbf-preview-v1": { depth: 12, nodes: 50000, stringUnits: 2048, arrayItems: 100, objectKeys: 32, tokens: 160000 },
  // Device timeline and alert pages: the default limits, but an event image may hold 1,024 code points = 2,048
  // UTF-16 units (event_contracts.ProcessStarted.image), exactly what maskedImage()/text() accept.
  "sp-events-alerts-v1": { depth: 12, nodes: 12000, stringUnits: 2048, arrayItems: 100, objectKeys: 32, tokens: 60000 },
} as const;
export type StrictJsonProfile = keyof typeof STRICT_JSON_BUDGETS;
type StrictJsonBudget = typeof STRICT_JSON_BUDGETS[StrictJsonProfile];
function boundedGraph(value: unknown, budget: StrictJsonBudget): unknown {
  const stack: [unknown, number][] = [[value, 0]];
  let count = 0;
  while (stack.length) {
    const current = stack.pop();
    requireValue(current !== undefined);
    const [item, depth] = current;
    requireValue(++count <= budget.nodes && depth <= budget.depth);
    if (typeof item === "string") requireValue(item.length <= budget.stringUnits);
    else if (typeof item === "number") requireValue(Number.isFinite(item));
    else if (item !== null && typeof item === "object") {
      const entries = Object.entries(item);
      requireValue(entries.length <= (Array.isArray(item) ? budget.arrayItems : budget.objectKeys));
      for (const [key, child] of entries) {
        requireValue(!["__proto__", "prototype", "constructor"].includes(key));
        stack.push([child, depth + 1]);
      }
    }
  }
  return value;
}
export function freeze<T>(value: T): T {
  if (value !== null && typeof value === "object") {
    Object.values(value as Record<string, unknown>).forEach(freeze);
    Object.freeze(value);
  }
  return value;
}
export function strictJson(textValue: string, profile: StrictJsonProfile = "default"): unknown {
  // A trusted caller selects a closed profile; JSON never supplies arbitrary limits.
  requireValue(profile === "default" || profile === "termivar-comparison-v1" || profile === "termivar-assessment-v1" || profile === "sp-hbf-preview-v1"
    || profile === "sp-events-alerts-v1");
  const budget = STRICT_JSON_BUDGETS[profile];
  // Native JSON.parse loses duplicate keys and rounds unsafe/fractional values.
  const token = /"(?:\\(?:["\\/bfnrt]|u[0-9a-fA-F]{4})|[^"\\\u0000-\u001f])*"|[{}\[\]:,]|-?(?:0|[1-9]\d*)(?:\.\d+)?(?:[eE][+-]?\d+)?|true|false|null/gy;
  const stack: { kind: string; keys: Set<string> }[] = [];
  let position = 0, count = 0;
  const whitespace = (offset: number): number => {
    while (offset < textValue.length && /[ \r\n\t]/.test(textValue[offset] ?? "")) offset++;
    return offset;
  };
  try {
    while ((position = whitespace(position)) < textValue.length) {
      token.lastIndex = position;
      const match = token.exec(textValue);
      requireValue(match !== null && ++count <= budget.tokens);
      const value = match[0];
      requireValue(value !== undefined);
      position = token.lastIndex;
      if (value === "{" || value === "[") {
        stack.push({ kind: value, keys: new Set() }); requireValue(stack.length <= budget.depth);
      } else if (value === "}" || value === "]") requireValue(stack.pop()?.kind === (value === "}" ? "{" : "["));
      else if (value.startsWith('"') && textValue[whitespace(position)] === ":") {
        const object = stack[stack.length - 1];
        requireValue(object?.kind === "{");
        const key: unknown = JSON.parse(value);
        requireValue(typeof key === "string" && !object.keys.has(key) && object.keys.size < budget.objectKeys);
        object.keys.add(key);
      } else if (/^[\d-]/.test(value)) requireValue(/^-?(?:0|[1-9]\d*)$/.test(value)
        && value !== "-0" && Number.isSafeInteger(Number(value)));
    }
    requireValue(stack.length === 0);
    return boundedGraph(JSON.parse(textValue) as unknown, budget);
  } catch { throw new ClientError("malformed"); }
}
