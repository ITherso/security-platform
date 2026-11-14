"""Inspect only the five new cohort query output artifacts."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation",
              _HERE.parent / "commercial_capsule_tabular",
              _HERE.parent / "commercial_tabular_inbox",
              _HERE.parent / "commercial_file_reference_index",
              _HERE.parent / "commercial_co_reference", _HERE):
    sys.path.insert(0, str(_path))

from cohort_contracts import (
    INSPECTION_SCHEMA, MAX_QUERY_BYTES, MAX_WITNESSES_BYTES, MAX_RECEIPT_BYTES,
    MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, json_bytes, parse_json, query_from_witnesses, validate_relationships,
)
from phase38_adapter import InputBudget
from output_renderer import render_cohort_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_cohort_query(query_path: str, witnesses_path: str, receipt_path: str,
                         summary_path: str, manifest_path: str) -> dict:
    """Check new-output relationships, with no original Phase38 source read."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_query = budget.read_text(query_path, MAX_QUERY_BYTES)
    raw_witnesses = budget.read_text(witnesses_path, MAX_WITNESSES_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    query, witnesses, receipt = validate_relationships(
        parse_json(raw_query, maximum=MAX_QUERY_BYTES),
        parse_json(raw_witnesses, maximum=MAX_WITNESSES_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    # This reconstruction is limited to the returned new witness records.
    # It neither reloads the parent group nor establishes source completeness.
    if (json_bytes(query, maximum=MAX_QUERY_BYTES)
            != json_bytes(query_from_witnesses(witnesses), maximum=MAX_QUERY_BYTES)):
        raise InputError("cohort_inspection_query_witness_mismatch")

    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_cohort_summary(query, witnesses, receipt):
        raise InputError("cohort_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "cohort-query.json": raw_query,
        "cohort-witnesses.json": raw_witnesses,
        "cohort-source-receipt.json": raw_receipt,
        "cohort-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(query, witnesses, receipt, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("cohort_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_phase38_join_sha256": query["source_phase38_join_sha256"],
        "source_phase38_manifest_sha256": query["source_phase38_manifest_sha256"],
        "source_artifacts": [dict(item) for item in receipt["source_artifacts"]],
        "source_counts": dict(receipt["source_counts"]),
        "query_counts": dict(query["counts"]),
        "request_reference": query["request"]["request_reference"],
        "cohort_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase38_files_read": False,
        "source_cohort_match_independently_verified": False,
        "source_no_other_matches_independently_verified": False,
        "source_import_independently_verified": False,
        "source_capsule_read": False,
        "Phase35_CSV_reparsed": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "spreadsheet_import_acceptance_performed": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "five_new_cohort_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Internal correspondence of the five new cohort query/witnesses/receipt/summary/manifest files only. "
            "No independent Phase38 source recheck, cohort matching or proof of no other source matches, "
            "current file state, physical or source relationship, import, source capsule, upstream guard, "
            "producer, compiler, ownership, human, legal, customer or release verification."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "cohort_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new cohort outputs only; no independent source matching or current-file verification.",
        allow_abbrev=False,
    )
    for name in ("query", "witnesses", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_cohort_query(args.query, args.witnesses, args.receipt, args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("cohort_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("cohort_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("cohort_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created cohort inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("original_Phase38_files_read=false; source_no_other_matches_independently_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_cohort_query",)
