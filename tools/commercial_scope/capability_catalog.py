"""Finite source-inspected planning metadata, never a detector or executor."""
from __future__ import annotations

import json
from types import MappingProxyType

from . import DEMO_LABEL
from .scope_contracts import InputError
from .source_manifest import (
    PINNED_COMMIT, SourceSnapshot, source_snapshot_to_dict, validate_snapshot,
)


CATALOG_CONTRACT = "termivar-assessment-capability-catalog/v1"
ROOT_AUTHORIZATION_CAPABILITY = "api.review.authorization-context.visibility-difference@1"
RESOURCE_AUTHORIZATION_CAPABILITY = "authorization.resource-cross-principal-equivalence@1"
OPENAPI_CAPABILITY = "api.openapi-contract-observed@1"
REST_CAPABILITY = "api.rest-readonly-surface-observed@1"
MAX_CATALOG_BYTES = 256 * 1024
EVIDENCE_CLASSES = (
    "source_declared", "implementation_inspected", "insufficient_source_evidence",
)
REQUIRED_CONTEXTS = (
    "feature_graphql_review", "opt_in_graphql_review",
    "feature_openapi_review", "opt_in_openapi_review",
    "feature_rest_review", "opt_in_rest_review", "same_run_openapi_catalogue",
    "feature_authorization_review", "opt_in_resource_authorization_review",
    "distinct_principal_contexts_declared", "resource_policy_declared",
    "opt_in_root_authorization_context", "root_context_declared",
)


def _budget(minimum: int, maximum: int, default: int, *source_refs: str):
    return MappingProxyType({"minimum": minimum, "maximum": maximum,
                             "default": default, "source_refs": source_refs})


# Rust API envelopes. They are not implemented CLI override flags, a native
# profile file, selected child allowances, or an estimate of probe costs.
BUDGET_LIMITS = MappingProxyType({
    "max_total_requests": _budget(0, 10000, 256, "termivar_web_assessment"),
    "max_wall_time_ms": _budget(0, 3600000, 300000, "termivar_web_assessment"),
    "max_subjects": _budget(1, 1024, 64, "termivar_web_assessment"),
    "max_discovery_depth": _budget(0, 16, 2, "termivar_web_assessment"),
    "max_active_verifications": _budget(0, 64, 10, "termivar_web_assessment"),
    "max_response_body_bytes": _budget(1, 16777216, 262144,
                                        "termivar_web_assessment", "termivar_http_policy"),
    "max_total_response_bytes": _budget(1, 268435456, 16777216,
                                         "termivar_web_assessment"),
})


def _evidence(snapshot: SourceSnapshot, source_id: str, first: int, last: int,
              evidence_class: str = "implementation_inspected") -> dict:
    source = next(item for item in snapshot.files if item.id == source_id)
    return {"evidence_class": evidence_class, "source_id": source.id,
            "path": source.path, "line_start": first, "line_end": last,
            "sha256": source.sha256, "byte_length": source.byte_length}


def _entry(snapshot: SourceSnapshot, capability_id: str, name: str, *,
           source_id: str, first: int, last: int,
           kind: str = "observation_only", namespace: str = "assessment_item",
           contexts: tuple[str, ...] = (), authenticated: bool = False,
           limitations: tuple[str, ...] = (), unsupported: tuple[str, ...] = (),
           supporting: tuple[tuple[str, int, int, str], ...] = ()) -> dict:
    unavailable = kind in ("metadata_only", "unsupported_stub")
    refs = [_evidence(snapshot, source_id, first, last)]
    refs.extend(_evidence(snapshot, item[0], item[1], item[2], item[3])
                for item in supporting)
    return {
        "capability_id": capability_id, "namespace": namespace, "kind": kind,
        "name": name,
        "assessment_profiles": [] if kind == "unsupported_stub" else ["web-review"],
        "evidence_class": "implementation_inspected",
        "planner_support": "unsupported" if unavailable else "supported_by_source",
        "requires_authenticated_context": authenticated,
        "native_scope": "not_applicable" if unavailable else "exact-origin",
        "budget_scope": ("not_applicable" if unavailable else
                         "shared_web_assessment_limits_not_per_capability_cost"),
        "required_contexts": list(contexts),
        "unsupported_conditions": list(unsupported),
        "source_evidence": refs,
        "limitations": list(limitations),
        # The CLI host/feature has lifecycle metadata; an item descriptor does
        # not independently declare that item's maturity or stability.
        "maturity": "unsupported" if kind == "unsupported_stub" else "not_separately_declared",
    }


def catalog_entries(snapshot: SourceSnapshot) -> tuple[dict, ...]:
    """Return all eleven selected rows; this is not full Termivar coverage."""
    validate_snapshot(snapshot)
    passive_limits = (
        "An eligible committed response is required; planning does not observe one.",
        "Informational observation only; absence is not exploit or impact proof.",
    )
    claim_ref = (("termivar_assessment_item", 1811, 1869, "implementation_inspected"),
                 ("termivar_reporting_contract", 156, 163, "source_declared"))
    return (
        _entry(snapshot, "web.passive.referrer-policy.missing@1",
               "Referrer-Policy was not observed", source_id="termivar_assessment_passive",
               first=226, last=235, limitations=passive_limits + (
                   "The native condition concerns an eligible HTML response, not every route.",),
               unsupported=("no_eligible_html_response",), supporting=claim_ref),
        _entry(snapshot, "web.passive.x-content-type-options.missing@1",
               "X-Content-Type-Options was not observed", source_id="termivar_assessment_passive",
               first=205, last=214, limitations=passive_limits + (
                   "The native condition concerns an eligible document response.",),
               unsupported=("no_eligible_document_response",), supporting=claim_ref),
        _entry(snapshot, "web.passive.permissions-policy.missing@1",
               "Permissions-Policy was not observed", source_id="termivar_assessment_passive",
               first=257, last=266, limitations=passive_limits + (
                   "The native condition concerns an eligible HTML response, not every route.",),
               unsupported=("no_eligible_html_response",), supporting=claim_ref),
        _entry(snapshot, "web.passive.csp.missing@1",
               "Content-Security-Policy was not observed", source_id="termivar_assessment_passive",
               first=164, last=173, limitations=passive_limits + (
                   "The native condition concerns an eligible HTML response, not browser exploitability.",),
               unsupported=("no_eligible_html_response",), supporting=claim_ref),
        _entry(snapshot, "graphql.anonymous-root-introspection@1",
               "Anonymous GraphQL schema-root introspection available",
               source_id="termivar_graphql_runtime", first=124, last=133,
               contexts=("feature_graphql_review", "opt_in_graphql_review"),
               limitations=("Anonymous bounded structure review; no mutation, authorization or availability claim.",
                            "The native child sends fixed anonymous JSON POSTs; composition is outside this planner's GET/HEAD-only method subset.",
                            "The executable root-introspection family differs from metadata-only catalog families.",
                            "Only correlated committed native results may produce this informational item."),
               unsupported=("mutation_or_authenticated_graphql_requested", "metadata_family_is_not_executable",
                            "anonymous_post_child_outside_planner_method_subset"),
               supporting=(("termivar_graphql_catalog", 592, 637, "implementation_inspected"),
                           ("termivar_cli_capabilities", 543, 553, "source_declared"),
                           ("termivar_request_broker", 2498, 2513, "implementation_inspected"),
                           ("termivar_cli_cargo", 57, 67, "implementation_inspected"))),
        _entry(snapshot, OPENAPI_CAPABILITY, "OpenAPI contract observed",
               source_id="termivar_openapi_runtime", first=49, last=108,
               contexts=("feature_openapi_review", "opt_in_openapi_review"),
               limitations=("One bounded anonymous document review; discovered operations are typed knowledge.",
                            "A discovered document never authorizes execution of its described operations.",
                            "An informational native item requires two committed, matching observations."),
               unsupported=("described_operations_treated_as_execution_authority",),
               supporting=(("termivar_cli_capabilities", 556, 566, "source_declared"),
                           ("termivar_cli_main", 174, 181, "implementation_inspected"))),
        _entry(snapshot, REST_CAPABILITY, "REST operation surface observed",
               source_id="termivar_rest_runtime", first=38, last=93,
               contexts=("feature_openapi_review", "feature_rest_review", "opt_in_openapi_review",
                         "opt_in_rest_review", "same_run_openapi_catalogue"),
               limitations=("One eligible anonymous bodyless GET from the same-run OpenAPI catalogue.",
                            "No generated required inputs, write operation, credential or vulnerability claim.",
                            "The native item requires two matching bounded JSON resource observations."),
               unsupported=("write_or_required_input_rest_operation", "no_same_run_openapi_catalogue"),
               supporting=(("termivar_cli_main", 217, 225, "implementation_inspected"),
                           ("termivar_cli_capabilities", 569, 583, "source_declared"))),
        _entry(snapshot, RESOURCE_AUTHORIZATION_CAPABILITY,
               "Unexpected cross-principal resource equivalence observed",
               source_id="termivar_resource_authorization_runtime", first=49, last=107,
               kind="differential_review", authenticated=True,
               contexts=("feature_authorization_review", "opt_in_resource_authorization_review",
                         "distinct_principal_contexts_declared", "resource_policy_declared"),
               limitations=("One exact-origin policy-declared JSON GET resource and two distinct declared principals.",
                            "Four ordered legs and one logical active verification; no identifier mutation or write.",
                            "A positive native relation is capped at NeedsReview/KnowledgeOnly, never confirmed bypass.",
                            "Demo context markers supply no credential, real identity, policy content or build proof."),
               unsupported=("combined_root_and_resource_authorization", "missing_distinct_principal_or_policy_context"),
               supporting=(("termivar_cli_main", 424, 434, "implementation_inspected"),
                           ("termivar_cli_capabilities", 586, 602, "source_declared"),
                           ("termivar_assessment_item", 1840, 1869, "implementation_inspected"))),
        _entry(snapshot, ROOT_AUTHORIZATION_CAPABILITY,
               "Authorization contexts returned different JSON visibility",
               source_id="termivar_root_api_visibility", first=1, last=52,
               kind="differential_review", authenticated=True,
               contexts=("opt_in_root_authorization_context", "root_context_declared"),
               limitations=("One explicit exact-root anonymous/authorized JSON comparison; difference may be intentional.",
                            "This is distinct from the gated four-leg resource authorization review.",
                            "A native difference requires human policy review, not a confirmed authorization claim.",
                            "Demo markers do not contain credentials or establish a real principal or authorized scope."),
               unsupported=("combined_root_and_resource_authorization", "non_root_authorization_context"),
               supporting=(("termivar_cli_main", 413, 434, "implementation_inspected"),
                           ("termivar_assessment_item", 925, 954, "implementation_inspected"))),
        _entry(snapshot, "graphql.get-query", "GetQuerySupport",
               source_id="termivar_graphql_catalog", first=592, last=637,
               namespace="graphql_catalog", kind="metadata_only",
               limitations=("This exact ID is a MetadataOnly GraphQL catalogue family, not an assessment-item ID.",
                            "Only the separate graphql.root-introspection family is executable in this catalogue.",
                            "Context markers cannot enable an unimplemented family."),
               unsupported=("metadata_only_catalogue_family",)),
        _entry(snapshot, "command.api", "HTTP API adapter",
               source_id="termivar_cli_capabilities", first=870, last=880,
               namespace="cli_surface", kind="unsupported_stub",
               limitations=("The feature-gated CLI surface reports a typed nonzero unsupported error; no listener exists.",
                            "Assessing an API target does not imply a working HTTP scan API service."),
               unsupported=("unsupported_cli_surface_stub",)),
    )


def build_catalog(snapshot: SourceSnapshot) -> dict:
    validate_snapshot(snapshot)
    budget_evidence = {
        "max_total_requests": (340, 343, 564, 573),
        "max_wall_time_ms": (352, 355, 605, 615),
        "max_subjects": (309, 311, 466, 472),
        "max_discovery_depth": (312, 315, 475, 483),
        "max_active_verifications": (356, 362, 618, 629),
        "max_response_body_bytes": (344, 347, 575, 583),
        "max_total_response_bytes": (348, 351, 586, 603),
    }
    budgets = {}
    for name, limit in BUDGET_LIMITS.items():
        lines = budget_evidence[name]
        refs = [_evidence(snapshot, "termivar_web_assessment", lines[0], lines[1]),
                _evidence(snapshot, "termivar_web_assessment", lines[2], lines[3])]
        if name == "max_response_body_bytes":
            refs.append(_evidence(snapshot, "termivar_http_policy", 9, 13))
        budgets[name] = {"minimum": limit["minimum"], "maximum": limit["maximum"],
                         "default": limit["default"], "source_refs": list(limit["source_refs"]),
                         "source_evidence": refs}
    return {
        "schema_version": CATALOG_CONTRACT, "source_commit": PINNED_COMMIT,
        "native_source": source_snapshot_to_dict(snapshot),
        "evidence_classes": list(EVIDENCE_CLASSES),
        "evidence_class_meaning": {
            "source_declared": "A pinned source contract declares the behavior; no runtime proof.",
            "implementation_inspected": "Related pinned implementation was statically inspected; no runtime proof.",
            "insufficient_source_evidence": "This finite review does not establish support; unknown requests remain unresolved.",
        },
        "entries": list(catalog_entries(snapshot)), "budget_limits": budgets,
        "profile_support": [
            {"profile": "web-review", "native_scope": "exact-origin", "planner_supported": True,
             "evidence_class": "implementation_inspected",
             "source_evidence": [_evidence(snapshot, "termivar_scan_profile", 500, 508)]},
            {"profile": "baseline", "native_scope": "single-resource", "planner_supported": False,
             "reason": "Defined by native source but outside this planner's supported subset; not native-unsupported.",
             "evidence_class": "source_declared",
             "source_evidence": [_evidence(snapshot, "termivar_scan_profile", 450, 498, "source_declared")]},
        ],
        "required_context_markers": list(REQUIRED_CONTEXTS),
        "budget_semantics": "Checked Rust WebAssessmentLimits envelopes, not CLI override flags or a native executable profile.",
        "budget_limitations": [
            "Zero request or wall-time allowance denies dispatch/execution; it is not successful coverage.",
            "Zero active allowance denies active requests, not every passive operation.",
            "Optional native child active allowances may be added when the default ceiling is selected; ten is not a universal combined-feature cap.",
            "This planner does not reproduce native child accounting or infer per-capability request costs.",
            "Body retention differs from wire-byte accounting; a final delivered chunk may overrun the remaining response budget.",
            "Provider/IdP budgets and the complete native profile's other dimensions are not composed by these seven checks.",
            "Matching a Rust envelope does not establish a CLI budget override, sufficient work allowance, completion or coverage.",
        ],
        "budget_limit_evidence": [
            _evidence(snapshot, "termivar_web_assessment", 2929, 3031),
            _evidence(snapshot, "termivar_request_broker", 2338, 2377),
            _evidence(snapshot, "termivar_scan_profile", 646, 653),
        ],
        "limitations": [
            "Eleven selected rows are not an exhaustive Termivar capability inventory.",
            "Assessment item IDs, GraphQL catalogue family IDs and CLI surface keys use separate namespaces.",
            "Source declarations, static implementation review and self-reported build features are not runtime acceptance or producer authenticity.",
            "All context markers are local declarations; no build, opt-in, session, credential, identity or same-run artifact is independently verified.",
            "Eligible response types and native committed-evidence predicates cannot be evaluated from a scope proposal.",
            "No native assessment capability currently produces Confirmed; KnowledgeOnly is runtime authority, not a wire disposition.",
            "Unlisted capabilities retain insufficient_source_evidence; no implicit supported fallback or full-coverage claim.",
            "Source byte identity and Git HEAD do not establish the authenticity of source, executable or legal authorization.",
        ],
        "source_claim_evidence": [
            _evidence(snapshot, "termivar_cli_capabilities", 1, 19, "source_declared"),
            _evidence(snapshot, "termivar_reporting_contract", 150, 163, "source_declared"),
            _evidence(snapshot, "termivar_assessment_item", 104, 127),
        ],
        "scope_source_evidence": [
            _evidence(snapshot, "termivar_http_policy", 42, 92),
            _evidence(snapshot, "termivar_discovery", 45, 68),
            _evidence(snapshot, "termivar_web_assessment", 757, 795),
            _evidence(snapshot, "termivar_web_assessment", 3150, 3160),
            _evidence(snapshot, "termivar_cli_main", 677, 735),
            _evidence(snapshot, "termivar_cli_main", 615, 631),
            _evidence(snapshot, "termivar_cli_main", 1991, 2002),
        ],
        "related_cli_surface_declarations": [
            {"key": key, "maturity": maturity, "implementation_status": status,
             "source_evidence": [_evidence(snapshot, "termivar_cli_capabilities", first, last,
                                           "source_declared")]}
            for key, first, last, maturity, status in (
                ("profile.web-review", 391, 401, "preview", "implemented"),
                ("option.graphql-review", 543, 553, "preview", "implemented"),
                ("option.openapi-review", 556, 566, "preview", "implemented"),
                ("option.rest-review", 569, 583, "preview", "implemented"),
                ("option.resource-authorization-review", 586, 602, "preview", "implemented"),
                ("command.api", 870, 880, "unsupported", "unsupported_stub"),
            )
        ],
        "demo_label": DEMO_LABEL, "demo_only": True,
        "execution_authorized": False, "authorization_verified": False,
        "production_ready": False,
    }


def render_catalog(snapshot: SourceSnapshot) -> bytes:
    raw = (json.dumps(build_catalog(snapshot), ensure_ascii=False, allow_nan=False,
                      sort_keys=True, indent=2) + "\n").encode("utf-8")
    if len(raw) > MAX_CATALOG_BYTES:
        raise InputError("scope_catalog_size_limit")
    return raw
