# Existing synthetic comparison / Mevcut sentetik karşılaştırma

`comparison-example.json` is an **exact-byte copy** of the already existing local Termivar document-processing example. It is not a new comparison or scan generated in this phase. Only the precomputed comparison JSON was copied; no assessment pair or HTML was imported, combined or executed.

`comparison-example.json`, önceden mevcut yerel Termivar belge işleme örneğinin **birebir byte kopyasıdır**. Bu tur yeni karşılaştırma veya scan üretilmedi. Yalnız hazır karşılaştırma JSON'u kopyalandı; iki assessment dosyası veya HTML içe alınmadı, birleştirilmedi, çalıştırılmadı.

| Copied file | Source path | Bytes | SHA256 |
|---|---|---:|---|
| `comparison-example.json` | `docs/examples/report-compare/comparison.json` | 5674 | `291f5e7b407a247cb786119a249fe6f3cb9f5526e6700605c4a0008bee91a1d0` |

Original and copied bytes were measured and matched before Phase12 packaging. The JSON was not reformatted. The source was a local, read-only checkout of the `ITherso/termivar` repository at the reviewed commit below; its machine-specific location is intentionally not recorded.

Reviewed checkout commit: `6a2639348c2366d0bf71b9a34e5484d40aa393a3`, origin `https://github.com/ITherso/termivar.git`. Read-only references were `crates/termivar-scanner/src/reporting/comparison.rs`, `docs/reporting.md` and the example's `README.md`, `comparison.json`, `provenance.json`.

The existing [source example record](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/README.md) and [provenance](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/provenance.json) attribute its historical generation to Termivar `0.10.0-alpha.2`, source commit `664d385bd455a4fc5002b98a2103078cfba1be29` (base `e19a2729e14d3cc142c94d07c0f6955d55d828dd`) and binary SHA256 `6690463ae8459245d7ffad703df0ede266a01f4c3c107bb6f51dd3ef6fe344da`. Those are recorded historical identities, not a binary executed or independently reproduced in this phase.

The fixture contains one record in each actual group: `only_in_after`, `only_in_before`, `changed`, `unchanged`. Its before/after metadata each declares three source items. The changed record differs in `redacted_summary`; the after-only identity and edited descriptions are deliberately synthetic. The example alleges no target change, vulnerability, remediation or equal coverage. Its two `optional_audits` objects are empty and it has no optional root comparison sections.

The source digests declared in the comparison are `33f709237ffea142d892891d818815251c1cb35d888abe155f7175e15d7d481f` (before) and `5ea44cfd6dbab132aa96e62813c32c12e35f0bf32c09b43a102a16e9ff7bbe64` (after). They identify the historical supplied input bytes; this UI does not read those inputs, recalculate the comparison or authenticate a producer or target.

The example must be explicitly selected and labelled **“Example comparison — does not prove a security change at a real target.”** It never silently replaces an invalid user file or mixes with an assessment import. A source hash or this file-integrity hash is not a signature, scope proof or verification of a fix. No CLI, scanner, runtime, fixture server or test runner was invoked for this copy.
