"""Fixed metadata-only case ZIP and no-overwrite local publication."""
from __future__ import annotations

import hashlib
import io
import os
from pathlib import Path
import re
import tempfile
from types import MappingProxyType
import zipfile

from commercial_handoff.input_loader import check_existing_path
from commercial_handoff.manifest import _same_directory

from .case_contracts import (
    CASE_CONTRACT, DEMO_LABEL, FALSE_FLAGS, CaseProjection, InputError,
    json_bytes, projection_to_dict, source_index_dict,
)
from .safe_projection import CASE_README_BYTES, render_case_summary


BUNDLE_MANIFEST_CONTRACT = "termivar-offline-case-bundle-manifest/v1"
ASSEMBLY_MANIFEST_CONTRACT = "termivar-offline-case-assembly-manifest/v1"
INSPECTION_CONTRACT = "termivar-offline-case-inspection/v1"
ZIP_NAMES = (
    "case-ledger.json", "case-summary.md", "source-index.json",
    "bundle-manifest.json", "README.txt",
)
PAYLOAD_NAMES = (
    "case-ledger.json", "case-summary.md", "source-index.json", "README.txt",
)
MEMBER_LIMITS = MappingProxyType({
    "case-ledger.json": 256 * 1024, "case-summary.md": 128 * 1024,
    "source-index.json": 256 * 1024, "bundle-manifest.json": 64 * 1024,
    "README.txt": 8 * 1024,
})
MAX_ZIP_BYTES = 2 * 1024 * 1024
MAX_EXPANDED_BYTES = 1024 * 1024
MAX_COMPRESSION_RATIO = 100
FIXED_ZIP_TIME = (2026, 11, 11, 0, 0, 0)
REGULAR_FILE_ATTRIBUTES = 0o100644 << 16
OUTER_NAMES = ("termivar-demo-case.zip", "assembly-summary.md", "case-manifest.json")
INTEGRITY_LIMIT = (
    "Member hashes bind this package's selected bytes only. They are not a signature, "
    "producer identity, source authentication, execution proof or client delivery approval."
)
SOURCE_RECHECK_LIMIT = (
    "Original source artifacts are not embedded. Their recorded relationships cannot "
    "be independently rechecked from this case summary alone."
)


def _flags() -> dict:
    return {"demo_only": True, "execution_binding": "not_established",
            **{name: False for name in FALSE_FLAGS}}


def _digest(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise InputError("case_invalid_digest")
    return value


def _count(value: object, minimum: int, maximum: int) -> int:
    if type(value) is not int or not minimum <= value <= maximum:
        raise InputError("case_invalid_byte_count")
    return value


def manifest_metadata(case_reference: str, payloads: dict[str, bytes]) -> dict:
    """Return the closed manifest for four actual payloads; never self-hash."""
    if (type(case_reference) is not str or not case_reference
            or type(payloads) is not dict or set(payloads) != set(PAYLOAD_NAMES)):
        raise InputError("case_invalid_bundle_payload_inventory")
    for name in PAYLOAD_NAMES:
        value = payloads[name]
        if type(value) is not bytes or not 0 < len(value) <= MEMBER_LIMITS[name]:
            raise InputError("case_bundle_member_size_limit")
    return {
        "schema_version": BUNDLE_MANIFEST_CONTRACT,
        "case_contract": CASE_CONTRACT,
        "case_reference": case_reference,
        "demo_label": DEMO_LABEL,
        "files": [{"name": name, "bytes": len(payloads[name]),
                   "sha256": hashlib.sha256(payloads[name]).hexdigest()}
                  for name in PAYLOAD_NAMES],
        "members": list(ZIP_NAMES),
        "manifest_self_excluded": True,
        "source_files_embedded": False,
        "source_verification_scope": "assembly_time_selected_sources_only",
        "integrity_limit": INTEGRITY_LIMIT,
        "source_recheck_limit": SOURCE_RECHECK_LIMIT,
        **_flags(),
    }


def _zip_bytes(payloads: dict[str, bytes]) -> bytes:
    if type(payloads) is not dict or set(payloads) != set(ZIP_NAMES):
        raise InputError("case_invalid_zip_inventory")
    if sum(len(value) for value in payloads.values()) > MAX_EXPANDED_BYTES:
        raise InputError("case_zip_expanded_size_limit")
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_DEFLATED,
                         compresslevel=9, allowZip64=False) as archive:
        for name in ZIP_NAMES:
            value = payloads[name]
            if type(value) is not bytes or not 0 < len(value) <= MEMBER_LIMITS[name]:
                raise InputError("case_bundle_member_size_limit")
            info = zipfile.ZipInfo(name, date_time=FIXED_ZIP_TIME)
            info.create_system = 3
            info.create_version = 20
            info.extract_version = 20
            info.external_attr = REGULAR_FILE_ATTRIBUTES
            info.internal_attr = 0
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, value, compress_type=zipfile.ZIP_DEFLATED,
                             compresslevel=9)
        # Generated metadata must remain inside the independent reader's caps.
        for info in archive.infolist():
            if (info.compress_size <= 0
                    or info.file_size > info.compress_size * MAX_COMPRESSION_RATIO):
                raise InputError("case_zip_compression_ratio_limit")
    raw = buffer.getvalue()
    if not 0 < len(raw) <= MAX_ZIP_BYTES:
        raise InputError("case_zip_size_limit")
    return raw


def _publish(output: Path, payloads: dict[str, bytes]) -> None:
    """Publish fixed completed files in a new directory, outer manifest last.

    A failed run may leave a new partial directory or owned staging. This is
    neither whole-directory atomicity nor hostile filesystem-race acceptance.
    """
    if set(payloads) != set(OUTER_NAMES):
        raise InputError("case_invalid_output_inventory")
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".case-bundle-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name in OUTER_NAMES:
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(payloads[name])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in OUTER_NAMES:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        try:
            _same_directory(stage, stage_info)
            for name in OUTER_NAMES:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass


def write_case_bundle(output: Path, projection: CaseProjection,
                      case_map_sha256: str, case_map_byte_length: int) -> None:
    """Write only a bounded case projection, never the original source files."""
    ledger = projection_to_dict(projection)
    selected_map = {"sha256": _digest(case_map_sha256),
                    "byte_length": _count(case_map_byte_length, 1, 128 * 1024)}
    payloads = {
        "case-ledger.json": json_bytes(ledger),
        "case-summary.md": render_case_summary(projection),
        "source-index.json": json_bytes(source_index_dict(projection)),
        "README.txt": CASE_README_BYTES,
    }
    inner_manifest = manifest_metadata(projection.case_reference, payloads)
    members = {**payloads, "bundle-manifest.json": json_bytes(inner_manifest,
                                                            maximum=64 * 1024)}
    raw_zip = _zip_bytes(members)
    zip_digest = hashlib.sha256(raw_zip).hexdigest()
    assembly_summary = payloads["case-summary.md"] + (
        "\n## Vaka ZIP byte kimliği\n\n"
        "- Dosya: termivar-demo-case.zip\n"
        f"- Bayt: {len(raw_zip)}\n"
        f"- SHA256: {zip_digest}\n\n"
        "Bu içerik kimliği üretici, çalışma yetkisi veya müşteri onayı değildir.\n"
    ).encode("utf-8")
    if len(assembly_summary) > 128 * 1024:
        raise InputError("case_assembly_summary_size_limit")
    outer = {
        "schema_version": ASSEMBLY_MANIFEST_CONTRACT,
        "case_contract": CASE_CONTRACT,
        "case_reference": projection.case_reference,
        "demo_label": DEMO_LABEL,
        "case_map": selected_map,
        "zip": {"name": "termivar-demo-case.zip", "bytes": len(raw_zip),
                "sha256": zip_digest, "members": list(ZIP_NAMES)},
        "files": [{"name": "termivar-demo-case.zip", "bytes": len(raw_zip),
                   "sha256": zip_digest},
                  {"name": "assembly-summary.md", "bytes": len(assembly_summary),
                   "sha256": hashlib.sha256(assembly_summary).hexdigest()}],
        "output_files": list(OUTER_NAMES),
        "manifest_self_excluded": True,
        "source_artifact_count": len(projection.artifacts),
        "source_files_embedded": False,
        "source_recheck_limit": SOURCE_RECHECK_LIMIT,
        "integrity_limit": INTEGRITY_LIMIT,
        "completion_marker": "Published last. Compare the declared ZIP and summary bytes; this manifest is not authentication.",
        **_flags(),
    }
    _publish(output, {
        "termivar-demo-case.zip": raw_zip,
        "assembly-summary.md": assembly_summary,
        "case-manifest.json": json_bytes(outer, maximum=64 * 1024),
    })


__all__ = (
    "write_case_bundle", "manifest_metadata", "ZIP_NAMES", "PAYLOAD_NAMES",
    "MEMBER_LIMITS", "MAX_ZIP_BYTES", "MAX_EXPANDED_BYTES",
    "MAX_COMPRESSION_RATIO", "REGULAR_FILE_ATTRIBUTES", "BUNDLE_MANIFEST_CONTRACT",
    "ASSEMBLY_MANIFEST_CONTRACT", "INSPECTION_CONTRACT", "INTEGRITY_LIMIT",
    "SOURCE_RECHECK_LIMIT",
)
