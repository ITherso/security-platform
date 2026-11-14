"""Inspect only the five new evidence follow-up output artifacts."""
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
              _HERE.parent / "commercial_cohort_query", _HERE):
    sys.path.insert(0, str(_path))

from followup_contracts import (
    INSPECTION_SCHEMA, MAX_QUEUE_BYTES, MAX_HANDOFF_BYTES, MAX_RECEIPT_BYTES,
    MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, handoff_from_queue, json_bytes, parse_json, validate_relationships,
)
from phase39_adapter import InputBudget
from output_renderer import render_followup_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_evidence_followup(queue_path: str, handoff_path: str, receipt_path: str,
                              summary_path: str, manifest_path: str) -> dict:
    """Check new artifacts without source observation or necessity acceptance."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_queue = budget.read_text(queue_path, MAX_QUEUE_BYTES)
    raw_handoff = budget.read_text(handoff_path, MAX_HANDOFF_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    queue, handoff, receipt = validate_relationships(
        parse_json(raw_queue, maximum=MAX_QUEUE_BYTES),
        parse_json(raw_handoff, maximum=MAX_HANDOFF_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    # The handoff binds canonical queue bytes. Require those same bytes to be
    # the actual input file, not merely an equivalent JSON object.
    if raw_queue != json_bytes(queue, maximum=MAX_QUEUE_BYTES):
        raise InputError("evidence_followup_inspection_queue_not_canonical")
    queue_sha256 = hashlib.sha256(raw_queue).hexdigest()
    if handoff["queue_sha256"] != queue_sha256:
        raise InputError("evidence_followup_inspection_actual_queue_digest_mismatch")
    if (json_bytes(handoff, maximum=MAX_HANDOFF_BYTES)
            != json_bytes(handoff_from_queue(queue), maximum=MAX_HANDOFF_BYTES)):
        raise InputError("evidence_followup_inspection_handoff_mismatch")

    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_followup_summary(queue, handoff, receipt):
        raise InputError("evidence_followup_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "evidence-followup-queue.json": raw_queue,
        "analyst-handoff.json": raw_handoff,
        "followup-source-receipt.json": raw_receipt,
        "followup-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(queue, handoff, receipt, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("evidence_followup_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_phase39_witnesses_sha256": queue["source_phase39_witnesses_sha256"],
        "source_phase39_manifest_sha256": queue["source_phase39_manifest_sha256"],
        "source_artifacts": [dict(item) for item in receipt["source_artifacts"]],
        "source_counts": dict(receipt["source_counts"]),
        "queue_counts": dict(queue["counts"]),
        "handoff_counts": dict(handoff["counts"]),
        "queue_sha256": queue_sha256,
        "request_reference": queue["request"]["request_reference"],
        "followup_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase39_files_read": False,
        "source_missing_observation_independently_verified": False,
        "source_followup_necessity_independently_verified": False,
        "source_import_independently_verified": False,
        "source_capsule_read": False,
        "Phase35_CSV_reparsed": False,
        "old_guard_reexecuted": False,
        "native_source_files_read": False,
        "original_source_artifact_bytes_independently_verified": False,
        "spreadsheet_import_acceptance_performed": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "tasks_sent": False,
        "tasks_assigned": False,
        "tasks_fulfilled": False,
        "collection_authorized": False,
        "human_acceptance_verified": False,
        "inspection_scope": "five_new_evidence_followup_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Internal correspondence of the five new follow-up queue/handoff/receipt/summary/manifest files only. "
            "No independent Phase39 source recheck, missing observation, task necessity, current file state, "
            "source relationship, import, guard, producer, compiler, ownership, human, legal, customer or release "
            "verification; no task sending, assignment, fulfillment, collection authorization or human acceptance."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "evidence_followup_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new follow-up outputs only; no observation, assignment or fulfillment acceptance.",
        allow_abbrev=False,
    )
    for name in ("queue", "handoff", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_evidence_followup(args.queue, args.handoff, args.receipt,
                                           args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("evidence_followup_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("evidence_followup_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("evidence_followup_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created evidence follow-up inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("original_Phase39_files_read=false; tasks_assigned=false; collection_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_evidence_followup",)
