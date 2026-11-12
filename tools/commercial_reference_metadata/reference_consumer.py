"""Apply the existing whole-reference guard before disclosing narrow metadata.

Only the public creation API consumes an immutable upstream snapshot. Selection
correspondence remains a separate operation over the new minimized wire models.
"""
from __future__ import annotations

from typing import TYPE_CHECKING

from .consumer_contracts import (
    GLOBAL_LIMITATIONS, RESPONSE_SCHEMA, RESULT_LIMITATIONS, STATUS_FOR_DECISION,
    MAX_PROJECTIONS_PER_REFERENCE, build_selection_model, common, fail,
    response_counts, validate_request, validate_response,
)
from .disclosure_projection import project_metadata

if TYPE_CHECKING:
    from .revalidation_adapter import ValidatedSnapshot


def _index(rows: list[dict], key: str) -> dict:
    indexed = {}
    for row in rows:
        if row[key] in indexed:
            fail("duplicate_upstream_identity")
        indexed[row[key]] = row
    return indexed


def _group_candidates(rows: list[dict]) -> dict:
    grouped = {}
    for row in rows:
        grouped.setdefault(row["reference_id"], []).append(row["candidate_id"])
    return grouped


def _provided_projections(ledger: dict, impact: dict, source_candidates: dict,
                          candidates: dict, candidate_groups: dict,
                          source_candidate_groups: dict, files: dict,
                          currents: dict, comparisons: dict, get_projection) -> list[dict]:
    """Use the owning getter only after the full reference is permitted."""
    reference_id = impact["reference"]["reference_id"]
    candidate_ids = impact["candidate_ids"]
    if (not 1 <= len(candidate_ids) <= MAX_PROJECTIONS_PER_REFERENCE
            or candidate_ids != candidate_groups.get(reference_id, [])
            or candidate_ids != source_candidate_groups.get(reference_id, [])
            or candidate_ids != impact["reusable_candidate_ids"]
            or impact["blocked_candidate_ids"]
            or impact["changed_candidate_ids"]
            or impact["unknown_candidate_ids"]):
        fail("allowed_reference_candidate_set")

    result = []
    for candidate_id in candidate_ids:
        candidate = candidates[candidate_id]
        source_candidate = source_candidates[candidate_id]
        file_id = candidate["file_id"]
        if (candidate["reference_id"] != reference_id
                or source_candidate["reference_id"] != reference_id
                or source_candidate["file_id"] != file_id
                or candidate["baseline_allowlist_status"] != "allowlisted"
                or source_candidate["allowlist_status"] != "allowlisted"
                or candidate["reuse_allowed"] is not True
                or file_id is None
                or file_id not in files or file_id not in currents or file_id not in comparisons):
            fail("allowed_candidate_source_binding")
        file_decision = files[file_id]
        current = currents[file_id]
        comparison = comparisons[file_id]
        if (file_decision["reuse_allowed"] is not True
                or candidate_id not in file_decision["candidate_ids"]
                or reference_id not in file_decision["reference_ids"]
                or candidate_id not in current["candidate_ids"]
                or candidate_id not in comparison["candidate_ids"]
                or reference_id not in comparison["reference_ids"]
                or any(row["current_observation_id"] != current["observation_id"]
                       for row in (candidate, file_decision, comparison))
                or any(row["comparison_status"] != comparison["comparison_status"]
                       for row in (candidate, file_decision))):
            fail("allowed_candidate_observation_binding")

        # No recorded candidate projection is used as permission. The public
        # owning getter rederives its file decision from primary observations.
        projection = get_projection(ledger, file_id)
        if (projection is None or projection != candidate["projection"]
                or projection != file_decision["projection"]
                or projection["file_id"] != file_id
                or projection["current_observation_id"] != current["observation_id"]
                or candidate["reuse_status"] != projection["projection_kind"]
                or file_decision["reuse_status"] != projection["projection_kind"]
                or any(projection[key] != current[key] for key in
                       ("root_id", "pinned_commit", "path", "source_file_presence", "read_stability"))
                or projection["current_observed_byte_size"] != current["current_observed_byte_size"]
                or projection["current_observed_sha256"] != current["current_observed_sha256"]):
            fail("owning_projection_not_bound")
        result.append(project_metadata(reference_id, candidate_id, projection, comparison))
    return result


def create_reference_metadata_response(validated_snapshot: ValidatedSnapshot,
                                       request: dict) -> dict:
    """Return only requested, wholly permitted, recorded candidate metadata.

    There is no source I/O here and no independent freshness calculation.
    Hash binding and all requested IDs are checked before any getter call.
    """
    # Lazy imports keep selection-only consumers on the new closed wire layer.
    from .revalidation_adapter import read_validated_snapshot
    from commercial_candidate_revalidation.evidence_reuse_guard import get_reusable_projection

    request = validate_request(request)
    ledger, reuse, reference = read_validated_snapshot(validated_snapshot)
    for role in ("ledger", "reuse"):
        if request["expected_" + role + "_sha256"] != reference["upstream_sources"][role]["sha256"]:
            fail("request_source_digest")

    # The complete source was already owner-validated. Indexing supports exact
    # requested-ID checks; it does not disclose or claim observation of others.
    impacts = {}
    for impact in reuse["reference_impact"]:
        reference_id = impact["reference"]["reference_id"]
        if reference_id in impacts:
            fail("duplicate_upstream_reference")
        impacts[reference_id] = impact
    if any(reference_id not in impacts for reference_id in request["reference_ids"]):
        fail("unknown_requested_reference")
    if any(impacts[reference_id]["reference"]["reference_kind"] != "external_module_declaration"
           for reference_id in request["reference_ids"]):
        fail("requested_reference_kind")

    source_candidates = _index(ledger["baseline_evidence"]["candidates"], "candidate_id")
    candidates = _index(reuse["candidates"], "candidate_id")
    source_groups = _group_candidates(ledger["baseline_evidence"]["candidates"])
    groups = _group_candidates(reuse["candidates"])
    files = _index(reuse["files"], "file_id")
    currents = _index(ledger["current_observations"], "file_id")
    comparisons = _index(ledger["comparisons"], "file_id")
    results = []
    for reference_id in request["reference_ids"]:
        impact = impacts[reference_id]
        decision = impact["impact_status"]
        if decision not in STATUS_FOR_DECISION:
            fail("unknown_upstream_reference_decision")
        status = STATUS_FOR_DECISION[decision]
        if status == "provided_limited_metadata":
            projections = _provided_projections(
                ledger, impact, source_candidates, candidates, groups, source_groups,
                files, currents, comparisons, get_reusable_projection)
        elif status == "withheld_by_existing_guard":
            # A positive file decision cannot bypass a blocked candidate in
            # this reference. Do not even request any sub-file projection.
            if (not impact["candidate_ids"] or not impact["blocked_candidate_ids"]
                    or (decision == "candidate_change_observed" and not impact["changed_candidate_ids"])):
                fail("withheld_reference_decision_binding")
            projections = []
        else:
            if impact["candidate_ids"] or groups.get(reference_id) or source_groups.get(reference_id):
                fail("outside_scope_reference_binding")
            projections = []
        results.append({
            "reference_id": reference_id,
            "status": status,
            "upstream_reference_decision": decision,
            "projections": projections,
            "limitation_codes": list(RESULT_LIMITATIONS[status]),
        })

    response = {
        **common(RESPONSE_SCHEMA, reference),
        "request_id": request["request_id"],
        "results": results,
        "counts": response_counts(results),
        "limitations": list(GLOBAL_LIMITATIONS),
    }
    # This validates only the minimized output shape, counts, distinct candidate
    # identities and consistent same-file metadata. It does not replace the
    # owning validation and getter calls made above.
    return validate_response(response)


def build_selection(response: dict, request: dict) -> dict:
    """Derive new-wire correspondence only; never reopen upstream evidence."""
    return build_selection_model(response, request)


__all__ = ("create_reference_metadata_response", "build_selection")
