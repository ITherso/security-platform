"""Assemble one explicit, offline, recorded-presence ALL-OF cohort query."""
from __future__ import annotations

import argparse
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
    InputError, MAX_REQUEST_BYTES, MAX_QUERY_BYTES, MAX_WITNESSES_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES,
    json_bytes, parse_json, validate_request, make_source_receipt,
)
from phase38_adapter import InputBudget, load_co_reference_source, read_co_reference_source
from cohort_matcher import build_cohort_query, read_cohort_query
from witness_projection import build_cohort_witnesses
from output_renderer import render_cohort_summary
from artifact_manifest import manifest_data, publish_cohort_query


def assemble_cohort_query(join_path: str, lookup_path: str, receipt_path: str,
                          summary_path: str, manifest_path: str,
                          request_path: str, output_dir: str) -> dict:
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    request = validate_request(parse_json(budget.read_text(request_path, MAX_REQUEST_BYTES),
                                         maximum=MAX_REQUEST_BYTES))
    source = load_co_reference_source(join_path, lookup_path, receipt_path,
                                     summary_path, manifest_path, budget)
    snapshot = build_cohort_query(source, request)
    query = read_cohort_query(snapshot)
    witnesses = build_cohort_witnesses(source, snapshot)
    join, _lookup, _receipt, artifacts, _old_request = read_co_reference_source(source)
    receipt = make_source_receipt(artifacts, join["source_counts"])
    payloads = {
        "cohort-query.json": json_bytes(query, maximum=MAX_QUERY_BYTES),
        "cohort-witnesses.json": json_bytes(witnesses, maximum=MAX_WITNESSES_BYTES),
        "cohort-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
        "cohort-summary.md": render_cohort_summary(query, witnesses, receipt),
    }
    manifest = manifest_data(query, witnesses, receipt, payloads)
    documents = {**payloads, "manifest.json": json_bytes(manifest, maximum=MAX_MANIFEST_BYTES)}
    budget.check_stability()
    publish_cohort_query(output_dir, documents)
    return query


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "cohort_query: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline disclosed ALL-OF metadata query only.", allow_abbrev=False)
    for name in ("join", "source-lookup", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        query = assemble_cohort_query(args.join, args.source_lookup, args.receipt,
                                     args.source_summary, args.source_manifest,
                                     args.request, args.output_dir)
    except FileNotFoundError:
        print("cohort_query: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("cohort_query: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("cohort_query: rejected; no successful cohort result is claimed", file=sys.stderr)
        return 1
    print("Created disclosed ALL-OF cohort query, whole-reference witnesses, source receipt, summary and manifest")
    print(query["demo_label"])
    print("source_files_reobserved=false; producer_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
