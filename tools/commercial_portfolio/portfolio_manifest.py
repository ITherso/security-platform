"""Fixed output inventory, actual byte manifests and no-overwrite publication."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import stat
import tempfile

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_handoff.manifest import _same_directory

from .portfolio_contracts import (
    DEMO_LABEL, FALSE_FLAGS, PORTFOLIO_CONTRACT, InputError, PortfolioIndex,
    json_bytes, portfolio_to_dict,
)
from .portfolio_renderer import render_html, render_markdown


MANIFEST_CONTRACT = "termivar-offline-portfolio-manifest/v1"
PAYLOAD_NAMES = ("portfolio-index.json", "portfolio-summary.md", "portfolio-overview.html")
MANIFEST_NAME = "portfolio-manifest.json"
PAYLOAD_LIMITS = {
    "portfolio-index.json": 512 * 1024,
    "portfolio-summary.md": 128 * 1024,
    "portfolio-overview.html": 512 * 1024,
}
INTEGRITY_LIMIT = (
    "Hashes bind generated portfolio payload bytes and declared case ZIP identities only. "
    "They authenticate neither producer, original sources, human review, authorization nor execution."
)


def manifest_data(index: PortfolioIndex, payloads: dict[str, bytes]) -> dict:
    portfolio_to_dict(index)
    if type(payloads) is not dict or set(payloads) != set(PAYLOAD_NAMES):
        raise InputError("portfolio_invalid_output_inventory")
    for name in PAYLOAD_NAMES:
        if type(payloads[name]) is not bytes or not 0 < len(payloads[name]) <= PAYLOAD_LIMITS[name]:
            raise InputError("portfolio_payload_size_limit")
    return {
        "schema_version": MANIFEST_CONTRACT,
        "portfolio_contract": PORTFOLIO_CONTRACT,
        "portfolio_reference": index.portfolio_reference,
        "demo_label": DEMO_LABEL,
        "source_map": {"sha256": index.source_map_sha256,
                       "byte_length": index.source_map_byte_length},
        "case_bundles": [{"sha256": case.bundle_sha256,
                          "byte_length": case.bundle_byte_length} for case in index.cases],
        "case_bundle_count": len(index.cases),
        "files": [{"name": name, "bytes": len(payloads[name]),
                   "sha256": hashlib.sha256(payloads[name]).hexdigest()} for name in PAYLOAD_NAMES],
        "output_files": [*PAYLOAD_NAMES, MANIFEST_NAME],
        "manifest_self_excluded": True,
        "source_relationships_rechecked": False,
        "original_sources_read": False,
        "source_case_bundles_embedded": False,
        "demo_only": True, "execution_binding": "not_established",
        **{name: False for name in FALSE_FLAGS},
        "integrity_limit": INTEGRITY_LIMIT,
        "completion_marker": "Published last. Compare the three explicit payloads; this manifest is not authentication or source revalidation.",
    }


def publish_portfolio(output: Path, index: PortfolioIndex) -> None:
    payloads = {
        "portfolio-index.json": json_bytes(portfolio_to_dict(index)),
        "portfolio-summary.md": render_markdown(index),
        "portfolio-overview.html": render_html(index),
    }
    manifest = manifest_data(index, payloads)
    documents = {**payloads, MANIFEST_NAME: json_bytes(manifest, maximum=64 * 1024)}
    names = (*PAYLOAD_NAMES, MANIFEST_NAME)
    parent_info = check_existing_path(output.parent, directory=True)
    if os.path.lexists(output):
        raise InputError("output_directory_must_be_new")
    stage = Path(tempfile.mkdtemp(prefix=".portfolio-stage-", dir=output.parent))
    stage_info = check_existing_path(stage, directory=True)
    try:
        for name in names:
            _same_directory(stage, stage_info)
            with (stage / name).open("xb") as stream:
                stream.write(documents[name])
                stream.flush()
                os.fsync(stream.fileno())
        _same_directory(output.parent, parent_info)
        output.mkdir(exist_ok=False)
        output_info = check_existing_path(output, directory=True)
        for name in names:
            _same_directory(output.parent, parent_info)
            _same_directory(output, output_info)
            _same_directory(stage, stage_info)
            os.link(stage / name, output / name, follow_symlinks=False)
    finally:
        try:
            _same_directory(stage, stage_info)
            for name in names:
                candidate = stage / name
                if os.path.lexists(candidate):
                    check_existing_path(candidate, directory=False)
                    candidate.unlink()
            stage.rmdir()
        except (OSError, InputError):
            pass


def read_selected_bytes(raw_path: str, maximum: int, suffix: str) -> bytes:
    """Read one explicitly supplied text payload; never follow a manifest path."""
    path = explicit_relative_path(raw_path)
    checked = check_existing_path(path, directory=False)
    if path.suffix.lower() != suffix or not 0 < checked.st_size <= maximum:
        raise InputError("portfolio_invalid_text_payload")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode)
                or (opened.st_dev, opened.st_ino) != (checked.st_dev, checked.st_ino)
                or getattr(opened, "st_file_attributes", 0)
                & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("portfolio_text_identity_changed")
        raw = stream.read(maximum + 1)
    if not 0 < len(raw) <= maximum or len(raw) != checked.st_size:
        raise InputError("portfolio_text_size_limit")
    raw.decode("utf-8", "strict")
    return raw


def validate_manifest(data: object, index: PortfolioIndex,
                      payloads: dict[str, bytes]) -> None:
    if json_bytes(data) != json_bytes(manifest_data(index, payloads)):
        raise InputError("portfolio_manifest_mismatch")
