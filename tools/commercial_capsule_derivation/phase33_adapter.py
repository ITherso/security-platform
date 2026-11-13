"""Narrow immutable adapter over the existing Phase33 capsule reader.

There is no second ZIP-security loop here. The public owner inspects each
explicit file; its existing bounded byte/member helpers recover the full
model from the same bytes rather than treating a lookup as a source capsule.
"""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
import hashlib

from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_composition.source_inventory import read_explicit_text, _same_api_identity
from capsule_contracts import (
    MAX_MEMBER_BYTES, MAX_ZIP_BYTES, build_lookup, fixed, parse_json,
    reference_ids, validate_capsule,
)
from capsule_manifest import PAYLOAD_NAMES, bundle_manifest
from capsule_renderer import README_BYTES, render_capsule_summary
from inspect_capsule import inspect_bundle, _read_bundle, _read_members

from derivation_contracts import InputError, MAX_TOTAL_INPUT_BYTES, validate_identity


class InputBudget:
    """Charge actual successful reads; reserve bounded ceilings before I/O.

    Each owner ZIP read reserves its 256 KiB-plus-sentinel ceiling. A failed
    read retains the whole reservation. Memory-only snapshot validation does
    not charge filesystem bytes. No private path/stat record is exported.
    """

    __slots__ = ("_consumed", "_maximum", "_paths")

    def __init__(self, maximum: int = MAX_TOTAL_INPUT_BYTES):
        if type(maximum) is not int or not 0 < maximum <= MAX_TOTAL_INPUT_BYTES:
            raise InputError("derivation_input_budget_invalid")
        self._consumed = 0
        self._maximum = maximum
        self._paths = {}

    @property
    def consumed(self) -> int:
        return self._consumed

    @property
    def maximum(self) -> int:
        return self._maximum

    def _reserve(self, maximum: int) -> int:
        if (type(maximum) is not int or maximum <= 0
                or self._consumed + maximum > self._maximum):
            raise InputError("derivation_total_input_budget_exceeded")
        self._consumed += maximum
        return maximum

    def _finish(self, reservation: int, actual: int) -> None:
        if type(actual) is not int or not 0 < actual <= reservation:
            raise InputError("derivation_actual_input_size_invalid")
        self._consumed -= reservation - actual

    def _remember(self, path, metadata: tuple) -> None:
        if path in self._paths and self._paths[path] != metadata:
            raise InputError("derivation_explicit_input_changed")
        self._paths[path] = metadata

    def read_text(self, raw_path: str, maximum: int) -> bytes:
        """Use the existing strict text/path reader and same-API stability."""
        if type(maximum) is not int or not 0 < maximum <= MAX_TOTAL_INPUT_BYTES:
            raise InputError("derivation_text_input_limit_invalid")
        remaining = self._maximum - self._consumed
        if remaining <= 1:
            raise InputError("derivation_total_input_budget_exceeded")
        limit = min(maximum, remaining - 1)
        reservation = self._reserve(limit + 1)
        path = explicit_relative_path(raw_path)
        raw, metadata = read_explicit_text(path, limit)
        self._finish(reservation, len(raw))
        self._remember(path, metadata)
        return raw

    def _track_zip(self, raw_path: str) -> None:
        path = explicit_relative_path(raw_path)
        self._remember(path, _same_api_identity(check_existing_path(path, directory=False)))

    def check_stability(self) -> None:
        for path, metadata in self._paths.items():
            current = check_existing_path(path, directory=False)
            if _same_api_identity(current) != metadata:
                raise InputError("derivation_input_changed_before_publication")


def _validated_memory(raw_bytes: bytes) -> tuple[dict, dict]:
    if type(raw_bytes) is not bytes or not 0 < len(raw_bytes) <= MAX_ZIP_BYTES:
        raise InputError("derivation_exact_immutable_capsule_bytes_required")
    # These are the unchanged owning security/parser/renderer functions. They
    # operate only on this in-memory capsule, not original sources or a path.
    members = _read_members(raw_bytes)
    capsule = validate_capsule(parse_json(members["reference-capsule.json"], maximum=MAX_MEMBER_BYTES))
    actual_manifest = parse_json(members["bundle-manifest.json"], maximum=MAX_MEMBER_BYTES)
    payloads = {name: members[name] for name in PAYLOAD_NAMES}
    fixed(actual_manifest, bundle_manifest(capsule, payloads), "derivation_source_inner_manifest")
    if members["reference-summary.md"] != render_capsule_summary(capsule):
        raise InputError("derivation_source_summary_mismatch")
    if members["README.txt"] != README_BYTES:
        raise InputError("derivation_source_readme_mismatch")
    identity = validate_identity({
        "bytes": len(raw_bytes),
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "capsule_reference": capsule["capsule_reference"],
    })
    return capsule, identity


@dataclass(frozen=True, slots=True)
class ValidatedSourceCapsule:
    """Immutable actual capsule bytes; no mutable model or approval token."""

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_memory(self.raw_bytes)


def read_validated_source(snapshot: ValidatedSourceCapsule) -> tuple[dict, dict]:
    """Revalidate exact-type immutable bytes and return independent models."""
    if type(snapshot) is not ValidatedSourceCapsule:
        raise InputError("derivation_exact_validated_source_capsule_required")
    capsule, identity = _validated_memory(snapshot.raw_bytes)
    return deepcopy(capsule), deepcopy(identity)


def load_validated_source(raw_path: str, selected_ids: list[str],
                          budget: InputBudget) -> ValidatedSourceCapsule:
    """Bind public owner inspection to a same-digest full-model reread."""
    if type(budget) is not InputBudget:
        raise InputError("derivation_exact_input_budget_required")
    selected_ids = list(reference_ids(selected_ids))
    budget._track_zip(raw_path)

    reservation = budget._reserve(MAX_ZIP_BYTES + 1)
    report, lookup = inspect_bundle(raw_path, selected_ids)
    budget._finish(reservation, report["bundle"]["bytes"])

    reservation = budget._reserve(MAX_ZIP_BYTES + 1)
    raw_bytes = _read_bundle(raw_path)
    budget._finish(reservation, len(raw_bytes))
    snapshot = ValidatedSourceCapsule(raw_bytes)
    capsule, identity = read_validated_source(snapshot)
    fixed(report["bundle"], {"bytes": identity["bytes"], "sha256": identity["sha256"]},
          "derivation_public_private_byte_binding")
    fixed(report["capsule_reference"], identity["capsule_reference"], "derivation_source_reference_binding")
    fixed(report["capsule_counts"], capsule["counts"], "derivation_source_count_binding")
    fixed(report["source_bindings"], capsule["source_bindings"], "derivation_source_descriptor_binding")
    fixed(lookup, build_lookup(capsule, selected_ids), "derivation_full_model_lookup_binding")
    budget.check_stability()
    return snapshot


__all__ = ("InputBudget", "ValidatedSourceCapsule", "read_validated_source", "load_validated_source")
