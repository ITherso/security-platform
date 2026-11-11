"""Create one synthetic, source-bound, non-executable scope proposal bundle."""
from __future__ import annotations

import argparse
import hashlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_handoff.schema import InputError
from commercial_scope import DEMO_LABEL
from commercial_scope.capability_catalog import build_catalog, render_catalog
from commercial_scope.plan_builder import build_plan, render_summary
from commercial_scope.publisher import publish_scope
from commercial_scope.scope_contracts import json_bytes, load_proposal
from commercial_scope.scope_validator import preflight_to_dict, validate_scope
from commercial_scope.source_manifest import verify_sources


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "scope_planner: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Offline demo-only scope matching; never executes an assessment.",
                       allow_abbrev=False)
    parser.add_argument("--proposal", required=True)
    parser.add_argument("--termivar-source", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        proposal = load_proposal(args.proposal)
        snapshot = verify_sources(args.termivar_source)
        catalog = build_catalog(snapshot)
        catalog_raw = render_catalog(snapshot)
        catalog_digest = hashlib.sha256(catalog_raw).hexdigest()
        preflight = validate_scope(proposal.document, catalog)
        plan = build_plan(proposal, catalog, catalog_digest, preflight, snapshot)
        publish_scope(output, {
            "capability-catalog.json": catalog_raw,
            "scope-preflight.json": json_bytes(preflight_to_dict(preflight), maximum=256 * 1024),
            "assessment-plan-proposal.json": json_bytes(plan, maximum=256 * 1024),
            "assessment-plan-summary.md": render_summary(plan, preflight),
        }, proposal, snapshot)
    except InputError as error:
        print("scope_planner: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("scope_planner: local_preparation_failed; no successful output is claimed", file=sys.stderr)
        return 1
    print("Created capability catalog, scope preflight, non-executable plan, summary and manifest")
    print(DEMO_LABEL)
    print("demo_only=true; execution_authorized=false; authorization_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
