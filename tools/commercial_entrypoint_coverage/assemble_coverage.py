"""Create unapplied repository source-scope proposals from explicit local files."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_entrypoint_coverage.coverage_contracts import InputError, DEMO_LABEL, parse_json, validate_scope
from commercial_entrypoint_coverage.source_adapter import load_sources, load_manifests
from commercial_entrypoint_coverage.cargo_target_reader import extract_targets
from commercial_entrypoint_coverage.entrypoint_file_reader import read_entrypoint_files
from commercial_entrypoint_coverage.source_coverage import build_coverage
from commercial_entrypoint_coverage.scope_delta import build_delta
from commercial_entrypoint_coverage.variant_projection import build_variants
from commercial_entrypoint_coverage.artifact_manifest import publish_coverage


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "entrypoint_coverage: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline explicit entry-point metadata only; no scope application or build.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        budget = ReadBudget(maximum=12 * 1024 * 1024)
        scope_raw = budget.read(explicit_relative_path(args.scope), 128 * 1024)
        scope = validate_scope(parse_json(scope_raw, maximum=128 * 1024))
        loaded = load_sources(scope, budget)
        raw_by_id, metadata = load_manifests(scope, loaded, args.termivar_root, budget)
        manifests, targets = extract_targets(raw_by_id, metadata)
        observations = read_entrypoint_files(scope, targets, args.termivar_root, budget)
        coverage = build_coverage(loaded.reference, loaded.context, manifests, targets, observations)
        delta = build_delta(coverage)
        variants = build_variants(coverage, delta)
        budget.check_stability()
        publish_coverage(output, coverage, delta, variants)
    except InputError:
        print("entrypoint_coverage: closed_contract_or_source_binding_rejected; no successful delivery is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("entrypoint_coverage: local_source_preparation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo entry-point coverage, unapplied source-scope delta, variant projection, Markdown and manifest")
    print(DEMO_LABEL)
    print("source_inventory_updated=false; scope_delta_applied=false; component_ownership_verified=false; build_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
