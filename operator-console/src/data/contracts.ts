/** GET response dictionaries in inventory.py/audit.py/events.py/alerts.py and contracts.py states. */
/** contracts.PRODUCT_IDS: a V2 snapshot (Stage 2 step 3) adds the agent's own `edr_agent` status. */
export const PRODUCT_IDS = ["hostbasedfirewall", "termivar", "antivirus", "edr_agent"] as const;
export type ProductId = typeof PRODUCT_IDS[number];
export type TenantRole = "tenant_admin" | "viewer";
export type ClientMode = "demo" | "live";
export type DemoScenario = "normal" | "empty" | "error";
export type ClientErrorCode = "unauthorized" | "forbidden" | "not_found" | "rate_limited" | "offline"
  | "malformed" | "timeout" | "aborted" | "disconnected" | "invalid_input" | "https_required" | "server_error";

export class ClientError extends Error {
  readonly code: ClientErrorCode;
  readonly status: number | null;
  constructor(code: ClientErrorCode, status: number | null = null) {
    super(code);
    this.name = "ClientError";
    this.code = code;
    this.status = status;
  }
}

export interface SourceClaims {
  readonly source: "self_reported";
  readonly producer_verification: "not_verified";
}
export interface AgeObservation {
  readonly age_seconds: number | null;
  readonly clock_state: "unknown" | "future" | "not_verified";
}
export interface Tenant {
  readonly id: string;
  readonly name: string;
  readonly role: TenantRole;
}
export interface Device extends SourceClaims {
  readonly id: string;
  readonly tenant_id: string;
  readonly label: string;
  readonly identity_status: "active" | "revoked";
  readonly connection_status: "recent" | "stale" | "never_seen";
  readonly created_at: string;
  readonly revoked_at: string | null;
  readonly last_sequence: number | null;
  readonly last_received_at: string | null;
  readonly source_observed_at: string | null;
  readonly source_observation: AgeObservation;
}
export interface DispositionCounts {
  readonly informational: number;
  readonly needs_review: number;
  readonly confirmed: number;
}
export interface SeverityCounts {
  readonly unassigned: number;
  readonly info: number;
  readonly low: number;
  readonly medium: number;
  readonly high: number;
  readonly critical: number;
}
export interface TermivarSummary extends SourceClaims {
  readonly digest: string;
  readonly report_schema: "venom-rendered-assessment/v1";
  readonly imported_at: string;
  readonly subject_count: number;
  readonly item_count: number;
  readonly counts: DispositionCounts;
  readonly severity_counts: SeverityCounts;
  readonly scope: "offline_report_summary";
}
export interface ReportedProduct extends SourceClaims {
  readonly catalog_available: boolean | null;
  readonly version: string | null;
  readonly source_observed_at: string | null;
}
export const HBF_ERROR_CODES = ["config_error", "policy_error", "temp_error", "runtime_error", "telemetry_error",
  "history_error", "network_profile_error", "recovery_error", "application_rule_recovery_error",
  "liveness_error", "application_usage_error", "maintenance", "health_unavailable", "unknown_error"] as const;
export type HbfErrorCode = typeof HBF_ERROR_CODES[number];
export interface HostBasedFirewallState extends ReportedProduct {
  readonly product_id: "hostbasedfirewall";
  readonly status: "running" | "observing" | "degraded" | "stopped" | "unavailable" | "unknown";
  readonly installed: boolean | null;
  readonly reported_running: boolean | null;
  readonly reported_stale: boolean | null;
  readonly firewall_mode: "enforce" | "sniff" | "unknown";
  readonly error_codes: readonly HbfErrorCode[] | null;
}
export interface TermivarState extends ReportedProduct {
  readonly product_id: "termivar";
  readonly status: "experimental" | "unknown";
  readonly scanner_installed: boolean | null;
  readonly execution_available: false | null;
  readonly report_presence: "present" | "none" | "unknown";
  readonly latest_report: TermivarSummary | null;
}
export interface AntivirusState extends ReportedProduct {
  readonly product_id: "antivirus";
  readonly catalog_available: false | null;
  readonly version: null;
  readonly status: "planned" | "unknown";
  readonly availability: "unavailable" | "unknown";
  readonly execution_available: false | null;
}
/** contracts.EdrAgentStatus: the Altay EDR agent's own self-reported state, never a protection claim. */
export const EDR_SENSOR_STATES = ["started", "lost", "failed", "stopped", "disabled", "unknown"] as const;
export type EdrSensorState = typeof EDR_SENSOR_STATES[number];
/** Counts since the agent process started, and the outbox backlog; each a safe integer or null. */
export const EDR_COUNTER_KEYS = ["events_queue_dropped", "events_write_failed", "events_unmapped", "events_skipped",
  "events_evicted", "events_discarded", "events_degraded", "outbox_backlog"] as const;
export type EdrCounterKey = typeof EDR_COUNTER_KEYS[number];
export type EdrAgentState = ReportedProduct & { readonly [K in EdrCounterKey]: number | null } & {
  readonly product_id: "edr_agent";
  readonly catalog_available: null;
  /** "running": only that the agent's service loop reported it. */
  readonly status: "running" | "unknown";
  readonly agent_started_at: string | null;
  readonly engine_id: string | null;
  /** Presence of the rule file only; never that rules are loaded. */
  readonly rule_file_present: boolean | null;
  readonly sensor_state: EdrSensorState;
  /** Only with sensor_state lost or failed. */
  readonly sensor_error_code: SensorErrorCode | null;
};
/** contracts.EdrAgentStatusV3 closed sets (Snapshot V3). Every value stays the agent's own claim. */
export const RULE_SET_STATES = ["compiled", "missing", "invalid", "unreadable", "unknown"] as const;
export type RuleSetState = typeof RULE_SET_STATES[number];
export const CAPABILITY_STATES = ["running", "degraded", "stopped", "failed", "not_available", "unknown"] as const;
export type CapabilityState = typeof CAPABILITY_STATES[number];
export const RESPONSE_CHANNEL_STATES = ["ready", "not_configured", "awaiting_tenant_binding", "journal_invalid", "unknown"] as const;
export type ResponseChannelState = typeof RESPONSE_CHANNEL_STATES[number];
export const RESPONSE_ACTIONS = ["scan_path", "terminate_process", "quarantine_file", "restore_file", "isolate_host",
  "release_host"] as const;
export type ResponseAction = typeof RESPONSE_ACTIONS[number];
export const ISOLATION_STATES = ["inactive", "active", "partial", "unknown"] as const;
export type IsolationState = typeof ISOLATION_STATES[number];
export const SERVICE_CONFIG_STATES = ["as_installed", "changed", "unknown"] as const;
export type ServiceConfigState = typeof SERVICE_CONFIG_STATES[number];
export const PREVIOUS_RUN_ENDS = ["clean", "unclean", "first_start", "unknown"] as const;
export type PreviousRunEnd = typeof PREVIOUS_RUN_ENDS[number];
/** contracts.EDR_V3_COUNTER_KEYS: the V2 counters, then the Stage 3 ones; each a safe integer (saturating) or null. */
export const EDR_V3_COUNTER_KEYS = ["events_queue_dropped", "events_write_failed", "events_unmapped", "events_skipped",
  "events_evicted", "events_discarded", "events_degraded", "outbox_backlog", "scans_completed", "scans_detected",
  "scans_no_verdict", "scan_jobs_dropped", "scan_cache_hits", "etw_events_lost", "file_change_gaps",
  "cmdline_unavailable"] as const;
export type EdrV3CounterKey = typeof EDR_V3_COUNTER_KEYS[number];
/** The four V3 fields that take a CAPABILITY_STATES value. */
export const EDR_CAPABILITY_KEYS = ["realtime_scan_state", "file_change_sensor_state", "command_line_sensor_state",
  "persistence_watch_state"] as const;
export type EdrCapabilityKey = typeof EDR_CAPABILITY_KEYS[number];
/** Snapshot V3's edr_agent state: every V2 field but rule_file_present, and the Stage 3 states and counters. The
 * console tells it from V2 by its key set (rule_set_state, and no rule_file_present). */
export type EdrAgentStateV3 = ReportedProduct & { readonly [K in EdrV3CounterKey]: number | null }
  & { readonly [K in EdrCapabilityKey]: CapabilityState } & {
  readonly product_id: "edr_agent";
  readonly catalog_available: null;
  /** "running": only that the agent's service loop reported it. */
  readonly status: "running" | "unknown";
  readonly agent_started_at: string | null;
  readonly engine_id: string | null;
  readonly sensor_state: EdrSensorState;
  /** Only with sensor_state lost or failed. */
  readonly sensor_error_code: SensorErrorCode | null;
  /** "compiled" says only that the agent compiled its rule file in this process. */
  readonly rule_set_state: RuleSetState;
  readonly rule_set_id: string | null;
  readonly response_channel_state: ResponseChannelState;
  /** Unique and sorted. */
  readonly response_actions_enabled: readonly ResponseAction[];
  /** At most 4 lowercase 64-hex IDs, unique and sorted. */
  readonly response_key_ids: readonly string[];
  readonly last_action_seq: number | null;
  /** "active" says only that the agent reports its own filters in place. */
  readonly isolation_state: IsolationState;
  readonly isolation_until: string | null;
  readonly isolation_checked_at: string | null;
  readonly quarantine_items: number | null;
  readonly service_config_state: ServiceConfigState;
  readonly previous_run_end: PreviousRunEnd;
  /** 30..3600, the agent's own heartbeat range. */
  readonly heartbeat_interval_seconds: number | null;
  readonly behavior_rules_version: string | null;
};
export type ProductState = HostBasedFirewallState | TermivarState | AntivirusState | EdrAgentState | EdrAgentStateV3;
interface ProductRecordBase<S extends ProductState> {
  readonly product_id: S["product_id"];
  readonly snapshot_sequence: number;
  readonly received_at: string;
  readonly observation: AgeObservation;
  readonly state: S;
}
export type ProductRecord = ProductRecordBase<HostBasedFirewallState>
  | (ProductRecordBase<TermivarState> & { readonly report_import_age: AgeObservation })
  | ProductRecordBase<AntivirusState>
  | ProductRecordBase<EdrAgentState | EdrAgentStateV3>;
export interface DeviceDetail extends Device {
  readonly products: readonly ProductRecord[];
  readonly missing_products: readonly ProductId[];
}
export type AuditAction = "tenant_created" | "membership_set" | "membership_revoked" | "enrollment_grant_created"
  | "enrollment_grant_revoked" | "device_enrolled" | "device_revoked" | "device_credential_rotated"
  | "tenant_event_retention_set" | "alert_acknowledged" | "alert_closed" | "tenant_alert_retention_set"
  | "alerts_pruned";
export type AuditObject = "tenant" | "membership" | "enrollment_grant" | "device" | "device_credential" | "alert";
export interface AuditEvent {
  readonly id: string;
  readonly tenant_id: string;
  readonly actor_type: "operator" | "device" | "local_admin";
  readonly actor_id: string | null;
  readonly action: AuditAction;
  readonly object_type: AuditObject;
  readonly object_id: string;
  readonly outcome: "success";
  readonly created_at: string;
}
export interface Page<T> {
  readonly items: readonly T[];
  readonly next_offset: number | null;
}
export type TenantPage = Page<Tenant>;
export type DevicePage = Page<Device>;
export type AuditPage = Page<AuditEvent>;

/** altay-edr-event/v1 and v2 timeline items (events.py `_event_view`); every event stays a device claim. */
export const SENSOR_STATES = ["started", "lost", "failed", "stopped"] as const;
export type SensorStateValue = typeof SENSOR_STATES[number];
export const SENSOR_ERROR_CODES = ["session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
  "session_stop_failed", "unknown"] as const;
export type SensorErrorCode = typeof SENSOR_ERROR_CODES[number];
/** event_contracts.EVENT_KINDS: the three v1 kinds, then the six v2 kinds. */
export const EVENT_KINDS = ["process_started", "process_stopped", "sensor_state", "scan_detected", "behavior_match",
  "persistence_change", "agent_state", "tamper_signal", "coverage_gap"] as const;
export type EventKind = typeof EVENT_KINDS[number];
/** event_contracts.EVENT_FIELDS: each kind's fields in a timeline item, v1 and v2 together, in the Platform's order.
 * A v1 row has null in the fields only v2 carries. */
export const EVENT_FIELDS = {
  process_started: ["pid", "parent_pid", "session_id", "image", "create_time", "parent_create_time"],
  process_stopped: ["pid", "exit_code", "image", "create_time"],
  sensor_state: ["state", "error_code"],
  scan_detected: ["trigger", "path", "size", "sha256", "rule_set_id", "hits", "omitted_hits", "pid", "create_time",
    "action_id"],
  behavior_match: ["rule", "rule_version", "pid", "create_time", "image", "parent_image", "found_at_start",
    "command_line_source"],
  persistence_change: ["location", "scope", "change", "entry_id", "target_image", "found_at_start"],
  agent_state: ["subject", "state", "code", "rule_set_id"],
  tamper_signal: ["signal", "detail"],
  coverage_gap: ["source", "reason", "lost"],
} as const satisfies Readonly<Record<EventKind, readonly string[]>>;
/** event_contracts.EVENT_VIEW_FIELDS: the name of each EVENT_FIELDS entry in a timeline item, position by position.
 * Only coverage_gap differs: its own `source` arrives as `gap_source`, because `source` is the item's claim key. */
export const EVENT_VIEW_FIELDS = {
  ...EVENT_FIELDS,
  coverage_gap: ["gap_source", "reason", "lost"],
} as const satisfies Readonly<Record<EventKind, readonly string[]>>;
/** The v2 closed sets of event_contracts. */
export const SCAN_TRIGGERS = ["process_start", "startup_scan", "file_change", "remote_scan", "persistence_target"] as const;
export type ScanTrigger = typeof SCAN_TRIGGERS[number];
export const SCAN_HIT_SEVERITIES = ["low", "medium", "high"] as const;
export type ScanHitSeverity = typeof SCAN_HIT_SEVERITIES[number];
export const BEHAVIOR_RULES = ["encoded_powershell", "powershell_download_cradle", "certutil_download_or_decode",
  "mshta_remote_or_script", "regsvr32_scriptlet", "rundll32_script", "bitsadmin_transfer", "shadow_copy_deletion",
  "defender_tampering_command", "event_log_clearing_command"] as const;
export type BehaviorRule = typeof BEHAVIOR_RULES[number];
export const COMMAND_LINE_SOURCES = ["kernel_logger", "process_query"] as const;
export type CommandLineSource = typeof COMMAND_LINE_SOURCES[number];
export const PERSISTENCE_LOCATIONS = ["run_key", "run_once_key", "service", "scheduled_task", "startup_folder"] as const;
export type PersistenceLocation = typeof PERSISTENCE_LOCATIONS[number];
export const PERSISTENCE_SCOPES = ["machine", "user"] as const;
export type PersistenceScope = typeof PERSISTENCE_SCOPES[number];
export const PERSISTENCE_CHANGES = ["added", "modified", "removed"] as const;
export type PersistenceChange = typeof PERSISTENCE_CHANGES[number];
/** event_contracts.AGENT_STATE_SUBJECTS: each subject and the states it allows, in the Platform's order. */
export const AGENT_STATE_SUBJECTS = {
  service: ["started", "stopping"],
  rule_set: ["compiled", "missing", "invalid", "unreadable"],
  realtime_scan: ["running", "degraded", "stopped", "failed"],
  file_change_sensor: ["running", "degraded", "stopped", "failed", "not_available"],
  command_line_sensor: ["running", "degraded", "stopped", "failed", "not_available"],
  persistence_watch: ["running", "degraded", "stopped", "failed", "not_available", "baseline_created"],
  response_channel: ["ready", "not_configured", "awaiting_tenant_binding", "journal_invalid"],
  isolation: ["active", "renewed", "released", "expired", "released_locally", "reverted_no_contact", "reapplied"],
  quarantine: ["restored_locally"],
} as const;
export type AgentStateSubject = keyof typeof AGENT_STATE_SUBJECTS;
export type AgentStatePair = { [S in AgentStateSubject]: { readonly subject: S; readonly state: typeof AGENT_STATE_SUBJECTS[S][number] } }[AgentStateSubject];
/** A code only with (service, started). */
export const AGENT_STATE_CODES = ["first_start", "clean_stop", "unclean_stop"] as const;
export type AgentStateCode = typeof AGENT_STATE_CODES[number];
export const TAMPER_SIGNALS = ["service_config_changed", "service_dacl_changed", "data_dir_acl_changed",
  "isolation_filters_missing", "isolation_filters_disabled", "isolation_released_locally", "event_log_cleared",
  "response_trust_changed", "previous_run_unclean", "quarantine_changed"] as const;
export type TamperSignal = typeof TAMPER_SIGNALS[number];
/** Required for event_log_cleared, null for every other signal. */
export const TAMPER_DETAILS = ["security", "system"] as const;
export type TamperDetail = typeof TAMPER_DETAILS[number];
/** coverage_gap.source on the wire: the part of the agent that lost records. A timeline item shows it as
 * `gap_source` (EVENT_VIEW_FIELDS), because `source` there is the claim key. */
export const COVERAGE_SOURCES = ["process_sensor", "file_change_sensor", "command_line_sensor", "agent_records"] as const;
export type CoverageSource = typeof COVERAGE_SOURCES[number];
export const COVERAGE_REASONS = ["etw_events_lost", "usn_journal_reset", "usn_entries_deleted", "volume_unmonitored",
  "queue_overflow"] as const;
export type CoverageReason = typeof COVERAGE_REASONS[number];
interface TimelineEventBase extends SourceClaims {
  readonly event_seq: number;
  readonly observed_at: string;
  readonly received_at: string;
}
export interface ProcessStartedEvent extends TimelineEventBase {
  readonly kind: "process_started";
  readonly pid: number;
  readonly parent_pid: number;
  readonly session_id: number;
  readonly image: string;
  /** v2: the payload's CreateTime; null on a v1 row. */
  readonly create_time: string | null;
  /** v2, beside create_time only; null on a v1 row or when the agent did not send it. */
  readonly parent_create_time: string | null;
}
export interface ProcessStoppedEvent extends TimelineEventBase {
  readonly kind: "process_stopped";
  readonly pid: number;
  readonly exit_code: number | null;
  readonly image: string | null;
  /** v2 and optional; null on a v1 row. */
  readonly create_time: string | null;
}
export interface SensorStateEvent extends TimelineEventBase {
  readonly kind: "sensor_state";
  readonly state: SensorStateValue;
  readonly error_code: SensorErrorCode | null;
}
export interface ScanHit { readonly rule: string; readonly severity: ScanHitSeverity }
/** scan_detected's fields, also the scan_detection alert's evidence. The only kind with a file SHA-256 and size. */
export interface ScanDetectedFields {
  readonly trigger: ScanTrigger;
  readonly path: string;
  readonly size: number;
  readonly sha256: string;
  readonly rule_set_id: string;
  /** 1-8 rule matches, no rule twice; omitted_hits counts the ones the agent left out. */
  readonly hits: readonly ScanHit[];
  readonly omitted_hits: number;
  readonly pid: number | null;
  /** Only beside a pid. */
  readonly create_time: string | null;
  readonly action_id: string | null;
}
/** behavior_match's fields, also the behavior_match alert's evidence; never any command-line text. */
export interface BehaviorMatchFields {
  readonly rule: BehaviorRule;
  readonly rule_version: number;
  readonly pid: number;
  readonly create_time: string;
  readonly image: string;
  readonly parent_image: string | null;
  readonly found_at_start: boolean;
  readonly command_line_source: CommandLineSource;
}
export interface PersistenceChangeFields<C extends PersistenceChange = PersistenceChange> {
  readonly location: PersistenceLocation;
  readonly scope: PersistenceScope;
  readonly change: C;
  readonly entry_id: string;
  readonly target_image: string | null;
  readonly found_at_start: boolean;
}
export type AgentStateFields = AgentStatePair & { readonly code: AgentStateCode | null; readonly rule_set_id: string | null };
export type TamperSignalFields = { readonly signal: "event_log_cleared"; readonly detail: TamperDetail }
  | { readonly signal: Exclude<TamperSignal, "event_log_cleared">; readonly detail: null };
export type ScanDetectedEvent = TimelineEventBase & ScanDetectedFields & { readonly kind: "scan_detected" };
export type BehaviorMatchEvent = TimelineEventBase & BehaviorMatchFields & { readonly kind: "behavior_match" };
export type PersistenceChangeEvent = TimelineEventBase & PersistenceChangeFields & { readonly kind: "persistence_change" };
export type AgentStateEvent = TimelineEventBase & AgentStateFields & { readonly kind: "agent_state" };
export type TamperSignalEvent = TimelineEventBase & TamperSignalFields & { readonly kind: "tamper_signal" };
/** The gap's own `source` arrives as `gap_source` (EVENT_VIEW_FIELDS); `source` in the item is the claim. */
export interface CoverageGapEvent extends TimelineEventBase {
  readonly kind: "coverage_gap";
  readonly gap_source: CoverageSource;
  readonly reason: CoverageReason;
  readonly lost: number | null;
}
export type TimelineEvent = ProcessStartedEvent | ProcessStoppedEvent | SensorStateEvent | ScanDetectedEvent
  | BehaviorMatchEvent | PersistenceChangeEvent | AgentStateEvent | TamperSignalEvent | CoverageGapEvent;
export interface TimelinePage {
  readonly items: readonly TimelineEvent[];
  readonly next_before_seq: number | null;
  readonly cap_deleted_events: number;
  readonly suppressed_alerts: number;
}

/** Rule matches of alerts.py (alerts.RULES, the SEVERITY order). A match is not a diagnosis; the source stays
 * self_reported/not_verified. */
export const ALERT_RULES = ["user_writable_launch", "office_browser_spawned_tool", "sensor_unstable", "event_loss",
  "scan_detection", "behavior_match", "persistence_added", "capability_down", "tamper_signal", "agent_silent"] as const;
export type AlertRule = typeof ALERT_RULES[number];
export const ALERT_STATUSES = ["open", "acknowledged", "closed"] as const;
export type AlertStatus = typeof ALERT_STATUSES[number];
export type AlertSeverity = "low" | "medium";
/** The agent_state (subject, state) pairs that raise capability_down; every other pair raises nothing. */
export const CAPABILITY_DOWN_STATES = {
  realtime_scan: ["stopped", "failed"],
  rule_set: ["missing", "invalid", "unreadable"],
  file_change_sensor: ["failed"],
  command_line_sensor: ["failed"],
  persistence_watch: ["failed"],
  response_channel: ["journal_invalid"],
} as const;
type CapabilityDownSubject = keyof typeof CAPABILITY_DOWN_STATES;
export type CapabilityDownEvidence = { [S in CapabilityDownSubject]: { readonly subject: S;
  readonly state: typeof CAPABILITY_DOWN_STATES[S][number] } }[CapabilityDownSubject]
  & { readonly code: null; readonly rule_set_id: string | null };
interface AlertCommon extends SourceClaims {
  readonly id: string;
  readonly device_id: string;
  readonly status: AlertStatus;
  readonly occurrences: number;
  readonly first_seen_at: string;
  readonly last_seen_at: string;
  readonly acknowledged_at: string | null;
  readonly closed_at: string | null;
}
/** An alert raised by events: the event_seq range of its matches. */
interface AlertBase extends AlertCommon {
  readonly first_event_seq: number;
  readonly last_event_seq: number;
}
export interface UserWritableLaunchAlert extends AlertBase {
  readonly rule: "user_writable_launch";
  readonly severity: "low";
  readonly evidence: { readonly image: string; readonly pid: number };
}
export interface SpawnedToolAlert extends AlertBase {
  readonly rule: "office_browser_spawned_tool";
  readonly severity: "medium";
  readonly evidence: { readonly image: string; readonly pid: number; readonly parent_image: string; readonly parent_pid: number };
}
export interface SensorUnstableAlert extends AlertBase {
  readonly rule: "sensor_unstable";
  readonly severity: "medium";
  readonly evidence: { readonly state: "lost" | "failed"; readonly error_code: SensorErrorCode | null };
}
export interface EventLossAlert extends AlertBase {
  readonly rule: "event_loss";
  readonly severity: "medium";
  readonly evidence: { readonly missing_events: number };
}
/** The evidence of the five Stage 3 event rules is the triggering event's own fields, under the same names. */
export interface ScanDetectionAlert extends AlertBase {
  readonly rule: "scan_detection";
  readonly severity: "medium";
  readonly evidence: ScanDetectedFields;
}
export interface BehaviorMatchAlert extends AlertBase {
  readonly rule: "behavior_match";
  /** From the server's table per rule ID, never from the agent. */
  readonly severity: "medium";
  readonly evidence: BehaviorMatchFields;
}
export interface PersistenceAddedAlert extends AlertBase {
  readonly rule: "persistence_added";
  readonly severity: "low";
  /** "removed" raises nothing. */
  readonly evidence: PersistenceChangeFields<"added" | "modified">;
}
export interface CapabilityDownAlert extends AlertBase {
  readonly rule: "capability_down";
  readonly severity: "medium";
  readonly evidence: CapabilityDownEvidence;
}
export interface TamperSignalAlert extends AlertBase {
  readonly rule: "tamper_signal";
  readonly severity: "medium";
  readonly evidence: TamperSignalFields;
}
/** Opened by `security-platform sweep` from the server clock, never by an event: the one rule whose event sequences
 * are null. */
export interface AgentSilentAlert extends AlertCommon {
  readonly rule: "agent_silent";
  readonly severity: "medium";
  readonly first_event_seq: null;
  readonly last_event_seq: null;
  readonly evidence: { readonly last_received_at: string; readonly threshold_seconds: number };
}
export type Alert = UserWritableLaunchAlert | SpawnedToolAlert | SensorUnstableAlert | EventLossAlert | ScanDetectionAlert
  | BehaviorMatchAlert | PersistenceAddedAlert | CapabilityDownAlert | TamperSignalAlert | AgentSilentAlert;
/** Keyset position of the alert list: (last_seen_at, id), newest first. */
export interface AlertCursor { readonly seen_at: string; readonly id: string }
export interface AlertPage {
  readonly items: readonly Alert[];
  readonly next_before: AlertCursor | null;
}

export interface RequestOptions { readonly signal?: AbortSignal }
export interface PageOptions extends RequestOptions { readonly limit?: number; readonly offset?: number }
export interface TimelineOptions extends RequestOptions { readonly limit?: number; readonly beforeSeq?: number }
export interface AlertOptions extends RequestOptions {
  readonly limit?: number;
  readonly status?: AlertStatus;
  readonly deviceId?: string;
  readonly before?: AlertCursor;
}
export interface DataClient {
  readonly mode: ClientMode;
  readonly sourceLabel: string;
  readonly referenceTime: string | null;
  readonly apiBase: string | null;
  readonly scenario: DemoScenario | null;
  listTenants(options?: PageOptions): Promise<TenantPage>;
  listDevices(tenantId: string, options?: PageOptions): Promise<DevicePage>;
  getDevice(tenantId: string, deviceId: string, options?: RequestOptions): Promise<DeviceDetail>;
  listAudit(tenantId: string, options?: PageOptions): Promise<AuditPage>;
  listDeviceEvents(tenantId: string, deviceId: string, options?: TimelineOptions): Promise<TimelinePage>;
  listAlerts(tenantId: string, options?: AlertOptions): Promise<AlertPage>;
  disconnect(): void;
}
