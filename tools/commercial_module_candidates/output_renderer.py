"""Pure bounded Markdown: candidate presence never becomes module resolution."""
from __future__ import annotations

import html

from .candidate_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 256 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_GROUPS = (
    ("reference_sources", ("ledger", "graph", "coverage", "summary", "manifest")),
    ("inventory_sources", ("inventory", "dependencies", "constraints", "summary", "manifest")),
)


def _md(value: object) -> str:
    return "".join(" " if char in "\r\n\t" else "&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _value(value: object, absent: str = "Gözlem bulunmuyor") -> str:
    if value is None:
        return absent
    if type(value) is bool:
        return "true" if value else "false"
    return _md(value)


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def render_summary(evidence: dict, triage: dict, coverage: dict) -> bytes:
    """Validate closed projections first; do not read source, paths or URLs."""
    validate_documents(evidence, triage, coverage)
    counts = evidence["counts"]
    triage_counts = triage["counts"]
    coverage_counts = coverage["counts"]
    source = evidence["source_reference"]
    lines = [
        "# Rust modül adayları ve path belirsizliği", "", _md(evidence["demo_label"]), "",
        "Bu çalışma yalnız açıkça seçilmiş aday yollarını ve izinli dosya gözlemlerini gösterir. Candidate file presence, Rust compiler module resolution değildir. Tek mevcut aday doğru dosya, exhaustive alternatif kümesi, module closure veya build başarısı sayılmaz.", "",
        "## 1. Kaynak ve inceleme paydaları", "",
        "- Yerel çalışma referansı: " + _md(source["candidate_reference"]),
        "- Termivar / platform pin beyanı: " + _md(source["source_commits"]["termivar"]) + " / " + _md(source["source_commits"]["platform"]),
        "- Korunan Phase29 source-reference: " + str(counts["source_reference_count"]),
        "- External module reference: " + str(counts["external_reference_count"]),
        "- Seçilen / seçilmeyen external reference: " + str(counts["selected_reference_count"]) + " / " + str(counts["not_selected_external_reference_count"]),
        "- İncelenen / not_examined reference: " + str(triage_counts["examined_reference_count"]) + " / " + str(triage_counts["not_examined_reference_count"]),
        "- Bildirilen candidate/reference ilişkisi: " + str(counts["candidate_count"]),
        "- Allowlisted / incelenen candidate ilişkisi: " + str(counts["allowlisted_candidate_count"]) + " / " + str(counts["examined_candidate_count"]),
        "- Present / missing / not-allowlisted candidate ilişkisi: " + str(counts["present_candidate_count"]) + " / " + str(counts["missing_candidate_count"]) + " / " + str(counts["not_allowlisted_candidate_count"]),
        "- Tekil dosya gözlemi: " + str(counts["unique_observed_file_count"]),
        "- Hash'lenmiş tekil dosya / yokluğu gözlenen tekil yol: " + str(counts["present_file_count"]) + " / " + str(counts["missing_file_count"]),
        "- Gerçek hash okuma baytı: " + str(counts["observed_file_bytes"]), "",
        "Reference, candidate ilişkisi ve tekil dosya farklı paydalardır. Aynı dosya birkaç reference'a bağlanırsa bir kez okunabilir; reference ilişkileri kaybolmaz. İncelenen yolun yokluğu fiziksel dosya içeriğinin okunduğu anlamına gelmez. Not-allowlisted path için exists/stat/open yapılmaz; varlık, boyut ve hash bilinmezdir.", "",
        "## 2. Seçilen adaylar ve dosya gözlemleri", "",
        "Candidate origin operatör veya context iddiasıdır; bağımsız uzman onayı değildir. Modül adından foo.rs veya foo/mod.rs otomatik üretilmez. Kaynak literal path taşımıyorsa dosya adı benzerliği supported static context kanıtı değildir.", "",
        "| Candidate | Phase29 reference | Parent source / modül | Kaynak line:column / byte | Root-relative candidate path | Origin / path context |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for row in evidence["candidates"]:
        position = row["source_position"]
        lines.append(_row((_md(row["candidate_id"]), _md(row["reference_id"]),
                           _md(row["parent_source_file_reference"]) + " / " + _md(row["module_name"]),
                           str(position["line"]) + ":" + str(position["column"]) + " / " + str(position["byte_offset"]),
                           _md(row["candidate_relative_path"]),
                           _md(row["candidate_origin"]) + " / " + _md(row["path_context"]["status"]))))
    if not evidence["candidates"]:
        lines.append("| — | — | Bu scope'ta candidate kaydı yok | — | — | — |")
    lines.extend(["", "| Candidate | Allowlist | Read / presence | Gerçek bayt | Gerçek SHA256 | File ID | Candidate durumu |",
                  "| --- | --- | --- | ---: | --- | --- | --- |"])
    for row in evidence["candidates"]:
        lines.append(_row((_md(row["candidate_id"]), _md(row["allowlist_status"]),
                           _md(row["read_status"]) + " / " + _md(row["source_file_presence"]),
                           _value(row["observed_byte_size"]), _value(row["observed_sha256"]),
                           _value(row["file_id"]), _md(row["candidate_status"]))))
    if not evidence["candidates"]:
        lines.append("| — | — | Dosya gözlemi yok | — | — | — | — |")
    lines.extend([
        "", "### Tekil izinli dosya gözlemleri", "",
        "| File ID | Root-relative path | Candidate ilişkileri | Okuma durumu | Regular-file kanıtı | Gerçek bayt | Gerçek SHA256 |",
        "| --- | --- | --- | --- | --- | ---: | --- |",
    ])
    for row in evidence["candidate_files"]:
        lines.append(_row((_md(row["file_id"]), _md(row["path"]), _items(row["candidate_ids"]),
                           _md(row["read_status"]), _value(row["regular_file"]),
                           _value(row["observed_byte_size"]), _value(row["observed_sha256"]))))
    if not evidence["candidate_files"]:
        lines.append("| — | — | — | İzinli dosya gözlemi yok | — | — | — |")
    lines.extend([
        "", "Missing yalnız güvenli biçimde incelenmiş izinli path'teki yokluktur. Permission, reparse/type, hash/identity veya race hatası missing'e çevrilmez; kapalı hata üretir. Bir reference'ın izni aynı path'teki başka candidate binding'ine otomatik yetki vermez. SHA256 yalnız gözlenen byte kimliğidir; producer/Git veya compiler attestation değildir.", "",
        "### Context ve koşul sınırları", "",
        "- Ambiguous / unsupported path-context candidate: " + str(counts["ambiguous_path_context_candidate_count"]) + " / " + str(counts["unsupported_path_context_candidate_count"]), "",
    ])
    for row in evidence["candidates"]:
        lines.extend([
            "- " + _md(row["candidate_id"]) + ": " + _md(row["path_context"]["status"]) +
            "; nedenler " + _items(row["path_context"]["reason_codes"]) +
            "; lexical scope " + _items(row["lexical_scope"]) +
            "; condition ID'leri " + _items(row["condition_ids"]) +
            "; condition evaluation " + _md(row["path_context"]["condition_evaluation"]),
        ])
    lines.extend([
        "", "Condition metadata true/false değerlendirilmez; feature/target seçimi yapılmaz. Nested veya güvenilir relative-base kanıtı eksikse context olumluya yükseltilmez. Context desteği ve dosya varlığı ayrı gözlemdir; ikisi birlikte bile compiler resolution değildir.", "",
        "## 3. Tüm external reference'ların triage durumu", "",
        "Birincil sınıflar reference'ı tek kez sayar. İkincil durumlar present/missing/not-allowlisted/context belirsizliklerini birlikte korur ve örtüşebilir; bu sütunlar toplanarak yeni dosya veya reference sayısı üretilmez. Unselected reference not_examined'dır; module missing değildir. Inline module ve ordinary macro external paydasına eklenmez.", "",
        "| Birincil triage | Reference |", "| --- | ---: |",
    ])
    for row in triage_counts["by_primary_status"]:
        lines.append(_row((_md(row["status"]), str(row["reference_count"]))))
    lines.extend(["", "| Örtüşebilen ikincil durum | Reference |", "| --- | ---: |"])
    for row in triage_counts["by_status"]:
        lines.append(_row((_md(row["status"]), str(row["reference_count"]))))
    lines.extend(["", "| Phase29 reference | Source / modül / line:column | Seçildi | Birincil / ikincil durumlar | Candidate ID'leri |",
                  "| --- | --- | --- | --- | --- |"])
    for row in triage["references"]:
        reference = row["reference"]
        position = reference["position"]
        lines.append(_row((_md(reference["reference_id"]),
                           _md(reference["source_file_reference"]) + " / " + _value(reference["declared_module_name"]) +
                           " / " + str(position["line"]) + ":" + str(position["column"]),
                           "Evet" if row["selected"] else "Hayır", _md(row["primary_status"]) + " / " + _items(row["statuses"]),
                           _items(row["candidate_ids"]))))
    lines.extend(["", "### Seçili reference ayrıntıları", ""])
    for row in triage["references"]:
        if not row["selected"]:
            continue
        item_counts = row["counts"]
        lines.extend([
            "- Reference: " + _md(row["reference"]["reference_id"]),
            "- Bildirilen / allowlisted / incelenen candidate: " + str(item_counts["declared_candidate_count"]) + " / " + str(item_counts["allowlisted_candidate_count"]) + " / " + str(item_counts["examined_candidate_count"]),
            "- Present / missing / not-allowlisted / incelenmemiş candidate: " + str(item_counts["present_candidate_count"]) + " / " + str(item_counts["missing_candidate_count"]) + " / " + str(item_counts["not_allowlisted_candidate_count"]) + " / " + str(item_counts["unexamined_candidate_count"]),
            "- Context çözülememiş candidate: " + str(item_counts["path_context_unresolved_candidate_count"]),
            "- Condition ID'leri / değerlendirme: " + _items(row["condition_ids"]) + " / " + _md(row["condition_evaluation"]),
            "- Alternatif sınırı: " + _md(row["unexamined_alternatives"]),
            "- Sonraki gerçek doğrulama ihtiyacı: " + _items(row["next_validation"]), "",
        ])
    lines.extend([
        "Alternatives_exhaustive=false; resolved_file=false; compiler_resolution_verified=false bütün kayıtlarda kalır. Bir present candidate yanında unread/unsupported alternatif varsa bu durum tamamlandı sayılmaz. Triage öncelik, güvenlik/risk puanı, SLA veya yayın/uygulama kararı değildir.", "",
        "## 4. Phase24 F kapsamı ve korunmuş engeller", "",
        "- Global F kataloğu / component source_file_refs birleşimi: " + str(coverage_counts["global_f_catalog_count"]) + " / " + str(coverage_counts["component_referenced_file_count"]),
        "- Listed / not-listed / scope-unknown candidate ilişkisi: " + str(coverage_counts["listed_candidate_count"]) + " / " + str(coverage_counts["not_listed_candidate_count"]) + " / " + str(coverage_counts["scope_unknown_candidate_count"]),
        "- Eski kimliği matched / mismatched / not-compared candidate: " + str(coverage_counts["identity_matched_candidate_count"]) + " / " + str(coverage_counts["identity_mismatched_candidate_count"]) + " / " + str(coverage_counts["not_compared_candidate_count"]),
        "- Korunan kesin owner / dependency / belirsiz D: " + str(coverage_counts["source_definite_owner_count"]) + " / " + str(coverage_counts["source_dependency_record_count"]) + " / " + str(coverage_counts["source_ambiguous_dependency_record_count"]), "",
        "Yalnız present/hash gözlemi olan candidate, root/pin/path ve eski byte/hash kanıtıyla karşılaştırılır. Unread veya missing dosya gözlenen inventory membership kazanmaz. F üyeliği, kimlik eşitliği, component F referansı ve component ownership ayrı tutulur. F'de yokluk excluded/unused değildir; genel selected/excluded/metadata_only bayrağı uydurulmaz.", "",
        "| Candidate | File ID | F bağı | Global F üyeliği | Eski kimlik karşılaştırması | Component F durumu | Ownership |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in coverage["candidates"]:
        lines.append(_row((_md(row["candidate_id"]), _value(row["file_id"]), _value(row["phase24_source_reference"]),
                           _md(row["phase24_catalog_status"]), _md(row["phase24_identity_status"]),
                           _md(row["component_source_status"]) + " / " + _items(row["referencing_component_ids"]),
                           _md(row["component_ownership_status"]))))
    if not coverage["candidates"]:
        lines.append("| — | — | — | Candidate projection yok | — | — | — |")
    boundary = coverage["phase28_delta_boundary"]
    lines.extend([
        "", "- Korunan uygulanmamış Phase28 proposal: " + str(boundary["proposal_count"]),
        "- application_authorized=false; application_performed=false; phase24_inventory_modified=false.", "",
        "| Korunan Phase28 proposal | EPF | Root-relative kaynak |", "| --- | --- | --- |",
    ])
    for row in boundary["proposals"]:
        lines.append(_row((_md(row["proposal_reference"]), _md(row["source_file_reference"]), _md(row["path"]))))
    license_counts = coverage["license_boundary_counts"]
    lines.extend([
        "", "- Ayrı lisans subject / unknown: " + str(license_counts["source_license_record_count"]) + " / " + str(license_counts["base_unknown_license_count"]),
        "- Önceki fresh evidence var / eksik: " + str(license_counts["evidence_present_record_count"]) + " / " + str(license_counts["missing_evidence_record_count"]),
        "- İnsan incelemesi gerekli / açık blocker: " + str(license_counts["human_review_required_record_count"]) + " / " + str(license_counts["source_blocker_count"]), "",
        "Yeni F, component source listesi veya Phase28 delta yazılmaz. Candidate gözlemi Phase29'un önceki resolved_file=false ve 0 kesin file-binding sonucunu değiştirmez. Eski scoped MIT beyanları yeni ilişkilere yayılmaz; unknown lisans ve insan/release engelleri kapanmaz.", "",
        "## 5. Artefact kimlikleri ve güven sınırı", "",
        "| Kaynak grubu | Rol | Sözleşme | Byte | SHA256 |", "| --- | --- | --- | ---: | --- |",
    ])
    for group, roles in _SOURCE_GROUPS:
        for role in roles:
            row = source[group][role]
            lines.append(_row((_md(group), _md(role), _value(row["schema_version"], "Markdown / şema yok"),
                               str(row["bytes"]), _md(row["sha256"]))))
    lines.extend([
        "", "demo_only=true; " + "; ".join(flag + "=false" for flag in FALSE_FLAGS) + ".", "",
        "Inspector yalnız beş yeni dosyanın kaydedilmiş model/ref/count/Markdown ve gerçek byte/hash tutarlılığını inceler. Candidate dosyası, eski Rust lexical kaynağı veya eski artefact yeniden açılmaz; lexer/compiler çalıştırılmaz. content_consistent upstream lexical truth, producer/Git attestation, compiler resolution, source completeness veya build/release kabulü değildir.", "",
        "Hash parçaları en fazla 64 KiB, candidate dosyası 512 KiB/toplam okuma 4 MiB, metadata toplamı 8 MiB; yeni JSON 2 MiB ve bu Markdown 256 KiB ile sınırlıdır. Sessiz truncation yapılmaz. Rust body decode/parse edilmez; snippet, ham JSON, mutlak source root veya dinamik URL rapora taşınmaz. Relative path/module identifier da hassas olabilir; allowlist secret detection/anonimlik garantisi değildir.", "",
        "NOT_RUN: hostile/duplicate/malformed JSON; UTF-8/Unicode ve manipüle reference/parent/path/digest; traversal/symlink/junction/reparse/hardlink; TOCTOU/permission/filesystem/değişim yarışı; byte/kayıt saldırıları; crash/partial write/power-loss; repeat determinism; Rust AST/compiler/module resolution; cfg/feature/target/macro expansion; module closure/build/runtime; producer/Git attestation; ownership; hukukî/uzman/kurumsal/release/production kabulü. Önceki açık kapılar korunur.", "",
        "Evidence sınırlamaları: " + _items(evidence["limitations"]),
        "Triage sınırlamaları: " + _items(triage["limitations"]),
        "Coverage sınırlamaları: " + _items(coverage["limitations"]), "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("module_candidate_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_summary",)
