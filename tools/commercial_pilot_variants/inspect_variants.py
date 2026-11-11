"""Inspect five explicit generated files; never reopen Phase24/25 or sources."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_composition.artifact_manifest import identity
from commercial_composition.source_inventory import read_explicit_text
from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.artifact_manifest import manifest_data
from commercial_pilot_variants.output_renderer import render_summary
from commercial_pilot_variants.variant_contracts import (
    ANALYSIS_SCHEMA, DEPENDENCIES_SCHEMA, LICENSES_SCHEMA, DEMO_LABEL, INSPECTION_SCHEMA,
    InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "pilot_variant_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Internal metadata consistency only; no original-source or release acceptance.", allow_abbrev=False)
    for name in ("analysis", "dependencies", "licenses", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        for role, maximum in (("analysis", 4 * 1024 * 1024), ("dependencies", 4 * 1024 * 1024),
                              ("licenses", 4 * 1024 * 1024), ("summary", 512 * 1024), ("manifest", 64 * 1024)):
            raw[role], _ = read_explicit_text(explicit_relative_path(getattr(args, role)), maximum)
        analysis, dependencies, licenses = (parse_json(raw[key]) for key in ("analysis", "dependencies", "licenses"))
        for doc, schema in ((analysis, ANALYSIS_SCHEMA), (dependencies, DEPENDENCIES_SCHEMA), (licenses, LICENSES_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                print("pilot_variant_inspection: unsupported_contract", file=sys.stderr)
                return 2
        validate_documents(analysis, dependencies, licenses)
        # Closed cross-document validation also recomputes all three pure
        # projections from the retained metadata. It performs no file I/O.
        if raw["summary"] != render_summary(analysis, dependencies, licenses):
            raise InputError("pilot_variant_markdown_projection_mismatch")
        payloads = {"variant-analysis.json": raw["analysis"], "dependency-exposure.json": raw["dependencies"],
                    "license-readiness.json": raw["licenses"], "variant-comparison.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=64 * 1024)) != json_bytes(
                manifest_data(analysis, dependencies, licenses, payloads)):
            raise InputError("pilot_variant_manifest_mismatch")
        report = {**common(INSPECTION_SCHEMA, analysis["candidate_reference"]),
                  "source_reference": analysis["source_reference"],
                  "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "source_counts": analysis["source_counts"],
                  "variant_count": len(analysis["variants"]), "comparison_count": len(analysis["comparisons"]),
                  "original_phase24_phase25_files_read": False, "original_evidence_files_read": False,
                  "source_producer_verified": False, "legal_review_performed": False,
                  "inspection_scope": "five_explicit_generated_files_and_recomputable_metadata_projections_only",
                  "integrity_limit": "Projected metadata and declared byte identities only; original record digests, source authenticity, dependency closure, legal permission, build and runtime are not independently authenticated."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("pilot_variant_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("pilot_variant_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("pilot_variant_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo pilot variant inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("original_phase24_phase25_files_read=false; dependency_closure_verified=false; redistribution_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
