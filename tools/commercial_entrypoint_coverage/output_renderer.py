"""Pure, bounded and inert Markdown for explicit entry-point source evidence."""
from __future__ import annotations

import html

from .coverage_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 256 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_GROUPS = (
    ("composition_sources", ("inventory", "dependencies", "constraints", "summary", "manifest")),
    ("dependency_evidence_sources", ("evidence", "graph", "variants", "summary", "manifest")),
    ("variant_sources", ("analysis", "dependencies", "licenses", "summary", "manifest")),
)


def _md(value: object) -> str:
    """Escape per character so entities cannot become new Markdown syntax."""
    return "".join(
        " " if char in "\r\n\t" else
        "&#" + str(ord(char)) + ";" if char in _PUNCTUATION else
        html.escape(char, quote=True)
        for char in str(value)
    )


def _value(value: object, missing: str = "Mevcut sonuçta bulunmuyor") -> str:
    if value is None:
        return missing
    if type(value) is bool:
        return "true" if value else "false"
    return _md(value)


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def _statuses(lines: list[str], rows: list) -> None:
    for row in rows:
        lines.append("- " + _md(row["status"]) + ": " + str(row["target_count"]))


def _flags() -> str:
    return "demo_only=true; " + "; ".join(flag + "=false" for flag in FALSE_FLAGS) + "."


def render_summary(coverage: dict, delta: dict, variants: dict) -> bytes:
    """Validate closed documents first; render metadata only, with no I/O."""
    validate_documents(coverage, delta, variants)
    counts = coverage["counts"]
    context = coverage["source_context"]
    reference = coverage["source_reference"]
    targets = {row["target_reference"]: row for row in coverage["targets"]}
    referenced_files = {file_ref for component in context["components"]
                        for file_ref in component["source_file_refs"]}
    outside = [row for row in context["files"] if row["file_id"] not in referenced_files]
    manifest_contexts = {}
    for row in context["dependency_manifest_refs"]:
        manifest_contexts.setdefault((row["root_id"], row["path"]), []).append(row["context"])
    lines = [
        "# Native giriş noktası kaynak kapsamı", "", _md(coverage["demo_label"]), "",
        "Bu çıktı manifest target bildirimini, izinli dosya gözlemini, Phase24 F kataloğu ilişkisini ve uygulanmamış kaynak kapsamı önerisini ayrı gösterir. Dosya varlığı ve içerik hash'i component ownership, tam source completeness, başarılı build veya release kanıtı değildir.", "",
        "## 1. Kaynak kimliği ve okunan manifestler", "",
        "- Yerel coverage referansı: " + _md(reference["candidate_reference"]),
        "- Korunan composition referansı: " + _md(reference["composition_candidate_reference"]),
        "- Termivar pin beyanı: " + _md(reference["source_commits"]["termivar"]),
        "- Platform pin beyanı: " + _md(reference["source_commits"]["platform"]), "",
        "Bu pinler kaynak kapsamı beyanıdır; producer veya Git commit attestation değildir. Metadata içindeki başka path, URL veya modül dosyası otomatik açılmaz.", "",
        "| Manifest | Root | Relative path | F referansı | Bayt | SHA256 | Paket beyanı |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in coverage["manifests"]:
        lines.append(_row((_md(row["manifest_id"]), _md(row["root_id"]), _md(row["path"]),
                           _md(row["phase24_file_ref"]), str(row["bytes"]), _md(row["sha256"]),
                           _value(row["package_name"], "virtual_workspace_no_package"))))
    lines.extend([
        "", "## 2. Explicit target ve izinli dosya gözlemi", "",
        "- Okunan Cargo manifesti: " + str(counts["manifest_count"]),
        "- Açık target bildirimi: " + str(counts["target_count"]),
        "- Explicit path içeren target: " + str(counts["explicit_path_target_count"]),
        "- Tekil kaynak dosyası gözlemi: " + str(counts["source_file_observation_count"]),
        "- Gerçekten mevcut ve hash'lenmiş dosya: " + str(counts["present_and_hashed_source_file_count"]),
        "- Açık izinli fakat bulunamayan dosya: " + str(counts["missing_source_file_count"]),
        "- Hash'lenmiş kaynak baytı: " + str(counts["observed_source_bytes"]), "",
        "Yalnız [lib] ve [[bin]] explicit bildirimleri kullanılır. Target adı executable veya component kimliği değildir. Path belirtilmemişse Cargo konvansiyonundan kesin dosya üretilmez; auto target discovery, Rust module graph ve feature/target activation yapılmaz.", "",
        "| Target referansı | Manifest | Tür / beyan edilen ad | Beyan edilen path | Normalize root-relative path | Path bildirimi | Gerekli feature metadata'sı |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in coverage["targets"]:
        lines.append(_row((_md(row["target_reference"]), _md(row["manifest_reference"]),
                           _md(row["target_kind"]) + " / " + _value(row["declared_target_name"]),
                           _value(row["declared_relative_path"]), _value(row["normalized_relative_path"]),
                           _value(row["target_path_declared"]),
                           "Mevcut sonuçta bulunmuyor" if row["required_features"] is None else _items(row["required_features"]))))
    if not coverage["targets"]:
        lines.append("| — | — | Açık target bildirimi bulunmadı | — | — | — | — |")
    lines.extend([
        "", "| Yerel dosya referansı | Root-relative path | Okuma durumu | Varlık | Regular-file kanıtı | Gerçek bayt | Gerçek SHA256 | İzinli target referansları |",
        "| --- | --- | --- | --- | --- | ---: | --- | --- |",
    ])
    for row in coverage["source_files"]:
        lines.append(_row((_md(row["source_file_reference"]), _md(row["path"]), _md(row["read_status"]),
                           _md(row["source_file_presence"]), _value(row["regular_file"]),
                           _value(row["observed_byte_size"]), _value(row["observed_sha256"]),
                           _items(entry["target_reference"] for entry in row["allowlist_entries"]))))
    if not coverage["source_files"]:
        lines.append("| — | — | Okuma gözlemi yok | — | — | — | — | — |")
    lines.extend([
        "", "EPF referansları yeni yerel dosya gözlemleridir; yeni Phase24 F kaydı değildir. Allowlist dışındaki target için dosya varlığı veya hash uydurulmaz. read_not_performed fiziksel dosya yokluğu değildir. Eksik dosyada hash ve boyut null kalır. Kaynak gövdeleri bu çıktıya, log'a veya teslim ZIP'ine kopyalanmaz.", "",
        "## 3. Global F kataloğu ve component referans kapsamı", "",
        "- Global F kataloğu: " + str(counts["global_f_catalog_count"]),
        "- Component source_file_refs birleşimindeki farklı F: " + str(counts["component_referenced_file_count"]),
        "- Bu birleşim dışında kalan global F: " + str(len(outside)), "",
        "F satırlarında genel selected, metadata_only veya excluded alanı yoktur. Component referansında bulunmamak otomatik excluded değildir; bulunmak runtime inclusion değildir. Lock veya yerel lisans dosyasının component birleşimi dışında kalması kendi kaynak bağlamını değiştirmez. Ortak pyproject sekiz helper'ın runtime sahipliğini kanıtlamaz.", "",
        "| Component birleşimi dışındaki F | Root | Relative path | Mevcut dependency-manifest bağlamı |",
        "| --- | --- | --- | --- |",
    ])
    for row in outside:
        lines.append(_row((_md(row["file_id"]), _md(row["root_id"]), _md(row["path"]),
                           _items(manifest_contexts.get((row["root_id"], row["path"]), [])))))
    if not outside:
        lines.append("| — | — | Bu projection'da birleşim dışı F yok | — |")
    lines.extend([
        "", "Tablodaki —, bu dar dependency-manifest projection'ında kapsam niteliği bulunmadığını belirtir. Lisans dosyası kendi yerel kaynak bağlamını korur; yeni selected/excluded sınıfı atanmaz. Katalog üyeliği ile eski byte/hash eşitliği ayrı kontrol edilir; yalnız relative path benzerliği kesin coverage değildir.", "",
        "### Coverage sonuçları", "",
    ])
    _statuses(lines, counts["by_coverage_status"])
    for row in coverage["coverage"]:
        target = targets[row["target_reference"]]
        lines.extend([
            "", "### " + _md(row["target_reference"]), "",
            "- Coverage referansı: " + _md(row["coverage_reference"]),
            "- Manifest / target türü: " + _md(row["manifest_reference"]) + " / " + _md(row["target_kind"]),
            "- Kaynak path: " + _value(row["normalized_relative_path"]),
            "- Target/path bildirimi: " + _value(target["target_declared"]) + " / " + _value(target["target_path_declared"]),
            "- Allowlist: " + _md(row["allowlist_status"]),
            "- Yerel dosya referansı: " + _value(row["source_file_reference"]),
            "- Dosya varlığı / kanıt: " + _md(row["source_file_presence"]) + " / " + _md(row["source_evidence_status"]),
            "- Gerçek byte / SHA256: " + _value(row["observed_byte_size"]) + " / " + _value(row["observed_sha256"]),
            "- Phase24 F bağı: " + _value(row["phase24_source_reference"]),
            "- Global F membership: " + _md(row["phase24_catalog_status"]),
            "- Eski dosya kimliği karşılaştırması: " + _md(row["phase24_identity_status"]),
            "- Component F referans durumu: " + _md(row["component_source_status"]),
            "- Dosyayı referanslayan component'ler: " + _items(row["referencing_component_ids"]),
            "- Mevcut manifest kapsam bağlamları: " + _items(
                item["manifest_id"] + ": " + item["context"]
                for item in row["phase24_manifest_contexts"]),
            "- Coverage sonucu: " + _md(row["phase24_coverage_status"]),
            "- Target component ownership: " + _md(row["component_ownership_status"]),
            "- Korunan manifest ownership: " + _md(row["manifest_ownership_status"]),
            "- Potansiyel component adayları: " + _items(row["candidate_component_ids"]),
            "- Kesin component: " + _value(row["established_component_id"], "not_established"),
            "- Sınırlamalar: " + _items(row["limitations"]),
        ])
    lines.extend([
        "", "Envanter kapsamındaki boşluk kaynak dosyasının fiziksel yokluğu değildir. source_present_inventory_gap ile component_ownership_unresolved aynı target için birlikte bulunabilir. Yeni hash eski artefact'taki eksik byte/hash bilgisini geriye dönük doldurmaz.", "",
        "## 4. Repository-level kaynak kapsamı önerileri", "",
        "- Benzersiz global öneri: " + str(delta["counts"]["unique_proposal_count"]),
        "- Önerilerin koruduğu target referansı: " + str(delta["counts"]["proposal_target_reference_count"]),
        "- Önerilen tekil kaynak dosyası: " + str(delta["counts"]["proposal_source_file_count"]),
        "- Uygulama yetkili / uygulanmış öneri: " + str(delta["counts"]["application_authorized_count"]) + " / " + str(delta["counts"]["application_performed_count"]), "",
        "Öneri ancak explicit target, exact allowlist, gerçek dosya kimliği ve global F boşluğu birlikte destekliyorsa üretilir. Eylem adı propose_selected_source_inclusion, eski F modeline selected alanı eklemez. Aynı kaynak kimliği için tek global öneri tutulur; farklı target bağları kaybolmaz.", "",
    ])
    for row in delta["proposals"]:
        lines.extend([
            "### " + _md(row["proposal_reference"]), "",
            "- Düzey / eylem: " + _md(row["proposal_level"]) + " / " + _md(row["proposed_scope_action"]),
            "- Dosya / path: " + _md(row["source_file_reference"]) + " / " + _md(row["path"]),
            "- Root / pin beyanı: " + _md(row["root_id"]) + " / " + _md(row["pinned_commit"]),
            "- Gerçek byte / SHA256: " + str(row["observed_byte_size"]) + " / " + _md(row["observed_sha256"]),
            "- Mevcut coverage: " + _md(row["current_phase24_coverage"]),
            "- Bütün destekleyen target'lar: " + _items(row["source_target_references"]),
            "- Destekleyen manifestler: " + _items(row["manifest_references"]),
            "- Destekleyen coverage kayıtları: " + _items(row["supporting_evidence"]["coverage_references"]),
            "- Dosya hash gözlemi / explicit allowlist: " + _value(row["supporting_evidence"]["source_hash_observed"]) + " / " + _value(row["supporting_evidence"]["explicit_allowlist"]),
            "- Önerilen component: " + _value(row["proposed_component_id"], "Atama yapılmadı"),
            "- Ownership sınırı: " + _md(row["ownership_limitation"]),
            "- Uygulama önkoşulları: " + _items(row["application_preconditions"]),
            "- application_authorized=false; application_performed=false; phase24_inventory_modified=false; component_ownership_verified=false.", "",
        ])
    if not delta["proposals"]:
        lines.extend(["Bu veri için desteklenen repository-level inclusion önerisi oluşmadı.", ""])
    lines.extend([
        "Öneri component ownership düzeltmesi değildir. Eski inventory patch edilmez; yeni F numarası veya component source listesi yazılmaz. İleride inclusion ayrı bir kararla uygulanırsa dahi build/runtime, dependency closure veya lisans/dağıtım yetkisi kanıtlanmış olmaz.", "",
        "## 5. Phase26 varyant projection", "",
        "- Varyant: " + str(variants["counts"]["variant_count"]),
        "- Global target: " + str(variants["counts"]["global_target_count"]),
        "- Global benzersiz öneri: " + str(variants["counts"]["global_proposal_count"]),
        "- Ayrı varyant target referansı: " + str(variants["counts"]["variant_target_reference_count"]), "",
        "Global öneriler bir defa sayılır; varyantlar bunlara referans verir. Varyant referans toplamı global öneri veya ek dependency sayısı değildir. Potansiyel source-scope ilgisi kesin component-owned entry-point'e yükseltilmez; helper'lar için native target uydurulmaz.", "",
    ])
    for variant in variants["variants"]:
        item_counts = variant["counts"]
        lines.extend([
            "### " + _md(variant["variant_id"]) + " — " + _md(variant["label"]), "", _md(variant["description"]), "",
            "- Seçilen component'ler: " + _items(variant["selected_component_ids"]),
            "- Seçilmeyen component'ler: " + _items(variant["not_selected_component_ids"]),
            "- Kesin source-metadata component ilişkili target: " + str(item_counts["definite_source_metadata_target_count"]),
            "- Potansiyel ilgi, ownership çözülmemiş target: " + str(item_counts["ownership_unresolved_candidate_target_count"]),
            "- Seçilmiş component ilişkisi kurulamayan target: " + str(item_counts["unattributed_target_count"]),
            "- Global öneri referansları: " + _items(variant["proposal_references"]), "",
            "| Target | Coverage | Dosya | F coverage sonucu | Ownership | Varyant ilişkisi | Global öneri referansları |",
            "| --- | --- | --- | --- | --- | --- | --- |",
        ])
        for row in variant["target_projections"]:
            lines.append(_row((_md(row["target_reference"]), _md(row["coverage_reference"]),
                               _value(row["source_file_reference"]), _md(row["phase24_coverage_status"]),
                               _md(row["component_ownership_status"]), _md(row["relationship"]),
                               _items(row["proposal_references"]))))
        if not variant["target_projections"]:
            lines.append("| — | — | — | Target projection yok | — | — | — |")
        _statuses(lines, item_counts["by_coverage_status"])
        lines.extend(["", _flags(), ""])
    for row in variants["comparisons"]:
        lines.extend([
            "### " + _md(row["left"]) + " / " + _md(row["right"]), "",
            "- Ortak component'ler: " + _items(row["shared_component_ids"]),
            "- Yalnız sol / yalnız sağ component'ler: " + _items(row["only_left_component_ids"]) + " / " + _items(row["only_right_component_ids"]),
            "- Ortak target referansları: " + _items(row["shared_target_references"]),
            "- Yalnız sol / yalnız sağ target referansları: " + _items(row["only_left_target_references"]) + " / " + _items(row["only_right_target_references"]),
            "- Ortak global öneri referansları: " + _items(row["shared_proposal_references"]),
            "- Yalnız sol / yalnız sağ öneri referansları: " + _items(row["only_left_proposal_references"]) + " / " + _items(row["only_right_proposal_references"]), "",
            "Bu kaynak ilişki karşılaştırması completeness oranı, runtime farkı veya production readiness artışı değildir.", "",
        ])
    license_counts = context["license_boundary_counts"]
    lines.extend([
        "## 6. Korunan sahiplik, dependency ve lisans sınırları", "",
        "- Önceki kesin component owner: " + str(context["source_definite_owner_count"]),
        "- Ownership çözülmemiş target: " + str(counts["unresolved_ownership_target_count"]),
        "- Korunan dependency kaydı: " + str(context["source_dependency_record_count"]),
        "- Korunan belirsiz eski dependency D kaydı: " + str(context["source_ambiguous_dependency_record_count"]),
        "- Ayrı lisans subject'i / unknown: " + str(license_counts["source_license_record_count"]) + " / " + str(license_counts["base_unknown_license_count"]),
        "- Önceki fresh evidence var / eksik: " + str(license_counts["evidence_present_record_count"]) + " / " + str(license_counts["missing_evidence_record_count"]),
        "- İnsan incelemesi gerekli: " + str(license_counts["human_review_required_record_count"]),
        "- Önceki açık blocker: " + str(license_counts["source_blocker_count"]), "",
        "Eski dependency kayıtları veya iki scoped MIT beyanının kapsamı genişletilmez. Target/file ilişkisi yeni lisans kanıtı oluşturmaz; önceki unknown, producer, human/legal review ve release kapıları kapanmaz. Kaynak kodunun tamamının bulunduğu veya binary'ye dahil edildiği sonucu çıkarılmaz.", "",
        "## 7. Açık artefact kimlikleri", "",
        "Yalnız açıkça seçilmiş önceki artefact'ların byte kimlikleri aşağıdadır. Bu referanslar dış URL veya otomatik dosya açma talimatı değildir.", "",
        "| Kaynak grubu | Rol | Sözleşme | Bayt | SHA256 |",
        "| --- | --- | --- | ---: | --- |",
    ])
    for group, roles in _SOURCE_GROUPS:
        for role in roles:
            item = reference[group][role]
            lines.append(_row((_md(group), _md(role), _value(item["schema_version"], "Markdown / şema yok"),
                               str(item["bytes"]), _md(item["sha256"]))))
    lines.extend([
        "", "## 8. Veri sınırı ve açık kabul kapıları", "", _flags(), "",
        "Dosya gövdesi tutulmaz; yalnız sınırlı metadata görüntülenir. Metadata allowlist'i secret detection, anonimleştirme veya şifreleme garantisi değildir. Relative path, target ve package adları da hassas olabilir. Yerel deterministik referanslar imza, attestation veya global release kimliği değildir.", "",
        "Cargo manifesti 256 KiB; target-source dosyası 512 KiB, toplam target okuması 1 MiB; hash parçası en fazla 64 KiB; toplam açık girdi 12 MiB; yeni JSON 2 MiB ve bu Markdown 256 KiB ile sınırlıdır. Limit aşımı kısmi listeyi tam başarı olarak döndürmez.", "",
        "Inspector yalnız beş yeni dosyanın iç model/ilişki/sayım/Markdown ve gerçek byte/hash tutarlılığına bakar. Eski artefact'ları, Cargo veya target-source dosyalarını bağımsız yeniden okumaz. content_consistent kaynak otoritesi, Git attestation, başarılı build veya release kabulü değildir.", "",
        "NOT_RUN: hostile/duplicate/malformed JSON; bozuk veya desteklenmeyen TOML; yanlış target path; allowlist dışı dosya; kaynak/hash manipülasyonu; symlink/junction/reparse/hardlink; traversal/TOCTOU; değişim/permission/filesystem race; limit; crash/partial write/power-loss; tekrar determinism; Cargo otomatik target keşfi; Rust module graph; tam source completeness; native build/runtime; dependency closure; üretici/Git attestation; insan/uzman/hukukî onay; production/release. Önceki kabul kapıları korunur.", "",
        "Coverage sınırlamaları: " + _items(coverage["limitations"]),
        "Delta sınırlamaları: " + _items(delta["limitations"]),
        "Varyant sınırlamaları: " + _items(variants["limitations"]), "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("entrypoint_summary_byte_limit_exceeded")
    return raw
