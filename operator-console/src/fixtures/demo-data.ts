/** Synthetic DTO-shaped fixtures. No real device/account/security action. */
import { EDR_COUNTER_KEYS, EDR_V3_COUNTER_KEYS, PRODUCT_IDS } from "../data/contracts";
import type { AgeObservation, AgentStateFields, Alert, AlertStatus, AntivirusState, AuditEvent, BehaviorMatchFields,
  CoverageReason, CoverageSource, Device, DeviceDetail, EdrAgentState, EdrAgentStateV3, EdrCounterKey, EdrSensorState, EdrV3CounterKey,
  HostBasedFirewallState, HbfErrorCode, PersistenceChangeFields, ProductRecord, ProductState, ReportedProduct,
  ScanDetectedFields, SensorErrorCode, SensorStateValue, SourceClaims, TamperSignalFields, Tenant, TermivarState,
  TimelineEvent } from "../data/contracts";

export const DEMO_TENANT_IDS = ["10000000-0000-4000-8000-000000000001", "10000000-0000-4000-8000-000000000002"] as const;
/** One device's stored events, newest first, with the platform's counters for it. */
export interface DemoTimeline {
  readonly deviceId: string;
  readonly events: readonly TimelineEvent[];
  readonly capDeletedEvents: number;
  readonly suppressedAlerts: number;
}
export interface DemoDataset {
  readonly tenants: readonly Tenant[];
  readonly devices: readonly DeviceDetail[];
  readonly audit: readonly AuditEvent[];
  readonly timelines: readonly DemoTimeline[];
  readonly alerts: readonly Alert[];
  readonly referenceTime: string;
}
interface DeviceSpec {
  n: number; tenant: 0 | 1; label: string; connection: Device["connection_status"];
  received: number | null; observed: number | null; sequence: number | null; revoked?: number;
  states: ProductState[];
}
const claims: SourceClaims = { source: "self_reported", producer_verification: "not_verified" };

export function createDemoData(): DemoDataset {
  const now = Date.now();
  const at = (secondsAgo: number): string => new Date(now - secondsAgo * 1000).toISOString();
  const observation = (seconds: number | null): AgeObservation => seconds === null
    ? { age_seconds: null, clock_state: "unknown" }
    : seconds < 0 ? { age_seconds: null, clock_state: "future" } : { age_seconds: seconds, clock_state: "not_verified" };
  const base = (observed: number | null, version: string | null = null, available: boolean | null = null): ReportedProduct => ({
    catalog_available: available, ...claims, version, source_observed_at: observed === null ? null : at(observed),
  });
  const firewall = (status: HostBasedFirewallState["status"], mode: HostBasedFirewallState["firewall_mode"],
    observed: number, errors: HbfErrorCode[] = []): HostBasedFirewallState => ({
    ...base(observed, "1.4.3", true), product_id: "hostbasedfirewall", status, installed: true,
    reported_running: ["running", "observing", "degraded"].includes(status), reported_stale: false,
    firewall_mode: mode, error_codes: errors,
  });
  const termivar = (observed: number, withReport: boolean, index = 0): TermivarState => ({
    ...base(observed, null, true), product_id: "termivar", status: "experimental", scanner_installed: null,
    execution_available: false, report_presence: withReport ? "present" : "none", latest_report: withReport ? {
      digest: (index ? "b" : "a").repeat(64), report_schema: "venom-rendered-assessment/v1",
      imported_at: at(index ? 172800 : 7200), subject_count: 1, item_count: index ? 6 : 8,
      counts: { informational: index ? 4 : 5, needs_review: index ? 2 : 3, confirmed: 0 },
      severity_counts: { unassigned: index ? 6 : 8, info: 0, low: 0, medium: 0, high: 0, critical: 0 },
      ...claims, scope: "offline_report_summary",
    } : null,
  });
  const antivirus = (): AntivirusState => ({ ...base(null), catalog_available: false, version: null,
    product_id: "antivirus", status: "planned", availability: "unavailable", execution_available: false });
  /** The agent's own status (Snapshot V2); `counts` null is the one-shot CLI heartbeat, which knows no counters. */
  const edrAgent = (observed: number, sensor: EdrSensorState, options: { started?: number | null;
    code?: SensorErrorCode; ruleFile?: boolean | null; counts?: readonly number[] | null } = {}): EdrAgentState => {
    const counts = options.counts === undefined ? [0, 0, 0, 0, 0, 0, 0, 0] : options.counts;
    const counters = Object.fromEntries(EDR_COUNTER_KEYS.map((key, index) =>
      [key, counts === null ? null : counts[index] ?? 0])) as { readonly [K in EdrCounterKey]: number | null };
    const started = options.started === undefined ? observed + 14400 : options.started;
    return { ...base(observed, "0.3.0"), ...counters, catalog_available: null, product_id: "edr_agent",
      status: counts === null ? "unknown" : "running", agent_started_at: started === null ? null : at(started),
      engine_id: "edr-agent/0.3.0", rule_file_present: options.ruleFile === undefined ? true : options.ruleFile,
      sensor_state: sensor, sensor_error_code: options.code ?? null };
  };
  /** A sample Snapshot V3 agent state: every V2 key but rule_file_present, and the Stage 3 states and counters. The
   * rule set ID is a visibly fake pattern; no rule file exists. */
  const edrAgentV3 = (observed: number): EdrAgentStateV3 => {
    // EDR_V3_COUNTER_KEYS order: the eight V2 counters, then scans completed, detected, without a result, jobs
    // dropped, cache hits, ETW events lost, file change gaps, processes without a command line.
    const counts = [0, 0, 0, 0, 0, 0, 0, 2, 1840, 1, 3, 0, 912, 14, 1, 2];
    const counters = Object.fromEntries(EDR_V3_COUNTER_KEYS.map((key, index) =>
      [key, counts[index] ?? 0])) as { readonly [K in EdrV3CounterKey]: number | null };
    return { ...base(observed, "0.4.0"), ...counters, catalog_available: null, product_id: "edr_agent", status: "running",
      agent_started_at: at(observed + 86400), engine_id: "edr-agent/0.4.0", sensor_state: "started", sensor_error_code: null,
      rule_set_state: "compiled", rule_set_id: "0123456789abcdef".repeat(4), realtime_scan_state: "running",
      file_change_sensor_state: "degraded", command_line_sensor_state: "running", persistence_watch_state: "running",
      response_channel_state: "awaiting_tenant_binding", response_actions_enabled: [], response_key_ids: [],
      last_action_seq: null, isolation_state: "inactive", isolation_until: null, isolation_checked_at: null,
      quarantine_items: 0, service_config_state: "as_installed", previous_run_end: "clean", heartbeat_interval_seconds: 300,
      behavior_rules_version: "altay-behavior/v1" };
  };
  // Counter order: EDR_COUNTER_KEYS (queue dropped, write failed, unmapped, skipped, evicted, discarded, degraded, backlog).
  const specs: DeviceSpec[] = [
    { n: 1, tenant: 0, label: "DEMO · Ankara uç noktası", connection: "recent", received: 45, observed: 90,
      sequence: 42, states: [firewall("running", "enforce", 90), termivar(90, true), antivirus(),
        edrAgent(90, "started", { started: 5460, counts: [4, 0, 2, 0, 0, 0, 0, 3] })] },
    { n: 2, tenant: 0, label: "DEMO · İzmir gözlem istasyonu", connection: "stale", received: 2700, observed: 2760,
      sequence: 17, states: [firewall("observing", "sniff", 2760), termivar(2760, false), antivirus(),
        edrAgent(2760, "stopped", { started: 9060, counts: [0, 1, 0, 0, 0, 0, 0, 0] })] },
    { n: 3, tenant: 0, label: "DEMO · Yeni kayıt", connection: "never_seen", received: null, observed: null,
      sequence: null, states: [] },
    { n: 7, tenant: 0, label: "DEMO · İptal edilmiş saha kaydı", connection: "stale", received: 7200, observed: 7260,
      sequence: 12, revoked: 3600, states: [firewall("stopped", "unknown", 7260), termivar(7260, false), antivirus(),
        edrAgent(7260, "disabled", { ruleFile: false })] },
    { n: 8, tenant: 0, label: "DEMO · Kaynak saati ileride", connection: "recent", received: 55, observed: -180,
      sequence: 51, states: [firewall("degraded", "enforce", -180, ["telemetry_error"]), termivar(-180, true), antivirus(),
        edrAgent(-180, "started", { started: 1860, counts: [0, 0, 5, 3, 0, 0, 1, 12] })] },
    { n: 9, tenant: 0, label: "DEMO · Arşiv gözlem dizüstü", connection: "stale", received: 93600, observed: 97200,
      sequence: 24, states: [firewall("unavailable", "unknown", 97200, ["health_unavailable"]), antivirus(),
        edrAgent(97200, "failed", { code: "access_denied", ruleFile: null, counts: [0, 0, 0, 0, 0, 0, 0, 37] })] },
    { n: 4, tenant: 1, label: "DEMO · Araştırma iş istasyonu", connection: "recent", received: 80, observed: -120,
      sequence: 8, states: [firewall("degraded", "enforce", -120, ["telemetry_error"]), termivar(-120, true, 1), antivirus(),
        edrAgent(-120, "started", { started: 2460, counts: [0, 0, 1, 0, 0, 0, 0, 0] })] },
    { n: 5, tenant: 1, label: "DEMO · Saha dizüstü", connection: "stale", received: 93600, observed: 97200,
      sequence: 23, states: [firewall("unavailable", "unknown", 97200, ["health_unavailable"]), antivirus(),
        edrAgent(97200, "unknown", { started: null, counts: null })] },
    { n: 6, tenant: 1, label: "DEMO · İptal edilmiş cihaz kaydı", connection: "stale", received: 7200, observed: 7260,
      sequence: 11, revoked: 3600, states: [firewall("stopped", "unknown", 7260), termivar(7260, false), antivirus()] },
    // A sample Snapshot V3 agent; silent for 30 minutes, so the sample sweep opened agent_silent.
    { n: 10, tenant: 0, label: "DEMO · Bursa V3 ajan örneği", connection: "stale", received: 1800, observed: 1830,
      sequence: 63, states: [edrAgentV3(1830)] },
  ];
  const devices: DeviceDetail[] = specs.map((spec) => {
    const device: Device = {
      id: `20000000-0000-4000-8000-${String(spec.n).padStart(12, "0")}`, tenant_id: DEMO_TENANT_IDS[spec.tenant],
      label: spec.label, identity_status: spec.revoked ? "revoked" : "active", connection_status: spec.connection,
      created_at: at(604800 - spec.n * 600), revoked_at: spec.revoked ? at(spec.revoked) : null,
      last_sequence: spec.sequence, last_received_at: spec.received === null ? null : at(spec.received),
      source_observed_at: spec.observed === null ? null : at(spec.observed),
      source_observation: observation(spec.observed), ...claims,
    };
    const products: ProductRecord[] = spec.states.map((state) => {
      if (spec.sequence === null || device.last_received_at === null) throw new Error("invalid_demo_fixture");
      const common = { snapshot_sequence: spec.sequence, received_at: device.last_received_at,
        observation: observation(state.source_observed_at === null ? null : spec.observed) };
      if (state.product_id === "termivar") return { ...common, product_id: state.product_id, state,
        report_import_age: observation(state.latest_report === null ? null : Math.floor((now - Date.parse(state.latest_report.imported_at)) / 1000)) };
      if (state.product_id === "hostbasedfirewall") return { ...common, product_id: state.product_id, state };
      if (state.product_id === "edr_agent") return { ...common, product_id: state.product_id, state };
      return { ...common, product_id: state.product_id, state };
    });
    return { ...device, products,
      missing_products: PRODUCT_IDS.filter((id) => !products.some((product) => product.product_id === id)).sort() };
  });
  const tenants: Tenant[] = [
    { id: DEMO_TENANT_IDS[0], name: "Kuzey Operasyon · Demo", role: "tenant_admin" },
    { id: DEMO_TENANT_IDS[1], name: "Araştırma Birimi · Demo", role: "viewer" },
  ];
  const alertId = (n: number): string => `70000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
  const eventSpecs: { n: number; action: AuditEvent["action"]; object_type: AuditEvent["object_type"]; object_id: string; age: number }[] = [
    { n: 6, action: "alert_acknowledged", object_type: "alert", object_id: alertId(6), age: 600 },
    { n: 1, action: "device_enrolled", object_type: "device", object_id: "20000000-0000-4000-8000-000000000003", age: 900 },
    { n: 2, action: "enrollment_grant_created", object_type: "enrollment_grant", object_id: "50000000-0000-4000-8000-000000000001", age: 1200 },
    { n: 7, action: "alert_acknowledged", object_type: "alert", object_id: alertId(2), age: 2400 },
    { n: 8, action: "alert_closed", object_type: "alert", object_id: alertId(4), age: 2500 },
    { n: 9, action: "alert_closed", object_type: "alert", object_id: alertId(8), age: 3000 },
    { n: 3, action: "device_credential_rotated", object_type: "device_credential", object_id: "60000000-0000-4000-8000-000000000001", age: 3600 },
    { n: 4, action: "device_enrolled", object_type: "device", object_id: "20000000-0000-4000-8000-000000000001", age: 86400 },
    { n: 5, action: "membership_set", object_type: "membership", object_id: "40000000-0000-4000-8000-000000000001", age: 172800 },
  ];
  const audit: AuditEvent[] = eventSpecs.map((event) => ({
    id: `30000000-0000-4000-8000-${String(event.n).padStart(12, "0")}`, tenant_id: DEMO_TENANT_IDS[0],
    actor_type: "operator", actor_id: "40000000-0000-4000-8000-000000000001", action: event.action,
    object_type: event.object_type, object_id: event.object_id, outcome: "success", created_at: at(event.age),
  }));
  const { timelines, alerts } = createDemoEvents(at, alertId);
  return { tenants, devices, audit, timelines, alerts, referenceTime: at(0) };
}

/** Synthetic events (v1 process and sensor events, and one sample v2 agent's) with the rule matches they would raise,
 * and one sample sweep alert; all masked, all fictional. */
function createDemoEvents(at: (secondsAgo: number) => string, alertId: (n: number) => string): {
  timelines: DemoTimeline[]; alerts: Alert[];
} {
  // The API writes microseconds; fixture times use the same six fraction digits.
  const at6 = (secondsAgo: number): string => at(secondsAgo).replace(/Z$/, "000Z");
  const deviceId = (n: number): string => `20000000-0000-4000-8000-${String(n).padStart(12, "0")}`;
  /** `clockAhead` seconds make the device clock run ahead of the server; batches arrive every 30 seconds. */
  const recorder = (clockAhead: number) => {
    const times = (age: number) => ({ observed_at: at6(age - clockAhead), received_at: at6(Math.max(0, Math.floor(age / 30) * 30 - 30)) });
    return {
      /** `created`/`parentCreated`: the v2 creation times' ages; a v1 row has neither (null). */
      start: (seq: number, age: number, pid: number, parent: number, image: string, created: number | null = null,
        parentCreated: number | null = null): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "process_started", pid, parent_pid: parent, session_id: 1, image,
          create_time: created === null ? null : at6(created - clockAhead),
          parent_create_time: parentCreated === null ? null : at6(parentCreated - clockAhead), ...claims }),
      stop: (seq: number, age: number, pid: number, exit: number | null, image: string | null,
        created: number | null = null): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "process_stopped", pid, exit_code: exit, image,
          create_time: created === null ? null : at6(created - clockAhead), ...claims }),
      sensor: (seq: number, age: number, state: SensorStateValue, error: SensorErrorCode | null = null): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "sensor_state", state, error_code: error, ...claims }),
      scan: (seq: number, age: number, fields: ScanDetectedFields): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "scan_detected", ...fields, ...claims }),
      behavior: (seq: number, age: number, fields: BehaviorMatchFields): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "behavior_match", ...fields, ...claims }),
      persistence: (seq: number, age: number, fields: PersistenceChangeFields): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "persistence_change", ...fields, ...claims }),
      agent: (seq: number, age: number, fields: AgentStateFields): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "agent_state", ...fields, ...claims }),
      tamper: (seq: number, age: number, fields: TamperSignalFields): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "tamper_signal", ...fields, ...claims }),
      gap: (seq: number, age: number, gapSource: CoverageSource, reason: CoverageReason, lost: number | null): TimelineEvent =>
        ({ event_seq: seq, ...times(age), kind: "coverage_gap", gap_source: gapSource, reason, lost, ...claims }),
    };
  };
  const v3 = "\\Device\\HarddiskVolume3", v2 = "\\Device\\HarddiskVolume2";
  const explorer = `${v3}\\Windows\\explorer.exe`, svchost = `${v3}\\Windows\\System32\\svchost.exe`;
  const office = `${v3}\\Program Files\\Microsoft Office\\root\\Office16`;
  const winword = `${office}\\WINWORD.EXE`, excel = `${office}\\EXCEL.EXE`, outlook = `${office}\\OUTLOOK.EXE`;
  const chrome = `${v3}\\Program Files\\Google\\Chrome\\Application\\chrome.exe`;
  const edge = `${v3}\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe`;
  const powershell = `${v3}\\Windows\\System32\\WindowsPowerShell\\v1.0\\powershell.exe`, cmd = `${v3}\\Windows\\System32\\cmd.exe`;
  const notepad = `${v3}\\Windows\\System32\\notepad.exe`, taskmgr = `${v3}\\Windows\\System32\\Taskmgr.exe`;
  const downloaded = `${v3}\\Users\\*\\Downloads\\kurulum-demo.exe`, invoice = `${v3}\\Users\\*\\AppData\\Local\\Temp\\fatura-demo.exe`;
  const roaming = `${v3}\\Users\\*\\AppData\\Roaming\\demo-arac.exe`;
  const smss = `${v2}\\Windows\\System32\\smss.exe`, firefox = `${v2}\\Program Files\\Mozilla Firefox\\firefox.exe`;
  const mshta = `${v2}\\Windows\\System32\\mshta.exe`;
  const sample = `${v3}\\Users\\*\\Downloads\\demo-ornek.exe`, updater = `${v3}\\Users\\*\\AppData\\Roaming\\demo-guncelleyici.exe`;

  const d1 = recorder(0);
  const ankara = [
    d1.sensor(1, 5400, "started"), d1.start(2, 5330, 1180, 920, explorer), d1.start(3, 5100, 4012, 1180, winword),
    d1.start(4, 4900, 4388, 1180, chrome), d1.start(5, 4700, 5120, 4012, powershell), d1.stop(6, 4650, 5120, 0, "powershell.exe"),
    d1.start(7, 4300, 5544, 1180, downloaded), d1.stop(8, 4250, 5544, 3221225477, "kurulum-demo.exe"),
    d1.start(9, 4000, 6020, 4388, notepad), d1.stop(10, 3900, 6020, 0, "notepad.exe"),
    d1.start(11, 3700, 6204, 1180, cmd), d1.stop(12, 3650, 6204, 1, "cmd.exe"),
    // Sequences 13-16 never reached the platform: the sample's event-loss gap.
    d1.sensor(17, 3000, "lost", "session_in_use"), d1.sensor(18, 2950, "started"),
    d1.start(19, 2600, 7016, 1180, downloaded), d1.stop(20, 2550, 7016, 0, "kurulum-demo.exe"),
    d1.start(21, 2000, 7300, 640, svchost), d1.start(22, 1700, 7412, 4388, chrome), d1.stop(23, 1500, 7412, null, null),
    d1.start(24, 1200, 7520, 1180, excel), d1.stop(25, 900, 7520, 0, "EXCEL.EXE"),
    d1.sensor(26, 600, "stopped"), d1.sensor(27, 580, "started"),
    d1.start(28, 300, 8016, 1180, taskmgr), d1.stop(29, 200, 8016, 0, "Taskmgr.exe"), d1.start(30, 90, 8120, 1180, powershell),
  ];
  const d2 = recorder(0);
  const izmir = [
    d2.sensor(41, 9000, "started"), d2.start(42, 8800, 2200, 1020, outlook), d2.start(43, 8500, 2300, 2200, invoice),
    d2.stop(44, 8400, 2300, 0, "fatura-demo.exe"), d2.sensor(45, 2780, "stopped"),
  ];
  const d7 = recorder(0);
  const revoked = [d7.sensor(5, 7400, "started"), d7.start(6, 7350, 880, 640, svchost), d7.sensor(7, 7300, "stopped")];
  // The sample device whose clock runs five minutes ahead; the cap and retention removed its older events.
  const d8 = recorder(300);
  const ahead = [
    d8.sensor(2731, 1800, "started"), d8.sensor(2732, 1750, "failed", "access_denied"), d8.sensor(2733, 1700, "started"),
    d8.sensor(2734, 1650, "failed", "access_denied"), d8.sensor(2735, 1600, "started"), d8.start(2736, 1500, 900, 4, smss),
    // Sequences 2737-2773 are missing.
    d8.start(2774, 700, 3304, 2210, firefox), d8.start(2775, 650, 3390, 3304, mshta), d8.stop(2776, 640, 3390, 1, "mshta.exe"),
    d8.sensor(2777, 400, "failed", "unknown"), d8.sensor(2778, 380, "started"),
  ];
  const d4 = recorder(120);
  const research = [
    d4.sensor(201, 2400, "started"), d4.start(202, 2300, 3100, 900, edge), d4.start(203, 2200, 3150, 3100, cmd),
    d4.stop(204, 2150, 3150, 0, "cmd.exe"), d4.sensor(205, 1600, "lost", "session_in_use"), d4.sensor(206, 1550, "started"),
    d4.start(207, 900, 3400, 900, roaming), d4.stop(208, 850, 3400, 0, "demo-arac.exe"),
  ];
  // The sample v2 agent (Snapshot V3 device 10). Every hex value is a visibly fake pattern, every name a demo name.
  const d10 = recorder(0);
  const ruleSetId = "0123456789abcdef".repeat(4);
  const persisted: PersistenceChangeFields = { location: "run_key", scope: "user", change: "added",
    entry_id: "fedcba9876543210".repeat(4), target_image: updater, found_at_start: false };
  const scanned: ScanDetectedFields = { trigger: "process_start", path: sample, size: 482304, sha256: "deadbeef".repeat(8),
    rule_set_id: ruleSetId, hits: [{ rule: "Demo_Sample_Rule", severity: "medium" }], omitted_hits: 0, pid: 9120,
    create_time: at6(5000), action_id: null };
  const matched: BehaviorMatchFields = { rule: "encoded_powershell", rule_version: 1, pid: 9204, create_time: at6(4000),
    image: powershell, parent_image: cmd, found_at_start: false, command_line_source: "kernel_logger" };
  const tampered: TamperSignalFields = { signal: "data_dir_acl_changed", detail: null };
  const scanStopped: AgentStateFields = { subject: "realtime_scan", state: "stopped", code: null, rule_set_id: null };
  const bursa = [
    d10.agent(50, 9000, { subject: "service", state: "started", code: "clean_stop", rule_set_id: null }),
    d10.agent(51, 8990, { subject: "rule_set", state: "compiled", code: null, rule_set_id: ruleSetId }),
    d10.agent(52, 8980, { subject: "persistence_watch", state: "baseline_created", code: null, rule_set_id: null }),
    d10.persistence(53, 7000, persisted), d10.start(54, 5000, 9120, 1180, sample, 5000, 86000),
    d10.scan(55, 4990, scanned), d10.behavior(56, 4000, matched), d10.stop(57, 3990, 9204, 0, "powershell.exe", 4000),
    d10.gap(58, 3500, "process_sensor", "etw_events_lost", 14),
    d10.agent(59, 3000, { subject: "file_change_sensor", state: "degraded", code: null, rule_set_id: null }),
    d10.tamper(60, 2800, tampered), d10.agent(61, 2500, scanStopped),
    d10.agent(62, 2400, { subject: "realtime_scan", state: "running", code: null, rule_set_id: null }),
    d10.start(63, 1900, 9310, 1180, notepad, 1900, 86000),
  ];
  const newestFirst = (events: readonly TimelineEvent[]): readonly TimelineEvent[] => [...events].reverse();
  const timelines: DemoTimeline[] = [
    { deviceId: deviceId(1), events: newestFirst(ankara), capDeletedEvents: 0, suppressedAlerts: 0 },
    { deviceId: deviceId(2), events: newestFirst(izmir), capDeletedEvents: 0, suppressedAlerts: 0 },
    { deviceId: deviceId(7), events: newestFirst(revoked), capDeletedEvents: 0, suppressedAlerts: 0 },
    { deviceId: deviceId(8), events: newestFirst(ahead), capDeletedEvents: 1500, suppressedAlerts: 0 },
    { deviceId: deviceId(4), events: newestFirst(research), capDeletedEvents: 0, suppressedAlerts: 0 },
    { deviceId: deviceId(10), events: newestFirst(bursa), capDeletedEvents: 0, suppressedAlerts: 0 },
  ];

  /** first/last seen are the server receipt times of the matching events' batches. */
  const seenAt = (events: readonly TimelineEvent[], seq: number): string => {
    const event = events.find((item) => item.event_seq === seq);
    if (!event) throw new Error("invalid_demo_fixture");
    return event.received_at;
  };
  const base = (n: number, device: number, events: readonly TimelineEvent[], first: number, last: number, occurrences: number,
    status: AlertStatus, acknowledgedAge: number | null = null, closedAge: number | null = null) => ({
    id: alertId(n), device_id: deviceId(device), status, occurrences, first_event_seq: first, last_event_seq: last,
    first_seen_at: seenAt(events, first), last_seen_at: seenAt(events, last),
    acknowledged_at: acknowledgedAge === null ? null : at6(acknowledgedAge), closed_at: closedAge === null ? null : at6(closedAge),
    ...claims,
  });
  const alerts: Alert[] = [
    { ...base(1, 1, ankara, 5, 5, 1, "open"), rule: "office_browser_spawned_tool", severity: "medium",
      evidence: { image: powershell, pid: 5120, parent_image: winword, parent_pid: 4012 } },
    { ...base(2, 1, ankara, 7, 19, 2, "acknowledged", 2400), rule: "user_writable_launch", severity: "low",
      evidence: { image: downloaded, pid: 7016 } },
    { ...base(3, 1, ankara, 17, 17, 1, "open"), rule: "event_loss", severity: "medium", evidence: { missing_events: 4 } },
    { ...base(4, 1, ankara, 17, 17, 1, "closed", null, 2500), rule: "sensor_unstable", severity: "medium",
      evidence: { state: "lost", error_code: "session_in_use" } },
    { ...base(5, 8, ahead, 2732, 2777, 3, "open"), rule: "sensor_unstable", severity: "medium",
      evidence: { state: "failed", error_code: "unknown" } },
    { ...base(6, 8, ahead, 2774, 2774, 1, "acknowledged", 600), rule: "event_loss", severity: "medium", evidence: { missing_events: 37 } },
    { ...base(7, 8, ahead, 2775, 2775, 1, "open"), rule: "office_browser_spawned_tool", severity: "medium",
      evidence: { image: mshta, pid: 3390, parent_image: firefox, parent_pid: 3304 } },
    { ...base(8, 2, izmir, 43, 43, 1, "closed", null, 3000), rule: "user_writable_launch", severity: "low",
      evidence: { image: invoice, pid: 2300 } },
    { ...base(9, 4, research, 203, 203, 1, "open"), rule: "office_browser_spawned_tool", severity: "medium",
      evidence: { image: cmd, pid: 3150, parent_image: edge, parent_pid: 3100 } },
    { ...base(10, 4, research, 205, 205, 1, "acknowledged", 1200), rule: "sensor_unstable", severity: "medium",
      evidence: { state: "lost", error_code: "session_in_use" } },
    { ...base(11, 4, research, 207, 207, 1, "open"), rule: "user_writable_launch", severity: "low",
      evidence: { image: roaming, pid: 3400 } },
    // Stage 3 sample rules: the evidence is the matching event's own fields.
    { ...base(12, 10, bursa, 53, 53, 1, "open"), rule: "persistence_added", severity: "low",
      evidence: { ...persisted, change: "added" } },
    { ...base(13, 10, bursa, 55, 55, 1, "open"), rule: "scan_detection", severity: "medium", evidence: scanned },
    { ...base(14, 10, bursa, 56, 56, 1, "acknowledged", 1500), rule: "behavior_match", severity: "medium", evidence: matched },
    { ...base(15, 10, bursa, 60, 60, 1, "open"), rule: "tamper_signal", severity: "medium", evidence: tampered },
    { ...base(16, 10, bursa, 61, 61, 1, "open"), rule: "capability_down", severity: "medium",
      evidence: { subject: "realtime_scan", state: "stopped", code: null, rule_set_id: null } },
    // The sample sweep: no event, so no event sequences; first and last seen are the sweep time.
    { id: alertId(17), device_id: deviceId(10), status: "open", occurrences: 1, first_event_seq: null, last_event_seq: null,
      first_seen_at: at6(600), last_seen_at: at6(600), acknowledged_at: null, closed_at: null, ...claims,
      rule: "agent_silent", severity: "medium", evidence: { last_received_at: at6(1800), threshold_seconds: 900 } },
  ];
  return { timelines, alerts };
}
