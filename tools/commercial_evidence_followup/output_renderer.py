"""Pure bounded Markdown for recorded missing-evidence follow-up metadata."""
from __future__ import annotations

import html

from followup_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_COUNT_LABELS = {
    "required_file_count": "Kaynak Phase39 QUERY required File ID",
    "matched_reference_count": "Kaynak Phase39 QUERY matched reference",
    "matched_projection_count": "Kaynak Phase39 QUERY bütün matched projection",
    "matched_candidate_count": "Kaynak Phase39 QUERY matched candidate",
    "matched_present_projection_count": "Kaynak Phase39 QUERY kayıtlı present projection",
    "matched_absence_projection_count": "Kaynak Phase39 QUERY kayıtlı absence projection",
}
_FOLLOWUP_COUNT_LABELS = {
    "selected_reference_count": "Bu paketteki seçili reference",
    "selected_projection_count": "Bu paketteki bütün seçili projection",
    "recorded_present_projection_count": "Bu paketteki kayıtlı present projection",
    "recorded_missing_projection_count": "Bu paketteki kayıtlı missing projection",
    "pending_task_count": "Benzersiz gerçek binding için hazırlanan pending talep",
    "distinct_file_count": "Bütün seçili projection içindeki farklı File ID",
    "distinct_candidate_count": "Bütün seçili projection içindeki farklı candidate",
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
    return "null — kayıtlı değer yok" if value is None else _md(value)


def _items(values: list) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def _counts(lines: list[str], labels: dict, counts: dict) -> None:
    lines.extend(["| Sayım ve kendi paydası | Adet |", "| --- | ---: |"])
    for key, label in labels.items():
        lines.append(_row((label, _md(counts[key]))))


def _tasks(lines: list[str], tasks: list) -> None:
    lines.extend([
        "| Yerel task ID | Reference | Candidate | Metadata File ID | Kayıtlı presence | Follow-up türü | Task durumu | Fulfillment durumu |",
        "| --- | --- | --- | --- | --- | --- | --- | --- |",
    ])
    for task in tasks:
        lines.append(_row(_md(task[key]) for key in (
            "task_id", "reference_id", "candidate_id", "file_id",
            "recorded_source_file_presence", "followup_kind", "task_status", "fulfillment_status",
        )))
    if not tasks:
        lines.extend(["", "Bu kapalı pakette hazırlanmış takip işi yoktur; bu sonuç yeni fiziksel gözlem veya kaynak tamlığı kanıtı değildir."])


def _packets(lines: list[str], packets: list) -> None:
    for packet in packets:
        lines.extend([
            "", "### " + _md(packet["reference_id"]), "",
            "Kayıtlı disclosure durumu: " + _md(packet["disclosure_status"]),
            "Kaynak witness matched File ID'leri, kaynak sırasıyla: " + _items(packet["matched_file_ids"]), "",
            "| Gerçek supporting reference | Gerçek supporting candidate | Gerçek supporting File ID |",
            "| --- | --- | --- |",
        ])
        for binding in packet["supporting_projection_bindings"]:
            lines.append(_row((_md(binding["reference_id"]), _md(binding["candidate_id"]), _md(binding["file_id"]))))
        lines.extend([
            "", "Tam izinli projection listesi, kaynak sırası ve türleriyle; yalnız missing satırlara daraltılmaz:", "",
            "| Reference | Candidate | Metadata File ID | Kayıtlı presence | Typed byte | Typed SHA256 | Upstream projection kodu |",
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
    if not packets:
        lines.extend(["", "Bu pakette reference packet yoktur; gizli kaynak veya başka referanslar hakkında sonuç çıkarılmaz."])


def render_followup_summary(queue: dict, handoff: dict, receipt: dict) -> bytes:
    """Render validated closed copies; perform no source read or assignment."""
    queue, handoff, receipt = validate_relationships(queue, handoff, receipt)
    request = queue["request"]
    lines = [
        "# Offline recorded missing-evidence follow-up", "", DEMO_LABEL, "",
        "Bu çıktı, önceden açıklanmış witness metadata'sında missing olarak kayıtlı gerçek binding'ler için takip talebi hazırlar. recorded_missing_source güncel fiziksel dosya yokluğu değildir. Yeni source observation, dosya arama/toplama veya gerçek analist ataması yapılmaz.", "",
        "## 1. Strict request ve current Phase39 kimlikleri", "",
        "- Queue sözleşmesi: " + _md(queue["schema_version"]),
        "- Analyst handoff sözleşmesi: " + _md(handoff["schema_version"]),
        "- Source receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Yerel request reference: " + _md(request["request_reference"]),
        "- Gerçek current Phase39 WITNESSES SHA256: " + _md(queue["source_phase39_witnesses_sha256"]),
        "- Gerçek current Phase39 manifest SHA256: " + _md(queue["source_phase39_manifest_sha256"]),
        "- İstenen görünür reference ID'leri: " + _items(request["requested_reference_ids"]), "",
        "Current witnesses kimliği beşli source grubunun ikinci dosyasıdır; ilk QUERY dosyasının hash'i değildir. Phase39 içine kaydedilmiş eski Phase38 JOIN/manifest pinleri lineage metadata'sıdır; current Phase39 kimlikleri yerine kullanılmaz.", "",
        "## 2. Gerçek beş Phase39 source artefact kimliği", "",
        "| Sabit source rolü | Gerçek source sözleşme | Gerçek byte | Gerçek SHA256 |",
        "| --- | --- | ---: | --- |",
    ]
    for artifact in receipt["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _value(artifact["schema_version"]), _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend(["", "Receipt source schema haritası:", "", "| Source rolü | Kayıtlı schema |", "| --- | --- |"])
    for artifact in receipt["source_artifacts"]:
        name = artifact["name"]
        lines.append(_row((_md(name), _value(receipt["source_schema_versions"][name]))))
    lines.extend(["", "Sabit dosya rolleri yeni path/URL takip etme yetkisi değildir. Owner Markdown ve manifest eşliği source-bound adapter'ın işidir; bu görünüm yalnız doğrulanmış kapalı üç modelden üretilir.", "",
                  "## 3. Üç ayrı kapsam ve sayım paydası", "", "### Kaynak Phase39 QUERY sonucu: altı sayım", ""])
    _counts(lines, _SOURCE_COUNT_LABELS, receipt["source_counts"])
    lines.extend(["", "### Queue: seçilen bütün reference paketleri ve gerçek pending işler", ""])
    _counts(lines, _FOLLOWUP_COUNT_LABELS, queue["counts"])
    lines.extend(["", "### Handoff: yalnız işi olan referansların bütün paketleri ve aynı işler", ""])
    _counts(lines, _FOLLOWUP_COUNT_LABELS, handoff["counts"])
    lines.extend([
        "", "Receipt source_counts gerçek Phase39 QUERY.counts altılısıdır; eski receipt'in inherited visible altılısı, pair onlusu veya global/bloke toplamlar değildir. Queue/handoff yedi sayımında distinct File ID ve candidate bütün seçili projection'ları sayar; pending task sayımı yalnız benzersiz gerçek missing binding'lerden gelir. Handoff sayımları kendi paketlerinden yeniden türetilir; işi olmayan referansların paketleri aktarılmaz.", "",
        "## 4. Hazırlanan queue işleri", "",
        "Task ID yerel deterministik sıra etiketidir; global kimlik/producer imzası değildir. Her missing projection için gerçek supporting triple gerekir. Desteksiz missing, duplicate/çelişkili veya ambiguous binding bütün isteği reddeder; sessiz seçim ya da kısmi başarı yoktur. Present projection için missing işi üretilmez.", "",
    ])
    _tasks(lines, queue["followup_tasks"])
    lines.extend(["", "prepared_unassigned ve not_observed açık iş talebini anlatır. İnsan/reviewer/assignee uydurulmaz; gönderme, atama, onay, kabul, fulfilment veya dosya toplama yetkisi yoktur.", "",
                  "## 5. Queue içindeki bütün izinli reference paketleri", ""])
    _packets(lines, queue["reference_packets"])
    lines.extend([
        "", "## 6. Ayrı analyst handoff", "",
        "Handoff yerel request reference: " + _md(handoff["request_reference"]),
        "Handoff canonical queue SHA256: " + _md(handoff["queue_sha256"]), "",
        "Queue SHA256 doğrulanmış queue'nun canonical JSON byte kimliğidir; producer authentication, imza, attestation veya görev yetkisi değildir. Handoff bütün queue işlerini aynı ID/binding/durumla taşır ve yalnız bu işlerin referansları için bütün izinli beş alanlı packet'ı korur. Aşağıdaki handoff kendi açık iş bağlamını içerir.", "",
    ])
    _tasks(lines, handoff["handoff_tasks"])
    _packets(lines, handoff["reference_packets"])
    lines.extend([
        "", "Kayıtlı missing projection byte/hash alanları null kalır. Null; count sıfırı, boş string veya sıfır-byte file değildir. Bütün 11 projection alanı, sıra, tür, observation/comparison kimliği ve upstream limitation kodları korunur. Eski fresh kodu yeni source observation veya TTL garantisi sağlamaz.", "",
        "## 7. Trust, receipt ve inspector sınırı", "",
        "Receipt content_scope: " + _md(receipt["content_scope"]),
        "Queue sınırlamaları: " + _items(queue["limitations"]),
        "Handoff sınırlamaları: " + _items(handoff["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "demo_only=true; kapalı trust_flags: " + "; ".join(_md(flag) + "=" + _md(queue["trust_flags"][flag]) for flag in FALSE_FLAGS) + ".", "",
        "Yeni inspector yalnız beş yeni queue/handoff/receipt/summary/manifest dosyasının kapalı modellerini, task/binding/missing/full-packet/count/null ilişkisini, canonical queue hash'ini, Markdown ve dört payload byte bağını inceler. Phase39 veya eski source dosyalarını yeniden açmaz. content_consistent yalnız bu yeni beş çıktının iç tutarlılığıdır; missing observation, takip gerekliliği, producer veya source doğruluğunu bağımsız kanıtlamaz.", "",
        "Hash bağları imza değildir; tutarlı dosyalar birlikte değiştirilip yeniden hash'lenebilir. Görev hazırlanması insan kabulü/atama veya collection authorization oluşturmaz. Source freshness, Phase31 guard, ownership, compiler/module closure, fiziksel dosya ve güvenlik ilişkisi doğrulanmaz; human/legal/customer/production/release yetkisi kazanılmaz.", "",
        "Bloke/eşleşmeyen full packet/olumlu child metadata, raw kaynak/path, credential veya gerçek kişi bilgisi aktarılmaz. ID ve hash hassas olabilir; minimizasyon şifreleme/anonimlik değildir. Owner kod bağımlılığı eski runtime/veri erişimi ya da ikinci host kabulü değildir.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8/BOM, yanlış digest/schema/unknown reference, duplicate/ambiguous binding, birden fazla veya sıfır missing record, değiştirilmiş witness, limit/permission/crash/partial write/repeat determinism/ikinci offline host; gerçek analist kabulü/ataması, source reobservation/dosya toplama, source freshness/Phase31 guard, compiler/module closure/ownership/native/producer/human/legal/customer/release. Koruma kodu runtime kabulü değildir. Test/runner/coverage/typecheck/build/install ve Phase19 file:// UI kabulü beklemededir; engel aşılmaz.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("followup_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_followup_summary",)
