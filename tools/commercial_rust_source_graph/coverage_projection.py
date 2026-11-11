"""Pure F-catalog/EPF projection; no inventory update or module resolution."""
from __future__ import annotations

from copy import deepcopy

from .source_graph_contracts import COVERAGE_SCHEMA, InputError, LIMITATIONS, common


def _index(rows: list, key: str) -> dict:
    result = {}
    for row in rows:
        if row[key] in result:
            raise InputError("rust_source_coverage_duplicate_reference")
        result[row[key]] = row
    return result


def build_projection(ledger: dict, graph: dict) -> dict:
    parent = ledger["parent_context"]
    context = parent["phase24_context"]
    summaries = _index(ledger["lexical_summaries"], "source_file_reference")
    bindings = _index(ledger["bindings"], "reference_id")
    entries = _index(parent["phase28_entrypoints"], "source_file_reference")
    catalog = {}
    for row in context["files"]:
        key = (row["root_id"], row["path"])
        if key in catalog:
            raise InputError("rust_source_coverage_duplicate_catalog_path")
        catalog[key] = row
    graph_sources, graph_references = {}, {}
    for node in graph["nodes"]:
        if node["node_type"] in ("entrypoint_source", "allowlisted_source_file"):
            graph_sources[node["source_reference_id"]] = node["node_id"]
        elif node["node_type"] == "static_reference":
            graph_references[node["source_reference_id"]] = node["node_id"]
    source_files = []
    for source in ledger["source_files"]:
        source_id = source["source_file_reference"]
        old = catalog.get((source["root_id"], source["path"]))
        entry = entries.get(source_id)
        component_ids = ([] if old is None else [row["component_id"] for row in context["components"]
                                                if old["file_id"] in row["source_file_refs"]])
        identity_status = "not_in_catalog" if old is None else "not_compared"
        inventory_status = "source_read_not_performed"
        if source["read_status"] == "present_and_hashed":
            if old is None:
                inventory_status = "source_present_inventory_gap"
            elif old["bytes"] == source["observed_byte_size"] and old["sha256"] == source["observed_sha256"]:
                identity_status, inventory_status = "matched", "catalog_identity_matched"
            else:
                identity_status, inventory_status = "mismatch", "source_identity_mismatch"
        elif old is not None:
            inventory_status = "catalog_identity_not_compared"
        proposal_refs = [row["proposal_reference"] for row in parent["phase28_deltas"]
                         if entry is not None and row["source_file_reference"] == entry["entrypoint_reference"]
                         and all(row[key] == source[key] for key in ("root_id", "pinned_commit", "path"))]
        summary = summaries.get(source_id)
        source_files.append({"source_file_reference": source_id,
                             "entrypoint_reference": None if entry is None else entry["entrypoint_reference"],
                             "root_id": source["root_id"], "pinned_commit": source["pinned_commit"], "path": source["path"],
                             "observed_byte_size": source["observed_byte_size"], "observed_sha256": source["observed_sha256"],
                             "read_status": source["read_status"],
                             "lexical_status": "not_performed" if summary is None else summary["lexical_status"],
                             "phase24_source_reference": None if old is None else old["file_id"],
                             "phase24_catalog_status": "not_listed_in_global_f_catalog" if old is None else "listed_in_global_f_catalog",
                             "phase24_identity_status": identity_status,
                             "component_source_status": "referenced_by_component" if component_ids else "not_referenced_by_component",
                             "referencing_component_ids": component_ids, "source_inventory_status": inventory_status,
                             "phase28_target_reference": None if entry is None else entry["target_reference"],
                             "component_ownership_status": "component_ownership_unresolved",
                             "phase28_proposal_references": proposal_refs,
                             "graph_node_reference": graph_sources[source_id]})
    references = []
    for reference in ledger["references"]:
        ref_id = reference["reference_id"]
        binding = bindings[ref_id]
        node_id = graph_references[ref_id]
        edges = [row["edge_id"] for row in graph["edges"] if node_id in (row["from_node_id"], row["to_node_id"])]
        reasons = list(dict.fromkeys([*reference["reason_codes"], *binding["reason_codes"]]))
        references.append({"reference_id": ref_id, "source_file_reference": reference["source_file_reference"],
                           "reference_kind": reference["reference_kind"], "graph_node_reference": node_id,
                           "condition_status": "condition_declared_evaluation_not_performed" if reference["condition_ids"] else "not_declared",
                           "evaluation_status": "not_performed", "has_explicit_literal_path": reference["literal_relative_path"] is not None,
                           "binding_status": binding["binding_status"], "bound_source_file_reference": binding["bound_file_reference"],
                           "candidate_source_file_references": deepcopy(binding["candidate_file_references"]),
                           "unresolved_reason_codes": reasons, "graph_edge_references": edges})
    kinds = [row["reference_kind"] for row in ledger["references"]]
    counts = {"source_file_count": len(source_files), "entrypoint_source_file_count": len(entries),
              "present_and_hashed_source_file_count": sum(row["read_status"] == "present_and_hashed" for row in source_files),
              "missing_source_file_count": sum(row["read_status"] == "declared_file_missing" for row in source_files),
              "source_reference_count": len(references), "external_module_reference_count": kinds.count("external_module_declaration"),
              "inline_module_reference_count": kinds.count("inline_module_declaration"),
              "explicit_literal_reference_count": sum(row["reference_kind"] in ("explicit_path_module_declaration", "literal_include_reference")
                                                       and row["literal_relative_path"] is not None for row in ledger["references"]),
              "bound_reference_count": sum(row["binding_status"] == "bound_to_observed_file" for row in references),
              "unresolved_reference_count": sum(row["binding_status"] not in ("bound_to_observed_file", "inline_not_external") for row in references),
              "conditional_reference_count": sum(bool(row["condition_ids"]) for row in ledger["references"]),
              "phase28_unapplied_delta_count": len(parent["phase28_deltas"]), "global_f_catalog_count": len(context["files"]),
              "component_referenced_file_count": len({ref for row in context["components"] for ref in row["source_file_refs"]}),
              "files_not_in_global_f_catalog_count": sum(row["phase24_catalog_status"] == "not_listed_in_global_f_catalog" for row in source_files),
              "files_with_identity_mismatch_count": sum(row["phase24_identity_status"] == "mismatch" for row in source_files),
              **{key: context[key] for key in ("source_dependency_record_count", "source_ambiguous_dependency_record_count", "source_definite_owner_count")}}
    return {**common(COVERAGE_SCHEMA, ledger["source_reference"]), "source_files": source_files,
            "reference_coverage": references, "phase28_entrypoints": deepcopy(parent["phase28_entrypoints"]),
            "phase28_deltas": deepcopy(parent["phase28_deltas"]), "counts": counts,
            "license_boundary_counts": deepcopy(context["license_boundary_counts"]), "limitations": list(LIMITATIONS)}


__all__ = ("build_projection",)
