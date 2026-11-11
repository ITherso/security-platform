"""Inspect five new metadata files; never import the Rust lexer or read sources."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_case.bundle_reader import publish_inspection
from commercial_handoff.input_loader import explicit_relative_path
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_composition.artifact_manifest import identity
from commercial_rust_source_graph.artifact_manifest import manifest_data
from commercial_rust_source_graph.output_renderer import render_summary
from commercial_rust_source_graph.source_graph_contracts import (
    LEDGER_SCHEMA, GRAPH_SCHEMA, COVERAGE_SCHEMA, INSPECTION_SCHEMA, DEMO_LABEL,
    InputError, common, json_bytes, parse_json, validate_documents,
)


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "rust_source_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Internal metadata consistency only, never independent lexical or compiler acceptance.", allow_abbrev=False)
    for name in ("ledger", "graph", "coverage", "summary", "manifest", "output"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        raw = {}
        budget = ReadBudget(maximum=12 * 1024 * 1024)
        for role, maximum in (("ledger", 2 * 1024 * 1024), ("graph", 2 * 1024 * 1024), ("coverage", 2 * 1024 * 1024),
                              ("summary", 256 * 1024), ("manifest", 128 * 1024)):
            raw[role] = budget.read(explicit_relative_path(getattr(args, role)), maximum)
        ledger, graph, coverage = (parse_json(raw[key]) for key in ("ledger", "graph", "coverage"))
        for doc, schema in ((ledger, LEDGER_SCHEMA), (graph, GRAPH_SCHEMA), (coverage, COVERAGE_SCHEMA)):
            if type(doc) is not dict or doc.get("schema_version") != schema:
                print("rust_source_inspection: unsupported_contract", file=sys.stderr)
                return 2
        validate_documents(ledger, graph, coverage)
        if raw["summary"] != render_summary(ledger, graph, coverage):
            raise InputError("rust_source_summary_projection_mismatch")
        payloads = {"source-reference-ledger.json": raw["ledger"], "source-evidence-graph.json": raw["graph"],
                    "module-coverage-projection.json": raw["coverage"], "source-graph-summary.md": raw["summary"]}
        if json_bytes(parse_json(raw["manifest"], maximum=128 * 1024)) != json_bytes(manifest_data(ledger, graph, coverage, payloads)):
            raise InputError("rust_source_manifest_mismatch")
        budget.check_stability()
        report = {**common(INSPECTION_SCHEMA, ledger["source_reference"]), "internal_content_status": "content_consistent",
                  "input_files": [{"role": role, **identity(value)} for role, value in raw.items()],
                  "ledger_counts": ledger["counts"], "graph_counts": graph["counts"], "coverage_counts": coverage["counts"],
                  "original_phase24_phase27_phase28_files_read": False, "original_rust_files_read": False,
                  "lexer_reexecuted": False, "independent_lexical_correctness_verified": False,
                  "source_producer_verified": False, "legal_review_performed": False,
                  "inspection_scope": "five_explicit_new_files_and_recomputable_metadata_relationships_only",
                  "integrity_limit": "Internal identity, references, bindings, graph, coverage and summary consistency only; original Rust lexical truth, AST/module resolution, producer/pinned Git attestation, build/runtime and release authority are not independently verified."}
        publish_inspection(args.output, report)
    except FileNotFoundError:
        print("rust_source_inspection: missing_required_output", file=sys.stderr)
        return 2
    except InputError:
        print("rust_source_inspection: content_inconsistent", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("rust_source_inspection: content_inconsistent; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created demo Rust source graph inspection; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("original_rust_files_read=false; lexer_reexecuted=false; module_closure_verified=false; release_authorized=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
