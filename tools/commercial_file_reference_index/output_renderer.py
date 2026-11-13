"""Pure inert Markdown for the closed disclosed-index/lookup/receipt models."""
from __future__ import annotations

import html

from index_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_COUNT_LABELS = {
    "requested_reference_count": "Kaynak inbox referansı",
    "provided_reference_count": "Kaynak provided referansı",
    "withheld_reference_count": "Kaynak withheld referansı — yalnız toplam",
    "unavailable_reference_count": "Kaynak kapsam dışı referansı — yalnız toplam",
    "projection_count": "Kaynak izinli projection ilişkisi",
    "unique_candidate_count": "Kaynak benzersiz candidate",
    "unique_file_count": "Kaynak benzersiz metadata File ID",
    "present_projection_count": "Kaynak kayıtlı present projection",
    "absence_projection_count": "Kaynak kayıtlı absence projection",
}
_INDEX_COUNT_LABELS = {
    "file_count": "Görünür metadata File ID",
    "reference_count": "İndeksteki provided referans",
    "candidate_count": "İndeksteki benzersiz candidate",
    "projection_count": "İndeksteki projection ilişkisi",
    "present_projection_count": "Kayıtlı present projection",
    "absence_projection_count": "Kayıtlı absence projection",
}
_LOOKUP_COUNT_LABELS = {
    "requested_file_count": "İstenen File ID",
    "matched_file_count": "Görünür indekste eşleşen File ID",
    "not_in_disclosed_index_count": "Ortak görünür-kapsam-dışı sonucu",
    "returned_reference_count": "Bir kez dönen provided referans",
    "returned_projection_count": "Bütün referans paketlerinde dönen projection",
    "returned_candidate_count": "Dönen benzersiz candidate",
    "returned_present_projection_count": "Dönen kayıtlı present projection",
    "returned_absence_projection_count": "Dönen kayıtlı absence projection",
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


def render_index_summary(index: dict, lookup: dict, receipt: dict) -> bytes:
    """Render validated copies only; no source read, guard or physical lookup."""
    index, lookup, receipt = validate_relationships(index, lookup, receipt)
    request = lookup["request"]
    lines = [
        "# Offline disclosed File ID ve ters referans lookup", "", _md(DEMO_LABEL), "",
        "Bu indeks yalnız doğrulanmış typed inbox'taki provided referansların mevcut izinli projection'larından oluşur. File ID metadata kimliğidir; fiziksel inode, Windows File ID, kaynak path veya evrensel dosya kimliği değildir. Kaynak dosyalar yeniden gözlenmedi; indeksleme yeni disclosure yetkisi oluşturmaz.", "",
        "## 1. Açık istek ve gerçek Phase36 artefact bağı", "",
        "- İndeks sözleşmesi: " + _md(index["schema_version"]),
        "- Lookup sözleşmesi: " + _md(lookup["schema_version"]),
        "- Receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Kaynak inbox sözleşmesi: " + _md(index["source_schema_version"]),
        "- Gerçek Phase36 inbox dosyasının SHA256 değeri: " + _md(index["source_inbox_sha256"]),
        "- Gerçek Phase36 manifest dosyasının SHA256 değeri: " + _md(index["source_manifest_sha256"]),
        "- Yerel request kimliği: " + _md(request["request_reference"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Request'in Phase36 inbox SHA256 beklentisi: " + _md(request["source_inbox_sha256"]),
        "- Request'in Phase36 manifest SHA256 beklentisi: " + _md(request["source_manifest_sha256"]), "",
        "Yalnız açıkça istenen File ID'ler:", "",
    ]
    lines.extend("- " + _md(file_id) for file_id in request["requested_file_ids"])
    lines.extend([
        "", "Aşağıdaki beş kimlik gerçek Phase36 input dosyalarına aittir; inbox içine kaydedilmiş eski Phase35 provenance descriptor'larıyla karıştırılmaz. Sabit dosya adları path takip etme veya yeni input keşfi yetkisi değildir.", "",
        "| Kaynak artefact | Kaynak sözleşme | Gerçek byte | Gerçek SHA256 |",
        "| --- | --- | ---: | --- |",
    ])
    for artifact in index["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _value(artifact["schema_version"]),
                           _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend(["", "## 2. Ayrı kaynak, indeks ve lookup paydaları", "", "### Tam kaynak inbox toplamları", ""])
    _counts(lines, _SOURCE_COUNT_LABELS, index["source_counts"])
    lines.extend(["", "### Yalnız görünür dosya indeksi", ""])
    _counts(lines, _INDEX_COUNT_LABELS, index["counts"])
    lines.extend(["", "### Yalnız bu açık lookup sonucu", ""])
    _counts(lines, _LOOKUP_COUNT_LABELS, lookup["counts"])
    lines.extend([
        "", "Kaynak withheld/kapsam dışı değerleri yalnız aggregate sayımdır; bu referanslar file index'e ve olumlu lookup sonuçlarına alınmaz. File/reference/candidate/projection ilişkileri ayrı paydalardır. Bir referansın birden fazla File ID ile eşleşmesi referansı veya bütün projection paketini çoğaltmaz.", "",
        "## 3. Yalnız açıklanmış File ID ilişkileri", "",
        "| Metadata File ID | Görünür reference ID'leri | Görünür candidate ID'leri |",
        "| --- | --- | --- |",
    ])
    for record in index["file_records"]:
        lines.append(_row((_md(record["file_id"]), _items(record["reference_ids"]), _items(record["candidate_ids"]))))
    lines.extend([
        "", "Projection kimliği uydurulmaz; bağ mevcut üçlüyle gösterilir:", "",
        "| Reference | Candidate | Metadata File ID |", "| --- | --- | --- |",
    ])
    for record in index["file_records"]:
        for binding in record["projection_bindings"]:
            lines.append(_row((_md(binding["reference_id"]), _md(binding["candidate_id"]), _md(binding["file_id"]))))
    lines.extend([
        "", "Aynı File ID'nin gerçek çoklu görünür referans ilişkileri korunmalıdır. Duplicate veya çelişkili metadata sessiz birleştirilmez. Deterministik sıralama metadata görünümüdür; tekrar-determinism runtime kabulü değildir.", "",
        "## 4. İstenen File ID sonuçları", "",
        "| İstenen File ID | Ortak sonuç | Eşleşen görünür reference ID'leri |",
        "| --- | --- | --- |",
    ])
    for result in lookup["file_results"]:
        lines.append(_row((_md(result["file_id"]), _md(result["status"]), _items(result["reference_ids"]))))
    lines.extend([
        "", "not_in_disclosed_index yalnız görünür indeks içinde eşleşme olmadığını belirtir. Fiziksel yokluk, dosyanın bloke kayıtta bulunması veya başka kaynaktaki varlığı hakkında neden/kanıt vermez. Yanıt unknown ve görünür indeks dışı kimlikler için aynı durum ve boş reference listesidir.", "",
        "## 5. Tekilleştirilmiş bütün referans sonuçları", "",
        "| Görünür reference | Mevcut disclosure durumu | Bütün projection adedi | Eşleşen istenen File ID'ler | Yorumlama sınırlamaları |",
        "| --- | --- | ---: | --- | --- |",
    ])
    for result in lookup["reference_results"]:
        lines.append(_row((
            _md(result["reference_id"]), _md(result["disclosure_status"]), _md(result["projection_count"]),
            _items(result["matched_file_ids"]), _items(result["interpretation_limitations"]),
        )))
    for result in lookup["reference_results"]:
        lines.extend([
            "", "### " + _md(result["reference_id"]), "",
            "Eşleşme tek File ID üzerinden olsa bile referansın bütün mevcut izinli projection'ları birlikte korunur. İstenen File ID'lerle eşleşme listesi ayrı metadata'dır; projection kümesini daraltmaz.", "",
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
        "", "Projection alanları kaynak typed inbox'taki mevcut 11 alan/değerdir. Kayıtlı absence byte/hash null; integer count sıfırı, boş string veya sıfır-byte dosya ile aynı değildir. Absence projection'ına ait File ID görünür metadata ilişkisiyle eşleşebilir; bu fiziksel varlık sorgusu değildir. Upstream fresh kodları eski kayıt kodudur, yeni source gözlemi değildir.", "",
        "## 6. Receipt, mahremiyet ve güven sınırı", "",
        "Receipt içerik kapsamı: " + _md(receipt["content_scope"]),
        "İndeks sınırlamaları: " + _items(index["limitations"]),
        "Lookup sınırlamaları: " + _items(lookup["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "demo_only=true; trust_flags kapalı nesnesi: "
        + "; ".join(_md(flag) + "=" + _md(index["trust_flags"][flag]) for flag in FALSE_FLAGS) + ".", "",
        "Receipt yalnız beş gerçek Phase36 artefact kimliği/schema ve aggregate içerik kapsamını taşır; olumlu bloke metadata için ikinci audit kopyası yoktur. Hash iç byte bağıdır, dijital imza/producer authentication veya source freshness kanıtı değildir. Kaynak model ve bütün beraber tutarlı dosyalar yeniden hash'lenebileceğinden iç tutarlılık özgün kaynağın yetkisini kanıtlamaz.", "",
        "Yeni inspector yalnız beş yeni index/lookup/receipt/summary/manifest dosyasını okur. Phase36 inputlarını yeniden açmaz; source import davranışını bağımsız doğrulamaz. Phase35 CSV/kapsül/guard/native source açmaz. content_consistent yalnız yeni model/ref/file/candidate/whole-packet/count/MD ve dört payload byte/hash iç tutarlılığıdır.", "",
        "source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false korunur. Producer/source freshness/compiler/module closure/ownership/native/human/legal/customer/production/release otoritesi kazanılmaz. Kimlik/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.", "",
        "Kaynak path/root/physical identity, raw Rust/baseline/Phase35 CSV/kapsül ZIP'i, credential, exception veya bloke olumlu metadata taşınmaz. Kaynak JSON'daki path/URL yeni dosya açma yetkisi değildir. Kaynak kodu bağımlılığı eski runtime/veri/kapsül erişimiyle karıştırılmaz.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible File ID, duplicate/çelişkili projection, yanlış ref/file/candidate bağı, single-file full-reference runtime varyantı, shared-file multiple-reference, modified inbox, limit/permission/crash/partial write/repeat determinism, ikinci offline host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Kodda koruma olması bu runtime kabullerinin geçtiği anlamına gelmez. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("file_index_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_index_summary",)
