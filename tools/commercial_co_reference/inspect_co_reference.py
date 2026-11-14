"""Inspect only the five new co-reference output artifacts."""
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
              _HERE.parent / "commercial_file_reference_index", _HERE):
    sys.path.insert(0, str(_path))

from co_reference_contracts import (
    INSPECTION_SCHEMA, MAX_JOIN_BYTES, MAX_LOOKUP_BYTES, MAX_MANIFEST_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, json_bytes, lookup_from_join, make_source_receipt, parse_json,
    validate_relationships, validate_request,
)
from phase37_adapter import InputBudget
from output_renderer import render_co_reference_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_co_reference(join_path: str, lookup_path: str, receipt_path: str,
                         summary_path: str, manifest_path: str) -> dict:
    """Check new-wire correspondence without reopening Phase37 source files."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_join = budget.read_text(join_path, MAX_JOIN_BYTES)
    raw_lookup = budget.read_text(lookup_path, MAX_LOOKUP_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    join, lookup, receipt = validate_relationships(
        parse_json(raw_join, maximum=MAX_JOIN_BYTES),
        parse_json(raw_lookup, maximum=MAX_LOOKUP_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    # These pure reconstructions establish only new-output correspondence.
    # The source-bound public lookup requires the original five-file context
    # and is deliberately not called by this inspector.
    if (json_bytes(lookup, maximum=MAX_LOOKUP_BYTES)
            != json_bytes(lookup_from_join(join), maximum=MAX_LOOKUP_BYTES)):
        raise InputError("co_reference_inspection_lookup_mismatch")
    if (json_bytes(receipt, maximum=MAX_RECEIPT_BYTES)
            != json_bytes(make_source_receipt(join), maximum=MAX_RECEIPT_BYTES)):
        raise InputError("co_reference_inspection_receipt_mismatch")

    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_co_reference_summary(join, lookup, receipt):
        raise InputError("co_reference_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    if type(actual_manifest) is not dict:
        raise InputError("co_reference_inspection_manifest_object_required")
    request = validate_request(actual_manifest.get("request"))
    payloads = {
        "co-reference-join.json": raw_join,
        "co-reference-lookup.json": raw_lookup,
        "co-reference-source-receipt.json": raw_receipt,
        "co-reference-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(join, lookup, receipt, payloads, request)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("co_reference_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_counts": dict(join["source_counts"]),
        "join_counts": dict(join["counts"]),
        "lookup_counts": dict(lookup["counts"]),
        "source_artifacts": [dict(item) for item in join["source_artifacts"]],
        "request_reference": request["request_reference"],
        "co_reference_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase37_files_read": False,
        "source_co_reference_independently_verified": False,
        "source_import_independently_verified": False,
        "source_capsule_read": False,
        "Phase35_CSV_reparsed": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "spreadsheet_import_acceptance_performed": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "five_new_co_reference_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Internal correspondence of the five new co-reference join/lookup/receipt/summary/manifest files only. "
            "No independent Phase37 source recheck, source co-reference or import verification, physical-file "
            "relationship, current source, source capsule, upstream guard, producer, compiler, ownership, "
            "human, legal, customer or release verification."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "co_reference_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new co-reference outputs only; no independent source or physical-file verification.",
        allow_abbrev=False,
    )
    for name in ("join", "lookup", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_co_reference(args.join, args.lookup, args.receipt, args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("co_reference_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("co_reference_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("co_reference_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created co-reference inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("original_Phase37_files_read=false; source_co_reference_independently_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_co_reference",)
