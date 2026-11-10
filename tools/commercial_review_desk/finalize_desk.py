"""Convert an explicit decision draft through the unchanged Phase18 binding."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import load_input, output_location
from commercial_handoff.schema import InputError
from commercial_review.manifest import validate_packet_manifest
from commercial_review.review_contracts import load_review_json, validate_packet
from commercial_review_desk.desk_projection import finalize_draft, render_overlay
from commercial_review_desk.manifest import publish_desk


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "review_desk: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Finalize a declared draft into a demo-only Phase18 overlay.", allow_abbrev=False)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--packet-manifest", required=True)
    parser.add_argument("--handoff-input", required=True, help="Explicit original Phase17 input required by existing Phase18 binding.")
    parser.add_argument("--decision-draft", required=True)
    parser.add_argument("--output-dir", required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        packet_file = load_review_json(args.review_packet)
        packet = validate_packet(packet_file.data)
        manifest_file = load_review_json(args.packet_manifest, maximum=64 * 1024)
        validate_packet_manifest(manifest_file, packet_file)
        original = load_input(args.handoff_input)
        draft_file = load_review_json(args.decision_draft)
        overlay = finalize_draft(packet_file, packet, original, draft_file)
        inputs = {role: {"sha256": loaded.sha256, "byte_length": loaded.byte_length}
                  for role, loaded in (("review_packet", packet_file), ("packet_manifest", manifest_file),
                                       ("handoff_input", original), ("decision_draft", draft_file))}
        publish_desk(output, {"decision-overlay.json": render_overlay(overlay)}, "finalize_desk", {
            "inputs": inputs, "source_assessment_digest": packet.source_assessment.sha256,
            "observation_count": len(packet.observations), "decision_count": len(overlay["decisions"]),
        })
    except InputError as error:
        print("review_desk: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("review_desk: local_finalization_failed; no successful overlay is claimed", file=sys.stderr)
        return 1
    print("Created demo-only decision-overlay.json and overlay-manifest.json")
    print("human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
