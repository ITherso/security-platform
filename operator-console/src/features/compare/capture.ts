/** Explicit capture of one displayed, validated detail; no reads or session data. */
import type { DeviceDetail, ProductRecord } from "../../data/contracts";
import { normalizeDeviceDetail } from "../../data/normalize";
import { CompareError, compareId, compareObject, compareTimestamp, copyComparableDevice } from "./compareModel";
import type { ComparableDevice, CompareFieldValues } from "./compareModel";

export interface CompareCaptureMetadata { readonly tenantId: string; readonly readAt: string }
type FirewallRecord = Extract<ProductRecord, { product_id: "hostbasedfirewall" }>;
type TermivarRecord = Extract<ProductRecord, { product_id: "termivar" }>;
type AntivirusRecord = Extract<ProductRecord, { product_id: "antivirus" }>;

export function captureComparableDevice(detail: DeviceDetail, metadata: CompareCaptureMetadata): ComparableDevice {
  try {
    compareObject(metadata, ["tenantId", "readAt"]);
    const tenantId = compareId(metadata.tenantId), readAt = compareTimestamp(metadata.readAt);
    const source = normalizeDeviceDetail(detail, tenantId, detail.id);
    const hbf = source.products.find((entry): entry is FirewallRecord => entry.product_id === "hostbasedfirewall");
    const termivar = source.products.find((entry): entry is TermivarRecord => entry.product_id === "termivar");
    const antivirus = source.products.find((entry): entry is AntivirusRecord => entry.product_id === "antivirus");
    const summary = termivar?.state.latest_report;
    // Each permitted scalar is selected explicitly; no DTO/state/session spread.
    const fields: CompareFieldValues = {
      "device.registration": source.identity_status,
      "device.connection": source.connection_status,
      "device.received_at": source.last_received_at,
      "device.observed_at": source.source_observed_at,
      "device.read_at": readAt,
      "device.revoked_at": source.revoked_at,
      "hbf.status": hbf?.state.status ?? null,
      "hbf.version": hbf?.state.version ?? null,
      "hbf.installed": hbf?.state.installed ?? null,
      "hbf.running": hbf?.state.reported_running ?? null,
      "hbf.stale": hbf?.state.reported_stale ?? null,
      "hbf.mode": hbf?.state.firewall_mode ?? null,
      "hbf.received_at": hbf?.received_at ?? null,
      "hbf.observed_at": hbf?.state.source_observed_at ?? null,
      "hbf.source": hbf?.state.source ?? null,
      "hbf.verification": hbf?.state.producer_verification ?? null,
      "termivar.status": termivar?.state.status ?? null,
      "termivar.version": termivar?.state.version ?? null,
      "termivar.scanner_installed": termivar?.state.scanner_installed ?? null,
      "termivar.execution_available": termivar?.state.execution_available ?? null,
      "termivar.report_presence": termivar?.state.report_presence ?? null,
      "termivar.subject_count": summary?.subject_count ?? null,
      "termivar.item_count": summary?.item_count ?? null,
      "termivar.informational": summary?.counts.informational ?? null,
      "termivar.needs_review": summary?.counts.needs_review ?? null,
      "termivar.confirmed": summary?.counts.confirmed ?? null,
      "termivar.unassigned": summary?.severity_counts.unassigned ?? null,
      "termivar.info": summary?.severity_counts.info ?? null,
      "termivar.low": summary?.severity_counts.low ?? null,
      "termivar.medium": summary?.severity_counts.medium ?? null,
      "termivar.high": summary?.severity_counts.high ?? null,
      "termivar.critical": summary?.severity_counts.critical ?? null,
      "termivar.imported_at": summary?.imported_at ?? null,
      "termivar.received_at": termivar?.received_at ?? null,
      "termivar.observed_at": termivar?.state.source_observed_at ?? null,
      "termivar.source": termivar?.state.source ?? null,
      "termivar.verification": termivar?.state.producer_verification ?? null,
      "av.status": antivirus?.state.status ?? null,
      "av.availability": antivirus?.state.availability ?? null,
      "av.execution_available": antivirus?.state.execution_available ?? null,
      "av.received_at": antivirus?.received_at ?? null,
      "av.observed_at": antivirus?.state.source_observed_at ?? null,
      "av.source": antivirus?.state.source ?? null,
      "av.verification": antivirus?.state.producer_verification ?? null,
      "device.source": source.source,
      "device.verification": source.producer_verification,
    };
    return copyComparableDevice({ tenantId, deviceId: source.id, deviceName: source.label, fields });
  } catch (error) {
    if (error instanceof CompareError) throw error;
    throw new CompareError("invalid_comparison");
  }
}
