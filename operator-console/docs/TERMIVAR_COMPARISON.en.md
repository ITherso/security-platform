# Termivar Web assessment comparison

This view reads **precomputed JSON from the existing `termivar report compare` CLI** in the local browser. It does not repeat the CLI's offline operation, combine two assessments, run a scanner or introduce a comparison algorithm. [Türkçe kullanım](TERMIVAR_COMPARISON.tr.md).

## Opening and reviewing a file

1. Open comparison review within **Termivar Web Assessments**. Use **Open comparison file** to select one local `termivar-report-comparison/v1` JSON, up to **8 MiB**. An assessment, manifest, HTML document or before/after pair is not this importer's input.
2. Read the before/after source metadata and scope limits. The four group cards count the actual validated arrays; no fictional top-level `counts` field is expected.
3. Group cards, filtering and search operate only on loaded records. Select an item to inspect its supplied before/after projections. An empty filter says there are no displayed records in that group, not that there are no security problems.
4. **Show permitted comparison metadata** is an explicit choice for this import. Titles/capability/category/CWE/summary/remediation and source/item fingerprints are omitted from the initial DOM. When enabled, only permitted plain text appears; fingerprints start abbreviated and need a separate expansion for the full value. Text is not interpreted as HTML, links or commands. A “redacted” field name does not guarantee that an untrusted file contains no secrets.
5. A new selection clears the previous comparison and presentation preference. An invalid replacement retains no previous success. Clear removes derived data; reload does not restore it. Navigation and TR/EN preserve the import; tenant/source/session changes, disconnect and existing access cleanup conservatively clear it.

Assessment review, policy previews, device comparison and report drafts remain independent. Importing a comparison does not copy into them or change verified tenant/device security state. No source digest or target name is mapped to a device.

## Four groups and their limits

| Actual group | Meaning only |
|---|---|
| `only_in_after` | Present only in the supplied after report; no verified time of first appearance or new-vulnerability claim. |
| `only_in_before` | Present only in the supplied before report; **not Fixed, Resolved, Remediated or Safe**. |
| `changed` | A matched identity has different supported comparable content; not automatically increased/decreased risk or a different vulnerability. |
| `unchanged` | Equal supported item projections; not proof of equal security conditions, target identity or assessment coverage. |

The producer's matching uses stable fingerprints with compatible capability identities. This UI validates/displays the saved groups and does not pair new inputs. Local reference numbers, titles and order do not establish a target. Severity/confidence remain supplied values; the UI recalculates neither. Remediation text is a recommendation, not an applied or verified fix. No CVSS, risk/security score or vulnerability verification is derived.

`changed_fields` is also an imported source claim. Shape/order/uniqueness and group bindings are checked; the browser does not recalculate projection differences to create new groups or decisions.

## Actual JSON to UI mapping

| Field | Display and trust boundary |
|---|---|
| `schema` | Supported `termivar-report-comparison/v1`; another version is rejected. |
| `scope_assurance=operator-declared` | Operator assertion recorded by CLI `--same-scope`, not scope equality or target authority. |
| `coverage_equivalence=not-established` | Equivalent checks/evidence coverage has not been established. |
| `source_authenticity=not-established-by-parsing` | Parsing does not authenticate the producer/source. |
| `interpretation_limits` | Source contract limitations, never promoted to a positive security judgment. |
| `before`, `after` | Each carries SHA256, assessment/source/run/profile schemas, profile/status, subject/item totals and empty `optional_audits`. Missing times/producer/target are not invented. |
| Four group arrays | Counts come from actual array lengths. Up to 4,096 items per source and a reconciled union of at most 8,192 records; no silent truncation. |
| Item `fingerprint`, `capability_id`, `before`, `after`, `changed_fields` | Identity, supplied one/two-sided projections and reported changed fields. A null side denotes its one-sided group, not zero or a clean result. |
| Projection `title`, `category`, `disposition`, `claim_basis`, `severity`, `cwe`, `confidence_ppm`, `redacted_summary` | Source metadata/plain text without endorsement. `severity=null` remains unassigned; explicit zero remains supplied data. |
| Projection `remediation{id,summary}` | Source recommendation, not proof of implementation or verification. |
| Projection `evidence` | Evidence/direct/control/candidate reference counts, case/outcome presence flags and optional verification stage. No raw evidence is opened or independently established. |

Before/after SHA256 values identify **supplied source bytes**. This UI does not locate/open those source files or recalculate their digests from them. Equal hashes authenticate neither producer, target, scope, authority nor freshness. `--same-scope` records the operator's choice of reports for comparison; parsing does not establish equivalent scope.

## Optional sections are explicitly unsupported

This UI supports only the **base comparison v1** subset. Any optional root comparison section or nonempty before/after `optional_audits` rejects the **entire file** with `unsupported_section`. It neither displays partial base counts as a complete interpretation nor silently drops an extension. There is no retained, uninterpreted partial extension model in this version.

The reviewed native source contains `control_reference_mapping_comparison` and `wordpress_review_comparison`, including WordPress nested comparison `/v1`–`/v4` constants. They are **unsupported in this UI version** and are not converted between versions. Other comparison/audit extensions share that boundary. Wider native CLI support does not imply support here. Mapping/catalogue/methodology changes are not newly observed target vulnerabilities, remediation or compliance transitions. This viewer does not calculate missing/one-sided audit outcomes.

## Bounds and local privacy

Only explicit File API selection is read. **8 MiB** is the UI byte limit, not native CLI capacity. The closed `termivar-comparison-v1` parser profile bounds **depth 12**, **250,000 nodes**, **750,000 tokens**, **4,096 elements per array**, **32 object keys** and **1,024 UTF-16 code units per string**, plus native field-specific UTF-8 limits. UTF-8, duplicate keys, NaN/Infinity, wrong numeric types, safe integers, versions, fields and record-binding consistency are checked. Some larger valid CLI outputs may be rejected; no first-N view is silently substituted. The API parser default is unchanged. Termivar Web assessment import and policy preview import use their own closed profiles (`termivar-assessment-v1`, `sp-hbf-preview-v1`), described in their guides.

Raw JSON is not put in the global store or inventory DTOs. A closed immutable view model contains only permitted fields. Filename/private target/raw data are not written to titles, URLs, logs, audit, telemetry or persistent browser storage. There is no upload/network, extra-file lookup, URL/path/HTML/command execution, raw request/response or evidence opening, copy/export/print/PDF. Hidden values are omitted from DOM/attributes rather than concealed with CSS, and hidden free text is not a search oracle.

Permitted opt-in title/summary/metadata may contain HTTP content or secrets. Showing it does not sanitize, anonymize or encrypt it. Clear does not promise forensic erasure of OS/browser memory.

## Sources and example provenance

Local `ITherso/termivar` was reviewed read-only at `6a2639348c2366d0bf71b9a34e5484d40aa393a3`: [comparison.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison.rs), [reporting.md](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md), and the [example record](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/README.md).

The existing four-group synthetic CLI output was **copied unchanged**; no CLI/scanner was run this phase. **Example comparison — does not prove a security change at a real target.** Each group has one item; `changed` demonstrates an intentionally edited summary only. Reviewed/historical source commits, byte/SHA256 identity and limits are in the [provenance record](../src/features/termivarComparison/examples/README.md). It opens only after explicit selection and never merges with user imports.

Actual install/typecheck/build, chunk warning and limited manual observations are recorded separately in [Phase12 delivery](DELIVERY.tr.md). Tests/runners/coverage, CLI/scanner/runtime, live API/IdP/PostgreSQL, Windows/VM/admin, new policy/enforcement authority, PDF/export and deployment/push/release remain held. Historical results are not new security acceptance.
