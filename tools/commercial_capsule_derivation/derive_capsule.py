"""Derive a strict selected-reference subset of one existing portable capsule."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))
sys.path.insert(0, str(_HERE.parent / "commercial_reference_capsule"))
sys.path.insert(0, str(_HERE))

from capsule_manifest import zip_bytes
from derivation_contracts import (
    DEMO_LABEL, InputError, MAX_REQUEST_BYTES, MAX_LEDGER_BYTES, MAX_MANIFEST_BYTES,
    parse_json, json_bytes, validate_request, make_ledger,
)
from phase33_adapter import InputBudget, load_validated_source, read_validated_source
from derived_capsule_builder import derive_reference_subset
from derivation_renderer import render_summary
from artifact_manifest import byte_identity, manifest_data, publish_derivation


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "capsule_derivation: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline strict capsule subset; no original-source verification.", allow_abbrev=False)
    for name in ("source-bundle", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        budget = InputBudget()
        request = validate_request(parse_json(budget.read_text(args.request, MAX_REQUEST_BYTES), maximum=MAX_REQUEST_BYTES))
        snapshot = load_validated_source(args.source_bundle, request["selected_reference_ids"], budget)
        source, source_identity = read_validated_source(snapshot)
        derived = derive_reference_subset(snapshot, request)
        raw_zip = zip_bytes(derived)
        derived_identity = {**byte_identity(raw_zip), "capsule_reference": derived["capsule_reference"]}
        ledger = make_ledger(request, source, derived, source_identity, derived_identity)
        payloads = {"derived-reference-capsule.zip": raw_zip,
                    "derivation-ledger.json": json_bytes(ledger, maximum=MAX_LEDGER_BYTES),
                    "derivation-summary.md": render_summary(ledger)}
        documents = {**payloads, "manifest.json": json_bytes(manifest_data(ledger, payloads), maximum=MAX_MANIFEST_BYTES)}
        budget.check_stability()
        publish_derivation(args.output_dir, documents)
    except FileNotFoundError:
        print("capsule_derivation: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("capsule_derivation: contract_or_subset_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError,
            RecursionError, StopIteration, OverflowError):
        print("capsule_derivation: rejected; no complete delivery claimed", file=sys.stderr)
        return 1
    print("Created derived capsule, metadata-only ledger, summary and manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; upstream_guard_independently_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
