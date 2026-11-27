/** Explicit capture of one displayed, validated detail; no reads or session data. */
import type { DeviceDetail, ProductRecord } from "../../data/contracts";
import { isEdrAgentStateV3, normalizeDeviceDetail } from "../../data/normalize";
import { CompareError, compareId, compareObject, compareTimestamp, copyComparableDevice } from "./compareModel";
import type { ComparableDevice, CompareFieldValues } from "./compareModel";

export interface CompareCaptureMetadata { readonly tenantId: string; readonly readAt: string }
type FirewallRecord = Extract<ProductRecord, { product_id: "hostbasedfirewall" }>;
type TermivarRecord = Extract<ProductRecord, { product_id: "termivar" }>;
type AntivirusRecord = Extract<ProductRecord, { product_id: "antivirus" }>;
type AgentRecord = Extract<ProductRecord, { product_id: "edr_agent" }>;

export function captureComparableDevice(detail: DeviceDetail, metadata: CompareCaptureMetadata): ComparableDevice {
  try {
    compareObject(metadata, ["tenantId", "readAt"]);
    const tenantId = compareId(metadata.tenantId), readAt = compareTimestamp(metadata.readAt);
    const source = normalizeDeviceDetail(detail, tenantId, detail.id);
    const hbf = source.products.find((entry): entry is FirewallRecord => entry.product_id === "hostbasedfirewall");
    const termivar = source.products.find((entry): entry is TermivarRecord => entry.product_id === "termivar");
    const antivirus = source.products.find((entry): entry is AntivirusRecord => entry.product_id === "antivirus");
    const agentRecord = source.products.find((entry): entry is AgentRecord => entry.product_id === "edr_agent");
    const agent = agentRecord?.state;
    // V3 is told from V2 by its key set (normalize.ts isEdrAgentStateV3), as the device-detail card does.
    const v3 = agent !== undefined && isEdrAgentStateV3(agent) ? agent : undefined;
    const v2 = agent !== undefined && !isEdrAgentStateV3(agent) ? agent : undefined;
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
      "edr.status": agent?.status ?? null,
      "edr.version": agent?.version ?? null,
      "edr.agent_started_at": agent?.agent_started_at ?? null,
      "edr.engine_id": agent?.engine_id ?? null,
      "edr.rule_file_present": v2?.rule_file_present ?? null,
      "edr.rule_set_state": v3?.rule_set_state ?? null,
      "edr.rule_set_id": v3?.rule_set_id ?? null,
      "edr.behavior_rules_version": v3?.behavior_rules_version ?? null,
      "edr.sensor_state": agent?.sensor_state ?? null,
      "edr.sensor_error_code": agent?.sensor_error_code ?? null,
      "edr.service_config_state": v3?.service_config_state ?? null,
      "edr.previous_run_end": v3?.previous_run_end ?? null,
      "edr.heartbeat_interval_seconds": v3?.heartbeat_interval_seconds ?? null,
      "edr.realtime_scan_state": v3?.realtime_scan_state ?? null,
      "edr.file_change_sensor_state": v3?.file_change_sensor_state ?? null,
      "edr.command_line_sensor_state": v3?.command_line_sensor_state ?? null,
      "edr.persistence_watch_state": v3?.persistence_watch_state ?? null,
      "edr.response_channel_state": v3?.response_channel_state ?? null,
      "edr.last_action_seq": v3?.last_action_seq ?? null,
      "edr.isolation_state": v3?.isolation_state ?? null,
      "edr.isolation_until": v3?.isolation_until ?? null,
      "edr.isolation_checked_at": v3?.isolation_checked_at ?? null,
      "edr.quarantine_items": v3?.quarantine_items ?? null,
      "edr.events_queue_dropped": agent?.events_queue_dropped ?? null,
      "edr.events_write_failed": agent?.events_write_failed ?? null,
      "edr.events_unmapped": agent?.events_unmapped ?? null,
      "edr.events_skipped": agent?.events_skipped ?? null,
      "edr.events_evicted": agent?.events_evicted ?? null,
      "edr.events_discarded": agent?.events_discarded ?? null,
      "edr.events_degraded": agent?.events_degraded ?? null,
      "edr.outbox_backlog": agent?.outbox_backlog ?? null,
      "edr.scans_completed": v3?.scans_completed ?? null,
      "edr.scans_detected": v3?.scans_detected ?? null,
      "edr.scans_no_verdict": v3?.scans_no_verdict ?? null,
      "edr.scan_jobs_dropped": v3?.scan_jobs_dropped ?? null,
      "edr.scan_cache_hits": v3?.scan_cache_hits ?? null,
      "edr.etw_events_lost": v3?.etw_events_lost ?? null,
      "edr.file_change_gaps": v3?.file_change_gaps ?? null,
      "edr.cmdline_unavailable": v3?.cmdline_unavailable ?? null,
      "edr.received_at": agentRecord?.received_at ?? null,
      "edr.observed_at": agent?.source_observed_at ?? null,
      "edr.source": agent?.source ?? null,
      "edr.verification": agent?.producer_verification ?? null,
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
