"""Closed immutable portfolio metadata; selected paths never enter outputs."""
from __future__ import annotations

from dataclasses import dataclass, field
import json
import re

from commercial_handoff.input_loader import (
    _depth_check, _integer, _pairs, _reject_number, _tree_budget,
    check_existing_path, explicit_relative_path,
)
from commercial_handoff.schema import InputError
from commercial_review.review_contracts import digest, enum_value, integer, literal, object_fields
from commercial_traceability.contracts import read_metadata
from commercial_case.case_contracts import (
    BLOCKER_CODES, CASE_CONTRACT, FALSE_FLAGS, STAGE_IDS, STAGE_STATUSES,
    WorkflowFacts, case_reference,
)


PORTFOLIO_MAP_CONTRACT = "termivar-offline-portfolio-map/v1"
PORTFOLIO_CONTRACT = "termivar-offline-portfolio/v1"
DEMO_LABEL = "DEMONSTRATION ONLY — OFFLINE CASE PORTFOLIO — NO CLIENT OR EXECUTION VERIFIED"
MAX_MAP_BYTES = 64 * 1024
MAX_PORTFOLIO_BYTES = 512 * 1024
MAX_JSON_BYTES = MAX_PORTFOLIO_BYTES
MAX_BUNDLES = 25
MAX_BUNDLE_BYTES = 2 * 1024 * 1024
MAX_TOTAL_BUNDLE_BYTES = 16 * 1024 * 1024
MAX_CASE_BUNDLES = MAX_BUNDLES
MAX_TOTAL_COMPRESSED_BYTES = MAX_TOTAL_BUNDLE_BYTES
MAX_SAFE_INTEGER = (1 << 53) - 1
TRUST_LIMITATIONS = (
    "selected_case_bundles_only_not_customer_or_assessment_inventory",
    "package_counts_are_not_real_customer_assessment_or_vulnerability_counts",
    "one_package_can_contribute_to_multiple_blocker_groups",
    "internal_content_consistency_is_not_producer_authentication",
    "original_source_artifacts_are_not_read_or_reverified",
    "case_reference_is_an_organization_label_not_a_run_identity",
    "portfolio_inclusion_does_not_raise_any_case_trust_level",
    "observation_counts_are_reported_metadata_not_verified_findings",
    "no_automatic_redaction_or_secret_detection_guarantee",
)
NOT_RUN = (
    "two_or_more_independent_cases", "same_reference_different_bundle_conflict",
    "duplicate_source_bundle", "malformed_duplicate_or_hostile_json",
    "modified_or_corrupt_case_zip", "zip_bomb_or_path_traversal",
    "wrong_manifest", "large_data_or_limit_scenarios", "symlink_reparse",
    "filesystem_race_permission_or_crash", "repeat_run_determinism",
    "real_customer_data", "real_producer_expert_or_organizational_authentication",
    "independent_browser_visual_acceptance", "automatic_tests_runner_or_coverage",
)


@dataclass(frozen=True, slots=True)
class BundleSelection:
    path: str
    display_label: str | None
    expected_contract: str
    expected_sha256: str | None


@dataclass(frozen=True, slots=True)
class DisplayPreferences:
    show_source_hashes: bool
    expand_case_details: bool


@dataclass(frozen=True, slots=True)
class PortfolioMap:
    portfolio_reference: str
    case_bundles: tuple[BundleSelection, ...]
    display_preferences: DisplayPreferences
    sha256: str
    byte_length: int
    schema_version: str = field(default=PORTFOLIO_MAP_CONTRACT, init=False)
    mode: str = field(default="demo", init=False)


@dataclass(frozen=True, slots=True)
class CaseStage:
    stage: str
    status: str


@dataclass(frozen=True, slots=True)
class PortfolioCase:
    case_reference: str
    case_contract: str
    bundle_sha256: str
    bundle_byte_length: int
    display_label: str | None
    internal_content_status: str
    source_index_record_count: int
    observation_count: int
    stages: tuple[CaseStage, ...]
    workflow_facts: WorkflowFacts
    blockers: tuple[str, ...]
    demo_only: bool = field(default=True, init=False)
    execution_binding: str = field(default="not_established", init=False)
    source_relationships_rechecked: bool = field(default=False, init=False)
    original_sources_read: bool = field(default=False, init=False)
    source_files_embedded: bool = field(default=False, init=False)
    plan_execution_verified: bool = field(default=False, init=False)
    scope_fulfillment_verified: bool = field(default=False, init=False)
    authorization_verified: bool = field(default=False, init=False)
    human_review_verified: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    release_authorized: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    production_ready: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class BlockerSummary:
    code: str
    case_bundle_count: int
    source_bundle_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class StageSummary:
    stage: str
    status: str
    case_bundle_count: int
    source_bundle_sha256s: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PortfolioIndex:
    portfolio_reference: str
    source_map_sha256: str
    source_map_byte_length: int
    display_preferences: DisplayPreferences
    cases: tuple[PortfolioCase, ...]
    blocker_summary: tuple[BlockerSummary, ...]
    stage_summary: tuple[StageSummary, ...]
    schema_version: str = field(default=PORTFOLIO_CONTRACT, init=False)
    mode: str = field(default="demo", init=False)
    demo_label: str = field(default=DEMO_LABEL, init=False)
    demo_only: bool = field(default=True, init=False)
    execution_binding: str = field(default="not_established", init=False)
    source_relationships_rechecked: bool = field(default=False, init=False)
    original_sources_read: bool = field(default=False, init=False)
    source_files_embedded: bool = field(default=False, init=False)
    plan_execution_verified: bool = field(default=False, init=False)
    scope_fulfillment_verified: bool = field(default=False, init=False)
    authorization_verified: bool = field(default=False, init=False)
    human_review_verified: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    release_authorized: bool = field(default=False, init=False)
    execution_authorized: bool = field(default=False, init=False)
    production_ready: bool = field(default=False, init=False)


_SOURCE_FLAGS = ("source_relationships_rechecked", "original_sources_read", "source_files_embedded")
_FACT_FIELDS = (
    "plan_precondition", "assessment_status", "observation_count", "unreviewed_count",
    "unknown_scope_count", "pending_inclusion_count", "overlay_decision_count",
    "reconciled_observation_count", "handoff_input_binding", "handoff_manifest_scope",
)
_CASE_FIELDS = (
    "case_reference", "case_contract", "bundle_sha256", "bundle_byte_length",
    "display_label", "internal_content_status", "source_index_record_count",
    "observation_count", "stages", "workflow_facts", "blockers", "demo_only",
    "execution_binding", *_SOURCE_FLAGS, *FALSE_FLAGS,
)


def _values(value: object) -> None:
    stack = [value]
    while stack:
        item = stack.pop()
        if type(item) is dict:
            if any(type(key) is not str for key in item):
                raise InputError("portfolio_invalid_json_key")
            stack.extend(item.values())
        elif type(item) is list:
            stack.extend(item)
        elif type(item) is int:
            if not -MAX_SAFE_INTEGER <= item <= MAX_SAFE_INTEGER:
                raise InputError("portfolio_integer_limit")
        elif item is not None and type(item) not in (str, bool):
            raise InputError("portfolio_invalid_json_value")


def json_bytes(value: object, maximum: int = MAX_JSON_BYTES) -> bytes:
    """Bounded integer-only UTF-8 JSON; supports the new 512KiB output ceiling."""
    integer(maximum, 1, MAX_JSON_BYTES)
    _tree_budget(value)
    _values(value)
    try:
        raw = (json.dumps(value, ensure_ascii=False, allow_nan=False,
                          sort_keys=True, indent=2) + "\n").encode("utf-8", "strict")
    except (TypeError, ValueError, UnicodeError, RecursionError):
        raise InputError("portfolio_invalid_json") from None
    if not 0 < len(raw) <= maximum:
        raise InputError("portfolio_json_size_limit")
    _depth_check(raw.decode("utf-8", "strict"))
    return raw


def parse_json_bytes(raw: bytes, maximum: int = MAX_JSON_BYTES) -> object:
    integer(maximum, 1, MAX_JSON_BYTES)
    if type(raw) is not bytes or not 0 < len(raw) <= maximum:
        raise InputError("portfolio_json_size_limit")
    try:
        text = raw.decode("utf-8", "strict")
    except UnicodeError:
        raise InputError("portfolio_invalid_utf8") from None
    if text.startswith("\ufeff"):
        raise InputError("portfolio_utf8_bom_not_supported")
    _depth_check(text)
    try:
        value = json.loads(text, object_pairs_hook=_pairs, parse_int=_integer,
                           parse_float=_reject_number, parse_constant=_reject_number)
    except (json.JSONDecodeError, RecursionError):
        raise InputError("portfolio_invalid_json") from None
    _tree_budget(value)
    _values(value)
    return value


def read_json_file(raw_path: str, maximum: int = MAX_JSON_BYTES):
    integer(maximum, 1, MAX_JSON_BYTES)
    loaded = read_metadata(raw_path, maximum)
    _values(loaded.data)
    return loaded


def _array(value: object, maximum: int, minimum: int = 0) -> list:
    if type(value) is not list or not minimum <= len(value) <= maximum:
        raise InputError("portfolio_invalid_array")
    return value


def _reference(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"DEMO-[A-Z0-9_-]{1,59}", value) is None:
        raise InputError("portfolio_invalid_demo_reference")
    return value


def _label(value: object) -> str | None:
    return None if value is None else _reference(value)


def _preferences(value: object) -> DisplayPreferences:
    row = object_fields(value, ("show_source_hashes", "expand_case_details"))
    if any(type(row[name]) is not bool for name in row):
        raise InputError("portfolio_invalid_display_preference")
    return DisplayPreferences(row["show_source_hashes"], row["expand_case_details"])


def _preference_dict(value: DisplayPreferences) -> dict:
    if type(value) is not DisplayPreferences:
        raise InputError("portfolio_invalid_display_preference")
    return {"show_source_hashes": value.show_source_hashes,
            "expand_case_details": value.expand_case_details}


def read_portfolio_map(raw_path: str) -> PortfolioMap:
    loaded = read_json_file(raw_path, MAX_MAP_BYTES)
    row = object_fields(loaded.data, ("schema_version", "mode", "portfolio_reference",
                                     "case_bundles", "display_preferences"))
    literal(row["schema_version"], PORTFOLIO_MAP_CONTRACT)
    literal(row["mode"], "demo")
    reference = _reference(row["portfolio_reference"])
    preferences = _preferences(row["display_preferences"])
    selections = []
    total = 0
    selected_paths = set()
    for item in _array(row["case_bundles"], MAX_BUNDLES, 1):
        item = object_fields(item, ("path", "display_label", "expected_contract", "expected_sha256"))
        path = explicit_relative_path(item["path"])
        checked = check_existing_path(path, directory=False)
        if path.suffix.lower() != ".zip" or not 0 < checked.st_size <= MAX_BUNDLE_BYTES:
            raise InputError("portfolio_invalid_bundle_size_or_type")
        normalized = str(path).casefold()
        if normalized in selected_paths:
            raise InputError("portfolio_duplicate_selected_path")
        selected_paths.add(normalized)
        total += checked.st_size
        if total > MAX_TOTAL_BUNDLE_BYTES:
            raise InputError("portfolio_total_source_size_limit")
        literal(item["expected_contract"], CASE_CONTRACT)
        if item["expected_sha256"] is not None:
            digest(item["expected_sha256"])
        selections.append(BundleSelection(item["path"], _label(item["display_label"]),
                                          CASE_CONTRACT, item["expected_sha256"]))
    return PortfolioMap(reference, tuple(selections), preferences, loaded.sha256, loaded.byte_length)


def _flags(row: dict) -> None:
    literal(row["demo_only"], True)
    literal(row["execution_binding"], "not_established")
    for name in (*FALSE_FLAGS, *_SOURCE_FLAGS):
        literal(row[name], False)


def _facts(value: object, observation_count: int) -> WorkflowFacts:
    row = object_fields(value, _FACT_FIELDS)
    enum_value(row["plan_precondition"], ("pending_authorization", "not_reported"))
    enum_value(row["assessment_status"], ("complete", "not_reported"))
    for name in _FACT_FIELDS[2:8]:
        integer(row[name], 0, 256)
    literal(row["overlay_decision_count"], 0)
    if any(row[name] != observation_count for name in (
            "observation_count", "unreviewed_count", "unknown_scope_count", "pending_inclusion_count")):
        raise InputError("portfolio_observation_state_count_mismatch")
    if row["reconciled_observation_count"] not in (0, observation_count):
        raise InputError("portfolio_reconciled_count_mismatch")
    enum_value(row["handoff_input_binding"], ("same_input_bytes_only", "not_established", "not_reported"))
    enum_value(row["handoff_manifest_scope"], ("selected_markdown_entries_only", "not_reported"))
    return WorkflowFacts(*(row[name] for name in _FACT_FIELDS))


def validate_portfolio_case(value: object) -> PortfolioCase:
    row = object_fields(value, _CASE_FIELDS)
    _flags(row)
    reference = case_reference(row["case_reference"])
    literal(row["case_contract"], CASE_CONTRACT)
    sha = digest(row["bundle_sha256"])
    size = integer(row["bundle_byte_length"], 1, MAX_BUNDLE_BYTES)
    label = _label(row["display_label"])
    literal(row["internal_content_status"], "content_consistent")
    literal(row["source_index_record_count"], 20)
    count = integer(row["observation_count"], 0, 256)
    stages = []
    for expected, item in zip(STAGE_IDS, _array(row["stages"], len(STAGE_IDS), len(STAGE_IDS))):
        item = object_fields(item, ("stage", "status"))
        literal(item["stage"], expected)
        stages.append(CaseStage(expected, enum_value(item["status"], STAGE_STATUSES)))
    facts = _facts(row["workflow_facts"], count)
    blockers = tuple(_array(row["blockers"], len(BLOCKER_CODES), len(BLOCKER_CODES)))
    if blockers != BLOCKER_CODES:
        raise InputError("portfolio_source_blockers_changed")
    return PortfolioCase(reference, CASE_CONTRACT, sha, size, label, "content_consistent",
                         20, count, tuple(stages), facts, blockers)


def _case_dict(case: PortfolioCase) -> dict:
    if type(case) is not PortfolioCase or type(case.workflow_facts) is not WorkflowFacts:
        raise InputError("portfolio_invalid_case_model")
    facts = case.workflow_facts
    return {
        "case_reference": case.case_reference, "case_contract": case.case_contract,
        "bundle_sha256": case.bundle_sha256, "bundle_byte_length": case.bundle_byte_length,
        "display_label": case.display_label, "internal_content_status": case.internal_content_status,
        "source_index_record_count": case.source_index_record_count,
        "observation_count": case.observation_count,
        "stages": [{"stage": row.stage, "status": row.status} for row in case.stages],
        "workflow_facts": {name: getattr(facts, name) for name in _FACT_FIELDS},
        "blockers": list(case.blockers), "demo_only": case.demo_only,
        "execution_binding": case.execution_binding,
        **{name: getattr(case, name) for name in (*FALSE_FLAGS, *_SOURCE_FLAGS)},
    }


def portfolio_case_to_dict(case: PortfolioCase) -> dict:
    value = _case_dict(case)
    if validate_portfolio_case(value) != case:
        raise InputError("portfolio_case_not_closed_immutable_model")
    return value


def _summary_sources(value: object) -> tuple[str, ...]:
    sources = tuple(digest(item) for item in _array(value, MAX_BUNDLES, 1))
    if len(set(sources)) != len(sources):
        raise InputError("portfolio_duplicate_summary_source")
    return sources


def _blocker_summary(value: object) -> BlockerSummary:
    row = object_fields(value, ("code", "case_bundle_count", "source_bundle_sha256s"))
    sources = _summary_sources(row["source_bundle_sha256s"])
    count = integer(row["case_bundle_count"], 1, MAX_BUNDLES)
    if count != len(sources):
        raise InputError("portfolio_summary_count_mismatch")
    return BlockerSummary(enum_value(row["code"], BLOCKER_CODES), count, sources)


def _stage_summary(value: object) -> StageSummary:
    row = object_fields(value, ("stage", "status", "case_bundle_count", "source_bundle_sha256s"))
    sources = _summary_sources(row["source_bundle_sha256s"])
    count = integer(row["case_bundle_count"], 1, MAX_BUNDLES)
    if count != len(sources):
        raise InputError("portfolio_summary_count_mismatch")
    return StageSummary(enum_value(row["stage"], STAGE_IDS),
                        enum_value(row["status"], STAGE_STATUSES), count, sources)


def validate_portfolio(value: object) -> PortfolioIndex:
    fields = ("schema_version", "mode", "portfolio_reference", "source_map",
              "display_preferences", "cases", "blocker_summary", "stage_summary",
              "totals", "demo_label", "demo_only", "execution_binding",
              "trust_limitations", "not_run", *_SOURCE_FLAGS, *FALSE_FLAGS)
    row = object_fields(value, fields)
    literal(row["schema_version"], PORTFOLIO_CONTRACT)
    literal(row["mode"], "demo")
    literal(row["demo_label"], DEMO_LABEL)
    _flags(row)
    reference = _reference(row["portfolio_reference"])
    source = object_fields(row["source_map"], ("sha256", "byte_length"))
    map_sha = digest(source["sha256"])
    map_size = integer(source["byte_length"], 1, MAX_MAP_BYTES)
    preferences = _preferences(row["display_preferences"])
    cases = tuple(validate_portfolio_case(item) for item in _array(row["cases"], MAX_BUNDLES, 1))
    digests = tuple(case.bundle_sha256 for case in cases)
    if len(set(digests)) != len(digests):
        raise InputError("portfolio_duplicate_source_bundle")
    references = tuple(case.case_reference for case in cases)
    if len(set(references)) != len(references):
        raise InputError("portfolio_case_reference_conflict")
    total_bytes = sum(case.bundle_byte_length for case in cases)
    if total_bytes > MAX_TOTAL_BUNDLE_BYTES:
        raise InputError("portfolio_total_source_size_limit")
    totals = object_fields(row["totals"], ("case_bundle_count", "total_source_zip_bytes", "cases_with_open_blockers"))
    for name, actual in (("case_bundle_count", len(cases)),
                         ("total_source_zip_bytes", total_bytes),
                         ("cases_with_open_blockers", sum(bool(case.blockers) for case in cases))):
        literal(totals[name], actual)
    blockers = tuple(_blocker_summary(item) for item in _array(row["blocker_summary"], len(BLOCKER_CODES)))
    stages = tuple(_stage_summary(item) for item in _array(row["stage_summary"], len(STAGE_IDS) * len(STAGE_STATUSES)))
    # Import only pure metadata grouping here, after model definitions exist.
    # The functions do not read bundles or run the previous phase's CLI.
    from .triage_projection import derive_blocker_summary, derive_stage_summary
    if blockers != derive_blocker_summary(cases) or stages != derive_stage_summary(cases):
        raise InputError("portfolio_derived_summary_mismatch")
    if (tuple(_array(row["trust_limitations"], len(TRUST_LIMITATIONS), len(TRUST_LIMITATIONS))) != TRUST_LIMITATIONS
            or tuple(_array(row["not_run"], len(NOT_RUN), len(NOT_RUN))) != NOT_RUN):
        raise InputError("portfolio_trust_limits_changed")
    return PortfolioIndex(reference, map_sha, map_size, preferences, cases, blockers, stages)


def portfolio_to_dict(index: PortfolioIndex) -> dict:
    if type(index) is not PortfolioIndex:
        raise InputError("portfolio_invalid_index_model")
    value = {
        "schema_version": index.schema_version, "mode": index.mode,
        "portfolio_reference": index.portfolio_reference,
        "source_map": {"sha256": index.source_map_sha256, "byte_length": index.source_map_byte_length},
        "display_preferences": _preference_dict(index.display_preferences),
        "cases": [portfolio_case_to_dict(case) for case in index.cases],
        "blocker_summary": [{"code": row.code, "case_bundle_count": row.case_bundle_count,
                            "source_bundle_sha256s": list(row.source_bundle_sha256s)}
                           for row in index.blocker_summary],
        "stage_summary": [{"stage": row.stage, "status": row.status,
                          "case_bundle_count": row.case_bundle_count,
                          "source_bundle_sha256s": list(row.source_bundle_sha256s)}
                         for row in index.stage_summary],
        "totals": {"case_bundle_count": len(index.cases),
                   "total_source_zip_bytes": sum(case.bundle_byte_length for case in index.cases),
                   "cases_with_open_blockers": sum(bool(case.blockers) for case in index.cases)},
        "demo_label": index.demo_label, "demo_only": index.demo_only,
        "execution_binding": index.execution_binding,
        "trust_limitations": list(TRUST_LIMITATIONS), "not_run": list(NOT_RUN),
        **{name: getattr(index, name) for name in (*FALSE_FLAGS, *_SOURCE_FLAGS)},
    }
    if validate_portfolio(value) != index:
        raise InputError("portfolio_index_not_closed_immutable_model")
    json_bytes(value)
    return value


__all__ = (
    "PORTFOLIO_MAP_CONTRACT", "PORTFOLIO_CONTRACT", "CASE_CONTRACT", "DEMO_LABEL",
    "MAX_MAP_BYTES", "MAX_PORTFOLIO_BYTES", "MAX_JSON_BYTES", "MAX_BUNDLES",
    "MAX_BUNDLE_BYTES", "MAX_TOTAL_BUNDLE_BYTES", "MAX_CASE_BUNDLES", "MAX_TOTAL_COMPRESSED_BYTES",
    "FALSE_FLAGS", "TRUST_LIMITATIONS", "NOT_RUN",
    "BundleSelection", "DisplayPreferences", "PortfolioMap", "CaseStage", "PortfolioCase",
    "BlockerSummary", "StageSummary", "PortfolioIndex", "WorkflowFacts", "InputError",
    "read_portfolio_map", "read_json_file", "json_bytes", "parse_json_bytes",
    "validate_portfolio_case", "portfolio_case_to_dict", "validate_portfolio", "portfolio_to_dict",
)
