"""Read only explicit bounded source files, returning temporary bytes and metadata."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import stat

from commercial_handoff.input_loader import check_existing_path
from commercial_composition.source_inventory import _identity, _same_api_identity
from commercial_entrypoint_coverage.entrypoint_file_reader import source_root, _check_root
from .source_graph_contracts import InputError


def read_sources(scope: dict, termivar_root: str, budget) -> tuple[dict, list]:
    root, root_identity = source_root(termivar_root)
    raw_by_id, observations = {}, []
    for selected in scope["allowed_source_files"]:
        if selected["root_id"] != "termivar" or selected["pinned_commit"] != scope["source_reference"]["source_commits"]["termivar"]:
            raise InputError("rust_source_root_or_pin_mismatch")
        path = root.joinpath(*selected["path"].split("/"))
        if os.path.commonpath((str(root), str(path))) != str(root):
            raise InputError("rust_source_root_escape")
        _check_root(root, root_identity)
        try:
            before = check_existing_path(path, directory=False)
        except FileNotFoundError:
            observations.append({**copy.deepcopy(selected), "read_status": "declared_file_missing",
                                 "source_file_presence": "missing", "regular_file": None,
                                 "observed_byte_size": None, "observed_sha256": None})
            continue
        maximum = min(selected["max_bytes"], 512 * 1024, budget.maximum - budget.consumed)
        if (not 0 <= before.st_size <= maximum or before.st_size != selected["expected_bytes"]
                or before.st_nlink != 1):
            raise InputError("rust_source_file_size_or_hardlink_rejected")
        physical = (before.st_dev, before.st_ino)
        if physical in budget.identities:
            raise InputError("rust_source_alias_rejected")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        digest, chunks, consumed = hashlib.sha256(), [], 0
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or _identity(opened) != _identity(before)
                    or getattr(opened, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
                raise InputError("rust_source_identity_changed")
            while True:
                chunk = stream.read(min(64 * 1024, maximum - consumed + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > maximum:
                    raise InputError("rust_source_byte_budget_exceeded")
                digest.update(chunk)
                chunks.append(chunk)
            after_open = os.fstat(stream.fileno())
        after_path = check_existing_path(path, directory=False)
        _check_root(root, root_identity)
        if (consumed != before.st_size or _same_api_identity(opened) != _same_api_identity(after_open)
                or _same_api_identity(before) != _same_api_identity(after_path)):
            raise InputError("rust_source_changed_during_read")
        observed_hash = digest.hexdigest()
        if observed_hash != selected["expected_sha256"]:
            raise InputError("rust_source_hash_mismatch")
        raw = b"".join(chunks)
        del chunks
        if raw.startswith(b"\xef\xbb\xbf"):
            raise InputError("rust_source_utf8_bom_not_supported")
        raw.decode("utf-8", "strict")
        budget.identities.add(physical)
        budget.paths.append((path, _same_api_identity(before)))
        budget.consumed += consumed
        raw_by_id[selected["source_file_reference"]] = raw
        observations.append({**copy.deepcopy(selected), "read_status": "present_and_hashed",
                             "source_file_presence": "present", "regular_file": True,
                             "observed_byte_size": consumed, "observed_sha256": observed_hash})
    _check_root(root, root_identity)
    return raw_by_id, observations
