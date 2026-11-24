/** GET response dictionaries in inventory.py/audit.py/events.py/alerts.py and contracts.py states. */
export const PRODUCT_IDS = ["hostbasedfirewall", "termivar", "antivirus"] as const;
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
export type ProductState = HostBasedFirewallState | TermivarState | AntivirusState;
interface ProductRecordBase<S extends ProductState> {
  readonly product_id: S["product_id"];
  readonly snapshot_sequence: number;
  readonly received_at: string;
  readonly observation: AgeObservation;
  readonly state: S;
}
export type ProductRecord = ProductRecordBase<HostBasedFirewallState>
  | (ProductRecordBase<TermivarState> & { readonly report_import_age: AgeObservation })
  | ProductRecordBase<AntivirusState>;
export interface DeviceDetail extends Device {
  readonly products: readonly ProductRecord[];
  readonly missing_products: readonly ProductId[];
}
export type AuditAction = "tenant_created" | "membership_set" | "membership_revoked" | "enrollment_grant_created"
  | "enrollment_grant_revoked" | "device_enrolled" | "device_revoked" | "device_credential_rotated"
  | "tenant_event_retention_set" | "alert_acknowledged" | "alert_closed";
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

/** altay-edr-event/v1 timeline items (events.py `_event_view`); every event stays a device claim. */
export const SENSOR_STATES = ["started", "lost", "failed", "stopped"] as const;
export type SensorStateValue = typeof SENSOR_STATES[number];
export const SENSOR_ERROR_CODES = ["session_name_invalid", "session_in_use", "access_denied", "session_start_failed",
  "session_stop_failed", "unknown"] as const;
export type SensorErrorCode = typeof SENSOR_ERROR_CODES[number];
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
}
export interface ProcessStoppedEvent extends TimelineEventBase {
  readonly kind: "process_stopped";
  readonly pid: number;
  readonly exit_code: number | null;
  readonly image: string | null;
}
export interface SensorStateEvent extends TimelineEventBase {
  readonly kind: "sensor_state";
  readonly state: SensorStateValue;
  readonly error_code: SensorErrorCode | null;
}
export type TimelineEvent = ProcessStartedEvent | ProcessStoppedEvent | SensorStateEvent;
export interface TimelinePage {
  readonly items: readonly TimelineEvent[];
  readonly next_before_seq: number | null;
  readonly cap_deleted_events: number;
  readonly suppressed_alerts: number;
}

/** Rule matches of alerts.py. A match is not a diagnosis; the source stays self_reported/not_verified. */
export const ALERT_RULES = ["user_writable_launch", "office_browser_spawned_tool", "sensor_unstable", "event_loss"] as const;
export type AlertRule = typeof ALERT_RULES[number];
export const ALERT_STATUSES = ["open", "acknowledged", "closed"] as const;
export type AlertStatus = typeof ALERT_STATUSES[number];
export type AlertSeverity = "low" | "medium";
interface AlertBase extends SourceClaims {
  readonly id: string;
  readonly device_id: string;
  readonly status: AlertStatus;
  readonly occurrences: number;
  readonly first_event_seq: number;
  readonly last_event_seq: number;
  readonly first_seen_at: string;
  readonly last_seen_at: string;
  readonly acknowledged_at: string | null;
  readonly closed_at: string | null;
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
export type Alert = UserWritableLaunchAlert | SpawnedToolAlert | SensorUnstableAlert | EventLossAlert;
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
