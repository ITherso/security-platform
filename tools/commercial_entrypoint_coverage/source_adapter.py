"""Bind explicit old artifacts to a narrow metadata context; never mutate them."""
from __future__ import annotations

import copy
from dataclasses import dataclass

from commercial_handoff.input_loader import explicit_relative_path
from commercial_composition.artifact_manifest import identity
from commercial_dependency_evidence.composition_adapter import load_context as load_previous_context
from commercial_dependency_evidence.evidence_contracts import validate_documents as validate_previous_documents
from commercial_dependency_evidence.graph_renderer import render_summary as previous_summary
from commercial_dependency_evidence.artifact_manifest import manifest_data as previous_manifest
from commercial_dependency_evidence.manifest_scope import load_manifests as load_previous_manifests
from .coverage_contracts import InputError, parse_json, json_bytes, validate_context

DEPENDENCY_SCHEMAS = {
    "evidence": "termivar-offline-direct-dependency-evidence/v1",
    "graph": "termivar-offline-direct-dependency-graph/v1",
    "variants": "termivar-offline-variant-dependency-evidence/v1",
    "summary": None, "manifest": "termivar-offline-direct-dependency-manifest/v1",
}


def descriptors(group: dict) -> dict:
    return {role: {key: row[key] for key in ("schema_version", "bytes", "sha256")}
            for role, row in group.items()}


@dataclass(frozen=True, slots=True)
class LoadedSources:
    reference: dict
    context: dict
    previous: object
    evidence: dict


def load_sources(scope: dict, budget) -> LoadedSources:
    """Old pure validators check internal bindings, not source producer authority."""
    raw, documents = {}, {}
    group = scope["dependency_evidence_sources"]
    for role, schema in DEPENDENCY_SCHEMAS.items():
        selected = group[role]
        maximum = 128 * 1024 if role == "manifest" else 256 * 1024 if role == "summary" else 2 * 1024 * 1024
        raw[role] = budget.read(explicit_relative_path(selected["path"]), maximum)
        if {"schema_version": schema, **identity(raw[role])} != descriptors(group)[role]:
            raise InputError("entrypoint_previous_evidence_identity_mismatch")
        if role != "summary":
            documents[role] = parse_json(raw[role], maximum=maximum)
            if type(documents[role]) is not dict or documents[role].get("schema_version") != schema:
                raise InputError("entrypoint_unsupported_previous_contract")
    evidence, graph, variants = (documents[key] for key in ("evidence", "graph", "variants"))
    validate_previous_documents(evidence, graph, variants)
    if raw["summary"] != previous_summary(evidence, graph, variants):
        raise InputError("entrypoint_previous_summary_mismatch")
    payloads = {"direct-dependency-evidence.json": raw["evidence"], "source-evidence-graph.json": raw["graph"],
                "variant-dependency-evidence.json": raw["variants"], "dependency-evidence-summary.md": raw["summary"]}
    if json_bytes(documents["manifest"]) != json_bytes(previous_manifest(evidence, graph, variants, payloads)):
        raise InputError("entrypoint_previous_manifest_mismatch")
    compatibility_scope = {
        "source_reference": {key: copy.deepcopy(evidence["source_reference"][key])
                             for key in ("candidate_reference", "composition_candidate_reference", "source_commits")},
        "composition_sources": descriptors(scope["composition_sources"]),
        "variant_sources": descriptors(scope["variant_sources"]),
        "component_ownership_sources": [{"component_id": row["component_id"],
                                         "source_record_sha256": row["source_record_sha256"]}
                                        for row in evidence["components"]],
    }
    old = load_previous_context(compatibility_scope,
                               {key: row["path"] for key, row in scope["composition_sources"].items()},
                               {key: row["path"] for key, row in scope["variant_sources"].items()}, budget)
    for key in ("components", "manifest_catalog", "phase24_records", "variant_selections", "license_boundary_counts"):
        if json_bytes(getattr(old, key)) != json_bytes(evidence[key]):
            raise InputError("entrypoint_cross_phase_source_projection_mismatch")
    if (scope["source_reference"]["source_commits"] != old.reference["source_commits"]
            or scope["source_reference"]["composition_candidate_reference"] != old.reference["composition_candidate_reference"]
            or evidence["source_reference"] != old.reference):
        raise InputError("entrypoint_source_commit_reference_mismatch")
    reference = {**copy.deepcopy(scope["source_reference"]),
                 **{key: descriptors(scope[key]) for key in
                    ("composition_sources", "dependency_evidence_sources", "variant_sources")}}
    component_fields = ("component_id", "root_id", "pinned_commit", "manifest_path", "source_file_refs")
    context = {
        "source_roots": copy.deepcopy(old.inventory["source_roots"]),
        "files": copy.deepcopy(old.inventory["files"]),
        "components": [{key: copy.deepcopy(row[key]) for key in component_fields}
                       for row in old.inventory["components"]],
        "ownership": copy.deepcopy(evidence["ownership"]),
        "variant_selections": copy.deepcopy(old.variant_selections),
        "license_boundary_counts": copy.deepcopy(old.license_boundary_counts),
        "dependency_manifest_refs": copy.deepcopy(old.inventory["dependency_manifest_refs"]),
        "source_dependency_record_count": len(old.phase24_records),
        "source_ambiguous_dependency_record_count": evidence["counts"]["possible_phase24_record_count"],
        "source_definite_owner_count": evidence["counts"]["ownership_established_manifest_count"],
    }
    validate_context(context)
    return LoadedSources(reference, context, old, evidence)


def load_manifests(scope: dict, loaded: LoadedSources, termivar_root: str, budget) -> tuple:
    raw, metadata = load_previous_manifests(scope, loaded.previous, termivar_root, budget)
    old_by_id = {row["manifest_id"]: row for row in loaded.evidence["source_manifests"]}
    for row in metadata:
        old = old_by_id.get(row["manifest_id"])
        if old is None or any(old[key] != value for key, value in row.items()):
            raise InputError("entrypoint_manifest_not_bound_to_previous_evidence")
    return raw, metadata
