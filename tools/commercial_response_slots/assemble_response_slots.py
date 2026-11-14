"""Create task-bound empty response slots; never ingest an observation."""
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
              _HERE.parent / "commercial_co_reference",
              _HERE.parent / "commercial_cohort_query",
              _HERE.parent / "commercial_evidence_followup", _HERE):
    sys.path.insert(0, str(_path))

from slot_contracts import (
    InputError, MAX_REQUEST_BYTES, MAX_SLOTS_BYTES, MAX_TEMPLATE_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES,
    json_bytes, parse_json, validate_request,
)
from phase40_adapter import InputBudget, load_source
from response_slot_builder import build_response_slots, read_response_slots, make_source_receipt
from response_template import build_response_template
from output_renderer import render_response_slot_summary
from artifact_manifest import manifest_data, publish_response_slots


def assemble_response_slots(queue_path: str, handoff_path: str, receipt_path: str,
                            summary_path: str, manifest_path: str,
                            request_path: str, output_dir: str) -> dict:
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    request = validate_request(parse_json(budget.read_text(request_path, MAX_REQUEST_BYTES),
                                         maximum=MAX_REQUEST_BYTES))
    source = load_source(queue_path, handoff_path, receipt_path,
                         summary_path, manifest_path, budget)
    snapshot = build_response_slots(source, request)
    slots = read_response_slots(snapshot)
    template = build_response_template(snapshot)
    receipt = make_source_receipt(source, snapshot)
    payloads = {
        "task-response-slots.json": json_bytes(slots, maximum=MAX_SLOTS_BYTES),
        "response-template.json": json_bytes(template, maximum=MAX_TEMPLATE_BYTES),
        "response-slot-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
        "response-slot-summary.md": render_response_slot_summary(slots, template, receipt),
    }
    manifest = manifest_data(slots, template, receipt, payloads)
    documents = {**payloads, "manifest.json": json_bytes(manifest, maximum=MAX_MANIFEST_BYTES)}
    budget.check_stability()
    publish_response_slots(output_dir, documents)
    return slots


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "response_slots: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Prepare unsubmitted task-bound response slots only; no observation or assignment.",
                       allow_abbrev=False)
    for name in ("queue", "handoff", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        slots = assemble_response_slots(args.queue, args.handoff, args.receipt,
                                         args.source_summary, args.source_manifest,
                                         args.request, args.output_dir)
    except FileNotFoundError:
        print("response_slots: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("response_slots: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("response_slots: rejected; no successful response slots are claimed", file=sys.stderr)
        return 1
    print("Created unsubmitted task-bound response slots, template, source receipt, summary and manifest")
    print(slots["demo_label"])
    print("submission_received=false; tasks_assigned=false; collection_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
