"""Create a standalone offline desk from explicit Phase18 artifacts."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_handoff.schema import InputError
from commercial_review_desk.desk_projection import build_projection, load_desk_sources
from commercial_review_desk.desk_renderer import render_desk
from commercial_review_desk.manifest import publish_desk


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "review_desk: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Prepare a local-only, demo analyst review HTML document.", allow_abbrev=False)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--packet-manifest", required=True)
    parser.add_argument("--overlay-template", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        sources = load_desk_sources(args.review_packet, args.packet_manifest, args.overlay_template)
        projection = build_projection(sources)
        html = render_desk(projection)
        inputs = {role: {"sha256": loaded.sha256, "byte_length": loaded.byte_length}
                  for role, loaded in (("review_packet", sources.packet_file),
                                       ("packet_manifest", sources.manifest_file),
                                       ("overlay_template", sources.template_file))}
        publish_desk(output, {"review-desk.html": html}, "prepare_desk", {
            "inputs": inputs, "source_assessment_digest": sources.packet.source_assessment.sha256,
            "observation_count": len(sources.packet.observations), "decision_count": 0,
        })
    except InputError as error:
        print("review_desk: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("review_desk: local_preparation_failed; no successful output is claimed", file=sys.stderr)
        return 1
    print("Created demo-only standalone review-desk.html and desk-manifest.json")
    print("human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
