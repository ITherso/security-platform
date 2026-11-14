"""Inspect only the five new response slot output artifacts."""
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
              _HERE.parent / "commercial_evidence_followup", _HERE):
    sys.path.insert(0, str(_path))

from slot_contracts import (
    INSPECTION_SCHEMA, MAX_SLOTS_BYTES, MAX_TEMPLATE_BYTES, MAX_RECEIPT_BYTES,
    MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    common, json_bytes, parse_json, template_from_slots, validate_relationships,
)
from phase40_adapter import InputBudget
from output_renderer import render_response_slot_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_response_slots(slots_path: str, template_path: str, receipt_path: str,
                            summary_path: str, manifest_path: str) -> dict:
    """Check internal new-output correspondence; accept no external response."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_slots = budget.read_text(slots_path, MAX_SLOTS_BYTES)
    raw_template = budget.read_text(template_path, MAX_TEMPLATE_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    slots, template, receipt = validate_relationships(
        parse_json(raw_slots, maximum=MAX_SLOTS_BYTES),
        parse_json(raw_template, maximum=MAX_TEMPLATE_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    if raw_slots != json_bytes(slots, maximum=MAX_SLOTS_BYTES):
        raise InputError("response_slot_inspection_slots_not_canonical")
    slots_sha256 = hashlib.sha256(raw_slots).hexdigest()
    if template["slots_sha256"] != slots_sha256:
        raise InputError("response_slot_inspection_actual_slots_digest_mismatch")
    if (json_bytes(template, maximum=MAX_TEMPLATE_BYTES)
            != json_bytes(template_from_slots(slots), maximum=MAX_TEMPLATE_BYTES)):
        raise InputError("response_slot_inspection_template_mismatch")
    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_response_slot_summary(slots, template, receipt):
        raise InputError("response_slot_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "task-response-slots.json": raw_slots,
        "response-template.json": raw_template,
        "response-slot-source-receipt.json": raw_receipt,
        "response-slot-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(slots, template, receipt, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("response_slot_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_phase40_queue_sha256": slots["source_phase40_queue_sha256"],
        "source_phase40_manifest_sha256": slots["source_phase40_manifest_sha256"],
        "source_artifacts": [dict(item) for item in receipt["source_artifacts"]],
        "source_counts": deepcopy_counts(receipt["source_counts"]),
        "slots_counts": dict(slots["counts"]),
        "template_counts": dict(template["counts"]),
        "slots_sha256": slots_sha256,
        "request_reference": slots["request"]["request_reference"],
        "response_slot_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase40_files_read": False,
        # These seventeen fields are this inspector's own limits. The five
        # Phase40 source models contain none of them; no inheritance is claimed.
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
        "inspection_scope": "five_new_response_slot_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Only the five new slots/template/receipt/summary/manifest files are compared. "
            "The 17 flat limit flags are local inspector declarations, not inherited from the five Phase40 sources. "
            "No original source recheck, task membership/necessity proof, response receipt, observation, "
            "assignment, fulfillment, collection authorization, producer, human, legal or release verification."
        ),
    }


def deepcopy_counts(value: dict) -> dict:
    """Copy the two closed original count maps without introducing new scopes."""
    return {"queue_counts": dict(value["queue_counts"]),
            "handoff_counts": dict(value["handoff_counts"])}


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "response_slot_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new slot outputs only; no response ingestion or observation acceptance.",
        allow_abbrev=False,
    )
    for name in ("slots", "template", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_response_slots(args.slots, args.template, args.receipt,
                                        args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("response_slot_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("response_slot_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("response_slot_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created response slot inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("original_Phase40_files_read=false; tasks_assigned=false; collection_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_response_slots",)
