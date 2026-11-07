/** Synthetic DTO-shaped fixtures. No real device/account/security action. */
import { PRODUCT_IDS } from "../data/contracts";
import type { AgeObservation, AntivirusState, AuditEvent, Device, DeviceDetail, HostBasedFirewallState,
  HbfErrorCode, ProductRecord, ProductState, ReportedProduct, SourceClaims, Tenant, TermivarState } from "../data/contracts";

export const DEMO_TENANT_IDS = ["10000000-0000-4000-8000-000000000001", "10000000-0000-4000-8000-000000000002"] as const;
export interface DemoDataset {
  readonly tenants: readonly Tenant[];
  readonly devices: readonly DeviceDetail[];
  readonly audit: readonly AuditEvent[];
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
  const specs: DeviceSpec[] = [
    { n: 1, tenant: 0, label: "DEMO · Ankara uç noktası", connection: "recent", received: 45, observed: 90,
      sequence: 42, states: [firewall("running", "enforce", 90), termivar(90, true), antivirus()] },
    { n: 2, tenant: 0, label: "DEMO · İzmir gözlem istasyonu", connection: "stale", received: 2700, observed: 2760,
      sequence: 17, states: [firewall("observing", "sniff", 2760), termivar(2760, false), antivirus()] },
    { n: 3, tenant: 0, label: "DEMO · Yeni kayıt", connection: "never_seen", received: null, observed: null,
      sequence: null, states: [] },
    { n: 7, tenant: 0, label: "DEMO · İptal edilmiş saha kaydı", connection: "stale", received: 7200, observed: 7260,
      sequence: 12, revoked: 3600, states: [firewall("stopped", "unknown", 7260), termivar(7260, false), antivirus()] },
    { n: 8, tenant: 0, label: "DEMO · Kaynak saati ileride", connection: "recent", received: 55, observed: -180,
      sequence: 51, states: [firewall("degraded", "enforce", -180, ["telemetry_error"]), termivar(-180, true), antivirus()] },
    { n: 9, tenant: 0, label: "DEMO · Arşiv gözlem dizüstü", connection: "stale", received: 93600, observed: 97200,
      sequence: 24, states: [firewall("unavailable", "unknown", 97200, ["health_unavailable"]), antivirus()] },
    { n: 4, tenant: 1, label: "DEMO · Araştırma iş istasyonu", connection: "recent", received: 80, observed: -120,
      sequence: 8, states: [firewall("degraded", "enforce", -120, ["telemetry_error"]), termivar(-120, true, 1), antivirus()] },
    { n: 5, tenant: 1, label: "DEMO · Saha dizüstü", connection: "stale", received: 93600, observed: 97200,
      sequence: 23, states: [firewall("unavailable", "unknown", 97200, ["health_unavailable"]), antivirus()] },
    { n: 6, tenant: 1, label: "DEMO · İptal edilmiş cihaz kaydı", connection: "stale", received: 7200, observed: 7260,
      sequence: 11, revoked: 3600, states: [firewall("stopped", "unknown", 7260), termivar(7260, false), antivirus()] },
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
      return { ...common, product_id: state.product_id, state };
    });
    return { ...device, products,
      missing_products: PRODUCT_IDS.filter((id) => !products.some((product) => product.product_id === id)).sort() };
  });
  const tenants: Tenant[] = [
    { id: DEMO_TENANT_IDS[0], name: "Kuzey Operasyon · Demo", role: "tenant_admin" },
    { id: DEMO_TENANT_IDS[1], name: "Araştırma Birimi · Demo", role: "viewer" },
  ];
  const eventSpecs: { n: number; action: AuditEvent["action"]; object_type: AuditEvent["object_type"]; object_id: string; age: number }[] = [
    { n: 1, action: "device_enrolled", object_type: "device", object_id: "20000000-0000-4000-8000-000000000003", age: 900 },
    { n: 2, action: "enrollment_grant_created", object_type: "enrollment_grant", object_id: "50000000-0000-4000-8000-000000000001", age: 1200 },
    { n: 3, action: "device_credential_rotated", object_type: "device_credential", object_id: "60000000-0000-4000-8000-000000000001", age: 3600 },
    { n: 4, action: "device_enrolled", object_type: "device", object_id: "20000000-0000-4000-8000-000000000001", age: 86400 },
    { n: 5, action: "membership_set", object_type: "membership", object_id: "40000000-0000-4000-8000-000000000001", age: 172800 },
  ];
  const audit: AuditEvent[] = eventSpecs.map((event) => ({
    id: `30000000-0000-4000-8000-${String(event.n).padStart(12, "0")}`, tenant_id: DEMO_TENANT_IDS[0],
    actor_type: "operator", actor_id: "40000000-0000-4000-8000-000000000001", action: event.action,
    object_type: event.object_type, object_id: event.object_id, outcome: "success", created_at: at(event.age),
  }));
  return { tenants, devices, audit, referenceTime: at(0) };
}
