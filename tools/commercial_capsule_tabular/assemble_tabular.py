"""Publish bounded typed JSON and encoded CSV views of a recorded capsule."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation", _HERE):
    sys.path.insert(0, str(_path))

from tabular_contracts import (
    DEMO_LABEL, InputError, MAX_SCOPE_BYTES, MAX_DATASET_BYTES, MAX_MANIFEST_BYTES,
    parse_json, json_bytes, fixed, validate_scope,
)
from capsule_adapter import InputBudget, load_capsule, read_capsule
from tabular_dataset import build_tabular_dataset
from csv_renderer import render_csvs
from output_renderer import render_summary
from artifact_manifest import manifest_data, publish_tabular


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "capsule_tabular: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Recorded capsule metadata only; no spreadsheet or source acceptance.", allow_abbrev=False)
    for name in ("source-bundle", "scope", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        budget = InputBudget()
        scope = validate_scope(parse_json(budget.read_text(args.scope, MAX_SCOPE_BYTES), maximum=MAX_SCOPE_BYTES))
        snapshot = load_capsule(args.source_bundle, scope["export_reference_ids"], budget)
        _source, identity = read_capsule(snapshot)
        fixed(identity["sha256"], scope["source_capsule_sha256"], "tabular_scope_source_hash")
        dataset = build_tabular_dataset(snapshot, scope["export_reference_ids"])
        fixed(dataset["scope"], scope, "tabular_scope_dataset_correspondence")
        references, projections = render_csvs(dataset)
        payloads = {"tabular-dataset.json": json_bytes(dataset, maximum=MAX_DATASET_BYTES),
                    "reference-register.csv": references, "projection-register.csv": projections,
                    "tabular-summary.md": render_summary(dataset)}
        documents = {**payloads, "manifest.json": json_bytes(manifest_data(dataset, payloads), maximum=MAX_MANIFEST_BYTES)}
        budget.check_stability()
        publish_tabular(args.output_dir, documents)
    except FileNotFoundError:
        print("capsule_tabular: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("capsule_tabular: contract_or_disclosure_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, OverflowError):
        print("capsule_tabular: rejected; no complete delivery claimed", file=sys.stderr)
        return 1
    print("Created typed tabular dataset, reference CSV, projection CSV, summary and manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; upstream_guard_independently_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
