"""Project public Phase22 inspection results; never implement another ZIP reader."""
from __future__ import annotations

from commercial_case.bundle_reader import inspect_case_bundle
from commercial_case.bundle_writer import INSPECTION_CONTRACT, MAX_ZIP_BYTES
from commercial_case.case_contracts import (
    CASE_CONTRACT, DEMO_LABEL as CASE_DEMO_LABEL, FALSE_FLAGS,
)
from commercial_handoff.input_loader import check_existing_path, explicit_relative_path
from commercial_review.review_contracts import (
    digest, integer, literal, object_fields,
)

from .portfolio_contracts import (
    MAX_CASE_BUNDLES, MAX_TOTAL_COMPRESSED_BYTES,
    BundleSelection, InputError, PortfolioCase, PortfolioMap,
    validate_portfolio_case,
)


_REPORT_FIELDS = frozenset((
    "schema_version", "case_contract", "case_reference", "demo_label", "bundle",
    "internal_content_status", "members", "source_index_record_count",
    "observation_count", "stages", "blockers", "workflow_facts",
    "source_relationships_rechecked", "original_sources_read", "source_files_embedded",
    "source_recheck_limit", "integrity_limit", "inspection_scope", "demo_only",
    "execution_binding", *FALSE_FLAGS,
))
_WORKFLOW_FIELDS = (
    "plan_precondition", "assessment_status", "observation_count", "unreviewed_count",
    "unknown_scope_count", "pending_inclusion_count", "overlay_decision_count",
    "reconciled_observation_count", "handoff_input_binding", "handoff_manifest_scope",
)


def _project_report(report: object, selection: BundleSelection) -> PortfolioCase:
    """Keep only a closed allowlist, dropping members and raw source details."""
    row = object_fields(report, _REPORT_FIELDS)
    literal(row["schema_version"], INSPECTION_CONTRACT)
    literal(row["case_contract"], CASE_CONTRACT)
    literal(row["demo_label"], CASE_DEMO_LABEL)
    literal(row["internal_content_status"], "content_consistent")
    literal(row["inspection_scope"], "selected_zip_member_structure_and_internal_bytes_only")
    literal(row["demo_only"], True)
    literal(row["execution_binding"], "not_established")
    for name in (*FALSE_FLAGS, "source_relationships_rechecked", "original_sources_read",
                 "source_files_embedded"):
        literal(row[name], False)
    source = object_fields(row["bundle"], ("sha256", "bytes"))
    digest(source["sha256"])
    integer(source["bytes"], 1, MAX_ZIP_BYTES)
    if selection.expected_sha256 is not None:
        digest(selection.expected_sha256)
        if source["sha256"] != selection.expected_sha256:
            raise InputError("portfolio_case_expected_digest_mismatch")
    facts = object_fields(row["workflow_facts"], _WORKFLOW_FIELDS)
    if type(row["stages"]) is not list or type(row["blockers"]) is not list:
        raise InputError("portfolio_invalid_case_inspection_metadata")
    stages = []
    for stage in row["stages"]:
        stage = object_fields(stage, ("stage", "status", "source_roles", "limitations"))
        stages.append({"stage": stage["stage"], "status": stage["status"]})
    # New DTO validation closes field types/enums/counts. The original report,
    # its source-index data, members and any local path are not retained.
    return validate_portfolio_case({
        "case_reference": row["case_reference"],
        "case_contract": row["case_contract"],
        "bundle_sha256": source["sha256"],
        "bundle_byte_length": source["bytes"],
        "display_label": selection.display_label,
        "internal_content_status": row["internal_content_status"],
        "source_index_record_count": row["source_index_record_count"],
        "observation_count": row["observation_count"],
        "stages": stages,
        "workflow_facts": {name: facts[name] for name in _WORKFLOW_FIELDS},
        "blockers": list(row["blockers"]),
        "demo_only": row["demo_only"],
        "execution_binding": row["execution_binding"],
        "source_relationships_rechecked": row["source_relationships_rechecked"],
        "original_sources_read": row["original_sources_read"],
        "source_files_embedded": row["source_files_embedded"],
        **{name: row[name] for name in FALSE_FLAGS},
    })


def load_case_bundles(portfolio_map: PortfolioMap) -> tuple[PortfolioCase, ...]:
    """Read only explicit selections, rejecting any invalid/duplicate/conflict.

    Each old reader call reserves its full 2MiB-plus-sentinel read ceiling
    before opening a file. Unused reservation is released after success and
    actual compressed bytes are charged. No partial successful index escapes.
    """
    if (type(portfolio_map) is not PortfolioMap
            or type(portfolio_map.case_bundles) is not tuple
            or not 1 <= len(portfolio_map.case_bundles) <= MAX_CASE_BUNDLES):
        raise InputError("portfolio_invalid_case_selection")
    consumed = 0
    paths_seen = set()
    digests_seen = set()
    references: dict[str, str] = {}
    cases = []
    for selection in portfolio_map.case_bundles:
        if type(selection) is not BundleSelection:
            raise InputError("portfolio_invalid_case_selection")
        literal(selection.expected_contract, CASE_CONTRACT)
        path = explicit_relative_path(selection.path)
        if path in paths_seen:
            raise InputError("portfolio_duplicate_source_zip")
        paths_seen.add(path)
        checked = check_existing_path(path, directory=False)
        if path.suffix.lower() != ".zip" or not 0 < checked.st_size <= MAX_ZIP_BYTES:
            raise InputError("portfolio_invalid_case_zip_size_or_type")
        reservation = MAX_ZIP_BYTES + 1
        if consumed + reservation > MAX_TOTAL_COMPRESSED_BYTES:
            raise InputError("portfolio_compressed_input_budget_exceeded")
        try:
            # Public domain validator supplies all Phase22 ZIP/ledger/index/
            # manifest/workflow checks. No CLI, subprocess or parser copy.
            report = inspect_case_bundle(selection.path)
        except InputError:
            raise
        except (OSError, UnicodeError, ValueError, RuntimeError):
            raise InputError("portfolio_case_bundle_unreadable") from None
        case = _project_report(report, selection)
        after = check_existing_path(path, directory=False)
        if (checked.st_dev, checked.st_ino, checked.st_size) != (
                after.st_dev, after.st_ino, after.st_size):
            raise InputError("portfolio_case_source_identity_changed")
        if case.bundle_byte_length != checked.st_size:
            raise InputError("portfolio_case_source_identity_changed")
        consumed += case.bundle_byte_length
        if consumed > MAX_TOTAL_COMPRESSED_BYTES:
            raise InputError("portfolio_compressed_input_budget_exceeded")
        if case.bundle_sha256 in digests_seen:
            raise InputError("portfolio_duplicate_source_zip")
        digests_seen.add(case.bundle_sha256)
        previous = references.get(case.case_reference)
        if previous is not None and previous != case.bundle_sha256:
            raise InputError("portfolio_case_reference_conflict")
        references[case.case_reference] = case.bundle_sha256
        cases.append(case)
    return tuple(cases)


__all__ = (
    "MAX_CASE_BUNDLES", "MAX_TOTAL_COMPRESSED_BYTES", "load_case_bundles",
)
