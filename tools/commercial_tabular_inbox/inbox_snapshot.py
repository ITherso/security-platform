"""Exact immutable typed inbox for pure local reference queries."""
from __future__ import annotations

from copy import deepcopy
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from inbox_contracts import InputError, MAX_INBOX_BYTES, json_bytes, parse_json, validate_inbox

if TYPE_CHECKING:
    from phase35_adapter import ValidatedTabularImport


def _validated_inbox(raw_bytes: bytes) -> dict:
    if type(raw_bytes) is not bytes:
        raise InputError("typed_inbox_exact_immutable_bytes_required")
    return validate_inbox(parse_json(raw_bytes, maximum=MAX_INBOX_BYTES))


@dataclass(frozen=True, slots=True)
class ValidatedInbox:
    """Closed typed JSON bytes; no mutable model cache or approval token."""

    raw_bytes: bytes = field(repr=False)

    def __post_init__(self) -> None:
        _validated_inbox(self.raw_bytes)


def read_typed_inbox(snapshot: ValidatedInbox) -> dict:
    if type(snapshot) is not ValidatedInbox:
        raise InputError("typed_inbox_exact_validated_snapshot_required")
    return deepcopy(_validated_inbox(snapshot.raw_bytes))


def build_typed_inbox(validated_tabular_import: ValidatedTabularImport) -> ValidatedInbox:
    """Build only after actual canonical CSV parsing and reconciliation."""
    from phase35_adapter import read_validated_import

    model = read_validated_import(validated_tabular_import)
    return ValidatedInbox(json_bytes(model, maximum=MAX_INBOX_BYTES))


__all__ = ("ValidatedInbox", "build_typed_inbox", "read_typed_inbox")
