"""Assemble one demo case-status projection from explicitly selected files."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_case.artifact_reader import load_case_artifacts
from commercial_case.bundle_writer import write_case_bundle
from commercial_case.case_contracts import DEMO_LABEL, InputError
from commercial_case.case_map import load_case_map
from commercial_case.relationship_graph import build_relationship_graph
from commercial_case.safe_projection import build_projection


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "case_bundle: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline demo case-status bundle; no execution or release authority.",
                       allow_abbrev=False)
    parser.add_argument("--workspace-root", required=True)
    parser.add_argument("--case-map", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        case_map = load_case_map(args.case_map, args.workspace_root)
        selected = load_case_artifacts(case_map, args.workspace_root)
        evidence = build_relationship_graph(selected)
        projection = build_projection(case_map.case_reference, evidence)
        write_case_bundle(output, projection, case_map.sha256, case_map.byte_length)
    except InputError as error:
        print("case_bundle: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("case_bundle: local_preparation_failed; no successful output is claimed", file=sys.stderr)
        return 1
    print("Created demo case ZIP, outer manifest and assembly summary")
    print(DEMO_LABEL)
    print("execution_binding=not_established; human_review_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
