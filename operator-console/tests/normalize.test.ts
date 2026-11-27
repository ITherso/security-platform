/** The scan_detected normalizer refuses exactly what the Platform's ingestion refuses (event_contracts.ScanDetected):
 * a hit rule that repeats, and a create time without a pid. The cases, with the Platform's verdict for each, are in
 * scan-detected-cases.json; tests/unit/test_console_stage3.py checks those verdicts against the Platform. */
import assert from "node:assert/strict";
import { test } from "node:test";
import { ClientError } from "../src/data/contracts";
import { normalizeAlertPage, normalizeTimelinePage } from "../src/data/normalize";
import scanCases from "./scan-detected-cases.json";

const CLAIMS = { source: "self_reported", producer_verification: "not_verified" } as const;
const RECEIVED_AT = "2030-01-02T03:04:06.000000Z";

/** A one-item timeline page: the stored event under services/events._event_view's keys. */
function timelinePage(event: Record<string, unknown>): unknown {
  return { items: [{ ...event, received_at: RECEIVED_AT, ...CLAIMS }], next_before_seq: null, cap_deleted_events: 0,
    suppressed_alerts: 0 };
}
/** The event's own fields, without kind, event_seq and observed_at: a scan_detection alert's evidence. */
function evidenceOf(event: Record<string, unknown>): Record<string, unknown> {
  const { kind: _kind, event_seq: _seq, observed_at: _observed, ...evidence } = event;
  return evidence;
}
/** A one-item alert page: the scan_detection alert this event opens. */
function alertPage(event: Record<string, unknown>): unknown {
  return { items: [{ id: "70000000-0000-4000-8000-000000000001", device_id: "20000000-0000-4000-8000-000000000001",
    rule: "scan_detection", severity: "medium", status: "open", occurrences: 1, first_event_seq: event.event_seq,
    last_event_seq: event.event_seq, first_seen_at: RECEIVED_AT, last_seen_at: RECEIVED_AT, evidence: evidenceOf(event),
    acknowledged_at: null, closed_at: null, ...CLAIMS }], next_before: null };
}
const readTimeline = (event: Record<string, unknown>) =>
  normalizeTimelinePage(timelinePage(event), { limit: 50, beforeSeq: null });
const readAlerts = (event: Record<string, unknown>) =>
  normalizeAlertPage(alertPage(event), { limit: 50, status: null, deviceId: null, before: null });
const malformed = (error: unknown): boolean => error instanceof ClientError && error.code === "malformed";

test("the cases cover both Platform refusals and the values next to them", () => {
  const errors = new Set(scanCases.cases.map((item) => item.platform_error));
  assert.deepEqual([...errors].sort(), ["create_time_requires_pid", "duplicate_hit_rule", null]);
});

for (const { name, changes, platform_error: refused } of scanCases.cases) {
  const event: Record<string, unknown> = { ...scanCases.event, ...changes };
  test(`scan_detected, ${name}: ${refused === null ? "accepted" : `refused (${refused})`}`, () => {
    if (refused === null) {
      // Accepted unchanged, as a timeline item and as alert evidence.
      assert.deepEqual(readTimeline(event).items, [{ ...event, received_at: RECEIVED_AT, ...CLAIMS }]);
      assert.deepEqual(readAlerts(event).items[0]?.evidence, evidenceOf(event));
    } else {
      assert.throws(() => readTimeline(event), malformed);
      assert.throws(() => readAlerts(event), malformed);
    }
  });
}
