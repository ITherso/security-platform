/** Ephemeral request state. No persistence, token decoding, refresh or discovery. */
import { ClientError } from "../data/contracts";
import type { ClientErrorCode, DataClient, PageOptions, RequestOptions } from "../data/contracts";
import { freeze, identifier, normalizeAuditPage, normalizeDeviceDetail, normalizeDevicePage,
  normalizeTenantPage, requireValue } from "../data/normalize";

export { ClientError } from "../data/contracts";
export const REQUEST_TIMEOUT_MS = 12000;
export interface ResolvedOptions { readonly limit: number; readonly offset: number; readonly signal?: AbortSignal }
export type ReadOperation = { readonly type: "tenants" }
  | { readonly type: "devices" | "audit"; readonly tenantId: string }
  | { readonly type: "detail"; readonly tenantId: string; readonly deviceId: string };
export type ReadTransport = <T>(operation: ReadOperation, options: ResolvedOptions,
  normalize: (body: unknown) => T) => Promise<T>;
type Metadata = Pick<DataClient, "mode" | "sourceLabel" | "referenceTime" | "apiBase" | "scenario">;

function options(input: unknown = {}, paged = false): ResolvedOptions {
  requireValue(input !== null && typeof input === "object" && !Array.isArray(input), "invalid_input");
  const value = input as Record<string, unknown>;
  requireValue(Object.keys(value).every((key) => ["signal", ...(paged ? ["limit", "offset"] : [])].includes(key)), "invalid_input");
  const signal = value.signal;
  requireValue(signal === undefined || (typeof AbortSignal !== "undefined" && signal instanceof AbortSignal), "invalid_input");
  const limit = value.limit === undefined ? 50 : value.limit, offset = value.offset === undefined ? 0 : value.offset;
  requireValue(typeof limit === "number" && Number.isInteger(limit) && limit >= 1 && limit <= 100
    && typeof offset === "number" && Number.isInteger(offset) && offset >= 0 && offset <= 10000, "invalid_input");
  return { limit, offset, signal };
}

/** Fixed four-method public surface used by both transports. */
export function createReadOnlyClient(read: ReadTransport, disconnect: () => void, metadata: Metadata): DataClient {
  return Object.freeze({ ...metadata, disconnect,
    async listTenants(value: PageOptions = {}) {
      const opts = options(value, true);
      return freeze(await read({ type: "tenants" }, opts, (body) => normalizeTenantPage(body, opts)));
    },
    async listDevices(tenantId: string, value: PageOptions = {}) {
      identifier(tenantId, "invalid_input");
      const opts = options(value, true);
      return freeze(await read({ type: "devices", tenantId }, opts, (body) => normalizeDevicePage(body, opts, tenantId)));
    },
    async getDevice(tenantId: string, deviceId: string, value: RequestOptions = {}) {
      identifier(tenantId, "invalid_input"); identifier(deviceId, "invalid_input");
      const opts = options(value);
      return freeze(await read({ type: "detail", tenantId, deviceId }, opts,
        (body) => normalizeDeviceDetail(body, tenantId, deviceId)));
    },
    async listAudit(tenantId: string, value: PageOptions = {}) {
      identifier(tenantId, "invalid_input");
      const opts = options(value, true);
      return freeze(await read({ type: "audit", tenantId }, opts, (body) => normalizeAuditPage(body, opts, tenantId)));
    },
  });
}

export function readPath(operation: ReadOperation, opts: ResolvedOptions): string {
  const query = `?limit=${opts.limit}&offset=${opts.offset}`;
  switch (operation.type) {
    case "tenants": return `/tenants${query}`;
    case "devices": return `/tenants/${encodeURIComponent(operation.tenantId)}/devices${query}`;
    case "audit": return `/tenants/${encodeURIComponent(operation.tenantId)}/audit${query}`;
    case "detail": return `/tenants/${encodeURIComponent(operation.tenantId)}/devices/${encodeURIComponent(operation.deviceId)}`;
  }
}

interface PendingRequest { controller: AbortController; reason: ClientErrorCode | null }
export interface RequestHandle {
  readonly signal: AbortSignal;
  reason(): ClientErrorCode | null;
  finish(): void;
}
export interface TokenSession {
  isConnected(): boolean;
  authorizationHeader(): string;
  begin(signal?: AbortSignal): RequestHandle;
  disconnect(): void;
}

export function createTokenSession(accessToken: unknown): TokenSession {
  requireValue(typeof accessToken === "string" && /^[\x21-\x7e]{1,16384}$/.test(accessToken), "invalid_input");
  let token = accessToken;
  let connected = true;
  const pending = new Set<PendingRequest>();
  const disconnect = (): void => {
    connected = false; token = "";
    for (const request of pending) { request.reason = "disconnected"; request.controller.abort(); }
    pending.clear();
  };
  return Object.freeze({
    isConnected: () => connected,
    authorizationHeader() {
      if (!connected) throw new ClientError("disconnected");
      return `Bearer ${token}`;
    },
    disconnect,
    begin(signal?: AbortSignal): RequestHandle {
      if (!connected) throw new ClientError("disconnected");
      if (signal?.aborted) throw new ClientError("aborted");
      if (pending.size >= 8) throw new ClientError("rate_limited");
      const entry: PendingRequest = { controller: new AbortController(), reason: null };
      const abort = (): void => {
        if (!entry.controller.signal.aborted) { entry.reason = "aborted"; entry.controller.abort(); }
      };
      const timer = setTimeout(() => {
        if (!entry.controller.signal.aborted) { entry.reason = "timeout"; entry.controller.abort(); }
      }, REQUEST_TIMEOUT_MS);
      pending.add(entry);
      signal?.addEventListener("abort", abort, { once: true });
      return Object.freeze({ signal: entry.controller.signal, reason: () => entry.reason,
        finish() { clearTimeout(timer); pending.delete(entry); signal?.removeEventListener("abort", abort); } });
    },
  });
}
