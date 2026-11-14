"""Pure task-bound future response definitions; no submitted response values."""
from __future__ import annotations

from slot_contracts import template_from_slots
from response_slot_builder import ValidatedResponseSlots, read_response_slots


def build_response_template(validated_slots: ValidatedResponseSlots) -> dict:
    """Return an unsubmitted template without ingestion or task mutation."""
    return template_from_slots(read_response_slots(validated_slots))


__all__ = ("build_response_template",)
