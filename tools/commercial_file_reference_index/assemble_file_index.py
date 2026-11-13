"""Build a disclosed-only file index and whole-reference reverse lookup."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation",
              _HERE.parent / "commercial_capsule_tabular",
              _HERE.parent / "commercial_tabular_inbox", _HERE):
    sys.path.insert(0, str(_path))

from index_contracts import (
    DEMO_LABEL, InputError, MAX_REQUEST_BYTES, MAX_INDEX_BYTES, MAX_LOOKUP_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, parse_json, json_bytes,
    validate_request, validate_relationships, make_source_receipt,
)
from phase36_adapter import InputBudget, load_source
from disclosed_file_index import build_disclosed_file_index, read_disclosed_file_index
from reverse_lookup import build_file_lookup
from output_renderer import render_index_summary
from artifact_manifest import manifest_data, publish_file_index


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "file_reference_index: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Disclosed recorded metadata only; no current source verification.", allow_abbrev=False)
    for name in ("inbox", "source-query", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        budget = InputBudget()
        request = validate_request(parse_json(budget.read_text(args.request, MAX_REQUEST_BYTES), maximum=MAX_REQUEST_BYTES))
        source = load_source(args.inbox, args.source_query, args.receipt,
                             args.source_summary, args.source_manifest, budget)
        snapshot = build_disclosed_file_index(source)
        index = read_disclosed_file_index(snapshot)
        lookup = build_file_lookup(snapshot, request)
        receipt = make_source_receipt(index)
        validate_relationships(index, lookup, receipt)
        payloads = {"file-reference-index.json": json_bytes(index, maximum=MAX_INDEX_BYTES),
                    "file-reference-lookup.json": json_bytes(lookup, maximum=MAX_LOOKUP_BYTES),
                    "index-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
                    "file-index-summary.md": render_index_summary(index, lookup, receipt)}
        documents = {**payloads, "manifest.json": json_bytes(manifest_data(index, lookup, receipt, payloads), maximum=MAX_MANIFEST_BYTES)}
        budget.check_stability()
        publish_file_index(args.output_dir, documents)
    except FileNotFoundError:
        print("file_reference_index: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("file_reference_index: contract_or_disclosure_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, OverflowError):
        print("file_reference_index: rejected; no complete delivery claimed", file=sys.stderr)
        return 1
    print("Created disclosed file index, whole-reference lookup, source receipt, summary and manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; producer_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
