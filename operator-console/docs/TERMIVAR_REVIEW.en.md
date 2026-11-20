# Termivar Assessment Review

**Termivar Assessments** reads supported, previously prepared Termivar JSON artefacts in the local browser. It is not a scanner, evaluator or report generator. **An assessment result is not verified security status.** It proves neither that Termivar is installed/running on a device nor authority to act on a target. [Türkçe kullanım](TERMIVAR_REVIEW.tr.md).

## Using the workspace

1. Open **Termivar Assessments** and explicitly select one local assessment JSON file, up to **1 MiB**. Example buttons load separately labelled synthetic data; an example never silently replaces an invalid file.
2. Read the version, completion, scope and missing-information statements. Search/filter only the loaded records and select one. A diagnostic whose item projection is unavailable is not shown as a completed empty assessment.
3. Free-text titles/descriptions and metadata start hidden. Showing details is an explicit choice for this import only; values remain plain text. A field named “redacted” does not guarantee that an untrusted file contains no secrets.
4. Optionally select a manifest of at most **64 KiB**, **separately and explicitly**. This native manifest ceiling is separate from the assessment's 1 MiB UI limit. Only the selected JSON's exact byte length, SHA256 and summary relationship to its manifest entry are checked. No HTML or other file is located or read.
5. Selecting a new assessment clears the previous model and presentation preference. An invalid replacement cannot retain the old success as its result. Clear removes derived views; reload does not restore them. Normal navigation and TR/EN changes preserve the import. Tenant/source/example-scenario/session changes and existing access cleanup conservatively clear it.

This local workspace is separate from inventory. It does not map target hostnames/IPs to `device_id`, associate a report with a device, write to the backend or copy data automatically into report drafts, device comparison or policy previews. It does not replace HBF's existing summary importer.

## Supported closed subset

| Artefact | Support and boundary |
|---|---|
| `venom-rendered-assessment/v1` | Completed base `web-review` document with nine required root fields and twenty actual fields per item. Optional capability audits are unsupported in this version; they are not stripped to make an extended report appear accepted. |
| `web-assessment/v2` | Separate exact-origin diagnostic identified by `schema_version`, with `disposition=incomplete|failed` only. Scope/profile limits/usage/reasons and unavailable item projection are reviewed; this is not a completed assessment. Advanced audit extensions and the single-resource diagnostic subtype are unsupported. |
| `termivar-report-bundle/v1` manifest | Optional, separately selected manifest. Its actual two fixed entries are validated structurally; only the selected JSON's bytes and summary are checked. HTML is not read and the full bundle is not verified. |
| `termivar-report-comparison/v1` and other types | Explicitly unsupported as assessment imports. A comparison is not a new scan, remediation proof or evidence of equivalent assessment coverage. |

UTF-8, duplicate-key, invalid/non-finite-number, safe-integer, field and version checks remain enforced. The assessment is parsed with the closed `termivar-assessment-v1` `strictJson` profile: **depth 12**, **300,000 nodes**, **1,024 UTF-16 code units per string**, **4,096 array elements**, **32 object keys** and **600,000 tokens**, plus narrower field-specific bounds (at most 4,096 items, 1,024 subjects/forms and 256 evidence references per item). The profile is sized from these adapter limits and the 1 MiB file limit, so a document the adapter accepts below 1 MiB is not rejected by the parsing budgets. The optional manifest keeps the shared default profile (depth 12, 12,000 nodes, 100 array elements, 32 object keys, 60,000 tokens) inside its 64 KiB limit. The native 16 MiB renderer limit is not a UI limit: native documents above 1 MiB are rejected as too large. No first-N truncation is presented as a complete assessment. Rejection is not a diagnosis of malicious content.

## Actual JSON to UI mapping

| Source fields | Meaning and limits |
|---|---|
| Complete `schema`, `source_schema`, `run_schema`, `profile_schema`, `profile`, `status` | Supported document family and completion claim; not producer identity or a safe-target conclusion. |
| Complete `subject_count`, `item_count`, `items` | Reported scope/item totals and disposition/severity counts of loaded records; not vulnerability counts or coverage percentages. |
| Item `disposition`, `claim_basis`, `severity`, `confidence_ppm` | Imported classification/basis/metadata; not independent confidence, impact or risk scoring. `severity=null` remains unassigned. |
| Item `evidence_count` and the three `*_evidence_references` arrays | Opaque reference counts and supported linkage consistency; no external evidence is opened or independently established. |
| Item `subject_reference`, `fingerprint`, `capability_id` | Document/source identifiers, not target locations, device mappings, signatures or authority. |
| Item `title`, `redacted_summary`, `category`, `cwe`, `remediation` | Supplied fixed text/recommendations, shown as text only after the presentation choice. A recommendation is not an applied or verified fix. |
| Item `case_reference`, `outcome_reference`, `verification_stage` | Opaque producer-side verifier linkage; it does not upgrade a `confirmed` claim to independent console verification. |
| Diagnostic `disposition`, `incomplete_reasons`, `assessment.report.assessment_items` | Incompleteness/started failure and unavailable item projection; missing items do not become zero findings. |
| Diagnostic `profile_contract.limits`, `assessment.report.usage` | Explicit limits and usage only when supplied. `max_total_requests` remains the request limit and `max_wall_time_ms` becomes coverage `wallTimeLimitMs`, separate from usage. Requests are not successful responses or findings; staying within a budget does not establish that all checks completed. |
| Diagnostic `semantics`, `defense`, `transport`, optional `failure_inventory` | Supported closed counters/consistency fields are validated. If present, `failure_inventory.consistent` and `unrepresented_ledger_subjects` are preserved as coverage `inventoryConsistent` / `unrepresentedLedgerSubjects`; inconsistency is not a clean result. Raw subject/form internals, query/control names and `target_origin` are validated then omitted from the UI model. |
| Manifest `producer`, `assessment`, fixed `files` entries | Producer claims, summary and byte metadata. No manifest means no guessed producer. Declared HTML metadata is not a selected/checked HTML payload. |

The completed base JSON has no start/end timestamps, producer object or request budgets/usage. These remain **Not present in this artefact**. File read time is not scan time. A diagnostic's `elapsed_ms` is a supplied duration, not a start/end timestamp. Real zero and missing data remain distinct. Unreported checks or completion results are not reconstructed.

## Observation, evidence, NeedsReview and KnowledgeOnly

Actual `claim_basis` values are **`observation`**, **`differential`** and **`verifier_transition`**. `evidence` is a reference/count concept, not another claim-basis value or finding category.

- `informational` with `observation` is a bounded observation claim, not a vulnerability, impact or verified fix.
- `needs_review` with `differential` is a review candidate. Supported linkage can use one direct reference or control/candidate references; it is not a definitive vulnerability verdict.
- `confirmed` with `verifier_transition` requires the source's complete opaque case/outcome/stage linkage. This reader independently verifies neither its producer nor the real-world claim.
- **KnowledgeOnly** is a runtime authority concept, not a standalone field, disposition or counter in these assessment wire formats. No KnowledgeOnly/“clean”/“critical” category is invented.

A completed empty item list, an incomplete assessment and an unsupported/missing result format remain distinct. None yields **Safe**, **Protected**, **Fixed**, **Verified** or a risk score. An observation disappearing, or appearing only-in-before in a separate comparison, does not prove remediation.

## What a manifest check means

The optional manifest is considered only after explicit selection. `selected_json_matches` means that the captured selected JSON's exact length/SHA256 and completed summary match its manifest JSON entry. `mismatch` means that relationship was not established; malicious tampering is not assumed. The exact selected bytes are bound, not a canonical reserialization.

HTML is never selected, read, opened or hashed. Fixed manifest names are not followed as paths. This is therefore **not full bundle verification**, HTML/JSON semantic equivalence, producer authentication, scope authority, finding accuracy or remediation proof. A payload and manifest can be edited consistently; a match is not a signature. Producer verification remains **not_verified**. HBF's local numeric summary and the central `latest_report` DTO are separate contracts.

## Memory and sensitive presentation

Files are read only through explicit File API selection. There is no network/upload, scanner/runtime, external URL/evidence opening, generated script/HTML/command, separate raw HTTP/evidence-field opening action, copy/export/print/PDF or persistent browser storage. Untrusted title/summary/metadata text may nevertheless contain HTTP content or secrets; opting in does not sanitize it. The raw artefact is not placed in the global store; only a validated closed immutable model remains. Hidden text is omitted from DOM/attributes rather than hidden with CSS; hidden-field search is not a match oracle.

Filenames and private targets are not written to titles, URLs, logs or analytics. Showing details does not encrypt or anonymize imported data; supplied “redacted” text still needs care. Clear does not promise forensic erasure of browser/OS memory.

## Sources, examples and work not performed

The local `ITherso/termivar` checkout was reviewed read-only at commit `6a2639348c2366d0bf71b9a34e5484d40aa393a3`: [reporting.md](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md), [assessment_scan.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/assessment_scan.rs), [report_bundle.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/report_bundle.rs), [import.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs), and [scan_profile.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/scan_profile.rs). Local paths and exact example byte/SHA256 provenance are in the [example record](../src/features/termivarReview/examples/README.md).

The built-in complete/incomplete files are hand-authored: **Example Termivar assessment — no scan was performed against a real target.** Separate `bundle-assessment.json` and `bundle-manifest.json` are unchanged copies of a historical benign numeric-loopback fixture, not scanner outputs generated this phase. They include no HTML. Examples never automatically replace invalid user input.

Actual typecheck/build and limited manual product observations are recorded separately in [Phase11 delivery](DELIVERY.tr.md). No tests/runners/coverage, scanner/runtime or fixture server, live API/IdP/PostgreSQL, Windows/VM/driver/admin operations, remote actions, print/PDF/export or deployment/push/release were run this phase. Historical test counts are not new workspace acceptance. Backend, HBF, wheel, auth, policy and dependency locks remain unchanged.
