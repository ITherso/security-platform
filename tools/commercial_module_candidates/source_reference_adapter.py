"""Consume explicit Phase24/29 artefacts; retain only validated source metadata.

This adapter never opens Rust source files, imports a Rust lexer, discovers paths,
or treats parent artefact consistency as producer or compiler attestation.
"""
from __future__ import annotations

from copy import deepcopy

from commercial_handoff.input_loader import explicit_relative_path
from commercial_composition.artifact_manifest import (
    identity, manifest_data as composition_manifest,
)
from commercial_composition.composition_contracts import (
    validate_documents as validate_composition,
)
from commercial_composition.composition_renderer import render_summary as composition_summary
from commercial_composition.release_constraints import build_constraints
from commercial_rust_source_graph.source_graph_contracts import (
    validate_documents as validate_source_graph,
)
from commercial_rust_source_graph.output_renderer import render_summary as source_graph_summary
from commercial_rust_source_graph.artifact_manifest import manifest_data as source_graph_manifest
from .candidate_contracts import InputError, parse_json, json_bytes, validate_source_context


REFERENCE_SCHEMAS = {
    "ledger": "termivar-offline-rust-source-reference-ledger/v1",
    "graph": "termivar-offline-rust-source-evidence-graph/v1",
    "coverage": "termivar-offline-module-coverage-projection/v1",
    "summary": None,
    "manifest": "termivar-offline-rust-source-graph-manifest/v1",
}
INVENTORY_SCHEMAS = {
    "inventory": "termivar-offline-composition/v1",
    "dependencies": "termivar-offline-dependency-license-ledger/v1",
    "constraints": "termivar-offline-release-constraints/v1",
    "summary": None,
    "manifest": "termivar-offline-composition-manifest/v1",
}
_REFERENCE_PAYLOADS = (
    ("ledger", "source-reference-ledger.json"),
    ("graph", "source-evidence-graph.json"),
    ("coverage", "module-coverage-projection.json"),
    ("summary", "source-graph-summary.md"),
)
_INVENTORY_PAYLOADS = (
    ("inventory", "composition-inventory.json"),
    ("dependencies", "dependency-license-ledger.json"),
    ("constraints", "release-constraints.json"),
    ("summary", "composition-summary.md"),
)


def _descriptors(group: dict) -> dict:
    return {role: {key: row[key] for key in ("schema_version", "bytes", "sha256")}
            for role, row in group.items()}


def _read_group(group: dict, schemas: dict, budget, *, source_graph: bool) -> tuple[dict, dict]:
    if type(group) is not dict or set(group) != set(schemas):
        raise InputError("module_candidate_parent_roles_invalid")
    raw, docs = {}, {}
    for role, schema in schemas.items():
        descriptor = group[role]
        if type(descriptor) is not dict or set(descriptor) != {"path", "schema_version", "bytes", "sha256"}:
            raise InputError("module_candidate_parent_descriptor_invalid")
        maximum = (128 * 1024 if role == "manifest" else 256 * 1024 if role == "summary"
                   else 1024 * 1024 if source_graph else 2 * 1024 * 1024)
        raw[role] = budget.read(explicit_relative_path(descriptor["path"]), maximum)
        actual = {"schema_version": schema, **identity(raw[role])}
        if json_bytes(actual) != json_bytes({key: descriptor[key] for key in actual}):
            raise InputError("module_candidate_parent_bytes_or_schema_mismatch")
        if role != "summary":
            docs[role] = parse_json(raw[role], maximum=maximum)
            if type(docs[role]) is not dict or docs[role].get("schema_version") != schema:
                raise InputError("module_candidate_parent_contract_unsupported")
    return raw, docs


def _same(left: object, right: object, reason: str) -> None:
    # Canonical JSON comparison preserves the distinction between bool and int.
    if json_bytes(left) != json_bytes(right):
        raise InputError(reason)


def load_context(scope: dict, budget) -> tuple[dict, dict]:
    """Read ten explicit metadata files and return a closed independent copy."""
    inventory_raw, composition = _read_group(
        scope["inventory_sources"], INVENTORY_SCHEMAS, budget, source_graph=False)
    inventory, dependencies, constraints = (
        composition[key] for key in ("inventory", "dependencies", "constraints"))
    validate_composition(inventory, dependencies, constraints)
    _same(constraints, build_constraints(inventory, dependencies),
          "module_candidate_composition_constraints_mismatch")
    if inventory_raw["summary"] != composition_summary(inventory, dependencies, constraints):
        raise InputError("module_candidate_composition_summary_mismatch")
    inventory_payloads = {name: inventory_raw[role] for role, name in _INVENTORY_PAYLOADS}
    _same(composition["manifest"], composition_manifest(inventory, dependencies, constraints, inventory_payloads),
          "module_candidate_composition_manifest_mismatch")

    source_raw, sources = _read_group(
        scope["reference_sources"], REFERENCE_SCHEMAS, budget, source_graph=True)
    ledger, graph, coverage = (sources[key] for key in ("ledger", "graph", "coverage"))
    validate_source_graph(ledger, graph, coverage)
    # A coherent partial ledger is not the corrected source authority for this
    # workflow. Do not silently reduce the denominator after a lexical failure.
    if (ledger["counts"]["partial_unverified_file_count"] != 0
            or any(not row["scan_complete"] or row["lexical_status"] != "lexically_bounded"
                   for row in ledger["lexical_summaries"])):
        raise InputError("module_candidate_partial_source_authority_rejected")
    if source_raw["summary"] != source_graph_summary(ledger, graph, coverage):
        raise InputError("module_candidate_source_summary_mismatch")
    source_payloads = {name: source_raw[role] for role, name in _REFERENCE_PAYLOADS}
    _same(sources["manifest"], source_graph_manifest(ledger, graph, coverage, source_payloads),
          "module_candidate_source_manifest_mismatch")

    pins = {row["root_id"]: row["pinned_commit"] for row in inventory["source_roots"]}
    reference = scope["source_reference"]
    _same(reference["source_commits"], pins, "module_candidate_scope_pin_mismatch")
    _same(ledger["source_reference"]["source_commits"], pins, "module_candidate_parent_pin_mismatch")
    _same(reference["composition_candidate_reference"], inventory["candidate_reference"],
          "module_candidate_composition_reference_mismatch")
    inventory_descriptors = _descriptors(scope["inventory_sources"])
    _same(ledger["source_reference"]["composition_sources"], inventory_descriptors,
          "module_candidate_parent_inventory_artifacts_mismatch")

    old_context = ledger["parent_context"]["phase24_context"]
    component_fields = ("component_id", "root_id", "pinned_commit", "manifest_path", "source_file_refs")
    expected_components = [{key: row[key] for key in component_fields} for row in inventory["components"]]
    for key, expected in (
        ("source_roots", inventory["source_roots"]), ("files", inventory["files"]),
        ("components", expected_components), ("dependency_manifest_refs", inventory["dependency_manifest_refs"]),
        ("source_dependency_record_count", len(dependencies["dependencies"])),
    ):
        _same(old_context[key], expected, "module_candidate_inventory_context_mismatch")

    reference_by_id = {row["reference_id"]: row for row in ledger["references"]}
    for selected in scope["selected_references"]:
        original = reference_by_id.get(selected["reference"]["reference_id"])
        if original is None or original["reference_kind"] != "external_module_declaration":
            raise InputError("module_candidate_selected_reference_not_external")
        _same(selected["reference"], original, "module_candidate_selected_reference_metadata_mismatch")

    condition_ids = {key for row in ledger["references"] for key in row["condition_ids"]}
    context = {
        "phase29_source_reference": deepcopy(ledger["source_reference"]),
        "parent_context": deepcopy(ledger["parent_context"]),
        "source_files": deepcopy(ledger["source_files"]),
        "references": deepcopy(ledger["references"]),
        "conditions": [deepcopy(row) for row in ledger["conditions"] if row["condition_id"] in condition_ids],
    }
    full_reference = {**deepcopy(reference),
                      "reference_sources": _descriptors(scope["reference_sources"]),
                      "inventory_sources": inventory_descriptors}
    validate_source_context(context, full_reference)
    return deepcopy(full_reference), deepcopy(context)


__all__ = ("load_context",)
