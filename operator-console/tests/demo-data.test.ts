/** The sample Snapshot V3 device agrees with its own timeline and carries the alerts that the Platform's rules
 * (services/alerts.py, batch_matches) raise for that timeline. */
import assert from "node:assert/strict";
import { test } from "node:test";
import type { Alert, TimelineEvent } from "../src/data/contracts";
import { alertOrderKey, isEdrAgentStateV3, normalizeAlertPage, normalizeTimelinePage } from "../src/data/normalize";
import { createDemoData } from "../src/fixtures/demo-data";

const data = createDemoData();
const samples = data.devices.flatMap((device) => device.products.flatMap((record) =>
  record.product_id === "edr_agent" && isEdrAgentStateV3(record.state) ? [{ device, state: record.state }] : []));
/** The device's stored events, newest first. */
function eventsOf(deviceId: string): readonly TimelineEvent[] {
  const timeline = data.timelines.find((entry) => entry.deviceId === deviceId);
  assert.ok(timeline, deviceId);
  return timeline.events;
}
const alertsOf = (deviceId: string): readonly Alert[] => data.alerts.filter((alert) => alert.device_id === deviceId);
/** [first_event_seq, last_event_seq, rule] of every alert that services/alerts.py raises for the sample V3 timeline:
 * a persistence entry added (53), a launch under Users\*\Downloads (54, user_writable), a scan match (55), a behavior
 * match (56), a tamper signal (60) and realtime_scan stopped (61, CAPABILITY_DOWN). The other agent_state pairs, the
 * process stop, the coverage gap and the launch under Windows\System32 raise nothing. */
const RAISED = [[53, 53, "persistence_added"], [54, 54, "user_writable_launch"], [55, 55, "scan_detection"],
  [56, 56, "behavior_match"], [60, 60, "tamper_signal"], [61, 61, "capability_down"]];

test("the sample data has one Snapshot V3 agent, with a timeline", () => {
  assert.equal(samples.length, 1);
  assert.ok(eventsOf(samples[0]?.device.id ?? "").length > 0);
});

test("the sample V3 agent started when the latest service start of its timeline says", () => {
  for (const { device, state } of samples) {
    // Newest first, so find() gives the latest service start.
    const start = eventsOf(device.id).find((event) => event.kind === "agent_state" && event.subject === "service"
      && event.state === "started");
    assert.ok(start && state.agent_started_at !== null, device.label);
    assert.equal(Date.parse(state.agent_started_at), Date.parse(start.observed_at), device.label);
  }
});

test("the sample V3 device carries exactly the event alerts the Platform raises for its timeline", () => {
  for (const { device } of samples) {
    const raised = alertsOf(device.id).filter((alert) => alert.first_event_seq !== null)
      .map((alert) => [alert.first_event_seq, alert.last_event_seq, alert.rule])
      .sort((left, right) => Number(left[0]) - Number(right[0]));
    assert.deepEqual(raised, RAISED, device.label);
    // user_writable_launch keeps the launch's image and pid; it is first and last seen when that event's batch arrived.
    const launch = eventsOf(device.id).find((event) => event.event_seq === 54);
    const alert = alertsOf(device.id).find((item) => item.rule === "user_writable_launch");
    assert.ok(launch?.kind === "process_started" && alert?.rule === "user_writable_launch", device.label);
    assert.deepEqual(alert.evidence, { image: launch.image, pid: launch.pid });
    assert.deepEqual([alert.first_seen_at, alert.last_seen_at, alert.occurrences], [launch.received_at, launch.received_at, 1]);
  }
});

test("the sample V3 device's timeline and alerts pass the console's normalizers", () => {
  for (const { device } of samples) {
    const events = eventsOf(device.id);
    assert.equal(normalizeTimelinePage({ items: events, next_before_seq: null, cap_deleted_events: 0, suppressed_alerts: 0 },
      { limit: events.length, beforeSeq: null }).items.length, events.length);
    // The alert list order: last_seen_at DESC, id DESC, as the API and the sample client page it.
    const key = (alert: Alert): string => alertOrderKey(alert.last_seen_at, alert.id);
    const alerts = [...alertsOf(device.id)].sort((left, right) => key(left) < key(right) ? 1 : key(left) > key(right) ? -1 : 0);
    assert.equal(normalizeAlertPage({ items: alerts, next_before: null },
      { limit: alerts.length, status: null, deviceId: device.id, before: null }).items.length, alerts.length);
  }
});
