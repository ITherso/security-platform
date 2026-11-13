"""Portable four-member capsule inspection and explicit in-capsule lookup.

Only this file and the three local capsule wire/renderer/manifest modules are
required. No Phase31/32 module, original artifact or native source is imported
or opened by this inspection path. The capsule is never extracted to disk.
"""
from __future__ import annotations

import argparse
import hashlib
import io
import os
from pathlib import Path
import stat
import sys
import zipfile
import zlib

# Isolated Python omits the script directory. Add only this portable tool
# directory, never its tools/repository parent or a Phase31/32 import location.
sys.path.insert(0, str(Path(__file__).resolve().parent))

from capsule_contracts import (
    DEMO_LABEL, INSPECTION_SCHEMA, MAX_COMPRESSION_RATIO, MAX_EXPANDED_BYTES,
    MAX_MEMBER_BYTES, MAX_ZIP_BYTES, InputError, build_lookup, common,
    json_bytes, parse_json, validate_capsule,
)
from capsule_manifest import (
    PAYLOAD_NAMES, REGULAR_FILE_ATTRIBUTES, ZIP_NAMES, bundle_manifest,
    check_path, explicit_path, publish_inspection,
)
from capsule_renderer import README_BYTES, render_capsule_summary


def _identity(info) -> tuple:
    """Comparable lstat/fstat fields; ctime meanings may differ on Windows."""
    return (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns,
            info.st_nlink)


def _same_api_identity(info) -> tuple:
    """Retain ctime comparisons within each API family before/after reading."""
    return (*_identity(info), info.st_ctime_ns)


def _read_bundle(raw_path: str) -> bytes:
    path = explicit_path(raw_path)
    checked = check_path(path, directory=False)
    if (path.suffix.lower() != ".zip" or checked.st_nlink != 1
            or not 0 < checked.st_size <= MAX_ZIP_BYTES):
        raise InputError("capsule_zip_file_size_type_or_alias_rejected")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or _identity(opened) != _identity(checked)
                or getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("capsule_zip_opened_identity_changed")
        raw = stream.read(MAX_ZIP_BYTES + 1)
        after_open = os.fstat(stream.fileno())
    after_path = check_path(path, directory=False)
    if (not 0 < len(raw) <= MAX_ZIP_BYTES or len(raw) != checked.st_size
            or _same_api_identity(after_open) != _same_api_identity(opened)
            or _same_api_identity(after_path) != _same_api_identity(checked)):
        raise InputError("capsule_zip_changed_during_bounded_read")
    return raw


def _read_members(raw_zip: bytes) -> dict[str, bytes]:
    """Read four fixed, bounded regular-file members in memory only."""
    if type(raw_zip) is not bytes or not 0 < len(raw_zip) <= MAX_ZIP_BYTES:
        raise InputError("capsule_zip_byte_limit")
    try:
        with zipfile.ZipFile(io.BytesIO(raw_zip), "r", allowZip64=False) as archive:
            infos = archive.infolist()
            names = [info.filename for info in infos]
            if (archive.comment or len(infos) != len(ZIP_NAMES)
                    or len(set(names)) != len(names) or set(names) != set(ZIP_NAMES)):
                raise InputError("capsule_zip_member_inventory_mismatch")
            expanded = 0
            for info in infos:
                # Fixed ASCII flat names reject traversal, alternate spelling,
                # directories and unknown members before any member is opened.
                # orig_filename retains a NUL spelling that ZipInfo may trim.
                if (info.filename != info.orig_filename or info.is_dir()
                        or info.extra or info.comment or info.flag_bits & ~0x800
                        or info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED)
                        or info.create_system != 3
                        or info.external_attr != REGULAR_FILE_ATTRIBUTES
                        or stat.S_IFMT(info.external_attr >> 16) != stat.S_IFREG
                        or info.extract_version > 20
                        or not 0 < info.file_size <= MAX_MEMBER_BYTES
                        or not 0 < info.compress_size <= MAX_ZIP_BYTES
                        or info.file_size > info.compress_size * MAX_COMPRESSION_RATIO):
                    raise InputError("capsule_zip_unsupported_or_unsafe_member")
                expanded += info.file_size
                if expanded > MAX_EXPANDED_BYTES:
                    raise InputError("capsule_zip_expanded_size_limit")
            members = {}
            actual_expanded = 0
            for info in infos:
                with archive.open(info, "r") as stream:
                    body = stream.read(MAX_MEMBER_BYTES + 1)
                if not 0 < len(body) <= MAX_MEMBER_BYTES or len(body) != info.file_size:
                    raise InputError("capsule_zip_member_size_mismatch")
                actual_expanded += len(body)
                if actual_expanded > MAX_EXPANDED_BYTES:
                    raise InputError("capsule_zip_expanded_size_limit")
                members[info.filename] = body
    except InputError:
        raise
    except (zipfile.BadZipFile, zipfile.LargeZipFile, RuntimeError,
            NotImplementedError, EOFError, ValueError, UnicodeError, zlib.error):
        raise InputError("capsule_invalid_zip_content") from None
    return members


def inspect_bundle(raw_path: str, requested_ids: list[str]) -> tuple[dict, dict]:
    """Inspect internal content and return only explicit in-capsule lookups.

    SHA256, model correspondence and the source descriptors recorded inside the
    capsule are not signatures, independent source observations or authority.
    """
    raw_zip = _read_bundle(raw_path)
    members = _read_members(raw_zip)
    capsule = validate_capsule(parse_json(
        members["reference-capsule.json"], maximum=MAX_MEMBER_BYTES))
    actual_manifest = parse_json(members["bundle-manifest.json"], maximum=MAX_MEMBER_BYTES)
    payloads = {name: members[name] for name in PAYLOAD_NAMES}
    expected_manifest = bundle_manifest(capsule, payloads)
    # Canonical typed equality rejects extra keys, changed byte identities and
    # bool/integer substitutions without trusting an embedded approval marker.
    if json_bytes(actual_manifest) != json_bytes(expected_manifest):
        raise InputError("capsule_inner_manifest_mismatch")
    members["reference-summary.md"].decode("utf-8", "strict")
    members["README.txt"].decode("utf-8", "strict")
    if members["reference-summary.md"] != render_capsule_summary(capsule):
        raise InputError("capsule_summary_projection_mismatch")
    if members["README.txt"] != README_BYTES:
        raise InputError("capsule_readme_mismatch")
    # The public wire function bounds and validates explicit lookup IDs, rejects
    # duplicates/unknown IDs, and preserves withheld results with no projections.
    lookup = build_lookup(capsule, requested_ids)
    inspection = {
        **common(INSPECTION_SCHEMA, capsule["capsule_reference"], capsule["source_bindings"]),
        "bundle": {"bytes": len(raw_zip), "sha256": hashlib.sha256(raw_zip).hexdigest()},
        "internal_content_status": "content_consistent",
        "members": [
            {"name": name, "bytes": len(members[name]),
             "sha256": hashlib.sha256(members[name]).hexdigest(),
             "manifest_binding": "self_excluded" if name == "bundle-manifest.json"
             else "content_consistent"}
            for name in ZIP_NAMES
        ],
        "capsule_counts": dict(capsule["counts"]),
        "lookup_requested_reference_count": len(requested_ids),
        "original_phase32_files_read": False,
        "original_phase31_files_read": False,
        "old_guard_reexecuted": False,
        "old_source_archive_read": False,
        "native_candidate_files_read": False,
        "source_artifact_bytes_independently_verified": False,
        "source_producer_verified": False,
        "legal_review_performed": False,
        "inspection_scope": "four_capsule_members_and_internal_model_byte_correspondence_only",
        "integrity_limit": (
            "Internal capsule model, four-member ZIP, manifest, summary and README correspondence only. "
            "No original Phase31/32 artifact bytes, guard truth, live freshness, producer, compiler, "
            "ownership, human, legal or release verification."
        ),
    }
    return inspection, lookup


class Arguments(argparse.ArgumentParser):
    def error(self, message):
        self.exit(2, "reference_capsule_inspection: invalid_arguments\n")


def main(argv=None) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="strict")
    parser = Arguments(
        description="Portable capsule integrity and explicit lookup only; no original-source verification.",
        allow_abbrev=False,
    )
    parser.add_argument("--bundle", required=True)
    parser.add_argument("--lookup-reference", action="append", required=True)
    parser.add_argument("--inspection-output", required=True)
    parser.add_argument("--lookup-output", required=True)
    args = parser.parse_args(argv)
    try:
        inspection, lookup = inspect_bundle(args.bundle, args.lookup_reference)
        publish_inspection(args.inspection_output, args.lookup_output, inspection, lookup)
    except FileNotFoundError:
        print("reference_capsule_inspection: missing_required_input", file=sys.stderr)
        return 2
    except InputError:
        print("reference_capsule_inspection: content_or_output_rejected", file=sys.stderr)
        return 2
    except (OSError, UnicodeError, ValueError, RuntimeError, TypeError, KeyError,
            IndexError, RecursionError, StopIteration, EOFError):
        print("reference_capsule_inspection: rejected; no successful inspection is claimed", file=sys.stderr)
        return 1
    print("Created portable capsule inspection and explicit lookups; internal_content_status=content_consistent")
    print(DEMO_LABEL)
    print("original_phase32_files_read=false; upstream_guard_independently_verified=false; source_files_reobserved=false")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


__all__ = ("inspect_bundle",)
