"""Separate current byte observations from immutable Phase30 history.

This is a narrow new hash reader, not an adaptation of the old expected-hash
contract. It reuses unchanged path/identity guards, never the old file reader.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
import stat

from commercial_handoff.input_loader import check_existing_path
from commercial_composition.source_inventory import _identity, _same_api_identity
from commercial_entrypoint_coverage.entrypoint_file_reader import source_root, _check_root
from commercial_module_candidates.candidate_file_reader import _inspect_explicit_path, _recheck_ancestors
from .revalidation_contracts import (
    InputError, MAX_CANDIDATE_BYTES, MAX_TOTAL_CANDIDATE_BYTES, MAX_CHUNK_BYTES,
    current_identifier, validate_review_scope, validate_current_observations,
)


def read_observations(review: dict, baseline_evidence: dict, termivar_root: str, budget) -> list:
    """Hash only the explicitly selected subset of historical allowed files."""
    review = validate_review_scope(review, baseline_evidence)
    selected = sorted(review["selected_files"], key=lambda row: row["file_id"])
    if not selected:
        return []
    historical = {row["file_id"]: row for row in baseline_evidence["candidate_files"]}
    root, root_identity = source_root(termivar_root)
    observations, total = [], 0
    for selection in selected:
        old = historical[selection["file_id"]]
        base = {key: deepcopy(selection[key]) for key in (
            "file_id", "root_id", "pinned_commit", "path", "candidate_ids", "current_expected_sha256")}
        # The historical hash is only a comparison anchor. It is never used as
        # an observed current hash or replaced with the current measurement.
        base["baseline_sha256"] = old["observed_sha256"]
        base["physical_identity"] = "not_exported"
        path, before, ancestors = _inspect_explicit_path(root, root_identity, selection["path"])
        if before is None:
            if selection["current_expected_sha256"] is not None:
                raise InputError("revalidation_current_hash_expectation_unverified_for_absence")
            row = {**base, "read_status": "declared_file_missing", "source_file_presence": "missing",
                   "regular_file": None, "current_observed_byte_size": None, "current_observed_sha256": None,
                   "read_stability": "safe_absence_observed"}
            row["observation_id"] = current_identifier(row)
            observations.append(row)
            continue
        maximum = min(selection["max_bytes"], MAX_CANDIDATE_BYTES, MAX_TOTAL_CANDIDATE_BYTES - total,
                      budget.maximum - budget.consumed)
        if not 0 <= before.st_size <= maximum or before.st_nlink != 1:
            raise InputError("revalidation_current_file_size_or_hardlink_rejected")
        physical = (before.st_dev, before.st_ino)
        if physical in budget.identities:
            raise InputError("revalidation_current_physical_alias_rejected")
        flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
        descriptor = os.open(path, flags)
        digest, consumed = hashlib.sha256(), 0
        with os.fdopen(descriptor, "rb") as stream:
            opened = os.fstat(stream.fileno())
            if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                    or _identity(opened) != _identity(before)
                    or getattr(opened, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
                raise InputError("revalidation_current_open_identity_changed")
            while True:
                chunk = stream.read(min(MAX_CHUNK_BYTES, maximum - consumed + 1))
                if not chunk:
                    break
                consumed += len(chunk)
                if consumed > maximum:
                    raise InputError("revalidation_current_byte_budget_exceeded")
                digest.update(chunk)
            after_open = os.fstat(stream.fileno())
        after_path = check_existing_path(path, directory=False)
        _recheck_ancestors(root, root_identity, ancestors)
        if (consumed != before.st_size or _same_api_identity(opened) != _same_api_identity(after_open)
                or _same_api_identity(before) != _same_api_identity(after_path)):
            raise InputError("revalidation_current_file_changed_during_read")
        observed_hash = digest.hexdigest()
        current_expectation = selection["current_expected_sha256"]
        if current_expectation is not None and observed_hash != current_expectation:
            raise InputError("revalidation_current_expected_hash_mismatch")
        budget.identities.add(physical)
        budget.paths.append((path, _same_api_identity(before)))
        budget.consumed += consumed
        total += consumed
        row = {**base, "read_status": "present_and_hashed", "source_file_presence": "present", "regular_file": True,
               "current_observed_byte_size": consumed, "current_observed_sha256": observed_hash,
               "read_stability": "stable_bounded_read"}
        row["observation_id"] = current_identifier(row)
        observations.append(row)
    _check_root(root, root_identity)
    return validate_current_observations(observations, review, baseline_evidence)


__all__ = ("read_observations",)
