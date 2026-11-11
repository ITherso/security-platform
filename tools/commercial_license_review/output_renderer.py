"""Pure bounded Markdown: original license labels and fresh bindings stay distinct."""
from __future__ import annotations

from collections import Counter
import html

from .evidence_contracts import InputError, validate_documents


MAX_SUMMARY_BYTES = 512 * 1024
_FALSE_FLAGS = (
    "license_review_completed", "redistribution_authorized", "release_authorized",
    "production_ready", "build_verified", "runtime_verified", "producer_verified",
    "human_review_verified",
)
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_GROUPS = {
    "conflicting_evidence": "Çelişki bildirimi bulunan kanıt",
    "ambiguous_binding": "Belirsiz kaynak bağı",
    "missing_evidence": "Bu bağlama kapsamında kanıt eksik",
    "evidence_present_review_pending": "Kanıt bağlı, insan incelemesi bekliyor",
    "unsupported_evidence": "Desteklenmeyen kanıt",
}
_CATEGORIES = {
    "duplicate_content": "Aynı kayıt için tekrarlanan içerik",
    "different_content": "Aynı kayıt için farklı içerik",
    "conflicting_license_declarations": "Farklı lisans beyanları",
    "ambiguous_binding": "Belirsiz kaynak bağı",
    "source_not_verified": "Kaynağı doğrulanmamış belge",
    "evidence_missing": "Açık istekte eksik kanıt",
    "evidence_hash_mismatch": "Beklenen ve okunan hash farklı",
    "unsupported_evidence": "Desteklenmeyen kanıt",
    "source_selector_mismatch": "Kaynak kayıt seçicisi eşleşmiyor",
}


def _md(value: object) -> str:
    # Render bounded metadata as text, never Markdown links, HTML or autolinks.
    return "".join("&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def render_summary(ledger: dict, queue: dict, conflicts: dict) -> bytes:
    """Validate and show every source record; never load evidence or old outputs."""
    validate_documents(ledger, queue, conflicts)
    subjects = ledger["source_subjects"]
    by_key = {row["source_key"]: row for row in subjects}
    records = {row["source_key"]: row for row in ledger["records"]}
    queued = {row["source_key"]: row for row in queue["records"]}
    unknown = sum(row["base_declared_license"] is None
                  or row["base_evidence_level"] == "conflicting_declarations" for row in subjects)
    known = len(subjects) - unknown
    known_without_new_file = sum(
        row["base_declared_license"] is not None
        and row["base_evidence_level"] != "conflicting_declarations"
        and records[row["source_key"]]["evidence_status"] == "evidence_missing"
        for row in subjects)
    scopes = Counter(row["product_scope"] for row in subjects)
    statuses = Counter(row["evidence_status"] for row in ledger["records"])
    binding_statuses = Counter(row["status"] for row in ledger["bindings"])
    label_counts = Counter(row["base_declared_license"] for row in subjects
                           if row["base_declared_license"] is not None)
    reference = ledger["composition_reference"]
    lines = ["# Çevrimdışı lisans kanıtı ve inceleme kuyruğu", "", ledger["demo_label"], "",
             "- Phase24 aday referansı: " + _md(reference["candidate_reference"]),
             "- Korunan kaynak lisans kaydı: " + str(len(subjects)),
             "- Phase24'te lisans etiketi bilinmeyen veya çelişkili kayıt: " + str(unknown),
             "- Phase24'te lisans etiketi bildirilen kayıt: " + str(known),
             "- Dosyası mevcut evidence referansı: " + str(ledger["counts"]["evidence_file_count"]),
             "- Kaynak içinde yeni kanıtı bağlanan kayıt: " + str(statuses["evidence_present"]),
             "- Bu bağlama kapsamında yeni kanıtı bulunmayan kayıt: " + str(statuses["evidence_missing"]), "",
             "Bilinmeyen lisans sayısı ile yeni kanıtın eksik olduğu kayıt sayısı farklıdır. Phase24 lisans beyanları değiştirilmez. Bir kayda bu turda dosya seçilmemesi, önceki bilinen lisans etiketini silmez; önceki metadata da yeni dosya seçilmiş gibi gösterilmez.", "",
             "- Lisans etiketi bilinen ama bu bağlama kapsamında yeni kanıtı olmayan kayıt: " + str(known_without_new_file),
             "- Kaynakta bildirilen etiketler: " + (", ".join(_md(label) + ": " + str(count)
                                                              for label, count in label_counts.items()) or "—"), "",
             "Kanıt dosyası veya MIT etiketi bulunması lisans koşullarının yorumlandığı, üreticinin doğrulandığı veya dağıtımın onaylandığı anlamına gelmez. Birinci taraf kanıtı üçüncü taraf dependency lisanslarına yayılmaz.", "",
             "## Kullanılan Phase24 içerik kimlikleri", "",
             "Bu beş kimlik seçilmiş eski dosyalarla ilişki kurar. Hash bir imza, vendor kimliği, build attestation veya hukukî kabul değildir. Phase24 dosyaları yeniden üretilmez ve güncellenmez.", "",
             "- Phase24'te bildirilen Termivar kaynak pin'i: " + _md(reference["source_commits"]["termivar"]),
             "- Phase24'te bildirilen platform kaynak pin'i: " + _md(reference["source_commits"]["platform"]),
             "Bu pinler eski inventory'nin kaynak beyanlarıdır; git kimliği, çalışma ağacı, üretici veya build bağımsız doğrulanmış sayılmaz.", "",
             "| Açık girdi rolü | Bayt | SHA256 |", "| --- | ---: | --- |"]
    for role in ("inventory", "dependencies", "constraints", "summary", "manifest"):
        item = reference[role]
        lines.append("| " + _md(role) + " | " + str(item["bytes"]) + " | " + _md(item["sha256"]) + " |")
    lines.extend(["", "## Seçilen yerel kanıtlar", "",
                  "Aşağıda dosya içeriği veya yolu bulunmaz. Evidence referansları, tür ve byte kimliği gösterilir. baseline_file_refs yalnız seçilmiş dosyanın Phase24 dosya metadata'sıyla içerik eşleşmesini belirtir; üretici veya hukukî yetki doğrulamaz.", "",
                  "| Evidence | Tür | Dosya var | Bayt | SHA256 | Hash ilişkisi | Biçim gözlemi | Gözlenen etiket | Phase24 dosya ref |",
                  "| --- | --- | --- | ---: | --- | --- | --- | --- | --- |"])
    for row in ledger["evidence_sources"]:
        lines.append("| " + " | ".join((
            _md(row["evidence_id"]), _md(row["kind"]), "true" if row["file_present"] else "false",
            str(row["bytes"]) if row["bytes"] is not None else "—", _md(row["sha256"] or "not_read"),
            _md(row["integrity_status"]), _md(row["format_status"]), _items(row["observed_license_labels"]),
            _items(row["baseline_file_refs"]),
        )) + " |")
    lines.extend(["", "Tüm evidence kaynaklarında source_verified=false korunur. Metadata beyanı tam lisans metni değildir. missing_evidence bir lisans türü değil, kanıt yokluğu kaydıdır. Beklenen hash uyumsuzluğu, yorumlanamayan biçim veya haricî belgenin varlığı kesin kaynak bağı oluşturmaz.", "",
                  "### Açık bağlama istekleri", "",
                  "Bağlama paket adına göre yapılmaz. İstek, gerçek Phase24 lisans kaydı, subject türü/kimliği ve primary row digest'ini birlikte seçer. Kaynak içi eşleşme bile yalnız o kayda aittir. Dependency'yi bildiren manifestin dosya kimliği, o dependency'nin lisansına uygulanabilirlik kanıtı değildir; böyle metadata veya declaring-manifest/lock dosyasının license-file diye seçilmesi belirsiz bağ olarak kalır.", "",
                  "| İstek | Evidence | Phase24 lisans kaydı | Subject | Durum | Eşleşen dosya ref | Nedenler |",
                  "| --- | --- | --- | --- | --- | --- | --- |"])
    for binding in ledger["bindings"]:
        subject = by_key[binding["source_key"]]
        lines.append("| " + " | ".join((
            _md(binding["request_id"]), _md(binding["evidence_id"]), _md(subject["source_license_id"]),
            _md(subject["subject_type"] + " " + subject["subject_id"] + " / " + subject["name"]), _md(binding["status"]),
            _md(binding["matched_source_file_ref"] or "not_matched"), _items(binding["reason_codes"]),
        )) + " |")
    lines.extend(["", "- Kaynak içinde doğrulanmış bağlama isteği: " + str(binding_statuses["binding_confirmed_within_source"]),
                  "- Açık istekte kanıt eksikliği: " + str(binding_statuses["evidence_missing"]),
                  "- Belirsiz veya kaynak doğrulaması bulunmayan kayıt: "
                  + str(statuses["binding_ambiguous"] + statuses["source_not_verified"]), "",
                  "## Salt okunur inceleme kuyruğu", "",
                  "- Benzersiz kaynak kaydı: " + str(queue["counts"]["unique_source_record_count"]),
                  "- Kuyruk satırı: " + str(queue["counts"]["queue_record_count"]),
                  "- Grup üyeliği toplamı: " + str(queue["counts"]["group_membership_count"]), "",
                  "Bir kaynak kaydı birden fazla inceleme nedeni taşıyabilir. Grup üyeliği toplamı benzersiz kayıt sayısı değildir. Gruplar ve deterministik sıra hukukî öncelik, risk skoru, görev ataması veya ticari önem değildir.", ""])
    for row in queue["counts"]["by_group"]:
        lines.append("- " + _GROUPS[row["group"]] + ": " + str(row["record_count"]) + " — " + _md(row["group"]))
    lines.extend(["", "### Kaynak kapsamı", "",
                  "- Önerilen kaynak bileşeni: " + str(scopes["proposed_source_component"]),
                  "- Seçili Termivar kaynak/dependency metadata kaydı: " + str(scopes["selected_source_metadata"]),
                  "- Yalnız excluded/backend-context: " + str(scopes["excluded_backend_context"]), "",
                  "Declaration ve lock kayıtları ayrı kaynak konumlarıdır; aynı paket adıyla birleştirilmez. Bu sayılar benzersiz yayınlanmış paket, müşteri, lisans sözleşmesi veya tamamlanmış inceleme sayısı değildir. Backend-context kaydı destek araçlarının runtime bağımlılığı veya adayın dağıtılacak bileşeni hâline gelmez.", "",
                  "## Bağlama olayları ve çakışmalar", "",
                  "- Bildirilen olay kaydı: " + str(conflicts["counts"]["conflict_count"]), "",
                  "Bu dosya eksik kanıt bildirimlerini de içerir; her olay lisans çelişkisi değildir. Farklı içerik otomatik hukukî uyumsuzluk değildir. Aynı lisans adı da aynı üretici veya eşdeğer belge anlamına gelmez. Çelişki sessizce çözülmez.", ""])
    for row in conflicts["counts"]["by_category"]:
        lines.append("- " + _CATEGORIES[row["category"]] + ": " + str(row["record_count"]) + " — " + _md(row["category"]))
    if not conflicts["conflicts"]:
        lines.extend(["", "Bu seçilmiş girdiler için olay kaydı üretilmedi. Bu sonuç bütün kanıtların hukukî açıdan uyumlu olduğunu kanıtlamaz."])
    for event in conflicts["conflicts"]:
        subject = by_key[event["source_key"]]
        lines.append("- " + _md(event["category"]) + "; " + _md(subject["source_license_id"] + " / " + subject["subject_id"])
                     + "; evidence: " + _items(event["evidence_refs"]) + "; istek: " + _items(event["request_refs"]))
    lines.extend(["", "## Bütün kaynak kayıtlarının izlenebilir görünümü", "",
                  "Her kaynak lisans kaydı aşağıda bir kez bulunur. Yerel binding key, eski dosya SHA256 + doğrulanmış JSON konumu + primary row digest'i + eski lisans kaydı ilişkisine bağlıdır. Gerçek paket yayını, vendor veya küresel kalıcı kimlik değildir. Tam digest ve kaynak metadata bağları license-evidence-ledger.json içinde korunur.", "",
                  "| Phase24 L ref | Subject / ad | Ekosistem / sürüm / kaynak türü | Ürün kapsamı | Phase24 lisans etiketi | Yeni evidence / review | Gruplar | Kaynak / lisans JSON konumu | Yerel binding key |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- | --- |"])
    for subject in subjects:
        record = records[subject["source_key"]]
        queue_row = queued[subject["source_key"]]
        base_label = subject["base_declared_license"] or "unknown"
        if subject["base_evidence_level"] == "conflicting_declarations":
            base_label += " / conflicting_declarations"
        lines.append("| " + " | ".join((
            _md(subject["source_license_id"]),
            _md(subject["subject_type"] + " " + subject["subject_id"] + " / " + subject["name"]),
            _md(subject["ecosystem"] + " / " + (subject["version"] or "unknown") + " / " + subject["source_type"]),
            _md(subject["product_scope"]), _md(base_label),
            _md(record["evidence_status"] + " / " + record["review_status"]), _items(queue_row["groups"]),
            _md(subject["source_json_pointer"] + " / " + subject["license_record_pointer"]),
            _md(subject["source_key"]),
        )) + " |")
    lines.extend(["", "Tüm kaynak kayıtlarında human_review_required=true ve phase24_license_review_required=true kalır. Yeni kanıt, Phase24 lisans beyanını veya release blocker'larını otomatik güncellemez. Kuyrukta gerçek reviewer, tarih, imza, owner, son tarih veya onay kararı yoktur.", "",
                  "## Güven, veri ve gerçek kabul sınırı", "",
                  "demo_only=true; " + "; ".join(flag + "=false" for flag in _FALSE_FLAGS) + ".", "",
                  "Bu araç lisans tarayıcısı, resolver, hukuki yorum motoru veya release sistemi değildir. Sadece açık yerel kanıtın byte kimliğini ve seçili kaynak kaydıyla sınırlı bağını gösterir. Lisans metni, ham JSON/kaynak kod, credential, özel kişi/müşteri bilgisi veya mutlak dosya yolu bu özete taşınmaz. Minimizasyon otomatik sır tespiti, redaksiyon ya da anonimlik garantisi değildir.", "",
                  "Inspector yalnız açık ledger/queue/conflicts/summary/manifest dosyalarının sözleşme, referans, byte/hash ve saf projeksiyon tutarlılığını inceler. Eski Phase24 girdilerini, kanıt dosyasını, repository köklerini veya git kimliğini yeniden okumaz. İç tutarlılık üretici doğrulaması, lisans incelemesi, build/runtime veya dağıtım kabulü değildir.", "",
                  "## NOT_RUN — açık kabul kapıları", "",
                  "Malformed/duplicate JSON; hostile Unicode/kontrol karakterleri; yanlış/eksik kaynak kimliği; sahte veya çelişen haricî kanıt; değiştirilmiş ledger; yanlış manifest/hash; boyut/kayıt limitleri; symlink/reparse/hardlink; okuma sırasında değişen kaynak; permission/race/crash/kısmi yazma/power loss; tekrarlı determinism; gerçek dependency çözümleme; gerçek lisans/uyumluluk/hukukî inceleme; imzalı binary ve gerçek release kabulü çalıştırılmadı. Kaynak incelemesi, sentetik üretim ve inspector sonucu otomatik test veya hukukî kabul değildir.", ""])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if not 0 < len(raw) <= MAX_SUMMARY_BYTES:
        raise InputError("license_evidence_summary_size_limit")
    return raw


__all__ = ("MAX_SUMMARY_BYTES", "render_summary")
