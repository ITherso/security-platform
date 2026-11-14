"""Pure bounded Markdown for disclosed co-reference metadata only."""
from __future__ import annotations

import html

from co_reference_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_SOURCE_COUNT_LABELS = {
    "file_count": "Kaynak görünür File ID",
    "reference_count": "Kaynak provided referansı",
    "candidate_count": "Kaynak görünür candidate",
    "projection_count": "Kaynak izinli projection",
    "present_projection_count": "Kaynak kayıtlı present projection",
    "absence_projection_count": "Kaynak kayıtlı absence projection",
}
_JOIN_COUNT_LABELS = {
    "requested_file_count": "İstenen File ID",
    "matched_file_count": "Görünür indekste eşleşen File ID",
    "not_in_disclosed_index_file_count": "Ortak görünür-kapsam-dışı file sonucu",
    "pair_count": "Benzersiz file çifti",
    "shared_pair_count": "Ortak görünür referanslı çift",
    "no_shared_pair_count": "Görünür kesişimi boş çift",
    "not_in_disclosed_index_pair_count": "Ortak görünür-kapsam-dışı çift sonucu",
    "shared_reference_count": "Benzersiz ortak provided referansı",
    "supporting_binding_count": "Çiftler boyunca supporting binding occurrence",
    "unique_supporting_binding_count": "Benzersiz gerçek supporting binding üçlüsü",
}
_LOOKUP_COUNT_LABELS = {
    "reference_count": "Bir kez dönen ortak referans",
    "projection_count": "Bütün ortak paketlerde dönen projection",
    "candidate_count": "Dönen benzersiz candidate",
    "present_projection_count": "Dönen kayıtlı present projection",
    "absence_projection_count": "Dönen kayıtlı absence projection",
    "matched_file_count": "Ortak referanslara katılan istenen File ID",
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


def render_co_reference_summary(join: dict, lookup: dict, receipt: dict) -> bytes:
    """Render validated copies only; no source I/O or relationship inference."""
    join, lookup, receipt = validate_relationships(join, lookup, receipt)
    lines = [
        "# Offline disclosed co-reference join", "", DEMO_LABEL, "",
        "İki File ID'nin aynı açıklanmış referansta bulunması fiziksel dosya eşitliği, içerik eşitliği, güvenlik veya nedensel ilişki, source ownership ya da compiler/module resolution değildir. Bu çalışma yalnız doğrulanmış görünür metadata kümeleri ve gerçek projection bağları üzerinde co-reference kesişimi gösterir.", "",
        "## 1. Gerçek Phase37 source bağı ve açık File ID seçimi", "",
        "- Join sözleşmesi: " + _md(join["schema_version"]),
        "- Lookup sözleşmesi: " + _md(lookup["schema_version"]),
        "- Receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Kaynak indeks sözleşmesi: " + _md(join["source_schema_version"]),
        "- Gerçek Phase37 index dosyasının SHA256 değeri: " + _md(join["source_index_sha256"]),
        "- Gerçek Phase37 manifest dosyasının SHA256 değeri: " + _md(join["source_manifest_sha256"]), "",
        "Yalnız açıkça istenen metadata File ID'ler:", "",
    ]
    lines.extend("- " + _md(file_id) for file_id in join["requested_file_ids"])
    lines.extend([
        "", "Bu kaynak kimlikleri beş gerçek Phase37 input dosyasına aittir; eski embedded Phase36 veya Phase35 provenance hash'leri yerine kullanılmaz. File ID inode/Windows File ID/path veya evrensel fiziksel dosya kimliği değildir. Source dosyalar yeniden gözlenmedi.", "",
        "| Kaynak artefact | Kaynak sözleşme | Gerçek byte | Gerçek SHA256 |",
        "| --- | --- | ---: | --- |",
    ])
    for artifact in join["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _value(artifact["schema_version"]),
                           _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend(["", "## 2. Ayrı source, join ve lookup sayımları", "", "### Kaynak indeksin yalnız görünür kapsamı", ""])
    _counts(lines, _SOURCE_COUNT_LABELS, join["source_counts"])
    lines.extend(["", "### Açık pairwise join kapsamı", ""])
    _counts(lines, _JOIN_COUNT_LABELS, join["counts"])
    lines.extend(["", "### Bütün ortak referans paketlerinin lookup kapsamı", ""])
    _counts(lines, _LOOKUP_COUNT_LABELS, lookup["counts"])
    lines.extend([
        "", "Source sayımları yalnız Phase37 görünür indeksinin altı paydasıdır; eski global inbox/bloke toplamları buraya kopyalanmaz. Aynı gerçek üçlü farklı çiftleri destekleyebilir: occurrence sayımı ile unique supporting binding sayımı ayrıdır. Aynı çift içinde duplicate binding reddedilir; çiftler arasında gerçek tekrar tek başına hata değildir.", "",
        "## 3. İstenen file'ların görünür referans kümeleri", "",
        "| İstenen File ID | Görünür indeks sonucu | Görünür reference ID kümesi |",
        "| --- | --- | --- |",
    ])
    for result in join["file_results"]:
        lines.append(_row((_md(result["file_id"]), _md(result["status"]), _items(result["visible_reference_ids"]))))
    lines.extend([
        "", "not_in_disclosed_index ortak görünür-kapsam-dışı yanıtıdır. Fiziksel yokluk, bloke kayıtta bulunma veya başka kaynaktaki varlık hakkında neden/kanıt vermez. Bilinen görünür metadata ile kayıtlı absence aynı fiziksel sorgu değildir.", "",
        "## 4. Her benzersiz File ID çifti ve gerçek supporting binding'ler", "",
        "| Sol File ID | Sağ File ID | Yalnız görünür ilişki sonucu | Ortak reference ID'leri |",
        "| --- | --- | --- | --- |",
    ])
    for pair in join["pair_results"]:
        lines.append(_row((_md(pair["left_file_id"]), _md(pair["right_file_id"]),
                           _md(pair["relationship_status"]), _items(pair["shared_reference_ids"]))))
    for pair in join["pair_results"]:
        lines.extend([
            "", "### Çift: " + _md(pair["left_file_id"]) + " + " + _md(pair["right_file_id"]),
            "", "Kayıtlı ilişki: " + _md(pair["relationship_status"]), "",
        ])
        if not pair["supporting_projection_bindings"]:
            lines.extend(["Bu görünür çift sonucu için supporting projection binding sunulmadı.", ""])
            continue
        lines.extend([
            "Aşağıdakiler kaynakta mevcut üçlülerdir; yeni projection ID oluşturulmaz.", "",
            "| Ortak reference | Gerçek candidate | Gerçek metadata File ID |",
            "| --- | --- | --- |",
        ])
        for binding in pair["supporting_projection_bindings"]:
            lines.append(_row((_md(binding["reference_id"]), _md(binding["candidate_id"]), _md(binding["file_id"]))))
    lines.extend([
        "", "shared_disclosed_reference yalnız iki görünür file kümesinin ortak provided referansı ve her iki taraftaki gerçek binding'leri demektir. no_shared_disclosed_reference yalnız bu görünür kapsamda kesişim bulunmamasıdır; dosyalar ilişkisizdir, farklı fiziksel dosyadır veya başka kaynakta ilişkileri yoktur sonucu çıkarılmaz. İsim/candidate/hash benzerliği ilişki üretmek için kullanılmaz.", "",
        "## 5. Tekilleştirilmiş bütün ortak referans paketleri", "",
        "| Ortak reference | Mevcut disclosure durumu | Eşleşen istenen File ID'ler | Bütün projection adedi |",
        "| --- | --- | --- | ---: |",
    ])
    for result in lookup["results"]:
        lines.append(_row((_md(result["reference_id"]), _md(result["disclosure_status"]),
                           _items(result["matched_file_ids"]), str(len(result["projections"])))))
    for result in lookup["results"]:
        lines.extend([
            "", "### " + _md(result["reference_id"]), "",
            "Bu ortak referansın bütün kaynak izinli projection kümesi korunur; yalnız istenen iki file'ın projection'larıyla filtrelenmez. Aynı referans birden fazla çiftle eşleşse de bir kez döner.", "",
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
        "", "Join içindeki reference_packets yalnız shared reference union'ının bütün eski provided paketleridir; iç all-or-nothing kontrolüne gerekli açık wire ekidir. Unshared full catalog veya bloke ID/metadata taşınmaz. Lookup'un dört result alanı dışında projection_count/reference limitation gibi gizli ek alan üretilmez; yukarıdaki adet gerçek projection listesinin uzunluğudur.", "",
        "Kayıtlı absence byte/hash null kalır; count integer sıfırı, boş string veya sıfır-byte source dosyası değildir. Absence metadata'sının bir co-reference bağında yer alması fiziksel varlık kanıtı değildir. Upstream fresh kodları eski kayıt kodudur; yeni source observation veya TTL garantisi değildir.", "",
        "## 6. Receipt, güven ve yeni inspector sınırı", "",
        "Receipt içerik kapsamı: " + _md(receipt["content_scope"]),
        "Join sınırlamaları: " + _items(join["limitations"]),
        "Lookup sınırlamaları: " + _items(lookup["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "demo_only=true; trust_flags kapalı nesnesi: "
        + "; ".join(_md(flag) + "=" + _md(join["trust_flags"][flag]) for flag in FALSE_FLAGS) + ".", "",
        "Receipt yalnız beş gerçek Phase37 identity/schema, visible source sayımları ve içerik kapsamını taşır. Bloke referans adı/kimliği/olumlu metadata veya eski global bloke aggregate sayımı içermez. Hash imza veya producer authentication değildir; bütün tutarlı girdiler beraber değiştirilip yeniden hash'lenebilir.", "",
        "Yeni inspector yalnız beş yeni join/lookup/receipt/summary/manifest dosyasını okur. Phase37 dosyalarını yeniden açmaz; co-reference ilişkisini özgün kaynaktan bağımsız yeniden doğrulamaz. Source import/CSV/kapsül/guard/native davranışı kabul edilmez. content_consistent yalnız yeni modellerin pair/binding/full-packet/count/MD ve dört payload byte/hash iç tutarlılığıdır.", "",
        "source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false korunur. Fiziksel/içerik/güvenlik/nedensel/source/compiler/ownership ilişkisi veya producer/human/legal/customer/production/release yetkisi kazanılmaz. Kimlik/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.", "",
        "Raw Rust/baseline/Phase35 CSV/kapsül ZIP'i, source path/root/physical identity, credential, exception veya gerçek kullanıcı/müşteri bilgisi taşınmaz. JSON URL/path yeni dosya okuma yetkisi değildir. Korunmuş owner kodu bağımlılığı eski runtime/veri erişimiyle veya gerçek ikinci host kabulüyle karıştırılmaz.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible File ID, no-shared-reference çifti, shared-file multiple-reference, duplicate/çelişkili binding veya sahte shared-reference, modified index, limit/permission/crash/partial write/repeat determinism/ikinci offline host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Koruma kodu bu runtime kabul kapılarının geçtiği anlamına gelmez. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir; file:// kısıtı korunur.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("co_reference_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_co_reference_summary",)
