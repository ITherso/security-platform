/** View state and display helpers for the device timeline and the alert list. No request, timer or authority. */
import type { Alert, AlertCursor, AlertPage, AlertRule, AlertSeverity, AlertStatus, ScanHitSeverity, SensorStateValue,
  TimelineEvent, TimelinePage } from '../../data/contracts';
import type { EventsTextKey } from '../../i18n/catalogs/events';
import type { ProductTextKey } from '../../i18n/catalogs/products';

export type LoadStatus = 'idle' | 'loading' | 'ready' | 'error';
export type BadgeTone = 'success' | 'warning' | 'danger' | 'neutral' | 'purple';
/** Explicit "Older" reads stop here, so one view never holds an unbounded table. */
export const MAX_TIMELINE_EVENTS = 1000;
export const MAX_LOADED_ALERTS = 500;
/** First device page read for alert labels and the device filter (the API's page maximum). */
export const ALERT_DEVICE_PAGE = 100;

/** Loaded timeline pages of one device, newest first, as one continuous list. */
export interface TimelineView {
  readonly deviceId: string;
  readonly events: readonly TimelineEvent[];
  readonly nextBeforeSeq: number | null;
  readonly capDeletedEvents: number;
  readonly suppressedAlerts: number;
  readonly readAt: string;
}
/** Loaded alert pages for one filter, newest activity first. */
export interface AlertListView {
  readonly items: readonly Alert[];
  readonly nextBefore: AlertCursor | null;
  readonly readAt: string;
}

/** Appends an older page; the normalizer already proved every new event is below the previous cursor. */
export function appendTimeline(current: TimelineView | null, page: TimelinePage, deviceId: string, readAt: string): TimelineView {
  const previous: readonly TimelineEvent[] = current !== null && current.deviceId === deviceId ? current.events : [];
  return Object.freeze({ deviceId, events: Object.freeze([...previous, ...page.items]), nextBeforeSeq: page.next_before_seq,
    capDeletedEvents: page.cap_deleted_events, suppressedAlerts: page.suppressed_alerts, readAt });
}
/** An alert updated between two reads can only move up; a repeated id keeps its first loaded row. */
export function appendAlerts(current: AlertListView | null, page: AlertPage, readAt: string): AlertListView {
  const previous: readonly Alert[] = current?.items ?? [];
  const known = new Set(previous.map((alert) => alert.id));
  return Object.freeze({ items: Object.freeze([...previous, ...page.items.filter((alert) => !known.has(alert.id))]),
    nextBefore: page.next_before, readAt });
}

export type TimelineRow = { readonly type: 'event'; readonly event: TimelineEvent }
  | { readonly type: 'gap'; readonly from: number; readonly to: number; readonly missing: number };
/** Marks every jump between consecutive loaded sequences, page boundaries included. */
export function timelineRows(events: readonly TimelineEvent[]): TimelineRow[] {
  const rows: TimelineRow[] = [];
  let newer: number | null = null;
  for (const event of events) {
    if (newer !== null && newer - event.event_seq > 1) {
      rows.push({ type: 'gap', from: event.event_seq + 1, to: newer - 1, missing: newer - event.event_seq - 1 });
    }
    rows.push({ type: 'event', event });
    newer = event.event_seq;
  }
  return rows;
}
export function sequenceRange(from: number, to: number): string {
  return from === to ? String(from) : `${String(from)}–${String(to)}`;
}
/** Windows exit codes above 16 bits are NTSTATUS-like values; show their hex form next to the decimal one. */
export function exitCodeText(code: number): string {
  return code > 0xffff ? `${String(code)} (0x${code.toString(16).toUpperCase().padStart(8, '0')})` : String(code);
}
export function shortDeviceId(id: string): string {
  return id.slice(0, 8).toUpperCase();
}

/** agent_silent's row label names the time instead (alerts.rule.agent_silent.since); this one has none. */
export const RULE_LABELS: Readonly<Record<AlertRule, EventsTextKey>> = {
  user_writable_launch: 'alerts.rule.user_writable_launch', office_browser_spawned_tool: 'alerts.rule.office_browser_spawned_tool',
  sensor_unstable: 'alerts.rule.sensor_unstable', event_loss: 'alerts.rule.event_loss',
  scan_detection: 'alerts.rule.scan_detection', behavior_match: 'alerts.rule.behavior_match',
  persistence_added: 'alerts.rule.persistence_added', capability_down: 'alerts.rule.capability_down',
  tamper_signal: 'alerts.rule.tamper_signal', agent_silent: 'alerts.rule.agent_silent',
};
/** What each rule matched; never a diagnosis. */
export const RULE_DESCRIPTIONS: Readonly<Record<AlertRule, EventsTextKey>> = {
  user_writable_launch: 'alerts.description.user_writable_launch',
  office_browser_spawned_tool: 'alerts.description.office_browser_spawned_tool',
  sensor_unstable: 'alerts.description.sensor_unstable', event_loss: 'alerts.description.event_loss',
  scan_detection: 'alerts.description.scan_detection', behavior_match: 'alerts.description.behavior_match',
  persistence_added: 'alerts.description.persistence_added', capability_down: 'alerts.description.capability_down',
  tamper_signal: 'alerts.description.tamper_signal', agent_silent: 'alerts.description.agent_silent',
};
export const STATUS_LABELS: Readonly<Record<AlertStatus, EventsTextKey>> = {
  open: 'alerts.status.open', acknowledged: 'alerts.status.acknowledged', closed: 'alerts.status.closed',
};
export const STATUS_TONES: Readonly<Record<AlertStatus, BadgeTone>> = { open: 'warning', acknowledged: 'purple', closed: 'neutral' };
export const SEVERITY_LABELS: Readonly<Record<AlertSeverity, ProductTextKey>> = { low: 'product.severity.low', medium: 'product.severity.medium' };
export const SEVERITY_TONES: Readonly<Record<AlertSeverity, BadgeTone>> = { low: 'neutral', medium: 'warning' };
export const KIND_LABELS: Readonly<Record<TimelineEvent['kind'], EventsTextKey>> = {
  process_started: 'events.kind.process_started', process_stopped: 'events.kind.process_stopped', sensor_state: 'events.kind.sensor_state',
  scan_detected: 'events.kind.scan_detected', behavior_match: 'events.kind.behavior_match',
  persistence_change: 'events.kind.persistence_change', agent_state: 'events.kind.agent_state',
  tamper_signal: 'events.kind.tamper_signal', coverage_gap: 'events.kind.coverage_gap',
};
/** A scan hit's severity is the rule file's own label for that rule, as the agent reported it. */
export const HIT_SEVERITY_LABELS: Readonly<Record<ScanHitSeverity, ProductTextKey>> = {
  low: 'product.severity.low', medium: 'product.severity.medium', high: 'product.severity.high',
};
export const SENSOR_STATE_LABELS: Readonly<Record<SensorStateValue, EventsTextKey>> = {
  started: 'events.state.started', lost: 'events.state.lost', failed: 'events.state.failed', stopped: 'events.state.stopped',
};
