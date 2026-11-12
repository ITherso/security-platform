"""Inspect four new metadata files; never reopen original artefacts or sources."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_composition.artifact_manifest import identity
from commercial_candidate_revalidation.artifact_manifest import manifest_data
from commercial_candidate_revalidation.output_renderer import render_summary
from commercial_candidate_revalidation.revalidation_contracts import (
    LEDGER_SCHEMA, REUSE_SCHEMA, INSPECTION_SCHEMA, DEMO_LABEL, MAX_JSON_BYTES, MAX_SUMMARY_BYTES,
    MAX_MANIFEST_BYTES, MAX_METADATA_BYTES, InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "revalidation_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Recorded metadata consistency only; no independent source, filesystem or context revalidation.", allow_abbrev=False)
    for name in ("ledger", "reuse", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        budget = ReadBudget(maximum=MAX_METADATA_BYTES)
        for role, maximum in (("ledger", MAX_JSON_BYTES), ("reuse", MAX_JSON_BYTES),
                              ("summary", MAX_SUMMARY_BYTES), ("manifest", MAX_MANIFEST_BYTES)):
            raw[role] = budget.read(explicit_relative_path(getattr(args, role)), maximum)
        ledger, reuse = (parse_json(raw[key]) for key in ("ledger", "reuse"))
        for doc, schema in ((ledger, LEDGER_SCHEMA), (reuse, REUSE_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                raise InputError("revalidation_unsupported_contract")
        validate_documents(ledger, reuse)
        if raw["summary"] != render_summary(ledger, reuse):
            raise InputError("revalidation_summary_projection_mismatch")
        payloads = {"revalidation-ledger.json": raw["ledger"], "evidence-reuse.json": raw["reuse"],
                    "revalidation-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=MAX_MANIFEST_BYTES)) != json_bytes(manifest_data(ledger, reuse, payloads)):
            raise InputError("revalidation_manifest_mismatch")
        budget.check_stability()
        report = {**common(INSPECTION_SCHEMA, ledger["source_reference"]), "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "ledger_counts": ledger["counts"], "reuse_counts": reuse["counts"],
                  "original_phase30_files_read": False, "source_package_reopened": False,
                  "candidate_source_files_read": False, "original_entrypoint_or_Phase24_files_read": False,
                  "lexer_reexecuted": False, "independent_current_observation_verified": False,
                  "historical_physical_identity_verified": False, "source_producer_verified": False,
                  "legal_review_performed": False,
                  "inspection_scope": "four_explicit_new_files_and_recomputable_recorded_metadata_only",
                  "integrity_limit": "Historical/current metadata and guard consistency only. No independent filesystem observation, enduring freshness, physical identity, original lexical context, Rust compiler resolution, producer/Git, ownership, build/runtime or release acceptance."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("revalidation_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("revalidation_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
        print("revalidation_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo revalidation inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("candidate_source_files_read=false; reference_context_revalidated=false; compiler_resolution_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
