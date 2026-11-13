"""Fixed four-member capsule format and narrow exclusive publication.

Standard library and local portable modules only. No original-source readers.
"""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path, PureWindowsPath
import stat
import tempfile
import zipfile

from capsule_contracts import (
    InputError, MAX_ZIP_BYTES, MAX_MEMBER_BYTES, MAX_EXPANDED_BYTES,
    BUNDLE_MANIFEST_SCHEMA, ASSEMBLY_MANIFEST_SCHEMA, common, json_bytes, validate_capsule,
)
from capsule_renderer import README_BYTES, render_capsule_summary

ZIP_NAMES = ("reference-capsule.json", "reference-summary.md", "bundle-manifest.json", "README.txt")
PAYLOAD_NAMES = ("reference-capsule.json", "reference-summary.md", "README.txt")
ASSEMBLY_PAYLOAD_NAMES = ("guarded-reference-capsule.zip", "capsule-source-bindings.json", "capsule-assembly-summary.md")
ASSEMBLY_NAMES = (*ASSEMBLY_PAYLOAD_NAMES, "assembly-manifest.json")
REGULAR_FILE_ATTRIBUTES = (stat.S_IFREG | 0o600) << 16


def byte_identity(raw: bytes) -> dict:
    return {"bytes": len(raw), "sha256": hashlib.sha256(raw).hexdigest()}


def _manifest(schema: str, capsule: dict, payloads: dict, names: tuple) -> dict:
    capsule = validate_capsule(capsule)
    if type(payloads) is not dict or tuple(payloads) != names:
        raise InputError("reference_capsule_payload_inventory_invalid")
    rows = []
    for name, raw in payloads.items():
        maximum = MAX_ZIP_BYTES if name.endswith(".zip") else MAX_MEMBER_BYTES
        if type(raw) is not bytes or not 0 < len(raw) <= maximum:
            raise InputError("reference_capsule_payload_size_invalid")
        rows.append({"name": name, **byte_identity(raw)})
    return {**common(schema, capsule["capsule_reference"], capsule["source_bindings"]),
            "files": rows, "counts": capsule["counts"], "manifest_self_excluded": True,
            "integrity_scope": "internal_byte_and_model_correspondence_only"}


def bundle_manifest(capsule: dict, payloads: dict) -> dict:
    return _manifest(BUNDLE_MANIFEST_SCHEMA, capsule, payloads, PAYLOAD_NAMES)


def assembly_manifest(capsule: dict, payloads: dict) -> dict:
    return _manifest(ASSEMBLY_MANIFEST_SCHEMA, capsule, payloads, ASSEMBLY_PAYLOAD_NAMES)


def zip_bytes(capsule: dict) -> bytes:
    capsule = validate_capsule(capsule)
    payloads = {"reference-capsule.json": json_bytes(capsule),
                "reference-summary.md": render_capsule_summary(capsule), "README.txt": README_BYTES}
    documents = {**payloads, "bundle-manifest.json": json_bytes(bundle_manifest(capsule, payloads))}
    if any(not 0 < len(raw) <= MAX_MEMBER_BYTES for raw in documents.values()) or sum(map(len, documents.values())) > MAX_EXPANDED_BYTES:
        raise InputError("reference_capsule_expanded_size_invalid")
    buffer = io.BytesIO()
    # STORED has ratio 1, so our own fixed-format output always obeys ratio 20.
    # The inspector also supports bounded DEFLATED inputs. Repeat-run acceptance
    # has not been performed merely because member metadata is deterministic.
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED, allowZip64=False) as archive:
        for name in ZIP_NAMES:
            info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = REGULAR_FILE_ATTRIBUTES
            info.compress_type = zipfile.ZIP_STORED
            archive.writestr(info, documents[name])
    raw = buffer.getvalue()
    if not 0 < len(raw) <= MAX_ZIP_BYTES:
        raise InputError("reference_capsule_archive_size_invalid")
    return raw


def explicit_path(raw: str) -> Path:
    if type(raw) is not str or not raw or len(raw) > 512 or PureWindowsPath(raw).drive:
        raise InputError("reference_capsule_explicit_relative_path_required")
    normalized = raw.replace("\\", "/")
    parts = normalized.split("/")
    reserved = {"CON", "PRN", "AUX", "NUL", *("COM" + str(n) for n in range(1, 10)), *("LPT" + str(n) for n in range(1, 10))}
    if any(not p or p in (".", "..") or p[-1:] in (" ", ".")
           or p.split(".", 1)[0].upper() in reserved
           or any(ord(c) < 32 or ord(c) == 127 or c in '<>:"|?*' for c in p) for p in parts):
        raise InputError("reference_capsule_unsafe_path")
    return Path(*parts)


def check_path(path: Path, *, directory: bool):
    absolute = path.absolute()
    for ancestor in (*reversed(absolute.parents), absolute):
        info = ancestor.lstat()
        if stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400):
            raise InputError("reference_capsule_link_or_reparse_rejected")
        if ancestor != absolute and not stat.S_ISDIR(info.st_mode):
            raise InputError("reference_capsule_parent_type_invalid")
    if (directory and not stat.S_ISDIR(info.st_mode)) or (not directory and not stat.S_ISREG(info.st_mode)):
        raise InputError("reference_capsule_path_type_invalid")
    return info


def same_directory(path: Path, expected) -> None:
    current = check_path(path, directory=True)
    if (current.st_dev, current.st_ino) != (expected.st_dev, expected.st_ino):
        raise InputError("reference_capsule_output_directory_changed")


def _publish(parent: Path, parent_info, documents: dict[str, bytes], output: Path | None = None) -> None:
    stage = Path(tempfile.mkdtemp(prefix=".reference-capsule-", dir=parent))
    stage_info = check_path(stage, directory=True)
    try:
        for name, raw in documents.items():
            same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
        same_directory(parent, parent_info)
        destination = parent
        destination_info = parent_info
        if output is not None:
            output.mkdir(exist_ok=False)
            destination, destination_info = output, check_path(output, directory=True)
        for name in documents:
            same_directory(parent, parent_info)
            same_directory(destination, destination_info)
            same_directory(stage, stage_info)
            os.link(stage / name, destination / name, follow_symlinks=False)
    finally:
        try:
            same_directory(stage, stage_info)
            for name in documents:
                item = stage / name
                if os.path.lexists(item):
                    check_path(item, directory=False)
                    item.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass


def publish_assembly(raw_output_dir: str, documents: dict[str, bytes]) -> None:
    if type(documents) is not dict or tuple(documents) != ASSEMBLY_NAMES:
        raise InputError("reference_capsule_assembly_inventory_invalid")
    for name, raw in documents.items():
        maximum = MAX_ZIP_BYTES if name.endswith(".zip") else MAX_MEMBER_BYTES
        if type(raw) is not bytes or not 0 < len(raw) <= maximum:
            raise InputError("reference_capsule_assembly_size_invalid")
    output = explicit_path(raw_output_dir)
    parent_info = check_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("reference_capsule_output_must_be_new")
    _publish(output.parent, parent_info, documents, output)


def publish_inspection(inspection_output: str, lookup_output: str, inspection: dict, lookup: dict) -> None:
    first, second = explicit_path(inspection_output), explicit_path(lookup_output)
    if (first.parent != second.parent or first.name.casefold() == second.name.casefold()
            or first.suffix.lower() != ".json" or second.suffix.lower() != ".json"):
        raise InputError("reference_capsule_distinct_same_parent_json_outputs_required")
    parent_info = check_path(first.parent, directory=True)
    if os.path.lexists(first) or os.path.lexists(second):
        raise InputError("reference_capsule_inspection_output_must_be_new")
    _publish(first.parent, parent_info, {first.name: json_bytes(inspection), second.name: json_bytes(lookup)})
