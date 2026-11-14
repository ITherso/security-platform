"""Create a minimal offline request capsule without dispatch or response."""
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
              _HERE.parent / "commercial_co_reference",
              _HERE.parent / "commercial_cohort_query",
              _HERE.parent / "commercial_evidence_followup",
              _HERE.parent / "commercial_response_slots",
              _HERE.parent / "commercial_deferred_intake", _HERE):
    sys.path.insert(0, str(_path))

from exchange_contracts import (
    InputError, MAX_REQUEST_BYTES, MAX_INDEX_BYTES, MAX_RECEIPT_BYTES,
    MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, build_response_contract,
    json_bytes, make_exchange_index, parse_json, validate_request,
)
from phase42_adapter import InputBudget, load_source
from task_request_projection import build_task_request, make_source_receipt
from portable_capsule import build_task_exchange_capsule
from recipient_reader import inspect_task_exchange_capsule, read_portable_task_request
from output_renderer import render_task_exchange_summary
from artifact_manifest import manifest_data, publish_task_exchange


def assemble_task_exchange(register_path: str, classification_path: str, receipt_path: str,
                            summary_path: str, manifest_path: str,
                            request_path: str, output_dir: str) -> dict:
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    request = validate_request(parse_json(budget.read_text(request_path, MAX_REQUEST_BYTES),
                                         maximum=MAX_REQUEST_BYTES))
    source = load_source(register_path, classification_path, receipt_path,
                         summary_path, manifest_path, budget)
    envelope = build_task_request(source, request)
    contract = build_response_contract()
    capsule = build_task_exchange_capsule(envelope, contract)
    portable = inspect_task_exchange_capsule(capsule)
    envelope, _contract, _inner_artifacts = read_portable_task_request(portable)
    index = make_exchange_index(envelope, hashlib.sha256(capsule).hexdigest())
    receipt = make_source_receipt(source, envelope)
    payloads = {
        "task-exchange-capsule.zip": capsule,
        "task-exchange-index.json": json_bytes(index, maximum=MAX_INDEX_BYTES),
        "task-exchange-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
        "task-exchange-summary.md": render_task_exchange_summary(envelope, index, receipt),
    }
    manifest = manifest_data(capsule, index, receipt, payloads)
    documents = {**payloads, "manifest.json": json_bytes(manifest, maximum=MAX_MANIFEST_BYTES)}
    budget.check_stability()
    publish_task_exchange(output_dir, documents)
    return index


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "task_exchange: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Prepare a portable pending-task request only; no dispatch or response.",
                       allow_abbrev=False)
    for name in ("register", "classification", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        index = assemble_task_exchange(args.register, args.classification, args.receipt,
                                       args.source_summary, args.source_manifest,
                                       args.request, args.output_dir)
    except FileNotFoundError:
        print("task_exchange: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("task_exchange: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("task_exchange: rejected; no successful exchange is claimed", file=sys.stderr)
        return 1
    print("Created portable task capsule, exchange index, source receipt, summary and manifest")
    print(index["demo_label"])
    print("task_dispatched=false; source_observation_verified=false; recipient_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
