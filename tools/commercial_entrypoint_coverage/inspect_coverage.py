"""Inspect only five explicit new output files, without original-source reads."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_composition.artifact_manifest import identity
from commercial_entrypoint_coverage.artifact_manifest import manifest_data
from commercial_entrypoint_coverage.output_renderer import render_summary
from commercial_entrypoint_coverage.coverage_contracts import (
    COVERAGE_SCHEMA, DELTA_SCHEMA, VARIANTS_SCHEMA, INSPECTION_SCHEMA, DEMO_LABEL,
    InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "entrypoint_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Internal consistency only, never original-source or release acceptance.", allow_abbrev=False)
    for name in ("coverage", "delta", "variants", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        budget = ReadBudget(maximum=12 * 1024 * 1024)
        for role, maximum in (("coverage", 2 * 1024 * 1024), ("delta", 2 * 1024 * 1024),
                              ("variants", 2 * 1024 * 1024), ("summary", 256 * 1024), ("manifest", 128 * 1024)):
            raw[role] = budget.read(explicit_relative_path(getattr(args, role)), maximum)
        coverage, delta, variants = (parse_json(raw[key]) for key in ("coverage", "delta", "variants"))
        for doc, schema in ((coverage, COVERAGE_SCHEMA), (delta, DELTA_SCHEMA), (variants, VARIANTS_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                print("entrypoint_inspection: unsupported_contract", file=sys.stderr)
                return 2
        validate_documents(coverage, delta, variants)
        if raw["summary"] != render_summary(coverage, delta, variants):
            raise InputError("entrypoint_summary_projection_mismatch")
        payloads = {"entrypoint-coverage.json": raw["coverage"], "source-scope-delta.json": raw["delta"],
                    "variant-entrypoint-projection.json": raw["variants"], "entrypoint-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=128 * 1024)) != json_bytes(
                manifest_data(coverage, delta, variants, payloads)):
            raise InputError("entrypoint_manifest_mismatch")
        budget.check_stability()
        report = {**common(INSPECTION_SCHEMA, coverage["source_reference"]),
                  "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "coverage_counts": coverage["counts"], "delta_counts": delta["counts"],
                  "variant_count": len(variants["variants"]),
                  "original_phase24_phase26_phase27_files_read": False,
                  "original_source_manifests_read": False, "original_target_files_read": False,
                  "source_producer_verified": False, "legal_review_performed": False,
                  "inspection_scope": "five_explicit_generated_files_and_recomputable_metadata_relationships_only",
                  "integrity_limit": "Internal reference, coverage, delta, ownership-limit, variant and summary consistency only. Source bytes, pinned Git attestation, producer, build, runtime and release permission are not independently verified."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("entrypoint_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("entrypoint_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("entrypoint_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo entry-point inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("original_target_files_read=false; component_ownership_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
