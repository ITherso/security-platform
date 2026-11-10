"""Render fixed offline drafts from separate internal and client models.

Only trusted adjacent templates are read. No input paths, output files, JSON,
network, browser or Termivar runtime are accessed by this module.
"""
from __future__ import annotations

from html import escape
from pathlib import Path
import string
from string import Template

from .review_rules import ClientDraft, ClientItem, ClientSource, InternalSummary


MAX_TEMPLATE_BYTES = 64 * 1024
MAX_DOCUMENT_BYTES = 4 * 1024 * 1024
_TEMPLATE_NAMES = frozenset(("internal_review.md", "client_draft.md", "client_draft.html"))
_MISSING = "not_provided"
_EMPTY_SELECTION = (
    "Bu taslakta müşteri raporuna dahil edilmesi kararlaştırılmış bir bulgu "
    "bulunmamaktadır. Bu durum değerlendirmede güvenlik açığı olmadığı anlamına gelmez."
)
_BLOCKER_LABELS = {
    "source_artifact_missing": "Kaynak artefakt referansı eksik.",
    "source_artifact_unknown": "Kaynak artefakt kayıtlı kaynaklar arasında bulunamadı.",
    "source_contract_not_assessment": "Kaynak sözleşmesi desteklenen assessment değildir.",
    "source_assessment_not_complete": "Kaynak assessment complete değildir.",
    "observation_reference_missing": "Mevcut gözlem fingerprint referansı eksik.",
    "source_json_pointer_missing": "Kaynak JSON pointer eksik.",
    "duplicate_source_observation": "Aynı kaynak gözlem birden fazla kayıtla eşlenmiş.",
    "decision_reference_missing": "İnsan karar referansı eksik.",
    "decision_reference_unknown": "Karar referansı kayıtlı kararlar arasında bulunamadı.",
    "decision_observation_mismatch": "Karar başka bir gözleme bağlı.",
    "decision_review_status_mismatch": "Gözlem ve karar review_status değerleri uyuşmuyor.",
    "decision_client_inclusion_mismatch": "Gözlem ve karar paylaşım tercihleri uyuşmuyor.",
    "reviewer_reference_missing": "Gerekli reviewer referansı sağlanmadı.",
    "review_timestamp_missing": "Gerekli inceleme zamanı sağlanmadı.",
    "scope_not_in_scope": "Gözlem kapsam içi olarak kaydedilmemiş.",
    "client_inclusion_not_selected": "Müşteri taslağına dahil etme açıkça seçilmemiş.",
    "review_status_not_eligible": "İnsan inceleme durumu müşteri kaydı seçimine uygun değil.",
    "safe_summary_missing": "İzinli müşteri açıklaması sağlanmadı.",
    "demo_only_not_for_delivery": "Yalnız demo; gerçek müşteri teslimine uygun değil.",
    "human_review_not_verified": "Gerçek insan incelemesi bağımsız doğrulanmadı.",
    "release_not_authorized": "Gerçek teslim veya yayın yetkisi verilmedi.",
    "authorization_not_verified": "Değerlendirme yetkisi doğrulanmadı.",
    "delivery_constraints_unresolved": "Girişteki teslim kısıtları açık kalıyor.",
    "observation_selection_blocked": "Bir veya daha fazla gözlem seçim önkoşullarını karşılamıyor.",
    "orphan_review_decision": "Kararın bağlı olduğu gözlem bulunamadı.",
    "unused_review_decision": "Karar mevcut bir gözlemin seçilmiş karar referansına bağlı değil.",
}


class RenderError(ValueError):
    """A fixed, non-sensitive rendering error code."""


def _literal(value: str | int | bool | None) -> str:
    if value is None:
        return _MISSING
    if type(value) is bool:
        return "true" if value else "false"
    if type(value) not in (str, int):
        raise RenderError("invalid_render_value")
    return str(value)


def _md(value: str | int | bool | None) -> str:
    """Keep dynamic content on one source line and inhibit Markdown syntax.

    ASCII punctuation is represented as numeric entities, including &, <, >,
    links, images, table delimiters, backticks and backslash escapes. Newlines
    and tabs are entities too, so supplied text cannot introduce block syntax.
    Entity-looking input has its ampersands encoded; it is not trusted markup.
    This is output encoding, not secret detection or redaction.
    """
    value = _literal(value)
    return "".join(
        f"&#{ord(char)};" if char in string.punctuation or char in "\r\n\t" else char
        for char in value
    )


def _html(value: str | int | bool | None) -> str:
    # All uses are element text, never attributes, comments or metadata.
    return escape(_literal(value), quote=True)


def _blocker_md(code: str) -> str:
    label = _BLOCKER_LABELS.get(code, "Tanımlı açıklaması olmayan seçim/teslim engeli; insan incelemesi gerekir.")
    return f"- {_md(code)} — {label}"


def _template(name: str, fields: dict[str, str]) -> bytes:
    if name not in _TEMPLATE_NAMES:
        raise RenderError("invalid_template")
    path = Path(__file__).parent / "templates" / name
    try:
        with path.open("rb") as handle:
            raw = handle.read(MAX_TEMPLATE_BYTES + 1)
        if len(raw) > MAX_TEMPLATE_BYTES:
            raise RenderError("template_size_limit")
        rendered = Template(raw.decode("utf-8", "strict")).substitute(fields)
        data = rendered.encode("utf-8", "strict")
    except RenderError:
        raise
    except (OSError, UnicodeError, KeyError, ValueError):
        raise RenderError("template_render_failed") from None
    if len(data) > MAX_DOCUMENT_BYTES:
        raise RenderError("document_size_limit")
    return data


def _md_fields(rows: tuple[tuple[str, str | int | bool | None], ...]) -> str:
    return "\n".join(f"- **{label}:** {_md(value)}" for label, value in rows)


def _html_fields(rows: tuple[tuple[str, str | int | bool | None], ...]) -> str:
    return "<dl>\n" + "\n".join(
        f"<dt>{escape(label, quote=True)}</dt><dd>{_html(value)}</dd>"
        for label, value in rows
    ) + "\n</dl>"


def _internal_markdown(internal: InternalSummary) -> bytes:
    if type(internal) is not InternalSummary:
        raise RenderError("invalid_internal_model")
    document = internal.document
    source_blocks = []
    for index, source in enumerate(document.source_artifacts, 1):
        source_blocks.append(f"### Kaynak {index}\n\n" + _md_fields((
            ("Artefakt referansı", source.artifact_id),
            ("Sözleşme", source.contract),
            ("Tam dosya byte SHA256", source.sha256),
            ("Byte uzunluğu — giriş beyanı", source.byte_length),
            ("Kaynak tamamlanma etiketi", source.completion_status),
            ("İç provenance notu — doğrulanmamış giriş", source.provenance_note),
        )))
    observation_blocks = []
    for index, review in enumerate(internal.observation_reviews, 1):
        observation = review.observation
        source = review.source_or_none
        decision = review.decision_or_none
        observation_blocks.append(f"### Gözlem {index}\n\n" + _md_fields((
            ("İç gözlem kimliği", observation.observation_id),
            ("Kaynak artefakt referansı", observation.source_artifact),
            ("Çözümlenen kaynak SHA256", source.sha256 if source else None),
            ("Mevcut kaynak fingerprint", observation.observation_ref),
            ("Kaynak JSON pointer", observation.source_json_pointer),
            ("Kaynak capability", observation.capability_id),
            ("Native disposition — kaynak etiketi", observation.source_disposition),
            ("İnsan review_status — giriş beyanı", observation.review_status),
            ("Scope_status", observation.scope_status),
            ("Client_inclusion", observation.client_inclusion),
            ("İnceleme/kanıt sınırlaması — iç kayıt", observation.evidence_limitations),
            ("Safe_summary adlı serbest giriş — otomatik temizlenmedi", observation.safe_summary),
            ("Karar referansı", observation.decision_ref),
            ("Çözümlenen karar kimliği", decision.decision_id if decision else None),
            ("Müşteri taslağı için seçildi", review.selected_for_draft),
        )) + "\n\n**Seçim engelleri / seçilmediyse nedenleri:**\n\n" + (
            "\n".join(_blocker_md(code) for code in review.blockers)
            or "Bu kayda özgü seçim engeli listelenmedi; bu ifade teslim onayı değildir."
        ))
    decision_blocks = []
    for index, decision in enumerate(document.review_decisions, 1):
        decision_blocks.append(f"### İç karar kaydı {index}\n\n" + _md_fields((
            ("Karar kimliği", decision.decision_id),
            ("İç gözlem kimliği", decision.observation_id),
            ("İnsan review_status", decision.review_status),
            ("Client_inclusion", decision.client_inclusion),
            ("Reviewer referansı — kimliği doğrulanmadı", decision.reviewer_ref),
            ("Reviewed_at — giriş beyanı", decision.reviewed_at),
            ("Yalnız iç karar gerekçesi", decision.reason),
        )))
    return _template("internal_review.md", {
        "case_fields": _md_fields((
            ("Vaka referansı", document.case_id),
            ("Giriş sözleşmesi", document.schema_version),
            ("Mod", document.mode),
            ("Bildirilen kapsam — doğrulanmadı", document.scope_summary),
            ("Authorization_status — giriş beyanı", document.authorization_status),
        )),
        "sources": "\n\n".join(source_blocks) or "Kaynak artefakt kaydı sağlanmadı.",
        "observations": "\n\n".join(observation_blocks) or "Kaynak gözlem kaydı sağlanmadı; temiz sonuç anlamına gelmez.",
        "decisions": "\n\n".join(decision_blocks) or "İnsan karar kaydı sağlanmadı.",
        "constraints": "\n".join(f"- {_md(value)}" for value in document.delivery_constraints)
            or "İç teslim kısıtı sağlanmadı; bu durum teslim izni değildir.",
        "blockers": "\n".join(_blocker_md(code) for code in internal.delivery_blockers)
            or "Ek blocker kodu listelenmedi; demo kısıtları ve dış kabul gereksinimleri devam eder.",
    })


def _client_item_rows(item: ClientItem) -> tuple[tuple[str, str], ...]:
    # Explicit whitelist, not dataclass serialization or a copy of an input row.
    return (
        ("Gözlem referansı", item.observation_id),
        ("Seçilmiş açıklama — insan incelemesi gerekir", item.safe_summary),
        ("Native disposition — kaynak etiketi", item.source_disposition),
        ("İnsan review_status — doğrulanmamış beyan", item.review_status),
        ("Kaynak artefakt referansı", item.source_artifact_id),
        ("Kaynak fingerprint", item.observation_ref),
        ("Kaynak JSON pointer", item.source_json_pointer),
    )


def _client_source_rows(source: ClientSource) -> tuple[tuple[str, str | int], ...]:
    return (
        ("Kaynak artefakt referansı", source.artifact_id),
        ("Sözleşme", source.contract),
        ("Tam dosya byte SHA256 — giriş beyanı", source.sha256),
        ("Byte uzunluğu — giriş beyanı", source.byte_length),
        ("Kaynak tamamlanma etiketi", source.completion_status),
    )


def _incomplete_text(client: ClientDraft) -> str:
    if client.incomplete_review:
        return (
            "İnsan incelemesinin doğruluğu bağımsız doğrulanmadığından inceleme ve kabul "
            "durumu açık kalır. Bu taslak eksik incelemeyi sonuçlandırmaz; unavailable projection "
            "veya kapsanmamış alanlar temiz sonuç değildir. İç karar notları bu belgeye aktarılmaz."
        )
    return (
        "İstemci modelinde ek tamamlanmamış inceleme işareti bulunmaması, assessment kapsamının "
        "eksiksiz olduğunu, reviewer kimliğini veya teknik doğrulamayı kanıtlamaz. "
        "İç karar notları bu belgeye aktarılmaz."
    )


def _client_markdown(client: ClientDraft) -> bytes:
    if type(client) is not ClientDraft:
        raise RenderError("invalid_client_model")
    selected = "\n\n".join(
        f"### Seçilmiş kayıt {index}\n\n{_md_fields(_client_item_rows(item))}"
        for index, item in enumerate(client.selected_items, 1)
    ) or _EMPTY_SELECTION
    sources = "\n\n".join(
        f"### Kaynak referansı {index}\n\n{_md_fields(_client_source_rows(source))}"
        for index, source in enumerate(client.source_references, 1)
    ) or "Müşteri modeli için izinli kaynak referansı bulunmuyor; bu durum kaynakta gözlem olmadığı anlamına gelmez."
    return _template("client_draft.md", {
        "case_id": _md(client.case_id),
        "scope_summary": _md(client.scope_summary),
        "selected_items": selected,
        "incomplete_review": _md(_incomplete_text(client)),
        "source_references": sources,
    })


def _client_html(client: ClientDraft) -> bytes:
    if type(client) is not ClientDraft:
        raise RenderError("invalid_client_model")
    selected = "\n".join(
        f"<article><h3>Seçilmiş kayıt {index}</h3>{_html_fields(_client_item_rows(item))}</article>"
        for index, item in enumerate(client.selected_items, 1)
    ) or f"<p>{_html(_EMPTY_SELECTION)}</p>"
    sources = "\n".join(
        f"<article><h3>Kaynak referansı {index}</h3>{_html_fields(_client_source_rows(source))}</article>"
        for index, source in enumerate(client.source_references, 1)
    ) or "<p>Müşteri modeli için izinli kaynak referansı bulunmuyor; bu durum kaynakta gözlem olmadığı anlamına gelmez.</p>"
    return _template("client_draft.html", {
        "case_id": _html(client.case_id),
        "scope_summary": _html(client.scope_summary),
        "selected_items": selected,
        "incomplete_review": _html(_incomplete_text(client)),
        "source_references": sources,
    })


def render_documents(internal: InternalSummary, client: ClientDraft) -> dict[str, bytes]:
    """Return three fixed UTF-8 documents; the caller owns output publication."""
    return {
        "internal-review-summary.md": _internal_markdown(internal),
        "client-handoff-draft.md": _client_markdown(client),
        "client-handoff-draft.html": _client_html(client),
    }
