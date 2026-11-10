"""Read explicit existing artifacts and create a demo-only handoff input."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_handoff.schema import InputError
from commercial_intake.assessment_reader import read_assessment
from commercial_intake.handoff_adapter import render_handoff_input
from commercial_intake.source_mapping import build_source_mapping
from commercial_intake.provenance import (read_manifest, build_intake_manifest,
                                          publish_intake)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "assessment_intake: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Create a demo-only handoff input from an existing bounded assessment.", allow_abbrev=False)
    parser.add_argument("--assessment", required=True, help="One explicit cwd-relative existing assessment JSON.")
    parser.add_argument("--manifest", help="Optional, separately selected cwd-relative bundle manifest JSON.")
    parser.add_argument("--output-dir", required=True, help="New cwd-relative output directory; parent must exist.")
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        source = read_assessment(args.assessment)
        manifest_check = read_manifest(args.manifest, source)
        handoff = render_handoff_input(source)
        mapping = build_source_mapping(source, manifest_check)
        documents = {
            "handoff-input.json": handoff,
            "source-mapping.json": (json.dumps(mapping, ensure_ascii=False, sort_keys=True, indent=2) + "\n").encode("utf-8"),
        }
        metadata = build_intake_manifest(source, manifest_check, documents)
        publish_intake(output, documents, metadata)
    except InputError as error:
        print("assessment_intake: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError):
        print("assessment_intake: local_intake_failed; no successful conversion is claimed", file=sys.stderr)
        return 1
    print("Created demo-only intake: handoff-input.json, source-mapping.json, intake-manifest.json")
    print("demo_only=true; human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
