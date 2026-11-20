# Policy impact review workbench

**Policy previews** reads a packet-policy preview previously produced by the existing `security-policy` CLI. The browser does not evaluate policies, load HBF source or know a device's active policy. It adds no evaluator, device connection or apply/send authority. [Türkçe kullanım](POLICY_REVIEW_WORKBENCH.tr.md).

## Open and inspect a file

1. Open **Policy previews**, then **Open policy preview file** and select one local JSON output. Use the CLI's `--output` file; its base/candidate `--input` envelope is not a supported output.
2. Read the contract, result status, scope and separate identities. `ok` means a preview was produced for the supplied scenarios. A `blocked` outcome contains blockers and must not be presented as a successful decision.
3. Search and filter only the loaded scenarios. Select one to inspect base/candidate decisions, the first matched policy and the available bounded explanation. Equal decisions do not establish equal protection.
4. Detailed source/destination information starts hidden. **Show details** applies to this import only and resets for a new file or clear. Expand a fingerprint explicitly when its full value is needed.
5. Select another file or clear the data from memory. An invalid replacement must not leave the previous success looking like the new file's result.

Normal page navigation and TR/EN changes preserve a valid import. Tenant, example/API source, example scenario or connection-session changes, and existing access cleanup, conservatively clear sensitive imported data. Reload does not restore it. Device comparison, report drafts and device-detail navigation are separate; no policy is added to a report automatically.

## Supported existing contract

The supported artefact is the direct **PreviewOutcome** JSON with `contract_version="sp-hbf-preview/v1"`. This output has no root `schema_version`; the CLI input envelope does. Both successful and valid blocked outcomes are supported. The file must be valid UTF-8, no larger than **512 KiB**, and satisfy the supported closed field/type/number/string bounds. Duplicate keys, invalid numbers, unsupported versions and missing/malformed required identities are errors. Nullable identities permitted by a valid blocked outcome are not replaced with invented success evidence.

The `strictJson` parser uses the closed `sp-hbf-preview-v1` profile: depth **12**, **50,000** nodes, **2,048 UTF-16 code units** per string (a 1,024-character CLI text field can need two units per character), **100** elements per array, **32** keys per object and **160,000** tokens. Narrower field-specific limits also apply (32 scenarios, 64 trace rows per evaluation, 4 reasons per row). The profile is sized from the CLI maxima of 32 scenarios x 2 evaluations x 64 trace rows (about 42,000 nodes and 128,000 tokens), so such outputs within the 512 KiB browser limit are not rejected by the parsing budgets. Larger files are rejected as too large; data is never silently truncated. The CLI's **8 MiB** output limit is not the browser import limit.

`check-preconditions` and `validate-rollout` are separate CLI output types and are not merged into this preview. PreviewOutcome does not carry controller revision evidence, endpoint revision evidence, a separate CAS result or rollout validation. These fields are **Not present in this result**. The workbench does not invent `consistent_fixture_only`, `precondition_evidence_missing` or `would_pause` outcomes, nor obtain missing information from another file, backend or evaluator.

A successful preview may contain up to 32 scenarios and up to 64 trace entries per evaluation, with the total and completeness flag recorded separately. A bounded trace is not a complete proof of the whole policy. Missing explicit profile/time or required country context can produce `insufficient_context`; the UI does not fill in a definitive decision.

## Identities and decisions

| Field | Meaning |
|---|---|
| `legacy_base_version` | Existing HBF base snapshot hash; compatibility information. |
| `base_fingerprint` | Normalized base bundle and versioned representation. |
| `candidate_fingerprint` | Normalized candidate bundle and versioned representation. |
| `adapter_fingerprint` | Source manifest, adapter/evaluator contract and runtime identity. |
| `preview_fingerprint` | Identity binding base/candidate/adapter, explicit scenarios and normalized results. |

These identities are not interchangeable. A shortened fingerprint is not a unique identity or security proof. Shape validation does not recompute the content hash, verify a signature or attest to its producer. An equal legacy hash need not imply equal behavior: the same equal-prefix network in different zones can hide an order-dependent legacy resolver decision. The existing CLI blocks that ambiguity; the workbench does not repair or reevaluate legacy behavior. See the [source policy contract](../../docs/POLICY_CONTRACT_V1.tr.md).

`ALLOW→DENY` describes a decision change only for the supplied scenario. `DENY→ALLOW` does not mean safer, and ALLOW does not prove a real connection succeeded. DENY is not automatically correct, fewer DENYs are not automatically better, and equal decisions do not prove equal protection. `DENY_TEMP` creates no timer/block; NAT is policy intent, not an applied packet change. Missing policy names, conditions or explanations are not guessed. There is no score, risk ranking or automatic fix.

The fixed guards remain `authorization=not_evaluated`, `execution_authorized=false`, `verification=not_performed`, `scope=packet_policy_preview_only`. Native Windows application rules, whitelists, connection state, IP/domain lists, temporary blocks, the NAT table and driver behavior cannot be inferred from this preview. The result is never promoted to **Ready to deploy**, **Applied**, **Verified** or **Safe**.

## Memory and sensitive information

The File API reads only the single file explicitly selected by the user. JSON is not executed as code, HTML, modules or commands; paths and URLs in it are not followed. There is no upload, API request, persistent browser storage, audit/telemetry, raw console logging, copy/export facility or new data collection. A closed immutable UI model is made from validated fields; the raw artefact is not placed in the global store. The filename is not automatically put in the page title or URL.

Hidden details are omitted from rendered DOM text and attributes rather than concealed with CSS. Clear removes the model and derived details. This local presentation boundary does not promise encryption, anonymity or forensic erasure of browser/OS memory. File contents do not establish authorization, approval, freshness or live device state.

## Synthetic outputs from the real CLI

**Example policy preview — not a real device assessment.** The [generation record](../src/features/policyReview/examples/README.md) includes two synthetic inputs and the two outputs produced without modifying the existing CLI. Open `preview-output.json` or `preview-missing-context-output.json`; the input files are for the CLI. The successful example has one `ALLOW→DENY` and one `ALLOW→ALLOW` scenario. The blocked example reports `insufficient_context`. An example never silently replaces an invalid user file or merges with device data.

The CLI is responsible for using the existing evaluator from an explicitly selected trusted local HBF source directory. The workbench only displays its precomputed output. CLI exit `0` means the file was written, including a blocked output; it is not application or security acceptance. Generating these examples is ordinary offline CLI use, not a software-test run.

Actual typecheck/build and manual product observations are recorded separately in [DELIVERY.tr.md](DELIVERY.tr.md). Tests/runners/coverage, live API/IdP/PostgreSQL, real device/Windows acceptance, native enforcement, print/PDF, push/release and deployment remain held. Historical test counts are not new workbench acceptance; real policy revision/lineage authority and Windows gates remain unchanged.
