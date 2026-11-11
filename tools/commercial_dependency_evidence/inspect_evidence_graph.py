"""Inspect five explicit generated files, without reopening source manifests."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_composition.artifact_manifest import identity
from commercial_composition.source_inventory import read_explicit_text
from commercial_dependency_evidence.artifact_manifest import manifest_data
from commercial_dependency_evidence.graph_renderer import render_summary
from commercial_dependency_evidence.evidence_contracts import (
    EVIDENCE_SCHEMA, GRAPH_SCHEMA, VARIANTS_SCHEMA, INSPECTION_SCHEMA, DEMO_LABEL,
    InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "dependency_evidence_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Inspect internal source evidence metadata; no original-source or build acceptance.", allow_abbrev=False)
    for name in ("evidence", "graph", "variants", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        for role, maximum in (("evidence", 4 * 1024 * 1024), ("graph", 4 * 1024 * 1024),
                              ("variants", 4 * 1024 * 1024), ("summary", 512 * 1024), ("manifest", 64 * 1024)):
            raw[role], _ = read_explicit_text(explicit_relative_path(getattr(args, role)), maximum)
        evidence, graph, variants = (parse_json(raw[key]) for key in ("evidence", "graph", "variants"))
        for doc, schema in ((evidence, EVIDENCE_SCHEMA), (graph, GRAPH_SCHEMA), (variants, VARIANTS_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                print("dependency_evidence_inspection: unsupported_contract", file=sys.stderr)
                return 2
        # Closed validation recomputes every claimed derived relationship from
        # the retained bounded metadata; it performs no original-source I/O.
        validate_documents(evidence, graph, variants)
        if raw["summary"] != render_summary(evidence, graph, variants):
            raise InputError("dependency_evidence_summary_projection_mismatch")
        payloads = {"direct-dependency-evidence.json": raw["evidence"], "source-evidence-graph.json": raw["graph"],
                    "variant-dependency-evidence.json": raw["variants"], "dependency-evidence-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=64 * 1024)) != json_bytes(
                manifest_data(evidence, graph, variants, payloads)):
            raise InputError("dependency_evidence_manifest_mismatch")
        report = {**common(INSPECTION_SCHEMA, evidence["source_reference"]),
                  "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "evidence_counts": evidence["counts"], "graph_counts": graph["counts"],
                  "variant_count": len(variants["variants"]),
                  "original_phase24_phase26_files_read": False, "original_source_manifests_read": False,
                  "source_producer_verified": False, "legal_review_performed": False,
                  "inspection_scope": "five_explicit_generated_files_and_recomputable_metadata_relationships_only",
                  "integrity_limit": "Internal projected identity, ownership, binding, inheritance, graph and summary consistency only; raw TOML truth, source authority, resolution, target/features, build, runtime and legal permission are not independently verified."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("dependency_evidence_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("dependency_evidence_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("dependency_evidence_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo dependency evidence inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("original_source_manifests_read=false; dependency_resolution_performed=false; redistribution_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
