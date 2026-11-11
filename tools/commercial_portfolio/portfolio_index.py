"""Build a closed portfolio index from a complete set of validated cases."""
from __future__ import annotations

from .portfolio_contracts import (
    MAX_CASE_BUNDLES, InputError, PortfolioCase, PortfolioIndex, PortfolioMap,
    portfolio_case_to_dict, portfolio_to_dict,
)
from .triage_projection import derive_blocker_summary, derive_stage_summary


def build_portfolio(portfolio_map: PortfolioMap,
                    cases: tuple[PortfolioCase, ...]) -> PortfolioIndex:
    """Preserve selection order and reject incomplete or ambiguous collections."""
    if (type(portfolio_map) is not PortfolioMap or type(cases) is not tuple
            or not 1 <= len(cases) <= MAX_CASE_BUNDLES
            or len(cases) != len(portfolio_map.case_bundles)):
        raise InputError("portfolio_incomplete_case_selection")
    for selection, case in zip(portfolio_map.case_bundles, cases):
        portfolio_case_to_dict(case)
        if (selection.expected_contract != case.case_contract
                or selection.display_label != case.display_label
                or (selection.expected_sha256 is not None
                    and selection.expected_sha256 != case.bundle_sha256)):
            raise InputError("portfolio_case_selection_binding_mismatch")
    index = PortfolioIndex(
        portfolio_reference=portfolio_map.portfolio_reference,
        source_map_sha256=portfolio_map.sha256,
        source_map_byte_length=portfolio_map.byte_length,
        display_preferences=portfolio_map.display_preferences,
        cases=cases,
        blocker_summary=derive_blocker_summary(cases),
        stage_summary=derive_stage_summary(cases),
    )
    # This serializer reparses the closed contract and recomputes summary rows.
    # It does not reopen the source map or any ZIP and grants no extra trust.
    portfolio_to_dict(index)
    return index


__all__ = ("build_portfolio",)
