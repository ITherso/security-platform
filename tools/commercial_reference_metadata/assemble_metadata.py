"""Consume explicit Phase31 guard decisions without partial reference disclosure."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_reference_metadata.consumer_contracts import InputError, DEMO_LABEL, MAX_TOTAL_INPUT_BYTES, MAX_REQUEST_BYTES, parse_json, validate_request
from commercial_reference_metadata.revalidation_adapter import load_validated_snapshot
from commercial_reference_metadata.reference_consumer import create_reference_metadata_response, build_selection
from commercial_reference_metadata.artifact_manifest import publish_metadata


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "reference_metadata: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline minimized reference metadata from recorded guard decisions; no new source observation.", allow_abbrev=False)
    for name in ("ledger", "reuse", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        budget = ReadBudget(maximum=MAX_TOTAL_INPUT_BYTES)
        request = validate_request(parse_json(budget.read(explicit_relative_path(args.request), MAX_REQUEST_BYTES), maximum=MAX_REQUEST_BYTES))
        snapshot = load_validated_snapshot({"ledger": args.ledger, "reuse": args.reuse,
                                            "summary": args.source_summary, "manifest": args.source_manifest}, budget)
        response = create_reference_metadata_response(snapshot, request)
        selection = build_selection(response, request)
        budget.check_stability()
        publish_metadata(output, response, selection)
    except InputError:
        print("reference_metadata: closed_request_source_or_guard_contract_rejected; no successful response is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError, StopIteration):
        print("reference_metadata: local_preparation_failed; no successful response is claimed", file=sys.stderr)
        return 1
    print("Created demo minimized reference metadata response, selection, Markdown and manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; reference_context_revalidated=false; independent_observation_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
