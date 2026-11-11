"""Bounded inert Markdown for source declarations, ownership and legacy binding."""
from __future__ import annotations

from collections import Counter
import html

from .evidence_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 512 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")


def _md(value: object) -> str:
    return "".join("&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def _optional(value) -> str:
    return "not_declared" if value is None else "true" if value is True else "false"


def _features(value) -> str:
    return "not_declared" if value is None else _items(value)


def render_summary(evidence: dict, graph: dict, variants: dict) -> bytes:
    validate_documents(evidence, graph, variants)
    counts = evidence["counts"]
    declarations = {row["declaration_id"]: row for row in evidence["declarations"]}
    bindings = {row["declaration_id"]: row for row in evidence["bindings"]}
    overlay = {row["dependency_id"]: row for row in variants["records"]}
    ambiguous = [row for row in evidence["bindings"] if row["status"] == "ambiguous_record_binding"]
    candidate_groups = list(dict.fromkeys(tuple(row["candidate_record_ids"]) for row in ambiguous))
    kinds = Counter(row["dependency_kind"] for row in evidence["declarations"])
    license_counts = evidence["license_boundary_counts"]
    lines = ["# Doğrudan dependency kaynak kanıtı", "", evidence["demo_label"], "",
             "Bu çıktı üç ayrı sınırı gösterir: manifestte kaynak bildirimi, Phase24 component sahipliği ve gerçek resolved/build dependency. İlk ikisi için mevcut metadata incelenir; resolution, activation, binary veya runtime doğrulanmaz.", "",
             "## 1. Okunan gerçek manifestler", "",
             "Yalnız açık seçilmiş Cargo dosyalarının byte kimlikleri bağlanır. Metadata içindeki URL, git/path dependency veya bin/lib entry dosyası takip edilmez.", "",
             "| Manifest id | Repo-relative referans | Bayt | SHA256 | Paket beyanı |",
             "| --- | --- | ---: | --- | --- |"]
    for row in evidence["source_manifests"]:
        lines.append(_row((_md(row["manifest_id"]), _md(row["path"]), str(row["bytes"]), _md(row["sha256"]),
                           _md(row["package_name"] or "virtual_workspace_no_package"))))
    lines.extend(["", "## 2. Bulunan kaynak bildirimleri", "",
                  "- Toplam desteklenen Rust source declaration: " + str(counts["source_declaration_count"]),
                  "- Workspace template pool: " + str(counts["workspace_pool_declaration_count"]),
                  "- Crate bildirimi: " + str(counts["crate_declaration_count"]),
                  "- Kaynakta açık workspace inheritance: " + str(counts["workspace_inherited_declaration_count"]),
                  "- Optional/dev/build/target koşullu bildirim: " + str(counts["conditional_declaration_count"]), "",
                  "Workspace pool bütün crate'lerin dependency listesi değildir. Bildirim anahtarı, gerçek package adı ve requirement ayrı tutulur. Requirement kesin lock sürümü veya resolution değildir.", "",
                  "## 3. Component ownership sınırı", "",
                  "- Kesin component–manifest sahipliği: " + str(counts["ownership_established_manifest_count"]),
                  "- Ambiguous ownership: " + str(counts["ambiguous_ownership_manifest_count"]),
                  "- Ownership kurulmamış: " + str(counts["ownership_not_established_manifest_count"]), "",
                  "| Manifest | Durum | Kesin component | F-scope adayları | Primary-manifest adayları |",
                  "| --- | --- | --- | --- | --- |"])
    for row in evidence["ownership"]:
        lines.append(_row((_md(row["manifest_id"]), _md(row["ownership_status"]), _md(row["component_id"] or "not_established"),
                           _items(row["candidate_component_ids"]), _items(row["primary_component_ids"]))))
    lines.extend(["", "Scanner/CLI ortak F kapsamı primary-manifest alanından sessizce bir owner seçtirmez. Core'un tek source-scope adayı olması, primary manifest ilişkisi yoksa ownership değildir. Virtual workspace root ortak template kaynağıdır. Sıfır kesin ownership, gerçek kaynak bildirimi veya inheritance kanıtını silmez; component edge'i uydurmak için gerekçe değildir.", "",
                  "Sekiz Python helper'ın ortak pyproject/F0004 kapsamı helper distribution metadata'sı değildir. Backend script/declaration/pin kayıtları helper runtime dependency'sine çevrilmez. Sınırlı entry-file stdlib/kardeş import gözlemi PyPI adı, sürüm, activation veya tam closure kanıtı değildir.", "",
                  "## 4–5. Phase24 kayıt bağı: tekil metadata eşleşmesi ve belirsiz adaylar", "",
                  "- Tekil legacy-projection eşleşen declaration: " + str(counts["unique_binding_declaration_count"]),
                  "- Bu eşleşmelerin farklı Phase24 D ref sayısı: " + str(counts["unique_matched_phase24_record_count"]),
                  "- Belirsiz binding declaration: " + str(counts["ambiguous_binding_declaration_count"]),
                  "- Belirsiz binding'lerde farklı olası D ref: " + str(counts["possible_phase24_record_count"]),
                  "- Farklı aday kümesi: " + str(len(candidate_groups)),
                  "- Eşleşmeyen/yetersiz declaration: " + str(counts["unmatched_declaration_count"]), "",
                  "Tekil eşleşme yalnız eski sınırlı declaration metadata projeksiyonuyla aynılığı belirtir; kesin component ownership veya resolved dependency değildir. Eski modelde kind/target/feature ayrımı yoksa yeni bilgiden bir eski ordinal seçilmez. Lock satırlarına ad/semver eşleştirmesi yapılmaz.", "",
                  "| Kaynak declaration | Package | Olası eski D ref'ler | Gerekçeler | Eksik eski alanlar |",
                  "| --- | --- | --- | --- | --- |"])
    for row in ambiguous:
        declaration = declarations[row["declaration_id"]]
        lines.append(_row((_md(row["declaration_id"]), _md(declaration["package_name"]), _items(row["candidate_record_ids"]),
                           _items(row["reason_codes"]), _items(row["missing_fields"]))))
    if not ambiguous:
        lines.append("| — | Bu seçilmiş metadata için belirsiz binding yok | — | — | — |")
    lines.extend(["", "## 6–7. Workspace, feature ve target metadata'sı", "",
                  "Inheritance için çocuk bildirimin workspace=true kullanımı, literal workspace üyeliği/exclude kontrolü, package.workspace override bulunmaması ve açık root template kimliği birlikte aranır. Glob veya override path takip edilmez. Çocuk/root feature ve default-feature beyanları ayrı tutulur; etkin bir union veya feature resolution sonucu üretilmez. Target cfg ifadesi değerlendirilmez; activation_unknown ve target_evaluation=not_performed korunur.", "",
                  "- Normal kind: " + str(kinds["normal"]), "- Dev kind: " + str(kinds["dev"]),
                  "- Build kind: " + str(kinds["build"]), "- Workspace template kind: " + str(kinds["workspace_template"]), "",
                  "Dev/build kind runtime inclusion veya runtime yokluğu kanıtı değildir. Kaynakta olmayan renamed/build fixture veya evaluator sonucu oluşturulmaz. Native bin/lib entry path'leri sınırlı metadata'dır; mevcut F kapsamı dışındaki dosyalar okunmaz.", "",
                  "## 8. Varyant kaynak kanıtı overlay'i", "",
                  "Phase26 dosyaları ve eski exposure enum'ları değişmez. Aşağıdaki ayrı sınıflar aynı 451 özgün D ref üzerine uygulanır. Ambiguous binding seçimle kesinleşmez; sahipliği bilinmeyen manifest source_scope_only sınırını aşmaz. Workspace template tek başına crate dependency'si değildir.", ""])
    for variant in variants["variants"]:
        lines.extend(["### " + _md(variant["variant_id"]) + " — " + _md(variant["label"]), "",
                      _md(variant["description"]), "",
                      "- Seçilen component: " + _items(variant["selected_component_ids"]),
                      "- Kesin sahip manifest: " + _items(variant["owned_manifest_ids"]),
                      "- Yalnız potansiyel source-scope manifesti: " + _items(variant["potential_manifest_ids"]),
                      "- Kesin sahibi seçilmiş crate declaration: " + _items(variant["owned_declaration_ids"]),
                      "- Ownership kurulmamış manifest: " + _items(variant["ownership_unestablished_manifest_ids"]), ""])
        for item in variant["classification_counts"]:
            lines.append("- " + _md(item["classification"]) + ": " + str(item["record_count"]))
        lines.extend(["", "demo_only=true; " + "; ".join(flag + "=false" for flag in FALSE_FLAGS) + ".", ""])
    for comparison in variants["comparisons"]:
        lines.extend(["### " + _md(comparison["left"] + " / " + comparison["right"]), "",
                      "- Ortak component: " + _items(comparison["shared_component_ids"]),
                      "- Yalnız sol component: " + _items(comparison["only_left_component_ids"]),
                      "- Yalnız sağ component: " + _items(comparison["only_right_component_ids"]),
                      "- Ortak kesin sahip manifest: " + _items(comparison["shared_owned_manifest_ids"]),
                      "- Yeni overlay sınıfı değişen D ref: " + str(comparison["classification_change_count"]), "",
                      "Bu sayım gerçek runtime dependency farkı değildir. Helper için attribution kurulamaması sıfır runtime dependency anlamına gelmez.", ""])
    lines.extend(["## 9–10. Bilinmeyen closure, lisans ve kabul sınırı", "",
                  "- Korunan Phase24 dependency: " + str(counts["phase24_record_count"]),
                  "- Declaration / lock: " + str(counts["phase24_declaration_record_count"]) + " / " + str(counts["phase24_lock_record_count"]),
                  "- Selected-source / excluded backend-context: " + str(counts["selected_source_record_count"]) + " / " + str(counts["excluded_context_record_count"]),
                  "- Ayrı lisans subject'i: " + str(license_counts["source_license_record_count"]),
                  "- Korunan unknown lisans: " + str(license_counts["base_unknown_license_count"]),
                  "- Önceki yeni evidence var / eksik: " + str(license_counts["evidence_present_record_count"]) + " / " + str(license_counts["missing_evidence_record_count"]),
                  "- İnsan incelemesi gerekli: " + str(license_counts["human_review_required_record_count"]),
                  "- Önceki açık blocker: " + str(license_counts["source_blocker_count"]), "",
                  "Global D satırları unique package sayısı değildir. Hiçbir declaration lock resolution, gerçek feature/target aktivasyonu, build closure veya binary/runtime inclusion kanıtı değildir. Direct source edge lisans kanıtı oluşturmaz; önceki iki scoped MIT beyanı ve tek L0001 kanıtının kapsamı genişletilmez. Unknown ve önceki review/release kapıları kapanmaz.", "",
                  "## Grafik özeti", "",
                  "- Düğüm: " + str(graph["counts"]["node_count"]), "- Kenar: " + str(graph["counts"]["edge_count"]),
                  "- Özgün Phase24 D düğümü: " + str(graph["counts"]["phase24_record_node_count"]), "",
                  "| Düğüm türü | Sayı |", "| --- | ---: |"])
    for row in graph["counts"]["by_node_type"]:
        lines.append(_row((_md(row["node_type"]), str(row["node_count"]))))
    lines.extend(["", "| Kenar türü | Definite | Possible |", "| --- | ---: | ---: |"])
    for row in graph["counts"]["by_edge_type"]:
        lines.append(_row((_md(row["edge_type"]), str(row["definite_edge_count"]), str(row["possible_edge_count"]))))
    lines.extend(["", "Definite/possible ilgili kaynak ilişkisinin sınırıdır; producer, hukukî karar veya binary kanıtı değildir. Node/edge id ve fingerprint canonical metadata içeriğine bağlı yerel kimliktir; imza veya küresel package kimliği değildir. Olası binding'lerden kesin D edge'i üretilmez.", "",
                  "## Bütün kaynak declaration'lar", "",
                  "| Declaration | Manifest / TOML alanı | Anahtar / package | Requirement / kind | Optional / target | Yerel features / defaults | Workspace template / root features / defaults | Kaynak status / binding |",
                  "| --- | --- | --- | --- | --- | --- | --- | --- |"])
    for row in evidence["declarations"]:
        binding = bindings[row["declaration_id"]]
        template = declarations.get(row["workspace_template_id"])
        template_text = (_md(row["workspace_template_id"]) + " / " + _features(template["features"]) + " / "
                         + _optional(template["default_features"])) if template is not None else "not_requested_or_unavailable"
        lines.append(_row((_md(row["declaration_id"]), _md(row["manifest_id"] + " / " + " / ".join(row["toml_field_path"])),
                           _md(row["dependency_key"] + " / " + row["package_name"]),
                           _md((row["declared_requirement"] or "not_declared") + " / " + row["dependency_kind"]),
                           _md(_optional(row["optional"]) + " / " + (row["target_condition"] or "not_declared")),
                           _features(row["features"]) + " / " + _optional(row["default_features"]), template_text,
                           _md(row["evidence_status"] + " / " + binding["status"])) ))
    lines.extend(["", "## Bütün Phase24 D kayıtlarının ayrı overlay'i", "",
                  "Tam eski alan/digest/pointer ve lisans source key'i primary JSON'da korunur. Aşağıda hiçbir D ref sessizce kesilmez; declaration/lock türü değişmez.", "",
                  _row(("D ref", "Package / sürüm", "Eski relation / scope", *(_md(row["variant_id"]) for row in variants["variants"]))),
                  _row("---" for _ in range(3 + len(variants["variants"])))])
    for row in evidence["phase24_records"]:
        mapped = {item["variant_id"]: item["classification"] for item in overlay[row["dependency_id"]]["exposures"]}
        lines.append(_row((_md(row["dependency_id"]), _md(row["name"] + " / " + (row["version"] or "unknown")),
                           _md(row["relation"] + " / " + row["review_scope"]),
                           *(_md(mapped[item["variant_id"]]) for item in variants["variants"]))))
    lines.extend(["", "## Kaynak kimliği ve mahremiyet", "",
                  "Pinler eski inventory'nin deklaratif metadata'sıdır; git/build/producer attestation değildir.",
                  "- Termivar pin'i: " + _md(evidence["source_reference"]["source_commits"]["termivar"]),
                  "- Platform pin'i: " + _md(evidence["source_reference"]["source_commits"]["platform"]), "",
                  "Ham Cargo/lock/source/JSON gövdesi, tam lisans metni, credential, özel kişi/müşteri verisi, mutlak kullanıcı kökü veya exception bu özete taşınmaz. Güvenli relative manifest referansı ve sınırlı field metadata'sı anonimliğin garantisi değildir. Secret detection/redaksiyon/şifreleme garantisi yoktur. Dinamik metin link veya HTML olarak çalıştırılmaz.", "",
                  "Inspector yalnız beş yeni açık çıktıdaki kapalı model, referans/count, normalized inheritance/ownership/binding, graph/overlay/Markdown ve dört payload manifest byte bağını inceler. Orijinal Cargo veya Phase24/26 dosyaları, git, package cache ve üretici tekrar doğrulanmaz. İç tutarlılık ham kaynağın bağımsız kabulü değildir.", "",
                  "## NOT_RUN — açık kabul kapıları", "",
                  "Malformed/duplicate/hostile JSON, bozuk/desteklenmeyen TOML, yanlış inheritance, renamed/build dependency kenar senaryoları, feature resolution, target cfg evaluation, Cargo metadata/resolution, çoklu lock version eşleme, digest manipülasyonu, bozuk node/edge referansları, grafik/dosya limitleri, symlink/reparse/hardlink, TOCTOU/race/permission/crash/partial write/power loss, repeat determinism, gerçek native build closure, binary/runtime inclusion, lisans/üretici/hukukî inceleme ve production/release kabulü çalıştırılmadı. Önceki NOT_RUN kapıları kapanmadı. Kaynak okuma, iki sentetik ürün çağrısı ve inspector sonucu test veya gerçek kabul değildir.", ""])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if not 0 < len(raw) <= MAX_SUMMARY_BYTES:
        raise InputError("direct_dependency_summary_size_limit")
    return raw


__all__ = ("MAX_SUMMARY_BYTES", "render_summary")
