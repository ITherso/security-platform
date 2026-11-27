/** The device-detail agent card's labels (components/ProductViews.tsx), shared by the status report and the device
 * comparison so that an agent value reads the same in all three. Labels only: every value stays the agent's own claim
 * (self_reported, not_verified), and none of these words says that rules are loaded or that anything is protected. */
import type { CapabilityState, EdrSensorState, IsolationState, PreviousRunEnd, ResponseChannelState, RuleSetState,
  ServiceConfigState } from "../data/contracts";
import type { ProductTextKey } from "../i18n/catalogs/products";
import type { ReportAgentMetricKey } from "./reports/reportModel";

/** Each agent field's row label on the card, by its Platform field name. */
export const AGENT_FIELD_LABELS: Readonly<Record<ReportAgentMetricKey, ProductTextKey>> = {
  agent_started_at: "product.edr.startedAt", engine_id: "product.edr.engine", rule_file_present: "product.edr.ruleFile",
  rule_set_state: "product.edrV3.ruleSet", rule_set_id: "product.edrV3.ruleSetId",
  behavior_rules_version: "product.edrV3.behaviorRules", sensor_state: "product.edr.sensorState",
  sensor_error_code: "product.edr.sensorError", service_config_state: "product.edrV3.serviceConfig",
  previous_run_end: "product.edrV3.previousRun", heartbeat_interval_seconds: "product.edrV3.heartbeat",
  realtime_scan_state: "product.edrV3.realtimeScan", file_change_sensor_state: "product.edrV3.fileChangeSensor",
  command_line_sensor_state: "product.edrV3.commandLineSensor", persistence_watch_state: "product.edrV3.persistenceWatch",
  response_channel_state: "product.edrV3.responseChannel", last_action_seq: "product.edrV3.lastAction",
  isolation_state: "product.edrV3.isolation", isolation_until: "product.edrV3.isolationUntil",
  isolation_checked_at: "product.edrV3.isolationChecked", quarantine_items: "product.edrV3.quarantine",
  events_queue_dropped: "product.edr.counter.events_queue_dropped", events_write_failed: "product.edr.counter.events_write_failed",
  events_unmapped: "product.edr.counter.events_unmapped", events_skipped: "product.edr.counter.events_skipped",
  events_evicted: "product.edr.counter.events_evicted", events_discarded: "product.edr.counter.events_discarded",
  events_degraded: "product.edr.counter.events_degraded", outbox_backlog: "product.edr.counter.outbox_backlog",
  scans_completed: "product.edr.counter.scans_completed", scans_detected: "product.edr.counter.scans_detected",
  scans_no_verdict: "product.edr.counter.scans_no_verdict", scan_jobs_dropped: "product.edr.counter.scan_jobs_dropped",
  scan_cache_hits: "product.edr.counter.scan_cache_hits", etw_events_lost: "product.edr.counter.etw_events_lost",
  file_change_gaps: "product.edr.counter.file_change_gaps", cmdline_unavailable: "product.edr.counter.cmdline_unavailable",
};
// The card's value tables, unchanged; "unknown" reads as display.unknown.
const EDR_SENSOR_LABELS: Readonly<Record<EdrSensorState, ProductTextKey>> = {
  started: "product.edr.sensor.started", lost: "product.edr.sensor.lost", failed: "product.edr.sensor.failed",
  stopped: "product.edr.sensor.stopped", disabled: "product.edr.sensor.disabled", unknown: "display.unknown",
};
const RULE_SET_LABELS: Readonly<Record<RuleSetState, ProductTextKey>> = {
  compiled: "product.edrV3.ruleSet.compiled", missing: "product.edrV3.ruleSet.missing",
  invalid: "product.edrV3.ruleSet.invalid", unreadable: "product.edrV3.ruleSet.unreadable", unknown: "display.unknown",
};
const CAPABILITY_LABELS: Readonly<Record<CapabilityState, ProductTextKey>> = {
  running: "product.edrV3.capability.running", degraded: "product.edrV3.capability.degraded",
  stopped: "product.edrV3.capability.stopped", failed: "product.edrV3.capability.failed",
  not_available: "product.edrV3.capability.not_available", unknown: "display.unknown",
};
const RESPONSE_CHANNEL_LABELS: Readonly<Record<ResponseChannelState, ProductTextKey>> = {
  ready: "product.edrV3.responseChannel.ready", not_configured: "product.edrV3.responseChannel.not_configured",
  awaiting_tenant_binding: "product.edrV3.responseChannel.awaiting_tenant_binding",
  journal_invalid: "product.edrV3.responseChannel.journal_invalid", unknown: "display.unknown",
};
const ISOLATION_LABELS: Readonly<Record<IsolationState, ProductTextKey>> = {
  inactive: "product.edrV3.isolation.inactive", active: "product.edrV3.isolation.active",
  partial: "product.edrV3.isolation.partial", unknown: "display.unknown",
};
const SERVICE_CONFIG_LABELS: Readonly<Record<ServiceConfigState, ProductTextKey>> = {
  as_installed: "product.edrV3.serviceConfig.as_installed", changed: "product.edrV3.serviceConfig.changed",
  unknown: "display.unknown",
};
const PREVIOUS_RUN_LABELS: Readonly<Record<PreviousRunEnd, ProductTextKey>> = {
  clean: "product.edrV3.previousRun.clean", unclean: "product.edrV3.previousRun.unclean",
  first_start: "product.edrV3.previousRun.first_start", unknown: "display.unknown",
};
/** The agent fields that take a closed state, each with the card's table for it. */
const AGENT_STATE_LABELS = {
  sensor_state: EDR_SENSOR_LABELS, rule_set_state: RULE_SET_LABELS, realtime_scan_state: CAPABILITY_LABELS,
  file_change_sensor_state: CAPABILITY_LABELS, command_line_sensor_state: CAPABILITY_LABELS,
  persistence_watch_state: CAPABILITY_LABELS, response_channel_state: RESPONSE_CHANNEL_LABELS,
  isolation_state: ISOLATION_LABELS, service_config_state: SERVICE_CONFIG_LABELS, previous_run_end: PREVIOUS_RUN_LABELS,
} as const satisfies Partial<Record<ReportAgentMetricKey, Readonly<Record<string, ProductTextKey>>>>;
export type AgentStateField = keyof typeof AGENT_STATE_LABELS;

export function isAgentStateField(field: string): field is AgentStateField {
  return Object.hasOwn(AGENT_STATE_LABELS, field);
}
/** The card's label for a closed state's value; display.unknown for any other value. */
export function agentStateLabel(field: AgentStateField, value: unknown): ProductTextKey {
  const labels: Readonly<Record<string, ProductTextKey>> = AGENT_STATE_LABELS[field];
  return typeof value === "string" && Object.hasOwn(labels, value) ? labels[value] ?? "display.unknown" : "display.unknown";
}
/** The agent's status as the card's heading reads it: "running" is only that its service loop reported it. */
export function agentStatusLabel(status: unknown): ProductTextKey {
  return status === "running" ? "product.edr.running" : "display.unknown";
}
/** Snapshot V2's rule file: whether the file is present, never that its rules are in effect. */
export function ruleFileLabel(present: unknown): ProductTextKey {
  return present === true ? "product.edr.ruleFile.present" : present === false ? "product.edr.ruleFile.absent" : "display.unknown";
}
/** The card's wording when the agent reports no sensor error code. */
export function sensorErrorAbsentLabel(sensorState: unknown): ProductTextKey {
  return sensorState === "lost" || sensorState === "failed" ? "product.edr.sensorError.notReported"
    : "product.edr.sensorError.notApplicable";
}
