"""Inspect four new minimized files; never execute the upstream guard."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_reference_metadata.artifact_manifest import manifest_data
from commercial_reference_metadata.output_renderer import render_summary
from commercial_reference_metadata.consumer_contracts import (
    RESPONSE_SCHEMA, SELECTION_SCHEMA, INSPECTION_SCHEMA, DEMO_LABEL, MAX_JSON_BYTES, MAX_SUMMARY_BYTES,
    MAX_MANIFEST_BYTES, MAX_TOTAL_INPUT_BYTES, InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "reference_metadata_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Minimized wire consistency only; no independent upstream guard or source verification.", allow_abbrev=False)
    for name in ("response", "selection", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        import hashlib
        raw = {}
        budget = ReadBudget(maximum=MAX_TOTAL_INPUT_BYTES)
        for role, maximum in (("response", MAX_JSON_BYTES), ("selection", MAX_JSON_BYTES),
                              ("summary", MAX_SUMMARY_BYTES), ("manifest", MAX_MANIFEST_BYTES)):
            raw[role] = budget.read(explicit_relative_path(getattr(args, role)), maximum)
        response, selection = (parse_json(raw[key]) for key in ("response", "selection"))
        for doc, schema in ((response, RESPONSE_SCHEMA), (selection, SELECTION_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                raise InputError("reference_metadata_unsupported_contract")
        validate_documents(response, selection)
        if raw["summary"] != render_summary(response, selection):
            raise InputError("reference_metadata_summary_projection_mismatch")
        payloads = {"reference-metadata-response.json": raw["response"], "metadata-selection-ledger.json": raw["selection"],
                    "metadata-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=MAX_MANIFEST_BYTES)) != json_bytes(manifest_data(response, selection, payloads)):
            raise InputError("reference_metadata_manifest_mismatch")
        budget.check_stability()
        report = {**common(INSPECTION_SCHEMA, response["source_reference"]), "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, "bytes": len(body), "sha256": hashlib.sha256(body).hexdigest()} for role, body in raw.items()],
                  "response_counts": response["counts"], "selection_counts": selection["counts"],
                  "original_phase31_files_read": False, "old_baseline_read": False, "candidate_files_read": False,
                  "source_archive_read": False, "old_guard_reexecuted": False,
                  "upstream_guard_independently_verified": False, "source_producer_verified": False,
                  "legal_review_performed": False,
                  "inspection_scope": "four_explicit_new_files_and_minimized_wire_correspondence_only",
                  "integrity_limit": "Internal response, selection, count, summary and manifest consistency only. No upstream guard truth, new source observation, live freshness, compiler, producer, ownership or release acceptance."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("reference_metadata_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("reference_metadata_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
        print("reference_metadata_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo metadata inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("upstream_guard_independently_verified=false; source_files_reobserved=false; independent_observation_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
