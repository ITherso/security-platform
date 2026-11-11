"""Extract bounded static Rust references without a compiler or module resolver."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from commercial_handoff.input_loader import explicit_relative_path, output_location
from commercial_pilot_variants.composition_adapter import ReadBudget
from commercial_rust_source_graph.source_graph_contracts import InputError, DEMO_LABEL, parse_json, validate_scope
from commercial_rust_source_graph.coverage_adapter import load_context
from commercial_rust_source_graph.rust_reference_reader import read_sources
from commercial_rust_source_graph.rust_reference_lexer import lex_source
from commercial_rust_source_graph.static_reference_classifier import classify_source
from commercial_rust_source_graph.source_file_binding import build_ledger
from commercial_rust_source_graph.module_evidence_graph import build_graph
from commercial_rust_source_graph.coverage_projection import build_projection
from commercial_rust_source_graph.artifact_manifest import publish_graph


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "rust_source_graph: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(description="Offline static reference metadata; no source discovery, Rust compiler or closure approval.", allow_abbrev=False)
    for name in ("scope", "termivar-root", "output-dir"):
        parser.add_argument("--" + name, required=True)
    args = parser.parse_args(argv)
    try:
        output = output_location(args.output_dir)
        artifact_budget = ReadBudget(maximum=12 * 1024 * 1024)
        raw_scope = artifact_budget.read(explicit_relative_path(args.scope), 128 * 1024)
        scope = validate_scope(parse_json(raw_scope, maximum=128 * 1024))
        reference, parent_context = load_context(scope, artifact_budget)
        source_budget = ReadBudget(maximum=1024 * 1024, identities=artifact_budget.identities)
        raw_by_id, sources = read_sources(scope, args.termivar_root, source_budget)
        summaries, references, conditions, diagnostics = [], [], [], []
        total_tokens = 0
        for source in sources:
            if source["read_status"] != "present_and_hashed":
                raise InputError("rust_source_required_file_missing_no_lexical_success")
            identity = {"source_id": source["source_file_reference"], "root_id": source["root_id"],
                        "pinned_commit": source["pinned_commit"], "path": source["path"],
                        "observed_bytes": source["observed_byte_size"], "observed_sha256": source["observed_sha256"]}
            raw = raw_by_id[source["source_file_reference"]]
            lexed = lex_source(raw, identity)
            result = classify_source(raw, identity, lexed)
            summaries.append(result["lexical_summary"])
            references.extend(result["references"])
            conditions.extend(result["conditions"])
            diagnostics.extend(result["diagnostics"])
            total_tokens += result["lexical_summary"]["token_count"]
            if total_tokens > 750_000 or len(references) > 2048 or len(conditions) > 4096 or len(diagnostics) > 4096:
                raise InputError("rust_source_aggregate_lexical_budget_exceeded")
            del raw, lexed, result
        del raw_by_id
        ledger = build_ledger(reference, parent_context, sources, summaries, references, conditions, diagnostics)
        graph = build_graph(ledger)
        coverage = build_projection(ledger, graph)
        artifact_budget.check_stability()
        source_budget.check_stability()
        publish_graph(output, ledger, graph, coverage)
    except InputError:
        print("rust_source_graph: closed_contract_source_or_lexical_budget_rejected; no successful delivery is claimed", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError, IndexError, RecursionError):
        print("rust_source_graph: local_source_preparation_failed; no successful delivery is claimed", file=sys.stderr)
        return 1
    print("Created demo Rust source-reference ledger, evidence graph, coverage projection, Markdown and manifest")
    print(DEMO_LABEL)
    print("module_closure_verified=false; source_inventory_updated=false; component_ownership_verified=false; build_verified=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
