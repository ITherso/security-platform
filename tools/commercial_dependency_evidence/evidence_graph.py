"""Pure source graphs and variant overlays; no resolver or ownership fallback."""
from __future__ import annotations

from collections import Counter
from copy import deepcopy
from itertools import combinations

from commercial_license_review.evidence_contracts import record_digest
from .evidence_contracts import (
    EVIDENCE_SCHEMA, GRAPH_SCHEMA, VARIANTS_SCHEMA, FALSE_FLAGS, LIMITATIONS,
    NODE_TYPES, EDGE_TYPES, OVERLAY_CLASSES, MAX_GRAPH_NODES, MAX_GRAPH_EDGES,
    InputError, common,
)


def _conditional(row: dict) -> bool:
    return (row["evidence_status"] == "conditional_declaration" or row["optional"] is True
            or row["target_condition"] is not None or row["dependency_kind"] in ("dev", "build"))


def build_primary(reference: dict, components: list[dict], manifest_catalog: list[dict],
                  phase24_records: list[dict], variant_selections: list[dict],
                  license_boundary_counts: dict, source_manifests: list[dict],
                  declarations: list[dict], ownership: list[dict], bindings: list[dict]) -> dict:
    """Retain closed source projections; full validators belong to the caller."""
    if (len({row["component_id"] for row in components}) != len(components)
            or len({row["dependency_id"] for row in phase24_records}) != len(phase24_records)
            or len({row["manifest_id"] for row in source_manifests}) != len(source_manifests)
            or len({row["declaration_id"] for row in declarations}) != len(declarations)):
        raise InputError("direct_dependency_duplicate_primary_reference")
    unique_bindings = [row for row in bindings if row["status"] == "declaration_record_matched"]
    ambiguous_bindings = [row for row in bindings if row["status"] == "ambiguous_record_binding"]
    counts = {
        "component_count": len(components), "source_manifest_count": len(source_manifests),
        "source_declaration_count": len(declarations),
        "workspace_pool_declaration_count": sum(row["scope"] == "workspace_pool" for row in declarations),
        "crate_declaration_count": sum(row["scope"] == "crate" for row in declarations),
        "workspace_inherited_declaration_count": sum(row["inheritance_status"] == "workspace_inherited_declaration" for row in declarations),
        "conditional_declaration_count": sum(_conditional(row) for row in declarations),
        "ownership_established_manifest_count": sum(row["ownership_status"] == "definite_ownership" for row in ownership),
        "ambiguous_ownership_manifest_count": sum(row["ownership_status"] == "ambiguous_ownership" for row in ownership),
        "ownership_not_established_manifest_count": sum(row["ownership_status"] == "ownership_not_established" for row in ownership),
        "unique_binding_declaration_count": len(unique_bindings),
        "ambiguous_binding_declaration_count": len(ambiguous_bindings),
        "unmatched_declaration_count": len(bindings) - len(unique_bindings) - len(ambiguous_bindings),
        "unique_matched_phase24_record_count": len({row["matched_record_id"] for row in unique_bindings}),
        "possible_phase24_record_count": len({identity for row in ambiguous_bindings for identity in row["candidate_record_ids"]}),
        "phase24_record_count": len(phase24_records),
        "phase24_declaration_record_count": sum(row["relation"] == "direct_declaration" for row in phase24_records),
        "phase24_lock_record_count": sum(row["relation"] == "lock_record" for row in phase24_records),
        "selected_source_record_count": sum(row["review_scope"] == "selected_source_metadata" for row in phase24_records),
        "excluded_context_record_count": sum(row["review_scope"] == "excluded_backend_context" for row in phase24_records),
        "variant_count": len(variant_selections),
    }
    return {**common(EVIDENCE_SCHEMA, reference), "components": deepcopy(components),
            "manifest_catalog": deepcopy(manifest_catalog), "phase24_records": deepcopy(phase24_records),
            "variant_selections": deepcopy(variant_selections),
            "license_boundary_counts": deepcopy(license_boundary_counts),
            "source_manifests": deepcopy(source_manifests), "declarations": deepcopy(declarations),
            "ownership": deepcopy(ownership), "bindings": deepcopy(bindings),
            "counts": counts, "limitations": list(LIMITATIONS)}


def rebuild_primary(primary: dict) -> dict:
    return build_primary(primary["source_reference"], *(primary[name] for name in (
        "components", "manifest_catalog", "phase24_records", "variant_selections", "license_boundary_counts",
        "source_manifests", "declarations", "ownership", "bindings")))


def build_graph(primary: dict) -> dict:
    """Each original D row gets one node; certainty is explicit on every edge."""
    nodes, edges, node_refs, edge_ids = [], [], {}, set()

    def node(kind, identity, fingerprint, label):
        key = (kind, identity)
        if key in node_refs or len(nodes) >= MAX_GRAPH_NODES:
            raise InputError("direct_dependency_graph_node_limit_or_duplicate")
        payload = {"node_type": kind, "source_reference_id": identity, "source_fingerprint": fingerprint}
        identity_digest = record_digest(payload)
        node_id = "termivar-direct-dependency-node/v1:" + identity_digest
        nodes.append({"node_id": node_id, **payload, "label": label, "evidence_status": "source_metadata_only"})
        node_refs[key] = node_id

    for row in primary["components"]:
        node("component", row["component_id"], row["source_record_sha256"], row["component_id"])
    for row in primary["source_manifests"]:
        node("source_manifest", row["manifest_id"], row["sha256"], row["package_name"] or row["manifest_id"])
    for row in primary["declarations"]:
        kind = "workspace_dependency_declaration" if row["scope"] == "workspace_pool" else "crate_dependency_declaration"
        node(kind, row["declaration_id"], row["source_fingerprint"], row["dependency_key"])
    for row in primary["phase24_records"]:
        node("phase24_dependency_record", row["dependency_id"], row["source_record_sha256"], row["name"])
    declarations = {row["declaration_id"]: row for row in primary["declarations"]}

    def declaration_ref(identity):
        row = declarations.get(identity)
        if row is None:
            raise InputError("direct_dependency_graph_declaration_reference_missing")
        kind = "workspace_dependency_declaration" if row["scope"] == "workspace_pool" else "crate_dependency_declaration"
        return node_refs[(kind, identity)]

    def edge(kind, source, target, certainty, evidence_refs):
        if len(edges) >= MAX_GRAPH_EDGES:
            raise InputError("direct_dependency_graph_edge_limit")
        payload = {"edge_type": kind, "from_node_id": source, "to_node_id": target,
                   "certainty": certainty, "evidence_refs": list(evidence_refs)}
        fingerprint = record_digest(payload)
        edge_id = "termivar-direct-dependency-edge/v1:" + fingerprint
        if edge_id in edge_ids:
            raise InputError("direct_dependency_duplicate_graph_edge")
        edge_ids.add(edge_id)
        edges.append({"edge_id": edge_id, **payload, "source_fingerprint": fingerprint})

    for row in primary["ownership"]:
        if row["ownership_status"] == "definite_ownership":
            component = row["component_id"]
            if component is None or ("component", component) not in node_refs:
                raise InputError("direct_dependency_graph_owner_reference_missing")
            edge("component_owns_manifest", node_refs[("component", component)],
                 node_refs[("source_manifest", row["manifest_id"])], "definite", (component, row["manifest_id"]))
    for row in primary["declarations"]:
        identity = row["declaration_id"]
        edge("manifest_declares_dependency", node_refs[("source_manifest", row["manifest_id"])],
             declaration_ref(identity), "definite", (row["manifest_id"], identity))
        if row["workspace_inherited"] and row["inheritance_status"] == "workspace_inherited_declaration":
            template = declarations.get(row["workspace_template_id"])
            if row["scope"] != "crate" or template is None or template["scope"] != "workspace_pool":
                raise InputError("direct_dependency_graph_inheritance_reference_missing")
            edge("crate_inherits_workspace_dependency", declaration_ref(identity), declaration_ref(template["declaration_id"]),
                 "definite", (identity, template["declaration_id"]))
    for row in primary["bindings"]:
        if row["status"] == "declaration_record_matched":
            identity = row["matched_record_id"]
            if identity is None or row["candidate_record_ids"] != [identity]:
                raise InputError("direct_dependency_graph_unique_binding_invalid")
            edge("declaration_matches_phase24_record", declaration_ref(row["declaration_id"]),
                 node_refs[("phase24_dependency_record", identity)], "definite", (row["declaration_id"], identity))
        elif row["status"] == "ambiguous_record_binding":
            for identity in row["candidate_record_ids"]:
                edge("declaration_may_match_phase24_record", declaration_ref(row["declaration_id"]),
                     node_refs[("phase24_dependency_record", identity)], "possible", (row["declaration_id"], identity))
    node_counts = Counter(row["node_type"] for row in nodes)
    edge_counts = Counter((row["edge_type"], row["certainty"]) for row in edges)
    return {**common(GRAPH_SCHEMA, primary["source_reference"]), "nodes": nodes, "edges": edges,
            "counts": {"node_count": len(nodes), "edge_count": len(edges),
                       "phase24_record_node_count": node_counts["phase24_dependency_record"],
                       "by_node_type": [{"node_type": kind, "node_count": node_counts[kind]} for kind in NODE_TYPES],
                       "by_edge_type": [{"edge_type": kind, "definite_edge_count": edge_counts[(kind, "definite")],
                                         "possible_edge_count": edge_counts[(kind, "possible")]} for kind in EDGE_TYPES]},
            "limitations": list(LIMITATIONS)}


def build_variants(primary: dict) -> dict:
    """A separate source-evidence overlay; never rewrite Phase26 exposure classes."""
    variants = primary["variant_selections"]
    declarations = {row["declaration_id"]: row for row in primary["declarations"]}
    owners = {row["manifest_id"]: row for row in primary["ownership"]}
    by_record = {row["dependency_id"]: [] for row in primary["phase24_records"]}
    for binding in primary["bindings"]:
        for identity in binding["candidate_record_ids"]:
            if identity not in by_record:
                raise InputError("direct_dependency_overlay_record_reference_missing")
            by_record[identity].append(binding)
    records = []
    for record in primary["phase24_records"]:
        selected_bindings = by_record[record["dependency_id"]]
        candidates = [declarations[row["declaration_id"]] for row in selected_bindings]
        exposures = []
        for variant in variants:
            selected = set(variant["selected_component_ids"])
            definite, possible = [], []
            for binding, declaration in zip(selected_bindings, candidates):
                owner = owners[declaration["manifest_id"]]
                if (binding["status"] == "declaration_record_matched" and declaration["scope"] == "crate"
                        and owner["ownership_status"] == "definite_ownership" and owner["component_id"] in selected):
                    definite.append(declaration["declaration_id"])
                elif selected.intersection(owner["candidate_component_ids"]):
                    possible.append(declaration["declaration_id"])
            condition_ids = [row["declaration_id"] for row in candidates if _conditional(row)]
            if record["review_scope"] == "excluded_backend_context":
                classification, reason = "excluded_context", "excluded_backend_context_preserved"
            elif any(row["status"] == "ambiguous_record_binding" for row in selected_bindings):
                classification, reason = "ambiguous_declaration_binding", "ambiguous_legacy_projection_binding"
            elif definite:
                if any(identity in condition_ids for identity in definite):
                    classification, reason = "conditional_declaration", "conditional_source_declaration_activation_unknown"
                else:
                    classification, reason = "evidenced_direct_declaration", "definite_source_declaration_activation_unknown"
            elif possible:
                classification, reason = "source_scope_only", "selected_source_scope_without_definite_component_owner"
            elif record["relation"] == "direct_declaration" and not selected_bindings:
                classification, reason = "insufficient_evidence", "insufficient_direct_declaration_evidence"
            else:
                classification, reason = "unattributed", "no_source_attribution"
            reasons = [reason]
            if possible and any(row["scope"] == "workspace_pool" for row in candidates):
                reasons.append("workspace_template_is_not_crate_dependency")
            if condition_ids:
                reasons.append("feature_target_activation_not_performed")
            exposures.append({"variant_id": variant["variant_id"], "classification": classification,
                              "reason_codes": reasons, "definite_declaration_ids": list(dict.fromkeys(definite)),
                              "possible_declaration_ids": list(dict.fromkeys(possible)),
                              "conditional_declaration_ids": list(dict.fromkeys(condition_ids)),
                              "ownership_statuses": list(dict.fromkeys(owners[row["manifest_id"]]["ownership_status"] for row in candidates))})
        records.append({"dependency_id": record["dependency_id"], "source_record_sha256": record["source_record_sha256"],
                        "exposures": exposures})
    result_variants, by_variant = [], []
    for variant in variants:
        selected = set(variant["selected_component_ids"])
        owned = [row["manifest_id"] for row in primary["ownership"]
                 if row["ownership_status"] == "definite_ownership" and row["component_id"] in selected]
        potential = [row["manifest_id"] for row in primary["ownership"] if selected.intersection(row["candidate_component_ids"])]
        classes = Counter(item["classification"] for row in records for item in row["exposures"]
                          if item["variant_id"] == variant["variant_id"])
        classifications = [{"classification": name, "record_count": classes[name]} for name in OVERLAY_CLASSES]
        result_variants.append({**deepcopy(variant), "demo_only": True, **{flag: False for flag in FALSE_FLAGS},
                                "owned_manifest_ids": owned, "potential_manifest_ids": potential,
                                "owned_declaration_ids": [row["declaration_id"] for row in primary["declarations"]
                                                          if row["scope"] == "crate" and row["manifest_id"] in owned],
                                "ownership_unestablished_manifest_ids": [row["manifest_id"] for row in primary["ownership"]
                                                                         if row["ownership_status"] != "definite_ownership"],
                                "classification_counts": deepcopy(classifications)})
        by_variant.append({"variant_id": variant["variant_id"], "classifications": classifications})
    comparisons = []
    for left, right in combinations(result_variants, 2):
        changes = []
        for record in records:
            mapped = {row["variant_id"]: row["classification"] for row in record["exposures"]}
            if mapped[left["variant_id"]] != mapped[right["variant_id"]]:
                changes.append({"dependency_id": record["dependency_id"], "left_classification": mapped[left["variant_id"]],
                                "right_classification": mapped[right["variant_id"]]})
        comparisons.append({"left": left["variant_id"], "right": right["variant_id"],
                            "only_left_component_ids": [identity for identity in left["selected_component_ids"] if identity not in right["selected_component_ids"]],
                            "only_right_component_ids": [identity for identity in right["selected_component_ids"] if identity not in left["selected_component_ids"]],
                            "shared_component_ids": [identity for identity in left["selected_component_ids"] if identity in right["selected_component_ids"]],
                            "shared_owned_manifest_ids": [identity for identity in left["owned_manifest_ids"] if identity in right["owned_manifest_ids"]],
                            "only_left_owned_manifest_ids": [identity for identity in left["owned_manifest_ids"] if identity not in right["owned_manifest_ids"]],
                            "only_right_owned_manifest_ids": [identity for identity in right["owned_manifest_ids"] if identity not in left["owned_manifest_ids"]],
                            "classification_changes": changes, "classification_change_count": len(changes)})
    return {**common(VARIANTS_SCHEMA, primary["source_reference"]), "variants": result_variants,
            "records": records, "comparisons": comparisons,
            "license_boundary_counts": deepcopy(primary["license_boundary_counts"]),
            "counts": {"source_record_count": len(records), "variant_count": len(variants), "by_variant": by_variant},
            "limitations": list(LIMITATIONS)}


__all__ = ("build_primary", "rebuild_primary", "build_graph", "build_variants")
