/** The Platform's golden responses in tests/fixtures/contracts (GitHub issue #10) through the console's real readers.
 * tests/integration/test_contract_fixtures.py writes each golden from the operator API after an accepted device
 * payload: the device's timeline page and its device detail. Here each one goes through strictJson with the profile
 * the read adapter uses for that route (platformReadOnly.responseProfile) and then through normalizeTimelinePage or
 * normalizeDeviceDetail: every golden must be accepted unchanged, and shape-broken copies of it (a missing required
 * field, a wrong type, an unknown enum value, an extra key) must be refused as malformed. */
import assert from "node:assert/strict";
import { createHash } from "node:crypto";
import { readFileSync } from "node:fs";
import { test } from "node:test";
import { ClientError, PRODUCT_IDS } from "../src/data/contracts";
import { isEdrAgentStateV3, normalizeDeviceDetail, normalizeTimelinePage, strictJson } from "../src/data/normalize";

const ROOT = new URL("../../tests/fixtures/contracts/", import.meta.url);
/** The placeholders the Platform test puts in place of the run's tenant and device IDs (see the tree's README). */
const TENANT = "11111111-1111-4111-8111-111111111111";
const DEVICE = "22222222-2222-4222-8222-222222222222";
/** The fixed clock of the Platform test: every server time in a golden. */
const NOW = "2030-01-02T03:04:05Z";
const CLAIMS = { source: "self_reported", producer_verification: "not_verified" } as const;

type Json = Record<string, unknown>;
interface ManifestEntry {
  readonly path: string; readonly sha256: string; readonly kind: string; readonly version?: number;
  readonly payload?: string; readonly golden?: string; readonly expected?: { readonly decision: string };
}
interface Golden { readonly payload: string; readonly ack: Json; readonly timeline: Json; readonly device: Json }

const read = (path: string): Buffer => readFileSync(new URL(path, ROOT));
const parse = (path: string): unknown => JSON.parse(read(path).toString("utf-8"));
const manifest = parse("manifest.json") as { readonly files: readonly ManifestEntry[] };
const goldens = manifest.files.filter((entry) => entry.kind === "golden");
const accepted = manifest.files.filter((entry) => entry.expected?.decision === "accepted");
const copy = <T>(value: T): T => structuredClone(value);
const malformed = (error: unknown): boolean => error instanceof ClientError && error.code === "malformed";

/** The bytes the adapter would read, parsed as it parses them. */
const readTimeline = (value: unknown) =>
  normalizeTimelinePage(strictJson(JSON.stringify(value), "sp-events-alerts-v1"), { limit: 50, beforeSeq: null });
const readDetail = (value: unknown) =>
  normalizeDeviceDetail(strictJson(JSON.stringify(value), "sp-device-detail-v1"), TENANT, DEVICE);

test("the manifest lists a golden for every accepted payload, with the hash of the file on disk", () => {
  assert.ok(goldens.length > 0);
  assert.deepEqual(goldens.map((entry) => entry.payload).sort(), accepted.map((entry) => entry.path).sort());
  assert.deepEqual(accepted.map((entry) => entry.golden).sort(), goldens.map((entry) => entry.path).sort());
  for (const entry of goldens) {
    assert.equal(createHash("sha256").update(read(entry.path)).digest("hex"), entry.sha256, entry.path);
  }
  // Each contract version has accepted payloads: events v1/v2, snapshots V1/V2/V3.
  const versions = new Set(accepted.map((entry) => `${entry.kind}/${entry.version}`));
  assert.deepEqual([...versions].sort(), ["event_batch/1", "event_batch/2", "snapshot/1", "snapshot/2", "snapshot/3"]);
});

/** One closed field of each kind and a value outside its set (or outside its documented rule). */
const BROKEN_FIELD: Readonly<Record<string, readonly [string, unknown]>> = {
  process_started: ["image", "\\Device\\HarddiskVolume3\\Users\\ahmet\\setup.exe"],
  process_stopped: ["image", "tools\\setup.exe"], sensor_state: ["state", "paused"],
  scan_detected: ["trigger", "on_demand"], behavior_match: ["rule", "custom_rule"],
  persistence_change: ["location", "wmi_subscription"], agent_state: ["subject", "firewall"],
  tamper_signal: ["signal", "unknown_signal"], coverage_gap: ["reason", "disk_full"],
};
/** A closed field of each product state and a value outside its set. */
const BROKEN_STATE: Readonly<Record<string, readonly [string, unknown]>> = {
  hostbasedfirewall: ["firewall_mode", "block"], termivar: ["report_presence", "maybe"],
  antivirus: ["availability", "available"], edr_agent: ["sensor_state", "paused"],
};

function timelineVariants(timeline: Json): [string, Json][] {
  const items = timeline.items as Json[];
  const variants: [string, Json][] = [];
  const variant = (name: string, change: (page: Json, item: Json) => void, index = 0) => {
    const page = copy(timeline);
    change(page, (page.items as Json[])[index] as Json);
    variants.push([name, page]);
  };
  variant("a page without cap_deleted_events", (page) => { delete page.cap_deleted_events; });
  variant("a missing observed_at", (_page, item) => { delete item.observed_at; });
  variant("event_seq as text", (_page, item) => { item.event_seq = String(item.event_seq); });
  variant("an unknown kind", (_page, item) => { item.kind = "network_connection"; });
  variant("an extra key", (_page, item) => { item.command_line = "setup.exe /S"; });
  variant("an upgraded trust claim", (_page, item) => { item.producer_verification = "verified"; });
  variant("an unknown received_at shape", (_page, item) => { item.received_at = "2030-01-02 03:04:05"; });
  for (const kind of new Set(items.map((item) => item.kind as string))) {
    const index = items.findIndex((item) => item.kind === kind);
    const [field, value] = BROKEN_FIELD[kind] ?? ["kind", null];
    variant(`${kind} with ${field}=${JSON.stringify(value)}`, (_page, item) => { item[field] = value; }, index);
  }
  return variants;
}

function detailVariants(detail: Json): [string, Json][] {
  const variants: [string, Json][] = [];
  const variant = (name: string, change: (value: Json) => void) => {
    const value = copy(detail);
    change(value);
    variants.push([name, value]);
  };
  variant("a missing connection_status", (value) => { delete value.connection_status; });
  variant("last_sequence as text", (value) => { value.last_sequence = "1"; });
  variant("an unknown connection_status", (value) => { value.connection_status = "online"; });
  variant("another tenant", (value) => { value.tenant_id = "33333333-3333-4333-8333-333333333333"; });
  variant("an upgraded trust claim", (value) => { value.producer_verification = "verified"; });
  // Every product is either present or missing, never both or neither.
  variant("a product in both lists or in neither", (value) => {
    const present = (value.products as Json[]).map((product) => product.product_id);
    value.missing_products = present.length > 0 ? [...(value.missing_products as unknown[]), present[0]] : [];
  });
  (detail.products as Json[]).forEach((product, index) => {
    const id = product.product_id as string;
    const state = (target: Json): Json => (target.products as Json[])[index]?.state as Json;
    const v3 = id === "edr_agent" && isEdrAgentStateV3(product.state as object);
    const [field, broken] = v3 ? ["realtime_scan_state", "on"] : BROKEN_STATE[id] ?? ["status", "x"];
    variant(`${id} with ${field}=${JSON.stringify(broken)}`, (value) => { state(value)[field] = broken; });
    variant(`${id} without its source claim`, (value) => { delete state(value).source; });
    variant(`${id} with a protection claim`, (value) => { state(value).protection_active = true; });
    variant(`${id} with status as a number`, (value) => { state(value).status = 1; });
    variant(`${id} with another received_at`, (value) => {
      ((value.products as Json[])[index] as Json).received_at = "2030-01-02T03:04:06Z"; });
  });
  return variants;
}

for (const entry of goldens) {
  const golden = parse(entry.path) as Golden;
  const payload = parse(golden.payload) as Json;
  const events = golden.payload.startsWith("events/");

  test(`${entry.path}: the timeline is accepted unchanged`, () => {
    assert.equal(golden.payload, entry.payload);
    const page = readTimeline(golden.timeline);
    assert.deepEqual(page, golden.timeline);
    const sent = events ? [...(payload.events as Json[])].reverse() : [];
    assert.deepEqual(page.items.map((item) => [item.event_seq, item.kind]), sent.map((event) => [event.event_seq, event.kind]));
    for (const [index, item] of page.items.entries()) {
      assert.equal(item.received_at, NOW);
      assert.deepEqual({ source: item.source, producer_verification: item.producer_verification }, CLAIMS);
      // coverage_gap's own source arrives as gap_source; source stays the trust label.
      if (item.kind === "coverage_gap") assert.equal(item.gap_source, sent[index]?.source);
    }
    assert.equal(page.next_before_seq, null);
  });

  test(`${entry.path}: the device detail is accepted unchanged`, () => {
    const detail = readDetail(golden.device);
    assert.deepEqual(detail, golden.device);
    assert.deepEqual([detail.id, detail.tenant_id, detail.identity_status], [DEVICE, TENANT, "active"]);
    assert.deepEqual({ source: detail.source, producer_verification: detail.producer_verification }, CLAIMS);
    if (events) {
      // Events never refresh the heartbeat: an events-only device has no product and stays never_seen.
      assert.deepEqual([detail.connection_status, detail.last_sequence, detail.products.length],
        ["never_seen", null, 0]);
      assert.deepEqual(detail.missing_products, [...PRODUCT_IDS].sort());
      return;
    }
    const sent = (payload.products as Json[]).map((product) => product.product_id as string).sort();
    assert.deepEqual([detail.connection_status, detail.last_sequence, detail.last_received_at],
      ["recent", payload.sequence, NOW]);
    assert.deepEqual(detail.products.map((product) => product.product_id), sent);
    assert.deepEqual(detail.missing_products, PRODUCT_IDS.filter((id) => !sent.includes(id)).sort());
    for (const product of detail.products) {
      assert.deepEqual([product.snapshot_sequence, product.received_at], [payload.sequence, NOW]);
      // A Snapshot V3 edr_agent state is told from V2's by its key set alone.
      if (product.product_id === "edr_agent") assert.equal(isEdrAgentStateV3(product.state), payload.schema_version === 3);
    }
  });

  const variants = [...(events ? timelineVariants(golden.timeline).map(([name, value]) =>
    [`timeline, ${name}`, () => readTimeline(value)] as const) : []),
    ...detailVariants(golden.device).map(([name, value]) => [`device detail, ${name}`, () => readDetail(value)] as const)];
  for (const [name, run] of variants) {
    test(`${entry.path}: refuses ${name}`, () => { assert.throws(run, malformed); });
  }
}
