# Offline Candidate Evidence Revalidation & Staleness Guard

**DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED**

Python 3.11+ standard-library tool. It binds five real Phase30 artifacts and the explicit Phase30 source ZIP byte identity, then re-observes only a selected subset of previously authorized candidate files. Historical metadata stays immutable; current observations and comparison results are separate. No new candidate, allowlist expansion, Rust decoding/lexing, module discovery, compiler, Cargo, package manager or network is involved.

The final local delivery is in `outputs/phase31-candidate-revalidation/`. These are the completed historical delivery commands, not permission to rerun them. They used the enclosing workspace containing `security-platform/` and `outputs/`, with the preserved read-only Termivar root supplied explicitly. The new-only source ZIP requires the old explicit artifacts, source ZIP and checkout; it is not a self-contained native release.

```powershell
python -I -B security-platform/tools/commercial_candidate_revalidation/assemble_revalidation.py --scope security-platform/tools/commercial_candidate_revalidation/examples/demo_revalidation_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase31-candidate-revalidation
```

The inspector ran only after assembly exited 0 and its four actual files had been manually reviewed:

```powershell
python -I -B security-platform/tools/commercial_candidate_revalidation/inspect_revalidation.py --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json --summary outputs/phase31-candidate-revalidation/revalidation-summary.md --manifest outputs/phase31-candidate-revalidation/manifest.json --output outputs/phase31-candidate-revalidation/inspection-summary.json
```

Both actual exits were 0 and inspection reports `content_consistent`. Phase31 has consumed 2/2 calls; its budget is closed with no further call, assembly retry, automatic repeat or third invocation authorized. Previous phase budgets and the Phase24/29 exceptions remain closed. Outputs require new directories, never overwrite. Exact commands, measured identities and open gates are recorded in [DEMO_DELIVERY.tr.md](../../docs/commercial/operations/phase31/DEMO_DELIVERY.tr.md).

All four previously authorized file paths were selected. Fresh reads produced three `bytes_reobserved_equal` comparisons (45,969 actual bytes) and one `absence_reobserved`. Four file-level metadata projections contain three current byte records and one current absence record; no historical fallback is used. Of five old candidates, four receive those limited projections and CAND0004 remains unqueried/blocked with a null projection. The scanner reference remains blocked because its unread CAND0004 alternative is not masked by equal CAND0003; two other references are reobserved with context still unverified, and 92 references remain outside scope/unknown. No natural change was observed or manufactured.

The generation-source commit was `f211a108d094c59c43c556c0677bdfeffd936532`, tree `37b7f7a76c1431e3d7f1d361b1ecab76a63b01f7`. The source package was read as 129,296 binary bytes, SHA256 `aab4d89f3fbf95992675ce08b095468680ba29fb07e2b85dea7ed1dbd3742485`; it was not extracted or parsed. Final ZIP identity and documentation/source manifest bindings are measured in `outputs/phase31-candidate-revalidation-delivery-manifest.json` after packaging, not invented here. Final README/DEMO edits are documentation only; no old source or runtime is updated.

Three hash roles remain explicit: baseline SHA256 is historical, current expected SHA256 is an independent nullable new-scope expectation, and current observed SHA256 is freshly measured. The new reader checks its current expectation without changing the baseline or passing None to bypass the old mandatory-hash reader. Expectation mismatch, unsafe root/path/type/identity, permission, race or byte-limit failure cannot become normal changed/missing success.

The seven comparisons separate equal bytes, changed bytes, disappeared, appeared, equal absence, not revalidated and inconclusive. Old inode/handle metadata was not recorded; physical identity is not comparable even when bytes match. Current physical identifiers are not exported. A same-API Windows ctime guard protects each read, not identity across observations.

Only equal bytes allow a small current candidate-byte projection; equal absence allows only current absence metadata. Every other state blocks reuse with no historical-success fallback. This guard is used only by this new tool; old consumers are unchanged. Reference context remains un-revalidated, and the observation is instantaneous with no TTL, polling or watcher. Old F membership, lexical conditions, ownership and release flags are not refreshed by a current candidate hash.

One authorized logical file may serve several old candidate/reference bindings through a single read. An unrevalidated/changed candidate cannot be masked by another unchanged candidate. CAND0004 remains unqueried and blocked; 92 references outside the old candidate scope remain unknown, not healthy/unaffected. No source mutation or changed-file fixture is created.

Limits: scope 128 KiB; metadata total 8 MiB including source ZIP; old JSON 2 MiB, summary 256 KiB and manifest 128 KiB; source ZIP 2 MiB, binary hash only with no archive parsing/extraction. Current candidate files allow 512 KiB each/4 MiB total/64 KiB chunks. New JSON 2 MiB, Markdown 256 KiB and manifest 128 KiB. Strict closed JSON and source-identity/path/alias/stability guards apply. Rust bodies never enter reports or ZIPs.

The manifest binds three actual payloads, excluding itself and the future inspector output. The inspector reads four new files only and rederives metadata comparison/reuse/reference impact plus exact summary and byte identities. It does not reopen old artifacts, ZIP, candidate files or lexical sources. `content_consistent` is not independent filesystem freshness, source authenticity, Rust/module correctness or release acceptance.

All fifteen trust flags remain false and demo remains true. The declared Phase24 platform source pin remains distinct from the frozen runtime pin; neither is attestation. Historical physical identity remains `not_recorded`, cross-observation identity `not_comparable`, and reference context un-revalidated. Actual CAND0004 blocking is not acceptance of all stale-evidence branches: changed/disappeared/appeared, file-level not-revalidated/inconclusive, expectation mismatch, shared-file, hostile/race/limit/crash/determinism and real compiler/build/runtime/legal gates remain NOT_RUN. See [contract](../../docs/commercial/operations/phase31/REVALIDATION_CONTRACT.tr.md), [comparison](../../docs/commercial/operations/phase31/OBSERVATION_COMPARISON.tr.md), [reuse boundary](../../docs/commercial/operations/phase31/EVIDENCE_REUSE_BOUNDARY.tr.md) and [trust/privacy](../../docs/commercial/operations/phase31/TRUST_AND_PRIVACY.tr.md).
