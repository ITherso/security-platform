"""Pure bounded view of deferred, unsubmitted task-bound intake records."""
from __future__ import annotations

import html

from intake_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SLOT_COUNT_LABELS = (
    ("selected_task_count", "Kaynak selected task"),
    ("selected_reference_count", "Kaynak selected reference"),
    ("response_slot_count", "Kaynak response slot"),
    ("unsubmitted_slot_count", "Kaynak unsubmitted slot"),
    ("submitted_response_count", "Kaynak submitted response"),
    ("assigned_task_count", "Kaynak assigned task"),
    ("observed_task_count", "Kaynak observed task"),
)
_PHASE40_COUNT_LABELS = (
    ("selected_reference_count", "Parent bütün selected reference"),
    ("selected_projection_count", "Parent bütün selected projection"),
    ("recorded_present_projection_count", "Parent kayıtlı present projection"),
    ("recorded_missing_projection_count", "Parent kayıtlı missing projection"),
    ("pending_task_count", "Parent pending task"),
    ("distinct_file_count", "Parent bütün projection içindeki farklı File ID"),
    ("distinct_candidate_count", "Parent bütün projection içindeki farklı candidate"),
)
_INTAKE_COUNT_LABELS = (
    ("selected_task_count", "Bu intake selected task"),
    ("selected_reference_count", "Bu intake selected reference"),
    ("intake_entry_count", "Bu intake entry"),
    ("awaiting_submission_count", "Yanıt bekleyen entry"),
    ("candidate_present_count", "Sağlanmış candidate"),
    ("structurally_compatible_count", "Yapısal uyumlu candidate"),
    ("observation_verified_count", "Doğrulanmış observation"),
    ("completed_task_count", "Tamamlanmış task"),
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
    return "null — sağlanmış değer yok" if value is None else _md(value)


def _items(values: list) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def _counts(lines: list[str], ordered_labels: tuple, counts: dict) -> None:
    lines.extend(["| Sayım ve kendi kapsamı | Adet |", "| --- | ---: |"])
    for key, label in ordered_labels:
        lines.append(_row((label, _md(counts[key]))))


def _packets(lines: list[str], packets: list) -> None:
    for packet in packets:
        lines.extend([
            "", "### " + _md(packet["reference_id"]), "",
            "Kayıtlı disclosure durumu: " + _md(packet["disclosure_status"]),
            "Matched File ID'ler kaynak sırasıyla: " + _items(packet["matched_file_ids"]), "",
            "| Gerçek supporting reference | Gerçek supporting candidate | Gerçek supporting File ID |",
            "| --- | --- | --- |",
        ])
        for binding in packet["supporting_projection_bindings"]:
            lines.append(_row((_md(binding["reference_id"]), _md(binding["candidate_id"]), _md(binding["file_id"]))))
        lines.extend([
            "", "Bütün izinli projection listesi, özgün sıra ve türlerle korunur; yalnız missing/selected task satırına kırpılmaz.", "",
            "| Reference | Candidate | Metadata File ID | Kayıtlı presence | Typed byte | Typed SHA256 | Upstream projection türü |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ])
        for projection in packet["projections"]:
            lines.append(_row((
                _md(projection["reference_id"]), _md(projection["candidate_id"]), _md(projection["file_id"]),
                _md(projection["source_file_presence"]), _value(projection["observed_byte_size"]),
                _value(projection["observed_sha256"]), _md(projection["upstream_projection_kind"]),
            )))
        lines.extend([
            "", "| Candidate | Phase31 observation kimliği | Phase31 comparison kimliği | Kayıtlı comparison durumu | Yorumlama sınırlamaları |",
            "| --- | --- | --- | --- | --- |",
        ])
        for projection in packet["projections"]:
            lines.append(_row((
                _md(projection["candidate_id"]), _md(projection["phase31_current_observation_id"]),
                _md(projection["phase31_comparison_id"]), _md(projection["upstream_comparison_status"]),
                _items(projection["interpretation_limitations"]),
            )))


def render_intake_summary(intake: dict, classification: dict, receipt: dict) -> bytes:
    """Render three validated closed copies; never call the future decoder."""
    intake, classification, receipt = validate_relationships(intake, classification, receipt)
    request = intake["request"]
    lines = [
        "# Offline deferred response intake", "", DEMO_LABEL, "",
        "Bu çıktı mevcut unsubmitted template'i bağımsız deferred intake tüketicisine bağlar; candidate verilmemiş durumunu korur. structurally_valid observation_verified değildir; task_binding_matched authorized_submission değildir; response=null fiziksel source dosyasının şimdi missing olduğu anlamına gelmez.", "",
        "## 1. Strict request ve current Phase41 source kimlikleri", "",
        "- Intake sözleşmesi: " + _md(intake["schema_version"]),
        "- Classification sözleşmesi: " + _md(classification["schema_version"]),
        "- Receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Yerel request reference: " + _md(request["request_reference"]),
        "- Candidate source: " + _md(request["candidate_source"]),
        "- Seçilen gerçek source Task ID'leri: " + _items(request["selected_task_ids"]),
        "- Current Phase41 slots SHA256: " + _md(intake["source_phase41_slots_sha256"]),
        "- Current Phase41 manifest SHA256: " + _md(intake["source_phase41_manifest_sha256"]), "",
        "Current Phase41 slots/manifest kimlikleri gerçek beşli byte'larına aittir. Phase41 içine kaydedilmiş parent40 queue/manifest pinleri ayrı rollerdir; current kimlik olarak kullanılmaz. Original Task ID ve kaynak binding kopyalanır; yeniden numaralama veya yeni task yoktur.", "",
        "## 2. Beş gerçek Phase41 source artefact", "",
        "| Sabit source rolü | Gerçek source schema | Gerçek byte | Gerçek SHA256 |",
        "| --- | --- | ---: | --- |",
    ]
    for artifact in receipt["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _value(artifact["schema_version"]), _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend(["", "| Sabit source rolü | Receipt source schema haritası |", "| --- | --- |"])
    for artifact in receipt["source_artifacts"]:
        name = artifact["name"]
        lines.append(_row((_md(name), _value(receipt["source_schema_versions"][name]))))
    lines.extend([
        "", "Dosya adları sabit source rolleridir; JSON path/URL yeni okuma yetkisi değildir. Markdown schema null kalır. Source adapter actual dört payload/manifest bağını, owner üç modeli/template ilişkisini, düzeltilmiş owner Markdown ve full manifest eşliğini doğrular; bu renderer fiziksel dosya açmaz.", "",
        "## 3. Dört source sayım kapsamı ve yeni sekiz sayım", "", "### Kaynak Phase41 slots yedi sayımı", "",
    ])
    _counts(lines, _SLOT_COUNT_LABELS, receipt["source_counts"]["slots_counts"])
    lines.extend(["", "### Kaynak Phase41 template yedi sayımı", ""])
    _counts(lines, _SLOT_COUNT_LABELS, receipt["source_counts"]["template_counts"])
    lines.extend(["", "### Kaynak receipt içindeki parent40 queue yedi sayımı", ""])
    _counts(lines, _PHASE40_COUNT_LABELS, receipt["source_counts"]["phase40_counts"]["queue_counts"])
    lines.extend(["", "### Kaynak receipt içindeki parent40 handoff yedi sayımı", ""])
    _counts(lines, _PHASE40_COUNT_LABELS, receipt["source_counts"]["phase40_counts"]["handoff_counts"])
    lines.extend(["", "### Bu deferred intake register sekiz sayımı", ""])
    _counts(lines, _INTAKE_COUNT_LABELS, intake["counts"])
    lines.extend(["", "### Bu intake classification sekiz sayımı", ""])
    _counts(lines, _INTAKE_COUNT_LABELS, classification["counts"])
    lines.extend([
        "", "Dört source grubu ayrı paydalarıyla korunur; flatten edilmez. Tek missing task, parent whole packet'taki iki distinct file/candidate sayısını bire düşürmez. Yeni son dört count integer0'dır. Null candidate, false candidate_present, integer0 ve unknown farklı anlamlardır; birbirlerine dönüştürülmez.", "",
        "## 4. Gerçek yanıtsız intake entry'leri", "",
        "| Original Task ID | Reference | Candidate | Metadata File ID | Kaynaktan korunan binding | Slot durumu | Response durumu | Candidate present | Candidate classification | Candidate response |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for entry in intake["intake_entries"]:
        lines.append(_row((
            _md(entry["task_id"]), _md(entry["reference_id"]), _md(entry["candidate_id"]), _md(entry["file_id"]),
            _md(entry["binding_digest"]), _md(entry["slot_status"]), _md(entry["response_status"]),
            _md(entry["candidate_present"]), _md(entry["candidate_classification"]), _value(entry["candidate_response"]),
        )))
    lines.extend([
        "", "No candidate supplied, unsubmitted ve awaiting_external_response gerçek mevcut template durumudur. Consumer doğrudan source slot submission=null ve template response=null/unsubmitted ilişkisini okur. Future decoder pozitif/negatif/None argümanıyla bu demo veya inspector tarafından çağrılmaz; sahte candidate ya da observation üretilmez.", "",
        "## 5. Tam izinli source reference paketleri", "",
    ])
    _packets(lines, intake["reference_packets"])
    lines.extend([
        "", "Bütün beş alanlı packet ve 11 projection alanı kaynak sırası/tür/null ile korunur. Present CAND0001 bağlamı pakette kalır; ona yeni intake entry oluşturulmaz. Missing observation byte/hash null, integer0 veya sıfır-byte file değildir. Eski fresh kodu source freshness/TTL garantisi sağlamaz. Bloke/eşleşmeyen olumlu child metadata çoğaltılmaz.", "",
        "## 6. Classification ve canonical register kimliği", "",
        "Classification canonical intake_register_sha256: " + _md(classification["intake_register_sha256"]), "",
        "| Task ID | Kaynak binding digest | Intake durumu | Structural sonuç | Observation verified | Task completed |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in classification["task_classifications"]:
        lines.append(_row((
            _md(row["task_id"]), _md(row["binding_digest"]), _md(row["intake_status"]),
            _md(row["structural_result"]), _md(row["observation_verified"]), _md(row["task_completed"]),
        )))
    lines.extend([
        "", "Awaiting_submission/not_evaluated_no_candidate; observation_verified ve task_completed false kalır. Canonical ilk JSON hash'i actual register byte kimliğini bağlar; producer imzası veya source yetkisi değildir.", "",
        "Inherited task binding parent40 queue preimage'ı ile türetilmiştir; current Phase41 slots hash'i kullanılarak yeniden türetilmez. Full source adapter eski owner'ın orijinal bağını doğrular ve source-bound builder exact digest/tuple'ı kopyalar. Yeni kapalı wire parent preimage'ı taşımaz; yalnız yeni beş dosyayı okuyan inspector original binding kriptografisini veya original task membership/necessity'yi bağımsız yeniden kanıtlayamaz.", "",
        "## 7. Gelecekteki candidate decoder sınırı", "",
        "Future memory-only API owner ValidatedResponseSlots ve exact yedi alanlı dict alır: task_id, binding_digest, reported_presence, observation_recorded_at, observation_method, source_locator_description, evidence_sha256_if_available. Bytes/JSON text/path/ikinci format kabul edilmez. Yapısal uyum structurally_compatible_unverified olarak kalır; observation verification/authorization değildir.", "",
        "Kapalı ret nedenleri unknown_task, binding_mismatch, invalid_field_set, invalid_field_type, invalid_field_value, duplicate_task_candidate'dır. Timestamp/method/locator için nonempty1..512 strict UTF-8 string yapısal sınırıdır; timestamp ISO/RFC/timezone/clock/freshness veya locator anlamı doğrulanmaz. Yanlış candidate digest/raw payload sonuç/log/store'a kopyalanmaz. Tek nesneli stateless API postconstruction duplicate JSON key veya çağrılar arası replay geçmişini bilemez.", "",
        "Bu API'nin dolu pozitif ve dolu negatif yolları NOT_RUN'dır. None da decoder'a gönderilmez. Gelecekteki alan sözleşmesi yeni kaynak locator'ı/analist kimliği/kanıt veya görev kabulü oluşturmaz.", "",
        "## 8. Trust, receipt ve inspector sınırı", "",
        "Receipt content_scope: " + _md(receipt["content_scope"]),
        "Intake sınırlamaları: " + _items(intake["limitations"]),
        "Classification sınırlamaları: " + _items(classification["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "demo_only=true; exact nested trust_flags: " + "; ".join(_md(flag) + "=" + _md(intake["trust_flags"][flag]) for flag in FALSE_FLAGS) + ".", "",
        "Source modelinde workflow_flags veya17 workflow alanı yoktur; miras gibi uydurulmaz. Yeni inspector'ın decoder/filled candidate/source read/assignment/observation/completion/producer/human kabul alanları yalnız kendi yerel false işlem sınırlarıdır. Exact18 trust false korunur; olumlu güven/authority sonucu türetilmez.", "",
        "Yeni inspector yalnız beş yeni intake/classification/receipt/summary/manifest dosyasının kapalı modelleri, task/digest eşliği, packet support, null/false/0, counts, canonical actual registerSHA, Markdown ve dört payload byte/hash ilişkisini inceler. content_consistent yalnız iç tutarlılıktır; eski Phase41 source, original binding preimage, candidate decoder, producer/observation/source freshness bağımsız doğrulaması değildir.", "",
        "Hash eşliği imza/Git attestation, anti-replay veya yetkilendirme değildir; tutarlı dosyalar birlikte değiştirilip yeniden hash'lenebilir. Kimlik/hash hassas olabilir; minimizasyon anonimlik/şifreleme değildir. Ham path/root/physical identity/credential/gerçek kişi bilgisi eklenmez. Owner kod bağımlılığı eski veri/native runtime veya ikinci host kabulü değildir.", "",
        "NOT_RUN: filled candidate positive/negative decoding, binding mismatch/unknown task/duplicate candidate/type-schema/wrongdigest/modifiedsource/hostile JSON/UTF-8/BOM, limit/permission/crash/partialwrite/repeatdeterminism/ikincihost; producer/anti-replay/source reobservation/evidence collection/analist atama-kabul-tamamlama/source freshness/Phase31 guard/compiler/module closure/ownership/native/human/legal/customer/release/production ve Phase19 UI. Test/build/install/import-smoke/AST/network/live çalışma yoktur; file:// engeli aşılmaz.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("deferred_intake_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_intake_summary",)
