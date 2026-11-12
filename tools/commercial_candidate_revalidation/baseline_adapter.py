"""Validate five explicit Phase30 payloads and hash their declared source ZIP.

Only metadata is retained. The ZIP is neither decoded nor parsed or extracted;
its byte identity is not archive-member or producer attestation.
"""
from __future__ import annotations

from copy import deepcopy
import hashlib
import os
from pathlib import Path
import stat

from commercial_handoff.input_loader import explicit_relative_path, check_existing_path
from commercial_composition.composition_contracts import closed, integer, sha256
from commercial_composition.source_inventory import _identity, _same_api_identity
from commercial_composition.artifact_manifest import identity
from commercial_module_candidates.candidate_contracts import validate_documents as validate_candidates
from commercial_module_candidates.output_renderer import render_summary as candidate_summary
from commercial_module_candidates.artifact_manifest import manifest_data as candidate_manifest
from commercial_module_candidates.candidate_file_reader import _inspect_explicit_path, _recheck_ancestors
from commercial_entrypoint_coverage.entrypoint_file_reader import source_root, _check_root
from .revalidation_contracts import (
    InputError, BASELINE_SCHEMAS, MAX_PACKAGE_BYTES, MAX_CHUNK_BYTES,
    MAX_MANIFEST_BYTES, MAX_SUMMARY_BYTES, MAX_JSON_BYTES,
    parse_json, json_bytes, validate_baseline_evidence,
)
_PAYLOADS = (
    ("evidence", "module-candidate-evidence.json"),
    ("triage", "candidate-triage.json"),
    ("coverage", "candidate-coverage.json"),
    ("summary", "candidate-summary.md"),
)


def _same(left: object, right: object, reason: str) -> None:
    if json_bytes(left) != json_bytes(right):
        raise InputError(reason)


def _package_identity(selected: dict, budget) -> dict:
    """Hash exactly one selected binary ZIP within the metadata read budget."""
    closed(selected, ("path", "bytes", "sha256"), "revalidation_source_package")
    if integer(selected["bytes"], "source_package_bytes", MAX_PACKAGE_BYTES) == 0:
        raise InputError("revalidation_empty_source_package")
    sha256(selected["sha256"], "source_package_sha256")
    requested = explicit_relative_path(selected["path"])
    if requested.suffix.lower() != ".zip":
        raise InputError("revalidation_source_package_must_be_zip")
    root, root_identity = source_root(str(Path.cwd()))
    relative = requested.relative_to(root).as_posix()
    path, before, ancestors = _inspect_explicit_path(root, root_identity, relative)
    if before is None:
        raise InputError("revalidation_required_source_package_missing")
    maximum = min(MAX_PACKAGE_BYTES, budget.maximum - budget.consumed)
    if not 0 < before.st_size <= maximum or before.st_size != selected["bytes"] or before.st_nlink != 1:
        raise InputError("revalidation_source_package_size_or_hardlink_rejected")
    physical = (before.st_dev, before.st_ino)
    if physical in budget.identities:
        raise InputError("revalidation_source_package_alias_rejected")
    flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
    descriptor = os.open(path, flags)
    digest, consumed = hashlib.sha256(), 0
    with os.fdopen(descriptor, "rb") as stream:
        opened = os.fstat(stream.fileno())
        if (not stat.S_ISREG(opened.st_mode) or opened.st_nlink != 1
                or _identity(opened) != _identity(before)
                or getattr(opened, "st_file_attributes", 0) & getattr(stat, "FILE_ATTRIBUTE_REPARSE_POINT", 0x400)):
            raise InputError("revalidation_source_package_open_identity_changed")
        while True:
            chunk = stream.read(min(MAX_CHUNK_BYTES, maximum - consumed + 1))
            if not chunk:
                break
            consumed += len(chunk)
            if consumed > maximum:
                raise InputError("revalidation_source_package_byte_budget_exceeded")
            digest.update(chunk)
        after_open = os.fstat(stream.fileno())
    after_path = check_existing_path(path, directory=False)
    _recheck_ancestors(root, root_identity, ancestors)
    if (consumed != before.st_size or _same_api_identity(opened) != _same_api_identity(after_open)
            or _same_api_identity(before) != _same_api_identity(after_path)):
        raise InputError("revalidation_source_package_changed_during_read")
    _check_root(root, root_identity)
    observed = {"bytes": consumed, "sha256": digest.hexdigest()}
    _same(observed, {key: selected[key] for key in ("bytes", "sha256")},
          "revalidation_source_package_hash_mismatch")
    budget.identities.add(physical)
    budget.paths.append((path, _same_api_identity(before)))
    budget.consumed += consumed
    return observed


def load_baseline(scope: dict, budget) -> tuple[dict, dict]:
    """Return independent closed baseline metadata after actual byte checks."""
    selected = closed(scope["baseline_sources"], BASELINE_SCHEMAS, "revalidation_baseline_sources")
    raw, documents, descriptors = {}, {}, {}
    for role, schema in BASELINE_SCHEMAS.items():
        row = closed(selected[role], ("path", "schema_version", "bytes", "sha256"), "revalidation_baseline_descriptor")
        maximum = MAX_MANIFEST_BYTES if role == "manifest" else MAX_SUMMARY_BYTES if role == "summary" else MAX_JSON_BYTES
        raw[role] = budget.read(explicit_relative_path(row["path"]), maximum)
        descriptors[role] = {"schema_version": schema, **identity(raw[role])}
        _same(descriptors[role], {key: row[key] for key in ("schema_version", "bytes", "sha256")},
              "revalidation_baseline_descriptor_mismatch")
        if role != "summary":
            documents[role] = parse_json(raw[role], maximum=maximum)
            if type(documents[role]) is not dict or documents[role].get("schema_version") != schema:
                raise InputError("revalidation_baseline_contract_unsupported")
    evidence, triage, coverage = (documents[key] for key in ("evidence", "triage", "coverage"))
    validate_candidates(evidence, triage, coverage)
    if raw["summary"] != candidate_summary(evidence, triage, coverage):
        raise InputError("revalidation_baseline_summary_mismatch")
    payloads = {name: raw[role] for role, name in _PAYLOADS}
    _same(documents["manifest"], candidate_manifest(evidence, triage, coverage, payloads),
          "revalidation_baseline_manifest_mismatch")
    _same(scope["source_reference"]["source_commits"], evidence["source_reference"]["source_commits"],
          "revalidation_baseline_source_pins_mismatch")
    _same(scope["source_reference"]["phase30_candidate_reference"], evidence["source_reference"]["candidate_reference"],
          "revalidation_baseline_candidate_reference_mismatch")
    package = _package_identity(scope["source_package"], budget)
    reference = {**deepcopy(scope["source_reference"]), "baseline_sources": descriptors, "source_package": package}
    validate_baseline_evidence(evidence, reference)
    return deepcopy(reference), deepcopy(evidence)


__all__ = ("load_baseline",)
