"""Create a bounded source composition proposal; never a distributable product."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_composition.artifact_manifest import identity, publish_composition
from commercial_composition.composition_contracts import DEMO_LABEL, InputError, parse_json, validate_scope
from commercial_composition.dependency_reader import read_dependencies
from commercial_composition.license_evidence import build_license_evidence
from commercial_composition.release_constraints import build_constraints
from commercial_composition.source_inventory import build_inventory, load_sources, read_explicit_text


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "composition: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline source composition; distribution remains unauthorized.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "platform-root", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        raw, _ = read_explicit_text(explicit_relative_path(args.scope), 512 * 1024)
        scope = validate_scope(parse_json(raw, maximum=512 * 1024))
        ctx = load_sources(scope, {"termivar": args.termivar_root,
                                   "platform": args.platform_root}, identity(raw))
        inventory = build_inventory(ctx)
        ledger = read_dependencies(ctx, inventory)
        evidence = build_license_evidence(ctx, inventory, ledger)
        ledger["license_evidence"] = evidence
        ledger["counts"]["license_evidence_count"] = len(evidence)
        ledger["counts"]["unknown_license_subject_count"] = sum(
            row["declared_license"] is None or row["evidence_level"] == "conflicting_declarations"
            for row in evidence)
        constraints = build_constraints(inventory, ledger)
        ctx.check_stability()
        publish_composition(output, inventory, ledger, constraints)
    except InputError as error:
        print("composition: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError):
        print("composition: local_inventory_failed; no successful composition is claimed", file=sys.stderr)
        return 1
    print("Created demo source inventory, dependency/license ledger, constraints, Markdown and manifest")
    print(DEMO_LABEL)
    print("redistribution_authorized=false; build_verified=false; runtime_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
