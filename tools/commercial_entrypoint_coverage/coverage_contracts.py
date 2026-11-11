"""Closed entry-point observations and unapplied repository-scope proposals."""
from __future__ import annotations

from collections import Counter
import copy
import re

from commercial_composition.composition_contracts import (
    InputError, ROOT_FIELDS, FILE_FIELDS, MANIFEST_REF_FIELDS, closed, text, integer,
    identifier, relative_path, sha256, parse_json as _parse_json, json_bytes as _json_bytes,
)
from commercial_dependency_evidence.evidence_contracts import (
    OWNERSHIP_FIELDS, OWNERSHIP_STATUSES, MANIFEST_SELECTION_FIELDS,
)
from commercial_license_review.evidence_contracts import record_digest

SCOPE_SCHEMA = "termivar-offline-entrypoint-coverage-scope/v1"
COVERAGE_SCHEMA = "termivar-offline-entrypoint-coverage/v1"
DELTA_SCHEMA = "termivar-offline-source-scope-delta/v1"
VARIANTS_SCHEMA = "termivar-offline-variant-entrypoint-projection/v1"
MANIFEST_SCHEMA = "termivar-offline-entrypoint-coverage-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-entrypoint-coverage-inspection/v1"
CANDIDATE_REFERENCE = "DEMO-TERMIVAR-ENTRYPOINT-COVERAGE-028"
COMPOSITION_CANDIDATE_REFERENCE = "DEMO-TERMIVAR-COMPOSITION-024"
DEMO_LABEL = "DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED"
FALSE_FLAGS = (
    "source_inventory_updated", "scope_delta_applied", "component_ownership_verified",
    "dependency_closure_verified", "build_verified", "runtime_verified", "producer_verified",
    "human_review_verified", "license_review_completed", "redistribution_authorized",
    "release_authorized", "production_ready",
)
MAX_SCOPE_BYTES = 128 * 1024
MAX_JSON_BYTES = 2 * 1024 * 1024
MAX_ARTIFACT_MANIFEST_BYTES = 128 * 1024
MAX_CARGO_BYTES = 256 * 1024
MAX_TARGET_BYTES = 512 * 1024
MAX_TOTAL_TARGET_BYTES = 1024 * 1024
MAX_TOTAL_INPUT_BYTES = 12 * 1024 * 1024
MAX_CHUNK_BYTES = 64 * 1024
MAX_SUMMARY_BYTES = 256 * 1024
MAX_MANIFESTS = 16
MAX_SOURCE_FILES = 32
MAX_ALLOWLIST_BINDINGS = 64
MAX_TARGETS = 64
MAX_F_REFERENCES = 512
MAX_COMPONENTS = 64
MAX_VARIANTS = 4
MAX_PROPOSALS = 64
COMMON_FIELDS = ("schema_version", "source_reference", "demo_label", "demo_only", *FALSE_FLAGS)
GROUP_SCHEMAS = {
    "composition_sources": {
        "inventory": "termivar-offline-composition/v1", "dependencies": "termivar-offline-dependency-license-ledger/v1",
        "constraints": "termivar-offline-release-constraints/v1", "summary": None,
        "manifest": "termivar-offline-composition-manifest/v1",
    },
    "dependency_evidence_sources": {
        "evidence": "termivar-offline-direct-dependency-evidence/v1", "graph": "termivar-offline-direct-dependency-graph/v1",
        "variants": "termivar-offline-variant-dependency-evidence/v1", "summary": None,
        "manifest": "termivar-offline-direct-dependency-manifest/v1",
    },
    "variant_sources": {
        "analysis": "termivar-offline-pilot-variant-analysis/v1", "dependencies": "termivar-offline-dependency-exposure/v1",
        "licenses": "termivar-offline-pilot-license-readiness/v1", "summary": None,
        "manifest": "termivar-offline-pilot-variant-manifest/v1",
    },
}
CONTEXT_FIELDS = ("source_roots", "files", "components", "ownership", "dependency_manifest_refs", "variant_selections",
                  "license_boundary_counts", "source_dependency_record_count", "source_ambiguous_dependency_record_count", "source_definite_owner_count")
COMPONENT_FIELDS = ("component_id", "root_id", "pinned_commit", "manifest_path", "source_file_refs")
VARIANT_FIELDS = ("variant_id", "label", "description", "selected_component_ids", "not_selected_component_ids")
BOUNDARY_FIELDS = ("source_license_record_count", "base_unknown_license_count", "evidence_present_record_count",
                   "missing_evidence_record_count", "human_review_required_record_count", "source_blocker_count")
MANIFEST_FIELDS = (*MANIFEST_SELECTION_FIELDS, "package_name", "is_workspace", "target_locations", "source_fingerprint")
TARGET_FIELDS = ("target_reference", "manifest_reference", "manifest_sha256", "root_id", "pinned_commit", "package_name",
                 "target_kind", "declared_target_name", "declared_relative_path", "normalized_relative_path", "toml_field_path",
                 "required_features", "target_declared", "target_path_declared", "extraction_status", "source_fingerprint")
ALLOWLIST_FIELDS = ("source_file_reference", "root_id", "path", "manifest_reference", "target_reference", "pinned_commit",
                    "expected_sha256", "max_bytes", "read_kind")
SOURCE_FILE_FIELDS = ("source_file_reference", "root_id", "pinned_commit", "path", "allowlist_entries", "read_status",
                      "source_file_presence", "regular_file", "observed_byte_size", "observed_sha256")
COVERAGE_STATUSES = (
    "covered_by_selected_source", "present_outside_selected_scope", "source_present_inventory_gap",
    "declared_target_file_missing", "entrypoint_not_established", "source_identity_mismatch",
    "source_read_not_performed", "scope_classification_unknown",
)
LIMITATIONS = (
    "explicit_selected_artifacts_and_allowed_files_only", "global_f_catalog_is_not_component_selection",
    "component_reference_is_not_runtime_inclusion", "ownership_uncertainty_preserved",
    "no_cargo_automatic_target_discovery", "no_rust_module_or_dependency_closure",
    "observed_hash_is_not_git_or_producer_attestation", "scope_delta_is_unapplied_repository_level_proposal",
    "inspector_checks_projected_metadata_not_original_source",
)
APPLICATION_PRECONDITIONS = (
    "human_source_scope_review_required", "component_assignment_requires_separate_ownership_evidence",
    "phase24_inventory_change_requires_explicit_authorization", "build_runtime_release_acceptance_not_established",
)


def _fail(label: str) -> None:
    raise InputError("entrypoint_invalid_" + label)


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


def _pin(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{40}", value) is None:
        _fail(label)
    return value


def _f_ref(value: object, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or re.fullmatch(r"F[0-9]{4}", value) is None or not 1 <= int(value[1:]) <= MAX_F_REFERENCES:
        _fail(label)
    return value


def _epf(value: object, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or re.fullmatch(r"EPF[0-9]{4}", value) is None or not 1 <= int(value[3:]) <= MAX_SOURCE_FILES:
        _fail(label)
    return value


def _digest_id(value: object, prefix: str, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or not value.startswith(prefix):
        _fail(label)
    sha256(value[len(prefix):], label)
    return value


def parse_json(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    integer(maximum, "json_byte_limit", MAX_JSON_BYTES)
    return _parse_json(raw, maximum=maximum)


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    integer(maximum, "json_byte_limit", MAX_JSON_BYTES)
    return _json_bytes(value, maximum=maximum)


def _group(value: object, name: str, *, paths: bool) -> dict:
    group = closed(value, GROUP_SCHEMAS[name], "source_group")
    for role, schema in GROUP_SCHEMAS[name].items():
        row = closed(group[role], ("path", "schema_version", "bytes", "sha256") if paths else ("schema_version", "bytes", "sha256"), "source_descriptor")
        _fixed(row["schema_version"], schema, "source_schema")
        if paths:
            relative_path(row["path"], "source_artifact_path")
        maximum = MAX_ARTIFACT_MANIFEST_BYTES if role == "manifest" else MAX_SUMMARY_BYTES if role == "summary" else MAX_JSON_BYTES
        if integer(row["bytes"], "source_bytes", maximum) == 0:
            _fail("source_bytes")
        sha256(row["sha256"], "source_hash")
    return group


def validate_reference(value: object, *, full: bool = True) -> dict:
    fields = ("candidate_reference", "composition_candidate_reference", "source_commits")
    if full:
        fields = (*fields, *GROUP_SCHEMAS)
    ref = closed(value, fields, "source_reference")
    _fixed(ref["candidate_reference"], CANDIDATE_REFERENCE, "candidate_reference")
    _fixed(ref["composition_candidate_reference"], COMPOSITION_CANDIDATE_REFERENCE, "composition_candidate_reference")
    commits = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for pin in commits.values():
        _pin(pin, "source_pin")
    if full:
        for name in GROUP_SCHEMAS:
            _group(ref[name], name, paths=False)
        if sum(item["bytes"] for name in GROUP_SCHEMAS for item in ref[name].values()) > MAX_TOTAL_INPUT_BYTES:
            _fail("source_byte_budget")
    return copy.deepcopy(ref)


validate_source_reference = validate_reference


def common(schema: str, reference: dict) -> dict:
    _enum(schema, (COVERAGE_SCHEMA, DELTA_SCHEMA, VARIANTS_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA), "schema")
    return {"schema_version": schema, "source_reference": validate_reference(reference), "demo_label": DEMO_LABEL,
            "demo_only": True, **{flag: False for flag in FALSE_FLAGS}}


def _common(value: dict, schema: str) -> dict:
    ref = validate_reference(value["source_reference"])
    for field, fixed in common(schema, ref).items():
        _fixed(value[field], fixed, "common_" + field)
    return ref


def _allowlist(rows: object) -> list:
    rows = _array(rows, MAX_ALLOWLIST_BINDINGS, "allowed_entrypoint_files")
    by_ref, by_path, bindings = {}, {}, []
    for row in rows:
        closed(row, ALLOWLIST_FIELDS, "allowlist_entry")
        identity = _epf(row["source_file_reference"], "source_file_reference")
        _fixed(row["root_id"], "termivar", "allowlist_root")
        path = relative_path(row["path"], "allowlist_path")
        identifier(row["manifest_reference"], "allowlist_manifest_reference")
        _digest_id(row["target_reference"], "target-", "allowlist_target_reference")
        pin = _pin(row["pinned_commit"], "allowlist_pin")
        sha256(row["expected_sha256"], "expected_source_hash", nullable=True)
        if integer(row["max_bytes"], "allowed_file_bytes", MAX_TARGET_BYTES) == 0:
            _fail("allowed_file_bytes")
        _fixed(row["read_kind"], "bounded_sha256", "read_kind")
        source = (row["root_id"], pin, path, row["expected_sha256"], row["max_bytes"], row["read_kind"])
        if identity in by_ref and by_ref[identity] != source:
            _fail("source_file_reference_alias")
        key = (row["root_id"], pin, path)
        if key in by_path and by_path[key] != identity:
            _fail("source_identity_multiple_references")
        by_ref[identity], by_path[key] = source, identity
        bindings.append((identity, row["manifest_reference"], row["target_reference"]))
    _unique(bindings, "duplicate_allowlist_binding")
    if len(by_ref) > MAX_SOURCE_FILES:
        _fail("unique_source_file_limit")
    return rows


def validate_scope(value: object) -> dict:
    raw = json_bytes(value, maximum=MAX_SCOPE_BYTES)
    root = closed(value, ("schema_version", "mode", "source_reference", *GROUP_SCHEMAS, "manifest_sources",
                          "allowed_entrypoint_files", "scope_delta_constraints"), "scope")
    _fixed(root["schema_version"], SCOPE_SCHEMA, "scope_schema")
    _fixed(root["mode"], "demo", "scope_mode")
    ref = validate_reference(root["source_reference"], full=False)
    source_bytes = len(raw)
    paths = []
    for name in GROUP_SCHEMAS:
        _group(root[name], name, paths=True)
        source_bytes += sum(row["bytes"] for row in root[name].values())
        paths.extend(row["path"] for row in root[name].values())
    _unique(paths, "source_artifact_paths")
    manifests = _array(root["manifest_sources"], MAX_MANIFESTS, "manifest_sources", 1)
    for row in manifests:
        closed(row, MANIFEST_SELECTION_FIELDS, "manifest_selection")
        identifier(row["manifest_id"], "manifest_id")
        _fixed(row["root_id"], "termivar", "manifest_root")
        relative_path(row["path"], "manifest_path")
        _fixed(row["format"], "cargo_toml", "manifest_format")
        _f_ref(row["phase24_file_ref"], "manifest_file_ref")
        if integer(row["bytes"], "cargo_bytes", MAX_CARGO_BYTES) == 0:
            _fail("cargo_bytes")
        sha256(row["sha256"], "manifest_hash")
        _fixed(row["pinned_commit"], ref["source_commits"]["termivar"], "manifest_pin")
        source_bytes += row["bytes"]
    for field in ("manifest_id", "path", "phase24_file_ref"):
        _unique([row[field] for row in manifests], "duplicate_manifest_" + field)
    _allowlist(root["allowed_entrypoint_files"])
    manifest_ids = {row["manifest_id"] for row in manifests}
    for row in root["allowed_entrypoint_files"]:
        if row["manifest_reference"] not in manifest_ids:
            _fail("allowlist_manifest_reference")
        _fixed(row["pinned_commit"], ref["source_commits"]["termivar"], "allowlist_pin")
    constraints = closed(root["scope_delta_constraints"], ("proposal_level", "proposed_scope_action", "application_authorized",
                        "application_performed", "phase24_inventory_modified", "component_ownership_verified"), "scope_delta_constraints")
    for field, expected in (("proposal_level", "repository"), ("proposed_scope_action", "propose_selected_source_inclusion"),
                            ("application_authorized", False), ("application_performed", False),
                            ("phase24_inventory_modified", False), ("component_ownership_verified", False)):
        _fixed(constraints[field], expected, "scope_delta_constraint")
    if source_bytes > MAX_TOTAL_INPUT_BYTES:
        _fail("total_input_budget")
    return copy.deepcopy(root)


def validate_context(value: object) -> dict:
    json_bytes(value)
    context = closed(value, CONTEXT_FIELDS, "source_context")
    roots = _array(context["source_roots"], 2, "source_roots", 2)
    pins, root_ids = {}, []
    for row in roots:
        closed(row, ROOT_FIELDS, "source_root")
        root_ids.append(_enum(row["root_id"], ("termivar", "platform"), "root_id"))
        label = text(row["repository_label"], "repository_label", 128)
        if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", label) is None or "://" in label:
            _fail("repository_label")
        pins[row["root_id"]] = _pin(row["pinned_commit"], "root_pin")
    _unique(root_ids, "root_ids")
    files = _array(context["files"], MAX_F_REFERENCES, "files", 1)
    by_ref, by_path = {}, {}
    for index, row in enumerate(files, 1):
        closed(row, FILE_FIELDS, "file_metadata")
        _fixed(row["file_id"], f"F{index:04d}", "file_id")
        _enum(row["root_id"], pins, "file_root")
        relative_path(row["path"], "file_path")
        integer(row["bytes"], "file_metadata_bytes", 4 * 1024 * 1024)
        sha256(row["sha256"], "file_hash")
        _fixed(row["local_artifact_present"], True, "local_artifact_present")
        key = (row["root_id"], row["path"])
        if key in by_path:
            _fail("duplicate_file_path")
        by_ref[row["file_id"]], by_path[key] = row, row
    components = _array(context["components"], MAX_COMPONENTS, "components", 1)
    component_ids, old_components = [], []
    for row in components:
        closed(row, COMPONENT_FIELDS, "component")
        component_ids.append(identifier(row["component_id"], "component_id"))
        _enum(row["root_id"], pins, "component_root")
        _fixed(row["pinned_commit"], pins[row["root_id"]], "component_pin")
        if row["manifest_path"] is not None:
            relative_path(row["manifest_path"], "component_manifest_path")
        refs = _array(row["source_file_refs"], MAX_F_REFERENCES, "component_file_refs", 1)
        for ref in refs:
            _f_ref(ref, "component_file_ref")
            if ref not in by_ref or by_ref[ref]["root_id"] != row["root_id"]:
                _fail("component_file_relationship")
        _unique(refs, "component_file_refs")
        key = (row["root_id"], row["manifest_path"])
        if key not in by_path or by_path[key]["file_id"] not in refs:
            _fail("component_manifest_file_relationship")
        old_components.append({**row, "manifest_file_ref": by_path[key]["file_id"]})
    _unique(component_ids, "component_ids")
    manifests = _array(context["dependency_manifest_refs"], MAX_F_REFERENCES, "dependency_manifest_refs")
    manifest_ids = []
    for row in manifests:
        closed(row, MANIFEST_REF_FIELDS, "dependency_manifest_ref")
        manifest_ids.append(identifier(row["manifest_id"], "manifest_id"))
        _enum(row["root_id"], pins, "dependency_manifest_root")
        relative_path(row["path"], "dependency_manifest_path")
        _enum(row["format"], ("cargo_toml", "cargo_lock", "pyproject_toml", "requirements_lock", "unsupported_yaml"), "manifest_format")
        _enum(row["context"], ("selected_source_metadata", "excluded_backend_context"), "manifest_context")
        if (row["root_id"], row["path"]) not in by_path:
            _fail("dependency_manifest_file_reference")
    _unique(manifest_ids, "dependency_manifest_ids")
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    ownership = _array(context["ownership"], MAX_MANIFESTS, "ownership", 1)
    ownership_ids, old_manifests = [], []
    for row in ownership:
        closed(row, OWNERSHIP_FIELDS, "ownership_record")
        ownership_ids.append(identifier(row["manifest_id"], "ownership_manifest_id"))
        _f_ref(row["phase24_file_ref"], "ownership_file_ref")
        if row["phase24_file_ref"] not in by_ref:
            _fail("ownership_file_reference")
        source = by_ref[row["phase24_file_ref"]]
        declared = manifest_by_id.get(row["manifest_id"])
        if (declared is None or declared["format"] != "cargo_toml"
                or declared["root_id"] != source["root_id"] or declared["path"] != source["path"]):
            _fail("ownership_manifest_catalog_relationship")
        text(row["package_name"], "ownership_package_name", 128, nullable=True)
        if row["component_id"] is not None:
            identifier(row["component_id"], "ownership_component_id")
        for field in ("candidate_component_ids", "primary_component_ids"):
            if not set(_ids(row[field], MAX_COMPONENTS, field)) <= set(component_ids):
                _fail("ownership_component_reference")
        _fixed(row["ownership_source"], "phase24_file_scope_and_package_metadata", "ownership_source")
        _ids(row["ownership_evidence"], 64, "ownership_evidence")
        _enum(row["ownership_status"], OWNERSHIP_STATUSES, "ownership_status")
        _ids(row["limitations"], 64, "ownership_limitations")
        sha256(row["source_fingerprint"], "ownership_fingerprint")
        old_manifests.append({"manifest_id": row["manifest_id"], "phase24_file_ref": row["phase24_file_ref"],
                              "root_id": source["root_id"], "path": source["path"], "pinned_commit": pins[source["root_id"]],
                              "package_name": row["package_name"]})
    _unique(ownership_ids, "ownership_manifest_ids")
    from commercial_dependency_evidence.component_ownership import build_ownership
    _fixed(ownership, build_ownership(old_manifests, old_components), "retained_ownership_projection")
    variants = _array(context["variant_selections"], MAX_VARIANTS, "variant_selections", 1)
    variant_ids = []
    for row in variants:
        closed(row, VARIANT_FIELDS, "variant_selection")
        variant_ids.append(identifier(row["variant_id"], "variant_id"))
        text(row["label"], "variant_label", 128)
        text(row["description"], "variant_description", 1024)
        selected = _ids(row["selected_component_ids"], MAX_COMPONENTS, "selected_components")
        omitted = _ids(row["not_selected_component_ids"], MAX_COMPONENTS, "not_selected_components")
        if not selected or set(selected) & set(omitted) or set(selected) | set(omitted) != set(component_ids):
            _fail("variant_component_partition")
    _unique(variant_ids, "variant_ids")
    boundary = closed(context["license_boundary_counts"], BOUNDARY_FIELDS, "license_boundary_counts")
    for field, item in boundary.items():
        integer(item, "license_boundary_count", 1024 * 9 if field == "source_blocker_count" else 1088)
    dependency_count = integer(context["source_dependency_record_count"], "source_dependency_record_count", 1024)
    ambiguous_count = integer(context["source_ambiguous_dependency_record_count"], "ambiguous_dependency_count", 1024)
    if ambiguous_count > dependency_count:
        _fail("ambiguous_dependency_denominator")
    _fixed(boundary["source_license_record_count"], dependency_count + len(components), "source_license_count")
    _fixed(boundary["human_review_required_record_count"], boundary["source_license_record_count"], "retained_license_review_required")
    if any(boundary[field] > boundary["source_license_record_count"] for field in BOUNDARY_FIELDS
           if field not in ("source_license_record_count", "source_blocker_count")):
        _fail("license_boundary_denominator")
    _fixed(context["source_definite_owner_count"], sum(row["ownership_status"] == "definite_ownership" for row in ownership), "source_definite_owner_count")
    return copy.deepcopy(context)


def validate_manifests(value: object, context: dict) -> list:
    manifests = _array(value, MAX_MANIFESTS, "manifests", 1)
    roots = {row["root_id"]: row["pinned_commit"] for row in context["source_roots"]}
    files = {row["file_id"]: row for row in context["files"]}
    ownership = {row["manifest_id"]: row for row in context["ownership"]}
    identities = []
    for row in manifests:
        closed(row, MANIFEST_FIELDS, "parsed_manifest")
        identities.append(identifier(row["manifest_id"], "manifest_id"))
        _fixed(row["root_id"], "termivar", "manifest_root")
        relative_path(row["path"], "manifest_path")
        _fixed(row["format"], "cargo_toml", "manifest_format")
        _f_ref(row["phase24_file_ref"], "manifest_file_ref")
        if row["phase24_file_ref"] not in files or row["manifest_id"] not in ownership:
            _fail("manifest_source_reference")
        source = files[row["phase24_file_ref"]]
        _fixed(row["phase24_file_ref"], ownership[row["manifest_id"]]["phase24_file_ref"], "manifest_ownership_file_reference")
        for field in ("root_id", "path", "bytes", "sha256"):
            _fixed(row[field], source[field], "manifest_file_identity")
        if integer(row["bytes"], "cargo_bytes", MAX_CARGO_BYTES) == 0:
            _fail("cargo_bytes")
        sha256(row["sha256"], "cargo_hash")
        _fixed(row["pinned_commit"], roots[row["root_id"]], "manifest_pin")
        _fixed(row["package_name"], ownership[row["manifest_id"]]["package_name"], "manifest_package_metadata")
        if type(row["is_workspace"]) is not bool:
            _fail("is_workspace")
        locations = _array(row["target_locations"], MAX_TARGETS, "target_locations")
        for location in locations:
            _target_location(location)
        _unique([tuple(location) for location in locations], "target_locations")
        _fixed(row["source_fingerprint"], record_digest({key: row[key] for key in MANIFEST_FIELDS if key != "source_fingerprint"}), "manifest_fingerprint")
    _unique(identities, "manifest_ids")
    return copy.deepcopy(manifests)


def _target_location(value: object) -> list:
    location = _array(value, 2, "target_location", 1)
    if location == ["lib"]:
        return location
    if len(location) != 2 or location[0] != "bin" or type(location[1]) is not str or re.fullmatch(r"0|[1-9][0-9]?", location[1]) is None:
        _fail("target_location")
    if int(location[1]) >= MAX_TARGETS:
        _fail("target_location_index")
    return location


def validate_targets(value: object, manifests: list) -> list:
    targets = _array(value, MAX_TARGETS, "targets")
    manifest_by_id = {row["manifest_id"]: row for row in manifests}
    identities, locations = [], []
    for row in targets:
        closed(row, TARGET_FIELDS, "target")
        identities.append(_digest_id(row["target_reference"], "target-", "target_reference"))
        identifier(row["manifest_reference"], "target_manifest_reference")
        if row["manifest_reference"] not in manifest_by_id:
            _fail("target_manifest_reference")
        manifest = manifest_by_id[row["manifest_reference"]]
        for field, source_field in (("manifest_sha256", "sha256"), ("root_id", "root_id"), ("pinned_commit", "pinned_commit"), ("package_name", "package_name")):
            _fixed(row[field], manifest[source_field], "target_manifest_relationship")
        _enum(row["target_kind"], ("lib", "bin"), "target_kind")
        text(row["declared_target_name"], "declared_target_name", 128, nullable=True)
        location = _target_location(row["toml_field_path"])
        _fixed(row["target_kind"], location[0], "target_kind_location")
        locations.append((row["manifest_reference"], tuple(location)))
        _fixed(row["target_declared"], True, "target_declared")
        features = _array(row["required_features"], 256, "target_required_features")
        for feature in features:
            text(feature, "required_feature", 256)
        if row["declared_relative_path"] is None:
            _fixed(row["normalized_relative_path"], None, "missing_explicit_target_path")
            _fixed(row["target_path_declared"], False, "target_path_declared")
            _fixed(row["extraction_status"], "entrypoint_not_established", "target_extraction_status")
        else:
            path = relative_path(row["declared_relative_path"], "declared_target_path")
            prefix = manifest["path"].rsplit("/", 1)[0] + "/" if "/" in manifest["path"] else ""
            _fixed(row["normalized_relative_path"], prefix + path, "normalized_target_path")
            relative_path(row["normalized_relative_path"], "normalized_target_path")
            _fixed(row["target_path_declared"], True, "target_path_declared")
            _fixed(row["extraction_status"], "explicit_path_declared", "target_extraction_status")
        fingerprint = record_digest({key: row[key] for key in TARGET_FIELDS if key != "source_fingerprint"})
        _fixed(row["source_fingerprint"], fingerprint, "target_fingerprint")
        _fixed(row["target_reference"], "target-" + record_digest({key: row[key] for key in (
            "root_id", "pinned_commit", "manifest_reference", "manifest_sha256", "toml_field_path")}), "target_identity")
    _unique(identities, "target_references")
    _unique(locations, "target_locations")
    for manifest in manifests:
        actual = [row["toml_field_path"] for row in targets if row["manifest_reference"] == manifest["manifest_id"]]
        _fixed(actual, manifest["target_locations"], "complete_manifest_target_locations")
    return copy.deepcopy(targets)


def validate_source_files(value: object, targets: list, context: dict) -> list:
    files = _array(value, MAX_SOURCE_FILES, "source_files")
    by_target = {row["target_reference"]: row for row in targets}
    pins = {row["root_id"]: row["pinned_commit"] for row in context["source_roots"]}
    identities, paths, entries = [], [], []
    total = 0
    for row in files:
        closed(row, SOURCE_FILE_FIELDS, "source_file_observation")
        identities.append(_epf(row["source_file_reference"], "source_file_reference"))
        _fixed(row["root_id"], "termivar", "source_file_root")
        _fixed(row["pinned_commit"], pins[row["root_id"]], "source_file_pin")
        relative_path(row["path"], "source_file_path")
        paths.append((row["root_id"], row["pinned_commit"], row["path"]))
        selected = _allowlist(row["allowlist_entries"])
        if not selected:
            _fail("source_observation_without_allowlist")
        entries.extend(selected)
        for entry in selected:
            for field in ("source_file_reference", "root_id", "pinned_commit", "path"):
                _fixed(entry[field], row[field], "observed_allowlist_identity")
            if entry["target_reference"] not in by_target:
                _fail("allowlist_target_reference")
            target = by_target[entry["target_reference"]]
            if not target["target_path_declared"]:
                _fail("allowlist_without_explicit_target_path")
            _fixed(entry["manifest_reference"], target["manifest_reference"], "allowlist_target_manifest")
            _fixed(entry["path"], target["normalized_relative_path"], "allowlist_target_path")
            _fixed(entry["root_id"], target["root_id"], "allowlist_target_root")
            _fixed(entry["pinned_commit"], target["pinned_commit"], "allowlist_target_pin")
        _enum(row["read_status"], ("present_and_hashed", "declared_file_missing"), "source_read_status")
        if row["read_status"] == "present_and_hashed":
            _fixed(row["source_file_presence"], "present", "source_file_presence")
            _fixed(row["regular_file"], True, "regular_file")
            size = integer(row["observed_byte_size"], "observed_byte_size", MAX_TARGET_BYTES)
            total += size
            sha256(row["observed_sha256"], "observed_source_hash")
            for entry in selected:
                if size > entry["max_bytes"]:
                    _fail("observed_allowlist_size_limit")
                if entry["expected_sha256"] is not None:
                    _fixed(row["observed_sha256"], entry["expected_sha256"], "observed_expected_hash")
        else:
            _fixed(row["source_file_presence"], "missing", "missing_source_presence")
            _fixed(row["regular_file"], None, "missing_regular_file")
            _fixed(row["observed_byte_size"], None, "missing_source_size")
            _fixed(row["observed_sha256"], None, "missing_source_hash")
    _unique(identities, "source_file_references")
    _unique(paths, "source_file_identities")
    _allowlist(entries)
    if total > MAX_TOTAL_TARGET_BYTES:
        _fail("total_target_bytes")
    return copy.deepcopy(files)


def validate_inputs(context: object, manifests: object, targets: object, source_files: object) -> None:
    checked_context = validate_context(context)
    checked_manifests = validate_manifests(manifests, checked_context)
    checked_targets = validate_targets(targets, checked_manifests)
    validate_source_files(source_files, checked_targets, checked_context)


def _status_counts(value: object) -> list:
    rows = _array(value, len(COVERAGE_STATUSES), "coverage_status_counts", len(COVERAGE_STATUSES))
    for expected, row in zip(COVERAGE_STATUSES, rows):
        closed(row, ("status", "target_count"), "coverage_status_count")
        _fixed(row["status"], expected, "coverage_status_order")
        integer(row["target_count"], "coverage_status_count", MAX_TARGETS)
    return rows


def _code_list(value: object, choices: tuple, label: str) -> list:
    rows = _ids(value, len(choices), label)
    for row in rows:
        _enum(row, choices, label)
    return rows


def validate_coverage(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "source_context", "manifests", "targets", "source_files", "coverage", "counts", "limitations"), "coverage")
    ref = _common(root, COVERAGE_SCHEMA)
    validate_inputs(root["source_context"], root["manifests"], root["targets"], root["source_files"])
    context = root["source_context"]
    _fixed({row["root_id"]: row["pinned_commit"] for row in context["source_roots"]}, ref["source_commits"], "context_source_pins")
    records = _array(root["coverage"], MAX_TARGETS, "coverage_records")
    _fixed(len(records), len(root["targets"]), "complete_target_coverage_count")
    target_by_id = {row["target_reference"]: row for row in root["targets"]}
    observations = {row["source_file_reference"]: row for row in root["source_files"]}
    file_ids = {row["file_id"] for row in context["files"]}
    component_ids = {row["component_id"] for row in context["components"]}
    seen = []
    statuses = Counter()
    for expected_target, row in zip(root["targets"], records):
        closed(row, ("coverage_reference", "target_reference", "manifest_reference", "root_id", "pinned_commit", "target_kind",
                     "declared_target_name", "declared_relative_path", "normalized_relative_path", "source_file_reference",
                     "allowlist_status", "source_file_presence", "observed_byte_size", "observed_sha256", "phase24_source_reference",
                     "phase24_catalog_status", "phase24_identity_status", "component_source_status", "referencing_component_ids",
                     "phase24_manifest_contexts", "phase24_coverage_status", "component_ownership_status", "manifest_ownership_status",
                     "candidate_component_ids", "established_component_id", "source_evidence_status", "limitations"), "coverage_record")
        _fixed(row["target_reference"], expected_target["target_reference"], "coverage_target_order")
        seen.append(_digest_id(row["coverage_reference"], "coverage-", "coverage_reference"))
        _fixed(row["coverage_reference"], "coverage-" + record_digest({"target_reference": row["target_reference"]}), "coverage_identity")
        target = target_by_id[row["target_reference"]]
        for field in ("manifest_reference", "root_id", "pinned_commit", "target_kind", "declared_target_name", "declared_relative_path", "normalized_relative_path"):
            _fixed(row[field], target[field], "coverage_target_relationship")
        _epf(row["source_file_reference"], "coverage_source_file_reference", nullable=True)
        if row["source_file_reference"] is not None and row["source_file_reference"] not in observations:
            _fail("coverage_source_file_reference")
        _enum(row["allowlist_status"], ("matched", "not_allowlisted", "not_applicable"), "allowlist_status")
        _enum(row["source_file_presence"], ("present", "missing", "not_established"), "source_file_presence")
        if row["observed_byte_size"] is not None:
            integer(row["observed_byte_size"], "coverage_observed_size", MAX_TARGET_BYTES)
        sha256(row["observed_sha256"], "coverage_observed_hash", nullable=True)
        _f_ref(row["phase24_source_reference"], "coverage_phase24_reference", nullable=True)
        if row["phase24_source_reference"] is not None and row["phase24_source_reference"] not in file_ids:
            _fail("coverage_phase24_reference")
        _enum(row["phase24_catalog_status"], ("listed_in_global_f_catalog", "not_listed_in_global_f_catalog", "scope_classification_unknown"), "catalog_status")
        _enum(row["phase24_identity_status"], ("matched", "mismatch", "not_compared", "not_in_catalog"), "phase24_identity_status")
        _enum(row["component_source_status"], ("referenced_by_component", "not_referenced_by_component", "scope_classification_unknown"), "component_source_status")
        for field in ("referencing_component_ids", "candidate_component_ids"):
            if not set(_ids(row[field], MAX_COMPONENTS, field)) <= component_ids:
                _fail("coverage_component_reference")
        contexts = _array(row["phase24_manifest_contexts"], MAX_F_REFERENCES, "phase24_manifest_contexts")
        for item in contexts:
            closed(item, MANIFEST_REF_FIELDS, "phase24_manifest_context")
            if item not in context["dependency_manifest_refs"]:
                _fail("phase24_manifest_context_reference")
        statuses[_enum(row["phase24_coverage_status"], COVERAGE_STATUSES, "coverage_status")] += 1
        _enum(row["component_ownership_status"], ("component_ownership_unresolved", "component_ownership_established"), "component_ownership_status")
        _enum(row["manifest_ownership_status"], OWNERSHIP_STATUSES, "manifest_ownership_status")
        if row["established_component_id"] is not None:
            identifier(row["established_component_id"], "established_component_id")
            if row["established_component_id"] not in component_ids:
                _fail("established_component_reference")
        _enum(row["source_evidence_status"], ("source_hash_observed", "source_file_missing", "read_not_performed", "entrypoint_not_established"), "source_evidence_status")
        _code_list(row["limitations"], LIMITATIONS, "coverage_limitations")
    _unique(seen, "coverage_references")
    counts = closed(root["counts"], ("manifest_count", "target_count", "explicit_path_target_count", "source_file_observation_count",
                                     "present_and_hashed_source_file_count", "missing_source_file_count", "observed_source_bytes",
                                     "global_f_catalog_count", "component_referenced_file_count", "unresolved_ownership_target_count",
                                     "by_coverage_status"), "coverage_counts")
    expected_counts = {
        "manifest_count": len(root["manifests"]), "target_count": len(root["targets"]),
        "explicit_path_target_count": sum(row["target_path_declared"] for row in root["targets"]),
        "source_file_observation_count": len(root["source_files"]),
        "present_and_hashed_source_file_count": sum(row["read_status"] == "present_and_hashed" for row in root["source_files"]),
        "missing_source_file_count": sum(row["read_status"] == "declared_file_missing" for row in root["source_files"]),
        "observed_source_bytes": sum(row["observed_byte_size"] or 0 for row in root["source_files"]),
        "global_f_catalog_count": len(context["files"]),
        "component_referenced_file_count": len({ref for row in context["components"] for ref in row["source_file_refs"]}),
        "unresolved_ownership_target_count": sum(row["component_ownership_status"] == "component_ownership_unresolved" for row in records),
    }
    for field, expected in expected_counts.items():
        _fixed(counts[field], expected, "coverage_count")
    _status_counts(counts["by_coverage_status"])
    for row in counts["by_coverage_status"]:
        _fixed(row["target_count"], statuses[row["status"]], "coverage_status_count")
    _fixed(root["limitations"], list(LIMITATIONS), "coverage_limitations")
    return copy.deepcopy(root)


def validate_delta(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "proposals", "counts", "limitations"), "delta")
    ref = _common(root, DELTA_SCHEMA)
    proposals = _array(root["proposals"], MAX_PROPOSALS, "proposals")
    references, identities = [], []
    target_ref_count = 0
    source_refs = []
    for row in proposals:
        closed(row, ("proposal_reference", "source_target_reference", "source_target_references", "manifest_references",
                     "source_file_reference", "root_id", "pinned_commit", "path", "observed_byte_size", "observed_sha256",
                     "current_phase24_coverage", "proposed_scope_action", "proposal_level", "proposed_component_id",
                     "supporting_evidence", "ownership_limitation", "application_preconditions", "application_authorized",
                     "application_performed", "phase24_inventory_modified", "component_ownership_verified"), "proposal")
        references.append(_digest_id(row["proposal_reference"], "proposal-", "proposal_reference"))
        targets = _array(row["source_target_references"], MAX_TARGETS, "proposal_target_references", 1)
        for target in targets:
            _digest_id(target, "target-", "proposal_target_reference")
        _unique(targets, "proposal_target_references")
        _fixed(row["source_target_reference"], targets[0] if len(targets) == 1 else None, "proposal_single_target_reference")
        _ids(row["manifest_references"], MAX_MANIFESTS, "proposal_manifest_references")
        source_refs.append(_epf(row["source_file_reference"], "proposal_source_reference"))
        _fixed(row["root_id"], "termivar", "proposal_root")
        _fixed(row["pinned_commit"], ref["source_commits"]["termivar"], "proposal_pin")
        relative_path(row["path"], "proposal_path")
        integer(row["observed_byte_size"], "proposal_source_size", MAX_TARGET_BYTES)
        sha256(row["observed_sha256"], "proposal_source_hash")
        payload = {key: row[key] for key in ("root_id", "pinned_commit", "path", "observed_byte_size", "observed_sha256")}
        _fixed(row["proposal_reference"], "proposal-" + record_digest(payload), "proposal_identity")
        identities.append((row["root_id"], row["pinned_commit"], row["path"]))
        _fixed(row["current_phase24_coverage"], "source_present_inventory_gap", "proposal_current_coverage")
        _fixed(row["proposed_scope_action"], "propose_selected_source_inclusion", "proposal_action")
        _fixed(row["proposal_level"], "repository_source_coverage", "proposal_level")
        _fixed(row["proposed_component_id"], None, "proposal_component_assignment")
        evidence = closed(row["supporting_evidence"], ("coverage_references", "manifest_references", "source_file_reference",
                                                     "source_hash_observed", "explicit_allowlist"), "proposal_supporting_evidence")
        coverage_refs = _array(evidence["coverage_references"], MAX_TARGETS, "proposal_coverage_references", 1)
        for coverage in coverage_refs:
            _digest_id(coverage, "coverage-", "proposal_coverage_reference")
        _unique(coverage_refs, "proposal_coverage_references")
        _fixed(evidence["manifest_references"], row["manifest_references"], "proposal_manifest_evidence")
        _fixed(evidence["source_file_reference"], row["source_file_reference"], "proposal_file_evidence")
        _fixed(evidence["source_hash_observed"], True, "proposal_hash_observed")
        _fixed(evidence["explicit_allowlist"], True, "proposal_allowlist_evidence")
        _enum(row["ownership_limitation"], ("component_ownership_unresolved", "scope_inclusion_does_not_verify_component_ownership"), "proposal_ownership_limitation")
        _fixed(row["application_preconditions"], list(APPLICATION_PRECONDITIONS), "proposal_preconditions")
        for flag in ("application_authorized", "application_performed", "phase24_inventory_modified", "component_ownership_verified"):
            _fixed(row[flag], False, "proposal_" + flag)
        target_ref_count += len(targets)
    _unique(references, "proposal_references")
    _unique(identities, "proposal_source_identities")
    counts = closed(root["counts"], ("unique_proposal_count", "proposal_target_reference_count", "proposal_source_file_count",
                                     "application_authorized_count", "application_performed_count"), "delta_counts")
    for field, expected in (("unique_proposal_count", len(proposals)), ("proposal_target_reference_count", target_ref_count),
                            ("proposal_source_file_count", len(set(source_refs))), ("application_authorized_count", 0), ("application_performed_count", 0)):
        _fixed(counts[field], expected, "delta_count")
    _fixed(root["limitations"], list(LIMITATIONS), "delta_limitations")
    return copy.deepcopy(root)


def validate_variants(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "variants", "comparisons", "counts", "limitations"), "variants")
    _common(root, VARIANTS_SCHEMA)
    variants = _array(root["variants"], MAX_VARIANTS, "variants", 1)
    identities = []
    target_refs, proposal_refs = set(), set()
    variant_target_count = 0
    for row in variants:
        closed(row, (*VARIANT_FIELDS, "target_projections", "proposal_references", "counts", "demo_only", *FALSE_FLAGS), "variant")
        identities.append(identifier(row["variant_id"], "variant_id"))
        text(row["label"], "variant_label", 128)
        text(row["description"], "variant_description", 1024)
        selected = _ids(row["selected_component_ids"], MAX_COMPONENTS, "selected_components")
        omitted = _ids(row["not_selected_component_ids"], MAX_COMPONENTS, "not_selected_components")
        if not selected or set(selected) & set(omitted):
            _fail("variant_component_partition")
        _fixed(row["demo_only"], True, "variant_demo_only")
        for flag in FALSE_FLAGS:
            _fixed(row[flag], False, "variant_" + flag)
        projections = _array(row["target_projections"], MAX_TARGETS, "target_projections")
        current_targets = []
        statuses, relationships = Counter(), Counter()
        projected_proposals = set()
        for projection in projections:
            closed(projection, ("target_reference", "coverage_reference", "source_file_reference", "phase24_coverage_status",
                                "component_ownership_status", "relationship", "proposal_references"), "variant_target_projection")
            current_targets.append(_digest_id(projection["target_reference"], "target-", "projected_target_reference"))
            _digest_id(projection["coverage_reference"], "coverage-", "projected_coverage_reference")
            _epf(projection["source_file_reference"], "projected_source_file_reference", nullable=True)
            statuses[_enum(projection["phase24_coverage_status"], COVERAGE_STATUSES, "projected_coverage_status")] += 1
            _enum(projection["component_ownership_status"], ("component_ownership_unresolved", "component_ownership_established"), "projected_ownership_status")
            relationships[_enum(projection["relationship"], ("definite_source_metadata_scope", "candidate_scope_relevant_ownership_unresolved",
                                                            "no_selected_component_relation_established"), "variant_relationship")] += 1
            refs = _array(projection["proposal_references"], MAX_PROPOSALS, "projected_proposal_references")
            for proposal in refs:
                _digest_id(proposal, "proposal-", "projected_proposal_reference")
            _unique(refs, "projected_proposal_references")
            projected_proposals.update(refs)
        _unique(current_targets, "variant_target_references")
        target_refs.update(current_targets)
        variant_target_count += len(current_targets)
        refs = _array(row["proposal_references"], MAX_PROPOSALS, "variant_proposal_references")
        for proposal in refs:
            _digest_id(proposal, "proposal-", "variant_proposal_reference")
        _unique(refs, "variant_proposal_references")
        if set(refs) != projected_proposals:
            _fail("variant_proposal_projection")
        proposal_refs.update(refs)
        counts = closed(row["counts"], ("target_reference_count", "definite_source_metadata_target_count", "ownership_unresolved_candidate_target_count",
                                       "unattributed_target_count", "proposal_reference_count", "by_coverage_status"), "variant_counts")
        for field, expected in (("target_reference_count", len(projections)),
                                ("definite_source_metadata_target_count", relationships["definite_source_metadata_scope"]),
                                ("ownership_unresolved_candidate_target_count", relationships["candidate_scope_relevant_ownership_unresolved"]),
                                ("unattributed_target_count", relationships["no_selected_component_relation_established"]),
                                ("proposal_reference_count", len(refs))):
            _fixed(counts[field], expected, "variant_count")
        _status_counts(counts["by_coverage_status"])
        for item in counts["by_coverage_status"]:
            _fixed(item["target_count"], statuses[item["status"]], "variant_coverage_count")
    _unique(identities, "variant_ids")
    comparisons = _array(root["comparisons"], MAX_VARIANTS * (MAX_VARIANTS - 1) // 2, "comparisons")
    _fixed(len(comparisons), len(variants) * (len(variants) - 1) // 2, "comparison_count")
    seen = []
    for row in comparisons:
        closed(row, ("left", "right", "shared_component_ids", "only_left_component_ids", "only_right_component_ids",
                     "shared_target_references", "only_left_target_references", "only_right_target_references",
                     "shared_proposal_references", "only_left_proposal_references", "only_right_proposal_references"), "comparison")
        if row["left"] not in identities or row["right"] not in identities or row["left"] == row["right"]:
            _fail("comparison_variant_reference")
        seen.append(frozenset((row["left"], row["right"])))
        for field in ("shared_component_ids", "only_left_component_ids", "only_right_component_ids"):
            _ids(row[field], MAX_COMPONENTS, field)
        for field in ("shared_target_references", "only_left_target_references", "only_right_target_references"):
            refs = _array(row[field], MAX_TARGETS, field)
            for ref in refs:
                _digest_id(ref, "target-", field)
            _unique(refs, field)
        for field in ("shared_proposal_references", "only_left_proposal_references", "only_right_proposal_references"):
            refs = _array(row[field], MAX_PROPOSALS, field)
            for ref in refs:
                _digest_id(ref, "proposal-", field)
            _unique(refs, field)
    _unique(seen, "comparison_pairs")
    counts = closed(root["counts"], ("variant_count", "global_target_count", "global_proposal_count", "variant_target_reference_count"), "variant_projection_counts")
    for field, expected in (("variant_count", len(variants)), ("global_target_count", len(target_refs)),
                            ("variant_target_reference_count", variant_target_count)):
        _fixed(counts[field], expected, "variant_projection_count")
    global_proposal_count = integer(counts["global_proposal_count"], "global_proposal_count", MAX_PROPOSALS)
    if len(proposal_refs) > global_proposal_count:
        _fail("referenced_proposals_exceed_global_count")
    _fixed(root["limitations"], list(LIMITATIONS), "variant_limitations")
    return copy.deepcopy(root)


def validate_documents(coverage: object, delta: object, variants: object) -> None:
    checked, proposals, projection = validate_coverage(coverage), validate_delta(delta), validate_variants(variants)
    for document in (proposals, projection):
        _fixed(document["source_reference"], checked["source_reference"], "source_reference_relationship")
    _fixed(projection["counts"]["global_proposal_count"], len(proposals["proposals"]), "global_proposal_count_relationship")
    from .source_coverage import rebuild_coverage
    from .scope_delta import build_delta
    from .variant_projection import build_variants
    _fixed(checked, rebuild_coverage(checked), "coverage_projection")
    _fixed(proposals, build_delta(checked), "delta_projection")
    _fixed(projection, build_variants(checked, proposals), "variant_projection")
