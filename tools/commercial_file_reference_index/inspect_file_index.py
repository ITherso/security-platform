"""Inspect only the five new disclosed-file-index output artifacts."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation",
              _HERE.parent / "commercial_capsule_tabular",
              _HERE.parent / "commercial_tabular_inbox", _HERE):
    sys.path.insert(0, str(_path))

from index_contracts import (
    INSPECTION_SCHEMA, MAX_INDEX_BYTES, MAX_LOOKUP_BYTES, MAX_MANIFEST_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, json_bytes, make_source_receipt, parse_json, validate_relationships,
)
from phase36_adapter import InputBudget
from disclosed_file_index import ValidatedFileIndex
from reverse_lookup import build_file_lookup
from output_renderer import render_index_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_file_index(index_path: str, lookup_path: str, receipt_path: str,
                       summary_path: str, manifest_path: str) -> dict:
    """Validate new-wire relations without reopening Phase36 source inputs."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_index = budget.read_text(index_path, MAX_INDEX_BYTES)
    raw_lookup = budget.read_text(lookup_path, MAX_LOOKUP_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    index, lookup, receipt = validate_relationships(
        parse_json(raw_index, maximum=MAX_INDEX_BYTES),
        parse_json(raw_lookup, maximum=MAX_LOOKUP_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    # Loading serialized new-index bytes establishes internal wire integrity,
    # not an independent recheck of its recorded five-file source group.
    snapshot = ValidatedFileIndex(raw_index)
    expected_lookup = build_file_lookup(snapshot, lookup["request"])
    expected_receipt = make_source_receipt(index)
    if (json_bytes(lookup, maximum=MAX_LOOKUP_BYTES)
            != json_bytes(expected_lookup, maximum=MAX_LOOKUP_BYTES)):
        raise InputError("file_index_inspection_lookup_mismatch")
    if (json_bytes(receipt, maximum=MAX_RECEIPT_BYTES)
            != json_bytes(expected_receipt, maximum=MAX_RECEIPT_BYTES)):
        raise InputError("file_index_inspection_receipt_mismatch")

    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_index_summary(index, lookup, receipt):
        raise InputError("file_index_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "file-reference-index.json": raw_index,
        "file-reference-lookup.json": raw_lookup,
        "index-source-receipt.json": raw_receipt,
        "file-index-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(index, lookup, receipt, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("file_index_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "index_counts": dict(index["counts"]),
        "lookup_counts": dict(lookup["counts"]),
        "source_counts": dict(index["source_counts"]),
        "source_artifacts": [
            {"name": item["name"], "bytes": item["bytes"],
             "sha256": item["sha256"], "schema_version": item["schema_version"]}
            for item in index["source_artifacts"]
        ],
        "request_reference": lookup["request"]["request_reference"],
        "file_index_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase36_files_read": False,
        "source_import_independently_verified": False,
        "source_capsule_read": False,
        "Phase35_CSV_reparsed": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "spreadsheet_import_acceptance_performed": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "five_new_file_index_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Internal correspondence of the five new file index/lookup/receipt/summary/manifest files only. "
            "No independent Phase36 input recheck or import behavior, source capsule, current source, "
            "upstream guard, producer, spreadsheet import, compiler, ownership, human, legal or release verification."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "file_index_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new disclosed-file-index outputs only; no independent source verification.",
        allow_abbrev=False,
    )
    for name in ("index", "lookup", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_file_index(args.index, args.lookup, args.receipt, args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("file_index_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("file_index_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("file_index_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created disclosed file-index inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("original_Phase36_files_read=false; source_import_independently_verified=false; source_capsule_read=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_file_index",)
