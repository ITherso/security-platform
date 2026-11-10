"""Prepare an offline, demo-only analyst packet from three explicit artifacts."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import output_location
from commercial_handoff.schema import InputError
from commercial_review.decision_overlay import make_empty_overlay
from commercial_review.manifest import publish_bundle
from commercial_review.packet_builder import (build_packet, load_prepare_sources,
                                               render_packet, render_worksheet)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "analyst_review: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Prepare a demo review packet; no human decision is created.", allow_abbrev=False)
    parser.add_argument("--handoff-input", required=True)
    parser.add_argument("--source-mapping", required=True)
    parser.add_argument("--intake-manifest", required=True)
    parser.add_argument("--output-dir", required=True, help="New cwd-relative directory; parent must exist.")
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        sources = load_prepare_sources(args.handoff_input, args.source_mapping, args.intake_manifest)
        packet = build_packet(sources)
        packet_bytes = render_packet(packet)
        overlay = make_empty_overlay(hashlib.sha256(packet_bytes).hexdigest(), packet.source_assessment.sha256)
        documents = {
            "review-packet.json": packet_bytes,
            "decision-overlay.template.json": (json.dumps(overlay, ensure_ascii=False, indent=2, sort_keys=True) + "\n").encode("utf-8"),
            "review-worksheet.md": render_worksheet(packet),
        }
        inputs = {name: {"sha256": getattr(sources.phase17_inputs, name).sha256,
                         "byte_length": getattr(sources.phase17_inputs, name).byte_length}
                  for name in ("handoff_input", "source_mapping", "intake_manifest")}
        publish_bundle(output, documents, "review-packet-manifest.json", {
            "inputs": inputs, "source_assessment_sha256": packet.source_assessment.sha256,
            "source_observation_count": len(packet.observations),
        })
    except InputError as error:
        print("analyst_review: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("analyst_review: local_preparation_failed; no successful packet is claimed", file=sys.stderr)
        return 1
    print("Created demo-only review packet, empty decision overlay, worksheet and manifest")
    print("DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED")
    print("human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
