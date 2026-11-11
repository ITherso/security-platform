"""Inspect five new files only; never open original source or parent artefacts."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_composition.artifact_manifest import identity
from commercial_module_candidates.artifact_manifest import manifest_data
from commercial_module_candidates.output_renderer import render_summary
from commercial_module_candidates.candidate_contracts import (
    LEDGER_SCHEMA, TRIAGE_SCHEMA, COVERAGE_SCHEMA, INSPECTION_SCHEMA, DEMO_LABEL,
    MAX_JSON_BYTES, MAX_SUMMARY_BYTES, MAX_MANIFEST_BYTES, MAX_METADATA_BYTES,
    InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "module_candidate_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Internal candidate metadata consistency only; no independent filesystem or Rust resolution acceptance.", allow_abbrev=False)
    for name in ("evidence", "triage", "coverage", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        budget = ReadBudget(maximum=MAX_METADATA_BYTES)
        for role, maximum in (("evidence", MAX_JSON_BYTES), ("triage", MAX_JSON_BYTES), ("coverage", MAX_JSON_BYTES),
                              ("summary", MAX_SUMMARY_BYTES), ("manifest", MAX_MANIFEST_BYTES)):
            raw[role] = budget.read(explicit_relative_path(getattr(args, role)), maximum)
        evidence, triage, coverage = (parse_json(raw[key]) for key in ("evidence", "triage", "coverage"))
        for doc, schema in ((evidence, LEDGER_SCHEMA), (triage, TRIAGE_SCHEMA), (coverage, COVERAGE_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                raise InputError("module_candidate_unsupported_contract")
        validate_documents(evidence, triage, coverage)
        if raw["summary"] != render_summary(evidence, triage, coverage):
            raise InputError("module_candidate_summary_projection_mismatch")
        payloads = {"module-candidate-evidence.json": raw["evidence"], "candidate-triage.json": raw["triage"],
                    "candidate-coverage.json": raw["coverage"], "candidate-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=MAX_MANIFEST_BYTES)) != json_bytes(manifest_data(evidence, triage, coverage, payloads)):
            raise InputError("module_candidate_manifest_mismatch")
        budget.check_stability()
        report = {**common(INSPECTION_SCHEMA, evidence["source_reference"]), "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "evidence_counts": evidence["counts"], "triage_counts": triage["counts"], "coverage_counts": coverage["counts"],
                  "original_phase24_files_read": False, "original_phase29_files_read": False,
                  "candidate_source_files_read": False, "lexer_reexecuted": False,
                  "independent_file_presence_verified": False, "independent_lexical_correctness_verified": False,
                  "source_producer_verified": False, "legal_review_performed": False,
                  "inspection_scope": "five_explicit_new_files_and_recomputable_metadata_relationships_only",
                  "integrity_limit": "Recorded metadata and byte consistency only. Candidate filesystem observations, original lexical truth, Rust AST/compiler resolution, source completeness, producer/pinned Git attestation, component ownership, build/runtime and release authority are not independently verified."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("module_candidate_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("module_candidate_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
        print("module_candidate_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo candidate inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("candidate_source_files_read=false; lexer_reexecuted=false; compiler_resolution_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
