"""Reobserve a prior allowlist subset; never mutate historical evidence."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_candidate_revalidation.revalidation_contracts import (
    InputError, DEMO_LABEL, MAX_METADATA_BYTES, MAX_SCOPE_BYTES, MAX_TOTAL_CANDIDATE_BYTES,
    REVIEW_FIELDS, parse_json, validate_scope, validate_review_scope,
)
from commercial_candidate_revalidation.baseline_adapter import load_baseline
from commercial_candidate_revalidation.observation_reader import read_observations
from commercial_candidate_revalidation.observation_comparison import build_ledger
from commercial_candidate_revalidation.evidence_reuse_guard import build_reuse
from commercial_candidate_revalidation.artifact_manifest import publish_revalidation


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "candidate_revalidation: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline historical/current candidate observations, with a tool-local metadata reuse guard.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        metadata_budget = ReadBudget(maximum=MAX_METADATA_BYTES)
        scope = validate_scope(parse_json(metadata_budget.read(explicit_relative_path(args.scope), MAX_SCOPE_BYTES), maximum=MAX_SCOPE_BYTES))
        reference, baseline = load_baseline(scope, metadata_budget)
        review = validate_review_scope({key: scope[key] for key in REVIEW_FIELDS}, baseline)
        candidate_budget = ReadBudget(maximum=MAX_TOTAL_CANDIDATE_BYTES, identities=metadata_budget.identities)
        current = read_observations(review, baseline, args.termivar_root, candidate_budget)
        ledger = build_ledger(reference, baseline, review, current)
        # This is the new consumer path: only guard-produced current projections
        # are published in evidence-reuse. No historical-success fallback exists.
        reuse = build_reuse(ledger)
        metadata_budget.check_stability()
        candidate_budget.check_stability()
        publish_revalidation(output, ledger, reuse)
    except InputError:
        print("candidate_revalidation: closed_contract_expectation_or_safe_read_rejected; no successful ledger is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
        print("candidate_revalidation: local_preparation_failed; no successful ledger is claimed", file=sys.stderr)
        return 1
    print("Created demo revalidation ledger, guarded evidence reuse, Markdown and manifest")
    print(DEMO_LABEL)
    print("reference_context_revalidated=false; compiler_resolution_verified=false; historical_physical_identity=not_recorded")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
