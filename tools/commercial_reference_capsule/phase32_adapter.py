"""Validate four explicit Phase32 wire files without observing original sources.

This assembly-only boundary deliberately imports the owning Phase32 contract,
renderer and manifest functions. The portable inspector does not import it.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from commercial_handoff.input_loader import explicit_relative_path
from commercial_reference_metadata.consumer_contracts import (
    InputError as Phase32InputError,
    json_bytes as phase32_json_bytes,
    parse_json as parse_phase32_json,
    validate_documents as validate_phase32_documents,
)
from commercial_reference_metadata.output_renderer import render_summary as render_phase32_summary
from commercial_reference_metadata.artifact_manifest import manifest_data as phase32_manifest_data

from capsule_contracts import InputError, make_source_bindings


_ROLES = ("response", "selection", "summary", "manifest")
_LIMITS = {
    "response": 512 * 1024,
    "selection": 512 * 1024,
    "summary": 128 * 1024,
    "manifest": 128 * 1024,
}


def _validated_models(response_bytes: bytes, selection_bytes: bytes,
                      summary_bytes: bytes, manifest_bytes: bytes) -> tuple[dict, dict, dict]:
    raw = {
        "response": response_bytes,
        "selection": selection_bytes,
        "summary": summary_bytes,
        "manifest": manifest_bytes,
    }
    for role, body in raw.items():
        if type(body) is not bytes or not 0 < len(body) <= _LIMITS[role]:
            raise InputError("capsule_phase32_snapshot_byte_type_or_limit_invalid")
    try:
        response = parse_phase32_json(response_bytes, maximum=_LIMITS["response"])
        selection = parse_phase32_json(selection_bytes, maximum=_LIMITS["selection"])
        # Full owning wire correspondence precedes any minimized projection.
        validate_phase32_documents(response, selection)
        if summary_bytes != render_phase32_summary(response, selection):
            raise InputError("capsule_phase32_summary_mismatch")
        manifest = parse_phase32_json(manifest_bytes, maximum=_LIMITS["manifest"])
        payloads = {
            "reference-metadata-response.json": response_bytes,
            "metadata-selection-ledger.json": selection_bytes,
            "metadata-summary.md": summary_bytes,
        }
        expected = phase32_manifest_data(response, selection, payloads)
        if (phase32_json_bytes(manifest, maximum=_LIMITS["manifest"])
                != phase32_json_bytes(expected, maximum=_LIMITS["manifest"])):
            raise InputError("capsule_phase32_manifest_mismatch")
    except Phase32InputError:
        # Raw models, paths and arbitrary source messages are not diagnostics.
        raise InputError("capsule_phase32_owning_contract_rejected") from None
    return response, selection, make_source_bindings(raw)


@dataclass(frozen=True, slots=True)
class ValidatedPhase32Snapshot:
    """Owner-validated immutable bytes; no caller-supplied approval marker."""

    response_bytes: bytes = field(repr=False)
    selection_bytes: bytes = field(repr=False)
    summary_bytes: bytes = field(repr=False)
    manifest_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_models(self.response_bytes, self.selection_bytes,
                          self.summary_bytes, self.manifest_bytes)


def read_validated_snapshot(snapshot: ValidatedPhase32Snapshot) -> tuple[dict, dict, dict]:
    """Revalidate exact-type bytes and return independent parsed models."""
    if type(snapshot) is not ValidatedPhase32Snapshot:
        raise InputError("capsule_exact_validated_phase32_snapshot_required")
    response, selection, bindings = _validated_models(
        snapshot.response_bytes, snapshot.selection_bytes,
        snapshot.summary_bytes, snapshot.manifest_bytes)
    return deepcopy(response), deepcopy(selection), deepcopy(bindings)


def load_validated_snapshot(paths: dict, budget) -> ValidatedPhase32Snapshot:
    """Read only the four CLI-selected Phase32 files under a shared budget."""
    if type(paths) is not dict or set(paths) != set(_ROLES):
        raise InputError("capsule_four_explicit_phase32_roles_required")
    raw = {}
    for role in _ROLES:
        raw[role] = budget.read(explicit_relative_path(paths[role]), _LIMITS[role])
    return ValidatedPhase32Snapshot(raw["response"], raw["selection"],
                                    raw["summary"], raw["manifest"])


__all__ = ("ValidatedPhase32Snapshot", "load_validated_snapshot", "read_validated_snapshot")
