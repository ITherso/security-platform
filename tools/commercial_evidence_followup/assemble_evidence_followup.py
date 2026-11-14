"""Prepare offline, unassigned requests from recorded missing evidence only."""
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
              _HERE.parent / "commercial_cohort_query", _HERE):
    sys.path.insert(0, str(_path))

from followup_contracts import (
    InputError, MAX_REQUEST_BYTES, MAX_QUEUE_BYTES, MAX_HANDOFF_BYTES,
    MAX_RECEIPT_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES,
    json_bytes, parse_json, validate_request, make_source_receipt,
)
from phase39_adapter import InputBudget, load_source, read_source
from missing_evidence_queue import build_followup_queue, read_followup_queue
from analyst_handoff import build_analyst_handoff
from output_renderer import render_followup_summary
from artifact_manifest import manifest_data, publish_evidence_followup


def assemble_evidence_followup(query_path: str, witnesses_path: str, receipt_path: str,
                               summary_path: str, manifest_path: str,
                               request_path: str, output_dir: str) -> dict:
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    request = validate_request(parse_json(budget.read_text(request_path, MAX_REQUEST_BYTES),
                                         maximum=MAX_REQUEST_BYTES))
    source = load_source(query_path, witnesses_path, receipt_path,
                         summary_path, manifest_path, budget)
    snapshot = build_followup_queue(source, request)
    queue = read_followup_queue(snapshot)
    handoff = build_analyst_handoff(snapshot)
    query, _witnesses, _receipt, artifacts = read_source(source)
    receipt = make_source_receipt(artifacts, query["counts"])
    payloads = {
        "evidence-followup-queue.json": json_bytes(queue, maximum=MAX_QUEUE_BYTES),
        "analyst-handoff.json": json_bytes(handoff, maximum=MAX_HANDOFF_BYTES),
        "followup-source-receipt.json": json_bytes(receipt, maximum=MAX_RECEIPT_BYTES),
        "followup-summary.md": render_followup_summary(queue, handoff, receipt),
    }
    manifest = manifest_data(queue, handoff, receipt, payloads)
    documents = {**payloads, "manifest.json": json_bytes(manifest, maximum=MAX_MANIFEST_BYTES)}
    budget.check_stability()
    publish_evidence_followup(output_dir, documents)
    return queue


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "evidence_followup: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Prepare recorded missing-evidence follow-up only; no assignment or observation.", allow_abbrev=False)
    for name in ("query", "witnesses", "receipt", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        queue = assemble_evidence_followup(args.query, args.witnesses, args.receipt,
                                          args.source_summary, args.source_manifest,
                                          args.request, args.output_dir)
    except FileNotFoundError:
        print("evidence_followup: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("evidence_followup: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("evidence_followup: rejected; no successful queue is claimed", file=sys.stderr)
        return 1
    print("Created recorded missing-evidence queue, analyst handoff, source receipt, summary and manifest")
    print(queue["demo_label"])
    print("tasks_assigned=false; collection_authorized=false; source_files_reobserved=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
