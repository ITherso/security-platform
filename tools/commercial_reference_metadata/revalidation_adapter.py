"""Validate four explicit Phase31 metadata files into immutable byte snapshots.

This boundary never reads candidate files, source archives or older artefacts.
Owner validation establishes recorded metadata consistency, not current source
observations, physical identity, compiler resolution or producer authority.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field

from commercial_handoff.input_loader import explicit_relative_path
from commercial_candidate_revalidation.revalidation_contracts import (
    InputError as UpstreamInputError,
    parse_json as parse_upstream_json,
    json_bytes as upstream_json_bytes,
    validate_documents as validate_upstream_documents,
)
from commercial_candidate_revalidation.output_renderer import render_summary as render_upstream_summary
from commercial_candidate_revalidation.artifact_manifest import manifest_data as upstream_manifest_data
from .consumer_contracts import InputError, make_source_reference


_ROLES = ("ledger", "reuse", "summary", "manifest")
_UPSTREAM_LIMITS = {
    "ledger": 1024 * 1024,
    "reuse": 1024 * 1024,
    "summary": 256 * 1024,
    "manifest": 128 * 1024,
}


def _validated_models(ledger_bytes: bytes, reuse_bytes: bytes,
                      summary_bytes: bytes, manifest_bytes: bytes) -> tuple[dict, dict, dict]:
    raw = {"ledger": ledger_bytes, "reuse": reuse_bytes,
           "summary": summary_bytes, "manifest": manifest_bytes}
    for role, body in raw.items():
        # Reject mutable byte buffers and bytes subclasses before interpreting
        # any content. No marker supplied by a caller can replace validation.
        if type(body) is not bytes or not 0 < len(body) <= _UPSTREAM_LIMITS[role]:
            raise InputError("reference_metadata_snapshot_byte_type_or_limit_invalid")
    try:
        # Use the owning upstream parser and graph budgets. New minimized wire
        # limits must not be applied to the embedded historical baseline.
        ledger = parse_upstream_json(ledger_bytes, maximum=_UPSTREAM_LIMITS["ledger"])
        reuse = parse_upstream_json(reuse_bytes, maximum=_UPSTREAM_LIMITS["reuse"])
        validate_upstream_documents(ledger, reuse)
        if summary_bytes != render_upstream_summary(ledger, reuse):
            raise InputError("reference_metadata_upstream_summary_mismatch")
        manifest = parse_upstream_json(manifest_bytes, maximum=_UPSTREAM_LIMITS["manifest"])
        payloads = {"revalidation-ledger.json": ledger_bytes,
                    "evidence-reuse.json": reuse_bytes,
                    "revalidation-summary.md": summary_bytes}
        expected_manifest = upstream_manifest_data(ledger, reuse, payloads)
        if (upstream_json_bytes(manifest, maximum=_UPSTREAM_LIMITS["manifest"])
                != upstream_json_bytes(expected_manifest, maximum=_UPSTREAM_LIMITS["manifest"])):
            raise InputError("reference_metadata_upstream_manifest_mismatch")
    except UpstreamInputError:
        # Do not propagate raw models, source paths or caller text in errors.
        raise InputError("reference_metadata_upstream_contract_rejected") from None
    source_reference = make_source_reference(raw)
    return ledger, reuse, source_reference


@dataclass(frozen=True, slots=True)
class ValidatedSnapshot:
    """Four immutable byte strings, actually owner-validated on construction.

    This object contains no external approval flag and no mutable parsed-model
    cache. Public consumption validates its bytes again before returning data.
    """

    ledger_bytes: bytes = field(repr=False)
    reuse_bytes: bytes = field(repr=False)
    summary_bytes: bytes = field(repr=False)
    manifest_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_models(self.ledger_bytes, self.reuse_bytes, self.summary_bytes, self.manifest_bytes)


def read_validated_snapshot(snapshot: ValidatedSnapshot) -> tuple[dict, dict, dict]:
    """Revalidate exact-type immutable bytes and return independent models."""
    if type(snapshot) is not ValidatedSnapshot:
        raise InputError("reference_metadata_exact_validated_snapshot_required")
    ledger, reuse, reference = _validated_models(
        snapshot.ledger_bytes, snapshot.reuse_bytes, snapshot.summary_bytes, snapshot.manifest_bytes)
    return deepcopy(ledger), deepcopy(reuse), deepcopy(reference)


def load_validated_snapshot(paths: dict, budget) -> ValidatedSnapshot:
    """Read only the four explicit CLI inputs under the shared read budget."""
    if type(paths) is not dict or set(paths) != set(_ROLES):
        raise InputError("reference_metadata_explicit_upstream_roles_required")
    raw = {}
    for role in _ROLES:
        raw[role] = budget.read(explicit_relative_path(paths[role]), _UPSTREAM_LIMITS[role])
    return ValidatedSnapshot(raw["ledger"], raw["reuse"], raw["summary"], raw["manifest"])


__all__ = ("ValidatedSnapshot", "read_validated_snapshot", "load_validated_snapshot")
