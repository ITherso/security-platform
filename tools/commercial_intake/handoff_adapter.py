"""Pure, fixed-text conversion to the unchanged Phase16 demo input contract."""
from __future__ import annotations

import json

from commercial_handoff.input_loader import _depth_check, _tree_budget
from commercial_handoff.schema import CONTRACT, MAX_INPUT_BYTES, InputError, validate

from .assessment_reader import AssessmentSource
from .source_mapping import _mapped_items


_CASE_ID = "DEMO-TERMIVAR-017"
_SOURCE_ID = "ART-A1"
_SCOPE_SUMMARY = (
    "Demonstration only — No real system assessed. "
    "Önceden mevcut assessment metadata'sının offline demo teslim girdisine aktarımıdır; "
    "gerçek hedef, müşteri kapsamı veya değerlendirme yetkisi doğrulanmadı."
)
_PROVENANCE_NOTE = (
    "Açıkça seçilmiş assessment'ın byte kimliği intake tarafından ölçüldü. "
    "Sözleşme ve kapalı metadata alt kümesi okundu; producer kimliği, özgün generation, "
    "gerçek hedef veya güvenlik iddiası bağımsız doğrulanmadı. "
    "Kaynak başlık/özet/öneri ve dosya yolu bu modele kopyalanmadı."
)
_EVIDENCE_LIMITATIONS = (
    "Yalnız mevcut kaynak metadata'sı eşlendi; gerçek uzman incelemesi yapılmadı. "
    "Opaque evidence referansları ham kanıta erişim veya paylaşım izni değildir; "
    "kaynak disposition'ı doğrulanmış zafiyet veya müşteri kararı olarak onaylanmadı."
)
_DELIVERY_CONSTRAINTS = (
    "Demonstration only — No real system assessed.",
    "Aktarılan kayıtlar unreviewed, scope unknown ve client inclusion pending_decision kalır; gerçek reviewer veya karar zamanı verilmez.",
    "Kaynak complete etiketi kapsamın eksiksizliği, temiz sonuç veya güvenli sistem kanıtı değildir.",
    "Kaynak hash'i ve varsa kısmi JSON-entry manifest eşleşmesi producer kimliği veya full-bundle doğrulaması değildir.",
    "Bağımsız comparison ve elle hazırlanmış incomplete diagnostic bu ana assessment modeline dahil edilmedi; retest sonucu üretilmedi.",
    "Ham HTTP, credential, hedef, iç yol ve kaynak serbest metni aktarılmaz; araç genel sır taraması veya otomatik redaksiyon yapmaz.",
    "Uzman incelemesi, kanıt erişimi, veri/saklama kararları ve gerçek müşteri teslim onayı açık kalır; bu demo çalışma veya teslim yetkisi vermez.",
)


def _payload(assessment: AssessmentSource) -> dict:
    items = _mapped_items(assessment)
    observations = []
    for item in items:
        observations.append({
            "observation_id": f"OBS-{item.index + 1:02d}",
            "source_artifact": _SOURCE_ID,
            "observation_ref": item.fingerprint,
            "source_json_pointer": f"/items/{item.index}",
            "capability_id": item.capability_id,
            "source_disposition": item.disposition,
            "review_status": "unreviewed",
            "scope_status": "unknown",
            "client_inclusion": "pending_decision",
            "safe_summary": None,
            "evidence_limitations": _EVIDENCE_LIMITATIONS,
            "decision_ref": None,
        })
    return {
        "schema_version": CONTRACT,
        "case_id": _CASE_ID,
        "mode": "demo",
        "scope_summary": _SCOPE_SUMMARY,
        "authorization_status": "not_provided",
        "source_artifacts": [{
            "artifact_id": _SOURCE_ID,
            "contract": assessment.schema,
            "sha256": assessment.sha256,
            "byte_length": assessment.byte_length,
            "completion_status": assessment.status,
            "provenance_note": _PROVENANCE_NOTE,
        }],
        "observations": observations,
        "review_decisions": [],
        "delivery_constraints": list(_DELIVERY_CONSTRAINTS),
    }


def _checked_bytes(payload: dict) -> bytes:
    # Reuse the existing input's aggregate key/value and node budgets. A reader
    # item-count success does not imply that the generated Phase16 input fits.
    # There is no truncation, partial success or automatic review escalation.
    _tree_budget(payload)
    validate(payload)
    try:
        text = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2,
                          allow_nan=False) + "\n"
        raw = text.encode("utf-8", "strict")
    except (UnicodeError, ValueError, TypeError):
        raise InputError("invalid_generated_handoff") from None
    _depth_check(text)
    if not 0 < len(raw) <= MAX_INPUT_BYTES:
        raise InputError("generated_handoff_size_limit")
    return raw


def build_handoff_input(assessment: AssessmentSource) -> dict:
    """Build and validate a fresh exact Phase16 input using allowed metadata."""
    payload = _payload(assessment)
    _checked_bytes(payload)
    return payload


def render_handoff_input(assessment: AssessmentSource) -> bytes:
    """Return deterministic UTF-8 JSON only after all Phase16 bounds pass."""
    return _checked_bytes(_payload(assessment))
