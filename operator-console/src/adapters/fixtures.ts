/** Explicit offline scenarios. The same normalizers are used by live GETs. */
import { ClientError } from "../data/contracts";
import type { DataClient, DemoScenario } from "../data/contracts";
import { requireValue } from "../data/normalize";
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
      if (operation.type === "audit") {
        if (membership.role !== "tenant_admin") throw new ClientError("forbidden", 403);
        body = scenario === "empty" ? [] : data.audit.filter((event) => event.tenant_id === operation.tenantId);
      } else if (operation.type === "detail") {
        body = scenario === "empty" ? undefined : data.devices.find((device) => device.tenant_id === operation.tenantId && device.id === operation.deviceId);
        if (!body) throw new ClientError("not_found", 404);
      } else body = scenario === "empty" ? [] : data.devices.filter((device) => device.tenant_id === operation.tenantId)
        .map(({ products: _products, missing_products: _missing, ...device }) => device);
    }
    if (operation.type !== "detail") {
      requireValue(Array.isArray(body));
      body = { items: body.slice(options.offset, options.offset + options.limit),
        next_offset: body.length > options.offset + options.limit ? options.offset + options.limit : null };
    }
    return normalize(body);
  }
  return createReadOnlyClient(read, () => { connected = false; data = null; }, { mode: "demo",
    sourceLabel: "Örnek veri — gerçek cihazlara bağlı değil", referenceTime, apiBase: null, scenario });
}
