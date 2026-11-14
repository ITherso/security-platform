"""Bounded inert Markdown for the closed, minimal portable request models."""
from __future__ import annotations

import html

from exchange_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    response_field_definitions,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_TASK_FIELDS = (
    "task_id", "reference_id", "candidate_id", "file_id", "binding_digest",
    "slot_status", "response_status", "candidate_present", "observation_verified",
    "task_completed",
)
_EXCHANGE_COUNTS = (
    "selected_task_count", "unsubmitted_request_count", "response_field_definition_count",
    "submitted_response_count", "verified_observation_count", "completed_task_count",
)
_RESPONSE_FIELDS = (
    "task_id", "binding_digest", "reported_presence", "observation_recorded_at",
    "observation_method", "source_locator_description", "evidence_sha256_if_available",
)
_CAPSULE_MEMBERS = (
    ("task-request.json", "Kapalı minimal görev talebi"),
    ("response-contract.json", "Yalnız gelecekteki yedi alanın tanımı"),
    ("README.txt", "Sabit çevrimdışı kapsam ve yetkili insan sınırı"),
    ("capsule-manifest.json", "İlk üç üyenin byte/SHA256 ilişkisi; kendisi hariç"),
)


def _md(value: object) -> str:
    text = str(value).lower() if type(value) is bool else str(value)
    return "".join(
        "&#" + str(ord(char)) + ";"
        if char in _PUNCTUATION or ord(char) < 32 or 127 <= ord(char) <= 159
        else html.escape(char, quote=True)
        for char in text
    )


def _value(value: object) -> str:
    return "null — uygulanabilir şema yok" if value is None else _md(value)


def _row(values: tuple[str, ...]) -> str:
    return "| " + " | ".join(values) + " |"


def _counts(lines: list[str], heading: str, counts: dict, fields: tuple | None = None) -> None:
    lines.extend(["", "### " + heading, "", "| Alan | Adet |", "| --- | ---: |"])
    for key in (sorted(counts) if fields is None else fields):
        lines.append(_row((_md(key), _md(counts[key]))))


def _limitations(lines: list[str], heading: str, values: list) -> None:
    lines.extend(["", heading])
    for value in values:
        lines.append("- " + _md(value))


def render_task_exchange_summary(envelope: dict, index: dict, receipt: dict) -> bytes:
    """Validate three closed copies and render without source IO or response decoding."""
    envelope, index, receipt = validate_relationships(envelope, index, receipt)
    lines = [
        "# Offline portable task exchange", "", DEMO_LABEL, "",
        "Bu çıktı yalnız seçilmiş, yanıtsız görevlerin minimal çevrimdışı talebini açıklar. Portable request geçerliliği source observation doğrulaması değildir; task binding eşliği producer authentication değildir; paket oluşturulması görev gönderimi değildir; recipient validation yetkili yanıt değildir.", "",
        "## 1. Güncel Phase42 kaynak kimliği ve kapsam", "",
        "- Portable request sözleşmesi: " + _md(envelope["schema_version"]),
        "- Exchange index sözleşmesi: " + _md(index["schema_version"]),
        "- Source receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Yerel request reference: " + _md(envelope["request_reference"]),
        "- Güncel Phase42 register SHA256: " + _md(envelope["source_phase42_register_sha256"]),
        "- Güncel Phase42 manifest SHA256: " + _md(envelope["source_phase42_manifest_sha256"]),
        "- Receipt content scope: " + _md(receipt["content_scope"]), "",
        "Bu iki digest güncel Phase42 dosyalarına aittir. Kaynak içindeki Phase41 slots/manifest kimlikleri ebeveyn provenance'dır; güncel Phase42 kimliği yerine geçmez. Kaynak beşlinin dosya kimlikleri hedef source dosyası gözlemi değildir.", "",
        "| Phase42 kaynak artefact | Byte | SHA256 | Sözleşme |",
        "| --- | ---: | --- | --- |",
    ]
    for artifact in receipt["source_artifacts"]:
        name = artifact["name"]
        lines.append(_row((
            _md(name), _md(artifact["bytes"]), _md(artifact["sha256"]),
            _value(receipt["source_schema_versions"][name]),
        )))
    _counts(lines, "Portable request ve index: bu paketin altı sayacı", envelope["counts"], _EXCHANGE_COUNTS)
    lines.extend([
        "", "Index aynı altı sayacı taşır; yedi future field definition bütün paket için ortak sözleşmedir, task sayısıyla çarpılmaz. submitted_response_count, verified_observation_count ve completed_task_count integer0 kalır.", "",
        "## 2. Altı ayrı kaynak sayım kapsamı", "",
        "Aşağıdaki paydalar birleştirilmez. Register/classification bu Phase42 kaynak grubudur; slots/template ve queue/handoff ebeveyn kapsamlarıdır. Ebeveynin farklı file/candidate sayısı, tek seçilmiş task gerekçesiyle küçültülmez.",
    ])
    source_counts = receipt["source_counts"]
    phase41 = source_counts["phase41_counts"]
    phase40 = phase41["phase40_counts"]
    for heading, counts in (
        ("Phase42 register_counts", source_counts["register_counts"]),
        ("Phase42 classification_counts", source_counts["classification_counts"]),
        ("Parent Phase41 slots_counts", phase41["slots_counts"]),
        ("Parent Phase41 template_counts", phase41["template_counts"]),
        ("Parent Phase40 queue_counts", phase40["queue_counts"]),
        ("Parent Phase40 handoff_counts", phase40["handoff_counts"]),
    ):
        _counts(lines, heading, counts)
    lines.extend(["", "## 3. Seçilmiş minimal görevler", ""])
    for task in envelope["tasks"]:
        lines.extend(["### " + _md(task["task_id"]), "", "| Exact görev alanı | Değer |", "| --- | --- |"])
        for key in _TASK_FIELDS:
            lines.append(_row((_md(key), _md(task[key]))))
        lines.append("")
    lines.extend([
        "awaiting_external_response/unsubmitted ve false candidate_present/observation_verified/task_completed korunur. Kaynak candidate_response=null bilgisi yanıtsız seçim koşuludur; portable görevde candidate_response alanı veya doldurulmuş payload yoktur. Null, false ve integer0 birbirinin yerine kullanılmaz. Kaynakta kayıtlı missing, dosyanın bugün fiziksel olarak yokluğunu kanıtlamaz.", "",
        "Inherited binding_digest kaynaktan kopyalanır; current Phase42 register/manifest veya parent Phase41 slots hash'iyle yeniden türetilmez. Orijinal Phase40 task-binding preimage'ı mevcut minimal wire'da yoktur. Buradaki eşlik, orijinal binding kriptografisini, görev sahipliğini, gerekliliğini veya original task membership'i bağımsız kanıtlamaz.", "",
        "## 4. Gelecekteki response: yalnız alan tanımları", "",
        "| Alan | Mevcut owner tür tanımı |", "| --- | --- |",
    ])
    definitions = response_field_definitions()
    for key in _RESPONSE_FIELDS:
        lines.append(_row((_md(key), _md(definitions[key]))))
    lines.extend([
        "", "Producer bu exact yedi tanımı mevcut owner submission_contract ile karşılaştırır; standalone recipient yalnız yeni v1 kapalı sözleşmesini okur. Bu tanımlar doldurulmuş response, dosya toplama talimatı veya candidate kabulü değildir. Timestamp grammar/timezone/clock/freshness, source locator anlamı, anti-replay veya producer trust oluşturulmaz.", "",
        "Eski decode_candidate_response exact Phase41 ValidatedResponseSlots ister. Bu araç ona Phase42 snapshot, sahte eski snapshot, dolu candidate veya None göndermez. Candidate decoding ve submission NOT_RUN'dır.", "",
        "## 5. Minimum disclosure ve iki arşivin ayrımı", "",
        "Portable capsule SHA256: " + _md(index["capsule_sha256"]), "",
        "| İç portable capsule'ın exact üyesi | Sorumluluk |", "| --- | --- |",
    ])
    for name, meaning in _CAPSULE_MEMBERS:
        lines.append(_row((_md(name), meaning)))
    lines.extend([
        "", "Portable capsule içinde exported reference packet=0 ve projection=0. Seçilmemiş task, present CAND0001 metadata'sı, observed_byte_size/observed_sha256, ham kaynak/candidate payload, source locator değeri, analist kimliği veya yerel filesystem path taşınmaz. Görevin reference/candidate/file ID bağı global fiziksel dosya kimliği değildir. Minimizasyon anonimlik veya şifreleme garantisi değildir.", "",
        "İç manifest ilk üç üyeyi byte/SHA256 ile bağlar; kendisini hash'lemez. ZIP_STORED, exact sıra, sabit 1980-01-01 epoch, Unix regular0600, boş extra/comment ve flags0 canonical konteynerdir. Epoch gerçek gözlem zamanı veya güvenilir timestamp değildir. Capsule içinde nested ZIP/directory/symlink/encryption/duplicate/traversal yoktur; diske extraction yapılmaz.", "",
        "Dış kaynak teslim ZIP'i yeni araç/belgeleri ve operasyonel çıktıları, dolayısıyla iç portable capsule'ı taşır. Dış ZIP'in görevi kaynak teslimidir; iç capsule'ın üretici imzası veya gerçek alıcı kabulü değildir. Dört teslim metadata dosyası dış kaynak ZIP'inin dışında kalır; self-hash döngüsü kurulmaz.", "",
        "## 6. Trust, recipient ve inspector sınırı", "",
        "demo_only=true; exact18 nested trust_flags: " + "; ".join(
            _md(flag) + "=" + _md(envelope["trust_flags"][flag]) for flag in FALSE_FLAGS
        ) + ".", "",
        "Kaynakta workflow_flags veya17 workflow alanı yoktur; miras gibi uydurulmaz. Yeni inspector'ın dokuz yerel false işlem alanı, kaynak trust modeline eklenmiş yetki değildir: original_Phase42_files_read, task_dispatched, analyst_assigned, candidate_response_processed, source_observation_verified, source_producer_verified, recipient_authorized, human_acceptance_verified, second_host_acceptance_performed.", "",
        "Recipient runtime yalnız Python stdlib ve yeni exchange_contracts/portable_capsule/recipient_reader modülleridir. Reader exact immutable bytes üzerinde ZIP üyelerini, canonical JSON/README/ZIP byte eşliğini, manifest/hash ilişkisini, kapalı task/response sözleşmelerini denetler; Phase42 kaynaklarını açmaz. Yapısal tutarlılık producer identity, authorization, source truth veya ikinci host kabulü değildir. Tutarlı değişiklikler birlikte yeniden hash'lenebilir.", "",
        "Yeni inspector yalnız beş yeni operasyonel output'u ve iç capsule'ı değerlendirir. Kapsam: five_new_task_exchange_outputs_and_capsule_internal_correspondence_only. content_consistent yalnız bu yeni dosyalar arasındaki iç tutarlılıktır. Eski kaynak beşli, source observation, orijinal preimage, producer veya yetkili recipient bağımsız kanıtlanmaz.", "",
        "Yeni dar modeller strict UTF-8/JSON, duplicate key, unknown schema/field, float/NaN/Infinity, boolean-as-integer, invalid digest/enum ve duplicate task için ret kodu içerir. Request32KiB; source256/128/64/128/64KiB; toplam fiziksel input1MiB; capsule raw/uncompressed128KiB; index128KiB; receipt64KiB; Markdown128KiB; manifest64KiB; selected task8; JSON string512/depth12/nodes20000 sınırlarıdır. Ret kodunun varlığı saldırgan senaryonun çalıştırıldığını kanıtlamaz.",
    ])
    _limitations(lines, "Portable request sınırlamaları:", envelope["limitations"])
    _limitations(lines, "Index sınırlamaları:", index["limitations"])
    _limitations(lines, "Receipt sınırlamaları:", receipt["limitations"])
    lines.extend([
        "", "## 7. Açık NOT_RUN kabul kapıları", "",
        "NOT_RUN: gerçek ikinci host import; gerçek analistin request alması; recipient authentication/authorization; doldurulmuş response; Phase42 future decoder; response submission/ingestion; producer identity; imza/anti-replay/güvenilir timestamp; source locator doğrulama; source reobservation/evidence collection; task assignment/acceptance/completion; hostile JSON/adversarial ZIP/modified capsule/wrong digest/duplicate member/symlink/traversal/ZIP bomb/limit aşımı; permission/crash/partial write; repeat determinism; Phase31 guard; Rust compiler/module closure; component ownership; native scanner/runtime; human/legal/customer/production/release ve Phase19 UI kabulü.", "",
        "Test/runner/coverage/typecheck/build/install/AST/import smoke/preflight/--help/eski CLI/helper execution/network/live/admin işlemi yapılmaz. Phase19 file:// engeli server/hosting/farklı browser ile aşılmaz. İzinli iki ürün çağrısı ve ölçülmüş teknik teslim sonunda durulur; Phase44 veya yeni özellik başlatılmaz.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("task_exchange_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_task_exchange_summary",)
