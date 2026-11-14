"""Pure bounded view of disclosed ALL-OF cohort witnesses."""
from __future__ import annotations

import html

from cohort_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_COUNT_LABELS = {
    "file_count": "Kayıtlı visible source File ID",
    "reference_count": "Kayıtlı visible source provided referansı",
    "candidate_count": "Kayıtlı visible source candidate",
    "projection_count": "Kayıtlı visible source projection",
    "present_projection_count": "Kayıtlı visible source present projection",
    "absence_projection_count": "Kayıtlı visible source absence projection",
}
_QUERY_COUNT_LABELS = {
    "required_file_count": "ALL-OF required File ID",
    "matched_reference_count": "Bir kez dönen eşleşmiş referans",
    "matched_projection_count": "Bütün eşleşmiş paketlerdeki projection",
    "matched_candidate_count": "Bütün eşleşmiş paketlerdeki candidate",
    "matched_present_projection_count": "Dönen kayıtlı present projection",
    "matched_absence_projection_count": "Dönen kayıtlı absence projection",
}


def _md(value: object) -> str:
    text = str(value).lower() if type(value) is bool else str(value)
    return "".join(
        " " if char in "\r\n\t"
        else "&#" + str(ord(char)) + ";" if char in _PUNCTUATION
        else html.escape(char, quote=True)
        for char in text
    )


def _value(value: object) -> str:
    return "null — kayıtlı değer yok" if value is None else _md(value)


def _items(values: list) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def _counts(lines: list[str], labels: dict, values: dict) -> None:
    lines.extend(["| Sayım | Adet |", "| --- | ---: |"])
    for key, label in labels.items():
        lines.append(_row((label, _md(values[key]))))


def render_cohort_summary(query: dict, witnesses: dict, receipt: dict) -> bytes:
    """Render validated closed copies only; no source read or new matching."""
    query, witnesses, receipt = validate_relationships(query, witnesses, receipt)
    request = query["request"]
    lines = [
        "# Offline disclosed ALL-OF cohort query", "", DEMO_LABEL, "",
        "Bu sonuç yalnız aynı görünür referansta bütün required File ID'lerin ve her dosya için istenen kayıtlı presence koşulunun sağlanmasını anlatır. cohort_condition_matched fiziksel dosyanın bugünkü durumunun doğrulandığı anlamına gelmez. Witness fiziksel/content/security/causal/source/compiler veya producer kanıtı değildir.", "",
        "## 1. Açık request ve kayıtlı presence koşulları", "",
        "- Query sözleşmesi: " + _md(query["schema_version"]),
        "- Witness sözleşmesi: " + _md(witnesses["schema_version"]),
        "- Receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Yerel request kimliği: " + _md(request["request_reference"]),
        "- Gerçek Phase38 JOIN SHA256: " + _md(query["source_phase38_join_sha256"]),
        "- Gerçek Phase38 manifest SHA256: " + _md(query["source_phase38_manifest_sha256"]), "",
        "| Required metadata File ID | Beklenen kayıtlı source_file_presence |",
        "| --- | --- |",
    ]
    for assertion in request["required_file_assertions"]:
        lines.append(_row((_md(assertion["file_id"]), _md(assertion["expected_source_file_presence"]))))
    lines.extend([
        "", "Gerçek owner presence enum'u present ve missing'dir; missing kayıtlı absence metadata'sıdır. Yeni absent enum'u veya bugünkü fiziksel file-state sorgusu oluşturulmaz. File ID metadata kimliğidir; inode/Windows File ID/path veya evrensel dosya kimliği değildir.", "",
        "ALL-OF doğrudan bütün required file visible-reference kümelerinin N-way kesişimini kullanır. Pairwise ortaklık transitif varsayılmaz: A+B ve B+C ayrı referanslarda eşleşiyor diye A+B+C için ortak referans oluşturulmaz. Her required file için gerçek projection ve kayıtlı presence eşliği gerekir; çelişki sessiz seçilmez.", "",
        "## 2. Gerçek beş Phase38 artefact kimliği", "",
        "Aşağıdaki current Phase38 JOIN/manifest kimlikleri, eski JOIN içine kaydedilmiş Phase37 source_index/source_manifest hash'leriyle karıştırılmaz. Dosya adları sabit transfer rolleridir; yeni path/URL takip etme yetkisi değildir.", "",
        "| Gerçek Phase38 artefact | Kaynak sözleşme | Gerçek byte | Gerçek SHA256 |",
        "| --- | --- | ---: | --- |",
    ])
    for artifact in receipt["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _value(artifact["schema_version"]),
                           _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend([
        "", "Receipt kaynak schema haritası:", "",
        "| Sabit source rolü | Kayıtlı schema |", "| --- | --- |",
    ])
    for artifact in receipt["source_artifacts"]:
        name = artifact["name"]
        lines.append(_row((_md(name), _value(receipt["source_schema_versions"][name]))))
    lines.extend(["", "## 3. Kaynak görünür kapsamı ve bu sorgu ayrı paydalardır", "", "### Kaynak JOIN içinde korunmuş visible source sayımları", ""])
    _counts(lines, _SOURCE_COUNT_LABELS, receipt["source_counts"])
    lines.extend(["", "### Bu ALL-OF sorgusu ve bütün witness paketleri", ""])
    _counts(lines, _QUERY_COUNT_LABELS, query["counts"])
    lines.extend([
        "", "Receipt source_counts, Phase38 JOIN'in inherited visible altı sayımıdır; pairwise join'in on sayımı veya eski global/bloke toplamları değildir. Query/witness projection sayımları yalnız supporting üçlüleri değil, dönen referansın bütün izinli projection listesini sayar.", "",
        "## 4. Görünür kapsam içindeki query sonucu", "",
        "Kayıtlı query_status: " + _md(query["query_status"]),
        "Eşleşen görünür reference ID'leri: " + _items(query["matched_reference_ids"]), "",
        "matched_in_disclosed_scope yalnız bu kayıtlı ALL-OF/presence koşullarının sağlanmasıdır. no_match_in_disclosed_scope yalnız doğrulanmış Phase38 görünür kapsamda koşulların sağlanmadığını söyler; fiziksel yokluk veya başka kaynakta ilişkinin bulunmaması değildir. Yeni inspector kaynağa dönmediği için başka eşleşme bulunmadığını bağımsız kanıtlamaz.", "",
        "## 5. Gerçek supporting binding ve bütün referans witness'ları", "",
        "| Eşleşen reference | Mevcut disclosure durumu | Bütün required File ID'ler | Bütün projection adedi |",
        "| --- | --- | --- | ---: |",
    ])
    for result in witnesses["results"]:
        lines.append(_row((_md(result["reference_id"]), _md(result["disclosure_status"]),
                           _items(result["matched_file_ids"]), str(len(result["projections"])))))
    for result in witnesses["results"]:
        lines.extend([
            "", "### " + _md(result["reference_id"]), "",
            "Her required File ID için source projection'dan gelen gerçek destek üçlüleri:", "",
            "| Gerçek reference | Gerçek candidate | Gerçek metadata File ID |",
            "| --- | --- | --- |",
        ])
        for binding in result["supporting_projection_bindings"]:
            lines.append(_row((_md(binding["reference_id"]), _md(binding["candidate_id"]), _md(binding["file_id"]))))
        lines.extend([
            "", "Aşağıdaki liste yalnız koşula uyan projection'larla filtrelenmez; referansın bütün source izinli paketi, özgün sıra ve türleriyle korunur.", "",
            "| Reference | Candidate | Metadata File ID | Kayıtlı presence | Typed byte | Typed SHA256 | Upstream projection kodu |",
            "| --- | --- | --- | --- | ---: | --- | --- |",
        ])
        for projection in result["projections"]:
            lines.append(_row((
                _md(projection["reference_id"]), _md(projection["candidate_id"]), _md(projection["file_id"]),
                _md(projection["source_file_presence"]), _value(projection["observed_byte_size"]),
                _value(projection["observed_sha256"]), _md(projection["upstream_projection_kind"]),
            )))
        lines.extend([
            "", "| Candidate | Phase31 current observation kimliği | Phase31 comparison kimliği | Kayıtlı comparison durumu | Yorumlama sınırlamaları |",
            "| --- | --- | --- | --- | --- |",
        ])
        for projection in result["projections"]:
            lines.append(_row((
                _md(projection["candidate_id"]), _md(projection["phase31_current_observation_id"]),
                _md(projection["phase31_comparison_id"]), _md(projection["upstream_comparison_status"]),
                _items(projection["interpretation_limitations"]),
            )))
    lines.extend([
        "", "Witness zarfı yalnız common alanlar, current Phase38 iki digest, yeni strict request, eşleşmiş results/counts ve sınırlamalardır. Ham source catalog, eşleşmemiş full packet veya bloke kimlik/olumlu metadata çoğaltılmaz. Yeni projection/witness ID uydurulmaz.", "",
        "Kayıtlı missing projection'ının byte/hash alanları null kalır; integer count sıfırı veya sıfır-byte file değildir. Mevcut source tür/değerleri, observation/comparison kimlikleri ve limitation kodları yükseltilmez. Upstream fresh kodu eski metadata'dır; yeni observation veya TTL garantisi değildir.", "",
        "## 6. Receipt, trust ve yeni inspector sınırı", "",
        "Receipt içerik kapsamı: " + _md(receipt["content_scope"]),
        "Query sınırlamaları: " + _items(query["limitations"]),
        "Witness sınırlamaları: " + _items(witnesses["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "demo_only=true; trust_flags kapalı nesnesi: "
        + "; ".join(_md(flag) + "=" + _md(query["trust_flags"][flag]) for flag in FALSE_FLAGS) + ".", "",
        "Yeni inspector yalnız beş yeni query/witnesses/receipt/summary/manifest dosyasını okur. Phase38 source dosyalarını açmaz, cohort eşleşmesini veya bütün-source/no-other-matches durumunu bağımsız yeniden doğrulamaz. content_consistent yalnız yeni kapalı modellerin assertion/ref/binding/presence/count/MD ve dört payload byte/hash iç tutarlılığıdır. Whole-packet kaynak eşliği source-bound builder'ın sorumluluğudur; inspector yalnız yeni paketlerin iç ilişkisini denetler.", "",
        "Hash'ler imza, producer authentication veya Git attestation değildir; tutarlı girdiler birlikte değiştirilip yeniden hash'lenebilir. source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false korunur. Current filesystem, physical/source/compiler/ownership veya güvenlik ilişkisi ve human/legal/customer/production/release yetkisi kazanılmaz.", "",
        "Raw Rust/baseline/CSV/kapsül ZIP'i, source path/root/physical identity, credential, exception veya gerçek kullanıcı/müşteri bilgisi taşınmaz. ID/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir. Owner kodu bağımlılığı eski runtime/veri erişimi veya ikinci host kabulü değildir.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest/File ID/unknown/nonvisible, çelişkili presence, ALL-OF no-match, üç veya daha fazla file'da transitive pair yanılsaması, duplicate/bozuk binding/sahte witness, modified JOIN/LOOKUP, limit/permission/crash/partial write/repeat determinism/ikinci offline host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Kodda koruma runtime kabulü değildir. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir; file:// yasağı aşılmaz.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("cohort_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_cohort_summary",)
