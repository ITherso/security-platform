"""Closed Phase24 wire contracts, bounded JSON, and pure cross-document checks.

These validators inspect metadata only. A recorded hash, commit declaration, or
license declaration never establishes source authenticity or release authority.
No helper in this module opens a file, imports a product, or resolves a package.
"""
from __future__ import annotations

from collections import Counter
import copy
import json
import re
import unicodedata


class InputError(ValueError):
    """A closed, bounded source-composition contract was not satisfied."""


SCOPE_SCHEMA = "termivar-offline-composition-scope/v1"
INVENTORY_SCHEMA = "termivar-offline-composition/v1"
LEDGER_SCHEMA = "termivar-offline-dependency-license-ledger/v1"
CONSTRAINTS_SCHEMA = "termivar-offline-release-constraints/v1"
MANIFEST_SCHEMA = "termivar-offline-composition-manifest/v1"
INSPECTION_SCHEMA = "termivar-offline-composition-inspection/v1"
CANDIDATE_REFERENCE = "DEMO-TERMIVAR-COMPOSITION-024"
CANDIDATE_LABEL = "Termivar Web & API Security Assessment — Offline Pilot Candidate"
DEMO_LABEL = ("DEMONSTRATION ONLY — PRODUCT COMPOSITION REVIEW — "
              "NOT AUTHORIZED FOR DISTRIBUTION")
FALSE_FLAGS = (
    "license_review_completed", "redistribution_authorized", "build_verified",
    "runtime_verified", "release_authorized", "production_ready",
)
MAX_JSON_BYTES = 4 * 1024 * 1024
MAX_SCOPE_BYTES = 512 * 1024
MAX_JSON_DEPTH = 16
MAX_JSON_NODES = 120_000
MAX_JSON_TEXT_BYTES = 2 * 1024 * 1024
MAX_STRING_LENGTH = 2048
MAX_SAFE_INTEGER = (1 << 53) - 1
MAX_COMPONENTS = 64
MAX_FILES = 5000
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TOTAL_SOURCE_BYTES = 32 * 1024 * 1024
MAX_DEPENDENCY_RECORDS = 10_000
ROOT_IDS = ("termivar", "platform")
ROLES = ("assessment_core", "reporting_comparison", "offline_support")
VERSION_SCOPES = (
    "workspace_package_metadata", "project_metadata_not_tool_release", "not_declared",
)
MANIFEST_FORMATS = (
    "cargo_toml", "cargo_lock", "pyproject_toml", "requirements_lock", "unsupported_yaml",
)
REVIEW_SCOPES = ("selected_source_metadata", "excluded_backend_context")
EVIDENCE_LEVELS = (
    "local_license_file", "package_metadata_declaration", "source_manifest_declaration",
    "not_available", "conflicting_declarations",
)
LICENSE_UNCERTAINTY_CODES = (
    "redistribution_not_reviewed", "workspace_license_inheritance_declared",
    "license_metadata_form_not_interpreted", "license_text_label_not_legal_validation",
    "local_license_text_not_classified", "workspace_license_declaration_unavailable",
    "conflicting_license_declarations", "scoped_declaration_not_dependency_license_clearance",
    "license_not_declared", "license_not_declared_in_lock", "dependency_license_not_declared",
    "package_artifact_not_selected_or_verified",
)
BLOCKER_CODES = (
    "license_review_required", "dependency_license_unknown",
    "third_party_provenance_incomplete", "binary_source_binding_missing",
    "build_acceptance_not_performed", "runtime_acceptance_not_performed",
    "data_handling_pending", "release_authority_missing",
)
BLOCKER_REASONS = {
    "license_review_required": ("local_evidence_is_not_redistribution_review",),
    "dependency_license_unknown": ("dependency_license_not_established_by_selected_metadata",),
    "third_party_provenance_incomplete": (
        "lock_identity_is_not_local_package_provenance",
        "declaration_is_not_resolved_package_provenance",
    ),
    "binary_source_binding_missing": ("proposed_sources_have_no_accepted_binary_binding",),
    "build_acceptance_not_performed": ("source_inventory_is_not_build_acceptance",),
    "runtime_acceptance_not_performed": ("source_inventory_is_not_runtime_acceptance",),
    "data_handling_pending": ("selected_metadata_has_no_data_handling_clearance",),
    "release_authority_missing": ("no_release_authority_is_established",),
}
BLOCKER_DECISIONS = {
    "license_review_required": "obtain_authorized_license_review",
    "dependency_license_unknown": "collect_scoped_dependency_license_evidence",
    "third_party_provenance_incomplete": "review_dependency_provenance_and_distribution_scope",
    "binary_source_binding_missing": "define_and_independently_accept_distributable_binding",
    "build_acceptance_not_performed": "perform_separately_authorized_build_acceptance",
    "runtime_acceptance_not_performed": "perform_separately_authorized_runtime_acceptance",
    "data_handling_pending": "confirm_metadata_handling_and_distribution_scope",
    "release_authority_missing": "obtain_explicit_release_authority",
}
SCOPE_LIMITATIONS = (
    "explicit_selected_files_only",
    "commit_pin_is_reviewed_scope_declaration_not_git_or_build_attestation",
    "not_complete_runtime_or_feature_dependency_closure",
    "source_metadata_not_distributable_artifacts",
    "no_secret_detection_or_legal_clearance_guarantee",
)
COMMON_FIELDS = (
    "schema_version", "candidate_reference", "candidate_label", "demo_label",
    "demo_only", "source_inventory_generated", *FALSE_FLAGS,
)
ROOT_FIELDS = ("root_id", "repository_label", "pinned_commit")
EXCLUDED_FIELDS = ("component_id", "reason_code")
MANIFEST_REF_FIELDS = ("manifest_id", "root_id", "path", "format", "context")
FILE_FIELDS = ("file_id", "root_id", "path", "bytes", "sha256", "local_artifact_present")
COMPONENT_FIELDS = (
    "component_id", "root_id", "repository_label", "pinned_commit", "role",
    "manifest_path", "source_file_refs", "version_declaration", "version_scope",
    "source_present", "distribution_status",
)
DEPENDENCY_FIELDS = (
    "dependency_id", "manifest_id", "ecosystem", "name", "version",
    "declared_requirement", "source_type", "source_checksum", "source_identity_sha256",
    "relation", "directness", "local_package_artifact", "review_scope",
)
LICENSE_FIELDS = (
    "evidence_id", "subject_type", "subject_id", "evidence_level", "declared_license",
    "source_file_refs", "uncertainty_codes", "human_review_required",
    "redistribution_authorized",
)
BLOCKER_FIELDS = (
    "code", "subject_type", "subject_id", "source_file_refs", "reason_code",
    "next_decision", "status",
)


def _fail(label: str) -> None:
    # Never include caller data, paths, or unknown keys in diagnostic messages.
    raise InputError("composition_invalid_" + label)


def closed(value: object, fields: object, label: str) -> dict:
    """Require an ordinary dictionary with exactly the supplied field names."""
    if type(value) is not dict or set(value) != set(fields):
        _fail(label)
    return value


def text(value: object, label: str, maximum: int = MAX_STRING_LENGTH,
         nullable: bool = False) -> str | None:
    """Validate bounded display metadata without retaining arbitrary objects."""
    if value is None and nullable:
        return None
    if (type(value) is not str or not 1 <= len(value) <= maximum
            or any(unicodedata.category(char).startswith("C") for char in value)):
        _fail(label)
    try:
        value.encode("utf-8", "strict")
    except UnicodeError:
        _fail(label)
    return value


def integer(value: object, label: str, maximum: int = MAX_SAFE_INTEGER) -> int:
    """Reject booleans, negative values, floats, and unsafe integers."""
    if type(value) is not int or not 0 <= value <= maximum:
        _fail(label)
    return value


def identifier(value: object, label: str) -> str:
    result = text(value, label, 128)
    if re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]*", result) is None:
        _fail(label)
    return result


def relative_path(value: object, label: str) -> str:
    """Accept a canonical repository-relative POSIX path; do not follow it."""
    result = text(value, label)
    if (result.startswith("/") or "\\" in result or ":" in result
            or any(part in ("", ".", "..") for part in result.split("/"))
            or any(char in result for char in "*?<>|\"")):
        _fail(label)
    return result


def sha256(value: object, label: str, nullable: bool = False) -> str | None:
    if value is None and nullable:
        return None
    if type(value) is not str or re.fullmatch(r"[0-9a-f]{64}", value) is None:
        _fail(label)
    return value


def _enum(value: object, choices: object, label: str) -> str:
    if type(value) is not str or value not in choices:
        _fail(label)
    return value


def _literal(value: object, expected: object, label: str) -> None:
    if type(value) is not type(expected) or value != expected:
        _fail(label)


def _list(value: object, maximum: int, label: str, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        _fail(label)
    return value


def _unique(values: list, label: str) -> None:
    if len(set(values)) != len(values):
        _fail(label)


def _sequence_id(value: object, prefix: str, index: int, label: str) -> str:
    expected = f"{prefix}{index:04d}"
    _literal(value, expected, label)
    return expected


def _file_refs(value: object, label: str) -> list[str]:
    items = _list(value, MAX_FILES, label)
    for item in items:
        if type(item) is not str or re.fullmatch(r"F[0-9]{4}", item) is None:
            _fail(label)
        if not 1 <= int(item[1:]) <= MAX_FILES:
            _fail(label)
    _unique(items, label)
    return items


def _tree(value: object) -> None:
    """Bound keys and values too; this is separate from encoded JSON bytes."""
    pending = [(value, 0)]
    nodes = total_text = 0
    while pending:
        item, depth = pending.pop()
        nodes += 1
        if nodes > MAX_JSON_NODES or depth > MAX_JSON_DEPTH:
            _fail("json_graph_limit")
        if type(item) is dict:
            for key, child in item.items():
                if type(key) is not str:
                    _fail("json_key")
                pending.append((key, depth + 1))
                pending.append((child, depth + 1))
        elif type(item) is list:
            pending.extend((child, depth + 1) for child in item)
        elif type(item) is str:
            if len(item) > MAX_STRING_LENGTH:
                _fail("json_string_limit")
            try:
                total_text += len(item.encode("utf-8", "strict"))
            except UnicodeError:
                _fail("json_utf8")
            if total_text > MAX_JSON_TEXT_BYTES:
                _fail("json_text_limit")
        elif type(item) is int:
            integer(item, "json_integer")
        elif item is not None and type(item) is not bool:
            _fail("json_type")


def _depth_before_parse(value: str) -> None:
    depth = 0
    quoted = escaped = False
    for char in value:
        if quoted:
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                quoted = False
        elif char == '"':
            quoted = True
        elif char in "[{":
            depth += 1
            if depth > MAX_JSON_DEPTH:
                _fail("json_depth")
        elif char in "]}":
            depth -= 1


def _pairs(pairs: list) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            _fail("json_duplicate_key")
        result[key] = value
    return result


def _reject_number(_value: str) -> None:
    _fail("json_number")


def _parse_integer(value: str) -> int:
    if len(value) > 16 or value.startswith("-"):
        _fail("json_integer")
    return integer(int(value), "json_integer")


def parse_json(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    """Strict UTF-8 JSON with no BOM, duplicate keys, floats, or huge graph."""
    integer(maximum, "json_byte_limit", MAX_JSON_BYTES)
    if (type(raw) is not bytes or not 1 <= len(raw) <= maximum
            or raw.startswith(b"\xef\xbb\xbf")):
        _fail("json_bytes")
    try:
        decoded = raw.decode("utf-8", "strict")
        _depth_before_parse(decoded)
        result = json.loads(decoded, object_pairs_hook=_pairs,
                            parse_int=_parse_integer, parse_float=_reject_number,
                            parse_constant=_reject_number)
    except (UnicodeError, json.JSONDecodeError, RecursionError, ValueError):
        _fail("json_encoding_or_syntax")
    _tree(result)
    return result


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    """Canonical bounded metadata serialization; never relax old phase limits."""
    integer(maximum, "json_byte_limit", MAX_JSON_BYTES)
    _tree(value)
    try:
        raw = (json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2,
                          allow_nan=False) + "\n").encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        _fail("json_encoding")
    if len(raw) > maximum:
        _fail("json_bytes")
    return raw


def common(schema: str, reference: str) -> dict:
    """Construct fixed trust fields, without deriving authority from metadata."""
    _enum(schema, (INVENTORY_SCHEMA, LEDGER_SCHEMA, CONSTRAINTS_SCHEMA,
                   MANIFEST_SCHEMA, INSPECTION_SCHEMA), "schema")
    _literal(reference, CANDIDATE_REFERENCE, "candidate_reference")
    return {
        "schema_version": schema, "candidate_reference": reference,
        "candidate_label": CANDIDATE_LABEL, "demo_label": DEMO_LABEL,
        "demo_only": True, "source_inventory_generated": True,
        **{flag: False for flag in FALSE_FLAGS},
    }


def _common(value: dict, schema: str) -> None:
    expected = common(schema, CANDIDATE_REFERENCE)
    for field, fixed in expected.items():
        _literal(value[field], fixed, "common_" + field)


def _roots(value: object) -> dict[str, dict]:
    roots = _list(value, 2, "source_roots", 2)
    by_id = {}
    for root in roots:
        closed(root, ROOT_FIELDS, "source_root")
        root_id = _enum(root["root_id"], ROOT_IDS, "root_id")
        label = text(root["repository_label"], "repository_label", 128)
        if (re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._/-]*", label) is None
                or any(part in ("", ".", "..") for part in label.split("/"))):
            _fail("repository_label")
        if (type(root["pinned_commit"]) is not str
                or re.fullmatch(r"[0-9a-f]{40}", root["pinned_commit"]) is None):
            _fail("pinned_commit")
        if root_id in by_id:
            _fail("duplicate_root")
        by_id[root_id] = root
    if set(by_id) != set(ROOT_IDS):
        _fail("source_roots")
    return by_id


def _excluded(value: object) -> set[str]:
    rows = _list(value, MAX_COMPONENTS, "excluded_components")
    ids = []
    for row in rows:
        closed(row, EXCLUDED_FIELDS, "excluded_component")
        ids.append(identifier(row["component_id"], "excluded_component_id"))
        identifier(row["reason_code"], "excluded_reason")
    _unique(ids, "excluded_component_ids")
    return set(ids)


def _manifest_refs(value: object) -> dict[str, dict]:
    rows = _list(value, MAX_FILES, "dependency_manifest_refs", 1)
    result = {}
    locations = []
    for row in rows:
        closed(row, MANIFEST_REF_FIELDS, "dependency_manifest_ref")
        identity = identifier(row["manifest_id"], "manifest_id")
        _enum(row["root_id"], ROOT_IDS, "manifest_root")
        relative_path(row["path"], "manifest_path")
        _enum(row["format"], MANIFEST_FORMATS, "manifest_format")
        _enum(row["context"], REVIEW_SCOPES, "manifest_context")
        if identity in result:
            _fail("duplicate_manifest_id")
        result[identity] = row
        locations.append((row["root_id"], row["path"]))
    _unique(locations, "duplicate_manifest_path")
    return result


def validate_scope(value: object) -> dict:
    """Validate only declared scope; paths are not opened by this function."""
    _tree(value)
    root = closed(value, (
        "schema_version", "mode", "candidate_reference", "source_roots",
        "included_components", "excluded_components", "dependency_manifests",
        "license_evidence_sources", "inspection_constraints",
    ), "scope")
    _literal(root["schema_version"], SCOPE_SCHEMA, "scope_schema")
    _literal(root["mode"], "demo", "scope_mode")
    _literal(root["candidate_reference"], CANDIDATE_REFERENCE, "candidate_reference")
    _roots(root["source_roots"])
    components = _list(root["included_components"], MAX_COMPONENTS, "included_components", 1)
    component_ids = []
    locations = set()
    for row in components:
        closed(row, ("component_id", "root_id", "role", "manifest_path", "source_files",
                     "version_scope"), "included_component")
        component_ids.append(identifier(row["component_id"], "component_id"))
        _enum(row["root_id"], ROOT_IDS, "component_root")
        _enum(row["role"], ROLES, "component_role")
        _enum(row["version_scope"], VERSION_SCOPES, "version_scope")
        files = _list(row["source_files"], MAX_FILES, "component_source_files", 1)
        for path in files:
            relative_path(path, "source_path")
            locations.add((row["root_id"], path))
        _unique(files, "component_source_files")
        if row["manifest_path"] is not None:
            relative_path(row["manifest_path"], "component_manifest")
            locations.add((row["root_id"], row["manifest_path"]))
    _unique(component_ids, "component_ids")
    excluded_ids = _excluded(root["excluded_components"])
    if len(component_ids) + len(excluded_ids) > MAX_COMPONENTS:
        _fail("component_reference_limit")
    if set(component_ids) & excluded_ids:
        _fail("included_excluded_overlap")
    manifests = _manifest_refs(root["dependency_manifests"])
    for row in manifests.values():
        locations.add((row["root_id"], row["path"]))
    sources = _list(root["license_evidence_sources"], MAX_FILES, "license_sources")
    source_ids = []
    for row in sources:
        closed(row, ("source_id", "root_id", "path", "kind", "applies_to"), "license_source")
        source_ids.append(identifier(row["source_id"], "license_source_id"))
        _enum(row["root_id"], ROOT_IDS, "license_source_root")
        relative_path(row["path"], "license_source_path")
        locations.add((row["root_id"], row["path"]))
        _enum(row["kind"], ("local_license_file", "source_manifest_declaration"), "license_kind")
        applies_to = _list(row["applies_to"], MAX_COMPONENTS, "license_applies_to", 1)
        for identity in applies_to:
            identifier(identity, "license_component_id")
            if identity not in component_ids:
                _fail("license_component_reference")
        _unique(applies_to, "license_applies_to")
    _unique(source_ids, "license_source_ids")
    if len(locations) > MAX_FILES:
        _fail("selected_file_count")
    limits = closed(root["inspection_constraints"], (
        "max_components", "max_files", "max_file_bytes", "max_total_source_bytes",
    ), "inspection_constraints")
    for field, fixed in (
        ("max_components", MAX_COMPONENTS), ("max_files", MAX_FILES),
        ("max_file_bytes", MAX_FILE_BYTES), ("max_total_source_bytes", MAX_TOTAL_SOURCE_BYTES),
    ):
        _literal(limits[field], fixed, "inspection_limit")
    if len(json_bytes(root, maximum=MAX_SCOPE_BYTES)) > MAX_SCOPE_BYTES:
        _fail("scope_bytes")
    return copy.deepcopy(root)


def validate_inventory(value: object) -> dict:
    """Validate closed first-party source metadata and its internal counts."""
    _tree(value)
    root = closed(value, (*COMMON_FIELDS, "source_scope", "source_roots", "components",
                          "excluded_components", "files", "dependency_manifest_refs",
                          "actual_distributable_artifacts", "counts", "scope_limitations"), "inventory")
    _common(root, INVENTORY_SCHEMA)
    scope = closed(root["source_scope"], ("bytes", "sha256"), "source_scope")
    if integer(scope["bytes"], "scope_size", MAX_SCOPE_BYTES) == 0:
        _fail("scope_size")
    sha256(scope["sha256"], "scope_hash")
    roots = _roots(root["source_roots"])
    files = _list(root["files"], MAX_FILES, "files", 1)
    by_id = {}
    by_path = {}
    total_bytes = 0
    for index, row in enumerate(files, 1):
        closed(row, FILE_FIELDS, "file")
        identity = _sequence_id(row["file_id"], "F", index, "file_id")
        _enum(row["root_id"], ROOT_IDS, "file_root")
        relative_path(row["path"], "file_path")
        total_bytes += integer(row["bytes"], "file_bytes", MAX_FILE_BYTES)
        sha256(row["sha256"], "file_hash")
        _literal(row["local_artifact_present"], True, "local_artifact_present")
        key = (row["root_id"], row["path"])
        if key in by_path:
            _fail("duplicate_file_path")
        by_id[identity] = row
        by_path[key] = row
    if total_bytes > MAX_TOTAL_SOURCE_BYTES:
        _fail("source_byte_budget")
    components = _list(root["components"], MAX_COMPONENTS, "components", 1)
    component_ids = []
    for row in components:
        closed(row, COMPONENT_FIELDS, "component")
        component_ids.append(identifier(row["component_id"], "component_id"))
        source_root = roots[_enum(row["root_id"], ROOT_IDS, "component_root")]
        for field in ("repository_label", "pinned_commit"):
            _literal(row[field], source_root[field], "component_" + field)
        _enum(row["role"], ROLES, "component_role")
        _enum(row["version_scope"], VERSION_SCOPES, "version_scope")
        text(row["version_declaration"], "version_declaration", nullable=True)
        if row["version_scope"] == "not_declared" and row["version_declaration"] is not None:
            _fail("undeclared_version")
        _literal(row["source_present"], True, "source_present")
        _literal(row["distribution_status"], "proposed_source_only", "distribution_status")
        refs = _file_refs(row["source_file_refs"], "component_file_refs")
        if not refs or any(ref not in by_id or by_id[ref]["root_id"] != row["root_id"] for ref in refs):
            _fail("component_file_reference")
        if row["manifest_path"] is not None:
            path = relative_path(row["manifest_path"], "component_manifest")
            if ((row["root_id"], path) not in by_path
                    or by_path[(row["root_id"], path)]["file_id"] not in refs):
                _fail("component_manifest_reference")
    _unique(component_ids, "component_ids")
    excluded_ids = _excluded(root["excluded_components"])
    if len(component_ids) + len(excluded_ids) > MAX_COMPONENTS:
        _fail("component_reference_limit")
    if set(component_ids) & excluded_ids:
        _fail("included_excluded_overlap")
    for manifest in _manifest_refs(root["dependency_manifest_refs"]).values():
        if (manifest["root_id"], manifest["path"]) not in by_path:
            _fail("dependency_manifest_file_reference")
    _literal(root["actual_distributable_artifacts"], [], "actual_distributable_artifacts")
    _literal(root["scope_limitations"], list(SCOPE_LIMITATIONS), "scope_limitations")
    counts = closed(root["counts"], ("component_count", "file_count", "excluded_component_count",
                                     "total_selected_source_bytes"), "inventory_counts")
    for name, actual in (
        ("component_count", len(components)), ("file_count", len(files)),
        ("excluded_component_count", len(root["excluded_components"])),
        ("total_selected_source_bytes", total_bytes),
    ):
        _literal(counts[name], actual, "inventory_count")
    return copy.deepcopy(root)


def validate_ledger(value: object) -> dict:
    """Validate metadata declarations and lock records without resolving them."""
    _tree(value)
    root = closed(value, (*COMMON_FIELDS, "manifest_records", "dependencies", "license_evidence", "counts"), "ledger")
    _common(root, LEDGER_SCHEMA)
    manifests = _list(root["manifest_records"], MAX_FILES, "manifest_records", 1)
    manifest_by_id = {}
    locations = []
    for row in manifests:
        closed(row, (*MANIFEST_REF_FIELDS, "sha256", "bytes", "parse_status", "record_count",
                     "limitation_code"), "manifest_record")
        identity = identifier(row["manifest_id"], "manifest_id")
        if identity in manifest_by_id:
            _fail("duplicate_manifest_id")
        _enum(row["root_id"], ROOT_IDS, "manifest_root")
        relative_path(row["path"], "manifest_path")
        sha256(row["sha256"], "manifest_hash")
        integer(row["bytes"], "manifest_bytes", MAX_FILE_BYTES)
        _enum(row["format"], MANIFEST_FORMATS, "manifest_format")
        _enum(row["context"], REVIEW_SCOPES, "manifest_context")
        _enum(row["parse_status"], ("parsed", "unsupported"), "manifest_parse_status")
        integer(row["record_count"], "manifest_record_count", MAX_DEPENDENCY_RECORDS)
        _enum(row["limitation_code"], (
            "selected_manifest_declarations_only", "whole_workspace_lock_not_selected_build",
            "excluded_backend_context_only", "unsupported_format_not_parsed",
        ), "manifest_limitation")
        if row["format"] == "unsupported_yaml":
            if (row["parse_status"] != "unsupported" or row["record_count"] != 0
                    or row["limitation_code"] != "unsupported_format_not_parsed"):
                _fail("unsupported_manifest")
        elif row["parse_status"] != "parsed":
            _fail("supported_manifest_status")
        expected_limitation = (
            "unsupported_format_not_parsed" if row["parse_status"] == "unsupported" else
            "excluded_backend_context_only" if row["context"] == "excluded_backend_context" else
            "whole_workspace_lock_not_selected_build" if row["format"] == "cargo_lock" else
            "selected_manifest_declarations_only"
        )
        _literal(row["limitation_code"], expected_limitation, "manifest_scope_limitation")
        if (row["format"] in ("pyproject_toml", "requirements_lock")
                and row["context"] != "excluded_backend_context"):
            _fail("python_backend_context")
        locations.append((row["root_id"], row["path"]))
        manifest_by_id[identity] = row
    _unique(locations, "duplicate_manifest_path")
    dependencies = _list(root["dependencies"], MAX_DEPENDENCY_RECORDS, "dependencies")
    dependency_ids = set()
    per_manifest = Counter()
    for index, row in enumerate(dependencies, 1):
        closed(row, DEPENDENCY_FIELDS, "dependency")
        identity = _sequence_id(row["dependency_id"], "D", index, "dependency_id")
        dependency_ids.add(identity)
        manifest_id = identifier(row["manifest_id"], "dependency_manifest_id")
        if manifest_id not in manifest_by_id:
            _fail("dependency_manifest_reference")
        manifest = manifest_by_id[manifest_id]
        if manifest["parse_status"] != "parsed":
            _fail("unsupported_manifest_dependency")
        _enum(row["ecosystem"], ("rust", "python"), "dependency_ecosystem")
        expected_ecosystem = "rust" if manifest["format"] in ("cargo_toml", "cargo_lock") else "python"
        _literal(row["ecosystem"], expected_ecosystem, "dependency_ecosystem")
        name = text(row["name"], "dependency_name", 128)
        name_pattern = r"[A-Za-z0-9_][A-Za-z0-9_-]*" if row["ecosystem"] == "rust" else r"[A-Za-z0-9][A-Za-z0-9._-]*"
        if re.fullmatch(name_pattern, name) is None:
            _fail("dependency_name")
        version = text(row["version"], "dependency_version", 128, nullable=True)
        if version is not None and re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9.!+_-]*", version) is None:
            _fail("dependency_version")
        text(row["declared_requirement"], "declared_requirement", 512, nullable=True)
        _enum(row["source_type"], ("registry", "git", "workspace", "declared_index", "unknown"), "source_type")
        sha256(row["source_checksum"], "source_checksum", nullable=True)
        sha256(row["source_identity_sha256"], "source_identity", nullable=True)
        _enum(row["relation"], ("direct_declaration", "lock_record"), "dependency_relation")
        _enum(row["directness"], ("direct_in_selected_manifest", "unknown"), "dependency_directness")
        _literal(row["local_package_artifact"], "not_selected_or_verified", "local_package_artifact")
        _literal(row["review_scope"], manifest["context"], "dependency_review_scope")
        if manifest["format"] in ("cargo_lock", "requirements_lock"):
            if row["relation"] != "lock_record" or row["version"] is None:
                _fail("lock_record_shape")
            if row["directness"] != "unknown":
                _fail("lock_record_inference")
            if manifest["format"] == "cargo_lock" and row["declared_requirement"] is not None:
                _fail("cargo_lock_requirement_inference")
        elif row["relation"] != "direct_declaration":
            _fail("declaration_relation")
        per_manifest[manifest_id] += 1
    for identity, manifest in manifest_by_id.items():
        _literal(manifest["record_count"], per_manifest[identity], "manifest_record_count")
    evidence = _list(root["license_evidence"], MAX_COMPONENTS + MAX_DEPENDENCY_RECORDS, "license_evidence")
    subjects = []
    for index, row in enumerate(evidence, 1):
        closed(row, LICENSE_FIELDS, "license_evidence")
        _sequence_id(row["evidence_id"], "L", index, "license_evidence_id")
        _enum(row["subject_type"], ("component", "dependency"), "license_subject_type")
        identifier(row["subject_id"], "license_subject_id")
        subjects.append((row["subject_type"], row["subject_id"]))
        _enum(row["evidence_level"], EVIDENCE_LEVELS, "evidence_level")
        declared_license = text(row["declared_license"], "declared_license", 256, nullable=True)
        if declared_license is not None and (
                re.fullmatch(r"[A-Za-z0-9 .()+:/_-]+", declared_license) is None
                or "://" in declared_license or declared_license != declared_license.strip()):
            _fail("declared_license")
        _file_refs(row["source_file_refs"], "license_file_refs")
        uncertainty = _list(row["uncertainty_codes"], 64, "license_uncertainty")
        for code in uncertainty:
            _enum(code, LICENSE_UNCERTAINTY_CODES, "license_uncertainty_code")
        _unique(uncertainty, "license_uncertainty_codes")
        _literal(row["human_review_required"], True, "human_review_required")
        _literal(row["redistribution_authorized"], False, "license_redistribution_authorized")
        if row["evidence_level"] == "not_available" and row["declared_license"] is not None:
            _fail("unavailable_license_declaration")
        if row["evidence_level"] in EVIDENCE_LEVELS[:3] and (
                row["declared_license"] is None or not row["source_file_refs"]):
            _fail("license_declaration_source")
        if row["evidence_level"] == "conflicting_declarations" and not uncertainty:
            _fail("license_conflict_uncertainty")
        if row["subject_type"] == "dependency" and row["subject_id"] not in dependency_ids:
            _fail("license_dependency_reference")
    _unique(subjects, "license_subjects")
    counts = closed(root["counts"], ("manifest_count", "dependency_record_count", "license_evidence_count",
                                     "unknown_license_subject_count"), "ledger_counts")
    unknown = sum(row["declared_license"] is None or row["evidence_level"] == "conflicting_declarations"
                  for row in evidence)
    for name, actual in (("manifest_count", len(manifests)), ("dependency_record_count", len(dependencies)),
                         ("license_evidence_count", len(evidence)), ("unknown_license_subject_count", unknown)):
        _literal(counts[name], actual, "ledger_count")
    return copy.deepcopy(root)


def validate_constraints(value: object) -> dict:
    """Validate open blockers, fixed authority flags, and derived subject counts."""
    _tree(value)
    root = closed(value, (*COMMON_FIELDS, "blockers", "counts"), "constraints")
    _common(root, CONSTRAINTS_SCHEMA)
    blockers = _list(root["blockers"], MAX_JSON_NODES, "blockers", 1)
    identities = []
    subjects_by_code = {}
    for row in blockers:
        closed(row, BLOCKER_FIELDS, "blocker")
        code = _enum(row["code"], BLOCKER_CODES, "blocker_code")
        _enum(row["subject_type"], ("candidate", "component", "dependency"), "blocker_subject_type")
        identity = identifier(row["subject_id"], "blocker_subject_id")
        allowed_subject_types = (
            ("component", "dependency") if code == "license_review_required" else
            ("dependency",) if code in ("dependency_license_unknown", "third_party_provenance_incomplete") else
            ("component",) if code == "binary_source_binding_missing" else ("candidate",)
        )
        _enum(row["subject_type"], allowed_subject_types, "blocker_code_subject_type")
        if row["subject_type"] == "candidate":
            _literal(identity, CANDIDATE_REFERENCE, "blocker_candidate")
        _file_refs(row["source_file_refs"], "blocker_file_refs")
        _enum(row["reason_code"], BLOCKER_REASONS[code], "blocker_reason")
        _literal(row["next_decision"], BLOCKER_DECISIONS[code], "blocker_next_decision")
        _literal(row["status"], "open", "blocker_status")
        identities.append((code, row["subject_type"], identity))
        subjects_by_code.setdefault(code, set()).add((row["subject_type"], identity))
    _unique(identities, "duplicate_blocker")
    counts = closed(root["counts"], ("blocker_count", "by_code"), "constraint_counts")
    _literal(counts["blocker_count"], len(blockers), "blocker_count")
    code_rows = _list(counts["by_code"], len(BLOCKER_CODES), "blocker_code_counts", 1)
    seen = []
    for row in code_rows:
        closed(row, ("code", "affected_subject_count"), "blocker_code_count")
        code = _enum(row["code"], BLOCKER_CODES, "blocker_code")
        seen.append(code)
        _literal(row["affected_subject_count"], len(subjects_by_code.get(code, set())), "blocker_subject_count")
        if row["affected_subject_count"] == 0:
            _fail("empty_blocker_code_count")
    _unique(seen, "duplicate_blocker_code_count")
    if set(seen) != set(subjects_by_code):
        _fail("missing_blocker_code_count")
    return copy.deepcopy(root)


def validate_documents(inventory: object, ledger: object, constraints: object) -> None:
    """Bind closed metadata documents without reopening their original sources."""
    inv = validate_inventory(inventory)
    dep = validate_ledger(ledger)
    con = validate_constraints(constraints)
    components = {row["component_id"]: row for row in inv["components"]}
    dependencies = {row["dependency_id"]: row for row in dep["dependencies"]}
    files = {row["file_id"]: row for row in inv["files"]}
    file_by_path = {(row["root_id"], row["path"]): row for row in inv["files"]}
    expected_manifests = {row["manifest_id"]: row for row in inv["dependency_manifest_refs"]}
    actual_manifests = {row["manifest_id"]: row for row in dep["manifest_records"]}
    if set(expected_manifests) != set(actual_manifests):
        _fail("manifest_set_relationship")
    for identity, expected in expected_manifests.items():
        actual = actual_manifests[identity]
        for field in MANIFEST_REF_FIELDS:
            _literal(actual[field], expected[field], "manifest_relationship")
        selected = file_by_path[(actual["root_id"], actual["path"])]
        _literal(actual["sha256"], selected["sha256"], "manifest_file_hash")
        _literal(actual["bytes"], selected["bytes"], "manifest_file_bytes")
    expected_subjects = {("component", identity) for identity in components}
    expected_subjects |= {("dependency", identity) for identity in dependencies}
    actual_subjects = {(row["subject_type"], row["subject_id"]) for row in dep["license_evidence"]}
    if actual_subjects != expected_subjects:
        _fail("complete_license_subject_projection")
    evidence_by_subject = {(row["subject_type"], row["subject_id"]): row for row in dep["license_evidence"]}
    for row in dep["license_evidence"]:
        if any(ref not in files for ref in row["source_file_refs"]):
            _fail("license_file_reference")
        if row["subject_type"] == "component":
            source_root = components[row["subject_id"]]["root_id"]
            if any(files[ref]["root_id"] != source_root for ref in row["source_file_refs"]):
                _fail("cross_repository_license_attribution")
        else:
            dependency = dependencies[row["subject_id"]]
            manifest = actual_manifests[dependency["manifest_id"]]
            expected_ref = file_by_path[(manifest["root_id"], manifest["path"])]["file_id"]
            if (row["evidence_level"] != "not_available" or row["declared_license"] is not None
                    or row["source_file_refs"] != [expected_ref]):
                _fail("dependency_license_not_in_selected_metadata")
    for row in con["blockers"]:
        if (row["subject_type"] == "component" and row["subject_id"] not in components
                or row["subject_type"] == "dependency" and row["subject_id"] not in dependencies
                or any(ref not in files for ref in row["source_file_refs"])):
            _fail("blocker_reference")
        if row["code"] == "dependency_license_unknown" and row["subject_type"] != "dependency":
            _fail("dependency_blocker_subject")
        if row["code"] == "license_review_required":
            evidence = evidence_by_subject[(row["subject_type"], row["subject_id"])]
            _literal(row["source_file_refs"], evidence["source_file_refs"], "license_blocker_sources")
        elif row["code"] in ("dependency_license_unknown", "third_party_provenance_incomplete"):
            dependency = dependencies[row["subject_id"]]
            manifest = actual_manifests[dependency["manifest_id"]]
            expected_ref = file_by_path[(manifest["root_id"], manifest["path"])]["file_id"]
            _literal(row["source_file_refs"], [expected_ref], "dependency_blocker_sources")
            if row["code"] == "third_party_provenance_incomplete":
                if dependency["source_type"] == "workspace":
                    _fail("workspace_is_not_third_party_classification")
                expected_reason = (
                    "lock_identity_is_not_local_package_provenance" if dependency["relation"] == "lock_record"
                    else "declaration_is_not_resolved_package_provenance"
                )
                _literal(row["reason_code"], expected_reason, "provenance_blocker_reason")
        elif row["code"] == "binary_source_binding_missing":
            _literal(row["source_file_refs"], components[row["subject_id"]]["source_file_refs"], "binary_binding_sources")
        else:
            _literal(row["source_file_refs"], [], "candidate_gate_sources")
    # Closed shape and references do not establish completeness of a real build.
    # Require a blocker for every unreviewed license subject and fixed open gates.
    blocker_subjects = {(row["code"], row["subject_type"], row["subject_id"]) for row in con["blockers"]}
    for evidence in dep["license_evidence"]:
        subject = (evidence["subject_type"], evidence["subject_id"])
        if ("license_review_required", *subject) not in blocker_subjects:
            _fail("missing_license_review_blocker")
        if (subject[0] == "dependency" and (evidence["declared_license"] is None
                or evidence["evidence_level"] == "conflicting_declarations")
                and ("dependency_license_unknown", *subject) not in blocker_subjects):
            _fail("missing_dependency_license_blocker")
        if (subject[0] == "dependency" and dependencies[subject[1]]["source_type"] != "workspace"
                and ("third_party_provenance_incomplete", *subject) not in blocker_subjects):
            _fail("missing_dependency_provenance_blocker")
    for component_id in components:
        if ("binary_source_binding_missing", "component", component_id) not in blocker_subjects:
            _fail("missing_component_binary_binding_blocker")
    for code in ("build_acceptance_not_performed", "runtime_acceptance_not_performed",
                 "data_handling_pending", "release_authority_missing"):
        if (code, "candidate", CANDIDATE_REFERENCE) not in blocker_subjects:
            _fail("missing_candidate_gate")
