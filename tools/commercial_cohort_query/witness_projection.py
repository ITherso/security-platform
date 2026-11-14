"""Source-bound complete reference witnesses for the immutable cohort query."""
from __future__ import annotations

from typing import TYPE_CHECKING

from cohort_contracts import fixed, validate_witnesses
from cohort_matcher import (
    ValidatedCohortQuery, _source_query_and_witnesses, read_cohort_query,
)

if TYPE_CHECKING:
    from phase38_adapter import ValidatedCoReferenceSource


def build_cohort_witnesses(validated_source: ValidatedCoReferenceSource,
                           validated_query: ValidatedCohortQuery) -> dict:
    """Reproduce the entire query from its actual source before disclosure."""
    query = read_cohort_query(validated_query)
    expected_query, witnesses = _source_query_and_witnesses(validated_source, query["request"])
    fixed(query, expected_query, "cohort_witness_actual_source_query")
    return validate_witnesses(witnesses)


__all__ = ("build_cohort_witnesses",)
