"""Reconcile an explicitly supplied overlay without running the handoff builder."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import load_input, output_location
from commercial_handoff.schema import InputError
from commercial_review.review_contracts import load_review_json, validate_packet
from commercial_review.decision_overlay import validate_overlay
from commercial_review.handoff_reconciler import (reconcile_handoff, render_reconciled_input,
                                                  render_reconciliation_report)
from commercial_review.manifest import publish_bundle, validate_packet_manifest


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "analyst_review: invalid_arguments\n")


def main(argv=None) -> int:
    parser = Arguments(description="Reconcile a demo-only review overlay; no approval or release is granted.", allow_abbrev=False)
    parser.add_argument("--review-packet", required=True)
    parser.add_argument("--packet-manifest", required=True)
    parser.add_argument("--handoff-input", required=True)
    parser.add_argument("--overlay", required=True)
    parser.add_argument("--output-dir", required=True, help="New cwd-relative directory; parent must exist.")
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        packet_file = load_review_json(args.review_packet)
        packet = validate_packet(packet_file.data)
        manifest_file = load_review_json(args.packet_manifest, maximum=64 * 1024)
        validate_packet_manifest(manifest_file, packet_file)
        original = load_input(args.handoff_input)
        overlay_file = load_review_json(args.overlay)
        overlay = validate_overlay(overlay_file.data)
        result = reconcile_handoff(packet, original, overlay, packet_digest=packet_file.sha256)
        documents = {
            "handoff-input.json": render_reconciled_input(result),
            "review-reconciliation.md": render_reconciliation_report(result),
        }
        inputs = {name: {"sha256": value.sha256, "byte_length": value.byte_length}
                  for name, value in (("review_packet", packet_file), ("packet_manifest", manifest_file),
                                      ("handoff_input", original), ("overlay", overlay_file))}
        publish_bundle(output, documents, "reconciliation-manifest.json", {
            "inputs": inputs, "source_assessment_sha256": packet.source_assessment.sha256,
            "source_observation_count": len(packet.observations),
        })
    except InputError as error:
        print("analyst_review: " + str(error), file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError):
        print("analyst_review: local_reconciliation_failed; no successful reconciliation is claimed", file=sys.stderr)
        return 1
    print("Created demo-only handoff input, reconciliation summary and manifest")
    print("DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED")
    print("human_review_verified=false; producer_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
