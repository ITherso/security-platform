"""Hash only exact allowlisted explicit target files; never retain source bodies."""
from __future__ import annotations

import copy
import hashlib
import os
from pathlib import Path
import stat

from commercial_handoff.input_loader import check_existing_path
from commercial_composition.source_inventory import _identity, _same_api_identity
from .coverage_contracts import InputError

CHUNK_BYTES = 64 * 1024
MAX_TARGET_BYTES = 512 * 1024
MAX_TARGET_TOTAL_BYTES = 1024 * 1024


def source_root(raw: str) -> tuple[Path, tuple]:
    root = Path(os.path.abspath(raw))
    info = check_existing_path(root, directory=True)
    return root, (info.st_dev, info.st_ino)


def _check_root(root: Path, identity: tuple) -> None:
    current = check_existing_path(root, directory=True)
    if (current.st_dev, current.st_ino) != identity:
        raise InputError("entrypoint_source_root_changed")


def read_entrypoint_files(scope: dict, targets: list, termivar_root: str, budget) -> list:
    """A manifest path alone never authorizes a read. No source decoding/parsing."""
    root, root_identity = source_root(termivar_root)
    target_by_id = {row["target_reference"]: row for row in targets}
    groups = {}
    for allowed in scope["allowed_entrypoint_files"]:
        target = target_by_id.get(allowed["target_reference"])
        if target is None or any(target[key] != allowed[key] for key in
                                 ("root_id", "pinned_commit", "manifest_reference")):
            raise InputError("entrypoint_allowlist_target_binding_rejected")
        if target["normalized_relative_path"] != allowed["path"]:
            raise InputError("entrypoint_allowlist_path_binding_rejected")
        key = (allowed["root_id"], allowed["pinned_commit"], allowed["path"])
        groups.setdefault(key, []).append(allowed)
    observations = []
    target_consumed = 0
    for (root_id, pin, relative), entries in sorted(groups.items()):
        if root_id != "termivar":
            raise InputError("entrypoint_unsupported_source_root")
        first = entries[0]
        binding = (first["source_file_reference"], first["expected_sha256"], first["max_bytes"], first["read_kind"])
        if any((row["source_file_reference"], row["expected_sha256"], row["max_bytes"], row["read_kind"]) != binding
               for row in entries):
            raise InputError("entrypoint_conflicting_allowlist_file_binding")
        path = root.joinpath(*relative.split("/"))
        if os.path.commonpath((str(root), str(path))) != str(root):
            raise InputError("entrypoint_source_root_escape")
        _check_root(root, root_identity)
        base = {"source_file_reference": first["source_file_reference"], "root_id": root_id,
                "pinned_commit": pin, "path": relative,
                "allowlist_entries": copy.deepcopy(entries)}
        try:
            before = check_existing_path(path, directory=False)
        except FileNotFoundError:
            observations.append({**base, "read_status": "declared_file_missing",
                                 "source_file_presence": "missing", "regular_file": None,
                                 "observed_byte_size": None, "observed_sha256": None})
            continue
        maximum = min(first["max_bytes"], MAX_TARGET_BYTES,
                      MAX_TARGET_TOTAL_BYTES - target_consumed, budget.maximum - budget.consumed)
        if not 0 <= before.st_size <= maximum or before.st_nlink != 1:
            raise InputError("entrypoint_file_size_or_hardlink_rejected")
        physical = (before.st_dev, before.st_ino)
        if physical in budget.identities:
            raise InputError("entrypoint_input_alias_rejected")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        digest, consumed = hashlib.sha256(), 0
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or _identity(before) != _identity(opened)
                    or getattr(opened, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
                raise InputError("entrypoint_source_identity_changed")
            while True:
                # The extra byte detects growth without accepting truncated data.
                chunk = stream.read(min(CHUNK_BYTES, maximum - consumed + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > maximum:
                    raise InputError("entrypoint_file_byte_budget_exceeded")
                digest.update(chunk)
            after_open = os.fstat(stream.fileno())
        after_path = check_existing_path(path, directory=False)
        _check_root(root, root_identity)
        if (consumed != before.st_size or _same_api_identity(opened) != _same_api_identity(after_open)
                or _same_api_identity(before) != _same_api_identity(after_path)):
            raise InputError("entrypoint_source_changed_during_read")
        observed_sha256 = digest.hexdigest()
        if first["expected_sha256"] is not None and observed_sha256 != first["expected_sha256"]:
            raise InputError("entrypoint_expected_hash_mismatch")
        budget.identities.add(physical)
        budget.paths.append((path, _same_api_identity(before)))
        budget.consumed += consumed
        target_consumed += consumed
        observations.append({**base, "read_status": "present_and_hashed", "source_file_presence": "present",
                             "regular_file": True, "observed_byte_size": consumed, "observed_sha256": observed_sha256})
    _check_root(root, root_identity)
    return observations
