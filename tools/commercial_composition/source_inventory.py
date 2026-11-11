"""Read only explicitly scoped, bounded text files; emit metadata, never bodies."""
from __future__ import annotations

from dataclasses import dataclass
import hashlib
import os
from pathlib import Path
import stat
import tomllib
from types import MappingProxyType

from commercial_handoff.input_loader import check_existing_path
from .composition_contracts import (
    InputError, INVENTORY_SCHEMA, common, relative_path, validate_scope,
)


def _identity(info):
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_nlink)


def _same_api_identity(info):
    # Windows lstat and fstat can expose different ctime meanings. Keep ctime
    # checks within each API family rather than treating the two as equal.
    return (*_identity(info), info.st_ctime_ns)


def read_explicit_text(path: Path, maximum: int) -> tuple[bytes, tuple]:
    """Do not resolve away link evidence; reject aliases and changing sources."""
    checked = check_existing_path(path, directory=False)
    if not 0 < checked.st_size <= maximum or checked.st_nlink != 1:
        raise InputError("composition_source_size_or_hardlink_rejected")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or _identity(opened) != _identity(checked)
                or getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("composition_source_identity_changed")
        raw = stream.read(maximum + 1)
        after_open = os.fstat(stream.fileno())
    after_path = check_existing_path(path, directory=False)
    if (len(raw) != checked.st_size or len(raw) > maximum
            or _same_api_identity(after_open) != _same_api_identity(opened)
            or _same_api_identity(after_path) != _same_api_identity(checked)):
        raise InputError("composition_source_changed_during_read")
    text = raw.decode("utf-8", "strict")
    if text.startswith("\ufeff"):
        raise InputError("composition_utf8_bom_not_supported")
    return raw, _same_api_identity(checked)


@dataclass(frozen=True, slots=True)
class SourceContext:
    scope: dict
    scope_identity: dict
    files: tuple[dict, ...]
    _raw: object
    _refs: object
    _paths: object
    _identities: object

    def raw(self, root_id: str, path: str) -> bytes:
        try:
            return self._raw[(root_id, path)]
        except KeyError:
            raise InputError("composition_unselected_source") from None

    def file_ref(self, root_id: str, path: str) -> str:
        try:
            return self._refs[(root_id, path)]
        except KeyError:
            raise InputError("composition_unselected_source_reference") from None

    def check_stability(self) -> None:
        for key, path in self._paths.items():
            current = check_existing_path(path, directory=False)
            if _same_api_identity(current) != self._identities[key]:
                raise InputError("composition_source_changed_before_publication")


def load_sources(scope: dict, roots: dict[str, str], scope_identity: dict) -> SourceContext:
    scope = validate_scope(scope)
    expected_roots = {r["root_id"] for r in scope["source_roots"]}
    if set(roots) != expected_roots:
        raise InputError("composition_explicit_roots_required")
    locations = {}
    for root_id, raw in roots.items():
        path = Path(raw).absolute()
        check_existing_path(path, directory=True)
        locations[root_id] = path
    if len({os.path.normcase(str(p)) for p in locations.values()}) != len(locations):
        raise InputError("composition_duplicate_source_root")
    selected = set()
    for component in scope["included_components"]:
        selected.update((component["root_id"], p) for p in component["source_files"])
        if component["manifest_path"] is not None:
            selected.add((component["root_id"], component["manifest_path"]))
    for item in scope["dependency_manifests"] + scope["license_evidence_sources"]:
        selected.add((item["root_id"], item["path"]))
    limits = scope["inspection_constraints"]
    if not 0 < len(selected) <= limits["max_files"]:
        raise InputError("composition_source_file_count_limit")
    bodies, refs, paths, identities, files = {}, {}, {}, {}, []
    total = 0
    physical = set()
    for root_id, raw_path in sorted(selected):
        path_text = relative_path(raw_path, "source_path")
        path = locations[root_id].joinpath(*path_text.split("/"))
        # lexical canonical relative paths plus every-component checks keep the root boundary.
        if os.path.commonpath((str(locations[root_id]), str(path))) != str(locations[root_id]):
            raise InputError("composition_source_root_escape")
        checked = check_existing_path(path, directory=False)
        if total + checked.st_size > limits["max_total_source_bytes"]:
            raise InputError("composition_total_source_byte_limit")
        raw, identity = read_explicit_text(path, limits["max_file_bytes"])
        if (identity[0], identity[1]) in physical:
            raise InputError("composition_source_alias_rejected")
        physical.add((identity[0], identity[1]))
        total += len(raw)
        if total > limits["max_total_source_bytes"]:
            raise InputError("composition_total_source_byte_limit")
        key = (root_id, path_text)
        ref = "F" + str(len(files) + 1).zfill(4)
        files.append({"file_id": ref, "root_id": root_id, "path": path_text,
                      "bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest(),
                      "local_artifact_present": True})
        bodies[key], refs[key], paths[key], identities[key] = raw, ref, path, identity
    context = SourceContext(scope, dict(scope_identity), tuple(files),
                            MappingProxyType(bodies), MappingProxyType(refs),
                            MappingProxyType(paths), MappingProxyType(identities))
    context.check_stability()
    return context


def _version(ctx: SourceContext, component: dict) -> str | None:
    path = component["manifest_path"]
    if path is None or component["version_scope"] == "not_declared":
        return None
    data = tomllib.loads(ctx.raw(component["root_id"], path).decode("utf-8"))
    if component["version_scope"] == "project_metadata_not_tool_release":
        value = data.get("project", {}).get("version")
    else:
        value = data.get("package", {}).get("version")
        if isinstance(value, dict) and value == {"workspace": True}:
            workspace = tomllib.loads(ctx.raw(component["root_id"], "Cargo.toml").decode("utf-8"))
            value = workspace.get("workspace", {}).get("package", {}).get("version")
    if value is not None and (type(value) is not str or not 0 < len(value) <= 128):
        raise InputError("composition_invalid_version_metadata")
    return value


def build_inventory(ctx: SourceContext) -> dict:
    roots = {r["root_id"]: r for r in ctx.scope["source_roots"]}
    components = []
    for row in ctx.scope["included_components"]:
        root = roots[row["root_id"]]
        selected = set(row["source_files"])
        if row["manifest_path"] is not None:
            selected.add(row["manifest_path"])
        components.append({"component_id": row["component_id"], "root_id": row["root_id"],
                           "repository_label": root["repository_label"],
                           "pinned_commit": root["pinned_commit"], "role": row["role"],
                           "manifest_path": row["manifest_path"],
                           "source_file_refs": sorted(ctx.file_ref(row["root_id"], p) for p in selected),
                           "version_declaration": _version(ctx, row),
                           "version_scope": row["version_scope"], "source_present": True,
                           "distribution_status": "proposed_source_only"})
    return {**common(INVENTORY_SCHEMA, ctx.scope["candidate_reference"]),
            "source_scope": ctx.scope_identity, "source_roots": ctx.scope["source_roots"],
            "components": components, "excluded_components": ctx.scope["excluded_components"],
            "files": list(ctx.files), "dependency_manifest_refs": ctx.scope["dependency_manifests"],
            "actual_distributable_artifacts": [],
            "counts": {"component_count": len(components), "file_count": len(ctx.files),
                       "excluded_component_count": len(ctx.scope["excluded_components"]),
                       "total_selected_source_bytes": sum(r["bytes"] for r in ctx.files)},
            "scope_limitations": ["explicit_selected_files_only",
                                  "commit_pin_is_reviewed_scope_declaration_not_git_or_build_attestation",
                                  "not_complete_runtime_or_feature_dependency_closure",
                                  "source_metadata_not_distributable_artifacts",
                                  "no_secret_detection_or_legal_clearance_guarantee"]}
