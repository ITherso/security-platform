/** Only the unwrapped output of `security-policy preview` v1 is supported. */
import { strictJson } from "../../data/normalize";
import { freezePolicyReview, MAX_POLICY_REVIEW_BYTES, POLICY_PREVIEW_CONTRACT, PolicyReviewError, policyReviewRequire } from "./policyReviewModel";
import type { PolicyReviewContext, PolicyReviewDecision, PolicyReviewDocument, PolicyReviewEvaluation,
  PolicyReviewScenario, PolicyReviewSource, PolicyReviewTrace } from "./policyReviewModel";

const BLOCKERS = ["evaluator_unavailable", "invalid_policy_bundle", "ambiguous_equal_prefix_zones", "insufficient_context",
  "input_limit_exceeded", "invalid_scenario", "invalid_evaluator_result", "evaluator_failed"] as const;
const ROOT_KEYS = ["contract_version", "status", "blocker_codes", "legacy_base_version", "base_fingerprint", "candidate_fingerprint",
  "adapter_fingerprint", "preview_fingerprint", "adapter_identity", "results", "authorization", "execution_authorized", "verification", "scope"];
const HEX = /^[a-f0-9]{64}$/;

function fullMatch(pattern: RegExp, value: string): boolean {
  // JS `$` can stop before a final line break; constrained CLI fields cannot.
  const match = pattern.exec(value);
  return match !== null && match.index === 0 && match[0] === value;
}

function object(input: unknown, keys: readonly string[]): Record<string, unknown> {
  policyReviewRequire(input !== null && typeof input === "object" && !Array.isArray(input));
  const result = input as Record<string, unknown>, actual = Object.keys(result);
  policyReviewRequire(actual.length === keys.length && actual.every((key) => keys.includes(key))
    && keys.every((key) => Object.prototype.hasOwnProperty.call(result, key)));
  return result;
}
function text(input: unknown, maximum: number, minimum = 0): string {
  policyReviewRequire(typeof input === "string" && input.length <= maximum * 2 && [...input].length <= maximum
    && [...input].length >= minimum && !/\u0000|[\uD800-\uDFFF]/u.test(input));
  return input;
}
function integer(input: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): number {
  policyReviewRequire(typeof input === "number" && Number.isSafeInteger(input) && input >= minimum && input <= maximum);
  return input;
}
function boolean(input: unknown): boolean { policyReviewRequire(typeof input === "boolean"); return input; }
function choice<const T extends readonly string[]>(input: unknown, values: T): T[number] {
  policyReviewRequire(typeof input === "string" && values.some((value) => value === input)); return input as T[number];
}
function array<T>(input: unknown, maximum: number, map: (value: unknown) => T): T[] {
  policyReviewRequire(Array.isArray(input) && input.length <= maximum); return (input as unknown[]).map(map);
}
function nullable<T>(input: unknown, map: (value: unknown) => T): T | null { return input === null ? null : map(input); }
function fingerprint(input: unknown, namespace: "bundle" | "adapter" | "preview"): string | null {
  return nullable(input, (value) => {
    const result = text(value, 96, 1), prefix = `sp-hbf-${namespace}-v1:sha256:`;
    policyReviewRequire(result.startsWith(prefix) && fullMatch(HEX, result.slice(prefix.length))); return result;
  });
}
function legacy(input: unknown): string | null {
  return nullable(input, (value) => { const result = text(value, 64, 64); policyReviewRequire(fullMatch(HEX, result)); return result; });
}
function address(input: unknown): string {
  const result = text(input, 45, 2);
  if (result.includes(":")) {
    // CLI ipaddress output uses hexadecimal IPv6, with no zone IDs or dotted suffix.
    policyReviewRequire(fullMatch(/^[a-f0-9:]+$/, result) && !result.includes(":::"));
    const split = result.split("::"); policyReviewRequire(split.length <= 2);
    const groups = result.split(":").filter(Boolean);
    policyReviewRequire(groups.every((group) => fullMatch(/^[a-f0-9]{1,4}$/, group))
      && (split.length === 2 ? groups.length < 8 : groups.length === 8));
    policyReviewRequire(split.every((side) => side === "" || side.split(":").every((group) => fullMatch(/^[a-f0-9]{1,4}$/, group))));
    if (split.length === 1) policyReviewRequire(!result.startsWith(":") && !result.endsWith(":"));
  } else {
    const groups = result.split(".");
    policyReviewRequire(groups.length === 4 && groups.every((group) => fullMatch(/^(?:0|[1-9][0-9]{0,2})$/, group) && Number(group) <= 255));
  }
  return result;
}
function scenarioContext(input: unknown): { scenarioId: string; context: PolicyReviewContext } {
  const value = object(input, ["scenario_id", "src_ip", "dst_ip", "protocol", "dst_port", "network_profile", "evaluation_local_time", "src_geo"]);
  const scenarioId = text(value.scenario_id, 64, 1); policyReviewRequire(fullMatch(/^[A-Za-z0-9._-]+$/, scenarioId));
  const sourceIp = address(value.src_ip), destinationIp = address(value.dst_ip);
  policyReviewRequire(sourceIp.includes(":") === destinationIp.includes(":"));
  const localTime = nullable(value.evaluation_local_time, (time) => {
    const result = text(time, 15, 8);
    policyReviewRequire(fullMatch(/^(?:[01][0-9]|2[0-3]):[0-5][0-9]:[0-5][0-9](?:\.[0-9]{1,6})?$/, result)); return result;
  });
  const sourceCountry = nullable(value.src_geo, (country) => {
    const result = text(country, 2, 2); policyReviewRequire(fullMatch(/^[A-Z]{2}$/, result)); return result;
  });
  return { scenarioId, context: { sourceIp, destinationIp, protocol: choice(value.protocol, ["TCP", "UDP"]),
    destinationPort: integer(value.dst_port, 1, 65535), networkProfile: nullable(value.network_profile, (profile) => choice(profile, ["HOME", "WORK", "PUBLIC"])),
    localTime, sourceCountry } };
}
function decision(input: unknown): PolicyReviewDecision {
  const value = object(input, ["action", "policy_id", "policy_name", "reason", "temp_block_sec", "nat", "log"]);
  const result: PolicyReviewDecision = { action: choice(value.action, ["ALLOW", "DENY", "DENY_TEMP"]),
    policyId: nullable(value.policy_id, (id) => integer(id, 1)), policyName: nullable(value.policy_name, (name) => text(name, 256)),
    reason: text(value.reason, 1024), tempBlockSeconds: nullable(value.temp_block_sec, (seconds) => integer(seconds, 1)),
    natIntent: boolean(value.nat), logIntent: boolean(value.log) };
  policyReviewRequire((result.action === "DENY_TEMP") === (result.tempBlockSeconds !== null)
    && (!result.natIntent || result.action === "ALLOW") && (result.policyId === null) === (result.policyName === null));
  return result;
}
function trace(input: unknown): PolicyReviewTrace {
  const value = object(input, ["policy_id", "policy_name", "matched", "selected", "reasons"]);
  return { policyId: integer(value.policy_id, 1), policyName: text(value.policy_name, 256), matched: boolean(value.matched),
    selected: boolean(value.selected), reasons: array(value.reasons, 4, (reason) => text(reason, 1024)) };
}
function evaluation(input: unknown): PolicyReviewEvaluation {
  const value = object(input, ["decision", "trace", "trace_total", "trace_complete"]);
  const result = { decision: decision(value.decision), trace: array(value.trace, 64, trace),
    traceTotal: integer(value.trace_total, 0, 500), traceComplete: boolean(value.trace_complete) };
  // The CLI retains at most 64 rows and explicitly reports truncation.
  policyReviewRequire(result.trace.length === Math.min(result.traceTotal, 64)
    && result.traceComplete === (result.traceTotal <= 64));
  return result;
}
function comparison(input: unknown): PolicyReviewScenario {
  const value = object(input, ["scenario", "base", "candidate", "decision_changed", "matched_policy_changed"]);
  const context = scenarioContext(value.scenario), base = evaluation(value.base), candidate = evaluation(value.candidate);
  policyReviewRequire(context.context.networkProfile !== null && context.context.localTime !== null);
  const decisionChanged = boolean(value.decision_changed), matchedPolicyChanged = boolean(value.matched_policy_changed);
  // Check the producer's change flags against its supplied scalars; no policy is evaluated.
  policyReviewRequire(decisionChanged === (base.decision.action !== candidate.decision.action
    || base.decision.tempBlockSeconds !== candidate.decision.tempBlockSeconds || base.decision.natIntent !== candidate.decision.natIntent
    || base.decision.logIntent !== candidate.decision.logIntent));
  policyReviewRequire(matchedPolicyChanged === (base.decision.policyId !== candidate.decision.policyId || base.decision.policyName !== candidate.decision.policyName));
  const changeType = !decisionChanged ? matchedPolicyChanged ? "policy_only_changed" : "unchanged"
    : base.decision.action === "ALLOW" && candidate.decision.action === "DENY" ? "allow_to_deny"
      : base.decision.action === "DENY" && candidate.decision.action === "ALLOW" ? "deny_to_allow" : "other_changed";
  return { ...context, base, candidate, decisionChanged, matchedPolicyChanged, changeType };
}
function adapterIdentity(input: unknown): void {
  const value = object(input, ["contract_version", "evaluator_contract", "normalization_version", "python_implementation", "python_version", "pydantic_version", "source_manifest"]);
  policyReviewRequire(value.contract_version === "sp-hbf-adapter/v1" && value.evaluator_contract === "hbf-explicit-time-profile/v1"
    && value.normalization_version === "hbf-source-normalization/v1");
  text(value.python_implementation, 32, 1); text(value.python_version, 32, 1); text(value.pydantic_version, 32, 1);
  const manifest = array(value.source_manifest, 16, (row) => {
    const entry = object(row, ["component", "name", "sha256"]), component = choice(entry.component, ["hbf", "platform"]);
    const name = text(entry.name, 64, 1); policyReviewRequire(fullMatch(/^[a-z_]+\.py$/, name));
    const digest = text(entry.sha256, 64, 64); policyReviewRequire(fullMatch(HEX, digest)); return `${component}:${name}`;
  });
  policyReviewRequire(manifest.length >= 1 && new Set(manifest).size === manifest.length);
  // Source names, source digests and runtime strings are validated, then discarded.
  // Their presence is not producer verification or an attestation.
}
function normalize(input: unknown, source: PolicyReviewSource): PolicyReviewDocument {
  policyReviewRequire(input !== null && typeof input === "object" && !Array.isArray(input));
  const header = input as Record<string, unknown>;
  if (!Object.prototype.hasOwnProperty.call(header, "contract_version")) throw new PolicyReviewError("unsupported_artifact");
  policyReviewRequire(header.contract_version === POLICY_PREVIEW_CONTRACT, "unsupported_version");
  const value = object(input, ROOT_KEYS);
  policyReviewRequire(value.authorization === "not_evaluated" && value.execution_authorized === false
    && value.verification === "not_performed" && value.scope === "packet_policy_preview_only");
  const status = choice(value.status, ["ok", "blocked"]), blockerCodes = array(value.blocker_codes, 16, (code) => choice(code, BLOCKERS));
  policyReviewRequire(new Set(blockerCodes).size === blockerCodes.length);
  const legacyBaseVersion = legacy(value.legacy_base_version), baseFingerprint = fingerprint(value.base_fingerprint, "bundle"),
    candidateFingerprint = fingerprint(value.candidate_fingerprint, "bundle"), adapterFingerprint = fingerprint(value.adapter_fingerprint, "adapter"),
    previewFingerprint = fingerprint(value.preview_fingerprint, "preview");
  if (value.adapter_identity !== null) adapterIdentity(value.adapter_identity);
  const scenarios = array(value.results, 32, comparison);
  policyReviewRequire(new Set(scenarios.map((row) => row.scenarioId)).size === scenarios.length);
  if (status === "ok") policyReviewRequire(blockerCodes.length === 0 && scenarios.length >= 1 && legacyBaseVersion !== null
    && baseFingerprint !== null && candidateFingerprint !== null && adapterFingerprint !== null && previewFingerprint !== null && value.adapter_identity !== null);
  else policyReviewRequire(blockerCodes.length >= 1 && scenarios.length === 0 && previewFingerprint === null);
  return freezePolicyReview({ source, artifactType: "preview", contractVersion: POLICY_PREVIEW_CONTRACT, status, blockerCodes,
    legacyBaseVersion, baseFingerprint, candidateFingerprint, adapterFingerprint, previewFingerprint, scenarios,
    authorization: "not_evaluated", executionAuthorized: false, verification: "not_performed", scope: "packet_policy_preview_only" });
}

export function parsePolicyReview(bytes: Uint8Array, source: PolicyReviewSource = "file"): PolicyReviewDocument {
  policyReviewRequire(bytes instanceof Uint8Array && (source === "file" || source === "example"));
  policyReviewRequire(bytes.byteLength <= MAX_POLICY_REVIEW_BYTES, "file_too_large");
  let contents: string;
  try { contents = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { throw new PolicyReviewError("invalid_utf8"); }
  let input: unknown;
  try { input = strictJson(contents, "sp-hbf-preview-v1"); }
  catch { throw new PolicyReviewError("invalid_json"); }
  // strictJson bounds depth/nodes/strings, rejects duplicate keys, non-finite,
  // fractional/unsafe numbers, prototype keys and malformed JSON. No I/O here.
  return normalize(input, source);
}
