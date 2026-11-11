"""Closed immutable proposal metadata; URLs are never opened or resolved.

The proposal is a new offline planning contract, not a native Termivar profile
or executable configuration. Native capability, scope and budget compatibility
are evaluated separately; this reader retains proposed values without repair.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from urllib.parse import urlsplit

from commercial_handoff.schema import InputError
from commercial_review.review_contracts import (
    check_json_budget,
    json_bytes,
    load_review_json,
)

from . import (
    DEMO_LABEL, MAX_PROPOSAL_BYTES, MAX_SAFE_INTEGER, PLAN_CONTRACT,
    PROPOSAL_CONTRACT, REVIEW_REQUIREMENTS,
)


PROPOSAL_FIELDS = frozenset((
    "schema_version", "mode", "proposal_id", "assessment_profile", "scope",
    "requested_capabilities", "budgets", "authorization_status",
    "data_handling_status", "review_requirements",
))
SCOPE_FIELDS = frozenset((
    "origin", "root_url", "requested_methods", "authenticated_context",
    "context_markers",
))
BUDGET_FIELDS = (
    "max_total_requests", "max_wall_time_ms", "max_subjects",
    "max_discovery_depth", "max_active_verifications", "max_response_body_bytes",
    "max_total_response_bytes",
)
PROFILES = frozenset(("baseline", "web-review"))
REQUESTED_METHODS = frozenset(("GET", "HEAD", "OPTIONS", "POST"))
AUTHENTICATED_CONTEXTS = frozenset(("not_provided", "placeholder_declared"))
MAX_CAPABILITIES = 32
MAX_CONTEXT_MARKERS = 16
MAX_URL_CHARACTERS = 2048


@dataclass(frozen=True, slots=True)
class ProposedScope:
    origin: str
    root_url: str
    requested_methods: tuple[str, ...]
    authenticated_context: str
    context_markers: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class ProposalBudgets:
    max_total_requests: int
    max_wall_time_ms: int
    max_subjects: int
    max_discovery_depth: int
    max_active_verifications: int
    max_response_body_bytes: int
    max_total_response_bytes: int


@dataclass(frozen=True, slots=True)
class ScopeProposal:
    schema_version: str
    mode: str
    proposal_id: str
    assessment_profile: str
    scope: ProposedScope
    requested_capabilities: tuple[str, ...]
    budgets: ProposalBudgets
    authorization_status: str
    data_handling_status: str
    review_requirements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class LoadedProposal:
    document: ScopeProposal
    sha256: str
    byte_length: int


def _fields(value: object, expected) -> dict:
    if type(value) is not dict or set(value) != set(expected):
        raise InputError("scope_invalid_fields")
    return value


def _literal(value: object, expected: str) -> str:
    if type(value) is not str or value != expected:
        raise InputError("scope_invalid_constant")
    return value


def _enum(value: object, allowed) -> str:
    if type(value) is not str or value not in allowed:
        raise InputError("scope_invalid_enum")
    return value


def _identifier(value: object, pattern: str) -> str:
    if type(value) is not str or re.fullmatch(pattern, value) is None:
        raise InputError("scope_invalid_identifier")
    return value


def _integer(value: object) -> int:
    # The JS-safe metadata range is not a native budget permission or ceiling.
    if type(value) is not int or not 0 <= value <= MAX_SAFE_INTEGER:
        raise InputError("scope_invalid_integer")
    return value


def _distinct_list(value: object, maximum: int, parser, minimum: int = 0) -> tuple:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise InputError("scope_invalid_array")
    result = tuple(parser(item) for item in value)
    if len(set(result)) != len(result):
        raise InputError("scope_duplicate_value")
    return result


def _demo_url(value: object, *, origin: bool) -> str:
    if (type(value) is not str or not 1 <= len(value) <= MAX_URL_CHARACTERS
            or not re.match(r"https?://", value)
            or any(ord(char) <= 32 or ord(char) >= 127 for char in value)
            or "\\" in value):
        raise InputError("scope_invalid_demo_url")
    try:
        parts = urlsplit(value)
        host = parts.hostname
        port = parts.port
        if (parts.scheme not in ("http", "https") or not parts.netloc
                or parts.username is not None or parts.password is not None
                or host is None or not host.endswith(".invalid")
                or len(host) > 253 or parts.netloc.endswith(":")
                or (port is not None and not 1 <= port <= 65535)):
            raise InputError("scope_invalid_demo_url")
        labels = host.split(".")
        if any(re.fullmatch(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?", label)
               is None for label in labels):
            raise InputError("scope_invalid_demo_url")
    except ValueError:
        raise InputError("scope_invalid_demo_url") from None
    if origin and (parts.path not in ("", "/") or "?" in value or "#" in value):
        raise InputError("scope_origin_root_required")
    # Cross-origin/root path/query/fragment compatibility is a preflight result.
    # Preserve the supplied string; do not drop context or normalize it to pass.
    return value


def validate_proposal(value: object) -> ScopeProposal:
    """Validate closed syntax and bounds without evaluating target authority."""
    check_json_budget(value, maximum=MAX_PROPOSAL_BYTES)
    row = _fields(value, PROPOSAL_FIELDS)
    scope = _fields(row["scope"], SCOPE_FIELDS)
    budgets = _fields(row["budgets"], BUDGET_FIELDS)
    checked_scope = ProposedScope(
        _demo_url(scope["origin"], origin=True),
        _demo_url(scope["root_url"], origin=False),
        _distinct_list(scope["requested_methods"], len(REQUESTED_METHODS),
                       lambda item: _enum(item, REQUESTED_METHODS), minimum=1),
        _enum(scope["authenticated_context"], AUTHENTICATED_CONTEXTS),
        _distinct_list(scope["context_markers"], MAX_CONTEXT_MARKERS,
                       lambda item: _identifier(item, r"[a-z][a-z0-9_:-]{0,63}")),
    )
    checked_budgets = ProposalBudgets(*(_integer(budgets[key]) for key in BUDGET_FIELDS))
    return ScopeProposal(
        _literal(row["schema_version"], PROPOSAL_CONTRACT),
        _literal(row["mode"], "demo"),
        _identifier(row["proposal_id"], r"[A-Za-z0-9][A-Za-z0-9_-]{0,63}"),
        _enum(row["assessment_profile"], PROFILES),
        checked_scope,
        _distinct_list(row["requested_capabilities"], MAX_CAPABILITIES,
                       lambda item: _identifier(item, r"[a-z][a-z0-9._:@-]{0,127}")),
        checked_budgets,
        _literal(row["authorization_status"], "not_provided"),
        _literal(row["data_handling_status"], "pending_decision"),
        _distinct_list(row["review_requirements"], len(REVIEW_REQUIREMENTS),
                       lambda item: _enum(item, REVIEW_REQUIREMENTS)),
    )


def load_proposal(raw_path: str) -> LoadedProposal:
    """Read one explicit local JSON file through the unchanged bounded reader."""
    loaded = load_review_json(raw_path, maximum=MAX_PROPOSAL_BYTES)
    return LoadedProposal(validate_proposal(loaded.data), loaded.sha256, loaded.byte_length)


def _proposal_dict(document: ScopeProposal) -> dict:
    if (type(document) is not ScopeProposal or type(document.scope) is not ProposedScope
            or type(document.budgets) is not ProposalBudgets):
        raise InputError("scope_invalid_document")
    return {
        "schema_version": document.schema_version,
        "mode": document.mode,
        "proposal_id": document.proposal_id,
        "assessment_profile": document.assessment_profile,
        "scope": {
            "origin": document.scope.origin,
            "root_url": document.scope.root_url,
            "requested_methods": list(document.scope.requested_methods),
            "authenticated_context": document.scope.authenticated_context,
            "context_markers": list(document.scope.context_markers),
        },
        "requested_capabilities": list(document.requested_capabilities),
        "budgets": {key: getattr(document.budgets, key) for key in BUDGET_FIELDS},
        "authorization_status": document.authorization_status,
        "data_handling_status": document.data_handling_status,
        "review_requirements": list(document.review_requirements),
    }


def proposal_to_dict(document: ScopeProposal) -> dict:
    """Serialize only the proposal allowlist, revalidating manually built DTOs."""
    return _proposal_dict(validate_proposal(_proposal_dict(document)))


__all__ = (
    "InputError", "DEMO_LABEL", "MAX_PROPOSAL_BYTES", "MAX_SAFE_INTEGER",
    "PROPOSAL_CONTRACT", "PLAN_CONTRACT", "REVIEW_REQUIREMENTS", "BUDGET_FIELDS",
    "ProposedScope", "ProposalBudgets", "ScopeProposal", "LoadedProposal",
    "load_proposal", "validate_proposal", "proposal_to_dict", "json_bytes",
)
