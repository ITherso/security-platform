"""Extract only explicit Cargo lib/bin declarations from supplied source bytes."""
from __future__ import annotations

from copy import deepcopy
import hashlib
import re

from commercial_composition.dependency_reader import _toml
from .coverage_contracts import InputError, closed, json_bytes, relative_path, record_digest


MANIFEST_METADATA_FIELDS = ("manifest_id", "root_id", "path", "format", "phase24_file_ref",
                            "bytes", "sha256", "pinned_commit")
PARSED_MANIFEST_FIELDS = (*MANIFEST_METADATA_FIELDS, "package_name", "is_workspace",
                          "target_locations", "source_fingerprint")
TARGET_FIELDS = ("target_reference", "manifest_reference", "manifest_sha256", "root_id",
                 "pinned_commit", "package_name", "target_kind", "declared_target_name",
                 "declared_relative_path", "normalized_relative_path", "toml_field_path",
                 "required_features", "target_declared", "target_path_declared",
                 "extraction_status", "source_fingerprint")
_NAME = re.compile(r"[A-Za-z0-9_][A-Za-z0-9_-]{0,127}\Z")


def _name(value: object) -> str:
    if type(value) is not str or _NAME.fullmatch(value) is None:
        raise InputError("entrypoint_unsupported_target_name")
    return value


def target_reference(root_id: str, pinned_commit: str, manifest_reference: str,
                     manifest_sha256: str, toml_field_path: list[str]) -> str:
    return "target-" + record_digest({"root_id": root_id, "pinned_commit": pinned_commit,
                                      "manifest_reference": manifest_reference,
                                      "manifest_sha256": manifest_sha256,
                                      "toml_field_path": toml_field_path})


def manifest_fingerprint(row: dict) -> str:
    return record_digest({name: row[name] for name in PARSED_MANIFEST_FIELDS if name != "source_fingerprint"})


def target_fingerprint(row: dict) -> str:
    return record_digest({name: row[name] for name in TARGET_FIELDS if name != "source_fingerprint"})


def normalize_target_path(manifest_path: str, declared_path: str | None) -> str | None:
    if declared_path is None:
        return None
    # This narrow reader accepts canonical relative paths, never traversals,
    # platform-specific paths or Cargo's automatic target discovery.
    relative_path(manifest_path, "target_manifest_path")
    relative_path(declared_path, "explicit_target_path")
    directory = manifest_path.rsplit("/", 1)[0] if "/" in manifest_path else ""
    result = directory + "/" + declared_path if directory else declared_path
    return relative_path(result, "root_relative_target_path")


def _entries(document: dict) -> list[tuple[list[str], str, dict]]:
    result = []
    if "lib" in document:
        if type(document["lib"]) is not dict:
            raise InputError("entrypoint_invalid_lib_target_table")
        result.append((["lib"], "lib", document["lib"]))
    bins = document.get("bin", [])
    if type(bins) is not list or len(bins) > 64 or any(type(row) is not dict for row in bins):
        raise InputError("entrypoint_invalid_bin_target_array")
    result.extend((["bin", str(index)], "bin", row) for index, row in enumerate(bins))
    return result


def extract_targets(raw_by_id: dict[str, bytes], metadata: list[dict]) -> tuple[list[dict], list[dict]]:
    """Parse given bytes only; target paths grant no authority to read files."""
    if type(raw_by_id) is not dict or type(metadata) is not list or not 1 <= len(metadata) <= 16:
        raise InputError("entrypoint_explicit_manifest_set_invalid")
    for row in metadata:
        closed(row, MANIFEST_METADATA_FIELDS, "entrypoint_manifest_metadata")
    identities = [row["manifest_id"] for row in metadata]
    if len(set(identities)) != len(identities) or set(raw_by_id) != set(identities):
        raise InputError("entrypoint_duplicate_or_unselected_manifest")
    manifests, targets = [], []
    for selected in metadata:
        body = raw_by_id[selected["manifest_id"]]
        if (selected["format"] != "cargo_toml" or type(selected["bytes"]) is not int
                or type(body) is not bytes or not 0 < len(body) <= 256 * 1024
                or len(body) != selected["bytes"] or hashlib.sha256(body).hexdigest() != selected["sha256"]):
            raise InputError("entrypoint_manifest_bytes_or_format_mismatch")
        relative_path(selected["path"], "entrypoint_manifest_path")
        document = _toml(body)
        # Existing strict graph bounds also reject unsupported TOML datetime or
        # floating-point values instead of retaining uncontrolled source data.
        json_bytes(document)
        package = document.get("package", {})
        if type(package) is not dict or ("workspace" in document and type(document["workspace"]) is not dict):
            raise InputError("entrypoint_invalid_package_or_workspace_table")
        package_name = None if "name" not in package else _name(package["name"])
        entries = _entries(document)
        manifest = {**deepcopy(selected), "package_name": package_name,
                    "is_workspace": "workspace" in document,
                    "target_locations": [deepcopy(path) for path, _kind, _entry in entries]}
        manifest["source_fingerprint"] = manifest_fingerprint(manifest)
        manifests.append(manifest)
        for location, kind, entry in entries:
            if len(targets) >= 64:
                raise InputError("entrypoint_target_declaration_limit")
            name = None if "name" not in entry else _name(entry["name"])
            path = entry.get("path")
            if "path" in entry and type(path) is not str:
                raise InputError("entrypoint_invalid_declared_target_path")
            normalized = normalize_target_path(selected["path"], path)
            features = entry.get("required-features", [])
            if type(features) is not list or len(features) > 256:
                raise InputError("entrypoint_invalid_required_features")
            features = [_name(feature) for feature in features]
            row = {"target_reference": target_reference(selected["root_id"], selected["pinned_commit"],
                                                        selected["manifest_id"], selected["sha256"], location),
                   "manifest_reference": selected["manifest_id"], "manifest_sha256": selected["sha256"],
                   "root_id": selected["root_id"], "pinned_commit": selected["pinned_commit"],
                   "package_name": package_name, "target_kind": kind, "declared_target_name": name,
                   "declared_relative_path": path, "normalized_relative_path": normalized,
                   "toml_field_path": deepcopy(location), "required_features": features,
                   "target_declared": True, "target_path_declared": path is not None,
                   "extraction_status": "explicit_path_declared" if path is not None else "entrypoint_not_established"}
            row["source_fingerprint"] = target_fingerprint(row)
            targets.append(row)
    return manifests, targets


__all__ = ("extract_targets", "target_reference", "manifest_fingerprint", "target_fingerprint",
           "normalize_target_path")
