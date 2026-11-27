/** GitHub issue #15: the status report and the device comparison carry the Altay EDR agent's own state, Snapshot V2
 * and V3. Every agent value stays the agent's claim (self_reported, not_verified), and a device without the agent
 * shows the product as missing. The Platform's golden device details (tests/fixtures/contracts) and the sample data
 * go through the console's real capture, closed-copy and draft functions; the comparison page and the report preview
 * are rendered with react-dom/server, as the console renders them, without a browser. */
import assert from "node:assert/strict";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { createElement } from "react";
import type { ReactElement } from "react";
import { renderToStaticMarkup } from "react-dom/server";
import { PRODUCT_IDS, RESPONSE_ACTIONS } from "../src/data/contracts";
import type { DeviceDetail } from "../src/data/contracts";
import { isEdrAgentStateV3 } from "../src/data/normalize";
import { createDemoData } from "../src/fixtures/demo-data";
import { captureComparableDevice } from "../src/features/compare/capture";
import { ComparePage } from "../src/features/compare/ComparePage";
import { compareFields } from "../src/features/compare/compareFields";
import { agentFieldFormat, agentFormat, COMPARE_FIELDS, compareBytes, CompareError, compareTimestamp,
  copyComparableDevice, MAX_COMPARABLE_BYTES, MAX_COMPARE_BYTES } from "../src/features/compare/compareModel";
import type { ComparableDevice, ComparedField, CompareFieldKey, CompareState, CompareValue } from "../src/features/compare/compareModel";
import { addComparableDevice, createCompareState } from "../src/features/compare/compareState";
import { captureRecord, copyReportRecord } from "../src/features/reports/capture";
import { addRecord, buildPreview, createDraft } from "../src/features/reports/reportDraft";
import { MAX_REPORT_BYTES, MAX_REPORT_RECORDS, REPORT_AGENT_V2_KEYS, REPORT_AGENT_V3_KEYS, REPORT_PRODUCT_IDS,
  ReportError, reportTimestamp } from "../src/features/reports/reportModel";
import type { ReportContext, ReportProduct, ReportRecord } from "../src/features/reports/reportModel";
import { ReportPreview } from "../src/features/reports/ReportPreview";
import { translate } from "../src/i18n";
import type { MessageKey } from "../src/i18n";
import { LocaleProvider } from "../src/i18n/LocaleProvider";
import type { Locale } from "../src/i18n/types";

type Json = Record<string, unknown>;
const ROOT = new URL("../../tests/fixtures/contracts/goldens/snapshots/", import.meta.url);
/** The placeholders and the fixed clock of the Platform test that wrote the goldens. */
const TENANT = "11111111-1111-4111-8111-111111111111";
const NOW = "2030-01-02T03:04:05Z";
const MAX = Number.MAX_SAFE_INTEGER;
const golden = (path: string): Json => (JSON.parse(readFileSync(new URL(path, ROOT), "utf-8")) as { device: Json }).device;
/** Snapshot V2: a lost sensor with its error code and counters at 2^53 - 1; an agent next to the three v1 products. */
const V2_LOST = golden("v2/edr_agent_sensor_lost.json");
const V2_FULL = golden("v2/edr_agent_with_v1_products.json");
/** Snapshot V3: every Stage 3 field set; a failed sensor with counters at 2^53 - 1. */
const V3_FULL = golden("v3/full_agent.json");
const V3_DEGRADED = golden("v3/agent_degraded.json");
/** A V3 snapshot without the agent (and without Termivar). */
const NO_AGENT = golden("v3/v1_products_only.json");

const CONTEXT: ReportContext = { tenantId: TENANT, mode: "api", generation: 0 };
const deviceId = (n: number): string => `22222222-2222-4222-8222-${String(n).padStart(12, "0")}`;
const withId = (detail: Json, n: number): DeviceDetail => ({ ...structuredClone(detail), id: deviceId(n) }) as unknown as DeviceDetail;
const report = (detail: Json, n = 1, tenantName = "Contract fixture tenant"): ReportRecord =>
  captureRecord(withId(detail, n), { context: CONTEXT, tenantName, readAt: NOW });
const comparable = (detail: Json, n = 1): ComparableDevice =>
  captureComparableDevice(withId(detail, n), { tenantId: TENANT, readAt: NOW });
function agentRecord(detail: Json): Json & { readonly state: Json } {
  const found = (detail.products as Json[]).find((entry) => entry.product_id === "edr_agent");
  assert.ok(found);
  return found as Json & { readonly state: Json };
}
function agentOf(record: ReportRecord): ReportProduct {
  const agent = record.products[REPORT_PRODUCT_IDS.indexOf("edr_agent")];
  assert.ok(agent && agent.product === "edr_agent");
  return agent;
}
const invalidReport = (error: unknown): boolean => error instanceof ReportError && error.code === "invalid_report";
const invalidComparison = (error: unknown): boolean => error instanceof CompareError && error.code === "invalid_comparison";
/** The isolation times are device times: the normalizer keeps them in its window, the years 1970 to 9998
 * (normalize.ts windowTime), while the generic timestamp check accepts the years 0001 to 9999. */
const ISOLATION_TIMES = ["isolation_until", "isolation_checked_at"] as const;
const OUT_OF_WINDOW = ["0001-01-01T00:00:00Z", "1969-12-31T23:59:59.999999Z", "9999-01-01T00:00:00Z"];
const IN_WINDOW = ["1970-01-01T00:00:00Z", "9998-12-31T23:59:59.999999Z"];

// --- The status report.

test("the report covers every Platform product, the agent last as on the device-detail card", () => {
  assert.deepEqual([...REPORT_PRODUCT_IDS], [...PRODUCT_IDS]);
  assert.deepEqual(report(V2_FULL).products.map((product) => product.product), [...PRODUCT_IDS]);
  // The limits and the per-record budget are unchanged.
  assert.deepEqual([MAX_REPORT_RECORDS, MAX_REPORT_BYTES], [20, 256 * 1024]);
});

test("a Snapshot V2 agent is copied with its status, sensor, rule file and counters, as its own claim", () => {
  for (const detail of [V2_LOST, V2_FULL]) {
    const { state, received_at: receivedAt } = agentRecord(detail);
    const agent = agentOf(report(detail));
    assert.equal(isEdrAgentStateV3(state), false);
    assert.deepEqual([agent.presence, agent.status, agent.version, agent.sourceObservedAt, agent.receivedAt],
      ["reported", state.status, state.version, state.source_observed_at, receivedAt]);
    assert.deepEqual([agent.source, agent.producerVerification], ["self_reported", "not_verified"]);
    assert.deepEqual(agent.metrics.map((row) => row.key), [...REPORT_AGENT_V2_KEYS]);
    for (const row of agent.metrics) assert.equal(row.value, state[row.key], row.key);
  }
  const lost = Object.fromEntries(agentOf(report(V2_LOST)).metrics.map((row) => [row.key, row.value]));
  assert.deepEqual([lost.sensor_state, lost.sensor_error_code, lost.rule_file_present, lost.events_unmapped],
    ["lost", "session_in_use", null, MAX]);
});

test("a Snapshot V3 agent is copied with every scalar field of its state, as its own claim", () => {
  for (const detail of [V3_FULL, V3_DEGRADED]) {
    const { state } = agentRecord(detail);
    const agent = agentOf(report(detail));
    assert.equal(isEdrAgentStateV3(state), true);
    assert.deepEqual([agent.presence, agent.status, agent.version, agent.source, agent.producerVerification],
      ["reported", state.status, state.version, "self_reported", "not_verified"]);
    assert.deepEqual(agent.metrics.map((row) => row.key), [...REPORT_AGENT_V3_KEYS]);
    for (const row of agent.metrics) assert.equal(row.value, state[row.key], row.key);
    // The two lists of the state are the only fields left out, beside the product's own ones.
    const copied = new Set<string>([...REPORT_AGENT_V3_KEYS, "status", "version", "source_observed_at", "source",
      "producer_verification", "product_id", "catalog_available"]);
    assert.deepEqual(Object.keys(state).filter((key) => !copied.has(key)).sort(), ["response_actions_enabled", "response_key_ids"]);
  }
  const degraded = Object.fromEntries(agentOf(report(V3_DEGRADED)).metrics.map((row) => [row.key, row.value]));
  assert.deepEqual([degraded.sensor_state, degraded.sensor_error_code, degraded.rule_set_state], ["failed", "session_start_failed", "invalid"]);
  assert.ok(Object.values(degraded).includes(MAX));
});

test("a device without the agent shows it as a missing product, with no value of its own", () => {
  const record = report(NO_AGENT);
  const agent = agentOf(record);
  assert.deepEqual(agent, { product: "edr_agent", presence: "missing", status: null, version: null, sourceObservedAt: null,
    receivedAt: null, observation: null, reportImportedAt: null, reportImportAge: null, source: null,
    producerVerification: null, metrics: [] });
  assert.equal(record.products[1]?.presence, "missing");
});

test("V2, V3 and missing agents make one frozen draft and one frozen preview", () => {
  let draft = createDraft(CONTEXT);
  [V2_LOST, V3_FULL, NO_AGENT].forEach((detail, index) => { draft = addRecord(draft, report(detail, index + 1)); });
  for (const locale of ["tr", "en"] as const) {
    const model = buildPreview(draft, { includeIdentifiers: false, createdAt: NOW, locale });
    const agents = model.records.map((record) => record.products[3]);
    assert.deepEqual(agents.map((agent) => [agent?.presence, agent?.metrics.length]),
      [["reported", REPORT_AGENT_V2_KEYS.length], ["reported", REPORT_AGENT_V3_KEYS.length], ["missing", 0]]);
    for (const agent of agents) {
      assert.ok(agent && Object.isFrozen(agent) && Object.isFrozen(agent.metrics) && agent.metrics.every(Object.isFrozen));
      assert.deepEqual([agent.source, agent.producerVerification],
        agent.presence === "reported" ? ["self_reported", "not_verified"] : [null, null]);
    }
  }
});

test("the closed copy refuses an agent copy the normalizer would not give", () => {
  const changed = (detail: Json, change: (agent: Json, metrics: Json[]) => void): ReportRecord => {
    const record = structuredClone(report(detail)) as unknown as { products: Json[] };
    const agent = record.products[3] as Json;
    change(agent, agent.metrics as Json[]);
    return record as unknown as ReportRecord;
  };
  const set = (key: string, value: unknown) => (_agent: Json, metrics: Json[]) => {
    const row = metrics.find((item) => item.key === key); assert.ok(row, key); row.value = value;
  };
  for (const detail of [V2_LOST, V3_FULL, NO_AGENT]) assert.deepEqual(copyReportRecord(report(detail)), report(detail));
  const cases: [string, Json, (agent: Json, metrics: Json[]) => void][] = [
    ["metrics out of order", V3_FULL, (_agent, metrics) => { metrics.reverse(); }],
    ["a V2 list cut short", V2_LOST, (_agent, metrics) => { metrics.pop(); }],
    ["a list field of V3", V3_FULL, (_agent, metrics) => { metrics.push({ key: "response_key_ids", value: "d".repeat(64) }); }],
    ["a counter above 2^53 - 1", V2_LOST, set("events_unmapped", 2 ** 53)],
    ["a negative counter", V3_FULL, set("scans_completed", -1)],
    ["a counter as text", V3_FULL, set("outbox_backlog", "7")],
    ["an unknown sensor state", V2_LOST, set("sensor_state", "paused")],
    ["an error code with a started sensor", V3_FULL, set("sensor_error_code", "access_denied")],
    ["an unknown capability state", V3_FULL, set("realtime_scan_state", "enabled")],
    ["a V3 closed state as null", V3_FULL, set("rule_set_state", null)],
    ["a heartbeat below 30 seconds", V3_FULL, set("heartbeat_interval_seconds", 29)],
    ["an engine ID outside its pattern", V3_FULL, set("engine_id", "edr;agent")],
    ["a rule set ID in capitals", V3_FULL, set("rule_set_id", "A".repeat(64))],
    ["an unknown agent status", V3_FULL, (agent) => { agent.status = "active"; }],
    ["an agent value without its claims", V2_LOST, (agent) => { agent.source = null; }],
    ["a missing agent with values", NO_AGENT, (agent) => {
      agent.metrics = REPORT_AGENT_V2_KEYS.map((key) => ({ key, value: null }));
    }],
    // An isolation time outside the normalizer's device-time window, though a valid timestamp.
    ...ISOLATION_TIMES.flatMap((key) => OUT_OF_WINDOW.map((time): [string, Json, (agent: Json, metrics: Json[]) => void] =>
      [`${key} at ${time}`, V3_FULL, set(key, time)])),
  ];
  for (const [name, detail, change] of cases) assert.throws(() => copyReportRecord(changed(detail, change)), invalidReport, name);
  // The controls: the generic check accepts each refused time, and the window's first and last instants are copied.
  for (const time of OUT_OF_WINDOW) assert.equal(reportTimestamp(time), time);
  for (const key of ISOLATION_TIMES) for (const time of IN_WINDOW) {
    const copy = copyReportRecord(changed(V3_FULL, set(key, time)));
    assert.equal(agentOf(copy).metrics.find((row) => row.key === key)?.value, time, `${key} at ${time}`);
  }
});

/** A V3 device detail with every value at the contract's longest or largest, as the console's normalizer accepts it. */
function largestDetail(n: number): Json {
  const time = "2030-01-02T03:04:05.123456Z";
  const age = { age_seconds: MAX, clock_state: "not_verified" };
  const common = { snapshot_sequence: MAX, received_at: time, observation: age };
  const claims = { source: "self_reported", producer_verification: "not_verified" };
  const agent = { ...claims, product_id: "edr_agent", catalog_available: null, status: "unknown", version: "E".repeat(64),
    source_observed_at: time, agent_started_at: time, engine_id: "G".repeat(128), sensor_state: "failed",
    sensor_error_code: "session_start_failed", rule_set_state: "unreadable", rule_set_id: "f".repeat(64),
    realtime_scan_state: "not_available", file_change_sensor_state: "not_available", command_line_sensor_state: "not_available",
    persistence_watch_state: "not_available", response_channel_state: "awaiting_tenant_binding",
    response_actions_enabled: [...RESPONSE_ACTIONS].sort(), response_key_ids: ["0", "a", "b", "f"].map((c) => c.repeat(64)),
    last_action_seq: MAX, isolation_state: "inactive", isolation_until: time, isolation_checked_at: time, quarantine_items: MAX,
    service_config_state: "as_installed", previous_run_end: "first_start", heartbeat_interval_seconds: 3600,
    behavior_rules_version: "altay-behavior/v999999", ...Object.fromEntries(REPORT_AGENT_V3_KEYS.slice(-16).map((key) => [key, MAX])) };
  return { id: deviceId(n), tenant_id: TENANT, label: "\u{1F512}".repeat(80), identity_status: "revoked", connection_status: "recent",
    created_at: time, revoked_at: time, last_sequence: MAX, last_received_at: time, source_observed_at: time,
    source_observation: age, ...claims, missing_products: [], products: [
      { ...common, product_id: "hostbasedfirewall", state: { ...claims, product_id: "hostbasedfirewall", catalog_available: false,
        status: "unavailable", version: "V".repeat(64), source_observed_at: time, installed: false, reported_running: false,
        reported_stale: false, firewall_mode: "unknown", error_codes: ["telemetry_error"] } },
      { ...common, product_id: "termivar", report_import_age: age, state: { ...claims, product_id: "termivar",
        catalog_available: false, status: "experimental", version: "T".repeat(64), source_observed_at: time,
        scanner_installed: false, execution_available: false, report_presence: "present", latest_report: { ...claims,
          digest: "c".repeat(64), report_schema: "venom-rendered-assessment/v1", imported_at: time, subject_count: 1024,
          item_count: 4096, counts: { informational: 4096, needs_review: 0, confirmed: 0 },
          severity_counts: { unassigned: 4096, info: 0, low: 0, medium: 0, high: 0, critical: 0 }, scope: "offline_report_summary" } } },
      { ...common, product_id: "antivirus", state: { ...claims, product_id: "antivirus", catalog_available: false, version: null,
        status: "unknown", availability: "unknown", execution_available: false, source_observed_at: time } },
      { ...common, product_id: "edr_agent", state: agent },
    ] };
}

test("twenty records with the largest V3 agent still fit the 256 KiB draft and its preview", () => {
  const tenantName = "\u{1F512}".repeat(120);
  let draft = createDraft(CONTEXT);
  for (let n = 1; n <= MAX_REPORT_RECORDS; n++) draft = addRecord(draft, report(largestDetail(n), n, tenantName));
  assert.equal(draft.records.length, 20);
  assert.ok(draft.bytes <= MAX_REPORT_BYTES, String(draft.bytes));
  for (const includeIdentifiers of [true, false]) buildPreview(draft, { includeIdentifiers, createdAt: NOW, locale: "tr" });
  assert.deepEqual(agentOf(draft.records[0] as ReportRecord).metrics.map((row) => row.key), [...REPORT_AGENT_V3_KEYS]);
});

// --- The device comparison.

const AGENT_KEYS: readonly CompareFieldKey[] = COMPARE_FIELDS.filter((field) => field.section === "edr_agent").map((field) => field.key);
const inList = (list: readonly string[]) => (key: string): boolean => list.some((name) => `edr.${name}` === key);
/** The agent fields of one Snapshot version only. */
const V2_ONLY = AGENT_KEYS.filter((key) => inList(REPORT_AGENT_V2_KEYS)(key) && !inList(REPORT_AGENT_V3_KEYS)(key));
const V3_ONLY = AGENT_KEYS.filter((key) => inList(REPORT_AGENT_V3_KEYS)(key) && !inList(REPORT_AGENT_V2_KEYS)(key));
/** What the capture should select for each agent field: the state's own value, or null when the state has none. */
function expectedAgentValue(detail: Json, key: CompareFieldKey): CompareValue {
  const record = (detail.products as Json[]).find((entry) => entry.product_id === "edr_agent") as Json & { state: Json } | undefined;
  if (record === undefined) return null;
  const name = key.slice(4);
  const own: Readonly<Record<string, unknown>> = { received_at: record.received_at, observed_at: record.state.source_observed_at,
    verification: record.state.producer_verification };
  return (Object.hasOwn(own, name) ? own[name] : record.state[name] ?? null) as CompareValue;
}
function rowsOf(left: ComparableDevice, right: ComparableDevice): readonly ComparedField[] {
  const state = addComparableDevice(addComparableDevice(createCompareState(CONTEXT), left), right);
  return compareFields(state).filter((row) => row.section === "edr_agent");
}

test("the comparison has an agent section with every agent field, before the antivirus section", () => {
  const sections = COMPARE_FIELDS.map((field) => field.section).filter((section, index, all) => all.indexOf(section) === index);
  assert.deepEqual(sections, ["device", "hbf", "termivar", "edr_agent", "antivirus"]);
  const names = new Set([...REPORT_AGENT_V2_KEYS, ...REPORT_AGENT_V3_KEYS, "status", "version", "received_at", "observed_at",
    "source", "verification"]);
  assert.deepEqual(AGENT_KEYS.map((key) => key.slice(4)).sort(), [...names].sort());
  // Each field of one Snapshot version only is marked with that version, and no other field is.
  assert.deepEqual([V2_ONLY.length, V3_ONLY.length], [1, 24]);
  for (const key of AGENT_KEYS) {
    assert.equal(agentFieldFormat(key), V2_ONLY.includes(key) ? "v2" : V3_ONLY.includes(key) ? "v3" : null, key);
  }
  assert.ok(COMPARE_FIELDS.every((field) => field.section === "edr_agent" || agentFieldFormat(field.key) === null));
});

test("a V2 and a V3 agent are compared field by field, each with its own values", () => {
  const left = comparable(V2_FULL, 1), right = comparable(V3_FULL, 2);
  assert.deepEqual([agentFormat(left.fields), agentFormat(right.fields)], ["v2", "v3"]);
  for (const key of AGENT_KEYS) {
    assert.equal(left.fields[key], expectedAgentValue(V2_FULL, key), key);
    assert.equal(right.fields[key], expectedAgentValue(V3_FULL, key), key);
  }
  const rows = rowsOf(left, right);
  assert.deepEqual(rows.map((row) => row.key), AGENT_KEYS);
  const result = (key: string) => rows.find((row) => row.key === key)?.result;
  assert.deepEqual(["edr.status", "edr.version", "edr.engine_id", "edr.sensor_state"].map(result),
    ["same", "different", "different", "different"]);
  // A field of the other Snapshot version is missing on one side, not "different".
  assert.deepEqual(["edr.rule_file_present", "edr.rule_set_state", "edr.scans_completed"].map(result), ["missing", "missing", "missing"]);
  // Counters count since each agent started: never ranked, even when known on both sides.
  assert.equal(rows.find((row) => row.key === "edr.events_queue_dropped")?.reason, "scope_not_established");
  assert.deepEqual(["edr.source", "edr.verification"].map(result), ["same", "same"]);
});

test("a device without the agent compares against one with it, and no row is shown for a version neither has", () => {
  const rows = rowsOf(comparable(V2_LOST, 1), comparable(NO_AGENT, 2));
  // 43 agent fields: the 19 a V2 agent has, and the 24 of V3 only.
  assert.deepEqual([AGENT_KEYS.length, rows.length], [43, 19]);
  assert.deepEqual(rows.map((row) => row.key), AGENT_KEYS.filter((key) => !V3_ONLY.includes(key)));
  assert.ok(rows.every((row) => row.result === "missing" && row.right === null));
  for (const row of rows) assert.equal(row.left, expectedAgentValue(V2_LOST, row.key), row.key);
  // The same pair the other way round, and two V2 agents: no V3 row either.
  assert.deepEqual(rowsOf(comparable(NO_AGENT, 1), comparable(V2_LOST, 2)).map((row) => row.key), rows.map((row) => row.key));
  assert.ok(rowsOf(comparable(V2_LOST, 1), comparable(V2_FULL, 2)).every((row) => !V3_ONLY.includes(row.key)));
  // A V3 agent against no agent: no V2 row. Two devices without the agent: the common rows, all missing.
  assert.ok(rowsOf(comparable(V3_FULL, 1), comparable(NO_AGENT, 2)).every((row) => !V2_ONLY.includes(row.key)));
  const neither = rowsOf(comparable(NO_AGENT, 1), comparable(NO_AGENT, 2));
  assert.deepEqual(neither.map((row) => row.key), AGENT_KEYS.filter((key) => !V2_ONLY.includes(key) && !V3_ONLY.includes(key)));
  assert.ok(neither.every((row) => row.result === "missing"));
});

test("the comparison copy refuses agent fields the normalizer would not give", () => {
  const changed = (detail: Json, values: Partial<Record<CompareFieldKey, CompareValue>>): ComparableDevice => {
    const device = structuredClone(comparable(detail)) as { -readonly [K in keyof ComparableDevice]: ComparableDevice[K] };
    device.fields = { ...device.fields, ...values };
    return device;
  };
  for (const detail of [V2_LOST, V3_FULL, NO_AGENT]) assert.deepEqual(copyComparableDevice(comparable(detail)), comparable(detail));
  // The copy keeps each agent's own fields: a refusal below is of the changed value, not of the agent section.
  assert.deepEqual([copyComparableDevice(comparable(V2_LOST)).fields["edr.sensor_error_code"],
    copyComparableDevice(comparable(V3_FULL)).fields["edr.rule_set_state"]], ["session_in_use", "compiled"]);
  const cases: [string, Json, Partial<Record<CompareFieldKey, CompareValue>>][] = [
    ["a V3 field on a V2 agent", V2_LOST, { "edr.quarantine_items": 1 }],
    ["a V2 field on a V3 agent", V3_FULL, { "edr.rule_file_present": true }],
    ["a V3 closed state as null", V3_FULL, { "edr.isolation_state": null }],
    ["an error code with a started sensor", V3_FULL, { "edr.sensor_error_code": "access_denied" }],
    ["agent fields without the agent", NO_AGENT, { "edr.sensor_state": "started" }],
    ["an agent received at another time", V3_FULL, { "edr.received_at": "2030-01-02T03:04:06Z" }],
    ["an agent value without its claims", V2_LOST, { "edr.verification": null }],
    ["a counter above 2^53 - 1", V2_LOST, { "edr.outbox_backlog": 2 ** 53 }],
    ["an engine ID outside its pattern", V3_FULL, { "edr.engine_id": "edr;agent" }],
    ["a heartbeat above an hour", V3_FULL, { "edr.heartbeat_interval_seconds": 3601 }],
    ["a behavior rules version outside its pattern", V3_FULL, { "edr.behavior_rules_version": "altay-behavior/v0" }],
    // An isolation time outside the normalizer's device-time window, though a valid timestamp.
    ...ISOLATION_TIMES.flatMap((key) => OUT_OF_WINDOW.map((time): [string, Json, Partial<Record<CompareFieldKey, CompareValue>>] =>
      [`edr.${key} at ${time}`, V3_FULL, at(`edr.${key}`, time)])),
  ];
  for (const [name, detail, values] of cases) {
    // Each change replaces a field the copy already has; none adds a key.
    assert.ok(Object.keys(values).every((key) => Object.hasOwn(comparable(detail).fields, key)), name);
    assert.throws(() => copyComparableDevice(changed(detail, values)), invalidComparison, name);
  }
  // The controls: the generic check accepts each refused time, and the window's first and last instants are copied.
  for (const time of OUT_OF_WINDOW) assert.equal(compareTimestamp(time), time);
  for (const key of ISOLATION_TIMES) for (const time of IN_WINDOW) {
    assert.equal(copyComparableDevice(changed(V3_FULL, at(`edr.${key}`, time))).fields[`edr.${key}`], time, `${key} at ${time}`);
  }
});
/** One changed comparison field. */
function at(key: CompareFieldKey, value: CompareValue): Partial<Record<CompareFieldKey, CompareValue>> {
  const values: Partial<Record<CompareFieldKey, CompareValue>> = {};
  values[key] = value;
  return values;
}

test("two of the largest V3 devices fit the comparison's size limits", () => {
  const left = comparable(largestDetail(1), 1), right = comparable(largestDetail(2), 2);
  assert.ok(compareBytes(left) <= MAX_COMPARABLE_BYTES, String(compareBytes(left)));
  const state = addComparableDevice(addComparableDevice(createCompareState(CONTEXT), left), right);
  assert.ok(state.bytes <= MAX_COMPARE_BYTES, String(state.bytes));
  assert.equal(left.fields["edr.events_unmapped"], MAX);
});

// --- The rendered pages.

/** A console page's markup in one locale, as react-dom/server renders it: no browser and no effects. */
function render(locale: Locale, page: ReactElement): string {
  return renderToStaticMarkup(createElement(LocaleProvider, { locale, setLocale: () => undefined, children: page }));
}
const ENTITIES: Readonly<Record<string, string>> = { "&amp;": "&", "&lt;": "<", "&gt;": ">", "&quot;": "\"", "&#x27;": "'" };
/** The text of a markup fragment: its tags dropped and React's escapes undone. */
const textOf = (html: string): string =>
  html.replace(/<[^>]*>/g, "").replace(/&(?:amp|lt|gt|quot|#x27);/g, (entity) => ENTITIES[entity] ?? entity);
interface RenderedRow { readonly label: string; readonly note: string | null; readonly left: string; readonly right: string }
/** One CompareFieldRow: its label, its note if it has one, and the left and the right cell. */
const COMPARE_ROW = new RegExp(String.raw`<div class="compare-field" data-comparison="\w+"><div class="compare-field-heading">`
  + String.raw`<h4>(.*?)</h4><span [^>]*>.*?</span>(?:<p class="muted">(.*?)</p>)?</div>`
  + String.raw`<div class="compare-field-value">.*?<div>(.*?)</div></div><div class="compare-field-value">.*?<div>(.*?)</div></div></div>`,
"g");
/** The comparison page's rendered agent section: its note, and the text of each agent row by its field. */
function renderedAgentSection(state: CompareState, locale: Locale): { readonly note: string; readonly rows: ReadonlyMap<CompareFieldKey, RenderedRow> } {
  const html = render(locale, createElement(ComparePage, { state, onRemove: () => undefined, onClear: () => undefined }));
  const start = html.indexOf(`<section class="panel compare-section" aria-label="${translate(locale, "compare.section.edr_agent")}">`);
  assert.ok(start >= 0, "the agent section");
  const section = html.slice(start, html.indexOf("</section>", start));
  const fields = compareFields(state).filter((row) => row.section === "edr_agent");
  const found = [...section.matchAll(COMPARE_ROW)];
  assert.equal(found.length, fields.length);
  return { note: textOf(/<p class="compare-section-note">(.*?)<\/p>/.exec(section)?.[1] ?? ""),
    rows: new Map(fields.map((field, index): [CompareFieldKey, RenderedRow] => {
      const [, label = "", note, left = "", right = ""] = found[index] ?? [];
      return [field.key, { label: textOf(label), note: note === undefined ? null : textOf(note), left: textOf(left), right: textOf(right) }];
    })) };
}
const pair = (left: ComparableDevice, right: ComparableDevice): CompareState =>
  addComparableDevice(addComparableDevice(createCompareState(CONTEXT), left), right);

test("the comparison page shows each agent value in the device-detail card's words, and each agent row its claim", () => {
  // A V2 agent with a rule file and a lost sensor that reported no code, to read beside a device without the agent.
  const lost = structuredClone(comparable(V2_LOST, 1)) as { -readonly [K in keyof ComparableDevice]: ComparableDevice[K] };
  lost.fields = { ...lost.fields, "edr.rule_file_present": true, "edr.sensor_error_code": null };
  // [field, its label, the left cell's words, the right cell's words]
  const cases: readonly [CompareState, readonly (readonly [CompareFieldKey, MessageKey, MessageKey, MessageKey])[]][] = [
    // V2 beside V3: the card's status, rule file, closed-state and sensor-code words, and each version's own fields.
    [pair(comparable(V2_FULL, 1), comparable(V3_FULL, 2)), [
      ["edr.status", "compare.field.edr.status", "product.edr.running", "product.edr.running"],
      ["edr.rule_file_present", "product.edr.ruleFile", "product.edr.ruleFile.absent", "compare.value.notInFormat"],
      ["edr.rule_set_state", "product.edrV3.ruleSet", "compare.value.notInFormat", "product.edrV3.ruleSet.compiled"],
      ["edr.sensor_state", "product.edr.sensorState", "product.edr.sensor.disabled", "product.edr.sensor.started"],
      ["edr.sensor_error_code", "product.edr.sensorError", "product.edr.sensorError.notApplicable",
        "product.edr.sensorError.notApplicable"],
      ["edr.service_config_state", "product.edrV3.serviceConfig", "compare.value.notInFormat",
        "product.edrV3.serviceConfig.as_installed"],
      ["edr.previous_run_end", "product.edrV3.previousRun", "compare.value.notInFormat", "product.edrV3.previousRun.clean"],
      ["edr.realtime_scan_state", "product.edrV3.realtimeScan", "compare.value.notInFormat", "product.edrV3.capability.running"],
      ["edr.command_line_sensor_state", "product.edrV3.commandLineSensor", "compare.value.notInFormat",
        "product.edrV3.capability.degraded"],
      ["edr.response_channel_state", "product.edrV3.responseChannel", "compare.value.notInFormat",
        "product.edrV3.responseChannel.ready"],
      ["edr.isolation_state", "product.edrV3.isolation", "compare.value.notInFormat", "product.edrV3.isolation.active"],
    ]],
    // A V2 agent beside a device without it: the agent's words on one side, no information on the other.
    [pair(lost, comparable(NO_AGENT, 2)), [
      ["edr.status", "compare.field.edr.status", "product.edr.running", "compare.value.missing"],
      ["edr.rule_file_present", "product.edr.ruleFile", "product.edr.ruleFile.present", "compare.value.missing"],
      ["edr.sensor_state", "product.edr.sensorState", "product.edr.sensor.lost", "compare.value.missing"],
      ["edr.sensor_error_code", "product.edr.sensorError", "product.edr.sensorError.notReported", "compare.value.missing"],
    ]],
  ];
  for (const locale of ["tr", "en"] as const) for (const [state, expected] of cases) {
    const { note, rows } = renderedAgentSection(state, locale);
    assert.equal(note, translate(locale, "compare.sectionNote.edr_agent"));
    for (const [key, label, left, right] of expected) {
      const row = rows.get(key);
      assert.deepEqual([row?.label, row?.left, row?.right],
        [translate(locale, label), translate(locale, left), translate(locale, right)], `${locale} ${key}`);
    }
    // A row's note is its result's; otherwise every agent row but the receipt time and the source is the agent's claim.
    for (const field of compareFields(state).filter((row) => row.section === "edr_agent")) {
      const key: MessageKey | null = field.reason === "scope_not_established" ? "compare.note.scope"
        : field.result === "missing" ? "compare.note.missing" : field.result === "incomparable" ? "compare.note.incomparable"
          : field.key === "edr.verification" ? "compare.note.verification"
            : field.key === "edr.received_at" || field.key === "edr.source" ? null : "compare.note.agentClaim";
      assert.equal(rows.get(field.key)?.note, key === null ? null : translate(locale, key), `${locale} ${field.key} note`);
    }
  }
  // The V3 agent's isolation "active" is its report of its filters, never the device registration's "active".
  const isolation = renderedAgentSection(cases[0]![0], "tr").rows.get("edr.isolation_state");
  assert.equal(isolation?.right, translate("tr", "product.edrV3.isolation.active"));
  assert.notEqual(isolation?.right, translate("tr", "compare.value.active"));
});

test("the report preview keeps the card's notes beside the agent's values, and gives a missing agent neither", () => {
  let draft = createDraft(CONTEXT);
  [V2_LOST, V3_FULL, NO_AGENT].forEach((detail, index) => { draft = addRecord(draft, report(detail, index + 1)); });
  for (const locale of ["tr", "en"] as const) {
    const html = render(locale, createElement(ReportPreview,
      { report: buildPreview(draft, { includeIdentifiers: false, createdAt: NOW, locale }) }));
    const heading = `<section class="report-product-section"><h3>${translate(locale, "report.product.edr_agent")}</h3>`;
    const sections = html.split(heading).slice(1).map((part) => part.slice(0, part.indexOf("</section>")));
    const notes = (section: string): string[] =>
      [...section.matchAll(/<p class="report-trust-note">(.*?)<\/p>/g)].map((match) => textOf(match[1] ?? ""));
    const claims = (section: string): number => section.split('<span class="report-claim">').length - 1;
    const words = (...keys: MessageKey[]): string[] => keys.map((key) => translate(locale, key));
    assert.equal(sections.length, 3);
    const [v2 = "", v3 = "", missing = ""] = sections;
    assert.deepEqual(notes(v2), words("report.agentNote", "product.edr.countersScope"));
    // V3 also keeps the card's scan note and its response note: the console sends the agent no actions.
    assert.deepEqual(notes(v3), words("report.agentNote", "product.edrV3.scanNote", "product.edrV3.responseScope",
      "product.edrV3.countersScope"));
    // A missing agent reports no value, so it has neither the agent's note nor a claim.
    assert.deepEqual(notes(missing), words("report.missingProductNote"));
    // The status, the version, the source observation time and every agent value carry the claim.
    assert.deepEqual([claims(v2), claims(v3), claims(missing)],
      [3 + REPORT_AGENT_V2_KEYS.length, 3 + REPORT_AGENT_V3_KEYS.length, 0]);
  }
});

// --- Sample mode.

test("every sample device goes into the report and the comparison; the two without the agent show it missing", () => {
  const data = createDemoData();
  const seen = new Set<string | null>();
  const missing: string[] = [];
  for (const tenantId of new Set(data.devices.map((device) => device.tenant_id))) {
    const devices = data.devices.filter((device) => device.tenant_id === tenantId);
    const context: ReportContext = { tenantId, mode: "example", generation: 0 };
    let draft = createDraft(context);
    for (const device of devices) {
      const record = captureRecord(device, { context, tenantName: "DEMO", readAt: data.referenceTime });
      const state = device.products.find((entry) => entry.product_id === "edr_agent")?.state;
      const format = state === undefined ? null : isEdrAgentStateV3(state) ? "v3" : "v2";
      const agent = agentOf(record);
      assert.equal(agent.presence, state === undefined ? "missing" : "reported", device.label);
      assert.deepEqual(agent.metrics.map((row) => row.key),
        format === "v3" ? [...REPORT_AGENT_V3_KEYS] : format === "v2" ? [...REPORT_AGENT_V2_KEYS] : [], device.label);
      const fields = captureComparableDevice(device, { tenantId, readAt: data.referenceTime }).fields;
      assert.equal(agentFormat(fields), format, device.label);
      if (format === null) missing.push(device.label);
      seen.add(format);
      draft = addRecord(draft, record);
    }
    for (const locale of ["tr", "en"] as const) buildPreview(draft, { includeIdentifiers: true, createdAt: data.referenceTime, locale });
  }
  assert.deepEqual([...seen].sort(), [null, "v2", "v3"].sort());
  assert.deepEqual(missing.sort(), ["DEMO · Yeni kayıt", "DEMO · İptal edilmiş cihaz kaydı"].sort());
});
