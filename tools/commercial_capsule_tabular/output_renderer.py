"""Pure bounded Markdown view of the closed, selected tabular dataset."""
from __future__ import annotations

import html
import json

from tabular_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_dataset,
)


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_COUNT_LABELS = {
    "requested_reference_count": "İhraç edilen referans",
    "provided_reference_count": "Sınırlı metadata verilen referans",
    "withheld_reference_count": "Mevcut guard nedeniyle metadata verilmeyen referans",
    "unavailable_reference_count": "Mevcut kapsamda metadata bulunmayan referans",
    "projection_count": "İhraç edilen projection ilişkisi",
    "unique_candidate_count": "İhraç edilen benzersiz candidate",
    "unique_file_count": "İhraç edilen benzersiz file",
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


def _closed_text(value: object) -> str:
    return _md(json.dumps(value, ensure_ascii=True, sort_keys=True, separators=(",", ":"), allow_nan=False))


def render_summary(dataset: dict) -> bytes:
    """Render only the validated closed model; no ZIP, source or CSV access."""
    dataset = validate_dataset(dataset)
    scope = dataset["scope"]
    source = dataset["source_capsule"]
    lines = [
        "# Offline capsule tabular disclosure", "", _md(DEMO_LABEL), "",
        "Bu özet yalnız doğrulanmış kaynak kapsülden seçilen kapalı tabular dataset'i gösterir. CSV üretmek source freshness, guard doğruluğu, producer veya insan yetkisini yükseltmez. Kaynak dosyalar yeniden gözlenmedi.", "",
        "## 1. Açık scope ve kaynak kapsül kimliği", "",
        "- Dataset sözleşmesi: " + _md(dataset["schema_version"]),
        "- Scope sözleşmesi: " + _md(scope["schema_version"]),
        "- Mode: " + _md(scope["mode"]),
        "- Kaynak kapsüldeki demo kimliği: " + _md(source["capsule_reference"]),
        "- Kaynak ZIP byte: " + _md(source["bytes"]),
        "- Kaynak ZIP SHA256: " + _md(source["sha256"]),
        "- Scope'un kaynak SHA256 beklentisi: " + _md(scope["source_capsule_sha256"]), "",
        "Yalnız açıkça seçilen referanslar:", "",
    ]
    lines.extend("- " + _md(ref) for ref in scope["export_reference_ids"])
    lines.extend([
        "", "Kaynak ZIP kimliği yalnız byte bağıdır; imza, producer attestation veya güncel filesystem kanıtı değildir. Scope yeni candidate, observation, override, dosya yolu veya kullanıcı/kurum yetkisi taşımaz.", "",
        "| Sayım | Adet |", "| --- | ---: |",
    ])
    for key, label in _COUNT_LABELS.items():
        lines.append(_row((label, _md(dataset["counts"][key]))))
    lines.extend([
        "", "Referans satırı ile projection satırı ayrı paydalardır. CSV header'ları veri satırı sayısına dahil değildir. Bir referans kaydının bulunması olumlu candidate/file metadata açıklama yetkisi değildir. Aynı file farklı ilişkilerde görünürse unique file sayımı ayrı hesaplanır.", "",
        "## 2. Reference register — her seçilmiş referans için bir kayıt", "",
        "| Reference | Korunan disclosure durumu | Projection sayısı | Yorumlama sınırlamaları |",
        "| --- | --- | ---: | --- |",
    ])
    for record in dataset["reference_records"]:
        lines.append(_row((
            _md(record["reference_id"]), _md(record["disclosure_status"]),
            _md(record["projection_count"]), _items(record["interpretation_limitations"]),
        )))
    lines.extend([
        "", "Bloke veya kapsam dışı referans projection sayısı sıfırdır. Olumlu alt metadata reference tablosuna, projection tablosuna veya audit bahanesiyle başka alana kopyalanmaz. Mevcut status yeniden değerlendirilmez.", "",
        "## 3. Projection register — yalnız izinli mevcut metadata", "",
        "| Reference | Candidate | File kimliği | Kayıtlı presence | Kayıtlı byte | Kayıtlı SHA256 | Upstream projection kodu |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ])
    for record in dataset["projection_records"]:
        lines.append(_row((
            _md(record["reference_id"]), _md(record["candidate_id"]), _md(record["file_id"]),
            _md(record["source_file_presence"]), _value(record["observed_byte_size"]),
            _value(record["observed_sha256"]), _md(record["upstream_projection_kind"]),
        )))
    lines.extend([
        "", "| Reference | Candidate | Phase31 current observation kimliği | Phase31 comparison kimliği | Kayıtlı comparison durumu | Yorumlama sınırlamaları |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for record in dataset["projection_records"]:
        lines.append(_row((
            _md(record["reference_id"]), _md(record["candidate_id"]),
            _md(record["phase31_current_observation_id"]), _md(record["phase31_comparison_id"]),
            _md(record["upstream_comparison_status"]), _items(record["interpretation_limitations"]),
        )))
    lines.extend([
        "", "Projection alanları kaynak kapsüldeki değerlerdir; yeni hash, byte veya observation üretilmez. Kayıtlı absence byte/hash null kalır; null bilinen sıfır-byte dosya veya boş string değildir. Upstream fresh kodları eski kayıt kodlarıdır; bu export yeni source observation veya TTL garantisi değildir.", "",
        "## 4. CSV encoding ve veri sınırı", "",
        "Dataset JSON kaynak değerleri taşır; CSV bu değerlerin tanımlı, tersine yorumlanabilir görünümüdür. Tüm DATA hücreleri j: öneki ve compact ASCII JSON ile kodlanır. Mantıksal hücre metinleri j:null, j:\"\", j:0 ve j:[\"a\"] farklıdır. Kaynak string j:null, j:\"j:null\" olur. CSV quoting'i bu hücre encoding'inden ayrı katmandır.", "",
        "Sabit header'lar normal sütun adlarıdır. Comma delimiter, QUOTE_ALL, LF ve UTF-8/no-BOM kullanılır. JSON encoding newline/tab/control karakterlerini kaçış dizilerine çevirir; hücre gerçek multiline/formula-leading payload olarak yazılmaz. Decoding tipli metadata'yı geri verir; formül değerlendirme veya yetkilendirme izni vermez.", "",
        "| Sabit encoding alanı | Kayıtlı politika |", "| --- | --- |",
    ])
    for key in sorted(dataset["csv_encoding"]):
        lines.append(_row((_md(key), _closed_text(dataset["csv_encoding"][key]))))
    lines.extend([
        "", "CSV güvenlik tasarımı gerçek spreadsheet import veya adversarial formula/control/null/empty/zero kabulünün yapıldığı anlamına gelmez. Demo yalnız gerçekten içerdiği değerleri gözlemleyebilir; tanımlı encoding örnekleri çalıştırılmış negatif fixture değildir.", "",
        "## 5. Sabit export sınırları", "",
        "| Sınır | Değer |", "| --- | --- |",
    ])
    for key in sorted(scope["export_constraints"]):
        lines.append(_row((_md(key), _closed_text(scope["export_constraints"][key]))))
    lines.extend([
        "", "Kaynak Phase33/34'ün mevcut ZIP/parser limitleri gevşetilmez; ikinci ZIP güvenlik reader'ı yazılmaz. Hücre/satır/model/dosya sınırı aşılırsa keserek başarı üretilmez. Output yeni/boş dizindir; overwrite, keyfî URL/path takip etme veya kaynak kapsülü değiştirme yoktur.", "",
        "## 6. Güven, mahremiyet ve inceleme sınırı", "",
        "demo_only=true; " + "; ".join(_md(flag) + "=false" for flag in FALSE_FLAGS) + ".", "",
        "Dataset sınırlamaları: " + _items(dataset["limitations"]), "",
        "source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false korunur. Producer/signature, native/compiler/module closure, ownership, insan/hukukî/müşteri/production/release otoritesi kazanılmaz.", "",
        "İçerik inspector'ı yalnız kaynak kapsül ile dataset/iki CSV/summary/manifest ilişkisini inceler. content_consistent gerçek Phase31 guard, producer kimliği, source freshness veya native davranışın bağımsız doğruluğu değildir. İmza, risk skoru veya otomatik müşteri teslimi yoktur.", "",
        "Tam baseline, kaynak path/root/physical identity, Rust, credential, raw exception, gerçek kullanıcı kimliği, bloke olumlu hash/byte veya kapsülde bulunmayan metadata taşınmaz. Kimlik ve hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.", "",
        "NOT_RUN: hostile/duplicate JSON/UTF-8, yanlış digest/ID, bloke projection enjeksiyonu, adversarial CSV formula/control/multiline/null-empty-zero, değiştirilmiş kapsül, ZIP bomb/traversal/symlink/limit, permission/crash/partial write/repeat determinism; gerçek ikinci offline host ve spreadsheet import; Phase31 guard/source freshness, compiler/module closure, ownership/native/human/legal/customer/release. Koruma kodu bu kabullerin geçtiğini göstermez. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("tabular_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_summary",)
