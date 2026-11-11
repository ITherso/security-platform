"""Closed bounded static source evidence; no resolution or ownership authority."""
from __future__ import annotations

from collections import Counter
import copy
import re

from commercial_composition.composition_contracts import (
    InputError, COMPONENT_FIELDS, DEPENDENCY_FIELDS, closed, text, integer,
    identifier, relative_path, sha256, parse_json, json_bytes, ROOT_IDS, ROLES, VERSION_SCOPES,
)
from commercial_license_review.evidence_contracts import record_digest
from commercial_pilot_variants.variant_contracts import (
    COMPONENT_CATALOG_FIELDS, MANIFEST_FIELDS as CATALOG_MANIFEST_FIELDS,
    COMPOSITION_SOURCE_SCHEMAS, VARIANT_SCOPE_FIELDS,
)

SCOPE_SCHEMA = "termivar-offline-direct-dependency-scope/v1"
EVIDENCE_SCHEMA = "termivar-offline-direct-dependency-evidence/v1"
GRAPH_SCHEMA = "termivar-offline-direct-dependency-graph/v1"
VARIANTS_SCHEMA = "termivar-offline-variant-dependency-evidence/v1"
MANIFEST_SCHEMA = "termivar-offline-direct-dependency-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-direct-dependency-inspection/v1"
CANDIDATE_REFERENCE = "DEMO-TERMIVAR-DIRECT-DEPENDENCY-027"
COMPOSITION_CANDIDATE_REFERENCE = "DEMO-TERMIVAR-COMPOSITION-024"
DEMO_LABEL = "DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED"
FALSE_FLAGS = (
    "dependency_resolution_performed", "build_closure_verified", "runtime_inclusion_verified",
    "license_review_completed", "redistribution_authorized", "release_authorized", "production_ready",
    "producer_verified", "human_review_verified", "build_verified", "runtime_verified",
)
MAX_SCOPE_BYTES = 128 * 1024
MAX_JSON_SOURCE_BYTES = 12 * 1024 * 1024
MAX_MANIFEST_BYTES = 256 * 1024
MAX_MANIFESTS = 16
MAX_COMPONENTS = 64
MAX_PHASE24_RECORDS = 1024
MAX_DECLARATIONS = 512
MAX_VARIANTS = 4
MAX_GRAPH_NODES = 4096
MAX_GRAPH_EDGES = 8192
VARIANT_SOURCE_SCHEMAS = {
    "analysis": "termivar-offline-pilot-variant-analysis/v1",
    "dependencies": "termivar-offline-dependency-exposure/v1",
    "licenses": "termivar-offline-pilot-license-readiness/v1", "summary": None,
    "manifest": "termivar-offline-pilot-variant-manifest/v1",
}
COMMON_FIELDS = ("schema_version", "source_reference", "demo_label", "demo_only", *FALSE_FLAGS)
MANIFEST_SELECTION_FIELDS = ("manifest_id", "root_id", "path", "format", "phase24_file_ref", "bytes", "sha256", "pinned_commit")
PHASE24_RECORD_FIELDS = (*DEPENDENCY_FIELDS, "source_json_pointer", "source_record_sha256",
                         "source_artifact_sha256", "manifest_file_ref", "license_source_key")
LICENSE_BOUNDARY_FIELDS = (
    "source_license_record_count", "base_unknown_license_count", "evidence_present_record_count",
    "missing_evidence_record_count", "human_review_required_record_count", "source_blocker_count",
)
NODE_TYPES = ("component", "source_manifest", "workspace_dependency_declaration",
              "crate_dependency_declaration", "phase24_dependency_record")
EDGE_TYPES = ("component_owns_manifest", "manifest_declares_dependency", "crate_inherits_workspace_dependency",
              "declaration_matches_phase24_record", "declaration_may_match_phase24_record")
OVERLAY_CLASSES = ("evidenced_direct_declaration", "conditional_declaration", "ambiguous_declaration_binding",
                   "source_scope_only", "unattributed", "excluded_context", "insufficient_evidence")
VARIANT_CLASSES = OVERLAY_CLASSES
OWNERSHIP_STATUSES = ("definite_ownership", "ambiguous_ownership", "ownership_not_established")
BINDING_STATUSES = ("declaration_record_matched", "ambiguous_record_binding", "insufficient_source_evidence")
EVIDENCE_STATUSES = ("direct_manifest_declaration", "workspace_inherited_declaration", "conditional_declaration",
                     "source_scope_only", "insufficient_source_evidence")
INHERITANCE_STATUSES = ("not_requested", "workspace_inherited_declaration", "insufficient_source_evidence")
INHERITANCE_REASONS = ("not_requested", "explicit_workspace_template", "workspace_root_unavailable",
                       "workspace_template_unavailable", "workspace_root_ambiguous", "workspace_membership_not_established")
LIMITATIONS = (
    "explicit_selected_artifacts_and_cargo_manifests_only", "declaration_is_not_component_ownership",
    "legacy_projection_binding_is_not_resolution", "possible_binding_must_not_become_definite",
    "feature_and_target_activation_not_evaluated", "python_shared_project_metadata_not_helper_ownership",
    "source_graph_is_not_build_runtime_license_or_release_acceptance", "phase24_phase26_records_not_modified",
    "inspector_checks_projected_metadata_not_original_source_authenticity",
)
PRIMARY_COUNT_FIELDS = (
    "component_count", "source_manifest_count", "source_declaration_count", "workspace_pool_declaration_count",
    "crate_declaration_count", "workspace_inherited_declaration_count", "conditional_declaration_count",
    "ownership_established_manifest_count", "ambiguous_ownership_manifest_count", "ownership_not_established_manifest_count",
    "unique_binding_declaration_count", "ambiguous_binding_declaration_count", "unmatched_declaration_count",
    "unique_matched_phase24_record_count", "possible_phase24_record_count", "phase24_record_count",
    "phase24_declaration_record_count", "phase24_lock_record_count", "selected_source_record_count",
    "excluded_context_record_count", "variant_count",
)
NORMALIZED_MANIFEST_FIELDS = (*MANIFEST_SELECTION_FIELDS, "package_name", "package_version", "package_version_workspace",
                              "workspace_package_version", "workspace_members", "workspace_exclude", "package_workspace_declared",
                              "is_workspace", "workspace_dependency_keys", "features",
                              "target_entries", "declaration_locations", "source_fingerprint")
DECLARATION_FIELDS = (
    "declaration_id", "manifest_id", "manifest_sha256", "phase24_file_ref", "source_fingerprint", "scope",
    "declaring_package_name", "dependency_key", "package_name", "declared_package_name", "declared_requirement",
    "dependency_kind", "target_condition", "toml_field_path", "workspace_inherited", "optional", "features",
    "default_features", "source_locator_kind", "source_locator_sha256", "git_reference_sha256", "workspace_template_id",
    "inheritance_status", "inheritance_reason_code", "legacy_projection", "evidence_status", "activation_status",
    "target_evaluation", "limitations",
)
OWNERSHIP_FIELDS = ("manifest_id", "phase24_file_ref", "package_name", "component_id", "candidate_component_ids",
                    "primary_component_ids", "ownership_source", "ownership_evidence", "ownership_status",
                    "source_fingerprint", "limitations")
BINDING_FIELDS = ("declaration_id", "status", "matched_record_id", "candidate_record_ids", "matched_fields",
                  "missing_fields", "reason_codes", "binding_fingerprint")
OVERLAY_REASON_CODES = (
    "excluded_backend_context_preserved", "ambiguous_legacy_projection_binding",
    "selected_source_scope_without_definite_component_owner", "definite_source_declaration_activation_unknown",
    "conditional_source_declaration_activation_unknown", "no_source_attribution",
    "insufficient_direct_declaration_evidence", "workspace_template_is_not_crate_dependency",
    "feature_target_activation_not_performed",
)
LEGACY_PROJECTION_FIELDS = ("ecosystem", "name", "version", "declared_requirement", "source_type", "source_checksum",
                            "source_identity_sha256", "relation", "directness", "local_package_artifact")


def _fail(label: str) -> None:
    raise InputError("dependency_evidence_invalid_" + label)


def _fixed(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        _fail(label)


def _enum(value: object, choices: object, label: str) -> str:
    if type(value) is not str or value not in choices:
        _fail(label)
    return value


def _array(value: object, maximum: int, label: str, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _fail(label)
    return value


def _unique(values: list, label: str) -> None:
    if len(set(values)) != len(values):
        _fail(label)


def _ids(value: object, maximum: int, label: str) -> list[str]:
    values = _array(value, maximum, label)
    for item in values:
        identifier(item, label)
    _unique(values, label)
    return values


def _file_ref(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"F[0-9]{4}", value) is None or not 1 <= int(value[1:]) <= 5000:
        _fail(label)
    return value


def _text_list(value: object, maximum: int, label: str, item_maximum: int = 256) -> list[str]:
    values = _array(value, maximum, label)
    for item in values:
        text(item, label, item_maximum)
    return values


def _bool(value: object, label: str, nullable: bool = False) -> None:
    if value is None and nullable:
        return
    if type(value) is not bool:
        _fail(label)


def _digest_id(value: object, prefix: str, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or not value.startswith(prefix):
        _fail(label)
    sha256(value[len(prefix):], label)
    return value


def _record_id(value: object, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or re.fullmatch(r"D[0-9]{4}", value) is None or not 1 <= int(value[1:]) <= MAX_PHASE24_RECORDS:
        _fail(label)
    return value


def _source_group(value: object, schemas: dict) -> dict:
    group = closed(value, schemas, "source_group")
    for role, expected_schema in schemas.items():
        row = closed(group[role], ("schema_version", "bytes", "sha256"), "source_descriptor")
        _fixed(row["schema_version"], expected_schema, "source_schema")
        maximum = 512 * 1024 if role == "summary" else 64 * 1024 if role == "manifest" else 2 * 1024 * 1024
        if integer(row["bytes"], "source_bytes", maximum) == 0:
            _fail("source_bytes")
        sha256(row["sha256"], "source_hash")
    return group


def validate_reference(value: object, *, full: bool = True) -> dict:
    fields = ("candidate_reference", "composition_candidate_reference", "source_commits")
    if full:
        fields = (*fields, "composition_sources", "variant_sources")
    ref = closed(value, fields, "source_reference")
    _fixed(ref["candidate_reference"], CANDIDATE_REFERENCE, "candidate_reference")
    _fixed(ref["composition_candidate_reference"], COMPOSITION_CANDIDATE_REFERENCE, "composition_candidate_reference")
    commits = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for pin in commits.values():
        if type(pin) is not str or re.fullmatch(r"[0-9a-f]{40}", pin) is None:
            _fail("source_commit")
    if full:
        _source_group(ref["composition_sources"], COMPOSITION_SOURCE_SCHEMAS)
        _source_group(ref["variant_sources"], VARIANT_SOURCE_SCHEMAS)
        if sum(row["bytes"] for group in (ref["composition_sources"], ref["variant_sources"]) for row in group.values()) > MAX_JSON_SOURCE_BYTES:
            _fail("source_byte_budget")
    return copy.deepcopy(ref)


validate_source_reference = validate_reference


def common(schema: str, reference: dict) -> dict:
    _enum(schema, (EVIDENCE_SCHEMA, GRAPH_SCHEMA, VARIANTS_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA), "schema")
    return {"schema_version": schema, "source_reference": validate_reference(reference),
            "demo_label": DEMO_LABEL, "demo_only": True, **{flag: False for flag in FALSE_FLAGS}}


def _common(value: dict, schema: str) -> dict:
    reference = validate_reference(value["source_reference"])
    for field, fixed in common(schema, reference).items():
        _fixed(value[field], fixed, "common_" + field)
    return reference


def _manifest_selection(value: object, reference: dict) -> dict:
    row = closed(value, MANIFEST_SELECTION_FIELDS, "manifest_selection")
    identifier(row["manifest_id"], "manifest_id")
    _fixed(row["root_id"], "termivar", "manifest_root")
    relative_path(row["path"], "manifest_path")
    if row["path"].split("/")[-1] != "Cargo.toml":
        _fail("cargo_manifest_path")
    _fixed(row["format"], "cargo_toml", "manifest_format")
    _file_ref(row["phase24_file_ref"], "manifest_file_ref")
    if integer(row["bytes"], "manifest_bytes", MAX_MANIFEST_BYTES) == 0:
        _fail("manifest_bytes")
    sha256(row["sha256"], "manifest_hash")
    _fixed(row["pinned_commit"], reference["source_commits"]["termivar"], "manifest_pin")
    return row


def validate_scope(value: object) -> dict:
    raw = json_bytes(value, maximum=MAX_SCOPE_BYTES)
    root = closed(value, ("schema_version", "mode", "source_reference", "composition_sources", "variant_sources",
                          "manifest_sources", "component_ownership_sources", "inspection_constraints"), "scope")
    _fixed(root["schema_version"], SCOPE_SCHEMA, "scope_schema")
    _fixed(root["mode"], "demo", "scope_mode")
    reference = validate_reference(root["source_reference"], full=False)
    _source_group(root["composition_sources"], COMPOSITION_SOURCE_SCHEMAS)
    _source_group(root["variant_sources"], VARIANT_SOURCE_SCHEMAS)
    if len(raw) + sum(row["bytes"] for group in (root["composition_sources"], root["variant_sources"]) for row in group.values()) > MAX_JSON_SOURCE_BYTES:
        _fail("source_byte_budget")
    manifests = _array(root["manifest_sources"], MAX_MANIFESTS, "manifest_sources", 1)
    for row in manifests:
        _manifest_selection(row, reference)
    for field in ("manifest_id", "path", "phase24_file_ref"):
        _unique([row[field] for row in manifests], "duplicate_manifest_" + field)
    ownership = _array(root["component_ownership_sources"], MAX_COMPONENTS, "component_ownership_sources", 1)
    for row in ownership:
        closed(row, ("component_id", "source_record_sha256"), "ownership_selection")
        identifier(row["component_id"], "component_id")
        sha256(row["source_record_sha256"], "component_record_hash")
    _unique([row["component_id"] for row in ownership], "component_ids")
    limits = closed(root["inspection_constraints"], ("max_json_source_bytes", "max_manifest_bytes", "max_manifests",
                    "max_components", "max_phase24_records", "max_declarations", "max_variants", "max_graph_nodes", "max_graph_edges"), "inspection_constraints")
    for field, fixed in (("max_json_source_bytes", MAX_JSON_SOURCE_BYTES), ("max_manifest_bytes", MAX_MANIFEST_BYTES),
                         ("max_manifests", MAX_MANIFESTS), ("max_components", MAX_COMPONENTS),
                         ("max_phase24_records", MAX_PHASE24_RECORDS), ("max_declarations", MAX_DECLARATIONS),
                         ("max_variants", MAX_VARIANTS), ("max_graph_nodes", MAX_GRAPH_NODES), ("max_graph_edges", MAX_GRAPH_EDGES)):
        _fixed(limits[field], fixed, "inspection_limit")
    return copy.deepcopy(root)


def _components(rows: object, reference: dict) -> list:
    rows = _array(rows, MAX_COMPONENTS, "components", 1)
    identities = []
    for index, row in enumerate(rows):
        closed(row, COMPONENT_CATALOG_FIELDS, "component")
        identities.append(identifier(row["component_id"], "component_id"))
        _enum(row["root_id"], ROOT_IDS, "component_root")
        text(row["repository_label"], "repository_label", 128)
        _fixed(row["pinned_commit"], reference["source_commits"][row["root_id"]], "component_pin")
        _enum(row["role"], ROLES, "component_role")
        if row["manifest_path"] is not None:
            relative_path(row["manifest_path"], "component_manifest_path")
        refs = _array(row["source_file_refs"], 5000, "component_file_refs", 1)
        for ref in refs:
            _file_ref(ref, "component_file_ref")
        _unique(refs, "component_file_refs")
        text(row["version_declaration"], "component_version", nullable=True)
        _enum(row["version_scope"], VERSION_SCOPES, "version_scope")
        _fixed(row["source_present"], True, "source_present")
        _fixed(row["distribution_status"], "proposed_source_only", "distribution_status")
        _file_ref(row["manifest_file_ref"], "component_manifest_ref")
        if row["manifest_file_ref"] not in refs:
            _fail("component_manifest_reference")
        _fixed(row["source_json_pointer"], f"/components/{index}", "component_pointer")
        _fixed(row["source_artifact_sha256"], reference["composition_sources"]["inventory"]["sha256"], "component_artifact_hash")
        _fixed(row["source_record_sha256"], record_digest({key: row[key] for key in COMPONENT_FIELDS}), "component_record_hash")
        _digest_id(row["license_source_key"], "termivar-license-binding/v1:", "component_license_key")
    _unique(identities, "component_ids")
    return rows


def _manifest_catalog(rows: object) -> list:
    rows = _array(rows, 5000, "manifest_catalog", 1)
    identities, locations, file_refs = [], [], []
    for row in rows:
        closed(row, CATALOG_MANIFEST_FIELDS, "manifest_catalog_record")
        identities.append(identifier(row["manifest_id"], "manifest_id"))
        _enum(row["root_id"], ROOT_IDS, "manifest_root")
        relative_path(row["path"], "manifest_path")
        locations.append((row["root_id"], row["path"]))
        _enum(row["format"], ("cargo_toml", "cargo_lock", "pyproject_toml", "requirements_lock", "unsupported_yaml"), "manifest_format")
        _enum(row["context"], ("selected_source_metadata", "excluded_backend_context"), "manifest_context")
        sha256(row["sha256"], "manifest_hash")
        integer(row["bytes"], "manifest_bytes", 4 * 1024 * 1024)
        _enum(row["parse_status"], ("parsed", "unsupported"), "manifest_parse_status")
        integer(row["record_count"], "manifest_record_count", MAX_PHASE24_RECORDS)
        _enum(row["limitation_code"], ("selected_manifest_declarations_only", "whole_workspace_lock_not_selected_build",
                                      "excluded_backend_context_only", "unsupported_format_not_parsed"), "manifest_limitation")
        file_refs.append(_file_ref(row["source_file_ref"], "manifest_file_ref"))
    _unique(identities, "manifest_catalog_ids")
    _unique(locations, "manifest_catalog_paths")
    _unique(file_refs, "manifest_catalog_refs")
    return rows


def _phase24_records(rows: object, reference: dict, manifests: list) -> list:
    rows = _array(rows, MAX_PHASE24_RECORDS, "phase24_records", 1)
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    counts = Counter()
    for index, row in enumerate(rows):
        closed(row, PHASE24_RECORD_FIELDS, "phase24_record")
        _fixed(row["dependency_id"], f"D{index + 1:04d}", "phase24_dependency_id")
        identifier(row["manifest_id"], "phase24_manifest_id")
        if row["manifest_id"] not in manifest_by_id:
            _fail("phase24_manifest_reference")
        manifest = manifest_by_id[row["manifest_id"]]
        _enum(row["ecosystem"], ("rust", "python"), "dependency_ecosystem")
        text(row["name"], "dependency_name", 128)
        text(row["version"], "dependency_version", 128, nullable=True)
        text(row["declared_requirement"], "declared_requirement", 512, nullable=True)
        _enum(row["source_type"], ("registry", "git", "workspace", "declared_index", "unknown"), "dependency_source_type")
        sha256(row["source_checksum"], "source_checksum", nullable=True)
        sha256(row["source_identity_sha256"], "source_identity", nullable=True)
        _enum(row["relation"], ("direct_declaration", "lock_record"), "dependency_relation")
        _enum(row["directness"], ("direct_in_selected_manifest", "unknown"), "dependency_directness")
        _fixed(row["local_package_artifact"], "not_selected_or_verified", "local_package_artifact")
        _fixed(row["review_scope"], manifest["context"], "dependency_review_scope")
        _fixed(row["source_json_pointer"], f"/dependencies/{index}", "dependency_pointer")
        _fixed(row["source_artifact_sha256"], reference["composition_sources"]["dependencies"]["sha256"], "dependency_artifact_hash")
        _fixed(row["source_record_sha256"], record_digest({key: row[key] for key in DEPENDENCY_FIELDS}), "dependency_record_hash")
        _fixed(row["manifest_file_ref"], manifest["source_file_ref"], "dependency_manifest_ref")
        _digest_id(row["license_source_key"], "termivar-license-binding/v1:", "dependency_license_key")
        counts[row["manifest_id"]] += 1
    for identity, manifest in manifest_by_id.items():
        _fixed(manifest["record_count"], counts[identity], "manifest_record_count")
    return rows


def _variant_selections(rows: object, components: list) -> list:
    rows = _array(rows, MAX_VARIANTS, "variant_selections", 1)
    component_ids = {row["component_id"] for row in components}
    identities = []
    for row in rows:
        closed(row, VARIANT_SCOPE_FIELDS, "variant_selection")
        identities.append(identifier(row["variant_id"], "variant_id"))
        text(row["label"], "variant_label", 128)
        text(row["description"], "variant_description", 1024)
        selected = _ids(row["selected_component_ids"], MAX_COMPONENTS, "selected_component_ids")
        omitted = _ids(row["not_selected_component_ids"], MAX_COMPONENTS, "not_selected_component_ids")
        if not selected or set(selected) & set(omitted) or set(selected) | set(omitted) != component_ids:
            _fail("variant_component_partition")
    _unique(identities, "variant_ids")
    return rows


def _license_boundary(value: object) -> dict:
    row = closed(value, LICENSE_BOUNDARY_FIELDS, "license_boundary_counts")
    for field, item in row.items():
        integer(item, "license_boundary_count", MAX_PHASE24_RECORDS * 9 if field == "source_blocker_count" else MAX_PHASE24_RECORDS + MAX_COMPONENTS)
    if any(row[field] > row["source_license_record_count"] for field in LICENSE_BOUNDARY_FIELDS
           if field not in ("source_license_record_count", "source_blocker_count")):
        _fail("license_boundary_denominator")
    _fixed(row["human_review_required_record_count"], row["source_license_record_count"], "retained_human_review_required")
    return row


def _normalized_manifests(rows: object, reference: dict, catalog: list) -> list:
    rows = _array(rows, MAX_MANIFESTS, "source_manifests", 1)
    catalog_by_id = {row["manifest_id"]: row for row in catalog}
    identities = []
    for row in rows:
        closed(row, NORMALIZED_MANIFEST_FIELDS, "normalized_manifest")
        _manifest_selection({key: row[key] for key in MANIFEST_SELECTION_FIELDS}, reference)
        identity = row["manifest_id"]
        identities.append(identity)
        if identity not in catalog_by_id:
            _fail("normalized_manifest_catalog_reference")
        original = catalog_by_id[identity]
        for field in ("root_id", "path", "format", "bytes", "sha256"):
            _fixed(row[field], original[field], "normalized_manifest_identity")
        _fixed(row["phase24_file_ref"], original["source_file_ref"], "normalized_manifest_file_ref")
        text(row["package_name"], "package_name", 128, nullable=True)
        text(row["package_version"], "package_version", 128, nullable=True)
        _bool(row["package_version_workspace"], "package_version_workspace")
        text(row["workspace_package_version"], "workspace_package_version", 128, nullable=True)
        for field in ("workspace_members", "workspace_exclude"):
            values = _text_list(row[field], MAX_DECLARATIONS, field, 1024)
            for item in values:
                if item.startswith("/") or "\\" in item or ":" in item:
                    _fail("unsafe_workspace_metadata_path")
        _bool(row["package_workspace_declared"], "package_workspace_declared")
        _bool(row["is_workspace"], "is_workspace")
        _text_list(row["workspace_dependency_keys"], MAX_DECLARATIONS, "workspace_dependency_keys", 128)
        features = _array(row["features"], MAX_DECLARATIONS, "manifest_features")
        names = []
        for feature in features:
            closed(feature, ("name", "members"), "manifest_feature")
            names.append(text(feature["name"], "manifest_feature_name", 128))
            _text_list(feature["members"], MAX_DECLARATIONS, "manifest_feature_members")
        _unique(names, "manifest_feature_names")
        targets = _array(row["target_entries"], 64, "manifest_target_entries")
        for target in targets:
            closed(target, ("kind", "name", "path", "required_features"), "target_entry")
            _enum(target["kind"], ("lib", "bin"), "target_kind")
            text(target["name"], "target_name", 128, nullable=True)
            if target["path"] is not None:
                relative_path(target["path"], "target_path_metadata")
            _text_list(target["required_features"], MAX_DECLARATIONS, "target_required_features")
        locations = _array(row["declaration_locations"], MAX_DECLARATIONS, "manifest_declaration_locations")
        for location in locations:
            for segment in _array(location, 8, "manifest_declaration_path", 2):
                text(segment, "manifest_declaration_path_segment", 1024)
        _unique([tuple(location) for location in locations], "manifest_declaration_locations")
        _fixed(row["source_fingerprint"], record_digest({key: row[key] for key in NORMALIZED_MANIFEST_FIELDS if key != "source_fingerprint"}), "manifest_metadata_fingerprint")
    _unique(identities, "source_manifest_ids")
    return rows


def _legacy_projection(value: object) -> dict | None:
    if value is None:
        return None
    row = closed(value, LEGACY_PROJECTION_FIELDS, "legacy_projection")
    _fixed(row["ecosystem"], "rust", "legacy_ecosystem")
    text(row["name"], "legacy_name", 128)
    _fixed(row["version"], None, "legacy_unresolved_version")
    text(row["declared_requirement"], "legacy_requirement", 512, nullable=True)
    _enum(row["source_type"], ("registry", "git", "unknown"), "legacy_source_type")
    _fixed(row["source_checksum"], None, "legacy_source_checksum")
    sha256(row["source_identity_sha256"], "legacy_source_identity", nullable=True)
    _fixed(row["relation"], "direct_declaration", "legacy_relation")
    _enum(row["directness"], ("direct_in_selected_manifest", "unknown"), "legacy_directness")
    _fixed(row["local_package_artifact"], "not_selected_or_verified", "legacy_local_artifact")
    return row


def _declarations(rows: object, manifests: list) -> list:
    rows = _array(rows, MAX_DECLARATIONS, "declarations")
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    identities, locations = [], []
    for row in rows:
        closed(row, DECLARATION_FIELDS, "declaration")
        identities.append(_digest_id(row["declaration_id"], "decl-", "declaration_id"))
        identifier(row["manifest_id"], "declaration_manifest_id")
        if row["manifest_id"] not in manifest_by_id:
            _fail("declaration_manifest_reference")
        manifest = manifest_by_id[row["manifest_id"]]
        _fixed(row["manifest_sha256"], manifest["sha256"], "declaration_manifest_hash")
        _fixed(row["phase24_file_ref"], manifest["phase24_file_ref"], "declaration_manifest_ref")
        sha256(row["source_fingerprint"], "declaration_fingerprint")
        _enum(row["scope"], ("workspace_pool", "crate"), "declaration_scope")
        for field in ("declaring_package_name", "declared_package_name"):
            text(row[field], field, 128, nullable=True)
        text(row["dependency_key"], "dependency_key", 128)
        text(row["package_name"], "package_name", 128)
        text(row["declared_requirement"], "declared_requirement", 512, nullable=True)
        _enum(row["dependency_kind"], ("workspace_template", "normal", "dev", "build"), "dependency_kind")
        text(row["target_condition"], "target_condition", 1024, nullable=True)
        path = _array(row["toml_field_path"], 8, "toml_field_path", 2)
        for segment in path:
            text(segment, "toml_path_segment", 1024)
        locations.append((row["manifest_id"], tuple(path)))
        _fixed(path[-1], row["dependency_key"], "declaration_path_key")
        sections = {"dependencies": "normal", "dev-dependencies": "dev", "build-dependencies": "build"}
        if len(path) == 3 and path[:2] == ["workspace", "dependencies"]:
            _fixed(row["scope"], "workspace_pool", "workspace_scope")
            _fixed(row["dependency_kind"], "workspace_template", "workspace_dependency_kind")
            _fixed(row["target_condition"], None, "workspace_target_condition")
            if not manifest["is_workspace"]:
                _fail("workspace_declaration_manifest")
        elif len(path) == 2 and path[0] in sections:
            _fixed(row["scope"], "crate", "crate_scope")
            _fixed(row["dependency_kind"], sections[path[0]], "crate_dependency_kind")
            _fixed(row["target_condition"], None, "untargeted_declaration")
        elif len(path) == 4 and path[0] == "target" and path[2] in sections:
            _fixed(row["scope"], "crate", "target_crate_scope")
            _fixed(row["dependency_kind"], sections[path[2]], "target_dependency_kind")
            _fixed(row["target_condition"], path[1], "target_condition_source_path")
        else:
            _fail("unsupported_declaration_path")
        _fixed(row["declaring_package_name"], manifest["package_name"], "declaring_package_metadata")
        _bool(row["workspace_inherited"], "workspace_inherited")
        _bool(row["optional"], "optional", nullable=True)
        _bool(row["default_features"], "default_features", nullable=True)
        if row["features"] is not None:
            _text_list(row["features"], MAX_DECLARATIONS, "dependency_features")
        if row["source_locator_kind"] is not None:
            _enum(row["source_locator_kind"], ("path", "git", "registry", "registry_index"), "source_locator_kind")
        sha256(row["source_locator_sha256"], "source_locator_hash", nullable=True)
        sha256(row["git_reference_sha256"], "git_reference_hash", nullable=True)
        if (row["source_locator_kind"] is None) != (row["source_locator_sha256"] is None):
            _fail("source_locator_identity_pair")
        if row["git_reference_sha256"] is not None and row["source_locator_kind"] != "git":
            _fail("git_selector_without_git_source")
        if row["workspace_inherited"] and any(row[field] is not None for field in (
                "declared_package_name", "declared_requirement", "source_locator_kind", "source_locator_sha256", "git_reference_sha256")):
            _fail("unsupported_local_workspace_override")
        _digest_id(row["workspace_template_id"], "decl-", "workspace_template_id", nullable=True)
        _enum(row["inheritance_status"], INHERITANCE_STATUSES, "inheritance_status")
        _enum(row["inheritance_reason_code"], INHERITANCE_REASONS, "inheritance_reason_code")
        _legacy_projection(row["legacy_projection"])
        _enum(row["evidence_status"], EVIDENCE_STATUSES, "declaration_evidence_status")
        _fixed(row["activation_status"], "activation_unknown", "activation_status")
        _fixed(row["target_evaluation"], "not_performed", "target_evaluation")
        _ids(row["limitations"], 64, "declaration_limitations")
    _unique(identities, "declaration_ids")
    _unique(locations, "declaration_locations")
    return rows


def _ownership(rows: object, manifests: list, components: list) -> list:
    rows = _array(rows, MAX_MANIFESTS, "ownership", 1)
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    component_ids = {row["component_id"] for row in components}
    seen = []
    for row in rows:
        closed(row, OWNERSHIP_FIELDS, "ownership_record")
        identity = identifier(row["manifest_id"], "ownership_manifest_id")
        seen.append(identity)
        if identity not in manifest_by_id:
            _fail("ownership_manifest_reference")
        manifest = manifest_by_id[identity]
        _fixed(row["phase24_file_ref"], manifest["phase24_file_ref"], "ownership_file_ref")
        _fixed(row["package_name"], manifest["package_name"], "ownership_package_name")
        if row["component_id"] is not None:
            identifier(row["component_id"], "ownership_component_id")
            if row["component_id"] not in component_ids:
                _fail("ownership_component_reference")
        candidates = _ids(row["candidate_component_ids"], MAX_COMPONENTS, "ownership_candidates")
        primary = _ids(row["primary_component_ids"], MAX_COMPONENTS, "ownership_primary_components")
        if not set(primary) <= set(candidates) or not set(candidates) <= component_ids:
            _fail("ownership_candidate_reference")
        _fixed(row["ownership_source"], "phase24_file_scope_and_package_metadata", "ownership_source")
        _ids(row["ownership_evidence"], 64, "ownership_evidence")
        _enum(row["ownership_status"], OWNERSHIP_STATUSES, "ownership_status")
        if row["ownership_status"] == "definite_ownership":
            if row["component_id"] is None or candidates != [row["component_id"]] or primary != candidates or manifest["package_name"] is None:
                _fail("unsupported_definite_ownership")
        elif row["component_id"] is not None:
            _fail("uncertain_ownership_has_definite_component")
        _ids(row["limitations"], 64, "ownership_limitations")
        _fixed(row["source_fingerprint"], record_digest({key: row[key] for key in OWNERSHIP_FIELDS if key != "source_fingerprint"}), "ownership_fingerprint")
    _unique(seen, "ownership_manifest_ids")
    _fixed(seen, list(manifest_by_id), "complete_ownership_projection")
    return rows


def _bindings(rows: object, declarations: list, phase24_records: list) -> list:
    rows = _array(rows, MAX_DECLARATIONS, "bindings")
    declaration_ids = {row["declaration_id"] for row in declarations}
    record_ids = {row["dependency_id"] for row in phase24_records}
    seen = []
    for row in rows:
        closed(row, BINDING_FIELDS, "binding")
        identity = _digest_id(row["declaration_id"], "decl-", "binding_declaration_id")
        seen.append(identity)
        if identity not in declaration_ids:
            _fail("binding_declaration_reference")
        _enum(row["status"], BINDING_STATUSES, "binding_status")
        _record_id(row["matched_record_id"], "matched_record_id", nullable=True)
        candidates = _array(row["candidate_record_ids"], MAX_PHASE24_RECORDS, "binding_candidates")
        for candidate in candidates:
            _record_id(candidate, "binding_candidate_id")
            if candidate not in record_ids:
                _fail("binding_phase24_reference")
        _unique(candidates, "binding_candidate_ids")
        if row["status"] == "declaration_record_matched":
            if row["matched_record_id"] is None or candidates != [row["matched_record_id"]]:
                _fail("unique_binding_conditions")
        elif row["matched_record_id"] is not None:
            _fail("uncertain_binding_has_definite_record")
        if row["status"] == "ambiguous_record_binding" and len(candidates) < 2:
            _fail("ambiguous_binding_candidate_count")
        _ids(row["matched_fields"], 64, "binding_matched_fields")
        _ids(row["missing_fields"], 64, "binding_missing_fields")
        _ids(row["reason_codes"], 64, "binding_reason_codes")
        _fixed(row["binding_fingerprint"], record_digest({key: row[key] for key in BINDING_FIELDS if key != "binding_fingerprint"}), "binding_fingerprint")
    _unique(seen, "binding_declaration_ids")
    _fixed(seen, [row["declaration_id"] for row in declarations], "complete_binding_projection")
    return rows


def validate_evidence(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "components", "manifest_catalog", "phase24_records", "variant_selections",
                          "license_boundary_counts", "source_manifests", "declarations", "ownership", "bindings", "counts", "limitations"), "evidence")
    reference = _common(root, EVIDENCE_SCHEMA)
    components = _components(root["components"], reference)
    catalog = _manifest_catalog(root["manifest_catalog"])
    by_path = {(row["root_id"], row["path"]): row for row in catalog}
    for component in components:
        key = (component["root_id"], component["manifest_path"])
        if key not in by_path or by_path[key]["source_file_ref"] != component["manifest_file_ref"]:
            _fail("component_manifest_catalog_relationship")
    records = _phase24_records(root["phase24_records"], reference, catalog)
    _variant_selections(root["variant_selections"], components)
    boundary = _license_boundary(root["license_boundary_counts"])
    _fixed(boundary["source_license_record_count"], len(components) + len(records), "license_subject_denominator")
    manifests = _normalized_manifests(root["source_manifests"], reference, catalog)
    declarations = _declarations(root["declarations"], manifests)
    for manifest in manifests:
        actual = [row["toml_field_path"] for row in declarations if row["manifest_id"] == manifest["manifest_id"]]
        _fixed(actual, manifest["declaration_locations"], "complete_manifest_declaration_locations")
        catalog_row = next(row for row in catalog if row["manifest_id"] == manifest["manifest_id"])
        _fixed(len(actual), catalog_row["record_count"], "retained_manifest_declaration_count")
        workspace_keys = [row["dependency_key"] for row in declarations
                          if row["manifest_id"] == manifest["manifest_id"] and row["scope"] == "workspace_pool"]
        _fixed(workspace_keys, manifest["workspace_dependency_keys"], "workspace_template_key_projection")
    _ownership(root["ownership"], manifests, components)
    _bindings(root["bindings"], declarations, records)
    counts = closed(root["counts"], PRIMARY_COUNT_FIELDS, "evidence_counts")
    for item in counts.values():
        integer(item, "evidence_count", MAX_PHASE24_RECORDS + MAX_DECLARATIONS + MAX_COMPONENTS)
    _fixed(root["limitations"], list(LIMITATIONS), "evidence_limitations")
    return copy.deepcopy(root)


validate_primary = validate_evidence


def _typed_counts(value: object, field: str, types: tuple, count_fields: tuple) -> list:
    rows = _array(value, len(types), "typed_counts", len(types))
    for expected, row in zip(types, rows):
        closed(row, (field, *count_fields), "typed_count")
        _fixed(row[field], expected, "typed_count_order")
        for key in count_fields:
            integer(row[key], "typed_count", MAX_GRAPH_EDGES)
    return rows


def validate_graph(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "nodes", "edges", "counts", "limitations"), "graph")
    _common(root, GRAPH_SCHEMA)
    nodes = _array(root["nodes"], MAX_GRAPH_NODES, "nodes")
    ids = []
    node_types = Counter()
    for row in nodes:
        closed(row, ("node_id", "node_type", "source_reference_id", "source_fingerprint", "label", "evidence_status"), "node")
        ids.append(_digest_id(row["node_id"], "termivar-direct-dependency-node/v1:", "node_id"))
        node_types[_enum(row["node_type"], NODE_TYPES, "node_type")] += 1
        text(row["source_reference_id"], "node_source_reference_id", 256)
        sha256(row["source_fingerprint"], "node_source_fingerprint")
        text(row["label"], "node_label", 256)
        _fixed(row["evidence_status"], "source_metadata_only", "node_evidence_status")
        _fixed(row["node_id"], "termivar-direct-dependency-node/v1:" + record_digest({key: row[key] for key in (
            "node_type", "source_reference_id", "source_fingerprint")}), "node_identity")
    _unique(ids, "node_ids")
    edges = _array(root["edges"], MAX_GRAPH_EDGES, "edges")
    edge_ids, edge_types = [], Counter()
    for row in edges:
        closed(row, ("edge_id", "edge_type", "from_node_id", "to_node_id", "certainty", "evidence_refs", "source_fingerprint"), "edge")
        edge_ids.append(_digest_id(row["edge_id"], "termivar-direct-dependency-edge/v1:", "edge_id"))
        _enum(row["edge_type"], EDGE_TYPES, "edge_type")
        _enum(row["certainty"], ("definite", "possible"), "edge_certainty")
        for field in ("from_node_id", "to_node_id"):
            _digest_id(row[field], "termivar-direct-dependency-node/v1:", "edge_node_reference")
            if row[field] not in ids:
                _fail("edge_missing_node")
        _text_list(row["evidence_refs"], MAX_DECLARATIONS, "edge_evidence_refs")
        fingerprint = record_digest({key: row[key] for key in ("edge_type", "from_node_id", "to_node_id", "certainty", "evidence_refs")})
        _fixed(row["source_fingerprint"], fingerprint, "edge_fingerprint")
        _fixed(row["edge_id"], "termivar-direct-dependency-edge/v1:" + fingerprint, "edge_identity")
        edge_types[(row["edge_type"], row["certainty"])] += 1
    _unique(edge_ids, "edge_ids")
    counts = closed(root["counts"], ("node_count", "edge_count", "phase24_record_node_count", "by_node_type", "by_edge_type"), "graph_counts")
    for field, actual in (("node_count", len(nodes)), ("edge_count", len(edges)), ("phase24_record_node_count", node_types["phase24_dependency_record"])):
        _fixed(counts[field], actual, "graph_count")
    _typed_counts(counts["by_node_type"], "node_type", NODE_TYPES, ("node_count",))
    _typed_counts(counts["by_edge_type"], "edge_type", EDGE_TYPES, ("definite_edge_count", "possible_edge_count"))
    for row in counts["by_node_type"]:
        _fixed(row["node_count"], node_types[row["node_type"]], "graph_node_type_count")
    for row in counts["by_edge_type"]:
        _fixed(row["definite_edge_count"], edge_types[(row["edge_type"], "definite")], "graph_definite_edge_count")
        _fixed(row["possible_edge_count"], edge_types[(row["edge_type"], "possible")], "graph_possible_edge_count")
    _fixed(root["limitations"], list(LIMITATIONS), "graph_limitations")
    return copy.deepcopy(root)


def _classification_counts(value: object) -> list:
    return _typed_counts(value, "classification", OVERLAY_CLASSES, ("record_count",))


def validate_variants(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "variants", "records", "comparisons", "license_boundary_counts", "counts", "limitations"), "variants")
    _common(root, VARIANTS_SCHEMA)
    variants = _array(root["variants"], MAX_VARIANTS, "variants", 1)
    variant_ids = []
    for row in variants:
        closed(row, (*VARIANT_SCOPE_FIELDS, "demo_only", *FALSE_FLAGS, "owned_manifest_ids", "potential_manifest_ids",
                     "owned_declaration_ids", "ownership_unestablished_manifest_ids", "classification_counts"), "variant")
        variant_ids.append(identifier(row["variant_id"], "variant_id"))
        text(row["label"], "variant_label", 128)
        text(row["description"], "variant_description", 1024)
        selected = _ids(row["selected_component_ids"], MAX_COMPONENTS, "selected_component_ids")
        omitted = _ids(row["not_selected_component_ids"], MAX_COMPONENTS, "not_selected_component_ids")
        if not selected or set(selected) & set(omitted):
            _fail("variant_partition")
        _fixed(row["demo_only"], True, "variant_demo_only")
        for flag in FALSE_FLAGS:
            _fixed(row[flag], False, "variant_" + flag)
        for field in ("owned_manifest_ids", "potential_manifest_ids", "ownership_unestablished_manifest_ids"):
            _ids(row[field], MAX_MANIFESTS, field)
        declarations = _array(row["owned_declaration_ids"], MAX_DECLARATIONS, "owned_declaration_ids")
        for item in declarations:
            _digest_id(item, "decl-", "owned_declaration_id")
        _unique(declarations, "owned_declaration_ids")
        _classification_counts(row["classification_counts"])
    _unique(variant_ids, "variant_ids")
    records = _array(root["records"], MAX_PHASE24_RECORDS, "overlay_records", 1)
    classifications = {identity: Counter() for identity in variant_ids}
    for index, row in enumerate(records):
        closed(row, ("dependency_id", "source_record_sha256", "exposures"), "overlay_record")
        _fixed(row["dependency_id"], f"D{index + 1:04d}", "overlay_dependency_id")
        sha256(row["source_record_sha256"], "overlay_source_record_hash")
        exposures = _array(row["exposures"], MAX_VARIANTS, "overlay_exposures", 1)
        _fixed([item.get("variant_id") if type(item) is dict else None for item in exposures], variant_ids, "overlay_variant_order")
        for exposure in exposures:
            closed(exposure, ("variant_id", "classification", "reason_codes", "definite_declaration_ids",
                              "possible_declaration_ids", "conditional_declaration_ids", "ownership_statuses"), "overlay_exposure")
            category = _enum(exposure["classification"], OVERLAY_CLASSES, "overlay_classification")
            for code in _ids(exposure["reason_codes"], 64, "overlay_reason_codes"):
                _enum(code, OVERLAY_REASON_CODES, "overlay_reason_code")
            for field in ("definite_declaration_ids", "possible_declaration_ids", "conditional_declaration_ids"):
                items = _array(exposure[field], MAX_DECLARATIONS, field)
                for item in items:
                    _digest_id(item, "decl-", field)
                _unique(items, field)
            statuses = _array(exposure["ownership_statuses"], len(OWNERSHIP_STATUSES), "overlay_ownership_statuses")
            for status in statuses:
                _enum(status, OWNERSHIP_STATUSES, "overlay_ownership_status")
            _unique(statuses, "overlay_ownership_statuses")
            classifications[exposure["variant_id"]][category] += 1
    counts = closed(root["counts"], ("source_record_count", "variant_count", "by_variant"), "overlay_counts")
    _fixed(counts["source_record_count"], len(records), "overlay_source_record_count")
    _fixed(counts["variant_count"], len(variants), "overlay_variant_count")
    grouped = _array(counts["by_variant"], MAX_VARIANTS, "overlay_by_variant", 1)
    _fixed([item.get("variant_id") if type(item) is dict else None for item in grouped], variant_ids, "overlay_summary_variant_order")
    for variant, summary in zip(variants, grouped):
        closed(summary, ("variant_id", "classifications"), "overlay_variant_count")
        _classification_counts(summary["classifications"])
        _fixed(summary["classifications"], variant["classification_counts"], "overlay_variant_summary_relationship")
        for row in summary["classifications"]:
            _fixed(row["record_count"], classifications[variant["variant_id"]][row["classification"]], "overlay_classification_count")
    comparisons = _array(root["comparisons"], MAX_VARIANTS * (MAX_VARIANTS - 1) // 2, "overlay_comparisons")
    _fixed(len(comparisons), len(variants) * (len(variants) - 1) // 2, "all_unordered_comparison_count")
    seen = []
    for row in comparisons:
        closed(row, ("left", "right", "only_left_component_ids", "only_right_component_ids", "shared_component_ids",
                     "shared_owned_manifest_ids", "only_left_owned_manifest_ids", "only_right_owned_manifest_ids",
                     "classification_changes", "classification_change_count"), "overlay_comparison")
        for side in ("left", "right"):
            if row[side] not in variant_ids:
                _fail("comparison_variant_reference")
        if row["left"] == row["right"]:
            _fail("self_comparison")
        seen.append(frozenset((row["left"], row["right"])))
        for field in ("only_left_component_ids", "only_right_component_ids", "shared_component_ids"):
            _ids(row[field], MAX_COMPONENTS, field)
        for field in ("shared_owned_manifest_ids", "only_left_owned_manifest_ids", "only_right_owned_manifest_ids"):
            _ids(row[field], MAX_MANIFESTS, field)
        changes = _array(row["classification_changes"], MAX_PHASE24_RECORDS, "classification_changes")
        changed_ids = []
        for item in changes:
            closed(item, ("dependency_id", "left_classification", "right_classification"), "classification_change")
            changed_ids.append(_record_id(item["dependency_id"], "changed_dependency_id"))
            _enum(item["left_classification"], OVERLAY_CLASSES, "left_classification")
            _enum(item["right_classification"], OVERLAY_CLASSES, "right_classification")
            if item["left_classification"] == item["right_classification"]:
                _fail("unchanged_classification_delta")
        _unique(changed_ids, "changed_dependency_ids")
        _fixed(row["classification_change_count"], len(changes), "classification_change_count")
    _unique(seen, "duplicate_unordered_pair")
    _license_boundary(root["license_boundary_counts"])
    _fixed(root["limitations"], list(LIMITATIONS), "overlay_limitations")
    return copy.deepcopy(root)


def validate_documents(evidence: object, graph: object, variants: object) -> None:
    """Pure model checks only; original TOML and old artifacts are not reread."""
    primary = validate_evidence(evidence)
    checked_graph, overlay = validate_graph(graph), validate_variants(variants)
    for document in (checked_graph, overlay):
        _fixed(document["source_reference"], primary["source_reference"], "source_reference_relationship")
    from .workspace_inheritance import rebuild_inheritance, declaration_location_id, declaration_fingerprint
    from .component_ownership import build_ownership
    from .dependency_binding import build_bindings
    from .evidence_graph import rebuild_primary, build_graph, build_variants
    declarations = primary["declarations"]
    for row in declarations:
        _fixed(row["declaration_id"], declaration_location_id(row["manifest_sha256"], row["toml_field_path"]), "declaration_location_id")
        _fixed(row["source_fingerprint"], declaration_fingerprint(row), "declaration_source_fingerprint")
    _fixed(declarations, rebuild_inheritance(primary["source_manifests"], declarations), "workspace_inheritance_projection")
    _fixed(primary["ownership"], build_ownership(primary["source_manifests"], primary["components"]), "ownership_projection")
    _fixed(primary["bindings"], build_bindings(declarations, primary["phase24_records"], primary["manifest_catalog"]), "binding_projection")
    _fixed(primary, rebuild_primary(primary), "primary_projection")
    _fixed(checked_graph, build_graph(primary), "graph_projection")
    _fixed(overlay, build_variants(primary), "variant_projection")
