# Offline Rust Source Reference Graph & Module Coverage Boundaries

**DEMONSTRATION ONLY — RUST SOURCE REFERENCES — NO MODULE CLOSURE OR BUILD AUTHORIZED**

Python 3.11+ standard-library tool. It reads fifteen explicitly bound Phase24/27/28 artifacts and the three explicitly allowlisted native entry files. A bounded lexer separates supported comments, literals and token-tree boundaries; a narrow classifier records static module/include/path observations and conditional uncertainty. Pure builders publish metadata only. No compiler, Cargo, rust-analyzer, macro expansion, environment lookup, module resolver or recursive source discovery runs.

The final usable delivery is in `outputs/phase29-rust-source-graph-corrected/`. The commands below record the completed corrective assembly and inspection; the invocation budget is closed and they must not be rerun under the existing authorization. They used the enclosing workspace containing `security-platform/` and `outputs/`, with the preserved read-only Termivar checkout root passed explicitly:

```powershell
python -I -B security-platform/tools/commercial_rust_source_graph/assemble_source_graph.py --scope security-platform/tools/commercial_rust_source_graph/examples/demo_source_graph_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase29-rust-source-graph-corrected
```

The inspector ran only after that assembly succeeded and its five actual files were manually reviewed:

```powershell
python -I -B security-platform/tools/commercial_rust_source_graph/inspect_source_graph.py --ledger outputs/phase29-rust-source-graph-corrected/source-reference-ledger.json --graph outputs/phase29-rust-source-graph-corrected/source-evidence-graph.json --coverage outputs/phase29-rust-source-graph-corrected/module-coverage-projection.json --summary outputs/phase29-rust-source-graph-corrected/source-graph-summary.md --manifest outputs/phase29-rust-source-graph-corrected/manifest.json --output outputs/phase29-rust-source-graph-corrected/inspection-summary.json
```

Output directories must be new. The first assembly exited 0 but retained a partial CLI analysis (82 external / 0 inline references overall); its five files remain separately preserved in `outputs/phase29-rust-source-graph/`. A concrete `if !` classifier correction was reviewed, then explicit human authorization allowed exactly two corrective calls: the assembly and inspector above. All three actual exits were 0; the corrected result is 95 external / 1 inline with three complete bounded scans, and inspection reports `content_consistent`. The human exception and all prior phase budgets are closed; no further call or automatic retry is authorized. This is not a test, build or lexical correctness acceptance.

Real commands, authorization, measured output identities and open gates are recorded in [DEMO_DELIVERY.tr.md](../../docs/commercial/operations/phase29/DEMO_DELIVERY.tr.md). No installation, tests, typecheck, build, native runtime or live activity is part of this phase. The new-only source ZIP requires the preserved original explicit inputs and checkout; it is not a native release. This final README path/counter update is documentation only; the twelve Python files and example scope retain their corrective-generation byte identities.

Source hashing and lexical inspection are separate evidence stages. Rust sources have a 512 KiB per-file and 1 MiB aggregate ceiling, read in chunks of at most 64 KiB. UTF-8 is strict, BOM and changing/aliased/unsafe files fail closed. Source bytes and temporary tokens remain bounded in process memory and are never emitted into JSON, Markdown, logs or the ZIP. Missing required demo sources stop assembly before lexical success. Portable path and same-API identity checks do not provide an atomic adversarial-filesystem snapshot.

Lexical failure produces explicit unresolved metadata with no guessed references from that file; budget overflow aborts. CRLF is one newline; UTF-8 byte offsets differ from Unicode character columns. The lexer line count includes a trailing empty line. Ordinary macro trees are opaque; `println!`, `json!`, `env!` and `concat!` are not source-include references by name alone. No source syntax absent from the selected files is fabricated to demonstrate support. Unsupported and hostile lexical cases remain acceptance gates.

`mod name;` records an external declaration without inventing `name.rs` or `name/mod.rs`. Inline modules remain separate. A supported literal path needs a reliable relative base and exact allowlist identity for a file binding; nested/conditional/unsupported contexts remain unresolved. File identity binding never means compiler module resolution or conditional activation. `resolved_file=false` keeps that distinction separate from observed-file binding records.

The preserved 111-row F catalog has no universal selected/excluded flag. Component references, global membership and ownership are distinct. Phase28's three proposals remain unapplied; no F record or component source list is added. All thirteen trust flags remain false, including module closure, source inventory update, ownership, dependency closure, build/runtime, producer/human/legal review and release/production authority.

The inspector reads only five new files and rederives closed metadata relationships. It neither imports the lexer/classifier nor reopens Rust or parent artifacts. `content_consistent` is not independent lexical correctness, Rust AST, source completeness, Git/producer attestation, ownership, build/runtime or release acceptance.

Documents: [contract](../../docs/commercial/operations/phase29/SOURCE_REFERENCE_CONTRACT.tr.md), [lexical limits](../../docs/commercial/operations/phase29/RUST_STATIC_REFERENCE_LIMITS.tr.md), [coverage](../../docs/commercial/operations/phase29/MODULE_COVERAGE.tr.md), [trust boundary](../../docs/commercial/operations/phase29/TRUST_BOUNDARY.tr.md).
