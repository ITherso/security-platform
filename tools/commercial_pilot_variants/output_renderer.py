"""Pure bounded comparison of declared source scope, never a build/release verdict."""
from __future__ import annotations

from collections import Counter
import html

from .variant_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 512 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_EXPOSURES = {
    "explicit_component_link": "Açık dependency–component bağı",
    "declared_source_scope": "Tek potansiyel component'in kaynak kapsamı",
    "shared_or_ambiguous_scope": "Paylaşılan veya belirsiz kaynak kapsamı",
    "unattributed_record": "Seçili component'e atfedilemeyen kayıt",
    "excluded_context_record": "Kaynakta excluded backend-context",
    "insufficient_dependency_evidence": "Yetersiz dependency kanıtı",
}
_RELATIONS = {
    "selected_component": "Seçilmiş component",
    "not_selected_component": "Seçilmemiş component",
    "related_dependency_scope": "Potansiyel kaynak ilişkili dependency",
    "unattributed_dependency": "Atfedilemeyen dependency",
    "excluded_context": "Excluded backend-context",
    "candidate_scope_unassigned": "Candidate düzeyinde atanmamış karar kapısı",
}


def _md(value: object) -> str:
    return "".join("&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def render_summary(analysis: dict, dependencies: dict, licenses: dict) -> bytes:
    """Validate projections, preserve all D/L records, and produce inert text."""
    validate_documents(analysis, dependencies, licenses)
    variants = analysis["variants"]
    catalog = {row["component_id"]: row for row in analysis["component_catalog"]}
    license_by_key = {row["source_key"]: row for row in licenses["records"]}
    reference = analysis["source_reference"]
    counts = analysis["source_counts"]
    relation_counts = Counter(row["relation"] for row in dependencies["records"])
    unknown = [row for row in licenses["records"] if row["base_declared_license"] is None
               or row["base_evidence_level"] == "conflicting_declarations"]
    present = [row for row in licenses["records"] if row["evidence_status"] == "evidence_present"]
    lines = ["# Pilot kapsamı ve dependency exposure karşılaştırması", "", analysis["demo_label"], "",
             "- Yerel candidate referansı: " + _md(analysis["candidate_reference"]),
             "- Birinci taraf kaynak bileşeni: " + str(counts["component_count"]),
             "- Global özgün dependency kaydı: " + str(len(dependencies["records"])),
             "- Ayrı kaynak lisans kaydı: " + str(len(licenses["records"])),
             "- Eski lisans etiketi unknown/çelişkili: " + str(len(unknown)),
             "- Phase25'te yeni kanıtı bağlı kayıt: " + str(len(present)),
             "- Phase25'te yeni kanıtı eksik kayıt: " + str(counts["missing_evidence_record_count"]), "",
             "Dependency kayıtları ile lisans subject'leri aynı envanter değildir. Aşağıdaki sayımlar bu seçilmiş kaynak kayıtları içindir; benzersiz yayınlanmış paket, müşteri veya tamamlanmış hukukî inceleme sayısı değildir.", "",
             "## 1–3. Seçilen, eklenen ve ortak birinci taraf kaynaklar", "",
             "Varyant kimlikleri yerel karar destek etiketidir. Gerçek SKU, müşteri paketi, çalıştırılabilir binary, dağıtım içeriği veya pilot GO değildir.", ""]
    for variant in variants:
        lines.extend(["### " + _md(variant["variant_id"]) + " — " + _md(variant["label"]), "",
                      _md(variant["description"]), "",
                      "- Seçilen component sayısı: " + str(len(variant["selected_component_ids"])),
                      "- Seçilen gerçek id'ler: " + _items(variant["selected_component_ids"]),
                      "- Seçilmemiş gerçek id'ler: " + _items(variant["not_selected_component_ids"]), "",
                      "| Component | Rol | Kaynak sürüm beyanı | Phase25 L ref | Eski lisans | Yeni kanıt / review |",
                      "| --- | --- | --- | --- | --- | --- |"])
        for component_id in variant["selected_component_ids"]:
            component = catalog[component_id]
            evidence = license_by_key[component["license_source_key"]]
            lines.append(_row((_md(component_id), _md(component["role"]),
                               _md(component["version_declaration"] or "not_declared"),
                               _md(evidence["source_license_id"]), _md(evidence["base_declared_license"] or "unknown"),
                               _md(evidence["evidence_status"] + " / " + evidence["review_status"]))))
        lines.extend(["", "Sürüm beyanı kaynak metadata'sıdır. Platform project sürümü standalone helper release sürümü değildir. Seçilmeyen component gerçek binary'den çıkarılmış sayılmaz.", ""])
    for comparison in analysis["comparisons"]:
        lines.extend(["### " + _md(comparison["left"] + " / " + comparison["right"]), "",
                      "- Yalnız solda: " + _items(comparison["only_left_component_ids"]),
                      "- Yalnız sağda: " + _items(comparison["only_right_component_ids"]),
                      "- Ortak: " + _items(comparison["shared_component_ids"]),
                      "- Dependency kaynak sınıfı değişen satır: " + str(comparison["dependency_classification_change_count"]), "",
                      "Bu farklar component seçimi ve kaynak sınıfı farkıdır. Ek transitive dependency veya runtime paket farkı çıkarılmaz. Sınıfların aynı kalması eşit dependency closure veya lisans kapsamı kanıtı değildir.", ""])
    lines.extend(["## 4–6. Kanıtlanan kaynak ilişkisi, declaration/lock ve bilinmeyen closure", "",
                  "Phase24 v1'de explicit dependency–component owner bağı yoktur. Manifest F referansının component source_file_refs içinde bulunması yalnız potansiyel kaynak ilişkisi oluşturur. Aynı repository veya ad explicit bağ değildir.", "",
                  "- Manifest declaration satırı: " + str(relation_counts["direct_declaration"]),
                  "- Lock satırı: " + str(relation_counts["lock_record"]), "",
                  "Lock satırları bütün workspace'e ait olabilir. Feature/dev/target/runtime aktivasyonu ve transitive closure çözümlenmez. Missing/unknown kaynak türü veya sürüm korunur; ilişki eksikliği dependency'nin kesin yokluğu değildir.", "",
                  "| Exposure sınıfı | Sınırlı anlamı |", "| --- | --- |"])
    for code, label in _EXPOSURES.items():
        lines.append(_row((_md(code), label)))
    lines.extend(["", "Excluded backend-context helper manifest F ilişkisine göre önceliklidir; bu kayıtlar helper runtime dependency'si yapılmaz. Tek seçili potansiyel source ilişkisi declared_source_scope, birden fazla potansiyel ilişki shared_or_ambiguous_scope, seçilmiş potansiyel ilişki yokluğu unattributed_record olur. Eksik referans kapalı hatadır. Bu kurallar build inclusion değildir.", ""])
    for variant in variants:
        lines.extend(["### Exposure — " + _md(variant["variant_id"]), "",
                      "Her özgün D kaydı bu varyantta tek sınıftadır; toplam global kaynak satır sayısına eşittir. Varyant üyelikleri global kaydı çoğaltmaz.", ""])
        for row in variant["dependency_exposure_counts"]:
            lines.append("- " + _EXPOSURES[row["classification"]] + ": " + str(row["record_count"])
                         + " — " + _md(row["classification"]))
    lines.extend(["", "## 7–9. Mevcut lisans kanıtları, unknown durumları ve subject kapsamı", "",
                  "Eski lisans beyanı, yeni evidence durumu ve insan kararı ayrıdır. İki scoped MIT beyanı bulunması, iki yeni kanıt bulunduğu anlamına gelmez. Yeni tek LICENSE bağı yalnız gerçek L0001 subject'inde kalır; L0002, helper veya Rust dependency'lerine yayılmaz. Yeni kanıt eksikliği, eski bilinen MIT beyanını silmez.", "",
                  "| Yeni evidence bulunan L ref | Subject / ad | Eski lisans | Kaynak içinde evidence / review |",
                  "| --- | --- | --- | --- |"])
    for row in present:
        lines.append(_row((_md(row["source_license_id"]), _md(row["subject_id"] + " / " + row["name"]),
                           _md(row["base_declared_license"] or "unknown"),
                           _md(row["evidence_status"] + " / " + row["review_status"]))))
    lines.extend(["", "### Taşınan evidence metadata'sı", "",
                  "| Evidence | Tür | Dosya var | Bayt | SHA256 | Kaynak doğrulama |",
                  "| --- | --- | --- | ---: | --- | --- |"])
    for row in licenses["evidence_catalog"]:
        lines.append(_row((_md(row["evidence_id"]), _md(row["kind"]), "true" if row["file_present"] else "false",
                           str(row["bytes"]) if row["bytes"] is not None else "—", _md(row["sha256"] or "not_read"),
                           "source_verified=false")))
    lines.extend(["", "Belgenin byte kimliği, lisansın o subject'e uygulanabilirliği, producer kimliği ve hukukî dağıtım izni ayrı olgulardır. Phase26 yeni lisans belgesi okumaz veya bağlamaz. Eksik evidence olayı lisans çelişkisi değildir; farklı içerik veya literal etiket otomatik hukukî uyumluluk kararı değildir.", "",
                  "- Phase25 bağlama olay kaydı: " + str(licenses["conflict_summary"]["conflict_count"]), ""])
    for item in licenses["conflict_summary"]["by_category"]:
        lines.append("- " + _md(item["category"]) + ": " + str(item["record_count"]))
    for variant in variants:
        summary = variant["license_summary"]
        lines.extend(["", "### Lisans paydaları — " + _md(variant["variant_id"]), "",
                      "- Global kaynak lisans kaydı: " + str(summary["global_source_record_count"]),
                      "- Global unknown/çelişkili lisans: " + str(summary["global_unknown_license_count"]), "",
                      "| İlişki | Kayıt | Unknown | Yeni kanıt var | Yeni kanıt eksik | İnsan incelemesi gerekli | Belirsiz / çelişkili / unsupported / unverified |",
                      "| --- | ---: | ---: | ---: | ---: | ---: | --- |"])
        for row in summary["by_relation"]:
            lines.append(_row((_RELATIONS[row["relation"]], str(row["record_count"]), str(row["unknown_license_count"]),
                               str(row["evidence_present_record_count"]), str(row["missing_evidence_record_count"]),
                               str(row["human_review_required_record_count"]),
                               " / ".join(str(row[key]) for key in ("ambiguous_record_count", "conflicting_record_count",
                                                                     "unsupported_record_count", "unverified_source_record_count")))))
    lines.extend(["", "Unknown veya review_required kayıt varyant seçimiyle resolved, approved ya da not_required olmaz. Seçilmemiş, unattributed ve excluded kaydın lisans incelemesi görünür kalır. Aşağıdaki tam kaynak dizini hangi kaydın hâlâ unknown olduğunu ayrıca gösterir.", "",
                  "## 10–11. Açık release/runtime engelleri ve onaylanmayan sonuç", "",
                  "Daha az component daha güvenli, hukukî olarak uygun veya production-ready demek değildir. Sekiz helper seçimi gerçek paket veya belirli lisans yükümlülüğü farkını kanıtlamaz. Exposure closure değildir; candidate scope gerçek artefact değildir; evidence present redistribution yetkisi değildir.", ""])
    for variant in variants:
        blockers = variant["open_blockers"]
        lines.extend(["### Açık engeller — " + _md(variant["variant_id"]), "",
                      "- Korunan kaynak blocker kaydı: " + str(blockers["source_blocker_count"]), ""])
        for row in blockers["by_code"]:
            lines.append("- " + _md(row["code"]) + ": " + str(row["record_count"]))
        lines.extend(["", "| Kaynak ilişkisi | Açık blocker kaydı |", "| --- | ---: |"])
        for row in blockers["by_relation"]:
            lines.append(_row((_RELATIONS[row["relation"]], str(row["blocker_count"]))))
        lines.extend(["", "demo_only=true; " + "; ".join(flag + "=false" for flag in FALSE_FLAGS) + ".", ""])
    lines.extend(["Kaynak blocker'ları seçilmemiş/excluded/belirsiz kategoriye geçince otomatik kapanmaz. Candidate build/runtime, veri işleme ve release yetkisi kapıları açıktır. Kaynak/hash tutarlılığı hukukî inceleme, üretici, build, binary–source bağı veya pilot GO sağlamaz. Phase14 talep/ödeme isteği not_validated kalır; fiyatlandırma veya müşteri uygunluğu önerilmez.", "",
                  "## Kaynak içerik kimlikleri", "",
                  "Pinler eski inventory'nin deklaratif beyanıdır; git/producer/build attestation değildir.",
                  "- Termivar pin'i: " + _md(reference["source_commits"]["termivar"]),
                  "- Platform pin'i: " + _md(reference["source_commits"]["platform"]), "",
                  "| Kaynak grubu / rol | Şema | Bayt | SHA256 |", "| --- | --- | ---: | --- |"])
    for group, roles in (("composition_sources", ("inventory", "dependencies", "constraints", "summary", "manifest")),
                         ("evidence_sources", ("ledger", "queue", "conflicts", "summary", "manifest"))):
        for role in roles:
            row = reference[group][role]
            lines.append(_row((_md(group + " / " + role), _md(row["schema_version"] or "Markdown"),
                               str(row["bytes"]), _md(row["sha256"]))))
    lines.extend(["", "## Özgün dependency kayıtlarının tamamı", "",
                  "Her D ref tek satırdır; potansiyel component adları ownership veya build inclusion değildir. Tam eski row digest ve artefact kimliği dependency-exposure.json içinde korunur.", "",
                  _row(("D ref", "Ad / ekosistem / sürüm", "Declaration veya lock", "Manifest id", "Kaynak türü / directness",
                        "Potansiyel component", *(_md(variant["variant_id"]) + " exposure" for variant in variants))),
                  _row("---" for _ in range(6 + len(variants)))])
    for row in dependencies["records"]:
        exposures = {item["variant_id"]: item for item in row["exposures"]}
        lines.append(_row((_md(row["dependency_id"]), _md(row["name"] + " / " + row["ecosystem"] + " / " + (row["version"] or "unknown")),
                           _md(row["relation"]), _md(row["manifest_id"]), _md(row["source_type"] + " / " + row["directness"]),
                           _items(row["potential_component_ids"]),
                           *(_md(exposures[variant["variant_id"]]["classification"]) for variant in variants))))
    lines.extend(["", "## Lisans subject'lerinin tamamı", "",
                  "Bu tablo önceki unknown ve review durumlarını korur. Yerel source key source artefact/pointer/digest ilişkisini belirtir; global package veya vendor kimliği değildir. Tam identity/ref/binding ayrıntısı license-readiness.json içindedir.", "",
                  _row(("L ref", "Subject / ad", "Eski lisans", "Yeni evidence / review",
                        *(_md(variant["variant_id"]) + " ilişkisi" for variant in variants), "Yerel source key")),
                  _row("---" for _ in range(5 + len(variants)))])
    for row in licenses["records"]:
        relations = {item["variant_id"]: item["relation"] for item in row["variant_relations"]}
        label = row["base_declared_license"] or "unknown"
        if row["base_evidence_level"] == "conflicting_declarations":
            label += " / conflicting_declarations"
        lines.append(_row((_md(row["source_license_id"]), _md(row["subject_type"] + " " + row["subject_id"] + " / " + row["name"]),
                           _md(label), _md(row["evidence_status"] + " / " + row["review_status"]),
                           *(_md(relations[variant["variant_id"]]) for variant in variants), _md(row["source_key"]))))
    lines.extend(["", "## Mahremiyet ve inspector sınırı", "",
                  "Özet kapalı metadata'dır; raw JSON, source body, tam lisans metni, credential, özel kullanıcı/müşteri verisi veya mutlak root yolu taşımaz. Minimizasyon secret detection, redaksiyon, şifreleme veya anonimlik garantisi değildir. Yeni HTML/web arayüzü ve dış link oluşturulmaz.", "",
                  "Inspector yalnız beş açık yeni dosyadaki sözleşme, referans/sayım, F-association, saf exposure/comparison/readiness/Markdown ve manifest byte bağını inceler. Eski Phase24/25, evidence, root, git veya package cache tekrar okunmaz. Projeksiyondan raw primary-row doğruluğu/producer/bağımsız source authority yeniden doğrulanamaz. İç tutarlılık otomatik test veya gerçek kabul değildir.", "",
                  "## NOT_RUN — açık kabul kapıları", "",
                  "Malformed/duplicate JSON, hostile encoding, yanlış kaynak/binding digest, değiştirilmiş ledger, sahte/çelişkili kanıt, geçersiz kimlik, limit aşımı, symlink/reparse/hardlink, permission/race/crash/kısmi yazma/power loss, tekrar determinism, gerçek dependency resolution, native build closure, binary analizi, hukukî lisans incelemesi, runtime/production, müşteri pilotu ve ödeme isteği kabulü çalıştırılmadı. Test/runner/coverage/typecheck/build, resolver, native runtime, ağ, release veya dağıtım yapılmadı.", ""])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if not 0 < len(raw) <= MAX_SUMMARY_BYTES:
        raise InputError("pilot_variant_summary_size_limit")
    return raw


__all__ = ("MAX_SUMMARY_BYTES", "render_summary")
