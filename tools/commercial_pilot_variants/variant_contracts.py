"""Closed offline variant metadata; source exposure is never build inclusion."""
from __future__ import annotations

from collections import Counter
import copy
import re

from commercial_composition.composition_contracts import (
    InputError, CANDIDATE_REFERENCE as COMPOSITION_CANDIDATE_REFERENCE,
    COMPONENT_FIELDS, DEPENDENCY_FIELDS, ROOT_IDS, ROLES, VERSION_SCOPES,
    BLOCKER_CODES, closed, text, integer, identifier, relative_path, sha256,
    parse_json, json_bytes,
)
from commercial_license_review.evidence_contracts import (
    SOURCE_FIELDS as EVIDENCE_FIELDS, BINDING_FIELDS, SUBJECT_FIELDS, RECORD_FIELDS,
    REASON_CODES, EVIDENCE_STATUSES, REVIEW_STATUSES, PRODUCT_SCOPES, QUEUE_GROUPS,
    NEXT_HUMAN_ACTIONS, CONFLICT_CATEGORIES, source_key_for, validate_subject,
    common as evidence_common, validate_documents as validate_evidence_documents,
    record_digest,
)

SCOPE_SCHEMA = "termivar-offline-pilot-variant-scope/v1"
ANALYSIS_SCHEMA = "termivar-offline-pilot-variant-analysis/v1"
DEPENDENCIES_SCHEMA = "termivar-offline-dependency-exposure/v1"
LICENSES_SCHEMA = "termivar-offline-pilot-license-readiness/v1"
MANIFEST_SCHEMA = "termivar-offline-pilot-variant-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-pilot-variant-inspection/v1"
DEMO_LABEL = "DEMONSTRATION ONLY — PILOT VARIANT ANALYSIS — NO BUILD OR DISTRIBUTION AUTHORIZED"
FALSE_FLAGS = (
    "dependency_closure_verified", "license_review_completed", "redistribution_authorized",
    "build_verified", "runtime_verified", "producer_verified", "release_authorized",
    "production_ready", "human_review_verified",
)
MAX_SCOPE_BYTES = 128 * 1024
MAX_SOURCE_BYTES = 6 * 1024 * 1024
MAX_COMPONENTS = 64
MAX_RECORDS = 2000
MAX_VARIANTS = 4
MAX_COMPARISON_PAIRS = 6
EXPOSURE_CLASSES = (
    "explicit_component_link", "declared_source_scope", "shared_or_ambiguous_scope",
    "unattributed_record", "excluded_context_record", "insufficient_dependency_evidence",
)
LICENSE_RELATIONS = (
    "selected_component", "not_selected_component", "related_dependency_scope",
    "unattributed_dependency", "excluded_context",
)
BLOCKER_RELATIONS = (*LICENSE_RELATIONS, "candidate_scope_unassigned")
SCOPE_LIMITATIONS = (
    "explicit_source_files_and_artifact_metadata_only",
    "no_explicit_component_dependency_links_in_source_contract",
    "potential_file_reference_association_is_not_build_inclusion",
    "workspace_lock_is_not_selected_feature_or_binary_closure",
    "license_evidence_is_not_legal_or_release_authority",
    "internal_consistency_is_not_independent_source_attestation",
    "unattributed_or_excluded_does_not_mean_runtime_absent",
)
SOURCE_COUNT_FIELDS = (
    "component_count", "dependency_record_count", "license_record_count", "base_unknown_license_count",
    "evidence_present_record_count", "missing_evidence_record_count",
)
MANIFEST_FIELDS = ("manifest_id", "root_id", "path", "format", "context", "sha256", "bytes",
                   "parse_status", "record_count", "limitation_code", "source_file_ref")
COMPONENT_CATALOG_FIELDS = (*COMPONENT_FIELDS, "manifest_file_ref", "source_json_pointer",
                            "source_record_sha256", "source_artifact_sha256", "license_source_key")
DEPENDENCY_RECORD_FIELDS = (*DEPENDENCY_FIELDS, "source_json_pointer", "source_record_sha256",
                            "source_artifact_sha256", "manifest_file_ref", "license_source_key",
                            "potential_component_ids", "exposures")
READINESS_RECORD_FIELDS = tuple(dict.fromkeys((*SUBJECT_FIELDS, *RECORD_FIELDS, "queue_groups",
                                             "next_human_action", "source_blocker_codes", "variant_relations")))
COMMON_FIELDS = ("schema_version", "candidate_reference", "demo_label", "demo_only", *FALSE_FLAGS)
VARIANT_SCOPE_FIELDS = ("variant_id", "label", "description", "selected_component_ids", "not_selected_component_ids")
COMPOSITION_SOURCE_SCHEMAS = {
    "inventory": "termivar-offline-composition/v1",
    "dependencies": "termivar-offline-dependency-license-ledger/v1",
    "constraints": "termivar-offline-release-constraints/v1", "summary": None,
    "manifest": "termivar-offline-composition-manifest/v1",
}
EVIDENCE_SOURCE_SCHEMAS = {
    "ledger": "termivar-license-evidence-ledger/v1", "queue": "termivar-license-review-queue/v1",
    "conflicts": "termivar-license-binding-conflicts/v1", "summary": None,
    "manifest": "termivar-license-evidence-manifest/v1",
}


def _fail(label: str) -> None:
    raise InputError("pilot_variant_invalid_" + label)


def _fixed(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        _fail(label)


def _enum(value: object, values: object, label: str) -> str:
    if type(value) is not str or value not in values:
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
    if (type(value) is not str or re.fullmatch(r"F[0-9]{4}", value) is None
            or not 1 <= int(value[1:]) <= 5000):
        _fail(label)
    return value


def _file_refs(value: object, label: str) -> list[str]:
    refs = _array(value, 5000, label)
    for ref in refs:
        _file_ref(ref, label)
    _unique(refs, label)
    return refs


def _candidate(value: object) -> str:
    result = identifier(value, "candidate_reference")
    if not result.startswith("DEMO-"):
        _fail("candidate_reference")
    return result


def common(schema: str, candidate_reference: str) -> dict:
    _enum(schema, (ANALYSIS_SCHEMA, DEPENDENCIES_SCHEMA, LICENSES_SCHEMA, MANIFEST_SCHEMA, INSPECTION_SCHEMA), "schema")
    return {"schema_version": schema, "candidate_reference": _candidate(candidate_reference),
            "demo_label": DEMO_LABEL, "demo_only": True, **{name: False for name in FALSE_FLAGS}}


def _common(value: dict, schema: str) -> None:
    for field, fixed in common(schema, value["candidate_reference"]).items():
        _fixed(value[field], fixed, "common_" + field)


def validate_source_group(value: object, group: str) -> dict:
    _enum(group, ("composition", "evidence"), "source_group_kind")
    schemas = COMPOSITION_SOURCE_SCHEMAS if group == "composition" else EVIDENCE_SOURCE_SCHEMAS
    rows = closed(value, schemas, "source_group")
    for role, schema in schemas.items():
        row = closed(rows[role], ("schema_version", "bytes", "sha256"), "source_identity")
        _fixed(row["schema_version"], schema, "source_schema")
        maximum = 512 * 1024 if role == "summary" else 64 * 1024 if role == "manifest" else 1024 * 1024
        if integer(row["bytes"], "source_bytes", maximum) == 0:
            _fail("source_bytes")
        sha256(row["sha256"], "source_hash")
    return copy.deepcopy(rows)


def validate_source_reference(value: object) -> dict:
    ref = closed(value, ("composition_candidate_reference", "source_commits", "composition_sources", "evidence_sources"), "source_reference")
    _fixed(ref["composition_candidate_reference"], COMPOSITION_CANDIDATE_REFERENCE, "composition_candidate_reference")
    commits = closed(ref["source_commits"], ("termivar", "platform"), "source_commits")
    for pin in commits.values():
        if type(pin) is not str or re.fullmatch(r"[0-9a-f]{40}", pin) is None:
            _fail("source_commit")
    validate_source_group(ref["composition_sources"], "composition")
    validate_source_group(ref["evidence_sources"], "evidence")
    if sum(row["bytes"] for group in (ref["composition_sources"], ref["evidence_sources"]) for row in group.values()) > MAX_SOURCE_BYTES:
        _fail("total_source_bytes")
    return copy.deepcopy(ref)


def _variant_selection(row: object) -> dict:
    row = closed(row, VARIANT_SCOPE_FIELDS, "variant_selection")
    identifier(row["variant_id"], "variant_id")
    text(row["label"], "variant_label", 128)
    text(row["description"], "variant_description", 1024)
    selected = _ids(row["selected_component_ids"], MAX_COMPONENTS, "selected_component_ids")
    not_selected = _ids(row["not_selected_component_ids"], MAX_COMPONENTS, "not_selected_component_ids")
    if set(selected) & set(not_selected) or not selected or len(selected) + len(not_selected) > MAX_COMPONENTS:
        _fail("component_partition")
    return row


def _pairs(rows: object, variant_ids: list[str]) -> list:
    rows = _array(rows, MAX_COMPARISON_PAIRS, "comparison_pairs")
    seen = []
    for row in rows:
        closed(row, ("left", "right"), "comparison_pair")
        for field in ("left", "right"):
            identifier(row[field], "pair_variant_id")
            if row[field] not in variant_ids:
                _fail("pair_variant_reference")
        if row["left"] == row["right"]:
            _fail("self_comparison")
        seen.append(frozenset((row["left"], row["right"])))
    _unique(seen, "duplicate_unordered_pair")
    return rows


def validate_scope(value: object) -> dict:
    raw = json_bytes(value, maximum=MAX_SCOPE_BYTES)
    root = closed(value, ("schema_version", "mode", "candidate_reference", "composition_sources", "evidence_sources",
                          "variants", "comparison_pairs", "inspection_constraints"), "scope")
    _fixed(root["schema_version"], SCOPE_SCHEMA, "scope_schema")
    _fixed(root["mode"], "demo", "scope_mode")
    _candidate(root["candidate_reference"])
    validate_source_group(root["composition_sources"], "composition")
    validate_source_group(root["evidence_sources"], "evidence")
    variants = _array(root["variants"], MAX_VARIANTS, "variants", 1)
    for row in variants:
        _variant_selection(row)
    variant_ids = [row["variant_id"] for row in variants]
    _unique(variant_ids, "variant_ids")
    partitions = [set(row["selected_component_ids"]) | set(row["not_selected_component_ids"]) for row in variants]
    if any(partition != partitions[0] for partition in partitions):
        _fail("variant_catalog_partition")
    _pairs(root["comparison_pairs"], variant_ids)
    limits = closed(root["inspection_constraints"], ("max_source_bytes", "max_components", "max_records", "max_variants", "max_comparison_pairs"), "inspection_constraints")
    for field, expected in (("max_source_bytes", MAX_SOURCE_BYTES), ("max_components", MAX_COMPONENTS),
                            ("max_records", MAX_RECORDS), ("max_variants", MAX_VARIANTS), ("max_comparison_pairs", MAX_COMPARISON_PAIRS)):
        _fixed(limits[field], expected, "inspection_limit")
    if len(raw) + sum(row["bytes"] for group in (root["composition_sources"], root["evidence_sources"]) for row in group.values()) > MAX_SOURCE_BYTES:
        _fail("total_source_bytes")
    return copy.deepcopy(root)


def _counts(value: object, fields: object, label: str, maximum: int = MAX_RECORDS * 9) -> dict:
    row = closed(value, fields, label)
    for item in row.values():
        integer(item, label, maximum)
    return row


def _source_key(value: object, label: str) -> str:
    if type(value) is not str or re.fullmatch(r"termivar-license-binding/v1:[0-9a-f]{64}", value) is None:
        _fail(label)
    return value


def _code_counts(rows: object) -> list:
    rows = _array(rows, len(BLOCKER_CODES), "blocker_code_counts", len(BLOCKER_CODES))
    seen = []
    for expected, row in zip(BLOCKER_CODES, rows):
        closed(row, ("code", "record_count"), "blocker_code_count")
        seen.append(_enum(row["code"], BLOCKER_CODES, "blocker_code"))
        _fixed(row["code"], expected, "blocker_code_order")
        integer(row["record_count"], "blocker_record_count", MAX_RECORDS * 9)
    _unique(seen, "blocker_codes")
    return rows


def _license_summary(value: object) -> dict:
    row = closed(value, ("global_source_record_count", "global_unknown_license_count", "by_relation"), "license_summary")
    integer(row["global_source_record_count"], "global_license_records", MAX_RECORDS)
    integer(row["global_unknown_license_count"], "global_unknown_records", MAX_RECORDS)
    relations = _array(row["by_relation"], len(LICENSE_RELATIONS), "license_relation_counts", len(LICENSE_RELATIONS))
    for expected, relation in zip(LICENSE_RELATIONS, relations):
        closed(relation, ("relation", "record_count", "unknown_license_count", "evidence_present_record_count",
                          "missing_evidence_record_count", "human_review_required_record_count",
                          "ambiguous_record_count", "conflicting_record_count", "unsupported_record_count",
                          "unverified_source_record_count"), "license_relation_count")
        _fixed(relation["relation"], expected, "license_relation_order")
        for field in relation:
            if field != "relation":
                integer(relation[field], "license_relation_count", MAX_RECORDS)
        if any(relation[field] > relation["record_count"] for field in relation if field not in ("relation", "record_count")):
            _fail("license_relation_denominator")
    _fixed(sum(item["record_count"] for item in relations), row["global_source_record_count"], "license_relation_total")
    _fixed(sum(item["unknown_license_count"] for item in relations), row["global_unknown_license_count"], "unknown_relation_total")
    return row


def _open_blockers(value: object) -> dict:
    row = closed(value, ("source_blocker_count", "by_code", "by_relation"), "open_blockers")
    integer(row["source_blocker_count"], "source_blocker_count", MAX_RECORDS * 9)
    _code_counts(row["by_code"])
    _fixed(sum(item["record_count"] for item in row["by_code"]), row["source_blocker_count"], "blocker_code_total")
    relations = _array(row["by_relation"], len(BLOCKER_RELATIONS), "blocker_relations", len(BLOCKER_RELATIONS))
    for expected, item in zip(BLOCKER_RELATIONS, relations):
        closed(item, ("relation", "blocker_count", "by_code"), "blocker_relation")
        _fixed(item["relation"], expected, "blocker_relation_order")
        integer(item["blocker_count"], "blocker_count", MAX_RECORDS * 9)
        _code_counts(item["by_code"])
        _fixed(sum(code["record_count"] for code in item["by_code"]), item["blocker_count"], "relation_blocker_total")
    _fixed(sum(item["blocker_count"] for item in relations), row["source_blocker_count"], "blocker_relation_total")
    return row


def _class_counts(value: object) -> list:
    rows = _array(value, len(EXPOSURE_CLASSES), "classifications", len(EXPOSURE_CLASSES))
    for expected, row in zip(EXPOSURE_CLASSES, rows):
        closed(row, ("classification", "record_count"), "classification_count")
        _fixed(row["classification"], expected, "classification_order")
        integer(row["record_count"], "classification_count", MAX_RECORDS)
    return rows


def _analysis_variant(value: object) -> dict:
    row = closed(value, (*VARIANT_SCOPE_FIELDS, "source_reference_ref", "demo_only", *FALSE_FLAGS,
                         "dependency_exposure_counts", "license_summary", "open_blockers"), "analysis_variant")
    _variant_selection({key: row[key] for key in VARIANT_SCOPE_FIELDS})
    _fixed(row["source_reference_ref"], "/source_reference", "source_reference_ref")
    _fixed(row["demo_only"], True, "variant_demo_only")
    for flag in FALSE_FLAGS:
        _fixed(row[flag], False, "variant_" + flag)
    _class_counts(row["dependency_exposure_counts"])
    _license_summary(row["license_summary"])
    _open_blockers(row["open_blockers"])
    return row


def validate_analysis(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "source_reference", "source_counts", "component_catalog", "manifest_catalog",
                          "variants", "comparison_pairs", "comparisons", "scope_limitations"), "analysis")
    _common(root, ANALYSIS_SCHEMA)
    ref = validate_source_reference(root["source_reference"])
    _counts(root["source_counts"], SOURCE_COUNT_FIELDS, "source_counts", MAX_RECORDS)
    components = _array(root["component_catalog"], MAX_COMPONENTS, "component_catalog", 1)
    ids = []
    for index, row in enumerate(components):
        closed(row, COMPONENT_CATALOG_FIELDS, "component_catalog_record")
        ids.append(identifier(row["component_id"], "component_id"))
        _enum(row["root_id"], ROOT_IDS, "component_root")
        text(row["repository_label"], "repository_label", 128)
        _fixed(row["pinned_commit"], ref["source_commits"][row["root_id"]], "component_pin")
        _enum(row["role"], ROLES, "component_role")
        if row["manifest_path"] is not None:
            relative_path(row["manifest_path"], "component_manifest")
        _file_refs(row["source_file_refs"], "component_file_refs")
        text(row["version_declaration"], "version_declaration", nullable=True)
        _enum(row["version_scope"], VERSION_SCOPES, "version_scope")
        _fixed(row["source_present"], True, "source_present")
        _fixed(row["distribution_status"], "proposed_source_only", "distribution_status")
        _file_ref(row["manifest_file_ref"], "component_manifest_ref")
        if row["manifest_file_ref"] not in row["source_file_refs"]:
            _fail("component_manifest_association")
        _fixed(row["source_json_pointer"], f"/components/{index}", "component_pointer")
        sha256(row["source_record_sha256"], "component_record_hash")
        _fixed(row["source_artifact_sha256"], ref["composition_sources"]["inventory"]["sha256"], "component_artifact_hash")
        _source_key(row["license_source_key"], "component_license_key")
        _fixed(row["source_record_sha256"], record_digest({key: row[key] for key in COMPONENT_FIELDS}), "component_projection_digest")
    _unique(ids, "component_ids")
    _fixed(root["source_counts"]["component_count"], len(components), "component_count")
    manifests = _array(root["manifest_catalog"], 5000, "manifest_catalog", 1)
    manifest_ids = []
    manifest_paths = []
    manifest_file_refs = []
    for row in manifests:
        closed(row, MANIFEST_FIELDS, "manifest_catalog_record")
        manifest_ids.append(identifier(row["manifest_id"], "manifest_id"))
        _enum(row["root_id"], ROOT_IDS, "manifest_root")
        relative_path(row["path"], "manifest_path")
        manifest_paths.append((row["root_id"], row["path"]))
        _enum(row["format"], ("cargo_toml", "cargo_lock", "pyproject_toml", "requirements_lock", "unsupported_yaml"), "manifest_format")
        _enum(row["context"], ("selected_source_metadata", "excluded_backend_context"), "manifest_context")
        sha256(row["sha256"], "manifest_hash")
        integer(row["bytes"], "manifest_bytes", 4 * 1024 * 1024)
        _enum(row["parse_status"], ("parsed", "unsupported"), "manifest_parse_status")
        integer(row["record_count"], "manifest_record_count", MAX_RECORDS)
        _enum(row["limitation_code"], ("selected_manifest_declarations_only", "whole_workspace_lock_not_selected_build",
                                      "excluded_backend_context_only", "unsupported_format_not_parsed"), "manifest_limitation")
        _file_ref(row["source_file_ref"], "manifest_file_ref")
        manifest_file_refs.append(row["source_file_ref"])
    _unique(manifest_ids, "manifest_ids")
    _unique(manifest_paths, "manifest_paths")
    _unique(manifest_file_refs, "manifest_file_refs")
    manifest_by_path = {(row["root_id"], row["path"]): row for row in manifests}
    for component in components:
        key = (component["root_id"], component["manifest_path"])
        if key not in manifest_by_path or manifest_by_path[key]["source_file_ref"] != component["manifest_file_ref"]:
            _fail("component_manifest_catalog_relationship")
    variants = _array(root["variants"], MAX_VARIANTS, "variants", 1)
    for row in variants:
        _analysis_variant(row)
        if set(row["selected_component_ids"] + row["not_selected_component_ids"]) != set(ids):
            _fail("variant_complete_component_partition")
    variant_ids = [row["variant_id"] for row in variants]
    _unique(variant_ids, "variant_ids")
    pairs = _pairs(root["comparison_pairs"], variant_ids)
    comparisons = _array(root["comparisons"], MAX_COMPARISON_PAIRS, "comparisons")
    _fixed(len(comparisons), len(pairs), "comparison_count")
    for pair, row in zip(pairs, comparisons):
        closed(row, ("left", "right", "source_reference_ref", "only_left_component_ids", "only_right_component_ids",
                     "shared_component_ids", "component_counts", "dependency_classification_changes",
                     "dependency_classification_change_count", "license_summary_left", "license_summary_right"), "comparison")
        _fixed(row["left"], pair["left"], "comparison_left")
        _fixed(row["right"], pair["right"], "comparison_right")
        _fixed(row["source_reference_ref"], "/source_reference", "comparison_source_reference")
        for field in ("only_left_component_ids", "only_right_component_ids", "shared_component_ids"):
            if any(item not in ids for item in _ids(row[field], MAX_COMPONENTS, field)):
                _fail("comparison_component_reference")
        counts = _counts(row["component_counts"], ("only_left", "only_right", "shared"), "comparison_counts", MAX_COMPONENTS)
        for field in counts:
            _fixed(counts[field], len(row[field + "_component_ids"]), "comparison_component_count")
        changes = _array(row["dependency_classification_changes"], MAX_RECORDS, "classification_changes")
        changed_ids = []
        for change in changes:
            closed(change, ("dependency_id", "left_classification", "right_classification"), "classification_change")
            changed_ids.append(identifier(change["dependency_id"], "changed_dependency_id"))
            _enum(change["left_classification"], EXPOSURE_CLASSES, "left_classification")
            _enum(change["right_classification"], EXPOSURE_CLASSES, "right_classification")
            if change["left_classification"] == change["right_classification"]:
                _fail("unchanged_classification_in_delta")
        _unique(changed_ids, "changed_dependency_ids")
        _fixed(row["dependency_classification_change_count"], len(changes), "classification_change_count")
        _license_summary(row["license_summary_left"])
        _license_summary(row["license_summary_right"])
    _fixed(root["scope_limitations"], list(SCOPE_LIMITATIONS), "scope_limitations")
    return copy.deepcopy(root)


def validate_dependencies(value: object) -> dict:
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "source_reference", "records", "counts", "package_identity_deduplication"), "dependencies")
    _common(root, DEPENDENCIES_SCHEMA)
    ref = validate_source_reference(root["source_reference"])
    _fixed(root["package_identity_deduplication"], "not_performed_records_are_not_unique_packages", "package_deduplication")
    records = _array(root["records"], MAX_RECORDS, "dependency_records")
    variant_ids = None
    by_relation = Counter()
    by_directness = Counter()
    for index, row in enumerate(records):
        closed(row, DEPENDENCY_RECORD_FIELDS, "dependency_record")
        _fixed(row["dependency_id"], f"D{index + 1:04d}", "dependency_id")
        identifier(row["manifest_id"], "dependency_manifest_id")
        _enum(row["ecosystem"], ("rust", "python"), "dependency_ecosystem")
        text(row["name"], "dependency_name", 128)
        text(row["version"], "dependency_version", 128, nullable=True)
        text(row["declared_requirement"], "declared_requirement", 512, nullable=True)
        _enum(row["source_type"], ("registry", "git", "workspace", "declared_index", "unknown"), "dependency_source_type")
        sha256(row["source_checksum"], "dependency_checksum", nullable=True)
        sha256(row["source_identity_sha256"], "dependency_source_identity", nullable=True)
        by_relation[_enum(row["relation"], ("direct_declaration", "lock_record"), "dependency_relation")] += 1
        by_directness[_enum(row["directness"], ("direct_in_selected_manifest", "unknown"), "dependency_directness")] += 1
        _fixed(row["local_package_artifact"], "not_selected_or_verified", "dependency_artifact_status")
        _enum(row["review_scope"], ("selected_source_metadata", "excluded_backend_context"), "dependency_review_scope")
        _fixed(row["source_json_pointer"], f"/dependencies/{index}", "dependency_pointer")
        _fixed(row["source_artifact_sha256"], ref["composition_sources"]["dependencies"]["sha256"], "dependency_artifact_hash")
        _fixed(row["source_record_sha256"], record_digest({key: row[key] for key in DEPENDENCY_FIELDS}), "dependency_projection_digest")
        _file_ref(row["manifest_file_ref"], "dependency_manifest_ref")
        _source_key(row["license_source_key"], "dependency_license_key")
        potential = _ids(row["potential_component_ids"], MAX_COMPONENTS, "potential_component_ids")
        exposures = _array(row["exposures"], MAX_VARIANTS, "dependency_exposures", 1)
        current_ids = []
        for exposure in exposures:
            closed(exposure, ("variant_id", "classification", "reason_code", "selected_potential_component_ids"), "exposure")
            current_ids.append(identifier(exposure["variant_id"], "exposure_variant_id"))
            _enum(exposure["classification"], EXPOSURE_CLASSES, "exposure_classification")
            _enum(exposure["reason_code"], ("excluded_backend_context_preserved", "potential_source_file_shared",
                                           "potential_source_file_single", "no_selected_potential_source_association"), "exposure_reason")
            selected = _ids(exposure["selected_potential_component_ids"], MAX_COMPONENTS, "selected_potential_components")
            if not set(selected) <= set(potential):
                _fail("selected_potential_component_reference")
        _unique(current_ids, "exposure_variant_ids")
        if variant_ids is None:
            variant_ids = current_ids
        _fixed(current_ids, variant_ids, "complete_variant_exposure_projection")
    counts = closed(root["counts"], ("source_dependency_record_count", "variant_count", "by_relation", "by_directness", "by_variant"), "dependency_counts")
    _fixed(counts["source_dependency_record_count"], len(records), "dependency_record_count")
    integer(counts["variant_count"], "dependency_variant_count", MAX_VARIANTS)
    if variant_ids is not None:
        _fixed(counts["variant_count"], len(variant_ids), "dependency_variant_count")
    for field, key, options, expected in (("by_relation", "relation", ("direct_declaration", "lock_record"), by_relation),
                                          ("by_directness", "directness", ("direct_in_selected_manifest", "unknown"), by_directness)):
        grouped = _array(counts[field], len(options), field)
        seen = []
        for row in grouped:
            closed(row, (key, "record_count"), field)
            item = _enum(row[key], options, field)
            seen.append(item)
            _fixed(row["record_count"], expected[item], field)
        _unique(seen, field)
        if set(seen) != set(expected):
            _fail(field)
    grouped_variants = _array(counts["by_variant"], MAX_VARIANTS, "dependency_variant_counts", 1)
    seen = []
    for row in grouped_variants:
        closed(row, ("variant_id", "classifications"), "dependency_variant_count")
        seen.append(identifier(row["variant_id"], "dependency_variant_id"))
        _class_counts(row["classifications"])
        _fixed(sum(item["record_count"] for item in row["classifications"]), len(records), "variant_dependency_membership_total")
    _unique(seen, "dependency_variant_ids")
    _fixed(len(seen), counts["variant_count"], "dependency_variant_count")
    if variant_ids is not None:
        _fixed(seen, variant_ids, "dependency_variant_order")
    return copy.deepcopy(root)


def _legacy_reference(ref: dict) -> dict:
    return {"candidate_reference": ref["composition_candidate_reference"], "source_commits": ref["source_commits"],
            **{role: {key: row[key] for key in ("bytes", "sha256")}
               for role, row in ref["composition_sources"].items()}}


def _blocker_codes(value: object, label: str) -> list[str]:
    values = _array(value, len(BLOCKER_CODES), label)
    for code in values:
        _enum(code, BLOCKER_CODES, label)
    _unique(values, label)
    return values


def validate_licenses(value: object) -> dict:
    """Validate the retained evidence model without reopening original sources."""
    json_bytes(value)
    root = closed(value, (*COMMON_FIELDS, "source_reference", "records", "evidence_catalog", "bindings",
                          "conflict_summary", "candidate_blocker_codes", "variants", "counts"), "licenses")
    _common(root, LICENSES_SCHEMA)
    ref = validate_source_reference(root["source_reference"])
    old_reference = _legacy_reference(ref)
    records = _array(root["records"], MAX_RECORDS, "license_records", 1)
    source_subjects, old_records = [], []
    source_keys, subject_ids = [], []
    relation_variant_ids = None
    for index, row in enumerate(records):
        closed(row, READINESS_RECORD_FIELDS, "license_record")
        subject = {key: row[key] for key in SUBJECT_FIELDS}
        validate_subject(subject, old_reference, index)
        source_subjects.append(subject)
        old_records.append({key: row[key] for key in RECORD_FIELDS})
        source_keys.append(row["source_key"])
        subject_ids.append((row["subject_type"], row["subject_id"]))
        groups = _array(row["queue_groups"], len(QUEUE_GROUPS), "queue_groups", 1)
        for group in groups:
            _enum(group, QUEUE_GROUPS, "queue_group")
        _unique(groups, "queue_group_memberships")
        _enum(row["next_human_action"], NEXT_HUMAN_ACTIONS, "next_human_action")
        source_codes = _blocker_codes(row["source_blocker_codes"], "source_blocker_codes")
        if "license_review_required" not in source_codes:
            _fail("missing_source_license_review")
        if row["subject_type"] == "component" and "binary_source_binding_missing" not in source_codes:
            _fail("missing_component_binary_blocker")
        if (row["subject_type"] == "dependency" and (row["base_declared_license"] is None
                or row["base_evidence_level"] == "conflicting_declarations")
                and "dependency_license_unknown" not in source_codes):
            _fail("missing_dependency_unknown_blocker")
        if (row["subject_type"] == "dependency" and row["source_type"] != "workspace"
                and "third_party_provenance_incomplete" not in source_codes):
            _fail("missing_dependency_provenance_blocker")
        relations = _array(row["variant_relations"], MAX_VARIANTS, "license_variant_relations", 1)
        current_ids = []
        for relation in relations:
            closed(relation, ("variant_id", "relation"), "license_variant_relation")
            current_ids.append(identifier(relation["variant_id"], "license_variant_id"))
            _enum(relation["relation"], LICENSE_RELATIONS, "license_relation")
        _unique(current_ids, "license_variant_ids")
        if relation_variant_ids is None:
            relation_variant_ids = current_ids
        _fixed(current_ids, relation_variant_ids, "license_variant_order")
    _unique(source_keys, "license_source_keys")
    _unique(subject_ids, "license_subject_ids")
    evidence = _array(root["evidence_catalog"], 64, "evidence_catalog")
    for row in evidence:
        closed(row, EVIDENCE_FIELDS, "evidence_catalog_record")
    bindings = _array(root["bindings"], 256, "bindings")
    for row in bindings:
        closed(row, BINDING_FIELDS, "binding_record")
    candidates = _blocker_codes(root["candidate_blocker_codes"], "candidate_blocker_codes")
    if set(candidates) != {"build_acceptance_not_performed", "runtime_acceptance_not_performed",
                           "data_handling_pending", "release_authority_missing"}:
        _fail("candidate_open_gates")
    counts = closed(root["counts"], ("source_license_record_count", "component_license_record_count",
                                    "dependency_license_record_count", "base_unknown_license_count",
                                    "evidence_present_record_count", "missing_evidence_record_count",
                                    "human_review_required_record_count", "source_blocker_count", "variant_count"), "license_counts")
    statuses = Counter(row["evidence_status"] for row in records)
    unknown = sum(row["base_declared_license"] is None or row["base_evidence_level"] == "conflicting_declarations" for row in records)
    expected_counts = {
        "source_license_record_count": len(records),
        "component_license_record_count": sum(row["subject_type"] == "component" for row in records),
        "dependency_license_record_count": sum(row["subject_type"] == "dependency" for row in records),
        "base_unknown_license_count": unknown, "evidence_present_record_count": statuses["evidence_present"],
        "missing_evidence_record_count": statuses["evidence_missing"],
        "human_review_required_record_count": len(records),
        "source_blocker_count": len(candidates) + sum(len(row["source_blocker_codes"]) for row in records),
        "variant_count": len(relation_variant_ids),
    }
    for field, expected in expected_counts.items():
        _fixed(counts[field], expected, "license_count")
    # All old subject/record/evidence/binding fields are retained, allowing the
    # unchanged Phase25 pure validators to check their internal relationships.
    old_ledger = {
        **evidence_common("termivar-license-evidence-ledger/v1", old_reference),
        "source_subjects": source_subjects, "evidence_sources": evidence, "bindings": bindings,
        "records": old_records,
        "counts": {
            "source_record_count": len(records), "base_unknown_license_count": unknown,
            "evidence_file_count": sum(row["file_present"] for row in evidence),
            "binding_request_count": len(bindings),
            **{field: statuses[status] for field, status in (
                ("evidence_present_record_count", "evidence_present"),
                ("missing_evidence_record_count", "evidence_missing"),
                ("ambiguous_record_count", "binding_ambiguous"), ("conflicting_record_count", "binding_conflict"),
                ("unsupported_record_count", "evidence_unsupported"), ("unverified_source_record_count", "source_not_verified"))},
        },
    }
    from commercial_license_review.conflict_analysis import build_conflicts
    from commercial_license_review.review_queue import build_queue
    old_conflicts = build_conflicts(old_ledger)
    old_queue = build_queue(old_ledger, old_conflicts)
    validate_evidence_documents(old_ledger, old_queue, old_conflicts)
    _fixed(root["conflict_summary"], old_conflicts["counts"], "retained_conflict_summary")
    for row, old_row in zip(records, old_queue["records"]):
        _fixed(row["queue_groups"], old_row["groups"], "retained_queue_groups")
        _fixed(row["next_human_action"], old_row["next_human_action"], "retained_queue_action")
    variants = _array(root["variants"], MAX_VARIANTS, "license_variants", 1)
    seen = []
    for row in variants:
        closed(row, ("variant_id", "license_summary", "open_blockers"), "license_variant")
        seen.append(identifier(row["variant_id"], "license_variant_id"))
        _license_summary(row["license_summary"])
        _open_blockers(row["open_blockers"])
    _unique(seen, "license_variant_ids")
    _fixed(seen, relation_variant_ids, "license_variant_order")
    return copy.deepcopy(root)


def validate_documents(analysis: object, dependencies: object, licenses: object) -> None:
    """Recompute projected metadata only; no old source or evidence file I/O."""
    ana, dep, lic = validate_analysis(analysis), validate_dependencies(dependencies), validate_licenses(licenses)
    for row in (dep, lic):
        _fixed(row["candidate_reference"], ana["candidate_reference"], "candidate_relationship")
        _fixed(row["source_reference"], ana["source_reference"], "source_reference_relationship")
    components = {row["component_id"]: row for row in ana["component_catalog"]}
    manifests = {row["manifest_id"]: row for row in ana["manifest_catalog"]}
    license_by_key = {row["source_key"]: row for row in lic["records"]}
    component_licenses = {row["subject_id"]: row for row in lic["records"] if row["subject_type"] == "component"}
    dependency_licenses = {row["subject_id"]: row for row in lic["records"] if row["subject_type"] == "dependency"}
    if len(dep["records"]) + len(lic["records"]) > MAX_RECORDS:
        _fail("combined_unique_record_reference_limit")
    _fixed(set(components), set(component_licenses), "complete_component_license_projection")
    _fixed({row["dependency_id"] for row in dep["records"]}, set(dependency_licenses), "complete_dependency_license_projection")
    for component_id, component in components.items():
        license_row = component_licenses[component_id]
        _fixed(component["license_source_key"], license_row["source_key"], "component_license_relationship")
        for field in ("source_json_pointer", "source_record_sha256", "source_artifact_sha256", "manifest_file_ref"):
            _fixed(component[field], license_row[field], "component_source_relationship")
        _fixed(component["version_declaration"], license_row["version"], "component_version_relationship")
    per_manifest = Counter()
    for row in dep["records"]:
        if row["manifest_id"] not in manifests:
            _fail("dependency_manifest_reference")
        manifest = manifests[row["manifest_id"]]
        _fixed(row["manifest_file_ref"], manifest["source_file_ref"], "dependency_manifest_file_ref")
        _fixed(row["review_scope"], manifest["context"], "dependency_manifest_context")
        license_row = dependency_licenses[row["dependency_id"]]
        _fixed(row["license_source_key"], license_row["source_key"], "dependency_license_relationship")
        for field in ("source_json_pointer", "source_record_sha256", "source_artifact_sha256", "manifest_file_ref",
                      "manifest_id", "ecosystem", "name", "version", "source_type"):
            _fixed(row[field], license_row[field], "dependency_source_relationship")
        _fixed(row["review_scope"], license_row["product_scope"], "dependency_license_scope")
        if any(identity not in components for identity in row["potential_component_ids"]):
            _fail("potential_component_reference")
        per_manifest[row["manifest_id"]] += 1
    for identity, manifest in manifests.items():
        _fixed(manifest["record_count"], per_manifest[identity], "manifest_record_count")
    # Reuse the owning Phase24 rule implementation. These are in-memory inputs
    # containing only the fields it actually reads, not reconstructed source
    # documents or an assertion that their original bytes were revalidated.
    from commercial_composition.release_constraints import build_constraints as source_constraints
    original_candidate = ana["source_reference"]["composition_candidate_reference"]
    pending_flags = {"build_verified": False, "runtime_verified": False, "release_authorized": False}
    source_inventory = {
        "candidate_reference": original_candidate, **pending_flags,
        "files": [{"root_id": row["root_id"], "path": row["path"], "file_id": row["source_file_ref"]}
                  for row in ana["manifest_catalog"]],
        "components": [{key: row[key] for key in COMPONENT_FIELDS} for row in ana["component_catalog"]],
        "actual_distributable_artifacts": [],
    }
    source_ledger = {
        "candidate_reference": original_candidate, **pending_flags,
        "manifest_records": [{key: row[key] for key in MANIFEST_FIELDS if key != "source_file_ref"}
                             for row in ana["manifest_catalog"]],
        "dependencies": [{key: row[key] for key in DEPENDENCY_FIELDS} for row in dep["records"]],
        "license_evidence": [{
            "evidence_id": row["source_license_id"], "subject_type": row["subject_type"],
            "subject_id": row["subject_id"], "declared_license": row["base_declared_license"],
            "evidence_level": row["base_evidence_level"], "source_file_refs": row["base_source_file_refs"],
            "human_review_required": row["base_human_review_required"], "redistribution_authorized": False,
        } for row in lic["records"]],
    }
    rederived = source_constraints(source_inventory, source_ledger)
    expected_subject_codes = {(row["subject_type"], row["subject_id"]): [] for row in lic["records"]}
    expected_candidate_codes = []
    for blocker in rederived["blockers"]:
        if blocker["subject_type"] == "candidate":
            expected_candidate_codes.append(blocker["code"])
        else:
            identity = (blocker["subject_type"], blocker["subject_id"])
            if identity not in expected_subject_codes:
                _fail("rederived_blocker_subject")
            expected_subject_codes[identity].append(blocker["code"])
    for row in lic["records"]:
        _fixed(row["source_blocker_codes"], expected_subject_codes[(row["subject_type"], row["subject_id"])],
               "rederived_source_blocker_codes")
    _fixed(lic["candidate_blocker_codes"], expected_candidate_codes, "rederived_candidate_blocker_codes")
    _fixed(lic["counts"]["source_blocker_count"], len(rederived["blockers"]), "rederived_source_blocker_count")
    expected_source_counts = {
        "component_count": len(components), "dependency_record_count": len(dep["records"]),
        "license_record_count": len(lic["records"]), "base_unknown_license_count": lic["counts"]["base_unknown_license_count"],
        "evidence_present_record_count": lic["counts"]["evidence_present_record_count"],
        "missing_evidence_record_count": lic["counts"]["missing_evidence_record_count"],
    }
    _fixed(ana["source_counts"], expected_source_counts, "source_counts_relationship")
    variants = [{key: row[key] for key in VARIANT_SCOPE_FIELDS} for row in ana["variants"]]
    # Pure projection builders must never call these validators recursively.
    from .dependency_exposure import rebuild_dependencies
    from .readiness_projection import rebuild_readiness
    from .variant_comparison import rebuild_analysis
    _fixed(dep, rebuild_dependencies(dep, ana["component_catalog"], ana["manifest_catalog"], variants), "dependency_projection")
    _fixed(lic, rebuild_readiness(lic, dep, variants), "readiness_projection")
    _fixed(ana, rebuild_analysis(ana, dep, lic), "analysis_projection")
