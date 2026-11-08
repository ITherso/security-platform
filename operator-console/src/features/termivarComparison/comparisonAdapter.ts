/** Interpret a pre-produced base comparison, never compare two assessments. */
import { strictJson } from "../../data/normalize";
import { COMPARISON_AUDIT_BOUND_CAPABILITIES, COMPARISON_CHANGED_FIELDS, COMPARISON_CLAIM_BASES, COMPARISON_DISPOSITIONS,
  COMPARISON_GROUPS, COMPARISON_INTERPRETATION_LIMITS, COMPARISON_RECORD_FIELDS, COMPARISON_ROOT_FIELDS, COMPARISON_SEVERITIES,
  COMPARISON_SOURCE_FIELDS, TERMIVAR_COMPARISON_SCHEMA } from "./comparisonContracts";
import { comparisonRequire, freezeComparisonReview, MAX_COMPARISON_REVIEW_BYTES, TermivarComparisonError } from "./comparisonModel";
import type { ComparisonEvidence, ComparisonGroup, ComparisonProjection, ComparisonRecord,
  ComparisonSource, ComparisonSourceMetadata, TermivarComparisonDocument } from "./comparisonModel";

function full(pattern: RegExp, value: string): boolean { const result = pattern.exec(value); return result !== null && result.index === 0 && result[0] === value; }
function object(input: unknown, keys: readonly string[]): Record<string, unknown> {
  comparisonRequire(input !== null && typeof input === "object" && !Array.isArray(input));
  const result = input as Record<string, unknown>;
  comparisonRequire(keys.every((key) => Object.hasOwn(result, key)));
  comparisonRequire(Object.keys(result).every((key) => keys.includes(key)), "unsupported_section"); return result;
}
function text(input: unknown, maximum: number): string {
  comparisonRequire(typeof input === "string" && input.length > 0 && input.length <= maximum && !/\u0000|[\uD800-\uDFFF]/u.test(input)
    && new TextEncoder().encode(input).byteLength <= maximum); return input;
}
function integer(input: unknown, maximum: number, minimum = 0): number {
  comparisonRequire(typeof input === "number" && Number.isSafeInteger(input) && input >= minimum && input <= maximum); return input;
}
function boolean(input: unknown): boolean { comparisonRequire(typeof input === "boolean"); return input; }
function choice<const T extends readonly string[]>(input: unknown, choices: T): T[number] {
  comparisonRequire(typeof input === "string" && choices.some((entry) => entry === input)); return input as T[number];
}
function nullable<T>(input: unknown, map: (value: unknown) => T): T | null { return input === null ? null : map(input); }
function array<T>(input: unknown, maximum: number, map: (value: unknown) => T): T[] {
  comparisonRequire(Array.isArray(input) && input.length <= maximum); return (input as unknown[]).map(map);
}
function digest(input: unknown, prefix = ""): string {
  const value = text(input, prefix.length + 64); comparisonRequire(value.startsWith(prefix) && full(/^[a-f0-9]{64}$/, value.slice(prefix.length))); return value;
}
function metadata(input: unknown): ComparisonSourceMetadata {
  const value = object(input, COMPARISON_SOURCE_FIELDS);
  comparisonRequire(value.schema === "venom-rendered-assessment/v1" && value.source_schema === "venom-assessment-run/v1" && value.run_schema === "venom-run/v1"
    && value.profile_schema === "venom.scan-profile/v1" && value.profile === "web-review" && value.status === "complete");
  object(value.optional_audits, []); // Never silently strip source coverage/audit metadata.
  return { sha256: digest(value.sha256), schema: "venom-rendered-assessment/v1", sourceSchema: "venom-assessment-run/v1", runSchema: "venom-run/v1",
    profileSchema: "venom.scan-profile/v1", profile: "web-review", status: "complete", subjectCount: integer(value.subject_count, 1024, 1), itemCount: integer(value.item_count, 4096) };
}
function evidence(input: unknown): ComparisonEvidence {
  const value = object(input, ["evidence_count", "evidence_reference_count", "control_reference_count", "candidate_reference_count", "case_present", "outcome_present", "verification_stage"]);
  const result = { evidenceCount: integer(value.evidence_count, 256), directReferenceCount: integer(value.evidence_reference_count, 256),
    controlReferenceCount: integer(value.control_reference_count, 256), candidateReferenceCount: integer(value.candidate_reference_count, 256),
    casePresent: boolean(value.case_present), outcomePresent: boolean(value.outcome_present), verificationStage: nullable(value.verification_stage, (stage) => choice(stage, ["passive", "active"])) };
  comparisonRequire(result.evidenceCount === result.directReferenceCount + result.controlReferenceCount + result.candidateReferenceCount); return result;
}
function projection(input: unknown): ComparisonProjection {
  const value = object(input, COMPARISON_CHANGED_FIELDS), remediation = object(value.remediation, ["id", "summary"]), links = evidence(value.evidence);
  const disposition = choice(value.disposition, COMPARISON_DISPOSITIONS), claimBasis = choice(value.claim_basis, COMPARISON_CLAIM_BASES);
  const direct = links.directReferenceCount, control = links.controlReferenceCount, candidate = links.candidateReferenceCount;
  const noVerifier = !links.casePresent && !links.outcomePresent && links.verificationStage === null;
  comparisonRequire(claimBasis === "observation" ? disposition === "informational" && direct > 0 && control === 0 && candidate === 0 && noVerifier
    : claimBasis === "differential" ? disposition === "needs_review" && noVerifier && (direct === 1 && control === 0 && candidate === 0 || direct === 0 && control > 0 && candidate > 0)
      : disposition === "confirmed" && direct > 0 && control === 0 && candidate === 0 && links.casePresent && links.outcomePresent && links.verificationStage !== null);
  return { title: text(value.title, 1024), category: text(value.category, 1024), disposition, claimBasis,
    severity: nullable(value.severity, (entry) => choice(entry, COMPARISON_SEVERITIES)), cwe: nullable(value.cwe, (entry) => text(entry, 128)),
    confidencePpm: integer(value.confidence_ppm, 1000000), redactedSummary: text(value.redacted_summary, 1024),
    remediation: { id: text(remediation.id, 128), summary: text(remediation.summary, 1024) }, evidence: links };
}
function record(input: unknown, group: ComparisonGroup, index: number, identities: Set<string>): ComparisonRecord {
  const value = object(input, COMPARISON_RECORD_FIELDS), fingerprint = digest(value.fingerprint, "sha256:"), capabilityId = text(value.capability_id, 128);
  comparisonRequire(!COMPARISON_AUDIT_BOUND_CAPABILITIES.some((entry) => entry === capabilityId), "unsupported_section");
  comparisonRequire(!identities.has(fingerprint)); identities.add(fingerprint);
  const before = nullable(value.before, projection), after = nullable(value.after, projection);
  const changedFields = array(value.changed_fields, 10, (entry) => choice(entry, COMPARISON_CHANGED_FIELDS));
  comparisonRequire(new Set(changedFields).size === changedFields.length);
  comparisonRequire(changedFields.every((field, offset) => offset === 0
    || COMPARISON_CHANGED_FIELDS.indexOf(field) > COMPARISON_CHANGED_FIELDS.indexOf(changedFields[offset - 1]!)));
  if (group === "only_in_before" || group === "only_in_after") {
    comparisonRequire(group === "only_in_before" ? before !== null && after === null : before === null && after !== null);
    comparisonRequire(changedFields.length === 0);
  } else {
    comparisonRequire(before !== null && after !== null);
    comparisonRequire(group === "changed" ? changedFields.length > 0 : changedFields.length === 0);
  }
  return { key: `comparison-${index + 1}`, group, fingerprint, capabilityId, before, after, changedFields };
}
export function parseTermivarComparison(bytes: Uint8Array, source: ComparisonSource = "file"): TermivarComparisonDocument {
  comparisonRequire(bytes instanceof Uint8Array && (source === "file" || source === "example"));
  comparisonRequire(bytes.byteLength <= MAX_COMPARISON_REVIEW_BYTES, "file_too_large");
  let contents: string;
  try { contents = new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes); } catch { throw new TermivarComparisonError("invalid_utf8"); }
  let input: unknown;
  try { input = strictJson(contents, "termivar-comparison-v1"); } catch { throw new TermivarComparisonError("invalid_json"); }
  comparisonRequire(input !== null && typeof input === "object" && !Array.isArray(input)); const header = input as Record<string, unknown>;
  if (header.schema !== TERMIVAR_COMPARISON_SCHEMA) throw new TermivarComparisonError(typeof header.schema === "string" && header.schema.startsWith("termivar-report-comparison/") ? "unsupported_version" : "unsupported_artifact");
  const value = object(input, COMPARISON_ROOT_FIELDS);
  comparisonRequire(value.scope_assurance === "operator-declared" && value.coverage_equivalence === "not-established" && value.source_authenticity === "not-established-by-parsing");
  const limits = array(value.interpretation_limits, 4, (entry) => text(entry, 1024));
  comparisonRequire(limits.length === COMPARISON_INTERPRETATION_LIMITS.length && limits.every((entry, index) => entry === COMPARISON_INTERPRETATION_LIMITS[index]));
  const before = metadata(value.before), after = metadata(value.after), identities = new Set<string>(), records: ComparisonRecord[] = [];
  const counts: Record<ComparisonGroup, number> = { only_in_after: 0, only_in_before: 0, changed: 0, unchanged: 0 };
  for (const group of COMPARISON_GROUPS) {
    let offset = 0;
    const entries = array(value[group], 4096, (entry) => record(entry, group, records.length + offset++, identities));
    counts[group] = entries.length;
    records.push(...entries); comparisonRequire(records.length <= 8192);
  }
  comparisonRequire(before.itemCount === counts.only_in_before + counts.changed + counts.unchanged
    && after.itemCount === counts.only_in_after + counts.changed + counts.unchanged);
  return freezeComparisonReview({ source, artifactType: "termivar_comparison", schema: TERMIVAR_COMPARISON_SCHEMA,
    scopeAssurance: "operator-declared", coverageEquivalence: "not-established", sourceAuthenticity: "not-established-by-parsing", before, after, records, counts });
}
