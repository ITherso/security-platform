"""Inspect five new typed-inbox outputs without reopening Phase35 inputs."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation",
              _HERE.parent / "commercial_capsule_tabular", _HERE):
    sys.path.insert(0, str(_path))

from inbox_contracts import (
    INSPECTION_SCHEMA, MAX_INBOX_BYTES, MAX_MANIFEST_BYTES, MAX_QUERY_BYTES,
    MAX_RECEIPT_BYTES, MAX_SUMMARY_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, json_bytes, parse_json, validate_relationships,
)
from phase35_adapter import InputBudget
from inbox_snapshot import ValidatedInbox
from reference_query import build_reference_query
from import_receipt import build_import_receipt
from output_renderer import render_inbox_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_inbox(inbox_path: str, query_path: str, receipt_path: str,
                  summary_path: str, manifest_path: str) -> dict:
    """Check only recorded new-wire models, rendering and actual byte ties."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_inbox = budget.read_text(inbox_path, MAX_INBOX_BYTES)
    raw_query = budget.read_text(query_path, MAX_QUERY_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    inbox, query, receipt = validate_relationships(
        parse_json(raw_inbox, maximum=MAX_INBOX_BYTES),
        parse_json(raw_query, maximum=MAX_QUERY_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    # This constructor validates only the closed new-inbox wire and its typed
    # relationships. It does not reconstruct a successful Phase35 source import.
    snapshot = ValidatedInbox(raw_inbox)
    expected_query = build_reference_query(snapshot, query["request"])
    expected_receipt = build_import_receipt(snapshot)
    if (json_bytes(query, maximum=MAX_QUERY_BYTES)
            != json_bytes(expected_query, maximum=MAX_QUERY_BYTES)):
        raise InputError("typed_inbox_inspection_query_mismatch")
    if (json_bytes(receipt, maximum=MAX_RECEIPT_BYTES)
            != json_bytes(expected_receipt, maximum=MAX_RECEIPT_BYTES)):
        raise InputError("typed_inbox_inspection_receipt_mismatch")

    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_inbox_summary(inbox, query, receipt):
        raise InputError("typed_inbox_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "typed-inbox.json": raw_inbox,
        "reference-query.json": raw_query,
        "import-receipt.json": raw_receipt,
        "inbox-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(inbox, query, receipt, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("typed_inbox_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "counts": dict(inbox["counts"]),
        "query_counts": dict(query["counts"]),
        "source_artifacts": [
            {"name": item["name"], "bytes": item["bytes"], "sha256": item["sha256"]}
            for item in inbox["source_artifacts"]
        ],
        "request_reference": query["request"]["request_reference"],
        "tabular_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "Phase35_CSV_reparsed": False,
        "import_behavior_independently_verified": False,
        "original_phase35_files_read": False,
        "source_capsule_read": False,
        "original_phase31_files_read": False,
        "original_phase32_files_read": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "spreadsheet_import_acceptance_performed": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "five_new_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Internal correspondence of five new inbox/query/receipt/summary/manifest files only. "
            "No independent Phase35 CSV parsing or import behavior, source capsule, original source "
            "freshness, upstream guard, producer, spreadsheet import, compiler, ownership, human, "
            "legal or release verification."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "tabular_inbox_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new inbox output correspondence only; no independent source-import verification.",
        allow_abbrev=False,
    )
    for name in ("inbox", "query", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_inbox(args.inbox, args.query, args.receipt, args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("tabular_inbox_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("tabular_inbox_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("tabular_inbox_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created typed inbox inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("Phase35_CSV_reparsed=false; import_behavior_independently_verified=false; source_capsule_read=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_inbox",)
