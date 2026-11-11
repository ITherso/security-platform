"""Produce an offline source declaration graph, never a resolved dependency graph."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_dependency_evidence.composition_adapter import load_context
from commercial_dependency_evidence.manifest_scope import load_manifests
from commercial_dependency_evidence.cargo_declarations import extract_declarations
from commercial_dependency_evidence.component_ownership import build_ownership
from commercial_dependency_evidence.dependency_binding import build_bindings
from commercial_dependency_evidence.evidence_graph import build_primary, build_graph, build_variants
from commercial_dependency_evidence.artifact_manifest import publish_evidence
from commercial_dependency_evidence.evidence_contracts import DEMO_LABEL, InputError, parse_json, validate_scope


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "dependency_evidence: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Bounded static source declarations only; no Cargo, build or approval path.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "output-dir", "composition-inventory", "composition-dependencies",
                 "composition-constraints", "composition-summary", "composition-manifest", "variant-analysis",
                 "variant-dependencies", "variant-licenses", "variant-summary", "variant-manifest"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        json_budget = ReadBudget(maximum=12 * 1024 * 1024)
        scope_raw = json_budget.read(explicit_relative_path(args.scope), 128 * 1024)
        scope = validate_scope(parse_json(scope_raw, maximum=128 * 1024))
        composition_paths = {key: getattr(args, "composition_" + key)
                             for key in ("inventory", "dependencies", "constraints", "summary", "manifest")}
        variant_paths = {key: getattr(args, "variant_" + key)
                         for key in ("analysis", "dependencies", "licenses", "summary", "manifest")}
        context = load_context(scope, composition_paths, variant_paths, json_budget)
        manifest_budget = ReadBudget(maximum=16 * 256 * 1024, identities=json_budget.identities)
        raw_by_id, metadata = load_manifests(scope, context, args.termivar_root, manifest_budget)
        source_manifests, declarations = extract_declarations(raw_by_id, metadata)
        ownership = build_ownership(source_manifests, context.components)
        bindings = build_bindings(declarations, context.phase24_records, context.manifest_catalog)
        evidence = build_primary(context.reference, context.components, context.manifest_catalog,
                                 context.phase24_records, context.variant_selections, context.license_boundary_counts,
                                 source_manifests, declarations, ownership, bindings)
        graph, variants = build_graph(evidence), build_variants(evidence)
        json_budget.check_stability()
        manifest_budget.check_stability()
        publish_evidence(output, evidence, graph, variants)
    except InputError:
        print("dependency_evidence: closed_contract_or_source_binding_rejected; no successful delivery is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("dependency_evidence: local_source_preparation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo direct dependency evidence, source graph, variant overlay, Markdown and manifest")
    print(DEMO_LABEL)
    print("dependency_resolution_performed=false; build_closure_verified=false; redistribution_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
