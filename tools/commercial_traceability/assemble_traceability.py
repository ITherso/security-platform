"""Inspect existing demo artifacts; never run or authorize an assessment."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_traceability.assessment_reader import load_assessment_bundle
from commercial_traceability.contracts import DEMO_LABEL, InputError, json_bytes
from commercial_traceability.manifest import publish_traceability
from commercial_traceability.plan_reader import load_plan_bundle
from commercial_traceability.renderer import render_summary
from commercial_traceability.source_binding import bind_source_mapping
from commercial_traceability.traceability import build_ledger, ledger_to_dict


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "traceability: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline source traceability for independent synthetic artifacts.",
                       allow_abbrev=False)
    for name in ("plan", "preflight", "catalog", "plan-manifest", "assessment",
                 "assessment-manifest", "source-mapping", "handoff-input",
                 "intake-manifest", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        plan = load_plan_bundle(args.plan, args.preflight, args.catalog, args.plan_manifest)
        assessment = load_assessment_bundle(args.assessment, args.assessment_manifest)
        binding = bind_source_mapping(assessment, args.source_mapping,
                                      args.handoff_input, args.intake_manifest)
        ledger = build_ledger(plan, assessment, binding)
        publish_traceability(output, {
            "traceability-ledger.json": json_bytes(ledger_to_dict(ledger)),
            "traceability-summary.md": render_summary(ledger),
        }, (*plan.source_files, *assessment.source_files, *binding.source_files))
    except InputError as error:
        print("traceability: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("traceability: local_preparation_failed; no successful output is claimed", file=sys.stderr)
        return 1
    print("Created demo traceability ledger, summary and manifest")
    print(DEMO_LABEL)
    print("execution_binding=not_established; plan_execution_verified=false; scope_fulfillment_verified=false")
    print("authorization_verified=false; human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
