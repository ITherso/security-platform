"""Pure metadata binding; a module name never supplies an inferred file path."""
from __future__ import annotations

import copy
from collections import Counter

from .source_graph_contracts import (
    LEDGER_SCHEMA, REFERENCE_KINDS, BINDING_STATUSES, LIMITATIONS, InputError,
    common, record_digest, relative_path, validate_inputs,
)


def bind_references(source_files: list, references: list) -> list:
    files = {row["source_file_reference"]: row for row in source_files}
    by_path = {(row["root_id"], row["pinned_commit"], row["path"]): row for row in source_files}
    bindings = []
    for ref in references:
        source = files[ref["source_file_reference"]]
        kind, interpretation = ref["reference_kind"], ref["interpretation_status"]
        literal, normalized, candidates, bound = ref["literal_relative_path"], None, [], None
        status, reasons = "unsupported_reference", ["unsupported_static_reference"]
        if kind == "dynamic_reference_unresolved" or interpretation == "dynamic_reference_unresolved":
            status, reasons = "dynamic_reference_unresolved", ["dynamic_include_not_evaluated"]
        elif interpretation == "conditional_path_unresolved":
            status, reasons = "conditional_path_unresolved", ["conditional_path_not_established"]
        elif interpretation == "path_resolution_context_unresolved":
            status, reasons = "path_resolution_context_unresolved", ["relative_path_context_not_established"]
        elif interpretation in ("attribute_binding_unresolved", "macro_context_unresolved", "unsupported_reference") or kind == "unsupported_reference":
            status, reasons = "unsupported_reference", ["unsupported_static_reference"]
        elif kind == "inline_module_declaration":
            status, reasons = "inline_not_external", ["inline_module_has_no_external_file"]
        elif ref["context_reliability"] != "lexically_bounded":
            status, reasons = "lexical_boundary_unresolved", ["lexical_context_not_established"]
        elif kind == "external_module_declaration" and literal is None:
            status, reasons = "external_module_path_unresolved", ["module_file_resolution_not_performed"]
        elif literal is not None:
            if ref["lexical_scope"] or interpretation == "path_resolution_context_unresolved":
                status, reasons = "path_resolution_context_unresolved", ["relative_path_context_not_established"]
            else:
                try:
                    relative_path(literal, "literal_reference_path")
                    directory = source["path"].rsplit("/", 1)[0] if "/" in source["path"] else ""
                    normalized = relative_path((directory + "/" if directory else "") + literal, "normalized_literal_path")
                except InputError:
                    status, reasons = "path_resolution_context_unresolved", ["unsafe_literal_path"]
                else:
                    target = by_path.get((source["root_id"], source["pinned_commit"], normalized))
                    if target is not None:
                        candidates = [target["source_file_reference"]]
                    if target is None:
                        status, reasons = "not_allowlisted", ["explicit_literal_path_not_allowlisted"]
                    elif target["read_status"] == "declared_file_missing":
                        status, reasons = "file_missing", ["allowlisted_file_missing"]
                    elif (target["read_status"] == "present_and_hashed" and target["regular_file"] is True
                          and target["observed_sha256"] == target["expected_sha256"]
                          and target["observed_byte_size"] == target["expected_bytes"]):
                        bound = target["source_file_reference"]
                        status, reasons = "bound_to_observed_file", ["observed_file_identity_bound"]
                    else:
                        raise InputError("rust_source_observed_file_identity_not_bound")
        if ref["condition_ids"]:
            reasons.append("condition_evaluation_not_performed")
        bindings.append({"binding_id": "binding-" + record_digest({"reference_id": ref["reference_id"]}),
                         "reference_id": ref["reference_id"], "source_file_reference": ref["source_file_reference"],
                         "literal_relative_path": literal, "normalized_relative_path": normalized,
                         "candidate_file_references": candidates, "bound_file_reference": bound,
                         "binding_status": status, "condition_ids": copy.deepcopy(ref["condition_ids"]),
                         "reason_codes": reasons})
    return bindings


def build_ledger(reference: dict, parent_context: dict, source_files: list, lexical_summaries: list,
                 references: list, conditions: list, diagnostics: list) -> dict:
    validate_inputs(parent_context, source_files, lexical_summaries, references, conditions, diagnostics)
    bindings = bind_references(source_files, references)
    kinds = Counter(row["reference_kind"] for row in references)
    statuses = Counter(row["binding_status"] for row in bindings)
    counts = {
        "source_file_count": len(source_files),
        "present_source_file_count": sum(row["read_status"] == "present_and_hashed" for row in source_files),
        "missing_source_file_count": sum(row["read_status"] == "declared_file_missing" for row in source_files),
        "observed_source_bytes": sum(row["observed_byte_size"] or 0 for row in source_files),
        "lexically_bounded_file_count": sum(row["lexical_status"] == "lexically_bounded" for row in lexical_summaries),
        "partial_unverified_file_count": sum(row["lexical_status"] != "lexically_bounded" for row in lexical_summaries),
        "token_count": sum(row["token_count"] for row in lexical_summaries),
        "reference_count": len(references), "external_module_count": kinds["external_module_declaration"],
        "inline_module_count": kinds["inline_module_declaration"],
        "explicit_literal_reference_count": sum(row["reference_kind"] in ("explicit_path_module_declaration", "literal_include_reference")
                                                and row["literal_relative_path"] is not None for row in references),
        "conditional_reference_count": sum(bool(row["condition_ids"]) for row in references),
        "condition_count": len(conditions), "diagnostic_count": len(diagnostics),
        "bound_file_reference_count": statuses["bound_to_observed_file"],
        "unresolved_reference_count": sum(row["binding_status"] not in ("bound_to_observed_file", "inline_not_external") for row in bindings),
        "by_reference_kind": [{"reference_kind": kind, "reference_count": kinds[kind]} for kind in REFERENCE_KINDS],
        "by_binding_status": [{"binding_status": status, "reference_count": statuses[status]} for status in BINDING_STATUSES],
    }
    return {**common(LEDGER_SCHEMA, reference), "parent_context": copy.deepcopy(parent_context),
            "source_files": copy.deepcopy(source_files), "lexical_summaries": copy.deepcopy(lexical_summaries),
            "references": copy.deepcopy(references), "conditions": copy.deepcopy(conditions),
            "diagnostics": copy.deepcopy(diagnostics), "bindings": bindings, "counts": counts,
            "limitations": list(LIMITATIONS)}


def rebuild_ledger(ledger: dict) -> dict:
    return build_ledger(ledger["source_reference"], ledger["parent_context"], ledger["source_files"],
                        ledger["lexical_summaries"], ledger["references"], ledger["conditions"], ledger["diagnostics"])
