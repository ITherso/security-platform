"""Independent bounded ZIP inspection; original source paths are never read."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import stat
import tempfile
import zipfile
import zlib

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_handoff.manifest import _same_directory

from .bundle_writer import (
    INSPECTION_CONTRACT, INTEGRITY_LIMIT, MAX_COMPRESSION_RATIO,
    MAX_EXPANDED_BYTES, MAX_ZIP_BYTES, MEMBER_LIMITS, PAYLOAD_NAMES,
    REGULAR_FILE_ATTRIBUTES, SOURCE_RECHECK_LIMIT, ZIP_NAMES, manifest_metadata,
)
from .case_contracts import (
    CASE_CONTRACT, DEMO_LABEL, FALSE_FLAGS, CaseEvidence, InputError, json_bytes,
    parse_json_bytes, projection_to_dict, validate_projection, validate_source_index,
)
from .safe_projection import CASE_README_BYTES, build_projection, render_case_summary


def _read_zip(raw_path: str) -> bytes:
    path = explicit_relative_path(raw_path)
    checked = check_existing_path(path, directory=False)
    if path.suffix.lower() != ".zip" or not 0 < checked.st_size <= MAX_ZIP_BYTES:
        raise InputError("case_invalid_zip_file_size_or_type")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (checked.st_dev, checked.st_ino)
                or getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("case_zip_input_identity_changed")
        raw = stream.read(MAX_ZIP_BYTES + 1)
    if not 0 < len(raw) <= MAX_ZIP_BYTES or len(raw) != opened.st_size:
        raise InputError("case_zip_size_limit")
    return raw


def _members(raw_zip: bytes) -> dict[str, bytes]:
    """Read at most the five named bounded members in memory, never extract."""
    try:
        with zipfile.ZipFile(io.BytesIO(raw_zip), "r", allowZip64=False) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if (archive.comment or len(infos) != len(ZIP_NAMES)
                    or len(set(names)) != len(names) or set(names) != set(ZIP_NAMES)):
                raise InputError("case_zip_member_inventory_mismatch")
            expanded = 0
            for info in infos:
                if (info.filename != info.orig_filename or info.is_dir()
                        or info.extra or info.comment
                        or info.flag_bits & ~0x800
                        or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or info.create_system != 3
                        or info.external_attr != REGULAR_FILE_ATTRIBUTES
                        or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG
                        or info.extract_version > 20
                        or not 0 < info.file_size <= MEMBER_LIMITS[info.filename]
                        or not 0 < info.compress_size <= MAX_ZIP_BYTES
                        or info.file_size > info.compress_size * MAX_COMPRESSION_RATIO):
                    raise InputError("case_zip_unsupported_or_unsafe_member")
                expanded += info.file_size
                if expanded > MAX_EXPANDED_BYTES:
                    raise InputError("case_zip_expanded_size_limit")
            members = {}
            actual_expanded = 0
            for info in infos:
                maximum = MEMBER_LIMITS[info.filename]
                with archive.open(info, "r") as stream:
                    data = stream.read(maximum + 1)
                if not 0 < len(data) <= maximum or len(data) != info.file_size:
                    raise InputError("case_zip_member_size_mismatch")
                actual_expanded += len(data)
                if actual_expanded > MAX_EXPANDED_BYTES:
                    raise InputError("case_zip_expanded_size_limit")
                members[info.filename] = data
    except InputError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError,
            NotImplementedError, EOFError, ValueError, UnicodeError, zlib.error):
        raise InputError("case_invalid_zip_bundle") from None
    return members


def inspect_case_bundle(raw_path: str) -> dict:
    """Report internal content consistency only, not source or producer proof."""
    raw_zip = _read_zip(raw_path)
    members = _members(raw_zip)
    projection = validate_projection(parse_json_bytes(
        members["case-ledger.json"], maximum=MEMBER_LIMITS["case-ledger.json"]))
    expected_projection = build_projection(projection.case_reference, CaseEvidence(
        projection.artifacts, projection.relationships, projection.observations,
        projection.facts))
    if projection != expected_projection:
        raise InputError("case_bundle_workflow_projection_mismatch")
    ledger = projection_to_dict(projection)
    index = parse_json_bytes(members["source-index.json"],
                             maximum=MEMBER_LIMITS["source-index.json"])
    validate_source_index(index, projection)
    actual_manifest = parse_json_bytes(members["bundle-manifest.json"],
                                       maximum=MEMBER_LIMITS["bundle-manifest.json"])
    expected_manifest = manifest_metadata(projection.case_reference,
                                         {name: members[name] for name in PAYLOAD_NAMES})
    # Canonical typed equality also rejects extra fields and bool/integer swaps.
    if json_bytes(actual_manifest) != json_bytes(expected_manifest):
        raise InputError("case_bundle_manifest_mismatch")
    if members["case-summary.md"] != render_case_summary(projection):
        raise InputError("case_bundle_summary_projection_mismatch")
    if members["README.txt"] != CASE_README_BYTES:
        raise InputError("case_bundle_readme_mismatch")
    return {
        "schema_version": INSPECTION_CONTRACT,
        "case_contract": CASE_CONTRACT,
        "case_reference": projection.case_reference,
        "demo_label": DEMO_LABEL,
        "bundle": {"bytes": len(raw_zip), "sha256": hashlib.sha256(raw_zip).hexdigest()},
        "internal_content_status": "content_consistent",
        "members": [{"name": name, "bytes": len(members[name]),
                     "sha256": hashlib.sha256(members[name]).hexdigest(),
                     "manifest_binding": "self_excluded" if name == "bundle-manifest.json"
                     else "content_consistent"} for name in ZIP_NAMES],
        "source_index_record_count": len(ledger["artifacts"]),
        "observation_count": len(ledger["observations"]),
        "stages": ledger["stages"],
        "blockers": ledger["blockers"],
        "workflow_facts": ledger["workflow_facts"],
        "source_relationships_rechecked": False,
        "original_sources_read": False,
        "source_files_embedded": False,
        "source_recheck_limit": SOURCE_RECHECK_LIMIT,
        "integrity_limit": INTEGRITY_LIMIT,
        "inspection_scope": "selected_zip_member_structure_and_internal_bytes_only",
        "demo_only": True,
        "execution_binding": "not_established",
        **{name: False for name in FALSE_FLAGS},
    }


def publish_inspection(raw_output: str, report: dict) -> None:
    """Publish one explicitly requested new JSON file without replacement."""
    path = explicit_relative_path(raw_output)
    if path.suffix.lower() != ".json":
        raise InputError("case_inspection_json_output_required")
    parent_info = check_existing_path(path.parent, directory=True)
    if os.path.lexists(path):
        raise InputError("case_inspection_output_must_be_new")
    raw = json_bytes(report)
    descriptor, stage_name = tempfile.mkstemp(prefix=".case-inspection-", suffix=".json",
                                             dir=path.parent)
    stage = Path(stage_name)
    stage_info = os.fstat(descriptor)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(raw)
            stream.flush()
            os.fsync(stream.fileno())
        _same_directory(path.parent, parent_info)
        current = check_existing_path(stage, directory=False)
        if (current.st_dev, current.st_ino) != (stage_info.st_dev, stage_info.st_ino):
            raise InputError("case_inspection_staging_identity_changed")
        os.link(stage, path, follow_symlinks=False)
    finally:
        try:
            _same_directory(path.parent, parent_info)
            current = check_existing_path(stage, directory=False)
            if (current.st_dev, current.st_ino) == (stage_info.st_dev, stage_info.st_ino):
                stage.unlink()
        except (OSError, InputError):
            pass


__all__ = ("inspect_case_bundle", "publish_inspection")
