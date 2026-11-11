"""Pure, source-bound compatibility checks for a synthetic scope proposal.

This is not Termivar's request broker, native AttackPlan or authorization gate.
Proposed values are retained unchanged; an unsupported condition is not repaired.
Context markers are declarations, never feature, credential or permission proof.
"""
from __future__ import annotations

from dataclasses import dataclass
from urllib.parse import urlsplit

from . import DEMO_LABEL, REVIEW_REQUIREMENTS
from .capability_catalog import (
    ROOT_AUTHORIZATION_CAPABILITY, RESOURCE_AUTHORIZATION_CAPABILITY,
)
from .scope_contracts import (
    BUDGET_FIELDS, InputError, ScopeProposal, proposal_to_dict, validate_proposal,
)
from .source_manifest import PINNED_COMMIT


PREFLIGHT_CONTRACT = "termivar-assessment-scope-preflight/v1"
CATALOG_CONTRACT = "termivar-assessment-capability-catalog/v1"
STATUSES = frozenset((
    "supported_by_source", "unsupported", "insufficient_source_evidence",
    "missing_required_context", "budget_conflict", "pending_authorization",
))
BASE_BLOCKERS = (
    "demo_only_no_execution", "authorization_not_provided",
    "data_handling_pending_decision", "scope_owner_not_verified",
    "human_review_not_performed", "runtime_qualification_not_performed",
)
LIMITATIONS = (
    "source_inspection_is_not_runtime_acceptance",
    "context_markers_are_declarations_not_runtime_authority",
    "native_get_is_not_a_side_effect_free_guarantee",
    "scope_origin_is_not_legal_authorization_or_asset_ownership",
    "native_cli_custom_budget_override_not_established",
    "budget_range_match_is_not_full_coverage_or_completion",
    "no_per_capability_request_cost_or_coverage_estimate",
    "optional_child_active_allowances_not_composed",
    "retained_body_limit_is_not_a_wire_chunk_ceiling",
    "third_party_provider_and_identity_scopes_not_authorized",
    "no_target_dns_network_or_credential_validation",
)


@dataclass(frozen=True, slots=True)
class PreflightCheck:
    check_id: str
    category: str
    subject: str
    status: str
    codes: tuple[str, ...]
    explanation: str
    source_refs: tuple[str, ...]
    proposed_value: int | None = None
    source_minimum: int | None = None
    source_maximum: int | None = None
    source_default: int | None = None


@dataclass(frozen=True, slots=True)
class Preflight:
    proposal_id: str
    assessment_profile: str
    technical_status: str
    overall_status: str
    checks: tuple[PreflightCheck, ...]
    human_requirements: tuple[str, ...]
    execution_blockers: tuple[str, ...]
    limitations: tuple[str, ...]


def _check(check_id: str, category: str, subject: str, status: str,
           codes: tuple[str, ...], explanation: str,
           source_refs: tuple[str, ...] = (),
           numeric_values: tuple[int, int | None, int | None, int | None] | None = None) -> PreflightCheck:
    if status not in STATUSES:
        raise InputError("scope_invalid_preflight_status")
    return PreflightCheck(check_id, category, subject, status, codes,
                          explanation, source_refs, *(numeric_values or (None, None, None, None)))


def _origin_key(value: str) -> tuple[str, str, int]:
    """Conservative ASCII .invalid subset of native Url origin equality.

    Syntax is checked by scope_contracts. No DNS, IDNA conversion or URL repair
    occurs here. Default-port equivalence follows the HTTP(S) origin model.
    """
    parts = urlsplit(value)
    return (parts.scheme.lower(), (parts.hostname or "").lower(),
            parts.port or (443 if parts.scheme == "https" else 80))


def _entry_refs(entry: dict) -> tuple[str, ...]:
    return tuple(dict.fromkeys(item["source_id"] for item in entry["source_evidence"]))


def _catalog_shape(catalog: object) -> tuple[dict[str, dict], dict, bool]:
    """Check local catalog seams without treating proposal data as a catalog."""
    if type(catalog) is not dict:
        raise InputError("scope_invalid_catalog")
    source_matches = (catalog.get("schema_version") == CATALOG_CONTRACT
                      and catalog.get("source_commit") == PINNED_COMMIT)
    if not source_matches:
        return {}, {}, False
    rows = catalog.get("entries")
    limits = catalog.get("budget_limits")
    if type(rows) is not list or len(rows) != 11 or type(limits) is not dict:
        raise InputError("scope_invalid_catalog")
    entries: dict[str, dict] = {}
    for row in rows:
        if (type(row) is not dict or type(row.get("capability_id")) is not str
                or row["capability_id"] in entries
                or row.get("planner_support") not in ("supported_by_source", "unsupported")
                or row.get("kind") not in ("observation_only", "differential_review",
                                            "metadata_only", "unsupported_stub")
                or row.get("namespace") not in ("assessment_item", "graphql_catalog", "cli_surface")
                or row.get("evidence_class") not in (
                    "source_declared", "implementation_inspected", "insufficient_source_evidence")
                or type(row.get("requires_authenticated_context")) is not bool
                or type(row.get("assessment_profiles")) is not list
                or type(row.get("required_contexts")) is not list
                or any(type(item) is not str for item in row["required_contexts"])
                or type(row.get("source_evidence")) is not list
                or not row["source_evidence"]):
            raise InputError("scope_invalid_catalog")
        for evidence in row["source_evidence"]:
            if type(evidence) is not dict or type(evidence.get("source_id")) is not str:
                raise InputError("scope_invalid_catalog")
        entries[row["capability_id"]] = row
    if set(limits) != set(BUDGET_FIELDS):
        raise InputError("scope_invalid_catalog")
    for row in limits.values():
        if (type(row) is not dict
                or any(type(row.get(key)) is not int for key in ("minimum", "maximum", "default"))
                or not 0 <= row["minimum"] <= row["default"] <= row["maximum"]
                or not isinstance(row.get("source_refs"), (tuple, list))
                or not row["source_refs"]
                or any(type(item) is not str for item in row["source_refs"])):
            raise InputError("scope_invalid_catalog")
    return entries, limits, True


def validate_scope(proposal: ScopeProposal, catalog: dict) -> Preflight:
    """Evaluate declared compatibility only; every outcome remains non-executable."""
    # Also revalidate manually constructed dataclasses, without mutating them.
    proposal = validate_proposal(proposal_to_dict(proposal))
    entries, limits, source_matches = _catalog_shape(catalog)
    checks: list[PreflightCheck] = []
    checks.append(_check(
        "source_version", "source", "termivar_source",
        "supported_by_source" if source_matches else "insufficient_source_evidence",
        ("pinned_source_catalog_declared",) if source_matches else ("source_version_mismatch",),
        "Katalog pinlenmiş kaynak sürümünü bildiriyor; dosya kimlikleri plan oluşturulurken bağlanır."
        if source_matches else "Katalog sürümü incelenen kaynak sürümüyle eşleşmiyor.",
    ))
    web_profile = proposal.assessment_profile == "web-review"
    checks.append(_check(
        "assessment_profile", "profile", proposal.assessment_profile,
        "supported_by_source" if web_profile else "unsupported",
        ("web_review_profile_source_declared",) if web_profile else ("unsupported_planner_profile",),
        "İlk planlayıcı yalnız kaynakta tanımlı web-review alt kümesini inceler."
        if web_profile else "Baseline kaynakta vardır; bu planlayıcının web-review alt kümesinde değerlendirilmez.",
        ("termivar_scan_profile",),
    ))

    same_origin = _origin_key(proposal.scope.origin) == _origin_key(proposal.scope.root_url)
    checks.append(_check(
        "exact_origin", "scope", "scope.root_url",
        "supported_by_source" if same_origin else "unsupported",
        ("exact_origin_matches",) if same_origin else ("root_origin_mismatch",),
        "Önerilen kök, bildirilen sentetik origin ile aynı scheme/host/etkin port kapsamındadır."
        if same_origin else "Önerilen kök başka origin'e aittir; kapsam sessizce genişletilmez.",
        ("termivar_http_policy", "termivar_discovery"),
    ))
    has_query_or_fragment = "?" in proposal.scope.root_url or "#" in proposal.scope.root_url
    checks.append(_check(
        "query_free_root", "scope", "scope.root_url",
        "unsupported" if has_query_or_fragment else "supported_by_source",
        ("root_query_or_fragment_would_be_removed",) if has_query_or_fragment
        else ("query_free_root_matches",),
        "Native assessment query/fragment'i kaldırır; bu planlayıcı girdiyi değiştirmeden uyumsuz bildirir."
        if has_query_or_fragment else "Önerilen kök native query-free assessment temsiline uygundur.",
        ("termivar_discovery", "termivar_web_assessment"),
    ))
    for method in proposal.scope.requested_methods:
        supported = method in ("GET", "HEAD")
        code = ("assessment_method_source_declared" if supported else
                "options_is_general_probe_not_assessment_method" if method == "OPTIONS"
                else "post_is_not_base_assessment_subject_method")
        checks.append(_check(
            "method_" + method.lower(), "method", method,
            "supported_by_source" if supported else "unsupported", (code,),
            "Assessment subject yöntemi kaynakta tanımlıdır; yan etkisizlik veya çalışma izni kanıtı değildir."
            if supported else "Bu yöntem ilk planlayıcının GET/HEAD assessment subject alt kümesinde desteklenmez.",
            ("termivar_web_assessment",),
        ))
    root_get = "GET" in proposal.scope.requested_methods
    checks.append(_check(
        "root_get_required", "scope", "scope.requested_methods",
        "supported_by_source" if root_get else "unsupported",
        ("assessment_root_get_declared",) if root_get else ("assessment_root_get_required",),
        "Native assessment kök subject'i GET olarak oluşturur; öneri bu yöntemi içerir."
        if root_get else "Native assessment kök subject'i GET'tir; HEAD-only öneri uyumlu ilan edilmez.",
        ("termivar_web_assessment",),
    ))

    declared_contexts = set(proposal.scope.context_markers)
    known_contexts = {context for row in entries.values() for context in row["required_contexts"]}
    for marker in proposal.scope.context_markers:
        known = marker in known_contexts
        checks.append(_check(
            "context_" + str(len(checks) + 1), "context", marker,
            "supported_by_source" if known else "insufficient_source_evidence",
            ("context_marker_declared_only",) if known else ("unknown_context_marker",),
            "Bu işaret yalnız kaynak önkoşulunun beyanıdır; feature/identity/runtime kabulünü doğrulamaz."
            if known else "Bu bağlam işareti sınırlı kaynak kataloğuyla eşlenemedi.",
        ))

    for index, capability in enumerate(proposal.requested_capabilities, 1):
        row = entries.get(capability)
        refs = _entry_refs(row) if row else ()
        if row is None:
            status, codes, message = (
                "insufficient_source_evidence", ("capability_not_in_inspected_catalog",),
                "Bu capability için mevcut sınırlı katalog yeterli destek kanıtı sunmuyor.",
            )
        elif row["planner_support"] == "unsupported" or row["kind"] in ("metadata_only", "unsupported_stub"):
            status, codes, message = (
                "unsupported", ("metadata_or_stub_is_not_executable_assessment_capability",),
                "Metadata veya mevcut CLI stub yüzeyi çalıştırılabilir assessment capability değildir.",
            )
        elif not web_profile or proposal.assessment_profile not in row["assessment_profiles"]:
            status, codes, message = (
                "unsupported", ("capability_outside_planner_profile",),
                "Seçilen capability bu planlayıcının incelenen profil alt kümesiyle eşlenmez.",
            )
        elif row["evidence_class"] == "insufficient_source_evidence":
            status, codes, message = (
                "insufficient_source_evidence", ("capability_source_evidence_insufficient",),
                "Kaynak sınıfı capability desteğini yeterli biçimde belirlemiyor.",
            )
        else:
            missing = tuple(context for context in row["required_contexts"] if context not in declared_contexts)
            if row["requires_authenticated_context"] and proposal.scope.authenticated_context != "placeholder_declared":
                missing += ("authenticated_context_placeholder",)
            if missing:
                status, codes, message = (
                    "missing_required_context", tuple("missing_context:" + context for context in missing),
                    "Capability için zorunlu kaynak bağlamı öneride bildirilmemiştir; gerçek credential istenmez.",
                )
            elif capability in ("graphql.anonymous-root-introspection@1", "graphql.surface-observed@1"):
                status, codes, message = (
                    "unsupported", ("unsupported_planner_method_composition",),
                    "GraphQL child POST kullanır; ilk planlayıcının GET/HEAD yöntem sınırıyla çalışma bileşimi kabul edilmez.",
                )
            else:
                status, codes, message = (
                    "supported_by_source", ("source_conditions_declared_only",),
                    "İncelenen kaynak tanımı ve bildirilen önkoşullar eşleşir; gerçek runtime veya yetki kabulü değildir.",
                )
        checks.append(_check("capability_" + str(index), "capability", capability,
                             status, codes, message, refs))

    root_auth = ROOT_AUTHORIZATION_CAPABILITY in proposal.requested_capabilities
    resource_auth = RESOURCE_AUTHORIZATION_CAPABILITY in proposal.requested_capabilities
    if root_auth or resource_auth:
        conflict = root_auth and resource_auth
        checks.append(_check(
            "authorization_composition", "combination", "root_and_resource_authorization",
            "unsupported" if conflict else "supported_by_source",
            ("root_and_resource_authorization_mutually_exclusive",) if conflict
            else ("no_root_resource_authorization_conflict",),
            "Native CLI root authorization-context ile resource authorization review birleşimini reddeder."
            if conflict else "İki ayrı authorization inceleme yolu birlikte istenmemiştir; bağlam yine doğrulanmış değildir.",
            ("termivar_cli_main",),
        ))
    if root_auth:
        target = urlsplit(proposal.scope.root_url)
        exact_root = target.path in ("", "/") and not has_query_or_fragment
        https = target.scheme == "https"
        valid = exact_root and https
        checks.append(_check(
            "root_authorization_target", "combination", ROOT_AUTHORIZATION_CAPABILITY,
            "supported_by_source" if valid else "unsupported",
            ("root_authorization_target_shape_matches",) if valid
            else ("root_authorization_requires_https_origin_root",),
            "Sentetik HTTPS origin root biçimi eşleşir; kimlik veya yetkilendirme kanıtı değildir."
            if valid else "Root authorization-context exact origin root ve HTTPS ister; numeric-loopback istisnası bu .invalid alt kümesinde yoktur.",
            ("termivar_cli_main",),
        ))

    for key in BUDGET_FIELDS:
        proposed = getattr(proposal.budgets, key)
        bound = limits.get(key)
        if not source_matches or not web_profile or bound is None:
            checks.append(_check(
                "budget_" + key, "budget", key, "insufficient_source_evidence",
                ("budget_not_evaluated_outside_web_review_source_subset",),
                "Bu değer için web-review aralığı başka profile veya eşleşmeyen kaynağa uygulanmaz.",
                tuple(bound["source_refs"]) if bound else (),
                (proposed, None, None, None),
            ))
            continue
        in_range = bound["minimum"] <= proposed <= bound["maximum"]
        paused = proposed == 0 and key in ("max_total_requests", "max_wall_time_ms")
        status = "supported_by_source" if in_range and not paused else "budget_conflict"
        code = ("zero_budget_prevents_dispatch" if paused else
                "budget_within_source_range" if in_range else "budget_outside_source_range")
        checks.append(_check(
            "budget_" + key, "budget", key, status, (code,),
            "Önerilen bütçe incelenen kaynak aralığındadır; CLI override, tamamlanma veya kapsama garantisi değildir."
            if status == "supported_by_source" else
            "Sıfır request/time bütçesi dispatch'i durdurur; çalışabilir değerlendirme önerisi kabul edilmez."
            if paused else "Önerilen bütçe incelenen kaynak sözleşmesindeki desteklenen aralığın dışındadır.",
            tuple(bound["source_refs"]),
            (proposed, bound["minimum"], bound["maximum"], bound["default"]),
        ))

    for requirement in REVIEW_REQUIREMENTS:
        declared = requirement in proposal.review_requirements
        checks.append(_check(
            "human_" + requirement, "human_requirement", requirement,
            "pending_authorization", ("human_requirement_pending:" + requirement,),
            "İnsan kararı gereği bildirilmiştir; gerçek karar veya yetki doğrulanmamıştır."
            if declared else "Bu insan kararı öneride listelenmemiştir; gereklilik devam eder.",
        ))
    technical = tuple(check for check in checks if check.category != "human_requirement")
    priority = ("insufficient_source_evidence", "unsupported", "missing_required_context", "budget_conflict")
    technical_status = next((status for status in priority if any(
        check.status == status for check in technical)), "supported_by_source")
    blockers = list(BASE_BLOCKERS)
    for check in checks:
        if check.status != "supported_by_source":
            blockers.extend(check.codes)
    return Preflight(
        proposal.proposal_id, proposal.assessment_profile, technical_status,
        "pending_authorization", tuple(checks), tuple(REVIEW_REQUIREMENTS),
        tuple(dict.fromkeys(blockers)), LIMITATIONS,
    )


def preflight_to_dict(preflight: Preflight) -> dict:
    if type(preflight) is not Preflight:
        raise InputError("scope_invalid_preflight")
    return {
        "schema_version": PREFLIGHT_CONTRACT,
        "demo_label": DEMO_LABEL,
        "proposal_id": preflight.proposal_id,
        "assessment_profile": preflight.assessment_profile,
        "technical_status": preflight.technical_status,
        "overall_status": preflight.overall_status,
        "checks": [{
            "check_id": check.check_id, "category": check.category,
            "subject": check.subject, "status": check.status,
            "codes": list(check.codes), "explanation": check.explanation,
            "source_refs": list(check.source_refs),
            "proposed_value": check.proposed_value,
            "source_minimum": check.source_minimum,
            "source_maximum": check.source_maximum,
            "source_default": check.source_default,
        } for check in preflight.checks],
        "human_requirements": list(preflight.human_requirements),
        "execution_blockers": list(preflight.execution_blockers),
        "limitations": list(preflight.limitations),
        "demo_only": True,
        "execution_authorized": False,
        "authorization_verified": False,
        "production_ready": False,
    }


__all__ = (
    "PREFLIGHT_CONTRACT", "PreflightCheck", "Preflight", "validate_scope",
    "preflight_to_dict",
)
