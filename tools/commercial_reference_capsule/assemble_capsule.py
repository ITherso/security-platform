"""Owner-validate four Phase32 inputs and publish one portable demo capsule."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE))
sys.path.insert(1, str(_HERE.parent))

from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.composition_adapter import ReadBudget
from capsule_contracts import (
    InputError, DEMO_LABEL, MAX_REQUEST_BYTES, MAX_TOTAL_INPUT_BYTES, BINDINGS_SCHEMA,
    common, json_bytes, parse_json, validate_request,
)
from phase32_adapter import load_validated_snapshot
from capsule_builder import create_capsule
from capsule_manifest import zip_bytes, assembly_manifest, publish_assembly
from capsule_renderer import render_assembly_summary


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "reference_capsule_assembly: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline demo capsule; no current source or producer verification.", allow_abbrev=False)
    for name in ("response", "selection", "source-summary", "source-manifest", "request", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        budget = ReadBudget(maximum=MAX_TOTAL_INPUT_BYTES)
        request = validate_request(parse_json(
            budget.read(explicit_relative_path(args.request), MAX_REQUEST_BYTES), maximum=MAX_REQUEST_BYTES))
        snapshot = load_validated_snapshot({"response": args.response, "selection": args.selection,
                                            "summary": args.source_summary, "manifest": args.source_manifest}, budget)
        capsule = create_capsule(snapshot, request)
        bindings = common(BINDINGS_SCHEMA, capsule["capsule_reference"], capsule["source_bindings"])
        payloads = {"guarded-reference-capsule.zip": zip_bytes(capsule),
                    "capsule-source-bindings.json": json_bytes(bindings),
                    "capsule-assembly-summary.md": render_assembly_summary(capsule)}
        documents = {**payloads, "assembly-manifest.json": json_bytes(assembly_manifest(capsule, payloads))}
        budget.check_stability()
        publish_assembly(args.output_dir, documents)
    except FileNotFoundError:
        print("reference_capsule_assembly: missing_explicit_input", file=sys.stderr)
        return 2
    except InputError:
        print("reference_capsule_assembly: contract_or_boundary_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError,
            RecursionError, StopIteration, OverflowError):
        print("reference_capsule_assembly: content_rejected; no complete delivery claimed", file=sys.stderr)
        return 1
    print("Created demo capsule, source bindings, summary and assembly manifest")
    print(DEMO_LABEL)
    print("source_files_reobserved=false; upstream_guard_independently_verified=false; production_ready=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
