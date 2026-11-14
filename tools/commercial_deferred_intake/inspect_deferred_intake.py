"""Inspect only the five new deferred-intake output artifacts."""
from __future__ import annotations

import argparse
from copy import deepcopy
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
              _HERE.parent / "commercial_response_slots", _HERE):
    sys.path.insert(0, str(_path))

from intake_contracts import (
    INSPECTION_SCHEMA, MAX_INTAKE_BYTES, MAX_CLASSIFICATION_BYTES, MAX_RECEIPT_BYTES,
    MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, InputError,
    classification_from_intake, common, json_bytes, parse_json, validate_relationships,
)
from phase41_adapter import InputBudget
from output_renderer import render_intake_summary
from artifact_manifest import manifest_data, publish_inspection


def _identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def inspect_deferred_intake(intake_path: str, classification_path: str, receipt_path: str,
                             summary_path: str, manifest_path: str) -> dict:
    """Check new-output correspondence without invoking a candidate decoder."""
    budget = InputBudget(maximum=MAX_TOTAL_INPUT_BYTES)
    raw_intake = budget.read_text(intake_path, MAX_INTAKE_BYTES)
    raw_classification = budget.read_text(classification_path, MAX_CLASSIFICATION_BYTES)
    raw_receipt = budget.read_text(receipt_path, MAX_RECEIPT_BYTES)
    intake, classification, receipt = validate_relationships(
        parse_json(raw_intake, maximum=MAX_INTAKE_BYTES),
        parse_json(raw_classification, maximum=MAX_CLASSIFICATION_BYTES),
        parse_json(raw_receipt, maximum=MAX_RECEIPT_BYTES),
    )
    if raw_intake != json_bytes(intake, maximum=MAX_INTAKE_BYTES):
        raise InputError("deferred_intake_inspection_register_not_canonical")
    intake_sha256 = hashlib.sha256(raw_intake).hexdigest()
    if classification["intake_register_sha256"] != intake_sha256:
        raise InputError("deferred_intake_inspection_actual_register_digest_mismatch")
    if (json_bytes(classification, maximum=MAX_CLASSIFICATION_BYTES)
            != json_bytes(classification_from_intake(intake), maximum=MAX_CLASSIFICATION_BYTES)):
        raise InputError("deferred_intake_inspection_classification_mismatch")
    raw_summary = budget.read_text(summary_path, MAX_SUMMARY_BYTES)
    if raw_summary != render_intake_summary(intake, classification, receipt):
        raise InputError("deferred_intake_inspection_summary_mismatch")
    raw_manifest = budget.read_text(manifest_path, MAX_MANIFEST_BYTES)
    actual_manifest = parse_json(raw_manifest, maximum=MAX_MANIFEST_BYTES)
    payloads = {
        "deferred-intake-register.json": raw_intake,
        "intake-classification.json": raw_classification,
        "intake-source-receipt.json": raw_receipt,
        "intake-summary.md": raw_summary,
    }
    expected_manifest = manifest_data(intake, classification, receipt, payloads)
    if (json_bytes(actual_manifest, maximum=MAX_MANIFEST_BYTES)
            != json_bytes(expected_manifest, maximum=MAX_MANIFEST_BYTES)):
        raise InputError("deferred_intake_inspection_manifest_mismatch")
    budget.check_stability()
    return {
        **common(INSPECTION_SCHEMA),
        "source_phase41_slots_sha256": intake["source_phase41_slots_sha256"],
        "source_phase41_manifest_sha256": intake["source_phase41_manifest_sha256"],
        "source_artifacts": [dict(item) for item in receipt["source_artifacts"]],
        "source_counts": deepcopy(receipt["source_counts"]),
        "intake_counts": dict(intake["counts"]),
        "classification_counts": dict(classification["counts"]),
        "intake_register_sha256": intake_sha256,
        "request_reference": intake["request"]["request_reference"],
        "intake_artifacts": [
            {"name": name, **_identity(body)}
            for name, body in (*payloads.items(), ("manifest.json", raw_manifest))
        ],
        "internal_content_status": "content_consistent",
        "original_Phase41_files_read": False,
        "candidate_decoder_executed": False,
        "filled_candidate_processed": False,
        "source_files_reobserved": False,
        "tasks_assigned": False,
        "observations_verified": False,
        "tasks_completed": False,
        "source_producer_verified": False,
        "human_acceptance_verified": False,
        "inspection_scope": "five_new_deferred_intake_outputs_internal_correspondence_only",
        "integrity_limit": (
            "Only the five new intake/classification/receipt/summary/manifest files are internally compared. "
            "Local operation flags are not inherited source workflow flags. No Phase41 source recheck, "
            "filled-candidate decoding, observation, assignment, completion, producer or human acceptance is verified."
        ),
    }


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "deferred_intake_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Five new deferred-intake outputs only; no filled-candidate decoding or observation acceptance.",
        allow_abbrev=False,
    )
    for name in ("intake", "classification", "receipt", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        report = inspect_deferred_intake(args.intake, args.classification, args.receipt,
                                         args.summary, args.manifest)
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("deferred_intake_inspection: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("deferred_intake_inspection: contract_or_correspondence_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError, OverflowError):
        print("deferred_intake_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created deferred intake inspection; internal_content_status=content_consistent")
    print(report["demo_label"])
    print("candidate_decoder_executed=false; observations_verified=false; tasks_completed=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_deferred_intake",)
