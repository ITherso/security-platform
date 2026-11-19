"""Inert, bounded Markdown view of a validated reconciliation report and inbox."""
from __future__ import annotations

import html

from reconciliation_contracts import (
    DEMO_LABEL, MAX_SUMMARY_BYTES, NON_CLAIMS, PRESENCE_SUMMARY_FIELDS, fail, validate_inbox, validate_report,
)

_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")


def _md(value: object) -> str:
    if value is None:
        return "null"
    text = str(value).lower() if type(value) is bool else str(value)
    return "".join("&#" + str(ord(char)) + ";" if char in _PUNCTUATION or ord(char) < 32 or 127 <= ord(char) <= 159
                   else html.escape(char, quote=True) for char in text)


def _row(*cells: object) -> str:
    return "| " + " | ".join(_md(cell) for cell in cells) + " |"


def render_reconciliation_summary(report: dict, inbox: dict) -> bytes:
    report, inbox = validate_report(report), validate_inbox(inbox)
    if report["capsule"] != inbox["capsule"] or report["eligibility"]["status"] != inbox["eligibility_status"]:
        fail("summary_report_inbox_correspondence")
    eligibility = report["eligibility"]
    archive = report["archive"]
    lines = [
        "# Offline task capsule reconciliation", "", DEMO_LABEL, "",
        "Bu çıktı, açıkça verilen tek bir Phase43 portable capsule'ın yerel ve güvenilmeyen (untrusted) içe alınmasını açıklar. "
        "Geçerli ZIP yapısı veya eşleşen hash, üretici kimlik doğrulaması, güvenli aktarım, kaynak doğruluğu, görev ataması, "
        "onay, yürütme veya gönderim değildir. Sonuç yalnız yapısal ve manuel inceleme sınıflandırmasıdır.", "",
        "## 1. Sonuç", "",
        "- Uygunluk durumu: **" + _md(eligibility["status"]) + "**",
        "- Manuel inceleme uygunluğu: " + _md(eligibility["manual_review"]),
        "- Manuel inceleme gerekliliği: " + _md(eligibility["manual_review_requirement"]),
        "- Inbox yaşam döngüsü aşaması: " + _md(inbox["lifecycle_stage"]),
        "- Inbox güven durumu: " + _md(inbox["trust_state"]),
        "- Karantinadaki inbox kaydına alınan görev sayısı (kabul, onay veya atama değildir): "
        + _md(inbox["admitted_task_count"]),
        "- Request reference: " + _md(report["request_reference"]),
        "- Gerekçe bulguları: " + (", ".join(_md(item) for item in eligibility["basis_finding_ids"]) or "yok"), "",
        "## 2. Capsule kimliği ve yapısal inceleme", "",
        "- Capsule byte / SHA256: " + _md(report["capsule"]["bytes"]) + " / " + _md(report["capsule"]["sha256"]),
        "- Arşiv durumu: " + _md(archive["archive_state"]) + "; container kararı: " + _md(archive["container_verdict"]),
        "- Üye sayısı: " + _md(archive["member_count"]) + " (listelenen " + _md(archive["listed_member_count"])
        + ", listelenmeyen " + _md(archive["omitted_member_count"]) + ")",
        "- Bildirilen açılmış boyut: " + _md(archive["declared_expanded_bytes"]) + "; üye sırası: "
        + _md(archive["member_order"]) + "; arşiv yorumu: " + _md(archive["archive_comment"]),
        "- Phase43 owner reader: " + _md(report["phase43_reader"]["compatibility"])
        + ("" if report["phase43_reader"]["owner_rejection_code"] is None
           else " (" + _md(report["phase43_reader"]["owner_rejection_code"]) + ")"), "",
        "| Konum | Ad | Ad durumu | Tehlikeler | Bildirilen boyut | Sıkıştırma | Tür | Boyut durumu |",
        "| ---: | --- | --- | --- | ---: | --- | --- | --- |",
    ]
    for item in report["members"]:
        lines.append(_row(item["position"], item["name"] if item["name"] is not None else "withheld sha256 " + item["name_sha256"],
                          item["name_state"], ",".join(item["name_hazards"]) or "-", item["declared_size"],
                          item["compression"], item["entry_type"], item["size_state"]))
    lines.extend(["", "| Gerekli üye | Varlık |", "| --- | --- |"])
    lines.extend(_row(item["name"], item["presence"]) for item in report["required_members"])
    lines.extend(["", "| Üye | İçerik | Şema | Canonical | Owner sözleşmesi | Owner kodu |",
                  "| --- | --- | --- | --- | --- | --- |"])
    for item in report["member_contents"]:
        lines.append(_row(item["name"], item["content_state"], item["schema_state"], item["canonical_encoding"],
                          item["owner_contract"], item["owner_rejection_code"] or "-"))
    manifest = report["manifest_correspondence"]
    lines.extend(["", "Inner manifest: " + _md(manifest["manifest_state"]) + "; owner manifest eşliği: "
                  + _md(manifest["fixed_fields"]) + "; bilinmeyen/duplicate/bozuk kayıt: "
                  + _md(manifest["unknown_entry_count"]) + "/" + _md(manifest["duplicate_entry_count"]) + "/"
                  + _md(manifest["malformed_entry_count"]), "",
                  "| Payload üyesi | Bildirilen byte | Gerçek byte | Sonuç |", "| --- | ---: | ---: | --- |"])
    for item in manifest["entries"]:
        lines.append(_row(item["member"], item["declared_bytes"], item["actual_bytes"], item["result"]))
    declaration = report["task_declaration"]
    identity = report["capsule_identity"]
    lines.extend([
        "", "## 3. Bildirilen ve temsil edilen görev kimliği", "",
        "- Bildirilen şema: " + _md(identity["declared_schema"]),
        "- tasks alanı: " + _md(declaration["tasks_field_state"]) + "; bildirilen sayı: "
        + _md(declaration["declared_task_count"]) + "; gerçek kayıt: " + _md(declaration["actual_task_entry_count"])
        + "; yorumlanan: " + _md(declaration["interpreted_task_entry_count"]) + "; tutarlılık: "
        + _md(declaration["consistency"]),
        "- Temsil durumu: " + _md(identity["represented_state"]) + "; bildirilen ve temsil edilen eşliği: "
        + _md(identity["claimed_vs_represented"]),
        "- Kaynak beyanı: register " + _md(identity["source_declaration"]["source_phase42_register_sha256"])
        + ", manifest " + _md(identity["source_declaration"]["source_phase42_manifest_sha256"])
        + ", request " + _md(identity["source_declaration"]["request_reference"]), "",
        "| Konum | task_id | reference_id | candidate_id | file_id | binding_digest |",
        "| ---: | --- | --- | --- | --- | --- |",
    ])
    for item in identity["declared_tasks"]:
        lines.append(_row(item["position"], item["task_id"], item["reference_id"], item["candidate_id"],
                          item["file_id"], item["binding_digest"]))
    lines.extend(["", "Alan varlık özeti (null, boş metin, boş liste, false ve 0 ayrı tutulur):", ""])
    for key in PRESENCE_SUMMARY_FIELDS:
        paths = report["field_presence_summary"][key]
        lines.append("- " + _md(key) + " (" + str(len(paths)) + "): " + (", ".join(_md(p) for p in paths) or "-"))
    reconciliation = report["local_reconciliation"]
    lines.extend([
        "", "## 4. Yerel mutabakat", "",
        "- Yerel referans modu: " + _md(report["local_reference"]["mode"]),
        "- Mutabakat durumu: " + _md(reconciliation["state"]), "",
        "| Konu | Görev | Phase42 araması | Phase43 araması |", "| --- | --- | --- | --- |",
    ])
    for item in reconciliation["task_lookups"]:
        lines.append(_row(item["subject"], item["task_id"], item["phase42_lookup"], item["phase43_lookup"]))
    lines.extend(["", "| Konu | Alan | Yerel kaynak | Capsule durumu | Yerel değer açıklaması | Sonuç |",
                  "| --- | --- | --- | --- | --- | --- |"])
    for item in reconciliation["comparisons"]:
        lines.append(_row(item["subject"], item["field"], item["reference_source"], item["capsule_value_state"],
                          item["local_value_disclosure"], item["result"]))
    lines.extend(["", "Değerlerin tamamı JSON raporundadır. Yerel değer yalnız capsule değeriyle aynıysa veya Phase43 "
                  "kaydında daha önce açıklanmışsa yazılır; aksi halde withheld kalır.", "",
                  "## 5. Bulgular", "", "| Bulgu | Önem | Kategori | Gözlem |", "| --- | --- | --- | --- |"])
    for item in report["findings"]:
        lines.append(_row(item["finding_id"], item["severity"], item["category"], item["observed_condition"]))
    lines.extend(["", "Her bulgunun beklenen koşulu ve iyileştirme önerisi JSON raporundadır. Öneriler bir işlemin "
                  "yapıldığını belirtmez.", "", "## 6. Güven sınırı ve NOT_RUN", "",
                  "Aşağıdaki iddiaların hepsi false'tur: " + ", ".join(_md(flag) for flag in NON_CLAIMS) + ".", "",
                  "Sınırlamalar: " + ", ".join(_md(item) for item in report["limitations"]) + ".", "",
                  "NOT_RUN: üretici kimlik doğrulaması, imza, anti-replay, güvenilir zaman damgası, güvenli aktarım, "
                  "gerçek ikinci host aktarımı, görev gönderimi/ataması/onayı/yürütmesi/tamamlanması, response gönderimi, "
                  "kaynak yeniden gözlemi ve insan/hukuk/müşteri/production kabulü.", ""])
    raw = ("\n".join(lines) + "\n").encode("utf-8", "strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        fail("summary_size")
    return raw


__all__ = ("render_reconciliation_summary",)
