# Offline Candidate Evidence Revalidation & Staleness Guard

**DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED**

Python 3.11+ standard-library tool. It binds five real Phase30 artifacts and the explicit Phase30 source ZIP byte identity, then re-observes only a selected subset of previously authorized candidate files. Historical metadata stays immutable; current observations and comparison results are separate. No new candidate, allowlist expansion, Rust decoding/lexing, module discovery, compiler, Cargo, package manager or network is involved.

Run from the enclosing workspace containing `security-platform/` and `outputs/`, with the preserved read-only Termivar root supplied explicitly. The new-only source ZIP requires the old explicit artifacts, source ZIP and checkout; it is not a self-contained native release.

```powershell
python -I -B security-platform/tools/commercial_candidate_revalidation/assemble_revalidation.py --scope security-platform/tools/commercial_candidate_revalidation/examples/demo_revalidation_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase31-candidate-revalidation
```

Only after successful assembly and manual review of its four actual files:

```powershell
python -I -B security-platform/tools/commercial_candidate_revalidation/inspect_revalidation.py --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json --summary outputs/phase31-candidate-revalidation/revalidation-summary.md --manifest outputs/phase31-candidate-revalidation/manifest.json --output outputs/phase31-candidate-revalidation/inspection-summary.json
```

These describe at most two Phase31 delivery calls; source preparation does not claim either has run. Actual commands, exits and measured identities belong in [DEMO_DELIVERY.tr.md](../../docs/commercial/operations/phase31/DEMO_DELIVERY.tr.md). Output must be new. An unsuccessful call is consumed; no assembly retry, automatic repeat or third call is authorized. Previous phase budgets and the closed Phase24/29 exceptions remain closed.

Three hash roles remain explicit: baseline SHA256 is historical, current expected SHA256 is an independent nullable new-scope expectation, and current observed SHA256 is freshly measured. The new reader checks its current expectation without changing the baseline or passing None to bypass the old mandatory-hash reader. Expectation mismatch, unsafe root/path/type/identity, permission, race or byte-limit failure cannot become normal changed/missing success.

The seven comparisons separate equal bytes, changed bytes, disappeared, appeared, equal absence, not revalidated and inconclusive. Old inode/handle metadata was not recorded; physical identity is not comparable even when bytes match. Current physical identifiers are not exported. A same-API Windows ctime guard protects each read, not identity across observations.

Only equal bytes allow a small current candidate-byte projection; equal absence allows only current absence metadata. Every other state blocks reuse with no historical-success fallback. This guard is used only by this new tool; old consumers are unchanged. Reference context remains un-revalidated, and the observation is instantaneous with no TTL, polling or watcher. Old F membership, lexical conditions, ownership and release flags are not refreshed by a current candidate hash.

One authorized logical file may serve several old candidate/reference bindings through a single read. An unrevalidated/changed candidate cannot be masked by another unchanged candidate. CAND0004 remains unqueried and blocked; 92 references outside the old candidate scope remain unknown, not healthy/unaffected. No source mutation or changed-file fixture is created.

Limits: scope 128 KiB; metadata total 8 MiB including source ZIP; old JSON 2 MiB, summary 256 KiB and manifest 128 KiB; source ZIP 2 MiB, binary hash only with no archive parsing/extraction. Current candidate files allow 512 KiB each/4 MiB total/64 KiB chunks. New JSON 2 MiB, Markdown 256 KiB and manifest 128 KiB. Strict closed JSON and source-identity/path/alias/stability guards apply. Rust bodies never enter reports or ZIPs.

The manifest binds three actual payloads, excluding itself and the future inspector output. The inspector reads four new files only and rederives metadata comparison/reuse/reference impact plus exact summary and byte identities. It does not reopen old artifacts, ZIP, candidate files or lexical sources. `content_consistent` is not independent filesystem freshness, source authenticity, Rust/module correctness or release acceptance.

All fifteen trust flags remain false and demo remains true. The declared Phase24 platform source pin remains distinct from the frozen runtime pin; neither is attestation. Changed/disappeared/appeared, shared-file, hostile/race/limit/crash/determinism and real compiler/build/runtime/legal gates remain NOT_RUN unless actually observed. See [contract](../../docs/commercial/operations/phase31/REVALIDATION_CONTRACT.tr.md), [comparison](../../docs/commercial/operations/phase31/OBSERVATION_COMPARISON.tr.md), [reuse boundary](../../docs/commercial/operations/phase31/EVIDENCE_REUSE_BOUNDARY.tr.md) and [trust/privacy](../../docs/commercial/operations/phase31/TRUST_AND_PRIVACY.tr.md).
