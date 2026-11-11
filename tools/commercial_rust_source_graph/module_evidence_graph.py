"""Pure source-metadata graph; never resolve modules or discover source files."""
from __future__ import annotations

from collections import Counter

from .source_graph_contracts import (
    GRAPH_SCHEMA, InputError, LIMITATIONS, MAX_NODES, MAX_EDGES, common,
    record_digest,
)


NODE_TYPES = ("entrypoint_source", "allowlisted_source_file", "static_reference", "unresolved_reference")
EDGE_TYPES = (
    "source_contains_reference", "reference_explicitly_names_file", "reference_bound_to_observed_file",
    "reference_may_resolve_to_file", "reference_unresolved", "conditional_reference_unresolved",
)
CERTAINTIES = ("definite", "possible", "unresolved")
_RESOLVED_BINDING_STATUSES = ("inline_not_external", "bound_to_observed_file")


def source_fingerprint(row: dict) -> str:
    if row["observed_sha256"] is not None:
        return row["observed_sha256"]
    return record_digest({key: row[key] for key in (
        "source_file_reference", "root_id", "pinned_commit", "path", "read_status")})


def node_identifier(node_type: str, source_reference_id: str, fingerprint: str) -> str:
    return "node-" + record_digest({"node_type": node_type, "source_reference_id": source_reference_id,
                                     "source_fingerprint": fingerprint})


def edge_payload(edge_type: str, source: str, target: str, certainty: str, evidence_refs: list) -> dict:
    return {"edge_type": edge_type, "from_node_id": source, "to_node_id": target,
            "certainty": certainty, "evidence_refs": list(dict.fromkeys(evidence_refs))}


def _index(rows: list, key: str) -> dict:
    result = {}
    for row in rows:
        if row[key] in result:
            raise InputError("rust_source_graph_duplicate_reference")
        result[row[key]] = row
    return result


def build_graph(ledger: dict) -> dict:
    """Derive only recorded syntax, candidate bindings and unresolved metadata."""
    sources = _index(ledger["source_files"], "source_file_reference")
    references = _index(ledger["references"], "reference_id")
    bindings = _index(ledger["bindings"], "reference_id")
    entrypoints = {row["source_file_reference"] for row in ledger["parent_context"]["phase28_entrypoints"]}
    nodes, edges = [], []
    source_nodes, reference_nodes, unresolved_nodes = {}, {}, {}
    node_ids, edge_ids = set(), set()

    def add_node(kind: str, reference: str, fingerprint: str, label: str) -> str:
        identity = node_identifier(kind, reference, fingerprint)
        if identity in node_ids or len(nodes) >= MAX_NODES:
            raise InputError("rust_source_graph_node_limit_or_duplicate")
        node_ids.add(identity)
        nodes.append({"node_id": identity, "node_type": kind, "source_reference_id": reference,
                      "source_fingerprint": fingerprint, "label": label,
                      "evidence_status": "source_metadata_only"})
        return identity

    def add_edge(kind: str, source: str, target: str, certainty: str, evidence: list) -> None:
        if source not in node_ids or target not in node_ids:
            raise InputError("rust_source_graph_unknown_endpoint")
        payload = edge_payload(kind, source, target, certainty, evidence)
        fingerprint = record_digest(payload)
        identity = "edge-" + fingerprint
        if identity in edge_ids or len(edges) >= MAX_EDGES:
            raise InputError("rust_source_graph_edge_limit_or_duplicate")
        edge_ids.add(identity)
        edges.append({"edge_id": identity, **payload, "source_fingerprint": fingerprint})

    for source in ledger["source_files"]:
        source_id = source["source_file_reference"]
        kind = "entrypoint_source" if source_id in entrypoints else "allowlisted_source_file"
        source_nodes[source_id] = add_node(kind, source_id, source_fingerprint(source), source_id)
    for reference in ledger["references"]:
        ref_id = reference["reference_id"]
        label = reference["reference_kind"]
        if reference["declared_module_name"] is not None:
            label += ": " + reference["declared_module_name"]
        reference_nodes[ref_id] = add_node("static_reference", ref_id, record_digest(reference), label)
    for reference in ledger["references"]:
        ref_id = reference["reference_id"]
        binding = bindings.get(ref_id)
        if binding is None:
            raise InputError("rust_source_graph_missing_binding")
        if binding["binding_status"] not in _RESOLVED_BINDING_STATUSES or reference["condition_ids"]:
            fingerprint = record_digest({"reference_fingerprint": record_digest(reference),
                                         "binding_status": binding["binding_status"],
                                         "condition_ids": reference["condition_ids"],
                                         "reason_codes": binding["reason_codes"]})
            unresolved_nodes[ref_id] = add_node("unresolved_reference", ref_id, fingerprint, "unresolved: " + ref_id)
    for reference in ledger["references"]:
        ref_id, source_id = reference["reference_id"], reference["source_file_reference"]
        binding, ref_node = bindings[ref_id], reference_nodes[ref_id]
        if source_id not in sources:
            raise InputError("rust_source_graph_unknown_source")
        add_edge("source_contains_reference", source_nodes[source_id], ref_node, "definite", [source_id, ref_id])
        status = binding["binding_status"]
        candidates = binding["candidate_file_references"]
        # A plain external mod name never produces a file candidate or path.
        if reference["reference_kind"] == "external_module_declaration" and reference["literal_relative_path"] is None and (
                candidates or binding["normalized_relative_path"] is not None or binding["bound_file_reference"] is not None):
            raise InputError("rust_source_graph_external_module_file_inference_rejected")
        if status in ("bound_to_observed_file", "file_missing"):
            if reference["literal_relative_path"] is None or binding["normalized_relative_path"] is None:
                raise InputError("rust_source_graph_file_binding_without_literal")
            for candidate in candidates:
                if candidate not in source_nodes:
                    raise InputError("rust_source_graph_unknown_file_candidate")
                add_edge("reference_explicitly_names_file", ref_node, source_nodes[candidate], "definite",
                         [ref_id, binding["binding_id"], candidate])
        if status == "bound_to_observed_file":
            target_id = binding["bound_file_reference"]
            target = sources.get(target_id)
            if (target is None or target_id not in candidates or target["read_status"] != "present_and_hashed"
                    or target["observed_sha256"] is None):
                raise InputError("rust_source_graph_bound_file_not_observed")
            add_edge("reference_bound_to_observed_file", ref_node, source_nodes[target_id], "definite",
                     [ref_id, binding["binding_id"], target_id])
        if status == "conditional_path_unresolved":
            if candidates and (reference["literal_relative_path"] is None or binding["normalized_relative_path"] is None):
                raise InputError("rust_source_graph_conditional_candidate_without_literal")
            for candidate in candidates:
                if candidate not in source_nodes:
                    raise InputError("rust_source_graph_unknown_conditional_candidate")
                add_edge("reference_may_resolve_to_file", ref_node, source_nodes[candidate], "possible",
                         [ref_id, binding["binding_id"], candidate, *reference["condition_ids"]])
        if status not in _RESOLVED_BINDING_STATUSES:
            add_edge("reference_unresolved", ref_node, unresolved_nodes[ref_id], "unresolved", [ref_id, binding["binding_id"]])
        if reference["condition_ids"]:
            add_edge("conditional_reference_unresolved", ref_node, unresolved_nodes[ref_id], "unresolved",
                     [ref_id, *reference["condition_ids"]])
    node_counts = Counter(row["node_type"] for row in nodes)
    edge_counts = Counter((row["edge_type"], row["certainty"]) for row in edges)
    certainty_counts = Counter(row["certainty"] for row in edges)
    counts = {"node_count": len(nodes), "edge_count": len(edges), "source_file_node_count": len(source_nodes),
              "reference_node_count": len(reference_nodes), "unresolved_reference_node_count": len(unresolved_nodes),
              "by_node_type": [{"node_type": kind, "node_count": node_counts[kind]} for kind in NODE_TYPES],
              "by_edge_type": [{"edge_type": kind, "definite_edge_count": edge_counts[(kind, "definite")],
                                "possible_edge_count": edge_counts[(kind, "possible")],
                                "unresolved_edge_count": edge_counts[(kind, "unresolved")]} for kind in EDGE_TYPES],
              "by_certainty": [{"certainty": kind, "edge_count": certainty_counts[kind]} for kind in CERTAINTIES]}
    return {**common(GRAPH_SCHEMA, ledger["source_reference"]), "nodes": nodes, "edges": edges,
            "counts": counts, "limitations": list(LIMITATIONS)}


__all__ = ("build_graph", "node_identifier", "source_fingerprint", "edge_payload", "NODE_TYPES", "EDGE_TYPES", "CERTAINTIES")
