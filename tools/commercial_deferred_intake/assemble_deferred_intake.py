"""Consume existing unsubmitted templates without candidate response intake."""
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
              _HERE.parent / "commercial_evidence_followup",
              _HERE.parent / "commercial_response_slots", _HERE):
    sys.path.insert(0, str(_path))

from intake_contracts import (
    InputError, MAX_REQUEST_BYTES, MAX_INTAKE_BYTES, MAX_CLASSIFICATION_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES,
    json_bytes, parse_json, validate_request,
)
from phase41_adapter import InputBudget, load_source
from task_bound_intake import build_deferred_intake, read_deferred_intake, build_intake_classification
from intake_receipt import make_source_receipt
from output_renderer import render_intake_summary
from artifact_manifest import manifest_data, publish_deferred_intake


def assemble_deferred_intake(slots_path: str, template_path: str, receipt_path: str,
                              summary_path: str, manifest_path: str,
                              request_path: str, output_dir: str) -> dict:
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    request = validate_request(parse_json(budget.read_text(request_path, MAX_REQUEST_BYTES),
                                         maximum=MAX_REQUEST_BYTES))
    source = load_source(slots_path, template_path, receipt_path,
                         summary_path, manifest_path, budget)
    snapshot = build_deferred_intake(source, request)
    intake = read_deferred_intake(snapshot)
    classification = build_intake_classification(snapshot)
    receipt = make_source_receipt(source, snapshot)
    payloads = {
        "deferred-intake-register.json": json_bytes(intake, maximum=MAX_INTAKE_BYTES),
        "intake-classification.json": json_bytes(classification, maximum=MAX_CLASSIFICATION_BYTES),
        "intake-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
        "intake-summary.md": render_intake_summary(intake, classification, receipt),
    }
    manifest = manifest_data(intake, classification, receipt, payloads)
    documents = {**payloads, "manifest.json": json_bytes(manifest, maximum=MAX_MANIFEST_BYTES)}
    budget.check_stability()
    publish_deferred_intake(output_dir, documents)
    return intake


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "deferred_intake: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Consume unsubmitted template metadata only; no candidate response processing.",
                       allow_abbrev=False)
    for name in ("slots", "template", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        intake = assemble_deferred_intake(args.slots, args.template, args.receipt,
                                           args.source_summary, args.source_manifest,
                                           args.request, args.output_dir)
    except FileNotFoundError:
        print("deferred_intake: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("deferred_intake: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("deferred_intake: rejected; no successful intake is claimed", file=sys.stderr)
        return 1
    print("Created deferred intake register, classification, source receipt, summary and manifest")
    print(intake["demo_label"])
    print("candidate_present=false; observations_verified=false; tasks_completed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
