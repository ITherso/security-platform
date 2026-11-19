"""Explicit import roots for the Phase44 reconciliation tools.

The Phase43 owner modules are imported as top-level modules, exactly as the
Phase43 commands do. This helper only lists those existing directories; it
does not scan the workspace or discover inputs.
"""
from __future__ import annotations

from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
TOOLS = HERE.parent
_OWNER_DIRS = (
    TOOLS, TOOLS / "commercial_reference_capsule", TOOLS / "commercial_capsule_derivation",
    TOOLS / "commercial_capsule_tabular", TOOLS / "commercial_tabular_inbox",
    TOOLS / "commercial_file_reference_index", TOOLS / "commercial_co_reference",
    TOOLS / "commercial_cohort_query", TOOLS / "commercial_evidence_followup",
    TOOLS / "commercial_response_slots", TOOLS / "commercial_deferred_intake",
    TOOLS / "commercial_task_exchange", HERE,
)


def install() -> None:
    """Put the fixed owner directories first; later entries win, as in Phase43."""
    for path in _OWNER_DIRS:
        text = str(path)
        while text in sys.path:
            sys.path.remove(text)
        sys.path.insert(0, text)


__all__ = ("install", "HERE", "TOOLS")
