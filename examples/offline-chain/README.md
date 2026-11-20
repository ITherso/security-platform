# Offline chain regeneration (phases 16-44)

`scripts/run_offline_chain.py` rebuilds the recorded demo outputs of the offline Termivar analyst toolchain
(`tools/commercial_*`, phases 16-44) in a new workspace with one command. It then compares the SHA256 of every
produced file with `expected-sha256.json`.

## What it proves and what it does not

A fully matched run shows **byte-identical, deterministic regeneration**: the current tool code, the committed
example inputs and the pinned external inputs produce exactly the bytes of the recorded demo deliveries.
This covers 168 files over 29 phases, including the ZIP capsules.

It does not show that any finding, source, licence, dependency or decision is correct, complete or trustworthy.
It is not a security assessment and it does not review, approve or release anything. Every tool still runs in
demo mode, and the outputs keep their demo labels and their false trust/authorization flags. The runner never
runs a scanner and never uses the network.

## Run

From the repository root, with Python 3.11 or newer and `git` on `PATH`:

```text
python -B scripts/run_offline_chain.py --workspace <new-empty-dir>
python -B scripts/run_offline_chain.py --workspace <new-empty-dir> --termivar-root <termivar-checkout> --phase30-delivery-zip <Termivar-Offline-Module-Candidates-phase30-2026-11-12.zip>
```

| Inputs supplied | Phases run | Others |
| --- | --- | --- |
| repository only | 16-19 | `NOT_RUN termivar_root_not_supplied` |
| `--termivar-root` | 16-30 | `NOT_RUN phase30_delivery_zip_not_supplied` |
| `--termivar-root` and `--phase30-delivery-zip` | 16-44 | none |

- `--termivar-root` must be a checkout of Termivar at commit `6a2639348c2366d0bf71b9a34e5484d40aa393a3`.
  The runner checks this with a read-only `git rev-parse HEAD` before it writes anything.
- `--phase30-delivery-zip` must have SHA256 `aab4d89f3fbf95992675ce08b095468680ba29fb07e2b85dea7ed1dbd3742485`.
  Phase31 hashes this ZIP; nothing extracts it.
- `--workspace` must be new or empty, and must not be inside the repository or the Termivar checkout.
  Everything is written inside it. The inputs are only read.

## What the runner does

1. Creates `W/security-platform` as a real copy (not a link) of the working-tree content of every git-tracked file,
   and creates `W/outputs`.
2. Copies `termivar-decision-draft.json` (the empty browser-exported desk draft used by the Phase19 demo) to
   `W/outputs/phase19-exported/`. If a ZIP was supplied, it also copies the ZIP to `W/outputs/`.
3. From `W`, runs the documented assemble/inspect commands of each phase in order with `python -I -B` and relative
   paths. These are the commands from each tool README or phase DEMO_DELIVERY, with the `security-platform/` prefix.
4. After each phase, checks the phase's output directories. Every expected file must exist with the expected
   SHA256, and no extra file may be present.

It prints one row per phase (status, command exit codes, files matched/total, seconds) and a final line.

| Result | Meaning | Exit code |
| --- | --- | --- |
| `ALL_MATCHED` | every phase ran and every file matched | 0 |
| `PARTIAL_MATCHED` | every phase that ran matched; some phases are `NOT_RUN` | 0 |
| `FAILED` | a command failed (`COMMAND_FAILED`) or bytes differed (`MISMATCH`); later phases are `NOT_RUN upstream_failed` | 1 |
| setup refusal | fixed `offline_chain: <code>; nothing was run` message | 2 |

Per-phase logs (commands, tool output, the names of differing files) are written to `W/run-logs/`.

## About `expected-sha256.json`

The values were taken from the recorded demo delivery outputs (`outputs/phaseNN-*`), not from a run of this
script. Two exceptions:

- Phase29 uses the corrected run (`phase29-rust-source-graph-corrected`). The original partial Phase29 output came
  from replaced code and is not reproduced.
- Phase44 uses the bytes of the r2 re-run, written to the documented `outputs/phase44-task-reconciliation`.

A `MISMATCH` means the tool behaviour, the inputs or the pinned files changed. Do not "fix" it by copying new
hashes into this file. Many later example requests pin upstream hashes, and Phase24-30 pin the platform's own
tool sources, so an edit to a pinned file breaks the chain on purpose.

## Tests

`tests/offline_chain/test_offline_chain.py` always runs phases 16-19. It runs the full chain only when both
`SP_TERMIVAR_ROOT` and `SP_PHASE30_DELIVERY_ZIP` are set; otherwise that test is skipped with a reason.

```text
python -B -m pytest tests/offline_chain -q -p no:cacheprovider
```

Requirements: the workspace must be on a filesystem with hard links (for example NTFS). The tools publish their
outputs through hard links.
