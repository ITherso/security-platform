/** Same-origin HTTPS only. No mutation, proxy, polling, retry or demo fallback. */
import { ClientError } from "../data/contracts";
import type { ClientErrorCode, DataClient } from "../data/contracts";
import { requireValue, strictJson } from "../data/normalize";
import type { StrictJsonProfile } from "../data/normalize";
import { createReadOnlyClient, createTokenSession, readPath } from "./session";
import type { ReadOperation, ResolvedOptions } from "./session";

export { ClientError } from "../data/contracts";
export const MAX_RESPONSE_BYTES = 512 * 1024;
export interface ApiConfiguration { readonly apiBase: string; readonly accessToken: string }

function target(input: unknown): string {
  requireValue(typeof input === "string", "invalid_input");
  const location = globalThis.location;
  requireValue(location?.protocol === "https:" && typeof location.origin === "string", "https_required");
  const expected = `${location.origin}/api/v1`;
  try {
    const parsed = new URL(input);
    requireValue(parsed.protocol === "https:" && parsed.origin === location.origin && parsed.pathname === "/api/v1"
      && parsed.username === "" && parsed.password === "" && parsed.search === "" && parsed.hash === ""
      && input === expected, "https_required");
  } catch { throw new ClientError("https_required"); }
  return expected;
}

/** The strictJson profile of a read, chosen by its fixed route, never by the response. */
function responseProfile(operation: ReadOperation): StrictJsonProfile {
  // Timeline and alert pages carry event images of up to 1,024 code points (2,048 UTF-16 units).
  return operation.type === "events" || operation.type === "alerts" ? "sp-events-alerts-v1" : "default";
}

async function bodyJson(response: Response, profile: StrictJsonProfile): Promise<unknown> {
  requireValue((response.headers.get("content-type") ?? "").split(";")[0]?.trim().toLowerCase() === "application/json");
  const length = response.headers.get("content-length");
  if (length !== null) requireValue(/^\d{1,10}$/.test(length) && Number(length) <= MAX_RESPONSE_BYTES);
  requireValue(response.body !== null && typeof response.body.getReader === "function");
  const reader = response.body.getReader();
  const chunks: Uint8Array[] = [];
  let size = 0;
  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      requireValue(value instanceof Uint8Array);
      size += value.byteLength;
      requireValue(size <= MAX_RESPONSE_BYTES);
      chunks.push(value);
    }
    const bytes = new Uint8Array(size);
    let offset = 0;
    for (const chunk of chunks) { bytes.set(chunk, offset); offset += chunk.byteLength; }
    try { return strictJson(new TextDecoder("utf-8", { fatal: true }).decode(bytes), profile); }
    catch { throw new ClientError("malformed"); }
  } finally {
    try { void reader.cancel().catch(() => {}); } catch { /* Never expose body/error text. */ }
    reader.releaseLock();
  }
}

export function createApiClient(config: ApiConfiguration): DataClient {
  requireValue(config !== null && typeof config === "object" && !Array.isArray(config)
    && Object.keys(config).length === 2 && Object.prototype.hasOwnProperty.call(config, "apiBase")
    && Object.prototype.hasOwnProperty.call(config, "accessToken"), "invalid_input");
  const base = target(config.apiBase);
  const session = createTokenSession(config.accessToken);
  async function read<T>(operation: ReadOperation, options: ResolvedOptions, normalize: (body: unknown) => T): Promise<T> {
    const request = session.begin(options.signal);
    try {
      const response = await fetch(base + readPath(operation, options), {
        method: "GET", credentials: "omit", mode: "same-origin", redirect: "error", cache: "no-store",
        referrerPolicy: "no-referrer", headers: { Accept: "application/json", Authorization: session.authorizationHeader() },
        signal: request.signal,
      });
      if (response.status !== 200) {
        try { void response.body?.cancel().catch(() => {}); } catch { /* Never parse an error response. */ }
        const codes: Readonly<Record<number, ClientErrorCode>> = { 401: "unauthorized", 403: "forbidden", 404: "not_found", 429: "rate_limited" };
        const code = codes[response.status] ?? "server_error";
        if (response.status === 401) session.disconnect();
        throw new ClientError(code, response.status);
      }
      const result = normalize(await bodyJson(response, responseProfile(operation)));
      if (!session.isConnected()) throw new ClientError("disconnected");
      if (request.signal.aborted) throw new ClientError(request.reason() ?? "aborted");
      return result;
    } catch (error: unknown) {
      if (error instanceof ClientError) throw error;
      throw new ClientError(request.reason() ?? "offline");
    } finally { request.finish(); }
  }
  return createReadOnlyClient(read, session.disconnect, { mode: "live", sourceLabel: "Canlı API · aynı HTTPS kaynağı",
    referenceTime: null, apiBase: base, scenario: null });
}
