"""Reuse the protected Phase34 immutable capsule and bounded input adapter.

No ZIP parsing, approval marker or alternate snapshot implementation is added.
The owning reader validates only recorded capsule content, not original source
freshness, producer identity or the upstream guard's independent truth.
"""
from __future__ import annotations

from phase33_adapter import (
    InputBudget,
    ValidatedSourceCapsule,
    load_validated_source,
    read_validated_source,
)


ValidatedCapsule = ValidatedSourceCapsule


def load_capsule(raw_path: str, selected_ids: list[str],
                 budget: InputBudget) -> ValidatedCapsule:
    """Read the explicit capsule through its existing bounded owning path."""
    return load_validated_source(raw_path, selected_ids, budget)


def read_capsule(snapshot: ValidatedCapsule) -> tuple[dict, dict]:
    """Return the full validated model and its actual ZIP-byte identity."""
    return read_validated_source(snapshot)


__all__ = ("ValidatedCapsule", "InputBudget", "load_capsule", "read_capsule")
