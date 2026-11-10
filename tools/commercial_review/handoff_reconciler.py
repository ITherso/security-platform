"""Apply exact, explicit analyst declarations to a fresh demo handoff only."""
from __future__ import annotations

from dataclasses import dataclass, field
import hashlib
import string

from commercial_handoff.input_loader import LoadedInput
from commercial_handoff.review_rules import build_models
from commercial_handoff.schema import HandoffInput, validate

from .decision_binding import bind_decisions
from .decision_overlay import DecisionOverlay
from .review_contracts import (
    ReviewError, ReviewPacket, handoff_to_dict, render_handoff_bytes,
)


@dataclass(frozen=True, slots=True)
class DecisionMapping:
    observation_id: str
    observation_key: str
    source_assessment_sha256: str
    source_json_pointer: str
    fingerprint: str
    source_disposition: str
    decision_id: str | None
    decision_context_digest: str | None
    safe_summary_digest: str | None
    mapping_status: str
    review_status: str
    scope_status: str
    client_inclusion: str
    selected_for_draft: bool
    selection_blockers: tuple[str, ...]
    not_transferred_fields: tuple[str, ...]
    reason_not_provided: bool


@dataclass(frozen=True, slots=True)
class ReconciliationMapping:
    review_packet_digest: str
    source_assessment_digest: str
    original_handoff_digest: str
    source_observation_count: int
    applied_decision_count: int
    observations: tuple[DecisionMapping, ...]
    delivery_blockers: tuple[str, ...]
    demo_only: bool = field(default=True, init=False)
    human_review_verified: bool = field(default=False, init=False)
    producer_verified: bool = field(default=False, init=False)
    release_authorized: bool = field(default=False, init=False)


@dataclass(frozen=True, slots=True)
class ReconcileResult:
    document: HandoffInput
    mapping: ReconciliationMapping


def reconcile_handoff(
    packet: ReviewPacket,
    original: LoadedInput,
    overlay: DecisionOverlay,
    *,
    packet_digest: str,
) -> ReconcileResult:
    """Reconcile declarations, not source truth, human identity or authority.

    Empty overlays return the original immutable document. Other overlays may
    update only representable human fields. There is no implicit overwrite of
    existing decisions, inference from source text, or current-time default.
    """
    bindings = bind_decisions(packet, original, overlay, packet_digest=packet_digest)
    by_observation = {bound.observation.observation_id: bound.decision for bound in bindings}
    if not bindings:
        document = original.document
    else:
        payload = handoff_to_dict(original.document)
        for row in payload["observations"]:
            decision = by_observation.get(row["observation_id"])
            if decision is None:
                continue
            row["review_status"] = decision.review_status
            row["scope_status"] = decision.scope_status
            row["client_inclusion"] = decision.client_inclusion
            # Exact explicit text (including null), never a prior narrative.
            row["safe_summary"] = decision.safe_summary
            row["decision_ref"] = decision.decision_id
            payload["review_decisions"].append({
                "decision_id": decision.decision_id,
                "observation_id": decision.observation_id,
                "review_status": decision.review_status,
                "client_inclusion": decision.client_inclusion,
                "reviewer_ref": decision.reviewer_ref,
                "reviewed_at": decision.reviewed_at,
                # Phase16 requires a non-null reason. This is an explicit
                # absence marker, not a manufactured analyst rationale.
                "reason": decision.reason if decision.reason is not None else "not_provided",
            })
        document = validate(payload)
    # Preserve the unchanged Phase16 aggregate limits before any publication.
    render_handoff_bytes(document)
    internal, _client = build_models(document)
    reviews = {row.observation.observation_id: row for row in internal.observation_reviews}
    mapping_rows = []
    for source in packet.observations:
        decision = by_observation.get(source.observation_id)
        current = reviews[source.observation_id]
        observation = current.observation
        untransferred = tuple(
            name for name in ("missing_evidence", "follow_up")
            if decision is not None and getattr(decision, name) is not None
        )
        mapping_rows.append(DecisionMapping(
            observation_id=source.observation_id,
            observation_key=source.observation_key,
            source_assessment_sha256=source.source_assessment_sha256,
            source_json_pointer=source.source_json_pointer,
            fingerprint=source.fingerprint,
            source_disposition=source.source_disposition,
            decision_id=decision.decision_id if decision else None,
            decision_context_digest=decision.decision_context_digest if decision else None,
            safe_summary_digest=(hashlib.sha256(decision.safe_summary.encode("utf-8", "strict")).hexdigest()
                if decision is not None and decision.safe_summary is not None else None),
            mapping_status="declared_decision_applied" if decision else "unchanged_pending",
            review_status=observation.review_status,
            scope_status=observation.scope_status,
            client_inclusion=observation.client_inclusion,
            selected_for_draft=current.selected_for_draft,
            selection_blockers=current.blockers,
            not_transferred_fields=untransferred,
            reason_not_provided=decision is not None and decision.reason is None,
        ))
    blockers = tuple(dict.fromkeys((*packet.delivery_blockers, *internal.delivery_blockers)))
    return ReconcileResult(document, ReconciliationMapping(
        review_packet_digest=packet_digest,
        source_assessment_digest=packet.source_assessment.sha256,
        original_handoff_digest=original.sha256,
        source_observation_count=len(packet.observations),
        applied_decision_count=len(bindings),
        observations=tuple(mapping_rows),
        delivery_blockers=blockers,
    ))


def render_reconciled_input(result: ReconcileResult) -> bytes:
    if type(result) is not ReconcileResult:
        raise ReviewError("invalid_reconciliation_result")
    return render_handoff_bytes(result.document)


def _md(value: str | int | bool | None) -> str:
    if value is None:
        value = "not_provided"
    elif type(value) is bool:
        value = "true" if value else "false"
    elif type(value) is int:
        value = str(value)
    if type(value) is not str:
        raise ReviewError("invalid_report_value")
    return "".join(f"&#{ord(c)};" if c in string.punctuation or c in "\r\n\t" else c for c in value)


def render_reconciliation_report(result: ReconcileResult) -> bytes:
    """Metadata-only Markdown; arbitrary analyst text is never rendered here."""
    if type(result) is not ReconcileResult:
        raise ReviewError("invalid_reconciliation_result")
    mapping = result.mapping
    parts = [
        "# İnceleme karar eşleme özeti",
        "**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**",
        "Bu demo etiketi bağımsız insan incelemesinin doğrulanmadığını belirtir. "
        "Aktarılan açık beyanlar gerçek uzman kimliğini, karar doğruluğunu veya teslim yetkisini kanıtlamaz.",
        "## Byte ve kaynak bağları",
        f"- Packet SHA256: {_md(mapping.review_packet_digest)}",
        f"- Kaynak assessment SHA256: {_md(mapping.source_assessment_digest)}",
        f"- Orijinal Phase17 girdi SHA256: {_md(mapping.original_handoff_digest)}",
        f"- Korunan kaynak gözlem sayısı: {_md(mapping.source_observation_count)}",
        f"- Açıkça sağlanmış ve bağlanmış karar sayısı: {_md(mapping.applied_decision_count)}",
        "Hash'ler yalnız byte/metadata bağlamasıdır; imza veya insan/üretici doğrulaması değildir.",
    ]
    for index, row in enumerate(mapping.observations, 1):
        parts.extend((
            f"## Gözlem {index}",
            f"- Observation ID: {_md(row.observation_id)}",
            f"- Kalıcı kaynak anahtarı: {_md(row.observation_key)}",
            f"- Kaynak SHA256: {_md(row.source_assessment_sha256)}",
            f"- JSON pointer: {_md(row.source_json_pointer)}",
            f"- Kaynak fingerprint: {_md(row.fingerprint)}",
            f"- Native disposition: {_md(row.source_disposition)}",
            f"- Eşleme durumu: {_md(row.mapping_status)}",
            f"- Decision ID: {_md(row.decision_id)}",
            f"- Tam karar context SHA256: {_md(row.decision_context_digest)}",
            f"- Exact safe_summary UTF-8 SHA256: {_md(row.safe_summary_digest)}",
            f"- İnsan review_status: {_md(row.review_status)}",
            f"- Scope_status: {_md(row.scope_status)}",
            f"- Client_inclusion: {_md(row.client_inclusion)}",
            f"- Phase16 taslak seçimi (doğrulama değildir): {_md(row.selected_for_draft)}",
            f"- Reason eksikliği not_provided marker ile kaydedildi: {_md(row.reason_not_provided)}",
            "### Phase16 seçim engelleri",
            "\n".join(f"- {_md(code)}" for code in row.selection_blockers)
                or "Bu satıra özgü seçim engeli listelenmedi; bu bir teslim onayı değildir.",
            "### Phase16'ya aktarılmayan overlay alanları",
            "\n".join(f"- {_md(name)}" for name in row.not_transferred_fields)
                or "Bu satırda ayrıca verilmiş, taşınamayan alan kaydı yok.",
        ))
    parts.extend((
        "## Açık teslim engelleri",
        "\n".join(f"- {_md(code)}" for code in mapping.delivery_blockers),
        "## Sabit güven sınırı",
        "- demo_only=true\n- human_review_verified=false\n- producer_verified=false\n- release_authorized=false",
        "İç karar gerekçesi, müşteri özeti, eksik kanıt ve takip metni bu raporda gösterilmez. "
        "missing_evidence/follow_up mevcut Phase16 şemasına zorla eklenmez; varsa ayrı seçilmiş overlay'de "
        "ve onun dosya hash bağında kalır. Reason null olduğunda yalnız not_provided marker'ı kullanılır. "
        "Mevcut kaynak metadata'sı ve evidence_limitations değiştirilmez.",
        "Serbest metinler otomatik redakte edilmez veya sır taramasından geçirilmez. "
        "Boş/pending seçim temiz değerlendirme veya güvenlik açığı olmadığı sonucu değildir. "
        "Gerçek uzman, yetki, veri işleme, güvenlik kabulü ve müşteri teslim kararları açık kalır.",
    ))
    raw = ("\n\n".join(parts) + "\n").encode("utf-8", "strict")
    if len(raw) > 1024 * 1024:
        raise ReviewError("reconciliation_report_size_limit")
    return raw
