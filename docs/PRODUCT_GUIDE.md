# Security Platform — product guide

Start here to evaluate, install and demonstrate Security Platform 0.1.0. This guide covers what is implemented today, how to run it, and what is not ready yet. The detailed Turkish reference documents are listed at the end. Türkçe: [PRODUCT_GUIDE.tr.md](PRODUCT_GUIDE.tr.md).

## What the product is

Security Platform is a set of security-operations components. Every result keeps its evidence level visible:

- a device report stays "reported by the device";
- a hash match stays "consistent bytes";
- nothing becomes "verified", "approved" or "authorized" just because it is displayed.

| Component | What it does today | Demo status |
| --- | --- | --- |
| **Operator console** (`operator-console/`) | Read-only web console in Turkish and English, opening on clearly labelled sample data. It covers the device inventory and comparison, a status report draft, policy impact review, and Termivar assessment and comparison review. Local JSON files are read in the browser only. | Ready when a built console is available ([section 3](#3-operator-console-sample-data)). |
| **Offline policy impact preview** (`security-policy`) | Compares a base and a candidate firewall policy over explicit scenarios, using the local HostBasedFirewall evaluator source. It also checks fixture CAS preconditions and simulates a rollout that cannot be executed. | Ready, offline. |
| **Offline Termivar analyst toolchain** (`tools/commercial_*`, phases 16–44) | Takes a Termivar assessment through intake to an analyst review packet, a self-contained HTML review desk and a client handoff draft. Later phases add case bundles, a portfolio, scope and traceability, composition, license and dependency evidence, a guarded reference capsule, and a minimal task capsule that can be exchanged and reconciled. | Reproducible with one command ([section 5](#5-termivar-offline-analyst-chain)). |
| **Inventory API** (`security-platform` service) | FastAPI and PostgreSQL. It stores tenant memberships, one-time device enrollments, device credentials and the last product status each device reports. Operators sign in with RS256 RFC 9068 access tokens. | Needs PostgreSQL, an identity provider and TLS ([section 6](#6-inventory-api-advanced)). |
| **Device sender** (`security-snapshot`) | Sends an exported HostBasedFirewall ecosystem summary once, or rotates the device credential when explicitly asked. | Needs the inventory API. |

The product does **not**:

- scan targets;
- push or apply firewall policy;
- run remote commands;
- contain an antivirus engine;
- enroll devices automatically;
- verify that a device's report is true.

HostBasedFirewall and Termivar are separate products. This repository reads their outputs or source code; it does not ship them.

## 1. Install

You need Python 3.12 or newer (verified on Windows x64 with Python 3.14), network access for the one-time `pip install`, and `git` on `PATH` for the chain runner.

Optional:

- Node 24 and pnpm 11 to build the console;
- PostgreSQL 16 or newer for the inventory API.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -c requirements-lock.txt -e '.[test]'
./.venv/Scripts/python.exe -m pip check
```

On Linux or macOS, use `.venv/bin/python`. Run all commands from the repository root with the venv interpreter.

## 2. One-command offline demo

```powershell
python -B scripts/run_demo.py
```

The demo runs the real command-line tools on the committed example inputs and writes the results to a new `demo-output/run-<UTC time>/` directory (git-ignored). Nothing is simulated.

`DEMO_SUMMARY.md` lists every step as one of:

- `PASSED`;
- `FAILED`;
- `NOT_RUN`: an external input was not supplied;
- `READY`: the console can be started.

The analyst-chain workspace is created in the system temporary directory, because the chain runner does not accept a workspace inside the repository. It holds a copy of the repository and all phase outputs. Its path is printed and recorded in the summary. It is kept for inspection, so delete it when you no longer need it. If you pass `--output-dir` outside the repository, the workspace is created there instead.

Optional inputs:

| Option | Enables |
| --- | --- |
| `--hbf-root <HostBasedFirewall source dir>` | Policy impact preview with the real evaluator |
| `--termivar-root <Termivar checkout at 6a2639348c2366d0bf71b9a34e5484d40aa393a3>` | Analyst chain phases 20–30 |
| `--phase30-delivery-zip <Termivar-Offline-Module-Candidates-phase30-2026-11-12.zip>` | Phases 31–44, together with `--termivar-root` |

Exit code 0 means no step failed.

Measured on 2026-11-20 with all three options supplied:

- the three policy steps passed;
- 29 phases of the analyst chain regenerated 168 of 168 recorded files, byte-identical, in 31 seconds;
- the console step was `NOT_RUN`, because this checkout has no built console.

A policy result such as `would_pause` or `precondition_evidence_missing` is the intended outcome for the example data, not an error.

## 3. Operator console (sample data)

The console needs a built `operator-console/dist/`. The build is not stored in git. Use the packaged console build, or build it with Node and pnpm as described in [operator-console/README.md](../operator-console/README.md).

```powershell
python -B operator-console/serve.py --port 8787
```

Open `http://127.0.0.1:8787/`. Stop with `Ctrl+C`.

The preview server:

- binds to loopback only and refuses a port that is already in use;
- serves only the files listed in the build manifest;
- sends a strict Content-Security-Policy.

Suggested 10-minute walkthrough:

1. **Product Hub**: product catalogue and stated limits.
2. **Devices**: open a device and read the separate registration, receipt and product-claim sections. Add it to the **Status report** and open the preview.
3. **Comparison**: open two device details and compare them.
4. **Policy previews**: load the built-in example, or a `policy-preview.json` produced in [section 4](#4-policy-impact-preview).
5. **Termivar assessments**: load the completed and incomplete examples. On the **Report comparison** tab, load the comparison example.
6. Switch to English with **Dil / Language**.

The console never contacts a device or a scanner. Live API mode needs the inventory API on the same HTTPS origin and an externally issued operator token. It has not been accepted against a real identity provider.

## 4. Policy impact preview

```powershell
New-Item -ItemType Directory -Force demo-output | Out-Null   # the output directory must exist
python -B -m security_platform.policy_contracts.cli preview --input examples/policy-preview.json --hbf-root <HostBasedFirewall source dir> --output demo-output/policy-preview.json
python -B -m security_platform.policy_contracts.cli check-preconditions --input examples/policy-preconditions.json --output demo-output/policy-preconditions.json
python -B -m security_platform.policy_contracts.cli validate-rollout --input examples/policy-rollout.json --evaluation-time 2030-01-01T00:30:00Z --output demo-output/policy-rollout.json
```

After installation, the same tool is also available as `security-policy`.

- **Exit 0** means the output file was written. Read its `status` and `blocker_codes`.
- **Exit 1** means the input was rejected. stderr shows one fixed code, and any existing output file is left unchanged. This applies to:
  - a schema error (`policy_input_invalid`);
  - an explicitly given `--hbf-root` that cannot be loaded (`evaluator_unavailable`);
  - with a loaded evaluator, an invalid policy bundle (`invalid_policy_bundle`);
  - with a loaded evaluator, an invalid scenario (`invalid_scenario`);
  - with a loaded evaluator, a network that appears in two zones (`ambiguous_equal_prefix_zones`).

The bundle, scenario and zone checks need the evaluator. Without `--hbf-root`, every schema-valid request is written as `blocked` with `evaluator_unavailable`.

What the examples show:

- The preview example shows an ALLOW → DENY change.
- The precondition and rollout examples intentionally lack real revision evidence. They end in `precondition_evidence_missing` and `would_pause`.
- `execution_authorized` is always `false`.

**The evaluator under `--hbf-root` is local Python code that the tool executes.** Point it only at a HostBasedFirewall checkout you trust.

## 5. Termivar offline analyst chain

```powershell
python -B scripts/run_offline_chain.py --workspace <new empty dir outside the repository> [--termivar-root <Termivar checkout>] [--phase30-delivery-zip <Phase30 delivery ZIP>]
```

The runner:

1. creates the fixed workspace layout the tools require (a real copy of the repository plus `outputs/`);
2. runs the documented commands of every phase in order;
3. compares every produced file with the recorded SHA-256 values in [examples/offline-chain/](../examples/offline-chain/README.md).

| Inputs | Phases run |
| --- | --- |
| Repository only | 16–19: assessment intake → handoff → review packet → HTML review desk → reconciled client draft |
| `--termivar-root` | 16–30 |
| Both options | 16–44 |

Phases that need a missing input are reported as `NOT_RUN`. The workspace must support hard links (NTFS on Windows).

A fully matched run shows that the current tools and inputs reproduce exactly the recorded demo outputs. It does not prove that any finding is correct, and it is not an authorized assessment.

**Putting analyst decisions into the client draft.** Decisions made on the review desk carry no reviewer and no time, so the handoff builder keeps them out of the client draft. To record who made the decisions and when, run [commercial_review_attribution](../tools/commercial_review_attribution/README.md) between `finalize_desk` and `reconcile_review`. Attribution:

- marks nothing as verified;
- does not change any decision;
- applies the same reviewer reference and time to every decision in the overlay.

The phase tools work only on the committed demonstration dataset ([section 10](#10-known-limitations-and-open-blockers)).

## 6. Inventory API (advanced)

The service needs:

- PostgreSQL with separate migration and runtime roles;
- an RS256 identity provider that issues RFC 9068 `at+jwt` access tokens, and its public JWKS file;
- a TLS certificate.

Missing settings stop the service. There is no mode that skips authentication.

| Variable | Meaning |
| --- | --- |
| `SP_DATABASE_URL` / `SP_MIGRATION_DATABASE_URL` | Runtime and schema-owner `postgresql+psycopg://` URLs |
| `SP_OPERATOR_ISSUER`, `SP_OPERATOR_AUDIENCE`, `SP_JWKS_FILE` | Fixed HTTPS issuer, audience and local public JWKS |
| `SP_ALLOWED_HOSTS` | Host header allow-list |
| `SP_CREDENTIAL_TTL_SECONDS` | Device credential lifetime: default 86400, maximum 30 days. A rotation can never ask for longer. |
| `SP_MAX_DEVICES_PER_TENANT` | Limit on active (non-revoked) devices |
| `SP_MAX_AUDIT_EVENTS_PER_TENANT` | Audit bound. A device-originated event evicts the oldest device event first, so repeated device actions cannot push administrative history out. Administrative events evict the oldest event. |
| `SP_REQUESTS_PER_MINUTE` | Request budget per client IP |

The order is `migrate`, `create-tenant`, `set-membership`, `serve`; see the root [README](../README.md#kurulum). Further detail:

- API contract: [API_V1.tr.md](API_V1.tr.md);
- roles and grants: [OPERATIONS.tr.md](OPERATIONS.tr.md);
- end-to-end acceptance test (two tenants, three devices, local test CA and JWKS): `python -B scripts/demo_acceptance.py`. It runs against the workspace PostgreSQL fixture, which `scripts/managed_postgres.py` manages as Windows-only test infrastructure, not a production installer.

**Device credentials expire.** Rotate before expiry:

```powershell
security-snapshot --rotate-credential --credential-file <private device.json> [--ca-file <CA bundle>]
```

The new secret is written atomically to the same protected file and is never printed. The server revokes the old secret in the same transaction. If the reply is lost, revoke the device and enroll it again. With a private or enterprise CA, pass `--ca-file`. Certificate and hostname verification are never disabled.

## 7. Tests

```powershell
python -B -m pytest -q -p no:cacheprovider
```

- Tests marked `integration` and `e2e` need the PostgreSQL fixture ([OPERATIONS.tr.md](OPERATIONS.tr.md)). Without it they fail with connection errors; those are not passes.
- On Windows, one POSIX-permission test is skipped, and one symlink test is skipped when symlinks cannot be created.
- The full analyst-chain test runs only when `SP_TERMIVAR_ROOT` and `SP_PHASE30_DELIVERY_ZIP` are set.

## 8. Troubleshooting

| Symptom | Cause | Action |
| --- | --- | --- |
| `preview_build_unavailable` from `serve.py` | No built console, or files do not match `build-manifest.json` | Use the packaged console build or run `pnpm build` |
| `preview_port_unavailable` | The port is already in use | Use another `--port` |
| `security-policy` exits 1 with `evaluator_unavailable` | `--hbf-root` is not a loadable HostBasedFirewall root | Pass the root of the HostBasedFirewall checkout |
| `security-policy` exits 1 with `policy_input_invalid` or another code | The input fails the schema or a policy rule | Compare it with `examples/`. Outputs are never overwritten on error. |
| `offline_chain: workspace_inside_repository` / `workspace_not_empty` | The workspace is inside the repository or not empty | Use a new directory outside the repository |
| `offline_chain: result=FAILED … MISMATCH` | A pinned file or tool behaviour changed | Read `W/run-logs/`. Do not copy new hashes over the recorded ones. |
| `task_reconciliation: rejected: <code>` | That fixed rejection code (listed in [IMPORT_AND_VALIDATION](commercial/operations/phase44/IMPORT_AND_VALIDATION.tr.md)) | Fix the named input |
| `Missing required setting: …` from `serve` | Required environment variable not set | See [section 6](#6-inventory-api-advanced) |
| Integration tests time out connecting | The PostgreSQL fixture is not running | Start it ([OPERATIONS.tr.md](OPERATIONS.tr.md)), or treat those tests as not run |

## 9. Security considerations

- **Secrets.** Secrets are read only from protected files or environment variables, never from arguments. Errors use fixed codes and never echo paths, tokens or policy contents.
- **Operator access.** Access comes only from database memberships keyed by issuer and subject. Token claims such as roles, tenant or e-mail grant nothing.
- **HTTP edge.** The edge requires HTTPS; the only exception is loopback with an explicit test flag. It also enforces allowed hosts, origin checks, a request budget, and limits on body size and depth.
- **Offline tools.** They accept strict JSON, bounded sizes and relative paths only. They never extract archives to disk and never overwrite outputs, and their output is deterministic.
- **Evaluator source.** The policy preview executes the evaluator source you select. Treat `--hbf-root` as trusted code.
- **Console.** Files and tokens stay in page memory only, and a strict CSP is applied.

These properties are covered by the automated tests in this repository. There has been no independent penetration test, no production deployment review and no third-party audit.

## 10. Known limitations and open blockers

Highest impact first:

1. **No production identity provider, deployment or database operations.** The inventory API has been accepted only against local fixtures: a test issuer and JWKS, a local TLS CA and a portable PostgreSQL. Not provided:
   - a real identity provider;
   - a reverse proxy for the console's live mode;
   - backups, high availability and monitoring.
2. **Console build not refreshed.** This release raises the console's import limits so that Termivar assessments with more than 100 items and policy previews up to the CLI maximum can be opened. That source change has not been compiled, because Node is not available on the build machine. Rebuild (`pnpm typecheck`, `pnpm build`) and re-check before demonstrating with large real files.
3. **Analyst chain limited to the demonstration dataset.** Intake accepts only the capability and category set of the bundled sample. The scope planner accepts one pinned Termivar commit. Later phases pin the hashes of earlier outputs. Processing a customer's own Termivar output needs these allow-lists and pins to become reviewed data inputs.
4. **Case bundles refuse cases with review decisions** (phase 22). The client draft can carry attributed decisions, but the case and portfolio views show unreviewed cases only.
5. **Manual credential lifecycle.** Rotation is explicit and manual. A lost rotation reply means re-enrollment. Revoked device rows are kept, and there is no purge command. After more than about 10,000 device rows in one tenant, the paged device list can no longer reach the newest devices; they stay reachable by device ID and through the audit log.
6. **No license or commercial terms.** No product license file or commercial terms are included; that is an owner decision.
7. **Windows acceptance not run.** Real HostBasedFirewall lifecycle, enforcement and signed-artifact acceptance are recorded as `NOT_RUN` ([WINDOWS_ACCEPTANCE_PLAN.tr.md](WINDOWS_ACCEPTANCE_PLAN.tr.md)).

## Reference documents

- Inventory API: [API_V1.tr.md](API_V1.tr.md), [ARCHITECTURE.tr.md](ARCHITECTURE.tr.md), [THREAT_MODEL.tr.md](THREAT_MODEL.tr.md), [OPERATIONS.tr.md](OPERATIONS.tr.md), [ACCEPTANCE.tr.md](ACCEPTANCE.tr.md).
- Policy: [POLICY_CONTRACT_V1.tr.md](POLICY_CONTRACT_V1.tr.md), [POLICY_PREVIEW_ACCEPTANCE.tr.md](POLICY_PREVIEW_ACCEPTANCE.tr.md).
- Console: [operator-console/README.md](../operator-console/README.md), [quick start (EN)](../operator-console/docs/QUICKSTART.en.md), [capability matrix](../operator-console/docs/CAPABILITY_MATRIX.tr.md).
- Commercial pilot package and analyst operations: [docs/commercial/README.tr.md](commercial/README.tr.md) and `docs/commercial/operations/phaseNN/`. The phase files are historical delivery records. Their "do not rerun" and "budget closed" notes describe how each phase was delivered; they do not restrict use of the tools.
