/** Closed runtime validation shared by fixtures and the real GET adapter. */
import { ClientError, HBF_ERROR_CODES, PRODUCT_IDS } from "./contracts";
import type { AgeObservation, AuditAction, AuditEvent, AuditObject, ClientErrorCode, Device, DeviceDetail,
  DispositionCounts, Page, ProductId, ProductRecord, ProductState, SeverityCounts, SourceClaims,
  Tenant, TermivarSummary } from "./contracts";

const CLAIM_KEYS = ["source", "producer_verification"];
const DEVICE_KEYS = ["id", "tenant_id", "label", "identity_status", "connection_status", "created_at", "revoked_at",
  "last_sequence", "last_received_at", "source_observed_at", "source_observation", ...CLAIM_KEYS];
const PRODUCT_KEYS = ["product_id", "catalog_available", ...CLAIM_KEYS, "version", "source_observed_at"];
const AUDIT_OBJECTS: Readonly<Record<AuditAction, AuditObject>> = {
  tenant_created: "tenant", membership_set: "membership", membership_revoked: "membership",
  enrollment_grant_created: "enrollment_grant", enrollment_grant_revoked: "enrollment_grant",
  device_enrolled: "device", device_revoked: "device", device_credential_rotated: "device_credential",
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
function productState(input: unknown, id: ProductId): ProductState {
  const specific = id === "hostbasedfirewall" ? ["status", "installed", "reported_running", "reported_stale", "firewall_mode", "error_codes"]
    : id === "termivar" ? ["status", "scanner_installed", "execution_available", "report_presence", "latest_report"]
      : ["status", "availability", "execution_available"];
  const value = shape(input, [...PRODUCT_KEYS, ...specific]);
  requireValue(value.product_id === id);
  const version = value.version === null ? null : text(value.version, 64);
  requireValue(version === null || /^[A-Za-z0-9][A-Za-z0-9._+\-]*$/.test(version));
  const common = { catalog_available: nullableBoolean(value.catalog_available), ...claims(value),
    version, source_observed_at: timestamp(value.source_observed_at, true) };
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
  const products = array<ProductRecord>(value.products, 3, (raw) => {
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
    return { ...common, product_id: state.product_id, state };
  });
  const present = unique(products.map((entry) => entry.product_id));
  const missing = unique(array(value.missing_products, 3, (id) => choice(id, PRODUCT_IDS)));
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

const STRICT_JSON_BUDGETS = {
  default: { depth: 12, nodes: 12000, stringUnits: 1024, arrayItems: 100, objectKeys: 32, tokens: 60000 },
  "termivar-comparison-v1": { depth: 12, nodes: 250000, stringUnits: 1024, arrayItems: 4096, objectKeys: 32, tokens: 750000 },
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
  requireValue(profile === "default" || profile === "termivar-comparison-v1");
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
