"""Pure bounded view of unsubmitted task-bound response slots."""
from __future__ import annotations

import html

from slot_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_COUNT_LABELS = {
    "selected_reference_count": "Kaynak bütün selected reference",
    "selected_projection_count": "Kaynak bütün selected projection",
    "recorded_present_projection_count": "Kaynak kayıtlı present projection",
    "recorded_missing_projection_count": "Kaynak kayıtlı missing projection",
    "pending_task_count": "Kaynak gerçek pending task",
    "distinct_file_count": "Kaynak bütün projection içindeki farklı File ID",
    "distinct_candidate_count": "Kaynak bütün projection içindeki farklı candidate",
}
_COUNT_LABELS = {
    "selected_task_count": "Bu request selected task",
    "selected_reference_count": "Bu request task-associated reference",
    "response_slot_count": "Oluşturulmuş yanıt yuvası",
    "unsubmitted_slot_count": "Yanıt verilmemiş yuva",
    "submitted_response_count": "Alınmış response",
    "assigned_task_count": "Atanmış task",
    "observed_task_count": "Gözlemlenmiş task",
}


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


def _counts(lines: list[str], labels: dict, counts: dict) -> None:
    lines.extend(["| Sayım ve kendi kapsamı | Adet |", "| --- | ---: |"])
    for key, label in labels.items():
        lines.append(_row((label, _md(counts[key]))))


def _definitions(lines: list[str], fields: dict) -> None:
    lines.extend(["| Gelecekteki response alan adı | Tür tanımı; gerçek yanıt değeri değildir |", "| --- | --- |"])
    for name, type_description in fields.items():
        lines.append(_row((_md(name), _md(type_description))))


def _packets(lines: list[str], packets: list) -> None:
    for packet in packets:
        lines.extend([
            "", "### " + _md(packet["reference_id"]), "",
            "Source disclosure durumu: " + _md(packet["disclosure_status"]),
            "Matched File ID'ler, source sırasıyla: " + _items(packet["matched_file_ids"]), "",
            "| Gerçek supporting reference | Gerçek supporting candidate | Gerçek supporting metadata File ID |",
            "| --- | --- | --- |",
        ])
        for binding in packet["supporting_projection_bindings"]:
            lines.append(_row((_md(binding["reference_id"]), _md(binding["candidate_id"]), _md(binding["file_id"]))))
        lines.extend([
            "", "Tam izinli projection listesi özgün sıra ve türlerle korunur; yalnız missing veya selected task satırına kırpılmaz.", "",
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


def render_response_slot_summary(slots: dict, template: dict, receipt: dict) -> bytes:
    """Render closed validated copies only; accept no response or observation."""
    slots, template, receipt = validate_relationships(slots, template, receipt)
    request = slots["request"]
    lines = [
        "# Offline task-bound response slots", "", DEMO_LABEL, "",
        "Bu çıktı mevcut pending görevler için gelecekte kullanılabilecek yanıt yuvaları ve alan tanımları hazırlar. response_slot_created observation_received değildir. Gerçek response alınmaz, yeni source dosyası okunmaz/toplanmaz; analist atanmaz, görev kabul edilmez veya tamamlanmaz.", "",
        "## 1. Request ve gerçek current Phase40 kimlikleri", "",
        "- Slots sözleşmesi: " + _md(slots["schema_version"]),
        "- Template sözleşmesi: " + _md(template["schema_version"]),
        "- Receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Yerel request reference: " + _md(request["request_reference"]),
        "- Seçilen gerçek kaynak Task ID'leri: " + _items(request["selected_task_ids"]),
        "- Current Phase40 queue SHA256: " + _md(slots["source_phase40_queue_sha256"]),
        "- Current Phase40 manifest SHA256: " + _md(slots["source_phase40_manifest_sha256"]), "",
        "Current queue/manifest kimlikleri gerçek Phase40 source beşlisine aittir. Phase40 içine kaydedilmiş parent39 witnesses/manifest kimlikleri current Phase40 hash'leri yerine kullanılmaz. Kaynak Task ID'leri korunur; seçili packet altkümesi üzerinden F kimliği yeniden numaralandırılmaz.", "",
        "## 2. Beş gerçek Phase40 source artefact", "",
        "| Sabit source rolü | Source schema | Gerçek byte | Gerçek SHA256 |",
        "| --- | --- | ---: | --- |",
    ]
    for artifact in receipt["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _value(artifact["schema_version"]), _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend([
        "", "Dosya adları sabit source rolleridir; yeni path/URL okuma yetkisi değildir. Markdown schema null'dur; yeni sürüm uydurulmaz. Immutable source adapter gerçek dört payload/manifest, üç owner model, qualified owner Markdown ve full manifest eşliğini doğrular. Bu renderer source açmaz.", "",
        "## 3. Kaynak kapsamları ve yeni slot sayımları", "", "### Gerçek source queue yedi sayımı", "",
    ])
    _counts(lines, _SOURCE_COUNT_LABELS, receipt["source_counts"]["queue_counts"])
    lines.extend(["", "### Gerçek source handoff yedi sayımı", ""])
    _counts(lines, _SOURCE_COUNT_LABELS, receipt["source_counts"]["handoff_counts"])
    lines.extend(["", "### Yeni response slots yedi sayımı", ""])
    _counts(lines, _COUNT_LABELS, slots["counts"])
    lines.extend(["", "### Yeni response template yedi sayımı", ""])
    _counts(lines, _COUNT_LABELS, template["counts"])
    lines.extend([
        "", "Receipt selected_task_count: " + _md(receipt["selected_task_count"]), "",
        "Source queue/handoff sayımları kendi bütün projection kapsamlarını korur: tek missing task, iki distinct File ID'yi bire düşürmez. Yeni slot sayımları seçilen task kapsamıdır. submitted_response_count, assigned_task_count ve observed_task_count integer 0'dır; null response veya sıfır-byte file değildir. Bu modellerde completed count/durum üretilmez.", "",
        "## 4. Gerçek task bağına bağlı, yanıt verilmemiş yuvalar", "",
        "Binding digest exact current queue SHA256 ve gerçek task_id/reference_id/candidate_id/file_id alanlarının beş anahtarlı canonical JSON byte SHA256'ıdır. Sıralı anahtarlar/UTF-8/LF owner encoding kullanılır; liste sırası digest girdisi değildir. Digest yalnız eşleştirme anahtarıdır; secret/token, imza, anti-replay, producer veya authorization kanıtı değildir.", "",
        "| Source Task ID | Reference | Candidate | Metadata File ID | Binding digest | Follow-up türü | Task durumu | Fulfillment | Slot durumu | Submission |",
        "| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for slot in slots["response_slots"]:
        lines.append(_row((
            _md(slot["task_id"]), _md(slot["reference_id"]), _md(slot["candidate_id"]), _md(slot["file_id"]),
            _md(slot["binding_digest"]), _md(slot["followup_kind"]), _md(slot["task_status"]),
            _md(slot["fulfillment_status"]), _md(slot["slot_status"]), _value(slot["submission"]),
        )))
    for slot in slots["response_slots"]:
        lines.extend(["", "### " + _md(slot["task_id"]) + " için gelecekteki yanıt sözleşmesi", ""])
        _definitions(lines, slot["submission_contract"])
    lines.extend([
        "", "submission=null ve awaiting_external_response gerçek başlangıç durumudur. Gelecekteki alanların tür tanımları observation değeri değildir. source_locator_description eski boş metadata'dan türetilmez; yetkili kişi ileride uygun biçimde sağlamalıdır. Bu turda future submission parser veya filled-response intake çalışmaz.", "",
        "## 5. Selected task referanslarının bütün izinli paketleri", "",
    ])
    _packets(lines, slots["reference_packets"])
    lines.extend([
        "", "Bütün beş alanlı reference packet ve 11 projection alanı korunur. Present projection aynı bağlamda kalır; onun için yeni missing task veya response slot üretilmez. Recorded missing byte/hash null kalır; yeni observation veya fiziksel yokluk değildir. Eski fresh kodu source freshness/TTL garantisi sağlamaz.", "",
        "## 6. Ayrı, doldurulmamış response template", "",
        "Template request reference: " + _md(template["request_reference"]),
        "Template canonical slots SHA256: " + _md(template["slots_sha256"]), "",
        "slots_sha256 canonical ilk JSON'un gerçek byte kimliğidir; producer imzası değildir. Her entry aynı task_id/binding_digest'i taşır; response_status unsubmitted ve response null kalır.", "",
        "| Template Task ID | Binding digest | Response durumu | Response |", "| --- | --- | --- | --- |",
    ])
    for entry in template["template_entries"]:
        lines.append(_row((_md(entry["task_id"]), _md(entry["binding_digest"]), _md(entry["response_status"]), _value(entry["response"]))))
    for entry in template["template_entries"]:
        lines.extend(["", "### " + _md(entry["task_id"]) + " template.required_fields tanımları", ""])
        _definitions(lines, entry["required_fields"])
    lines.extend([
        "", "## 7. Source flag yokluğu, trust ve inspector sınırı", "",
        "Receipt content_scope: " + _md(receipt["content_scope"]),
        "Slots sınırlamaları: " + _items(slots["limitations"]),
        "Template sınırlamaları: " + _items(template["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "demo_only=true; exact kapalı trust_flags: " + "; ".join(_md(flag) + "=" + _md(slots["trust_flags"][flag]) for flag in FALSE_FLAGS) + ".", "",
        "Beş gerçek Phase40 source modelinde workflow_flags veya 17 workflow alanı yoktur. Bu yüzden yeni kapalı modellerde workflow_flags üretilmez. Eski excluded altıncı aggregate inspector'ın 17 flat false alanı source inheritance kanıtı sayılmaz ve bu akışta okunmaz. Yeni inspector aynı adları yalnız kendi yerel yetki/kabul sınırları olarak false bildirebilir; devralınmış source flag değildir.", "",
        "Yeni inspector yalnız beş yeni slots/template/receipt/summary/manifest dosyasını okur. Task/binding tekilliği, gösterilen gerçek tuple'dan digest, supported missing/full packet, null submission/response, unsubmitted durumları, ayrı counts, canonical actual slots SHA, receipt/MD ve dört payload manifest bağını inceler. content_consistent yalnız yeni beş çıktının iç tutarlılığıdır; original Phase40 task membership/necessity veya source observation bağımsız doğrulanmaz.", "",
        "Hash eşliği producer authentication, imza/Git attestation, anti-replay veya yetkilendirme değildir; tutarlı dosyalar birlikte değiştirilip yeniden hash'lenebilir. Source freshness/Phase31 guard/ownership/compiler/module closure/native/runtime ve human/legal/customer/production/release kabulü oluşmaz. Task gönderme/atama/kabul/iptal/tamamlama, source reobservation veya evidence collection yapılmaz.", "",
        "Bloke veya eşleşmeyen full packet/olumlu child metadata, source path/root/physical identity, credential ya da gerçek analist kimliği eklenmez. ID/hash hassas olabilir; minimizasyon anonimlik veya şifreleme garantisi değildir. Owner kod bağımlılığı eski runtime/veri erişimi veya ikinci host kabulü değildir.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8/BOM, wrong digest/duplicate/unknown task/çelişkili binding/modified queue-handoff, sahte veya doldurulmuş external response, gerçek response parser, görev atama/kabul/iptal/tamamlama, locator doğrulaması/source reobservation/evidence collection, limit/permission/crash/partial write/repeat determinism/ikinci host; Phase31 guard/source freshness/compiler/module closure/ownership/native/producer/human/legal/customer/release. Future alan tanımları gerçek intake kabulü değildir. Test/runner/coverage/typecheck/build/install ve Phase19 file:// UI kabulü beklemededir; engel aşılmaz.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("response_slot_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_response_slot_summary",)
