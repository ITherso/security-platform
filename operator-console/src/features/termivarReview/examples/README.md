# Termivar review examples / Termivar inceleme örnekleri

The two built-in examples are **hand-authored synthetic documents**, not CLI output or scan results. This phase did not run Termivar, a scanner, a fixture server, a test or a report generator. The optional bundle pair is an exact copy of an already existing benign native example and is identified separately below. No HTML is included or read.

Yerleşik iki örnek **elle yazılmış sentetik belgedir**; CLI/scanner çıktısı değildir. Bu tur Termivar, scanner, fixture sunucusu, test veya rapor üretici çalıştırılmadı. İsteğe bağlı bundle çifti, önceden var olan benign yerel örneğin birebir kopyasıdır; aşağıda ayrı kaynaklandırılır. HTML dahil edilmedi veya okunmadı.

## Hand-authored examples / Elle yazılmış örnekler

| File | Meaning | Bytes | SHA256 |
|---|---|---:|---|
| `assessment-example.json` | Complete v1 shape; one informational/observation and one needs_review/differential item | 2377 | `1ef1eed88ad97d9e21e7df4e989db2eee65b3d5a1044f5c4208688f366096537` |
| `incomplete-example.json` | Separate exact-origin `web-assessment/v2` diagnostic shape, items unavailable | 3465 | `85881c1d3883bb719cd05e7fbd63f564188371ddab58be94eb7e56c9e84d4f0a` |

These were written directly from the reviewed source contract. The source checkout was `ITherso/termivar` commit `6a2639348c2366d0bf71b9a34e5484d40aa393a3`, at:

`C:/Users/galat/Documents/Codex/2026-07-31/github-plugin-github-openai-curated-remote/termivar`

Reviewed source: `docs/reporting.md`, `crates/termivar-cli/src/assessment_scan.rs`, `crates/termivar-cli/src/report_bundle.rs`, `crates/termivar-scanner/src/reporting/comparison/import.rs` and `crates/termivar-scanner/src/web_runtime/scan_profile.rs`.

The complete example's capability identifiers, descriptions, recommendation identifiers, opaque fingerprints and evidence references are synthetic placeholders. Both severities are unassigned; `confidence_ppm=0` is explicit example data. The differential item uses the existing direct-one-reference/no-verifier linkage permitted by the importer; it is not a newly implemented capability or proof that a native scan produced it.

The incomplete example retains one pending authorized-root subject and no forms, with no subject execution or requests. Its explicit zero wall-time budget is paired with native `wall_time_limit` / `subject_execution_incomplete` reason codes. The 24 retained URL bytes represent the synthetic canonical root `https://example.invalid/`; the adapter validates then discards target and subject internals and never opens the origin. Other limits use the source's built-in values. Zero usage values are authored fixture data, not measurements or defaults for missing data. An unavailable item projection is not a completed empty assessment. Neither file supplies authenticated producer identity, start/end timestamps or a verified-remediation claim.

## Existing benign bundle pair / Mevcut benign bundle çifti

| Copied file | Exact native source | Bytes | SHA256 |
|---|---|---:|---|
| `bundle-assessment.json` | `docs/examples/report-bundle/assessment-001/assessment.json` | 3907 | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `bundle-manifest.json` | `docs/examples/report-bundle/assessment-001/manifest.json` | 711 | `c77ce74508e8efaff7ebf1b0203331b4295d468c726e4acd7bad709eb85813df` |

Original and copied bytes were hashed and matched before this phase's packaging. They were not reformatted. The native [generation record at the reviewed commit](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-bundle/README.md) attributes the existing bundle to a historical `0.10.0-alpha.2` development execution against a repository-owned numeric-loopback fixture. It declares one subject and four informational items. That record is historical provenance, not a scan executed or independently repeated in this phase.

The manifest also declares `assessment.html` (8000 bytes, SHA256 `a43070ee91860782a1eb47cd081b5fe628423a847bcc172e1a039cb6055cf1c1`). That HTML is **not included, selected, read, rendered or verified** by this workspace. Its name and hash are merely unverified manifest metadata. The copied assessment can be selected as a local JSON file and the copied manifest selected separately to inspect only the selected JSON's exact byte length, SHA256 and summary binding.

`selected_json_matches` is a **partial JSON-entry match**, never full bundle verification, producer authentication, authorization, finding accuracy or remediation proof. A different selected JSON may mismatch this manifest without being malicious. Manifest names are fixed schema values, not paths to follow. No additional file is searched for. Local copy names intentionally differ from the manifest's fixed `assessment.json` entry; the comparison binds the explicitly selected bytes, not the displayed filename.

The existing HBF summary importer and the platform's numeric `latest_report` DTO remain separate. These review examples are not sent to them or associated with a device, tenant, report draft, device comparison or policy preview automatically. File-integrity hashes here are not signatures or source attestations.
