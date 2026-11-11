# Offline Entry-Point Coverage & Source-Scope Delta Workbench

**DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED**

Python 3.11+ standard-library tool. It binds existing Phase24/26/27 artifacts, reads explicitly selected Cargo `[lib]` / `[[bin]]` declarations, hashes only exact allowlisted entry files, compares them with the existing F catalog and produces unapplied repository-level inclusion proposals. No dependency installation, Cargo, network, source discovery or inventory write is involved.

Run from the enclosing delivery workspace, where `security-platform/` and `outputs/` already exist. The demo requires the preserved old artifacts and the actual read-only Termivar checkout. Pass its root explicitly; no absolute root is embedded in results. This new-only ZIP is source material with those prerequisites, not a self-contained native release.

```powershell
python -I -B security-platform/tools/commercial_entrypoint_coverage/assemble_coverage.py --scope security-platform/tools/commercial_entrypoint_coverage/examples/demo_coverage_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase28-entrypoint-coverage
```

Only after that command succeeds and its five files have been reviewed:

```powershell
python -I -B security-platform/tools/commercial_entrypoint_coverage/inspect_coverage.py --coverage outputs/phase28-entrypoint-coverage/entrypoint-coverage.json --delta outputs/phase28-entrypoint-coverage/source-scope-delta.json --variants outputs/phase28-entrypoint-coverage/variant-entrypoint-projection.json --summary outputs/phase28-entrypoint-coverage/entrypoint-summary.md --manifest outputs/phase28-entrypoint-coverage/manifest.json --output outputs/phase28-entrypoint-coverage/inspection-summary.json
```

The output directory must be new. No overwrite, automatic retry or third Phase28 product call is authorized. The two commands above document the real delivery invocation budget; they are not an invitation to rerun completed phases. Actual execution records are in [DEMO_DELIVERY.tr.md](../../docs/commercial/operations/phase28/DEMO_DELIVERY.tr.md).

Scope JSON lists all fifteen artifact paths and their exact identities, four manifests and three explicit file/target bindings. Expected SHA256 values constrain fresh reads; the implementation measures actual bytes. Strict UTF-8, duplicate-key/number/type/size/reference validation and existing closed parent contracts are reused. Existing payloads are validated internally, never re-published as a new dependency graph. Input paths in metadata are not followed automatically.

Cargo manifests have a 256 KiB per-file ceiling; entry files have a separate 512 KiB ceiling, 1 MiB aggregate and 64 KiB maximum read chunks. Total input budget is 12 MiB. Scope and manifests are limited to 128 KiB, JSON to 2 MiB and Markdown to 256 KiB. See the [contract](../../docs/commercial/operations/phase28/ENTRYPOINT_CONTRACT.tr.md) for record bounds.

The tool retains metadata only. It never decodes or parses Rust source, imports source modules, copies raw entry bodies into reports/ZIPs, adds F records or applies proposals. Unsafe identity/type/hash changes fail closed; a missing file is distinct from an unallowlisted or unestablished target. Parent-directory checks and same-API ctime comparisons preserve the Windows identity fix. These portable checks do not provide an atomic adversarial-filesystem snapshot; hostile paths, races and crash handling remain NOT_RUN acceptance gates.

Global F membership, component F references and dependency-manifest context are distinct. Phase24 has no universal selected/excluded flag. A local file hash is neither pinned Git attestation nor producer proof. Manifest ownership stays at the Phase27 evidence level; target name and package name are not product component ownership. Variants reference global proposals without multiplying their count. No build, runtime, legal, redistribution, release or production approval is derived.

Technical documents: [coverage](../../docs/commercial/operations/phase28/SOURCE_COVERAGE.tr.md), [unapplied delta](../../docs/commercial/operations/phase28/SCOPE_DELTA.tr.md), [trust boundary and NOT_RUN gates](../../docs/commercial/operations/phase28/TRUST_BOUNDARY.tr.md).
