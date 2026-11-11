"""Build a deterministic, non-executable plan from closed offline metadata.

No input-controlled path, native command, network, clock or random value is used.
The selected source snapshot was measured by the explicit source reader; these
pure helpers bind its identities without attesting a producer or execution right.
"""
from __future__ import annotations

import hashlib
import re

from . import DEMO_LABEL, MAX_PROPOSAL_BYTES, PLAN_CONTRACT
from .capability_catalog import build_catalog
from .scope_contracts import InputError, LoadedProposal, json_bytes, proposal_to_dict
from .scope_validator import Preflight, preflight_to_dict, validate_scope
from .source_manifest import SourceSnapshot, validate_snapshot


PLAN_ID_PREFIX = "termivar-scope-plan:sha256:"
PLAN_ID_RECIPE = "sha256(sorted_indent2_utf8_json_plus_lf_without_plan_id)"
PROVENANCE_LIMITATIONS = (
    "proposal_hash_binds_selected_input_bytes_only",
    "catalog_hash_binds_generated_catalog_bytes_only",
    "source_hashes_bind_only_explicitly_inspected_files",
    "source_commit_and_hashes_do_not_authenticate_a_producer",
    "no_binary_build_or_runtime_acceptance_performed",
    "plan_is_not_native_attack_plan_or_accepted_scan_profile",
    "deterministic_recipe_not_repeat_run_qualified",
)


def _sha256(value: object) -> str:
    if type(value) is not str or re.fullmatch(r"[a-f0-9]{64}", value) is None:
        raise InputError("scope_invalid_digest")
    return value


def _source_identity(snapshot: SourceSnapshot) -> dict:
    validate_snapshot(snapshot)
    return {
        "commit": snapshot.commit,
        "files": [{
            "source_id": item.id, "path": item.path,
            "sha256": item.sha256, "byte_length": item.byte_length,
        } for item in snapshot.files],
    }


def build_plan(loaded: LoadedProposal, catalog: dict, catalog_sha256: str,
               preflight: Preflight, snapshot: SourceSnapshot) -> dict:
    """Bind current metadata, retaining every requested value and every result.

    Source mismatch stops plan creation; it cannot quietly select a new source,
    reinterpret baseline budgets, remove a method or enable execution.
    """
    if (type(loaded) is not LoadedProposal or type(loaded.byte_length) is not int
            or not 0 < loaded.byte_length <= MAX_PROPOSAL_BYTES):
        raise InputError("scope_invalid_loaded_proposal")
    _sha256(loaded.sha256)
    _sha256(catalog_sha256)
    validate_snapshot(snapshot)
    # Rebuild from the fixed catalog implementation and prepared file identity,
    # rather than trusting caller-supplied fields or a source_commit alone.
    expected_catalog = build_catalog(snapshot)
    if catalog != expected_catalog:
        raise InputError("source_version_mismatch")
    if hashlib.sha256(json_bytes(catalog)).hexdigest() != catalog_sha256:
        raise InputError("scope_catalog_digest_mismatch")
    proposal = proposal_to_dict(loaded.document)
    expected_preflight = validate_scope(loaded.document, catalog)
    if type(preflight) is not Preflight or preflight != expected_preflight:
        raise InputError("scope_preflight_binding_mismatch")
    preflight_data = preflight_to_dict(preflight)
    checks = preflight_data["checks"]
    body = {
        "schema_version": PLAN_CONTRACT,
        "mode": "demo",
        "demo_label": DEMO_LABEL,
        "source_proposal": {
            "schema_version": proposal["schema_version"],
            "proposal_id": proposal["proposal_id"],
            "sha256": loaded.sha256,
            "byte_length": loaded.byte_length,
        },
        "source_catalog": {
            "schema_version": catalog["schema_version"],
            "sha256": catalog_sha256,
            "source_commit": catalog["source_commit"],
        },
        "source_termivar": _source_identity(snapshot),
        "assessment_profile": proposal["assessment_profile"],
        "proposed_scope": proposal["scope"],
        "requested_capabilities": proposal["requested_capabilities"],
        "budgets": proposal["budgets"],
        "authorization_status": proposal["authorization_status"],
        "data_handling_status": proposal["data_handling_status"],
        "declared_review_requirements": proposal["review_requirements"],
        "compatibility": {
            "technical_status": preflight.technical_status,
            "checks": checks,
        },
        "human_decisions": [{
            "requirement": requirement,
            "declared_in_proposal": requirement in loaded.document.review_requirements,
            "status": "pending_authorization",
        } for requirement in preflight.human_requirements],
        "source_gaps": [{
            "check_id": item["check_id"], "subject": item["subject"],
            "codes": item["codes"],
        } for item in checks if item["status"] == "insufficient_source_evidence"],
        "execution_blockers": list(preflight.execution_blockers),
        "precondition_result": preflight.overall_status,
        "scope_of_result": "offline_declarative_source_compatibility_only",
        "limitations": list(preflight.limitations),
        "provenance_limitations": list(PROVENANCE_LIMITATIONS),
        "plan_identity_recipe": PLAN_ID_RECIPE,
        "native_runtime_configuration": False,
        "demo_only": True,
        "execution_authorized": False,
        "authorization_verified": False,
        "production_ready": False,
    }
    identity = hashlib.sha256(json_bytes(body)).hexdigest()
    return {"plan_id": PLAN_ID_PREFIX + identity, **body}


def _markdown_text(value: object) -> str:
    """Use body text only; inhibit raw HTML, links, images and Markdown syntax."""
    value = str(value)
    return "".join(
        "&#" + str(ord(char)) + ";" if char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        else char for char in value
    )


def render_summary(plan: dict, preflight: Preflight) -> bytes:
    """Render the closed plan/result fields; never emit a runnable CLI line."""
    if (type(plan) is not dict or plan.get("schema_version") != PLAN_CONTRACT
            or plan.get("demo_label") != DEMO_LABEL
            or plan.get("demo_only") is not True
            or any(plan.get(flag) is not False for flag in (
                "execution_authorized", "authorization_verified", "production_ready"))
            or type(preflight) is not Preflight):
        raise InputError("scope_invalid_plan")
    body = {key: value for key, value in plan.items() if key != "plan_id"}
    if plan.get("plan_id") != PLAN_ID_PREFIX + hashlib.sha256(json_bytes(body)).hexdigest():
        raise InputError("scope_plan_digest_mismatch")
    if (plan["compatibility"]["checks"] != preflight_to_dict(preflight)["checks"]
            or plan["source_proposal"]["proposal_id"] != preflight.proposal_id
            or plan["assessment_profile"] != preflight.assessment_profile
            or plan["compatibility"]["technical_status"] != preflight.technical_status
            or plan["precondition_result"] != preflight.overall_status
            or plan["execution_blockers"] != list(preflight.execution_blockers)):
        raise InputError("scope_preflight_binding_mismatch")
    lines = [
        "# Çevrimdışı assessment kapsam önerisi", "", DEMO_LABEL, "",
        "Bu belge tarama başlatmaz, gerçek hedef değerlendirmesi veya çalışma yetkisi vermez. "
        "Kaynak uyumluluğu, insan onayı veya runtime kabulü değildir.", "",
        "## Kimlik ve beyan edilen kapsam", "",
        "- Proposal: " + _markdown_text(plan["source_proposal"]["proposal_id"]),
        "- Plan: " + _markdown_text(plan["plan_id"]),
        "- Proposal byte SHA256: " + _markdown_text(plan["source_proposal"]["sha256"]),
        "- Catalog byte SHA256: " + _markdown_text(plan["source_catalog"]["sha256"]),
        "- İncelenen Termivar commit: " + _markdown_text(plan["source_termivar"]["commit"]),
        "- Profil: " + _markdown_text(plan["assessment_profile"]),
        "- Önerilen sentetik origin: " + _markdown_text(plan["proposed_scope"]["origin"]),
        "- Önerilen kök URL: " + _markdown_text(plan["proposed_scope"]["root_url"]),
        "- Önerilen yöntemler: " + _markdown_text(", ".join(plan["proposed_scope"]["requested_methods"])),
        "- Authenticated context: " + _markdown_text(plan["proposed_scope"]["authenticated_context"]),
        "- Teknik sonuç: " + _markdown_text(preflight.technical_status),
        "- Önkoşul sonucu: " + _markdown_text(preflight.overall_status),
        "", "## Kaynakla eşleme ve uyumsuzluklar", "",
        "Aşağıdaki sonuçlar yalnız incelenmiş kod ve önerideki beyanlarla ilgilidir. "
        "Bilinmeyen veya uyumsuz istekler kaldırılmamıştır.", "",
    ]
    for check in preflight.checks:
        if check.category == "human_requirement":
            continue
        lines.extend([
            "- " + _markdown_text(check.category + "/" + check.subject + ": " + check.status),
            "  - " + _markdown_text(check.explanation),
            "  - Kod: " + _markdown_text(", ".join(check.codes)),
            "  - Kaynak: " + _markdown_text(", ".join(check.source_refs) or "not_provided"),
        ])
        if check.category == "budget":
            lines.append("  - Önerilen / kaynak minimum / maksimum / varsayılan: " +
                         _markdown_text(" / ".join(
                             str(value) if value is not None else "not_evaluated"
                             for value in (check.proposed_value, check.source_minimum,
                                           check.source_maximum, check.source_default))))
    lines.extend([
        "", "## İnsan kararı ve yürütme engelleri", "",
        "Yetkilendirme not_provided; veri işleme pending_decision kalır. "
        "Scope owner, gerçek izin, insan incelemesi ve runtime qualification doğrulanmamıştır.", "",
    ])
    lines.extend("- " + _markdown_text(code) for code in preflight.execution_blockers)
    lines.extend([
        "", "## Veri ve yorum sınırı", "",
        "demo_only=true; execution_authorized=false; authorization_verified=false; production_ready=false.",
        "", "SHA256 yalnız içerik bağını gösterir; üretici, varlık sahipliği, hukuki izin, "
        "runtime başarısı veya güvenli sistem sonucu değildir.", "",
    ])
    lines.extend("- " + _markdown_text(code) for code in (*preflight.limitations, *PROVENANCE_LIMITATIONS))
    lines.extend([
        "", "## Yapılmayan kabuller", "",
        "Native CLI, scanner, ağ/DNS, gerçek hedef veya credential değerlendirmesi yapılmadı. "
        "Malformed/hostile encoding, duplicate key, permission, symlink, race, crash ve "
        "tekrarlı determinism kabulleri NOT_RUN; kaynak okuması bunların geçtiği anlamına gelmez.", "",
    ])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if len(raw) > 256 * 1024:
        raise InputError("scope_summary_size_limit")
    return raw


__all__ = ("PLAN_ID_PREFIX", "PLAN_ID_RECIPE", "build_plan", "render_summary")
