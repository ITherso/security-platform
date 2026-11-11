"""Assemble explicit candidate file evidence without any Rust evaluation."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_module_candidates.candidate_contracts import (
    InputError, DEMO_LABEL, MAX_METADATA_BYTES, MAX_SCOPE_BYTES, MAX_TOTAL_CANDIDATE_BYTES, parse_json,
)
from commercial_module_candidates.candidate_scope import validate_scope, review_from_scope
from commercial_module_candidates.source_reference_adapter import load_context
from commercial_module_candidates.candidate_file_reader import read_candidate_files
from commercial_module_candidates.candidate_binding import build_evidence
from commercial_module_candidates.candidate_triage import build_triage
from commercial_module_candidates.inventory_projection import build_projection
from commercial_module_candidates.artifact_manifest import publish_candidates


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "module_candidates: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline explicit module candidate identities; no compiler, lexer, discovery or module resolution.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        metadata_budget = ReadBudget(maximum=MAX_METADATA_BYTES)
        scope = validate_scope(parse_json(metadata_budget.read(explicit_relative_path(args.scope), MAX_SCOPE_BYTES), maximum=MAX_SCOPE_BYTES))
        reference, context = load_context(scope, metadata_budget)
        review = review_from_scope(scope, context)
        candidate_budget = ReadBudget(maximum=MAX_TOTAL_CANDIDATE_BYTES, identities=metadata_budget.identities)
        files = read_candidate_files(review, args.termivar_root, candidate_budget, reference["source_commits"])
        evidence = build_evidence(reference, context, review, files)
        triage = build_triage(evidence)
        coverage = build_projection(evidence, triage)
        metadata_budget.check_stability()
        candidate_budget.check_stability()
        publish_candidates(output, evidence, triage, coverage)
    except InputError:
        print("module_candidates: closed_contract_source_or_byte_budget_rejected; no successful delivery is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
        print("module_candidates: local_preparation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo candidate evidence, triage, coverage, Markdown and manifest")
    print(DEMO_LABEL)
    print("compiler_resolution_verified=false; module_closure_verified=false; source_inventory_updated=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
