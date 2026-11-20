/** Display-only native subsets. No scanner, target following, evidence or HTML loading. */
import { strictJson } from "../../data/normalize";
import type { StrictJsonProfile } from "../../data/normalize";
import { TERMIVAR_AUDIT_BOUND_CAPABILITIES, TERMIVAR_CLAIM_BASES, TERMIVAR_DIAGNOSTIC_FIELDS, TERMIVAR_DIAGNOSTIC_REPORT_FIELDS,
  TERMIVAR_DIAGNOSTIC_SCHEMA, TERMIVAR_DISPOSITIONS, TERMIVAR_INCOMPLETE_REASONS, TERMIVAR_ITEM_FIELDS, TERMIVAR_MANIFEST_SCHEMA, TERMIVAR_PROFILE_CAPABILITIES,
  TERMIVAR_PROFILE_LIMITS, TERMIVAR_RENDERED_FIELDS, TERMIVAR_RENDERED_SCHEMA, TERMIVAR_SEVERITIES } from "./termivarContracts";
import { freezeTermivar, MAX_TERMIVAR_MANIFEST_BYTES, MAX_TERMIVAR_REVIEW_BYTES, TermivarReviewError, termivarRequire } from "./termivarModel";
import type { AssessmentDocument, ManifestReview, TermivarCoverage, TermivarFinding, TermivarReviewSource } from "./termivarModel";

const HEX = /^[a-f0-9]{64}$/;
const UINT32 = 4294967295;
type Projection = Omit<AssessmentDocument, "source" | "selectedBytesSha256" | "selectedByteLength" | "sourceClaim" | "producerVerification">;
function full(pattern: RegExp, value: string): boolean { const match = pattern.exec(value); return match !== null && match.index === 0 && match[0] === value; }
function object(input: unknown, required: readonly string[], optional: readonly string[] = []): Record<string, unknown> {
  termivarRequire(input !== null && typeof input === "object" && !Array.isArray(input));
  const result = input as Record<string, unknown>, keys = Object.keys(result);
  termivarRequire(required.every((key) => Object.prototype.hasOwnProperty.call(result, key)));
  termivarRequire(keys.every((key) => required.includes(key) || optional.includes(key)), "unsupported_extension"); return result;
}
function text(input: unknown, maximum: number, minimum = 1): string {
  termivarRequire(typeof input === "string" && input.length <= maximum && !/\u0000|[\uD800-\uDFFF]/u.test(input)
    && new TextEncoder().encode(input).byteLength <= maximum && input.length >= minimum); return input;
}
function integer(input: unknown, minimum = 0, maximum = Number.MAX_SAFE_INTEGER): number {
  termivarRequire(typeof input === "number" && Number.isSafeInteger(input) && input >= minimum && input <= maximum); return input;
}
function boolean(input: unknown): boolean { termivarRequire(typeof input === "boolean"); return input; }
function choice<const T extends readonly string[]>(input: unknown, choices: T): T[number] {
  termivarRequire(typeof input === "string" && choices.some((value) => value === input)); return input as T[number];
}
function array<T>(input: unknown, maximum: number, map: (value: unknown, index: number) => T): T[] {
  termivarRequire(Array.isArray(input) && input.length <= maximum); return (input as unknown[]).map(map);
}
function nullable<T>(input: unknown, map: (value: unknown) => T): T | null { return input === null ? null : map(input); }
function code(input: unknown): string { const value = text(input, 128); termivarRequire(full(/^[a-z][a-z0-9_]*$/, value)); return value; }
function reference(input: unknown, kind: string): { text: string; number: number } {
  const value = text(input, 128), prefix = `${kind}-`; termivarRequire(value.startsWith(prefix));
  const suffix = value.slice(prefix.length); termivarRequire(full(/^(?:[0-9]{4}|[1-9][0-9]{4,9})$/, suffix));
  return { text: value, number: integer(Number(suffix), 0, UINT32) };
}
function digest(input: unknown, prefix = ""): string {
  const value = text(input, prefix.length + 64); termivarRequire(value.startsWith(prefix) && full(HEX, value.slice(prefix.length))); return value;
}
function rawJson(bytes: Uint8Array, maximum: number, profile: StrictJsonProfile): unknown {
  termivarRequire(bytes instanceof Uint8Array); termivarRequire(bytes.byteLength <= maximum, "file_too_large");
  let value: string;
  try { value = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes); }
  catch { throw new TermivarReviewError("invalid_utf8"); }
  try { return strictJson(value, profile); } catch { throw new TermivarReviewError("invalid_json"); }
}
function absentCoverage(projectionStatus: "available" | "unavailable"): TermivarCoverage {
  return { scope: null, startedAt: null, finishedAt: null, requestLimit: null, wallTimeLimitMs: null, requestsUsed: null, activeVerifications: null,
    responseBytes: null, elapsedMs: null, projectionStatus, projectionCode: null, committedPassiveObservations: null,
    semanticTruncated: null, omittedDispatchReceipts: null, inventoryConsistent: null, unrepresentedLedgerSubjects: null };
}
function item(input: unknown, subjectCount: number, index: number, fingerprints: Set<string>): TermivarFinding {
  const value = object(input, TERMIVAR_ITEM_FIELDS); termivarRequire(value.schema === "venom-assessment-item/v1");
  const capabilityId = text(value.capability_id, 128);
  termivarRequire(!TERMIVAR_AUDIT_BOUND_CAPABILITIES.some((entry) => entry === capabilityId), "unsupported_extension");
  termivarRequire(reference(value.subject_reference, "subject").number < subjectCount);
  const fingerprint = digest(value.fingerprint, "sha256:"); termivarRequire(!fingerprints.has(fingerprint)); fingerprints.add(fingerprint);
  const unique = new Set<string>();
  const counts = ["evidence_references", "control_evidence_references", "candidate_evidence_references"].map((key) =>
    array(value[key], 256, (entry) => { const ref = reference(entry, "evidence").text; termivarRequire(!unique.has(ref)); unique.add(ref); return ref; }).length);
  const [direct, control, candidate] = counts;
  termivarRequire(direct !== undefined && control !== undefined && candidate !== undefined && integer(value.evidence_count, 0, 256) === unique.size);
  const caseReference = nullable(value.case_reference, (entry) => reference(entry, "case"));
  const outcomeReference = nullable(value.outcome_reference, (entry) => reference(entry, "outcome"));
  const verificationStage = nullable(value.verification_stage, (entry) => choice(entry, ["passive", "active"]));
  const disposition = choice(value.disposition, TERMIVAR_DISPOSITIONS), claimBasis = choice(value.claim_basis, TERMIVAR_CLAIM_BASES);
  const noVerifier = caseReference === null && outcomeReference === null && verificationStage === null;
  termivarRequire(claimBasis === "observation" ? disposition === "informational" && direct > 0 && control === 0 && candidate === 0 && noVerifier
    : claimBasis === "differential" ? disposition === "needs_review" && noVerifier && (direct === 1 && control === 0 && candidate === 0 || direct === 0 && control > 0 && candidate > 0)
      : disposition === "confirmed" && direct > 0 && control === 0 && candidate === 0 && caseReference !== null && outcomeReference !== null && verificationStage !== null);
  const remediation = object(value.remediation, ["id", "summary"]);
  return { key: `finding-${index + 1}`, capabilityId, title: text(value.title, 1024), disposition, claimBasis,
    severity: nullable(value.severity, (entry) => choice(entry, TERMIVAR_SEVERITIES)), confidencePpm: integer(value.confidence_ppm, 0, 1000000),
    evidenceCount: unique.size, directEvidenceCount: direct, controlEvidenceCount: control, candidateEvidenceCount: candidate,
    redactedSummary: text(value.redacted_summary, 1024), category: text(value.category, 1024), cwe: nullable(value.cwe, (entry) => text(entry, 128)),
    remediationId: text(remediation.id, 128), remediationSummary: text(remediation.summary, 1024), verificationStage };
}
function rendered(input: unknown): Projection {
  const value = object(input, TERMIVAR_RENDERED_FIELDS);
  termivarRequire(value.schema === TERMIVAR_RENDERED_SCHEMA && value.source_schema === "venom-assessment-run/v1" && value.run_schema === "venom-run/v1"
    && value.profile_schema === "venom.scan-profile/v1" && value.profile === "web-review" && value.status === "complete");
  const subjectCount = integer(value.subject_count, 1, 1024), itemCount = integer(value.item_count, 0, 4096), fingerprints = new Set<string>();
  const findings = array(value.items, 4096, (entry, index) => item(entry, subjectCount, index, fingerprints)); termivarRequire(findings.length === itemCount);
  const counts = { informational: 0, needs_review: 0, confirmed: 0 }, severityCounts = { unassigned: 0, info: 0, low: 0, medium: 0, high: 0, critical: 0 };
  for (const finding of findings) { counts[finding.disposition]++; severityCounts[finding.severity ?? "unassigned"]++; }
  return { artifactType: "rendered_assessment", schema: TERMIVAR_RENDERED_SCHEMA, profile: "web-review", status: "complete", subjectCount, itemCount,
    findings, counts, severityCounts, incompleteReasons: [], coverage: absentCoverage("available") };
}
function profile(input: unknown): Record<string, number> {
  const value = object(input, ["schema", "profile", "scope", "capabilities", "limits", "defense"]);
  termivarRequire(value.schema === "venom.scan-profile/v1" && value.profile === "web-review" && value.scope === "exact-origin");
  const capabilities = object(value.capabilities, TERMIVAR_PROFILE_CAPABILITIES);
  TERMIVAR_PROFILE_CAPABILITIES.forEach((key) => termivarRequire(capabilities[key] === true));
  const limits = object(value.limits, TERMIVAR_PROFILE_LIMITS.map(([key]) => key)), result: Record<string, number> = {};
  for (const [key, minimum, maximum] of TERMIVAR_PROFILE_LIMITS) result[key] = integer(limits[key], minimum, maximum);
  const defense = object(value.defense, ["enforcement_enabled"]); boolean(defense.enforcement_enabled);
  return result;
}
function terminal(input: unknown): void {
  if (input === null) return;
  const value = object(input, ["command", "stop_reason"]);
  choice(value.command, ["execute_action", "collect_active_evidence", "replan", "complete", "await_human_review", "halt", "other"]);
  nullable(value.stop_reason, code);
}
function runtimeLimit(input: unknown): void {
  if (input === null) return;
  const value = object(input, ["dimension", "limit", "observed", "action_id"]);
  code(value.dimension); integer(value.limit); integer(value.observed); nullable(value.action_id, (entry) => text(entry, 1024));
}
function diagnostic(input: unknown): Projection {
  const value = object(input, TERMIVAR_DIAGNOSTIC_FIELDS);
  termivarRequire(value.schema_version === TERMIVAR_DIAGNOSTIC_SCHEMA);
  const status = choice(value.disposition, ["incomplete", "failed"]), reasons = array(value.incomplete_reasons, 100, (entry) => choice(entry, TERMIVAR_INCOMPLETE_REASONS));
  termivarRequire(reasons.length > 0 && new Set(reasons).size === reasons.length);
  // Validate but deliberately discard the sensitive target. Never follow it.
  const target = text(value.target_origin, 1024);
  try {
    const origin = new URL(target);
    termivarRequire((origin.protocol === "https:" || origin.protocol === "http:") && origin.origin === target
      && origin.username === "" && origin.password === "" && origin.pathname === "/" && origin.search === "" && origin.hash === "");
  } catch { throw new TermivarReviewError("invalid_artifact"); }
  const limits = profile(value.profile_contract), assessment = object(value.assessment, ["scope", "report"]);
  termivarRequire(assessment.scope === "exact-origin");
  const report = object(assessment.report, TERMIVAR_DIAGNOSTIC_REPORT_FIELDS, ["failure_inventory"]);
  const subjectRefs = new Set<string>();
  const subjects = array(report.subjects, 1024, (input) => {
    const subject = object(input, ["subject_reference", "method", "depth", "provenance", "query_parameter_names", "discovery_evidence_count", "executed", "decision"]);
    const ref = reference(subject.subject_reference, "subject").text; termivarRequire(!subjectRefs.has(ref)); subjectRefs.add(ref);
    choice(subject.method, ["get", "head", "other"]); integer(subject.depth, 0, 16); choice(subject.provenance, ["authorized_root", "discovered", "other"]);
    array(subject.query_parameter_names, 256, (entry) => text(entry, 1024)); integer(subject.discovery_evidence_count); const executed = boolean(subject.executed);
    const decision = object(subject.decision, ["bootstrap_evidence_writes", "planning_turns", "verification_outcomes", "conclusive_outcomes", "inconclusive_outcomes",
      "unverified_evidence_writes", "terminal", "runtime_limit", "execution_failure_recorded"]);
    for (const key of ["bootstrap_evidence_writes", "planning_turns", "verification_outcomes", "conclusive_outcomes", "inconclusive_outcomes", "unverified_evidence_writes"]) integer(decision[key]);
    terminal(decision.terminal); runtimeLimit(decision.runtime_limit); boolean(decision.execution_failure_recorded);
    return executed;
  });
  const formRefs = new Set<string>();
  const forms = array(report.forms, 1024, (input) => {
    const form = object(input, ["form_reference", "method", "query_parameter_names", "control_names", "evidence_count"]);
    const ref = reference(form.form_reference, "form").text; termivarRequire(!formRefs.has(ref)); formRefs.add(ref);
    choice(form.method, ["get", "post", "dialog", "other"]);
    array(form.query_parameter_names, 256, (entry) => text(entry, 1024)); array(form.control_names, 256, (entry) => text(entry, 1024)); integer(form.evidence_count); return null;
  });
  const projection = object(report.assessment_items, ["projection_status", "code"], ["committed_passive_observations"]);
  termivarRequire(projection.projection_status === "unavailable");
  const projectionCode = choice(projection.code, ["incomplete_assessment_items_withheld", "runtime_failed_before_item_projection"]);
  const committed = Object.hasOwn(projection, "committed_passive_observations") ? integer(projection.committed_passive_observations) : null;
  termivarRequire(status === "incomplete" ? projectionCode === "incomplete_assessment_items_withheld" && committed === null
    : projectionCode === "runtime_failed_before_item_projection" && committed !== null);
  const semantics = object(report.semantics, ["entity_count", "entity_types", "truncated", "dropped_entities", "dropped_attributes", "dropped_sources"]);
  const entityTypes = object(semantics.entity_types, ["endpoint", "domain", "ip_address", "auth_artifact", "header", "technology", "parameter", "user_role", "other"]);
  Object.values(entityTypes).forEach((entry) => integer(entry));
  for (const key of ["entity_count", "dropped_entities", "dropped_attributes", "dropped_sources"]) integer(semantics[key]);
  const semanticTruncated = boolean(semantics.truncated);
  const defense = object(report.defense, ["mode", "observation_count", "metadata_only_observations", "complete_prefix_observations", "input_limited_observations", "challenge_observations",
    "rate_limit_observations", "transition_count", "candidate_block_transitions", "newly_rate_limited_transitions", "shadow_plan_count", "unchanged_actions", "deprioritized_actions", "suppressed_actions"]);
  choice(defense.mode, ["observation_only", "enforced"]); Object.entries(defense).forEach(([key, entry]) => { if (key !== "mode") integer(entry); });
  const usage = object(report.usage, ["retained_subjects", "executed_subjects", "retained_forms", "retained_unique_url_bytes", "total_requests", "active_verifications", "request_body_bytes", "response_bytes", "elapsed_ms"]);
  Object.values(usage).forEach((entry) => integer(entry));
  // Both native builders retain the authorized root, including pending/failed runs.
  const subjectCount = integer(usage.retained_subjects, 1, 1024), executedSubjects = integer(usage.executed_subjects, 0, 1024), retainedForms = integer(usage.retained_forms, 0, 1024);
  termivarRequire(executedSubjects <= subjectCount);
  integer(usage.total_requests, 0, UINT32); integer(usage.active_verifications, 0, 65535);
  const transport = object(report.transport, ["retained_dispatch_receipts", "omitted_dispatch_receipts"]);
  integer(transport.retained_dispatch_receipts); const omitted = integer(transport.omitted_dispatch_receipts);
  let inventoryConsistent: boolean | null = null, unrepresentedLedgerSubjects: number | null = null;
  if (Object.hasOwn(report, "failure_inventory")) {
    const failure = object(report.failure_inventory, ["consistent", "unrepresented_ledger_subjects"]);
    inventoryConsistent = boolean(failure.consistent); unrepresentedLedgerSubjects = integer(failure.unrepresented_ledger_subjects);
  }
  termivarRequire(status === "incomplete" ? inventoryConsistent === null : inventoryConsistent !== null);
  if (inventoryConsistent !== false) {
    termivarRequire(subjectCount === subjects.length && executedSubjects === subjects.filter(Boolean).length && retainedForms === forms.length);
    if (inventoryConsistent === true) termivarRequire(unrepresentedLedgerSubjects === 0);
  }
  return { artifactType: "web_assessment_diagnostic", schema: TERMIVAR_DIAGNOSTIC_SCHEMA, profile: "web-review", status, subjectCount, itemCount: null,
    findings: [], counts: null, severityCounts: null, incompleteReasons: reasons, coverage: { ...absentCoverage("unavailable"), scope: "exact-origin",
      requestLimit: limits.max_total_requests ?? null, wallTimeLimitMs: limits.max_wall_time_ms ?? null, requestsUsed: integer(usage.total_requests), activeVerifications: integer(usage.active_verifications),
      responseBytes: integer(usage.response_bytes), elapsedMs: integer(usage.elapsed_ms), projectionCode, committedPassiveObservations: committed,
      semanticTruncated, omittedDispatchReceipts: omitted, inventoryConsistent, unrepresentedLedgerSubjects } };
}
export async function parseTermivarAssessment(bytes: Uint8Array, source: TermivarReviewSource = "file"): Promise<AssessmentDocument> {
  termivarRequire(bytes instanceof Uint8Array && (source === "file" || source === "example"));
  termivarRequire(bytes.byteLength <= MAX_TERMIVAR_REVIEW_BYTES, "file_too_large");
  const selected = new Uint8Array(bytes), input = rawJson(selected, MAX_TERMIVAR_REVIEW_BYTES, "termivar-assessment-v1");
  termivarRequire(input !== null && typeof input === "object" && !Array.isArray(input)); const header = input as Record<string, unknown>;
  let projection: Projection;
  if (header.schema === TERMIVAR_RENDERED_SCHEMA) projection = rendered(input);
  else if (header.schema_version === TERMIVAR_DIAGNOSTIC_SCHEMA) projection = diagnostic(input);
  else if (typeof header.schema === "string" && header.schema.startsWith("venom-rendered-assessment/")
    || typeof header.schema_version === "string" && header.schema_version.startsWith("web-assessment/")) throw new TermivarReviewError("unsupported_version");
  else throw new TermivarReviewError("unsupported_artifact");
  let selectedBytesSha256: string;
  try {
    termivarRequire(globalThis.crypto?.subtle !== undefined, "digest_unavailable");
    const hash = await globalThis.crypto.subtle.digest("SHA-256", selected);
    selectedBytesSha256 = Array.from(new Uint8Array(hash), (byte) => byte.toString(16).padStart(2, "0")).join("");
  } catch { throw new TermivarReviewError("digest_unavailable"); }
  return freezeTermivar({ ...projection, source, selectedBytesSha256, selectedByteLength: selected.byteLength,
    sourceClaim: "self_reported", producerVerification: "not_verified" });
}
export function parseTermivarManifest(bytes: Uint8Array, assessment: AssessmentDocument): ManifestReview {
  const input = rawJson(bytes, MAX_TERMIVAR_MANIFEST_BYTES, "default");
  termivarRequire(input !== null && typeof input === "object" && !Array.isArray(input)); const header = input as Record<string, unknown>;
  if (header.schema !== TERMIVAR_MANIFEST_SCHEMA) throw new TermivarReviewError(typeof header.schema === "string" && header.schema.startsWith("termivar-report-bundle/") ? "unsupported_version" : "unsupported_manifest");
  const value = object(input, ["schema", "producer", "assessment", "files"]);
  const producer = object(value.producer, ["product", "version"]); termivarRequire(producer.product === "Termivar"); const producerVersion = text(producer.version, 128);
  const semver = /^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(?:-([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?(?:\+([0-9A-Za-z-]+(?:\.[0-9A-Za-z-]+)*))?$/;
  const version = semver.exec(producerVersion); termivarRequire(version !== null && version[0] === producerVersion);
  for (const component of version.slice(1, 4)) termivarRequire(component !== undefined && BigInt(component) <= 18446744073709551615n);
  if (version[4] !== undefined) termivarRequire(version[4].split(".").every((part) => !full(/^[0-9]+$/, part) || part === "0" || !part.startsWith("0")));
  const summary = object(value.assessment, ["profile", "status", "subject_count", "item_count"]);
  termivarRequire(summary.profile === "web-review" && summary.status === "complete");
  const subjectCount = integer(summary.subject_count, 1, 1024), itemCount = integer(summary.item_count, 0, 4096);
  const files = array(value.files, 2, (input) => {
    const file = object(input, ["name", "format", "media_type", "byte_length", "sha256"]);
    const name = choice(file.name, ["assessment.html", "assessment.json"]);
    termivarRequire(file.format === (name === "assessment.html" ? "html" : "json") && file.media_type === (name === "assessment.html" ? "text/html; charset=utf-8" : "application/json"));
    // report_verify.rs binds each nonempty file to the native 16 MiB renderer ceiling.
    return { name, byteLength: integer(file.byte_length, 1, 16 * 1024 * 1024), sha256: digest(file.sha256) };
  });
  termivarRequire(files.length === 2 && new Set(files.map((file) => file.name)).size === 2);
  termivarRequire(assessment.artifactType === "rendered_assessment" && assessment.schema === TERMIVAR_RENDERED_SCHEMA && assessment.status === "complete", "unsupported_manifest");
  const json = files.find((file) => file.name === "assessment.json"); termivarRequire(json !== undefined);
  const jsonHashMatches = json.sha256 === assessment.selectedBytesSha256, jsonLengthMatches = json.byteLength === assessment.selectedByteLength,
    summaryMatches = summary.profile === assessment.profile && summary.status === assessment.status && subjectCount === assessment.subjectCount && itemCount === assessment.itemCount;
  return freezeTermivar({ status: jsonHashMatches && jsonLengthMatches && summaryMatches ? "selected_json_matches" : "mismatch", producerProduct: "Termivar",
    producerVersion, jsonHashMatches, jsonLengthMatches, summaryMatches, htmlStatus: "not_selected_not_checked", producerVerification: "not_verified", bundleVerification: "not_performed" });
}
