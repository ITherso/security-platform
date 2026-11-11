"""Bounded inert Markdown for recorded Rust references and coverage boundaries."""
from __future__ import annotations

import html

from .source_graph_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 256 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_GROUPS = (
    ("composition_sources", ("inventory", "dependencies", "constraints", "summary", "manifest")),
    ("dependency_evidence_sources", ("evidence", "graph", "variants", "summary", "manifest")),
    ("entrypoint_sources", ("coverage", "delta", "variants", "summary", "manifest")),
)


def _md(value: object) -> str:
    return "".join(" " if char in "\r\n\t" else "&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _value(value: object, absent: str = "Mevcut sonuçta bulunmuyor") -> str:
    if value is None:
        return absent
    if type(value) is bool:
        return "true" if value else "false"
    return _md(value)


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def render_summary(ledger: dict, graph: dict, coverage: dict) -> bytes:
    validate_documents(ledger, graph, coverage)
    counts, projected = ledger["counts"], coverage["counts"]
    summaries = {row["source_file_reference"]: row for row in ledger["lexical_summaries"]}
    bindings = {row["reference_id"]: row for row in ledger["bindings"]}
    projected_refs = {row["reference_id"]: row for row in coverage["reference_coverage"]}
    source_reference = ledger["source_reference"]
    lines = [
        "# Rust kaynak referansları ve module coverage sınırı", "", _md(ledger["demo_label"]), "",
        "Bu çalışma gerçek dosya kimliğini, dar lexical gözlemi ve ayrı allowlisted file-binding metadata'sını gösterir. Bir external mod adı dosya yolu değildir. Graph compiler/module resolver sonucu, tam source completeness veya başarılı build kanıtı değildir.", "",
        "## 1. Gerçekten okunan Rust kaynakları", "",
        "- Yerel çalışma referansı: " + _md(source_reference["candidate_reference"]),
        "- Termivar / platform pin beyanı: " + _md(source_reference["source_commits"]["termivar"]) + " / " + _md(source_reference["source_commits"]["platform"]),
        "- Gözlenen kaynak baytı: " + str(counts["observed_source_bytes"]),
        "- Mevcut / eksik izinli dosya: " + str(counts["present_source_file_count"]) + " / " + str(counts["missing_source_file_count"]), "",
        "| Yerel source ID | Root-relative path | Okuma durumu | Gerçek bayt | Gerçek SHA256 | Lexical durum |",
        "| --- | --- | --- | ---: | --- | --- |",
    ]
    for source in ledger["source_files"]:
        summary = summaries.get(source["source_file_reference"])
        lines.append(_row((_md(source["source_file_reference"]), _md(source["path"]), _md(source["read_status"]),
                           _value(source["observed_byte_size"]), _value(source["observed_sha256"]),
                           "not_performed" if summary is None else _md(summary["lexical_status"]))))
    lines.extend([
        "", "Hash gözlemi ve lexical tarama ayrı aşamalardır. Kaynak gövdesi/snippet bu raporda veya teslim ZIP'inde bulunmaz. Hash ve pin beyanı producer/Git attestation değildir; izinli bir dosyanın okunması başka dosyalara okuma yetkisi vermez.", "",
        "### Kaydedilmiş lexical kapsam", "",
        "| Source | scan_complete | Token | Line / CRLF | Line / block comment | String / raw / byte / raw-byte | Char / lifetime | Opaque macro tree |",
        "| --- | --- | ---: | --- | --- | --- | --- | ---: |",
    ])
    for row in ledger["lexical_summaries"]:
        lines.append(_row((_md(row["source_file_reference"]), _value(row["scan_complete"]), str(row["token_count"]),
                           str(row["line_count"]) + " / " + str(row["crlf_count"]),
                           str(row["line_comment_count"]) + " / " + str(row["block_comment_count"]),
                           " / ".join(str(row[key]) for key in ("string_literal_count", "raw_string_literal_count", "byte_string_literal_count", "raw_byte_string_literal_count")),
                           str(row["character_literal_count"]) + " / " + str(row["lifetime_count"]),
                           str(row["opaque_macro_tree_count"]))))
    lines.extend([
        "", "scan_complete yalnız desteklenen lexical subset için kaydedilmiş tarama durumudur; Rust AST, macro expansion veya module closure değildir. CRLF tek newline sayılır; line_count trailing newline sonrasındaki boş satırı içerir ve CRLF sayısıyla aynı payda değildir. Opaque ordinary macro tree bir dinamik kaynak referansı sayılmaz. Kapanmamış/desteklenmeyen lexical bağlamda tam güvenilir source analizi iddiası üretilmez.", "",
        "## 2–3. Gözlenen bildirimler: external ve inline ayrımı", "",
        "- Kaynak referansı: " + str(counts["reference_count"]),
        "- External module declaration: " + str(counts["external_module_count"]),
        "- Inline module declaration: " + str(counts["inline_module_count"]),
        "- Koşul metadata'sına bağlı referans: " + str(counts["conditional_reference_count"]),
        "- Lexically bounded / partial-unverified dosya: " + str(counts["lexically_bounded_file_count"]) + " / " + str(counts["partial_unverified_file_count"]), "",
    ])
    for row in counts["by_reference_kind"]:
        lines.append("- " + _md(row["reference_kind"]) + ": " + str(row["reference_count"]))
    lines.extend([
        "", "External declaration yalnız kaynakta bir modül adı bildirildiğini belirtir; foo.rs/foo/mod.rs adayı üretilmez. Inline module aynı dosyadaki lexical scope'tur; external dosya değildir. Aynı isim farklı konum/scope/koşulda tek kayda birleştirilmez. Yorum ve string içindeki referans benzeri metin kod bildirimi sayılmaz.", "",
        "## 4–5. Açık literal path ve gerçek dosya bağı", "",
        "- Desteklenen açık literal source-reference: " + str(counts["explicit_literal_reference_count"]),
        "- Gözlenen allowlisted dosyaya kesin metadata bağı: " + str(counts["bound_file_reference_count"]), "",
        "Sade path attribute ve literal include farklı referans türleridir. Kesin fiziksel file-binding için güvenilir literal/relative base, exact allowlist ve gerçek dosya kimliği gerekir. include_str/include_bytes kaynak-modül kenarı değildir. Sıfır bound-file sonucu uydurma bir dosya kenarıyla yükseltilmez. Bütün reference.resolved_file alanları false kalır: ayrı gözlenen-file binding gerçek compiler resolution değildir.", "",
        "| Referans | Kaynak / konum (line:column; UTF-8 byte) | Tür / modül | Literal path | Binding | Bound file | Olası explicit adaylar |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for reference in ledger["references"]:
        binding = bindings[reference["reference_id"]]
        position = reference["position"]
        lines.append(_row((_md(reference["reference_id"]),
                           _md(reference["source_file_reference"]) + " / " + str(position["line"]) + ":" + str(position["column"]) + "; " + str(position["byte_offset"]),
                           _md(reference["reference_kind"]) + " / " + _value(reference["declared_module_name"]),
                           _value(reference["literal_relative_path"]), _md(binding["binding_status"]),
                           _value(binding["bound_file_reference"]), _items(binding["candidate_file_references"]))))
    if not ledger["references"]:
        lines.append("| — | — | Bu dar taramada referans kaydı yok | — | — | — | — |")
    lines.extend([
        "", "## 6. Çözülemeyen ilişkiler ve graph", "",
        "- File-binding'i çözülemeyen referans: " + str(counts["unresolved_reference_count"]),
        "- Graph source / static-reference / unresolved-reference düğümü: " + str(graph["counts"]["source_file_node_count"]) + " / " + str(graph["counts"]["reference_node_count"]) + " / " + str(graph["counts"]["unresolved_reference_node_count"]),
        "- Toplam düğüm / kenar: " + str(graph["counts"]["node_count"]) + " / " + str(graph["counts"]["edge_count"]), "",
        "| Kenar türü | Kesin | Olası | Çözülemeyen |",
        "| --- | ---: | ---: | ---: |",
    ])
    for row in graph["counts"]["by_edge_type"]:
        lines.append(_row((_md(row["edge_type"]), str(row["definite_edge_count"]), str(row["possible_edge_count"]), str(row["unresolved_edge_count"]))))
    lines.extend(["", "| Certainty | Kenar |", "| --- | ---: |"])
    for row in graph["counts"]["by_certainty"]:
        lines.append(_row((_md(row["certainty"]), str(row["edge_count"]))))
    lines.extend([
        "", "Kesin source_contains_reference kenarı yalnız recorded lexical gözlem ilişkisini belirtir. Literal naming ve observed-file binding ayrı kenarlardır. Graph'taki unresolved düğüm/kenar sayıları binding ve koşul belirsizliğini kapsayabilir; bir referansın iki belirsizliği bulunabilir. Bu sayımlar dosya yokluğu, farklı fiziksel dosya veya unique package sayısı değildir. Inline koşul belirsizliği external missing-file iddiası değildir.", "",
        "| Referans | Binding / yorumlama durumu | Lexical scope / parent inline | Belirsizlik nedenleri |",
        "| --- | --- | --- | --- |",
    ])
    for reference in ledger["references"]:
        projected_ref = projected_refs[reference["reference_id"]]
        binding = bindings[reference["reference_id"]]
        if binding["binding_status"] in ("bound_to_observed_file", "inline_not_external") and not reference["condition_ids"]:
            continue
        lines.append(_row((_md(reference["reference_id"]), _md(binding["binding_status"]) + " / " + _md(reference["interpretation_status"]),
                           _items(reference["lexical_scope"]) + " / " + _value(reference["parent_inline_reference"]),
                           _items(projected_ref["unresolved_reason_codes"]))))
    lines.extend([
        "", "## 7. Koşullar ve lexical tanılar", "",
        "- Kaydedilmiş condition attribute: " + str(counts["condition_count"]),
        "- Bu metadata'ya bağlı source-reference: " + str(counts["conditional_reference_count"]),
        "- Kaydedilmiş lexical tanı: " + str(counts["diagnostic_count"]), "",
        "cfg/cfg_attr metadata'sı true/false değerlendirilmez. Feature/target seçimi ve macro/env/build-time genişleme yapılmaz. Dinamik kaynak veya çözülemeyen path fiziksel missing_file anlamına gelmez. Attribute sayısı ile condition'a bağlı referans sayısı ayrı paydalardır.", "",
        "| Condition | Source / line:column | Tür / style | Değerlendirme | Span SHA256 |",
        "| --- | --- | --- | --- | --- |",
    ])
    for row in ledger["conditions"]:
        position = row["position"]
        lines.append(_row((_md(row["condition_id"]), _md(row["source_file_reference"]) + " / " + str(position["line"]) + ":" + str(position["column"]),
                           _md(row["kind"]) + " / " + _md(row["attribute_style"]), _md(row["evaluation_status"]), _md(row["span_sha256"]))))
    if not ledger["conditions"]:
        lines.append("| — | — | Bu dar taramada condition kaydı yok | not_performed | — |")
    for row in ledger["diagnostics"]:
        position = row["position"]
        lines.extend(["", "- Tanı " + _md(row["diagnostic_id"]) + ": " + _md(row["code"]) + "; " + _md(row["source_file_reference"]) +
                      " line " + str(position["line"]) + ", column " + str(position["column"]) + ", byte " + str(position["byte_offset"]) +
                      "; ilgili referans " + _value(row["reference_id"])])
    lines.extend([
        "", "Desteklenen lexical sözdizimi ile bu kaynaklarda gerçekten gözlenen sözdizimi ayrı tutulur. Burada kaydı bulunmayan path/include/nested-comment/macro olayı pozitif fixture veya kabul başarısı değildir.", "",
        "## 8. Phase24 F membership ve yeni kaynak gözlemi", "",
        "- Global F kataloğu / component referans birleşimi: " + str(projected["global_f_catalog_count"]) + " / " + str(projected["component_referenced_file_count"]),
        "- Okunan allowlisted kaynak içinde global F'de olmayan dosya: " + str(projected["files_not_in_global_f_catalog_count"]),
        "- Eski dosya kimliğiyle uyuşmazlık: " + str(projected["files_with_identity_mismatch_count"]), "",
        "| Source / EPF | F bağı | Global membership | Eski kimlik karşılaştırması | Component F durumu | Yeni kaynak gözlemi | Ownership |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in coverage["source_files"]:
        lines.append(_row((_md(row["source_file_reference"]) + " / " + _value(row["entrypoint_reference"]),
                           _value(row["phase24_source_reference"]), _md(row["phase24_catalog_status"]), _md(row["phase24_identity_status"]),
                           _md(row["component_source_status"]), _md(row["source_inventory_status"]), _md(row["component_ownership_status"]))))
    lines.extend([
        "", "F satırlarında genel selected/excluded/metadata_only alanı yoktur; yeni bayrak atanmaz. Component referansında bulunmamak excluded/unused değildir; bulunmak runtime inclusion değildir. Katalog üyeliği ve byte/hash eşitliği ayrı kanıttır. Envanter boşluğu mevcut dosyanın fiziksel olarak bulunmadığını söylemez.", "",
        "## 9. Korunan Phase28 entry-point ve uygulanmamış delta katmanı", "",
        "- Korunan EPF kaydı: " + str(len(coverage["phase28_entrypoints"])),
        "- Uygulanmamış global Phase28 delta: " + str(projected["phase28_unapplied_delta_count"]), "",
        "| EPF / source | Cargo target | Manifest | Byte / SHA256 kimliği |",
        "| --- | --- | --- | --- |",
    ])
    for row in coverage["phase28_entrypoints"]:
        lines.append(_row((_md(row["entrypoint_reference"]) + " / " + _md(row["source_file_reference"]), _md(row["target_reference"]),
                           _md(row["manifest_reference"]), str(row["bytes"]) + " / " + _md(row["sha256"]))))
    lines.extend(["", "| Korunan proposal | EPF | Kaynak path | Uygulama yetkisi / uygulandı / inventory modified / ownership verified |",
                  "| --- | --- | --- | --- |"])
    for row in coverage["phase28_deltas"]:
        lines.append(_row((_md(row["proposal_reference"]), _md(row["source_file_reference"]), _md(row["path"]), "false / false / false / false")))
    lines.extend([
        "", "Bu yeni graph Phase28'in yerine geçmez ve eski target coverage durumunu metadata'da bulunmadığı yerden tahmin etmez. Mevcut proposal'lar uygulanmaz; yeni modül kaynak boşluğu yalnız Phase29 gözlemidir. Yeni F veya Phase28 delta kaydı oluşturulmaz. Kaynak referansı component ownership düzeltmesi değildir.", "",
        "## 10. Açık module closure, sahiplik ve kabul sınırları", "",
        "- Korunan kesin manifest owner: " + str(projected["source_definite_owner_count"]),
        "- Korunan dependency / belirsiz D kaydı: " + str(projected["source_dependency_record_count"]) + " / " + str(projected["source_ambiguous_dependency_record_count"]),
    ])
    license_counts = coverage["license_boundary_counts"]
    lines.extend([
        "- Ayrı lisans subject / unknown: " + str(license_counts["source_license_record_count"]) + " / " + str(license_counts["base_unknown_license_count"]),
        "- Önceki fresh evidence var / eksik: " + str(license_counts["evidence_present_record_count"]) + " / " + str(license_counts["missing_evidence_record_count"]),
        "- İnsan incelemesi gerekli / açık blocker: " + str(license_counts["human_review_required_record_count"]) + " / " + str(license_counts["source_blocker_count"]), "",
        "Bütün gözlenen referanslar bir dosyaya bağlansa bile macro, generated source, koşullu derleme ve desteklenmeyen Rust semantiği nedeniyle module closure/source completeness doğrulanmış olmaz. Dosya/ref graph'ı binary içeriği, güvenlik değerlendirmesi veya lisans kanıtı değildir. Önceki scoped MIT beyanları yeni kaynak ilişkilerine yayılmaz.", "",
        "demo_only=true; " + "; ".join(flag + "=false" for flag in FALSE_FLAGS) + ".", "",
        "### Açık önceki artefact kimlikleri", "",
        "| Grup | Rol | Sözleşme | Byte | SHA256 |", "| --- | --- | --- | ---: | --- |",
    ])
    for group, roles in _SOURCE_GROUPS:
        for role in roles:
            row = source_reference[group][role]
            lines.append(_row((_md(group), _md(role), _value(row["schema_version"], "Markdown / şema yok"), str(row["bytes"]), _md(row["sha256"]))))
    lines.extend([
        "", "Inspector yalnız beş yeni dosyadaki kaydedilmiş metadata'nın model/ref/count/Markdown ve gerçek byte/hash tutarlılığını değerlendirir. Rust kaynaklarını veya eski artefact'ları yeniden okumaz; lexer/classifier çalıştırmaz. content_consistent lexical yorumun Rust diline göre doğruluğu veya module closure kabulü değildir.", "",
        "NOT_RUN: hostile/duplicate/malformed JSON; UTF-8/BOM kenarları; kapanmamış string/comment; karmaşık raw delimiter; char/lifetime; macro token tree/procedural macro; cfg_attr path alternatifleri; desteklenmeyen lexical; AST/module resolution/generated source/feature-target; traversal/symlink/junction/reparse/hardlink; TOCTOU/filesystem race; source/hash manipülasyonu; token/node/byte limitleri; crash/partial write/power-loss; repeat determinism; gerçek build/scanner/runtime; module closure/source completeness; producer/Git attestation; component owner; uzman/hukukî/release/production kabulü. Önceki açık kapılar korunur.", "",
        "Hash okuma parçaları en fazla 64 KiB; kaynak dosyası 512 KiB/toplam Rust 1 MiB; eski artefact toplamı 12 MiB; yeni JSON 2 MiB ve bu Markdown 256 KiB ile sınırlıdır. Limit aşımında sessiz truncation yoktur. Metadata allowlist'i secret detection/anonimleştirme garantisi değildir; kısa path ve identifier bilgisi de hassas olabilir.", "",
        "Sınırlamalar: " + _items(ledger["limitations"]), "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("rust_source_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_summary",)
