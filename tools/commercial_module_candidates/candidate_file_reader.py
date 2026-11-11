"""Hash only explicit candidate files, once per declared logical source path.

No source decoding, parsing, directory enumeration or module discovery occurs.
An observed candidate file never establishes Rust compiler resolution.
"""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import re
import stat

from commercial_handoff.input_loader import check_existing_path
from commercial_composition.composition_contracts import closed
from commercial_composition.source_inventory import _identity, _same_api_identity
from commercial_entrypoint_coverage.entrypoint_file_reader import source_root, _check_root
from .candidate_contracts import (
    InputError, MAX_CANDIDATE_BYTES, MAX_TOTAL_CANDIDATE_BYTES, MAX_CHUNK_BYTES,
    file_identifier, pin as validate_pin, validate_review_scope,
)


def _groups(review_scope: dict, pins: dict) -> dict:
    closed(pins, ("termivar", "platform"), "candidate_source_pins")
    for pin in pins.values():
        validate_pin(pin)
    review = validate_review_scope(review_scope, pins)
    for selection in review["selected_references"]:
        reference = selection["reference"]
        if re.fullmatch(r"rust-ref-[0-9a-f]{64}", reference["reference_id"]) is None:
            raise InputError("module_candidate_invalid_external_selection")
    groups = {}
    for allowed_row in review["allowed_candidate_files"]:
        key = (allowed_row["root_id"], allowed_row["pinned_commit"], allowed_row["path"])
        groups.setdefault(key, []).append(allowed_row)
    return groups


def _recheck_ancestors(root: Path, root_identity: tuple, ancestors: list) -> None:
    _check_root(root, root_identity)
    for directory, metadata in ancestors:
        try:
            now = check_existing_path(directory, directory=True)
        except FileNotFoundError:
            raise InputError("module_candidate_parent_disappeared") from None
        if _same_api_identity(now) != metadata:
            raise InputError("module_candidate_parent_identity_changed")


def _confirm_missing(path: Path, root: Path, root_identity: tuple, ancestors: list) -> None:
    _recheck_ancestors(root, root_identity, ancestors)
    try:
        path.lstat()
    except FileNotFoundError:
        _recheck_ancestors(root, root_identity, ancestors)
        return
    raise InputError("module_candidate_missing_path_changed")


def _inspect_explicit_path(root: Path, root_identity: tuple, relative: str) -> tuple[Path, object, list]:
    path = root.joinpath(*relative.split("/"))
    if os.path.commonpath((str(root), str(path))) != str(root):
        raise InputError("module_candidate_source_root_escape")
    _check_root(root, root_identity)
    root_info = check_existing_path(root, directory=True)
    ancestors = [(root, _same_api_identity(root_info))]
    cursor = root
    for part in relative.split("/")[:-1]:
        cursor = cursor / part
        try:
            info = check_existing_path(cursor, directory=True)
        except FileNotFoundError:
            _confirm_missing(cursor, root, root_identity, ancestors)
            return path, None, ancestors
        ancestors.append((cursor, _same_api_identity(info)))
    try:
        before = check_existing_path(path, directory=False)
    except FileNotFoundError:
        _confirm_missing(path, root, root_identity, ancestors)
        return path, None, ancestors
    _recheck_ancestors(root, root_identity, ancestors)
    return path, before, ancestors


def read_candidate_files(review_scope: dict, termivar_root: str, budget, pins: dict) -> list:
    """Read only allowlisted candidate identities; discard every content chunk."""
    groups = _groups(review_scope, pins)
    if not groups:
        return []
    root, root_identity = source_root(termivar_root)
    observations, consumed_total = [], 0
    for (root_id, pin, relative), entries in sorted(groups.items()):
        first = entries[0]
        base = {"file_id": file_identifier({"root_id": root_id, "pinned_commit": pin, "path": relative}),
                "root_id": root_id, "pinned_commit": pin, "path": relative,
                "candidate_ids": sorted(row["candidate_id"] for row in entries),
                "expected_sha256": first["expected_sha256"], "max_bytes": first["max_bytes"], "read_kind": first["read_kind"]}
        path, before, ancestors = _inspect_explicit_path(root, root_identity, relative)
        if before is None:
            observations.append({**base, "read_status": "declared_file_missing", "source_file_presence": "missing",
                                 "regular_file": None, "observed_byte_size": None, "observed_sha256": None})
            continue
        maximum = min(first["max_bytes"], MAX_CANDIDATE_BYTES, MAX_TOTAL_CANDIDATE_BYTES - consumed_total,
                      budget.maximum - budget.consumed)
        if not 0 <= before.st_size <= maximum or before.st_nlink != 1:
            raise InputError("module_candidate_size_or_hardlink_rejected")
        physical = (before.st_dev, before.st_ino)
        if physical in budget.identities:
            raise InputError("module_candidate_physical_alias_rejected")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        digest, consumed = hashlib.sha256(), 0
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or _identity(opened) != _identity(before)
                    or getattr(opened, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
                raise InputError("module_candidate_open_identity_changed")
            while True:
                chunk = stream.read(min(MAX_CHUNK_BYTES, maximum - consumed + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > maximum:
                    raise InputError("module_candidate_byte_budget_exceeded")
                digest.update(chunk)
            after_open = os.fstat(stream.fileno())
        after_path = check_existing_path(path, directory=False)
        _recheck_ancestors(root, root_identity, ancestors)
        if (consumed != before.st_size or _same_api_identity(opened) != _same_api_identity(after_open)
                or _same_api_identity(before) != _same_api_identity(after_path)):
            raise InputError("module_candidate_changed_during_hash_read")
        observed_hash = digest.hexdigest()
        if first["expected_sha256"] is not None and observed_hash != first["expected_sha256"]:
            raise InputError("module_candidate_expected_hash_mismatch")
        budget.identities.add(physical)
        budget.paths.append((path, _same_api_identity(before)))
        budget.consumed += consumed
        consumed_total += consumed
        observations.append({**base, "read_status": "present_and_hashed", "source_file_presence": "present",
                             "regular_file": True, "observed_byte_size": consumed, "observed_sha256": observed_hash})
    _check_root(root, root_identity)
    return observations


__all__ = ("read_candidate_files",)
