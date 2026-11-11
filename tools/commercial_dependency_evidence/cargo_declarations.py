"""Read explicit Cargo TOML bytes, retain closed metadata and old projections."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from commercial_composition.dependency_reader import (
    _cargo_declaration, _cargo_detail, _toml,
)
from .evidence_contracts import (InputError, MAX_DECLARATIONS, MAX_MANIFEST_BYTES,
                                 MAX_MANIFESTS, json_bytes, record_digest)
from .workspace_inheritance import declaration_location_id, rebuild_inheritance


MANIFEST_SOURCE_FIELDS = ("manifest_id", "root_id", "path", "format", "phase24_file_ref", "bytes", "sha256", "pinned_commit")
MANIFEST_FIELDS = (*MANIFEST_SOURCE_FIELDS, "package_name", "package_version", "package_version_workspace",
                   "workspace_package_version", "is_workspace", "workspace_members", "workspace_exclude",
                   "package_workspace_declared", "workspace_dependency_keys", "features",
                   "target_entries", "declaration_locations", "source_fingerprint")
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,127}\Z")
_FEATURE_MEMBER = re.compile(r"(?:dep:)?[A-Za-z0-9_][A-Za-z0-9_-]*(?:\??/[A-Za-z0-9_][A-Za-z0-9_-]*)?\Z")
_SECTIONS = (("dependencies", "normal"), ("dev-dependencies", "dev"), ("build-dependencies", "build"))


def _text(value: object, maximum: int = 1024) -> str:
    if (type(value) is not str or not 0 < len(value) <= maximum or value != value.strip()
            or any(ord(char) < 32 for char in value) or "://" in value):
        raise InputError("direct_dependency_invalid_bounded_metadata")
    return value


def _name(value: object) -> str:
    value = _text(value, 128)
    if _NAME.fullmatch(value) is None:
        raise InputError("direct_dependency_invalid_source_name")
    return value


def _table(value: object) -> dict:
    if type(value) is not dict:
        raise InputError("direct_dependency_invalid_toml_table")
    return value


def _features(value: object, *, members: bool = False) -> list[str]:
    if type(value) is not list or len(value) > 256:
        raise InputError("direct_dependency_invalid_feature_array")
    result = []
    for item in value:
        item = _text(item, 256)
        if (_FEATURE_MEMBER if members else _NAME).fullmatch(item) is None:
            raise InputError("direct_dependency_unsupported_feature_token")
        result.append(item)
    return result


def _groups(document: dict) -> list[tuple[list[str], str, dict]]:
    result = []
    workspace = _table(document.get("workspace", {}))
    if "dependencies" in workspace:
        result.append((["workspace", "dependencies"], "workspace_template", _table(workspace["dependencies"])))
    for section, kind in _SECTIONS:
        if section in document:
            result.append(([section], kind, _table(document[section])))
    for target, table in _table(document.get("target", {})).items():
        target, table = _text(target, 1024), _table(table)
        for section, kind in _SECTIONS:
            if section in table:
                result.append((["target", target, section], kind, _table(table[section])))
    return result


def _version(package: dict) -> tuple[str | None, bool]:
    value = package.get("version")
    if value is None:
        return None, False
    if type(value) is dict:
        if set(value) != {"workspace"} or value["workspace"] is not True:
            raise InputError("direct_dependency_unsupported_package_version")
        return None, True
    return _text(value, 128), False


def _target_entries(document: dict) -> list[dict]:
    entries = []
    for kind, values in (("lib", [document["lib"]] if "lib" in document else []),
                         ("bin", document.get("bin", []))):
        if type(values) is not list or len(values) > 16:
            raise InputError("direct_dependency_invalid_target_entries")
        for value in values:
            value = _table(value)
            name = None if "name" not in value else _name(value["name"])
            path = None if "path" not in value else _text(value["path"], 512)
            if path is not None and (path.startswith(("/", "\\")) or "\\" in path or ":" in path
                                     or any(part in ("", ".", "..") for part in path.split("/"))):
                raise InputError("direct_dependency_unsupported_target_path_metadata")
            entries.append({"kind": kind, "name": name, "path": path,
                            "required_features": _features(value.get("required-features", []))})
    return entries


def manifest_fingerprint(row: dict) -> str:
    return record_digest({name: row[name] for name in MANIFEST_FIELDS if name != "source_fingerprint"})


def _workspace_paths(value: object) -> list[str]:
    if type(value) is not list or len(value) > 256:
        raise InputError("direct_dependency_invalid_workspace_path_metadata")
    # Patterns are retained as metadata only; inheritance never expands them.
    result = [_text(item, 1024) for item in value]
    if any(item.startswith("/") or "\\" in item or ":" in item for item in result):
        raise InputError("direct_dependency_unsafe_workspace_path_metadata")
    return result


def _manifest(metadata: dict, document: dict) -> dict:
    package = _table(document.get("package", {}))
    workspace = _table(document.get("workspace", {}))
    workspace_package = _table(workspace.get("package", {}))
    if "workspace" in package:
        _text(package["workspace"], 1024)
    version, inherited = _version(package)
    features = [{"name": _name(name), "members": _features(members, members=True)}
                for name, members in _table(document.get("features", {})).items()]
    groups = _groups(document)
    result = {**{name: deepcopy(metadata[name]) for name in MANIFEST_SOURCE_FIELDS},
              "package_name": None if "name" not in package else _name(package["name"]),
              "package_version": version, "package_version_workspace": inherited,
              "workspace_package_version": None if "version" not in workspace_package else _text(workspace_package["version"], 128),
              "is_workspace": "workspace" in document,
              "workspace_members": _workspace_paths(workspace.get("members", [])),
              "workspace_exclude": _workspace_paths(workspace.get("exclude", [])),
              "package_workspace_declared": "workspace" in package,
              "workspace_dependency_keys": [_name(name) for name in _table(workspace.get("dependencies", {}))],
              "features": features, "target_entries": _target_entries(document),
              "declaration_locations": [path + [_name(alias)] for path, _kind, table in groups for alias in table]}
    result["source_fingerprint"] = manifest_fingerprint(result)
    return result


def _source_declaration(manifest: dict, path: list[str], kind: str, alias: str, value: object) -> dict:
    detail = _cargo_detail(value)
    alias = _name(alias)
    field_path = path + [alias]
    locator = next((key for key in ("path", "git", "registry", "registry-index") if key in detail), None)
    locator_hash = None if locator is None else hashlib.sha256(detail[locator].encode("utf-8")).hexdigest()
    selectors = {key: detail[key] for key in ("branch", "tag", "rev") if key in detail}
    if len(selectors) > 1:
        raise InputError("direct_dependency_conflicting_git_selectors")
    workspace = detail.get("workspace") is True
    if workspace and set(detail) - {"workspace", "features", "optional", "default-features"}:
        raise InputError("direct_dependency_unsupported_workspace_override")
    return {"declaration_id": declaration_location_id(manifest["sha256"], field_path),
            "manifest_id": manifest["manifest_id"], "manifest_sha256": manifest["sha256"],
            "phase24_file_ref": manifest["phase24_file_ref"],
            "scope": "workspace_pool" if kind == "workspace_template" else "crate",
            "declaring_package_name": manifest["package_name"], "dependency_key": alias,
            "declared_package_name": None if "package" not in detail else _name(detail["package"]),
            "declared_requirement": detail.get("version"), "dependency_kind": kind,
            "target_condition": path[1] if path[0] == "target" else None,
            "toml_field_path": field_path, "workspace_inherited": workspace,
            "optional": detail.get("optional"),
            "features": None if "features" not in detail else _features(detail["features"]),
            "default_features": detail.get("default-features"),
            "source_locator_kind": None if locator is None else locator.replace("-", "_"),
            "source_locator_sha256": locator_hash,
            "git_reference_sha256": None if not selectors else record_digest(selectors),
            "activation_status": "activation_unknown", "target_evaluation": "not_performed"}


def extract_declarations(raw_by_id: dict[str, bytes], selected_metadata: list[dict]) -> tuple[list[dict], list[dict]]:
    """Only explicit input bytes; never follow dependency sources or entry paths."""
    metadata = {row["manifest_id"]: row for row in selected_metadata}
    if (len(metadata) != len(selected_metadata) or set(metadata) != set(raw_by_id)
            or not 1 <= len(metadata) <= MAX_MANIFESTS):
        raise InputError("direct_dependency_explicit_manifest_set_invalid")
    documents, manifests = {}, []
    for selected in selected_metadata:
        body = raw_by_id[selected["manifest_id"]]
        if (type(body) is not bytes or not 0 < len(body) <= MAX_MANIFEST_BYTES or len(body) != selected["bytes"]
                or hashlib.sha256(body).hexdigest() != selected["sha256"]):
            raise InputError("direct_dependency_manifest_bytes_mismatch")
        document = _toml(body)
        # Apply existing bounded integer/string JSON graph guards to parsed TOML.
        # Unsupported datetime/float metadata cannot masquerade as source proof.
        json_bytes(document)
        documents[selected["manifest_id"]] = document
        manifests.append(_manifest(selected, document))
    declarations, original_projections = [], {}
    for manifest in manifests:
        document = documents[manifest["manifest_id"]]
        roots = [item for item in manifests if item["root_id"] == manifest["root_id"]
                 and item["pinned_commit"] == manifest["pinned_commit"] and item["path"] == "Cargo.toml" and item["is_workspace"]]
        pool = {} if len(roots) != 1 else documents[roots[0]["manifest_id"]].get("workspace", {}).get("dependencies", {})
        for path, kind, table in _groups(document):
            for alias, value in table.items():
                if len(declarations) >= MAX_DECLARATIONS:
                    raise InputError("direct_dependency_declaration_limit")
                declaration = _source_declaration(manifest, path, kind, alias, value)
                declarations.append(declaration)
                if not declaration["workspace_inherited"] or len(roots) == 1 and alias in pool:
                    original_projections[declaration["declaration_id"]] = _cargo_declaration(
                        alias, value, pool, shared=kind == "workspace_template")
    normalized = rebuild_inheritance(manifests, declarations)
    for declaration in normalized:
        if declaration["legacy_projection"] is not None and declaration["declaration_id"] in original_projections and (
                declaration["legacy_projection"] != original_projections[declaration["declaration_id"]]):
            raise InputError("direct_dependency_owning_legacy_projection_mismatch")
    return manifests, normalized


__all__ = ("extract_declarations", "manifest_fingerprint")
