"""Inspect five explicit new files; never reopen source artifacts or evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_composition.artifact_manifest import identity
from commercial_composition.source_inventory import read_explicit_text
from commercial_handoff.input_loader import explicit_relative_path
from commercial_license_review.conflict_analysis import build_conflicts
from commercial_license_review.evidence_contracts import (
    DEMO_LABEL, INSPECTION_SCHEMA, InputError, common, json_bytes, parse_json, validate_documents,
)
from commercial_license_review.evidence_manifest import manifest_data
from commercial_license_review.output_renderer import render_summary
from commercial_license_review.review_queue import build_queue


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "license_evidence_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Inspect internal evidence metadata and byte bindings only.", allow_abbrev=False)
    for name in ("ledger", "queue", "conflicts", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        for role, maximum in (("ledger", 4 * 1024 * 1024), ("queue", 4 * 1024 * 1024),
                              ("conflicts", 4 * 1024 * 1024), ("summary", 512 * 1024),
                              ("manifest", 64 * 1024)):
            raw[role], _ = read_explicit_text(explicit_relative_path(getattr(args, role)), maximum)
        ledger, queue, conflicts = (parse_json(raw[role]) for role in ("ledger", "queue", "conflicts"))
        validate_documents(ledger, queue, conflicts)
        if json_bytes(conflicts) != json_bytes(build_conflicts(ledger)):
            raise InputError("license_review_conflict_projection_mismatch")
        if json_bytes(queue) != json_bytes(build_queue(ledger, conflicts)):
            raise InputError("license_review_queue_projection_mismatch")
        if raw["summary"] != render_summary(ledger, queue, conflicts):
            raise InputError("license_review_summary_projection_mismatch")
        payloads = {"license-evidence-ledger.json": raw["ledger"],
                    "review-queue.json": raw["queue"],
                    "binding-conflicts.json": raw["conflicts"],
                    "evidence-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=64 * 1024)) != json_bytes(
                manifest_data(ledger, queue, conflicts, payloads)):
            raise InputError("license_review_manifest_mismatch")
        report = {**common(INSPECTION_SCHEMA, ledger["composition_reference"]),
                  "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "ledger_counts": ledger["counts"], "queue_counts": queue["counts"],
                  "conflict_counts": conflicts["counts"],
                  "original_composition_files_read": False, "evidence_files_read": False,
                  "source_producer_verified": False, "legal_review_performed": False,
                  "inspection_scope": "five_explicit_generated_files_and_pure_metadata_projections_only",
                  "integrity_limit": "Internal byte/model consistency only; no evidence authenticity, package applicability, human decision, legal clearance or release authority."}
        publish_inspection(args.output, report)
    except InputError as error:
        print("license_evidence_inspection: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError):
        print("license_evidence_inspection: local_inspection_failed; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo license evidence inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("evidence_files_read=false; legal_review_performed=false; redistribution_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
