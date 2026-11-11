"""Create demo pilot scope metadata without running any product or resolver."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.artifact_manifest import publish_variants
from commercial_pilot_variants.composition_adapter import ReadBudget, load_composition
from commercial_pilot_variants.evidence_adapter import load_evidence
from commercial_pilot_variants.component_selection import build_component_catalog, build_manifest_catalog
from commercial_pilot_variants.dependency_exposure import build_dependencies
from commercial_pilot_variants.readiness_projection import build_readiness
from commercial_pilot_variants.variant_comparison import build_analysis
from commercial_pilot_variants.variant_contracts import DEMO_LABEL, InputError, parse_json, validate_scope


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "pilot_variants: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline pilot scope decision support; no executable or approval path.", allow_abbrev=False)
    names = ("scope", "output-dir", "composition-inventory", "composition-dependencies",
             "composition-constraints", "composition-summary", "composition-manifest",
             "evidence-ledger", "evidence-queue", "evidence-conflicts", "evidence-summary", "evidence-manifest")
    for name in names:
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        budget = ReadBudget()
        raw = budget.read(explicit_relative_path(args.scope), 128 * 1024)
        scope = validate_scope(parse_json(raw, maximum=128 * 1024))
        composition_paths = {key: getattr(args, "composition_" + key)
                             for key in ("inventory", "dependencies", "constraints", "summary", "manifest")}
        evidence_paths = {key: getattr(args, "evidence_" + key)
                          for key in ("ledger", "queue", "conflicts", "summary", "manifest")}
        composition = load_composition(scope, composition_paths, budget)
        evidence = load_evidence(scope, evidence_paths, composition, budget)
        components = build_component_catalog(composition.inventory, evidence.ledger)
        manifests = build_manifest_catalog(composition.inventory, composition.dependencies)
        dependencies = build_dependencies(composition.dependencies, components, manifests,
                                          evidence.ledger, scope["variants"], evidence.source_reference,
                                          candidate_reference=scope["candidate_reference"])
        licenses = build_readiness(composition.constraints, evidence.ledger, evidence.queue,
                                   evidence.conflicts, dependencies, scope["variants"], evidence.source_reference,
                                   candidate_reference=scope["candidate_reference"])
        analysis = build_analysis(scope, components, manifests, dependencies, licenses, evidence.source_reference)
        budget.check_stability()
        publish_variants(output, analysis, dependencies, licenses)
    except InputError:
        print("pilot_variants: closed_contract_or_source_binding_rejected; no successful delivery is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("pilot_variants: local_preparation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo variant analysis, dependency exposure, license readiness, Markdown and manifest")
    print(DEMO_LABEL)
    print("dependency_closure_verified=false; redistribution_authorized=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
