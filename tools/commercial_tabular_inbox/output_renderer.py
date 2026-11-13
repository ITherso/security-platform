"""Pure bounded view of the closed inbox/query/receipt relationship."""
from __future__ import annotations

import html

from inbox_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_relationships,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_COUNT_LABELS = {
    "requested_reference_count": "Referans",
    "provided_reference_count": "Sınırlı metadata verilen referans",
    "withheld_reference_count": "Mevcut guard nedeniyle metadata verilmeyen referans",
    "unavailable_reference_count": "Mevcut kapsamda metadata bulunmayan referans",
    "projection_count": "Projection ilişkisi",
    "unique_candidate_count": "Benzersiz candidate",
    "unique_file_count": "Benzersiz file",
    "present_projection_count": "Kayıtlı present projection ilişkisi",
    "absence_projection_count": "Kayıtlı absence projection ilişkisi",
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


def render_inbox_summary(inbox: dict, query: dict, receipt: dict) -> bytes:
    """Render validated copies only; never read a CSV, capsule or source path."""
    inbox, query, receipt = validate_relationships(inbox, query, receipt)
    request = query["request"]
    lines = [
        "# Offline typed tabular inbox ve reference query", "", _md(DEMO_LABEL), "",
        "Typed reference/projection kayıtları gerçekten parse edilmiş canonical CSV hücrelerinden gelir. Phase35 dataset JSON yalnız sahip sözleşmesi ve alan/tür/değer eşliği için karşılaştırma kaynağıdır; JSON kayıtlarını kopyalamak CSV import yerine geçmez. Kaynak kapsül, Phase31/32 guard veya native dosya açılmaz.", "",
        "## 1. Kapalı model ve açık sorgu isteği", "",
        "- Inbox sözleşmesi: " + _md(inbox["schema_version"]),
        "- Query sözleşmesi: " + _md(query["schema_version"]),
        "- Receipt sözleşmesi: " + _md(receipt["schema_version"]),
        "- Kaynak dataset sözleşmesi: " + _md(inbox["source_dataset_schema"]),
        "- Kaynak manifest sözleşmesi: " + _md(receipt["source_manifest_schema"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Yerel request kimliği: " + _md(request["request_reference"]),
        "- Request'in kaynak manifest SHA256 beklentisi: " + _md(request["source_manifest_sha256"]), "",
        "Yalnız açıkça istenen reference ID'leri:", "",
    ]
    lines.extend("- " + _md(ref) for ref in request["requested_reference_ids"])
    lines.extend([
        "", "Query yalnız içe alınmış inbox kayıtlarını kullanır. Unknown/duplicate ID, query ifadesi, yeni candidate, override veya keyfî dosya yolu kabul otoritesi değildir. Referans içindeki izinli projection kümesi bütünüyle sunulur; bloke referansta projection listesi boş kalır.", "",
        "## 2. Kaydedilmiş beş Phase35 artefact kimliği", "",
        "Bu adlar sabit aktarım dosyası rolleridir; bu özet herhangi bir path/URL takip etmez. Byte/SHA256 içerik kimliğidir; üretici imzası veya source freshness kanıtı değildir.", "",
        "| Kaynak artefact adı | Kayıtlı byte | Kayıtlı SHA256 |",
        "| --- | ---: | --- |",
    ])
    for artifact in inbox["source_artifacts"]:
        lines.append(_row((_md(artifact["name"]), _md(artifact["bytes"]), _md(artifact["sha256"]))))
    lines.extend([
        "", "- Query'nin kaynak manifest adı: " + _md(query["source_manifest"]["name"]),
        "- Query'nin kaynak manifest byte: " + _md(query["source_manifest"]["bytes"]),
        "- Query'nin kaynak manifest SHA256: " + _md(query["source_manifest"]["sha256"]), "",
        "| Sayım | İçe alınmış inbox | Açık query sonucu |",
        "| --- | ---: | ---: |",
    ])
    for key, label in _COUNT_LABELS.items():
        lines.append(_row((label, _md(inbox["counts"][key]), _md(query["counts"][key]))))
    lines.extend([
        "", "Import kapsamı ve query kapsamı ayrı paydalardır. Referans, projection ilişkisi, benzersiz candidate ve benzersiz file sayıları birbirinin yerine geçmez. CSV header satırı veri sayısına dahil değildir; sayımlar kaynak dosya taraması veya risk skoru değildir.", "",
        "## 3. CSV'den içe alınmış referans kayıtları", "",
        "| Reference | Korunan disclosure durumu | Typed projection sayısı | Yorumlama sınırlamaları |",
        "| --- | --- | ---: | --- |",
    ])
    for record in inbox["reference_records"]:
        lines.append(_row((
            _md(record["reference_id"]), _md(record["disclosure_status"]),
            _md(record["projection_count"]), _items(record["interpretation_limitations"]),
        )))
    lines.extend([
        "", "| İçe alınmış reference | İzinli typed candidate ilişkileri |",
        "| --- | --- |",
    ])
    for link in inbox["reference_projection_links"]:
        lines.append(_row((_md(link["reference_id"]), _items(link["candidate_ids"]))))
    lines.extend([
        "", "Boş candidate ilişkisi otomatik source missing anlamına gelmez. Mevcut withheld/kapsam dışı durumun projection listesi ve sayısı ayrı doğrulanır. Referans kaydı bulunması olumlu file metadata açıklama yetkisi değildir; bloke olumlu alt bilgiler inbox/query/receipt/audit alanına kopyalanmaz.", "",
        "## 4. Yalnız istenen referansların query sonuçları", "",
        "| Reference | Korunan disclosure durumu | Typed projection sayısı | Yorumlama sınırlamaları |",
        "| --- | --- | ---: | --- |",
    ])
    for result in query["results"]:
        lines.append(_row((
            _md(result["reference_id"]), _md(result["disclosure_status"]),
            _md(result["projection_count"]), _items(result["interpretation_limitations"]),
        )))
    for result in query["results"]:
        lines.extend(["", "### " + _md(result["reference_id"]), ""])
        if not result["projections"]:
            lines.extend(["Mevcut disclosure durumuna göre projection sunulmadı; olumlu child metadata yok.", ""])
            continue
        lines.extend([
            "| Reference | Candidate | File kimliği | Kayıtlı presence | Typed byte | Typed SHA256 | Upstream projection kodu |",
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
        "", "Typed null kayıtlı yokluk/raporlanmayan değerdir; integer sıfır veya boş string değildir. Boş string, string sıfır ve boş liste ayrı JSON tür/değerleridir; alan sözleşmesi izin vermiyorsa reddedilir. Mevcut Phase35 DATA hücre sözleşmesi boolean kabul etmez; false integer sıfıra dönüştürülmez. Ortak güven bayraklarındaki false ayrı, zorunlu boolean metadata'dır.", "",
        "## 5. Receipt ve canonical CSV reconciliation", "",
        "- Reference CSV header'ları: " + _items(receipt["csv_headers"]["reference"]),
        "- Projection CSV header'ları: " + _items(receipt["csv_headers"]["projection"]),
        "- İçe alınmış reference veri satırı: " + _md(receipt["csv_rows"]["reference_data_rows"]),
        "- İçe alınmış projection veri satırı: " + _md(receipt["csv_rows"]["projection_data_rows"]),
        "- Import sırasında kaydedilen canonical CSV durumu: " + _md(receipt["canonical_CSV_reconciliation"]),
        "- Import sırasında kaydedilen dataset/CSV ilişkisi: " + _md(receipt["dataset_CSV_relation"]),
        "- Inbox kapsamı: " + _md(inbox["import_scope"]),
        "- Query kapsamı: " + _md(query["query_scope"]),
        "- Receipt kapsamı: " + _md(receipt["receipt_scope"]), "",
        "DATA hücreleri j: + canonical compact ASCII JSON olarak gerçekten parse edilir; mevcut owning encoder ile hücre ve tam CSV byte eşliği aranır. Prefix kaldırılıp ham değer CSV/formül/shell olarak yürütülmez. Sessiz temizleme, CRLF normalizasyonu, bozuk satır atlama veya kısmi kayıt kabulü yoktur.", "",
        "Receipt'teki matched/equal ifadeleri import sırasında kaydedilen iç ilişkilerdir. Bir saldırgan CSV, dataset ve manifesti birlikte değiştirip yeniden hash'leyebilir; iç hash eşliği özgün kaynağı veya üreticiyi doğrulamaz. Receipt imza, insan yetkisi, ikinci host aktarımı veya güncel dosya kanıtı değildir.", "",
        "## 6. Güven, veri minimizasyonu ve inspector sınırı", "",
        "demo_only=true; " + "; ".join(_md(flag) + "=false" for flag in FALSE_FLAGS) + ".", "",
        "Inbox sınırlamaları: " + _items(inbox["limitations"]),
        "Query sınırlamaları: " + _items(query["limitations"]),
        "Receipt sınırlamaları: " + _items(receipt["limitations"]), "",
        "Yeni inspector yalnız beş yeni açık inbox/query/receipt/summary/manifest dosyasını okur. Kaynak Phase35 CSV'lerini yeniden parse etmez, import davranışını bağımsız yeniden doğrulamaz, kapsül ZIP'i veya guard açmaz. content_consistent yalnız yeni modellerin/ref/count/MD ve gerçek dört payload byte/hash iç tutarlılığıdır.", "",
        "source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false korunur. Producer/source freshness, compiler/module closure, ownership, native, insan/hukukî/müşteri/production/release otoritesi kazanılmaz. Kayıtlı upstream fresh kodları yeni gözlem veya TTL garantisi değildir.", "",
        "Ham kaynak path/root/physical identity, Rust, tam baseline, credential, exception veya içe alınmamış referans/olumlu bloke metadata taşınmaz. Kimlik ve hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir. Yeni araç kapsül olmadan bu beş dosyayı tüketir; korunmuş owner kodu bağımlılığı ikinci offline host kabulüyle karıştırılmaz.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8/BOM; adversarial formula/quoting/header/column/canonical j: ve null-empty-zero-string-boolean senaryoları; duplicate ref/projection, wrong manifest/hash veya değiştirilmiş CSV/dataset; limit/permission/crash/partial write/repeat determinism; gerçek ikinci offline host ve spreadsheet import; Phase31 guard/source freshness, Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Koruma kodu bu kabullerin geçtiğini göstermez. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("inbox_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_inbox_summary",)
