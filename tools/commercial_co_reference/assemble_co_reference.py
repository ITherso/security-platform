"""Join only recorded disclosed references; no physical-file relationship."""
from __future__ import annotations

import argparse
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
    DEMO_LABEL, InputError, MAX_REQUEST_BYTES, MAX_JOIN_BYTES, MAX_LOOKUP_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, parse_json, json_bytes, fixed,
    validate_request, validate_relationships, make_source_receipt,
)
from phase37_adapter import InputBudget, load_source
from co_reference_join import build_co_reference_join, read_co_reference_join
from co_reference_lookup import build_co_reference_lookup
from output_renderer import render_co_reference_summary
from artifact_manifest import manifest_data, publish_co_reference


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "co_reference: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Disclosed co-reference only; no physical or source relationship verification.", allow_abbrev=False)
    for name in ("index", "source-lookup", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        budget = InputBudget()
        request = validate_request(parse_json(budget.read_text(args.request, MAX_REQUEST_BYTES), maximum=MAX_REQUEST_BYTES))
        source = load_source(args.index, args.source_lookup, args.receipt,
                             args.source_summary, args.source_manifest, budget)
        snapshot = build_co_reference_join(source, request["requested_file_ids"])
        join = read_co_reference_join(snapshot)
        for key in ("source_index_sha256", "source_manifest_sha256", "requested_file_ids"):
            fixed(request[key], join[key], "co_reference_request_actual_source")
        lookup = build_co_reference_lookup(source, snapshot)
        receipt = make_source_receipt(join)
        validate_relationships(join, lookup, receipt)
        payloads = {"co-reference-join.json": json_bytes(join, maximum=MAX_JOIN_BYTES),
                    "co-reference-lookup.json": json_bytes(lookup, maximum=MAX_LOOKUP_BYTES),
                    "co-reference-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
                    "co-reference-summary.md": render_co_reference_summary(join, lookup, receipt)}
        documents = {**payloads, "manifest.json": json_bytes(manifest_data(join, lookup, receipt, payloads, request), maximum=MAX_MANIFEST_BYTES)}
        budget.check_stability()
        publish_co_reference(args.output_dir, documents)
    except FileNotFoundError:
        print("co_reference: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("co_reference: contract_or_disclosure_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, OverflowError):
        print("co_reference: rejected; no complete delivery claimed", file=sys.stderr)
        return 1
    print("Created disclosed co-reference join, whole-reference lookup, source receipt, summary and manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; producer_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
