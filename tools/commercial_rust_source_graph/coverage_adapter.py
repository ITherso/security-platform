"""Consume fifteen explicit old payloads; retain only bounded source projections."""
from __future__ import annotations

import copy

from commercial_handoff.input_loader import explicit_relative_path
from commercial_composition.artifact_manifest import identity, manifest_data as composition_manifest
from commercial_composition.composition_contracts import validate_documents as validate_composition
from commercial_composition.composition_renderer import render_summary as composition_summary
from commercial_composition.release_constraints import build_constraints
from commercial_dependency_evidence.evidence_contracts import validate_documents as validate_dependency
from commercial_dependency_evidence.graph_renderer import render_summary as dependency_summary
from commercial_dependency_evidence.artifact_manifest import manifest_data as dependency_manifest
from commercial_entrypoint_coverage.coverage_contracts import validate_documents as validate_entrypoint
from commercial_entrypoint_coverage.output_renderer import render_summary as entrypoint_summary
from commercial_entrypoint_coverage.artifact_manifest import manifest_data as entrypoint_manifest
from .source_graph_contracts import InputError, parse_json, json_bytes, validate_parent_context

SCHEMAS = {
    "composition_sources": {
        "inventory": "termivar-offline-composition/v1", "dependencies": "termivar-offline-dependency-license-ledger/v1",
        "constraints": "termivar-offline-release-constraints/v1", "summary": None,
        "manifest": "termivar-offline-composition-manifest/v1"},
    "dependency_evidence_sources": {
        "evidence": "termivar-offline-direct-dependency-evidence/v1", "graph": "termivar-offline-direct-dependency-graph/v1",
        "variants": "termivar-offline-variant-dependency-evidence/v1", "summary": None,
        "manifest": "termivar-offline-direct-dependency-manifest/v1"},
    "entrypoint_sources": {
        "coverage": "termivar-offline-entrypoint-coverage/v1", "delta": "termivar-offline-source-scope-delta/v1",
        "variants": "termivar-offline-variant-entrypoint-projection/v1", "summary": None,
        "manifest": "termivar-offline-entrypoint-coverage-manifest/v1"},
}


def descriptors(group: dict) -> dict:
    return {role: {key: row[key] for key in ("schema_version", "bytes", "sha256")}
            for role, row in group.items()}


def _group(name: str, selected: dict, budget) -> tuple:
    raw, docs = {}, {}
    for role, schema in SCHEMAS[name].items():
        row = selected[role]
        maximum = 128 * 1024 if role == "manifest" else 512 * 1024 if role == "summary" else 2 * 1024 * 1024
        raw[role] = budget.read(explicit_relative_path(row["path"]), maximum)
        if {"schema_version": schema, **identity(raw[role])} != descriptors(selected)[role]:
            raise InputError("rust_source_parent_artifact_identity_mismatch")
        if role != "summary":
            docs[role] = parse_json(raw[role], maximum=maximum)
            if type(docs[role]) is not dict or docs[role].get("schema_version") != schema:
                raise InputError("rust_source_unsupported_parent_contract")
    return raw, docs


def _payloads(raw: dict, names: tuple) -> dict:
    return {name: raw[role] for role, name in names}


def load_context(scope: dict, budget) -> tuple[dict, dict]:
    selected = scope["coverage_sources"]
    c_raw, comp = _group("composition_sources", selected["composition_sources"], budget)
    inv, deps, constraints = (comp[k] for k in ("inventory", "dependencies", "constraints"))
    validate_composition(inv, deps, constraints)
    if json_bytes(constraints) != json_bytes(build_constraints(inv, deps)) or c_raw["summary"] != composition_summary(inv, deps, constraints):
        raise InputError("rust_source_composition_projection_mismatch")
    c_payloads = _payloads(c_raw, (("inventory", "composition-inventory.json"), ("dependencies", "dependency-license-ledger.json"),
                                  ("constraints", "release-constraints.json"), ("summary", "composition-summary.md")))
    if json_bytes(comp["manifest"]) != json_bytes(composition_manifest(inv, deps, constraints, c_payloads)):
        raise InputError("rust_source_composition_manifest_mismatch")
    d_raw, dependency = _group("dependency_evidence_sources", selected["dependency_evidence_sources"], budget)
    evidence, graph, variants = (dependency[k] for k in ("evidence", "graph", "variants"))
    validate_dependency(evidence, graph, variants)
    if d_raw["summary"] != dependency_summary(evidence, graph, variants):
        raise InputError("rust_source_dependency_summary_mismatch")
    d_payloads = _payloads(d_raw, (("evidence", "direct-dependency-evidence.json"), ("graph", "source-evidence-graph.json"),
                                  ("variants", "variant-dependency-evidence.json"), ("summary", "dependency-evidence-summary.md")))
    if json_bytes(dependency["manifest"]) != json_bytes(dependency_manifest(evidence, graph, variants, d_payloads)):
        raise InputError("rust_source_dependency_manifest_mismatch")
    e_raw, entry = _group("entrypoint_sources", selected["entrypoint_sources"], budget)
    coverage, delta, projection = (entry[k] for k in ("coverage", "delta", "variants"))
    validate_entrypoint(coverage, delta, projection)
    if e_raw["summary"] != entrypoint_summary(coverage, delta, projection):
        raise InputError("rust_source_entrypoint_summary_mismatch")
    e_payloads = _payloads(e_raw, (("coverage", "entrypoint-coverage.json"), ("delta", "source-scope-delta.json"),
                                  ("variants", "variant-entrypoint-projection.json"), ("summary", "entrypoint-summary.md")))
    if json_bytes(entry["manifest"]) != json_bytes(entrypoint_manifest(coverage, delta, projection, e_payloads)):
        raise InputError("rust_source_entrypoint_manifest_mismatch")
    pins = {r["root_id"]: r["pinned_commit"] for r in inv["source_roots"]}
    comp_ids, dependency_ids = descriptors(selected["composition_sources"]), descriptors(selected["dependency_evidence_sources"])
    for old in (evidence, coverage):
        if old["source_reference"]["source_commits"] != pins or old["source_reference"]["composition_sources"] != comp_ids:
            raise InputError("rust_source_parent_commit_or_artifact_reference_mismatch")
    if (scope["source_reference"]["source_commits"] != pins
            or scope["source_reference"]["composition_candidate_reference"] != inv["candidate_reference"]
            or coverage["source_reference"]["dependency_evidence_sources"] != dependency_ids
            or coverage["source_reference"]["variant_sources"] != evidence["source_reference"]["variant_sources"]):
        raise InputError("rust_source_cross_phase_reference_mismatch")
    ctx = coverage["source_context"]
    fields = ("component_id", "root_id", "pinned_commit", "manifest_path", "source_file_refs")
    expected_components = [{k: copy.deepcopy(r[k]) for k in fields} for r in inv["components"]]
    for key, actual in (("source_roots", inv["source_roots"]), ("files", inv["files"]), ("components", expected_components),
                        ("dependency_manifest_refs", inv["dependency_manifest_refs"]), ("ownership", evidence["ownership"]),
                        ("variant_selections", evidence["variant_selections"]), ("license_boundary_counts", evidence["license_boundary_counts"])):
        if ctx[key] != actual:
            raise InputError("rust_source_narrow_parent_projection_mismatch")
    if len(evidence["phase24_records"]) != len(deps["dependencies"]):
        raise InputError("rust_source_dependency_denominator_mismatch")
    for actual, retained in zip(deps["dependencies"], evidence["phase24_records"]):
        if any(retained.get(k) != value for k, value in actual.items()):
            raise InputError("rust_source_retained_dependency_changed")
    if (ctx["source_dependency_record_count"] != len(deps["dependencies"])
            or ctx["source_ambiguous_dependency_record_count"] != evidence["counts"]["possible_phase24_record_count"]
            or ctx["source_definite_owner_count"] != evidence["counts"]["ownership_established_manifest_count"]):
        raise InputError("rust_source_retained_boundary_changed")
    old_files = {r["source_file_reference"]: r for r in coverage["source_files"]}
    old_targets = {r["target_reference"]: r for r in coverage["targets"]}
    for row in scope["entrypoint_sources"]:
        old, target = old_files.get(row["entrypoint_reference"]), old_targets.get(row["target_reference"])
        if (old is None or target is None or old["read_status"] != "present_and_hashed"
                or any(old[k] != row[k] for k in ("root_id", "pinned_commit", "path"))
                or old["observed_byte_size"] != row["bytes"] or old["observed_sha256"] != row["sha256"]
                or target["manifest_reference"] != row["manifest_reference"]
                or target["normalized_relative_path"] != row["path"]
                or not any(a["target_reference"] == row["target_reference"] for a in old["allowlist_entries"])):
            raise InputError("rust_source_entrypoint_selection_not_source_bound")
    delta_fields = ("proposal_reference", "source_file_reference", "path", "root_id", "pinned_commit", "observed_byte_size", "observed_sha256",
                    "application_authorized", "application_performed", "phase24_inventory_modified", "component_ownership_verified")
    parent = {"phase24_context": copy.deepcopy(ctx), "phase28_entrypoints": copy.deepcopy(scope["entrypoint_sources"]),
              "phase28_deltas": [{k: copy.deepcopy(row[k]) for k in delta_fields} for row in delta["proposals"]]}
    validate_parent_context(parent)
    reference = {**copy.deepcopy(scope["source_reference"]), **{k: descriptors(group) for k, group in selected.items()}}
    return reference, parent
