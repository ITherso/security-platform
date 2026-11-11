"""Count exact reported blockers/states; no priority, score or task assignment."""
from __future__ import annotations

from commercial_case.case_contracts import BLOCKER_CODES, STAGE_IDS

from .portfolio_contracts import (
    MAX_CASE_BUNDLES, BlockerSummary, InputError, PortfolioCase, StageSummary,
    portfolio_case_to_dict,
)


def _closed_cases(cases: tuple[PortfolioCase, ...]) -> tuple[PortfolioCase, ...]:
    if type(cases) is not tuple or not 1 <= len(cases) <= MAX_CASE_BUNDLES:
        raise InputError("portfolio_invalid_case_inventory")
    digests = set()
    references = {}
    for case in cases:
        if type(case) is not PortfolioCase:
            raise InputError("portfolio_invalid_case_model")
        portfolio_case_to_dict(case)
        if case.bundle_sha256 in digests:
            raise InputError("portfolio_duplicate_source_zip")
        digests.add(case.bundle_sha256)
        if (case.case_reference in references
                and references[case.case_reference] != case.bundle_sha256):
            raise InputError("portfolio_case_reference_conflict")
        references[case.case_reference] = case.bundle_sha256
    return cases


def derive_blocker_summary(cases: tuple[PortfolioCase, ...]) -> tuple[BlockerSummary, ...]:
    """A package can belong to several groups; counts are not customer counts."""
    cases = _closed_cases(cases)
    result = []
    for code in BLOCKER_CODES:
        members = tuple(case.bundle_sha256 for case in cases if code in case.blockers)
        result.append(BlockerSummary(code=code, case_bundle_count=len(members),
                                     source_bundle_sha256s=members))
    return tuple(result)


def derive_stage_summary(cases: tuple[PortfolioCase, ...]) -> tuple[StageSummary, ...]:
    """Stable stage order, alphabetical reported status; neither is priority."""
    cases = _closed_cases(cases)
    result = []
    for name in STAGE_IDS:
        statuses = sorted({stage.status for case in cases for stage in case.stages
                           if stage.stage == name})
        for status in statuses:
            members = tuple(case.bundle_sha256 for case in cases
                            if any(stage.stage == name and stage.status == status
                                   for stage in case.stages))
            result.append(StageSummary(stage=name, status=status,
                case_bundle_count=len(members), source_bundle_sha256s=members))
    return tuple(result)


def build_triage(cases: tuple[PortfolioCase, ...]) -> tuple[tuple[BlockerSummary, ...], tuple[StageSummary, ...]]:
    return derive_blocker_summary(cases), derive_stage_summary(cases)


__all__ = ("derive_blocker_summary", "derive_stage_summary", "build_triage")
