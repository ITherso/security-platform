/** Explicit offline scenarios. The same normalizers are used by live GETs. */
import { ClientError } from "../data/contracts";
import type { Alert, DataClient, DemoScenario, DeviceDetail, TimelineEvent } from "../data/contracts";
import { alertOrderKey, requireValue, utcSortKey } from "../data/normalize";
import { createDemoData } from "../fixtures/demo-data";
import type { DemoDataset } from "../fixtures/demo-data";
import { createReadOnlyClient } from "./session";
import type { ReadOperation, ResolvedOptions } from "./session";

export { ClientError } from "../data/contracts";
export interface DemoConfiguration { readonly scenario?: DemoScenario }

export function createDemoClient(config: DemoConfiguration = {}): DataClient {
  requireValue(config !== null && typeof config === "object" && !Array.isArray(config)
    && Object.keys(config).every((key) => key === "scenario"), "invalid_input");
  const scenario = config.scenario === undefined ? "normal" : config.scenario;
  requireValue(["normal", "empty", "error"].includes(scenario), "invalid_input");
  let data: DemoDataset | null = createDemoData();
  let connected = true;
  const referenceTime = data.referenceTime;
  async function read<T>(operation: ReadOperation, options: ResolvedOptions, normalize: (body: unknown) => T): Promise<T> {
    if (!connected) throw new ClientError("disconnected");
    if (options.signal?.aborted) throw new ClientError("aborted");
    await Promise.resolve(); // cancellation only; no timer or background work
    if (!connected || data === null) throw new ClientError("disconnected");
    if (options.signal?.aborted) throw new ClientError("aborted");
    let body: unknown;
    if (operation.type === "tenants") body = data.tenants;
    else {
      const membership = data.tenants.find((tenant) => tenant.id === operation.tenantId);
      if (!membership) throw new ClientError("not_found", 404);
      // Scenario changes never erase the selected tenant context or fake login.
      if (scenario === "error") throw new ClientError("offline");
      const tenantId = operation.tenantId;
      const tenantDevices: readonly DeviceDetail[] = scenario === "empty" ? [] : data.devices.filter((device) => device.tenant_id === tenantId);
      if (operation.type === "audit") {
        if (membership.role !== "tenant_admin") throw new ClientError("forbidden", 403);
        body = scenario === "empty" ? [] : data.audit.filter((event) => event.tenant_id === tenantId);
      } else if (operation.type === "detail") {
        const deviceId = operation.deviceId;
        body = tenantDevices.find((device) => device.id === deviceId);
        if (!body) throw new ClientError("not_found", 404);
      } else if (operation.type === "events") {
        // Same contract as the API: unknown or foreign device 404, newest first, strictly below before_seq.
        const deviceId = operation.deviceId, beforeSeq = operation.beforeSeq;
        if (!tenantDevices.some((device) => device.id === deviceId)) throw new ClientError("not_found", 404);
        const timeline = data.timelines.find((entry) => entry.deviceId === deviceId);
        const stored: readonly TimelineEvent[] = timeline?.events ?? [];
        const older = stored.filter((event) => beforeSeq === null || event.event_seq < beforeSeq);
        const items = older.slice(0, options.limit);
        body = { items, next_before_seq: older.length > options.limit ? items[items.length - 1]?.event_seq ?? null : null,
          cap_deleted_events: timeline?.capDeletedEvents ?? 0, suppressed_alerts: timeline?.suppressedAlerts ?? 0 };
      } else if (operation.type === "alerts") {
        // (last_seen_at DESC, id DESC) keyset; the cursor names the last row of the previous page.
        const { status, deviceId, before } = operation;
        if (deviceId !== null && !tenantDevices.some((device) => device.id === deviceId)) throw new ClientError("not_found", 404);
        const known = new Set(tenantDevices.map((device) => device.id));
        const cursor = before === null ? null : alertOrderKey(before.seen_at, before.id);
        const key = (alert: Alert): string => alertOrderKey(alert.last_seen_at, alert.id);
        const matching = data.alerts.filter((alert) => known.has(alert.device_id) && (status === null || alert.status === status)
          && (deviceId === null || alert.device_id === deviceId) && (cursor === null || key(alert) < cursor))
          .sort((left, right) => key(left) < key(right) ? 1 : key(left) > key(right) ? -1 : 0);
        const items = matching.slice(0, options.limit);
        const last = items[items.length - 1];
        body = { items, next_before: matching.length > options.limit && last !== undefined
          ? { seen_at: utcSortKey(last.last_seen_at), id: last.id } : null };
      } else body = tenantDevices.map(({ products: _products, missing_products: _missing, ...device }) => device);
    }
    if (operation.type === "tenants" || operation.type === "devices" || operation.type === "audit") {
      requireValue(Array.isArray(body));
      body = { items: body.slice(options.offset, options.offset + options.limit),
        next_offset: body.length > options.offset + options.limit ? options.offset + options.limit : null };
    }
    return normalize(body);
  }
  return createReadOnlyClient(read, () => { connected = false; data = null; }, { mode: "demo",
    sourceLabel: "Örnek veri — gerçek cihazlara bağlı değil", referenceTime, apiBase: null, scenario });
}
