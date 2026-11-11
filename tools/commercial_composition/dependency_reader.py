"""Read explicit source declarations and lock records without resolving packages.

Only SourceContext's already selected bytes are read. Source locators are hashed,
never followed or rendered. Declaration rows and whole-workspace lock rows stay
separate; neither selected features nor a distributable dependency closure is
inferred here.
"""
from __future__ import annotations

import hashlib
import re
import tomllib
from typing import TYPE_CHECKING

from .composition_contracts import InputError, LEDGER_SCHEMA, MAX_DEPENDENCY_RECORDS, common

if TYPE_CHECKING:
    from .source_inventory import SourceContext


_RUST_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,127}\Z")
_RUST_VERSION = re.compile(
    r"[0-9]+\.[0-9]+\.[0-9]+(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?\Z"
)
_CARGO_REQUIREMENT_PART = (
    r"(?:[~^<>=]{1,2})?\s*(?:\*|[0-9]+(?:\.(?:[0-9]+|\*|x|X)){0,2}"
    r"(?:-[0-9A-Za-z.-]+)?(?:\+[0-9A-Za-z.-]+)?)"
)
_REQUIREMENT = re.compile(
    _CARGO_REQUIREMENT_PART + r"(?:\s*,\s*" + _CARGO_REQUIREMENT_PART + r")*\Z"
)
_PYTHON_VERSION = re.compile(
    r"(?:[0-9]+!)?[0-9]+(?:\.[0-9]+)*(?:(?:a|b|rc)[0-9]+)?"
    r"(?:\.post[0-9]+)?(?:\.dev[0-9]+)?(?:\+[A-Za-z0-9]+(?:[._-][A-Za-z0-9]+)*)?\Z"
)
_PYTHON_REQUIREMENT = re.compile(
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"(?:\[[A-Za-z0-9_-]+(?:,[A-Za-z0-9_-]+)*\])?"
    r"(?P<spec>[^\s]*)\Z"
)
_PIN = re.compile(
    r"(?P<name>[A-Za-z0-9](?:[A-Za-z0-9._-]*[A-Za-z0-9])?)"
    r"==(?P<version>[A-Za-z0-9.!+_-]+)\Z"
)
_HEX = re.compile(r"[0-9a-f]{64}\Z")
_CARGO_SECTIONS = ("dependencies", "dev-dependencies", "build-dependencies")
_CARGO_DETAIL_KEYS = frozenset((
    "version", "package", "registry", "registry-index", "git", "branch",
    "tag", "rev", "path", "workspace", "features", "optional", "default-features",
))
_MAX_RECORDS = MAX_DEPENDENCY_RECORDS


def _text(value: object, maximum: int = 2048) -> str:
    if (type(value) is not str or not 0 < len(value) <= maximum
            or value != value.strip() or any(ord(char) < 32 for char in value)):
        raise InputError("composition_invalid_dependency_metadata")
    return value


def _table(value: object) -> dict:
    if type(value) is not dict:
        raise InputError("composition_invalid_dependency_table")
    return value


def _array(value: object) -> list:
    if type(value) is not list or len(value) > _MAX_RECORDS:
        raise InputError("composition_invalid_dependency_array")
    return value


def _toml(raw: bytes) -> dict:
    try:
        text = raw.decode("utf-8", "strict")
        if text.startswith("\ufeff"):
            raise InputError("composition_dependency_bom_not_supported")
        return tomllib.loads(text)
    except (UnicodeError, tomllib.TOMLDecodeError, RecursionError):
        raise InputError("composition_invalid_dependency_toml") from None


def _rust_name(value: object) -> str:
    name = _text(value, 128)
    if _RUST_NAME.fullmatch(name) is None:
        raise InputError("composition_invalid_cargo_package_name")
    return name


def _requirement(value: object) -> str:
    requirement = _text(value, 256)
    if _REQUIREMENT.fullmatch(requirement) is None:
        raise InputError("composition_unsupported_cargo_requirement")
    return requirement


def _identity(value: str | None) -> str | None:
    return None if value is None else hashlib.sha256(value.encode("utf-8")).hexdigest()


def _row(ecosystem: str, name: str, *, version: str | None = None,
         requirement: str | None = None, source_type: str = "unknown",
         checksum: str | None = None, source_identity: str | None = None,
         relation: str = "direct_declaration", directness: str = "unknown") -> dict:
    return {
        "ecosystem": ecosystem, "name": name, "version": version,
        "declared_requirement": requirement, "source_type": source_type,
        "source_checksum": checksum, "source_identity_sha256": source_identity,
        "relation": relation, "directness": directness,
        "local_package_artifact": "not_selected_or_verified",
    }


def _cargo_detail(value: object) -> dict:
    if type(value) is str:
        return {"version": _requirement(value)}
    detail = _table(value)
    if not detail or set(detail) - _CARGO_DETAIL_KEYS:
        raise InputError("composition_unsupported_cargo_dependency_fields")
    for key in ("optional", "default-features", "workspace"):
        if key in detail and type(detail[key]) is not bool:
            raise InputError("composition_invalid_cargo_dependency_boolean")
    if "workspace" in detail and detail["workspace"] is not True:
        raise InputError("composition_invalid_cargo_workspace_inheritance")
    for key in ("git", "branch", "tag", "rev", "path", "registry", "registry-index"):
        if key in detail:
            _text(detail[key])
    if "package" in detail:
        _rust_name(detail["package"])
    if "version" in detail:
        _requirement(detail["version"])
    if "features" in detail:
        for feature in _array(detail["features"]):
            _text(feature, 256)
    if sum(key in detail for key in ("git", "path", "registry", "registry-index")) > 1:
        raise InputError("composition_conflicting_cargo_dependency_sources")
    if any(key in detail for key in ("branch", "tag", "rev")) and "git" not in detail:
        raise InputError("composition_invalid_cargo_git_selector")
    return detail


def _cargo_declaration(alias: str, value: object, pool: dict, *, shared: bool) -> dict:
    _rust_name(alias)
    detail = _cargo_detail(value)
    if "workspace" in detail:
        if shared or set(detail) - {"workspace", "features", "optional", "default-features"}:
            raise InputError("composition_unsupported_cargo_workspace_override")
        if alias not in pool:
            raise InputError("composition_missing_explicit_cargo_workspace_dependency")
        detail = _cargo_detail(pool[alias])
        if "workspace" in detail:
            raise InputError("composition_invalid_cargo_workspace_inheritance")
    name = _rust_name(detail.get("package", alias))
    locator = next((detail[key] for key in ("path", "git", "registry", "registry-index")
                    if key in detail), None)
    # A local path is not proof of workspace membership or first-party ownership.
    source_type = ("unknown" if "path" in detail else "git" if "git" in detail
                   else "registry" if "version" in detail or locator is not None else "unknown")
    if source_type == "unknown" and locator is None:
        raise InputError("composition_missing_cargo_dependency_source")
    return _row("rust", name, requirement=detail.get("version"), source_type=source_type,
                source_identity=_identity(locator),
                directness="unknown" if shared else "direct_in_selected_manifest")


def _cargo_manifest(document: dict, workspace_document: dict | None) -> list[dict]:
    workspace = _table((workspace_document or {}).get("workspace", {}))
    pool = _table(workspace.get("dependencies", {}))
    package = _table(document.get("package", {}))
    if "version" in package:
        version = package["version"]
        if type(version) is dict:
            if set(version) != {"workspace"} or version["workspace"] is not True:
                raise InputError("composition_unsupported_cargo_package_version")
            version = _table(workspace.get("package", {})).get("version")
        if _RUST_VERSION.fullmatch(_text(version, 128)) is None:
            raise InputError("composition_invalid_cargo_package_version")
    rows = []
    local_workspace = _table(document.get("workspace", {}))
    for alias, value in _table(local_workspace.get("dependencies", {})).items():
        rows.append(_cargo_declaration(alias, value, pool, shared=True))
    for section in _CARGO_SECTIONS:
        for alias, value in _table(document.get(section, {})).items():
            rows.append(_cargo_declaration(alias, value, pool, shared=False))
    for target in _table(document.get("target", {})).values():
        target = _table(target)
        for section in _CARGO_SECTIONS:
            for alias, value in _table(target.get(section, {})).items():
                rows.append(_cargo_declaration(alias, value, pool, shared=False))
    return rows


def _cargo_lock(document: dict) -> list[dict]:
    if set(document) != {"version", "package"} or type(document["version"]) is not int:
        raise InputError("composition_unsupported_cargo_lock_shape")
    if document["version"] != 4:
        raise InputError("composition_unsupported_cargo_lock_version")
    rows, seen = [], set()
    for item in _array(document["package"]):
        item = _table(item)
        if not {"name", "version"} <= set(item) or set(item) - {
                "name", "version", "source", "checksum", "dependencies"}:
            raise InputError("composition_unsupported_cargo_lock_package")
        name = _rust_name(item["name"])
        version = _text(item["version"], 128)
        if _RUST_VERSION.fullmatch(version) is None:
            raise InputError("composition_invalid_cargo_lock_package_version")
        source = None if "source" not in item else _text(item["source"])
        # Missing lock source does not establish a local package's ownership.
        source_type = ("unknown" if source is None else "registry" if source.startswith("registry+")
                       else "git" if source.startswith("git+") else "unknown")
        checksum = item.get("checksum")
        if checksum is not None and (type(checksum) is not str or _HEX.fullmatch(checksum) is None):
            raise InputError("composition_invalid_cargo_checksum")
        if source_type == "registry" and checksum is None:
            raise InputError("composition_missing_cargo_registry_checksum")
        if source is None and checksum is not None:
            raise InputError("composition_cargo_workspace_checksum_without_source")
        for dependency in _array(item.get("dependencies", [])):
            _text(dependency)
        identity = (name, version, source)
        if identity in seen:
            raise InputError("composition_duplicate_cargo_lock_record")
        seen.add(identity)
        rows.append(_row("rust", name, version=version, source_type=source_type,
                         checksum=checksum, source_identity=_identity(source), relation="lock_record"))
    return rows


def _python_declaration(requirement: object) -> dict:
    requirement = _text(requirement, 512)
    matched = _PYTHON_REQUIREMENT.fullmatch(requirement)
    if matched is None or len(matched["name"]) > 128:
        raise InputError("composition_unsupported_python_requirement")
    # Finite static name/extras/specifier syntax only, not a PEP508 resolver.
    # URL, environment-marker, wildcard and dynamic dependency inputs are not
    # silently interpreted as successfully parsed ordinary index declarations.
    if matched["spec"]:
        for part in matched["spec"].split(","):
            specifier = re.fullmatch(r"(?:===|==|!=|~=|<=|>=|<|>)(.+)", part)
            if specifier is None or _PYTHON_VERSION.fullmatch(specifier[1]) is None:
                raise InputError("composition_unsupported_python_requirement")
    return _row("python", matched["name"], requirement=requirement,
                source_type="declared_index", directness="direct_in_selected_manifest")


def _pyproject(document: dict) -> list[dict]:
    if "project" not in document:
        raise InputError("composition_missing_python_project_metadata")
    project = _table(document["project"])
    dynamic = _array(project.get("dynamic", []))
    if any(type(field) is not str for field in dynamic) or any(
            field in dynamic for field in ("dependencies", "optional-dependencies")):
        raise InputError("composition_dynamic_python_dependencies_unsupported")
    declarations = list(_array(project.get("dependencies", [])))
    for optional in _table(project.get("optional-dependencies", {})).values():
        declarations.extend(_array(optional))
    build = _table(document.get("build-system", {}))
    declarations.extend(_array(build.get("requires", [])))
    return [_python_declaration(item) for item in declarations]


def _requirements(raw: bytes) -> list[dict]:
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("composition_invalid_requirements_utf8") from None
    if text.startswith("\ufeff"):
        raise InputError("composition_dependency_bom_not_supported")
    rows, seen = [], set()
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        matched = _PIN.fullmatch(line)
        if matched is None or len(line) > 512 or len(matched["name"]) > 128:
            raise InputError("composition_unsupported_requirements_pin")
        name, version = matched["name"], matched["version"]
        if len(version) > 128 or _PYTHON_VERSION.fullmatch(version) is None:
            raise InputError("composition_invalid_requirements_pin")
        normalized = re.sub(r"[-_.]+", "-", name).lower()
        if normalized in seen:
            raise InputError("composition_duplicate_requirements_pin")
        seen.add(normalized)
        rows.append(_row("python", name, version=version, requirement=line,
                         source_type="declared_index", relation="lock_record"))
    return rows


def read_dependencies(ctx: SourceContext, inventory: dict) -> dict:
    """Return bounded source metadata, with license evidence populated later."""
    if inventory["candidate_reference"] != ctx.scope["candidate_reference"]:
        raise InputError("composition_dependency_scope_identity_mismatch")
    selections = ctx.scope["dependency_manifests"]
    metadata = {item["file_id"]: item for item in inventory["files"]}
    prepared = []
    workspaces = {}
    for selection in selections:
        key = (selection["root_id"], selection["path"])
        raw = ctx.raw(*key)
        ref = ctx.file_ref(*key)
        file = metadata.get(ref)
        if (file is None or (file["root_id"], file["path"]) != key
                or len(raw) != file["bytes"] or hashlib.sha256(raw).hexdigest() != file["sha256"]):
            raise InputError("composition_dependency_file_identity_mismatch")
        format_name = selection["format"]
        document = _toml(raw) if format_name in ("cargo_toml", "cargo_lock", "pyproject_toml") else None
        prepared.append((selection, file, raw, document))
        if format_name == "cargo_toml" and selection["path"] == "Cargo.toml":
            workspaces[selection["root_id"]] = document
    manifests, dependencies = [], []
    for selection, file, raw, document in prepared:
        format_name, context = selection["format"], selection["context"]
        if format_name in ("pyproject_toml", "requirements_lock") and context != "excluded_backend_context":
            raise InputError("composition_python_backend_context_required")
        if format_name == "cargo_toml":
            rows = _cargo_manifest(document, workspaces.get(selection["root_id"]))
        elif format_name == "cargo_lock":
            rows = _cargo_lock(document)
        elif format_name == "pyproject_toml":
            rows = _pyproject(document)
        elif format_name == "requirements_lock":
            rows = _requirements(raw)
        elif format_name == "unsupported_yaml":
            rows = []
        else:
            raise InputError("composition_unsupported_dependency_format")
        status = "unsupported" if format_name == "unsupported_yaml" else "parsed"
        limitation = ("unsupported_format_not_parsed" if status == "unsupported" else
                      "excluded_backend_context_only" if context == "excluded_backend_context" else
                      "whole_workspace_lock_not_selected_build" if format_name == "cargo_lock" else
                      "selected_manifest_declarations_only")
        manifests.append({
            "manifest_id": selection["manifest_id"], "root_id": selection["root_id"],
            "path": selection["path"], "sha256": file["sha256"], "bytes": file["bytes"],
            "format": format_name, "context": context, "parse_status": status,
            "record_count": len(rows), "limitation_code": limitation,
        })
        for row in rows:
            if len(dependencies) >= _MAX_RECORDS:
                raise InputError("composition_dependency_record_limit")
            dependencies.append({"dependency_id": f"D{len(dependencies) + 1:04d}",
                                 "manifest_id": selection["manifest_id"],
                                 **row, "review_scope": context})
    return {
        **common(LEDGER_SCHEMA, ctx.scope["candidate_reference"]),
        "manifest_records": manifests, "dependencies": dependencies, "license_evidence": [],
        "counts": {"manifest_count": len(manifests), "dependency_record_count": len(dependencies),
                   "license_evidence_count": 0, "unknown_license_subject_count": 0},
    }


__all__ = ("read_dependencies",)
