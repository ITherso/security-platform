"""Bounded Markdown product composition; no raw source bodies or executable view."""
from __future__ import annotations

from collections import Counter
import html

from .composition_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 512 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_ROLES = {"assessment_core": "Termivar assessment çekirdeği",
          "reporting_comparison": "Termivar raporlama ve karşılaştırma",
          "offline_support": "Ayrı çevrimdışı destek aracı"}
_BLOCKERS = {
    "license_review_required": "Yetkili lisans incelemesi gerekli",
    "dependency_license_unknown": "Dependency lisansı belirlenmemiş",
    "third_party_provenance_incomplete": "Üçüncü taraf provenance eksik",
    "binary_source_binding_missing": "Kabul edilmiş binary–source bağı yok",
    "build_acceptance_not_performed": "Build kabulü yapılmadı",
    "runtime_acceptance_not_performed": "Runtime kabulü yapılmadı",
    "data_handling_pending": "Veri işleme kapsamı kararı bekliyor",
    "release_authority_missing": "Release yetkisi yok",
}


def _md(value: object) -> str:
    text = str(value)
    # Entities render as text, preventing Markdown links, raw HTML, or autolinks.
    return "".join("&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in text)


def render_summary(inventory: dict, ledger: dict, constraints: dict) -> bytes:
    validate_documents(inventory, ledger, constraints)
    evidence = {(row["subject_type"], row["subject_id"]): row for row in ledger["license_evidence"]}
    dependencies = ledger["dependencies"]
    relation_counts = Counter(row["relation"] for row in dependencies)
    context_counts = Counter(row["review_scope"] for row in dependencies)
    unknown = sum(row["declared_license"] is None or row["evidence_level"] == "conflicting_declarations"
                  for row in ledger["license_evidence"])
    lines = ["# Çevrimdışı ürün bileşimi ve lisans hazırlığı", "", inventory["demo_label"], "",
             _md(inventory["candidate_label"]), "", "- Sentetik aday referansı: " + _md(inventory["candidate_reference"]),
             "- Birinci taraf kaynak bileşeni: " + str(len(inventory["components"])),
             "- Açıkça seçilmiş dosya metadata kaydı: " + str(len(inventory["files"])),
             "- Okunan seçili kaynak toplamı: " + str(inventory["counts"]["total_selected_source_bytes"]) + " bayt",
             "- Oluşturulan veya kabul edilen dağıtılabilir binary/installer/wheel: 0", "",
             "Bu ad mevcut ticari SKU veya yayın değildir. Envanter yalnız açıkça seçilmiş mevcut dosyaların kaynak metadata'sını tanımlar. Commit pinleri incelenmiş scope beyanıdır; git/build attestation veya binary eşleşmesi değildir.", "",
             "## Önerilen kaynak bileşimi", "",
             "Termivar kaynak çekirdeği ve raporlama kaynakları ile bağımsız Python destek araçları ayrı gösterilir. Destek araçları Termivar runtime'ının otomatik bağımlılıkları veya müşteriye dağıtılması zorunlu bileşenler değildir.", ""]
    for component in inventory["components"]:
        license_row = evidence[("component", component["component_id"])]
        declared = license_row["declared_license"] or "unknown"
        lines.extend(["### " + _md(component["component_id"]), "",
                      "- Rol: " + _ROLES[component["role"]],
                      "- Repository etiketi: " + _md(component["repository_label"]),
                      "- Scope'ta pinlenmiş commit: " + _md(component["pinned_commit"]),
                      "- Seçili kaynak dosya referansı sayısı: " + str(len(component["source_file_refs"])),
                      "- Sürüm beyanı: " + _md(component["version_declaration"] or "not_declared"),
                      "- Sürüm kapsamı: " + _md(component["version_scope"]),
                      "- Lisans etiketi: " + _md(declared),
                      "- Kanıt düzeyi: " + _md(license_row["evidence_level"]),
                      "- Kanıt dosya referansları: " + ", ".join(_md(ref) for ref in license_row["source_file_refs"]),
                      "- Belirsizlikler: " + ", ".join(_md(code) for code in license_row["uncertainty_codes"]),
                      "- proposed_source_only; human_review_required=true; redistribution_authorized=false.", ""])
    lines.extend(["Platform project sürümü bir standalone destek aracının release sürümü değildir. Yerel kaynak varlığı, build veya runtime kabulü değildir.", "",
                  "## Bağımlılık kayıtları ve kapsam", "",
                  "- Açık dependency manifesti/lock kaydı: " + str(len(ledger["manifest_records"])),
                  "- Dependency kayıt sayısı: " + str(len(dependencies)),
                  "- Manifest declaration kaydı: " + str(relation_counts["direct_declaration"]),
                  "- Lock kaydı: " + str(relation_counts["lock_record"]),
                  "- Seçili kaynak metadata kapsamındaki kayıt: " + str(context_counts["selected_source_metadata"]),
                  "- Kapsam dışı backend bağlamındaki kayıt: " + str(context_counts["excluded_backend_context"]),
                  "- Lisans kanıt kaydı: " + str(len(ledger["license_evidence"])),
                  "- Lisansı unknown veya çelişkili subject: " + str(unknown), "",
                  "Declaration ve lock kayıtları ayrı tutulur; aynı paket adı tek ve eksiksiz resolved bağımlılık grafiğine dönüştürülmez. Workspace dependency havuzu her bileşenin doğrudan bağımlılığı değildir. Cargo.lock bütün workspace kayıtlarını içerebilir; seçilen feature veya build closure'ını kanıtlamaz. Doğrudan/transitive ilişki güvenle belirlenmediyse unknown kalır.", "",
                  "Platform pyproject/requirements kayıtları yalnız excluded_backend_context'tir. Backend bu aday bileşimine dahil değildir; bu kayıtlar standalone destek araçlarının runtime bağımlılıkları olarak sunulmaz.", "",
                  "Cargo.lock sürüm/checksum bilgisi lisans veya yerel package artifact doğrulaması değildir. Hiçbir package indirilmedi, dependency çözülmedi veya cache içeriği doğrulanmadı. local_package_artifact=not_selected_or_verified korunur. Tam dependency kayıtları ve kaynak kimliği metadata'sı ayrı dependency-license-ledger.json dosyasındadır.", "",
                  "### İncelenen manifest durumları", ""])
    for manifest in ledger["manifest_records"]:
        lines.append("- " + _md(manifest["manifest_id"]) + ": " + _md(manifest["format"]) + "; "
                     + _md(manifest["parse_status"]) + "; " + str(manifest["record_count"]) + " kayıt; "
                     + _md(manifest["context"]) + "; " + _md(manifest["limitation_code"]))
    lines.extend(["", "## Lisans beyanı ve dağıtım izni", "",
                  "Lisans beyanı dağıtım izni değildir. Kaydedilen lisans etiketi yalnız o subject'e açıkça atfedilen kaynak kanıtıyla sınırlıdır. MIT etiketi bulunması diğer crate/dependency, destek aracı veya bütün ürüne yayılmaz. Lisans dosya referansları composition-inventory.json içindeki gerçek boyut/SHA256 metadata'sına bağlanır. Metnin etiketi, hukuki geçerlilik veya kapsam kararı değildir.", "",
                  "Platform pyproject içinde lisans beyanı yoksa destek araçlarının lisansı unknown kalır. Lock/manifest dependency satırında lisans bulunmaması paket adı veya ezberden doldurulmaz. Çelişkili beyanlar sessizce seçilmez; conflicting_declarations ve insan inceleme gereksinimi korunur. Bilinen etiketlerde de yetkili insan incelemesi gerekir.", "",
                  "## Açık dağıtım engelleri", "",
                  "- Toplam açık blocker kaydı: " + str(constraints["counts"]["blocker_count"]), ""])
    for row in constraints["counts"]["by_code"]:
        lines.append("- " + _BLOCKERS[row["code"]] + ": " + str(row["affected_subject_count"])
                     + " subject — " + _md(row["code"]))
    lines.extend(["", "Aynı subject birden fazla blocker grubunda bulunabilir. Sayımlar bileşen/dependency metadata kayıtlarıdır; risk puanı, görev, müşteri sayısı veya tamamlanma yüzdesi değildir. Kapsam dışı backend bağlamı içeren kayıtların blocker'ları bu backend'i adayın parçası yapmaz. Kaynak dayanağı ve bekleyen karar kodları release-constraints.json içindedir.", "",
                  "## Kapsam dışı bileşenler", ""])
    for excluded in inventory["excluded_components"]:
        lines.append("- " + _md(excluded["component_id"]) + " — " + _md(excluded["reason_code"]))
    lines.extend(["", "HBF, Altay, production backend, operator console, kurumsal IdP, canlı merkezî yönetim, policy execution, imzalı Windows installer ve gerçek zamanlı antivirüs bu kaynak adayına otomatik dahil edilmez.", "",
                  "## Güven ve kabul sınırı", "",
                  "Proposed source composition ile actual distributable artifacts ayrıdır. İkinci grup bu fazda boştur. Runtime binary, installer veya production wheel oluşturulmadı ve yeniden paketlenmedi. Source present, dependency declared, lock'ta resolved version, yerel dosya varlığı ve lisans beyanı; redistribution review, build/runtime kabulü veya release yetkisi değildir.", "",
                  "demo_only=true; source_inventory_generated=true; " + "; ".join(name + "=false" for name in FALSE_FLAGS) + ".", "",
                  "Manifest/hash yalnız seçilmiş kaynak metadata'sı ve üretilmiş çıktı baytlarının içerik kimliğini bağlar. Producer, hukukî uygunluk, lisans kapsamı, build, runtime veya gerçek ticari dağıtım onayı vermez. Envanter bütün olası runtime/feature/üçüncü taraf bileşenlerini eksiksiz kapsadığını iddia etmez. Ham kaynak, credential veya özel metin bu özete taşınmaz; otomatik secret detection, redaksiyon veya anonimlik garantisi yoktur.", "",
                  "Phase14 müşteri talebi ve ödeme isteği alanları not_validated kalır. Pilot GO veya ticari dağıtım onayı verilmedi.", "",
                  "## NOT_RUN — açık kabul kapıları", "",
                  "Malformed/duplicate/hostile input, yanlış lock sürümü, çelişkili lisans metadata'sı, eksik dependency, büyük kaynak sınırı, symlink/reparse/hardlink, dosya yarışı veya değişen kaynak, izin/kısmi yazma/crash, tekrarlı determinism, gerçek dependency çözümleme, build/runtime kabulü, yetkili ticari lisans incelemesi, imzalı release ve production dağıtımı çalıştırılmadı. İki sentetik üretim/inceleme komutu otomatik test, eksiksiz yazılım bileşimi doğrulaması veya hukukî kabul değildir.", ""])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if not 0 < len(raw) <= MAX_SUMMARY_BYTES:
        raise InputError("composition_summary_size_limit")
    return raw


__all__ = ("MAX_SUMMARY_BYTES", "render_summary")
