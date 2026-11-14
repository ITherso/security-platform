"""Pure, unassigned analyst handoff with complete task-related packets."""
from __future__ import annotations

from followup_contracts import handoff_from_queue
from missing_evidence_queue import ValidatedFollowupQueue, read_followup_queue


def build_analyst_handoff(validated_queue: ValidatedFollowupQueue) -> dict:
    """Prepare the ledger only; no sending, assignment or task fulfillment."""
    return handoff_from_queue(read_followup_queue(validated_queue))


__all__ = ("build_analyst_handoff",)
