"""Import five explicit Phase35 files, then publish typed reference metadata."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
for _path in (_HERE.parent, _HERE.parent / "commercial_reference_capsule",
              _HERE.parent / "commercial_capsule_derivation",
              _HERE.parent / "commercial_capsule_tabular", _HERE):
    sys.path.insert(0, str(_path))

from inbox_contracts import (
    DEMO_LABEL, InputError, MAX_REQUEST_BYTES, MAX_INBOX_BYTES, MAX_QUERY_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, parse_json, json_bytes, validate_request,
    validate_relationships,
)
from phase35_adapter import InputBudget, load_tabular_import
from inbox_snapshot import build_typed_inbox, read_typed_inbox
from reference_query import build_reference_query
from import_receipt import build_import_receipt
from output_renderer import render_inbox_summary
from artifact_manifest import manifest_data, publish_inbox


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "tabular_inbox: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Typed CSV metadata only; no source or producer verification.", allow_abbrev=False)
    for name in ("dataset", "references", "projections", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        budget = InputBudget()
        request = validate_request(parse_json(budget.read_text(args.request, MAX_REQUEST_BYTES), maximum=MAX_REQUEST_BYTES))
        imported = load_tabular_import(args.dataset, args.references, args.projections,
                                       args.source_summary, args.source_manifest, budget)
        snapshot = build_typed_inbox(imported)
        inbox = read_typed_inbox(snapshot)
        query = build_reference_query(snapshot, request)
        receipt = build_import_receipt(snapshot)
        validate_relationships(inbox, query, receipt)
        payloads = {"typed-inbox.json": json_bytes(inbox, maximum=MAX_INBOX_BYTES),
                    "reference-query.json": json_bytes(query, maximum=MAX_QUERY_BYTES),
                    "import-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
                    "inbox-summary.md": render_inbox_summary(inbox, query, receipt)}
        documents = {**payloads, "manifest.json": json_bytes(manifest_data(inbox, query, receipt, payloads), maximum=MAX_MANIFEST_BYTES)}
        budget.check_stability()
        publish_inbox(args.output_dir, documents)
    except FileNotFoundError:
        print("tabular_inbox: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("tabular_inbox: contract_or_reconciliation_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, OverflowError):
        print("tabular_inbox: rejected; no complete delivery claimed", file=sys.stderr)
        return 1
    print("Created CSV-derived typed inbox, reference query, import receipt, summary and manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; producer_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
