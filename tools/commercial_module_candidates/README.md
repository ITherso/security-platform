# Offline Rust Module Candidate Evidence & Path-Ambiguity Triage

**DEMONSTRATION ONLY — RUST MODULE CANDIDATE EVIDENCE — NO COMPILER RESOLUTION VERIFIED**

Python 3.11+ standard-library tool. It consumes the corrected Phase29 reference metadata and the real Phase24 inventory contracts, then hashes only explicitly allowlisted candidate files. Candidate paths are explicit operator declarations, not inferred Rust module resolution. The candidate Rust bodies are neither decoded nor parsed; no compiler, Cargo, lexer, recursive discovery, package manager or network runs.

Use the enclosing workspace containing `security-platform/` and `outputs/`; pass the preserved read-only Termivar root explicitly. The new-only source ZIP requires those old explicit artifacts and the original checkout. It is not a self-contained native release.

```powershell
python -I -B security-platform/tools/commercial_module_candidates/assemble_candidates.py --scope security-platform/tools/commercial_module_candidates/examples/demo_candidate_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase30-module-candidates
```

Only after assembly succeeds and its five actual files have been manually reviewed:

```powershell
python -I -B security-platform/tools/commercial_module_candidates/inspect_candidates.py --evidence outputs/phase30-module-candidates/module-candidate-evidence.json --triage outputs/phase30-module-candidates/candidate-triage.json --coverage outputs/phase30-module-candidates/candidate-coverage.json --summary outputs/phase30-module-candidates/candidate-summary.md --manifest outputs/phase30-module-candidates/manifest.json --output outputs/phase30-module-candidates/inspection-summary.json
```

These document the maximum two Phase30 delivery calls; the source preparation itself does not claim that either has run. Actual exits and measured artifacts belong in [DEMO_DELIVERY.tr.md](../../docs/commercial/operations/phase30/DEMO_DELIVERY.tr.md). Output must be a new directory. An unsuccessful assembly does not authorize a retry or inspector. No automatic repeat or third call is authorized; all previous phase budgets, including the closed Phase24 and Phase29 human exceptions, remain closed.

Scope separates candidate declarations from read authorization. An unallowlisted candidate is never checked with exists/stat/open; its presence, size and hash remain unknown. Missing means a safely observed absence at an authorized path, never permission denial or source-identity failure. Unsafe path/type/hash/race/alias conditions fail closed. Same logical root/pin/path can support several reference bindings through one file observation; conflicting read identities are rejected. Unique observed files, candidate relations and external references use separate counts.

All corrected Phase29 external references remain traceable. Unselected references are `not_examined`; they are not missing modules. One present candidate remains unresolved; multiple candidates or unexamined alternatives are not silently reduced to a successful choice. `alternatives_exhaustive=false` and `resolved_file=false` remain visible. Conditions are retained but not evaluated. An operator path does not establish human review, static context proof or compiler selection.

Metadata is bounded: scope 128 KiB; Phase29 JSON 1 MiB each, summary 256 KiB and manifest 128 KiB; Phase24 JSON 2 MiB and manifest 128 KiB; total metadata 8 MiB. Candidate hashing allows 512 KiB per file, 4 MiB aggregate and at most 64 KiB per chunk. New JSON is at most 2 MiB, Markdown 256 KiB and manifest 128 KiB. Strict versions/types/closed fields/duplicate-key/invalid-number checks and source binding guards apply. Record limits are in the [contract](../../docs/commercial/operations/phase30/CANDIDATE_CONTRACT.tr.md).

F catalog membership and observed byte/hash equality are separate from component F references and ownership. The 111 global / 107 component-reference boundary gains no universal selected/excluded flag. Phase28 proposals remain unapplied; no F or source list is written. Candidate presence does not close module/dependency closure, license review, producer/human review, build/runtime, redistribution, release or production gates. All inherited false trust flags and `compiler_resolution_verified=false` are retained.

The inspector reads only five new metadata files, rederives pure relationships and checks exact Markdown plus the four-payload manifest. It neither reopens candidate/old source files nor reexecutes the Phase29 lexer. `content_consistent` is not independent source truth, compiler/AST/module resolution, source completeness, producer attestation or release acceptance. Portable filesystem guards are not hostile/race acceptance; those and all real compiler/build/runtime/legal gates remain NOT_RUN.

Documents: [path boundaries](../../docs/commercial/operations/phase30/PATH_AND_MODULE_BOUNDARIES.tr.md), [triage and counts](../../docs/commercial/operations/phase30/SOURCE_TRIAGE.tr.md), [trust and privacy](../../docs/commercial/operations/phase30/TRUST_AND_PRIVACY.tr.md), [actual delivery](../../docs/commercial/operations/phase30/DEMO_DELIVERY.tr.md).
