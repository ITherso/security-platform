"""Inspect one existing capsule against its closed tabular handoff files."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(1, str(_HERE.parent / "commercial_reference_capsule"))
sys.path.insert(2, str(_HERE.parent / "commercial_capsule_derivation"))
sys.path.insert(3, str(_HERE.parent))

from tabular_contracts import (
    INSPECTION_SCHEMA, MAX_CSV_BYTES, MAX_DATASET_BYTES, MAX_MANIFEST_BYTES,
    MAX_SUMMARY_BYTES, MAX_TOTAL_INPUT_BYTES, InputError, common, json_bytes,
    parse_json, validate_dataset,
)
from capsule_adapter import InputBudget, load_capsule, read_capsule
from tabular_dataset import build_tabular_dataset
from csv_renderer import inspect_csvs
from output_renderer import render_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_tabular(source_bundle: str, dataset_path: str, references_path: str,
                    projections_path: str, summary_path: str, manifest_path: str) -> dict:
    """Check actual source-capsule correspondence and fixed tabular encoding.

    The full source model stays inside the validated immutable adapter. Only
    selected dataset rows are compared or rendered; no omitted source results
    or blocked candidate metadata are copied into this inspection report.
    """
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_dataset = budget.read_text(dataset_path, MAX_DATASET_BYTES)
    dataset = validate_dataset(parse_json(raw_dataset, maximum=MAX_DATASET_BYTES))
    ids = dataset["scope"]["export_reference_ids"]
    snapshot = load_capsule(source_bundle, ids, budget)
    _source_model, source_identity = read_capsule(snapshot)
    if source_identity["sha256"] != dataset["scope"]["source_capsule_sha256"]:
        raise InputError("capsule_tabular_inspection_source_digest_mismatch")
    expected_dataset = build_tabular_dataset(snapshot, ids)
    if (json_bytes(dataset, maximum=MAX_DATASET_BYTES)
            != json_bytes(expected_dataset, maximum=MAX_DATASET_BYTES)):
        raise InputError("capsule_tabular_inspection_source_dataset_mismatch")

    raw_references = budget.read_text(references_path, MAX_CSV_BYTES)
    raw_projections = budget.read_text(projections_path, MAX_CSV_BYTES)
    csv_rows = inspect_csvs(dataset, raw_references, raw_projections)
    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_summary(dataset):
        raise InputError("capsule_tabular_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "tabular-dataset.json": raw_dataset,
        "reference-register.csv": raw_references,
        "projection-register.csv": raw_projections,
        "tabular-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(dataset, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("capsule_tabular_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_capsule": dict(source_identity),
        "counts": dict(dataset["counts"]),
        "csv_rows": csv_rows,
        "csv_encoding": dict(dataset["csv_encoding"]),
        "internal_content_status": "content_consistent",
        "tabular_artifacts": [
            {"role": "dataset", **_identity(raw_dataset)},
            {"role": "references", **_identity(raw_references)},
            {"role": "projections", **_identity(raw_projections)},
            {"role": "summary", **_identity(raw_summary)},
            {"role": "manifest", **_identity(raw_manifest)},
        ],
        "original_phase31_files_read": False,
        "original_phase32_files_read": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "spreadsheet_import_acceptance_performed": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "explicit_capsule_and_dataset_two_CSVs_summary_manifest_correspondence_only",
        "integrity_limit": (
            "Internal capsule-to-dataset correspondence, decoded typed cells, canonical CSV, summary "
            "and manifest bytes only. No spreadsheet import acceptance, independent Phase31 guard, "
            "original-source freshness, producer, compiler, ownership, human, legal or release verification."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "capsule_tabular_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Recorded capsule-to-tabular correspondence only; no original-source verification.",
        allow_abbrev=False,
    )
    for name in ("source-bundle", "dataset", "references", "projections", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_tabular(args.source_bundle, args.dataset, args.references,
                                 args.projections, args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("capsule_tabular_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("capsule_tabular_inspection: contract_or_encoding_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("capsule_tabular_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created capsule tabular inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("source_files_reobserved=false; upstream_guard_independently_verified=false; spreadsheet_import_acceptance_performed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_tabular",)
