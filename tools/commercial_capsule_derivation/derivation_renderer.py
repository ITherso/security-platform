"""Pure minimized ledger summary; never inspect a capsule or source file."""
from __future__ import annotations

import html

from derivation_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_SUMMARY_BYTES,
    InputError,
    validate_ledger,
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


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def render_summary(ledger: dict) -> bytes:
    """Render only the validated closed ledger; no projection or omitted data."""
    ledger = validate_ledger(ledger)
    request = ledger["request"]
    lines = [
        "# Offline capsule derivation — sınırlı ilişki kaydı", "", _md(DEMO_LABEL), "",
        "Bu özet yalnız dış derivation ledger'ın kapalı kimlik, istek ve toplam sayım alanlarından türetilir. Projection içeriği, seçilmeyen referans kimlikleri veya olumlu alt dosya metadata'sı burada bulunmaz. Kaynak dosyalar yeniden gözlenmedi.", "",
        "## 1. Türetme isteği ve seçilen kapsam", "",
        "- Yerel derivation kimliği: " + _md(ledger["derivation_reference"]),
        "- Ledger sözleşmesi: " + _md(ledger["schema_version"]),
        "- Request sözleşmesi: " + _md(request["schema_version"]),
        "- Request mode: " + _md(request["mode"]),
        "- Request'in kaynak kapsül SHA256 beklentisi: " + _md(request["source_capsule_sha256"]),
        "- Kayıtlı ilişki: " + _md(ledger["subset_relation"]), "",
        "Yalnız açıkça seçilen reference ID'leri:", "",
    ]
    lines.extend("- " + _md(ref) for ref in request["selected_reference_ids"])
    lines.extend([
        "", "Seçilmemiş referansların kimlikleri veya projection'ları bu kayıt üzerinden açıklanmaz. Request yeni candidate, projection, override veya dosya/ZIP üyesi seçimi taşımaz. Daha küçük kapsam, daha yüksek güven veya insan yetkisi değildir.", "",
        "## 2. Kaynak ve türetilmiş ZIP byte kimlikleri", "",
        "| Rol | Kapsüldeki demo kimliği | Gerçek ZIP byte | Gerçek ZIP SHA256 |",
        "| --- | --- | ---: | --- |",
    ])
    for role, key in (("Kaynak kapsül", "source_capsule"), ("Türetilmiş kapsül", "derived_capsule")):
        item = ledger[key]
        lines.append(_row((role, _md(item["capsule_reference"]), _md(item["bytes"]), _md(item["sha256"]))))
    lines.extend([
        "", "Bu SHA256 değerleri yalnız iki ZIP'in byte kimlikleridir; imza, producer attestation veya kullanıcı yetkisi değildir. Farklı ZIP hash'leri tek başına subset ilişkisini kanıtlamaz. Türetilmiş kapsül tek başına özgün kapsülden geldiğinin bağımsız köken kanıtı değildir; ilişkiyi incelemek için iki kapsül birlikte gerekir.", "",
        "## 3. Ayrı toplam sayımlar", "",
        "| Sayım | Kaynak kapsül | Türetilmiş kapsül |", "| --- | ---: | ---: |",
    ])
    for key, label in _COUNT_LABELS.items():
        lines.append(_row((label, _md(ledger["source_counts"][key]), _md(ledger["derived_counts"][key]))))
    lines.extend([
        "", "Referans, projection ilişkisi, benzersiz candidate ve benzersiz file paydaları ayrıdır. Toplam sayımlar çıkarılan referansların adlarını, file kimliklerini veya olumlu hash/byte alanlarını açıklamaz. Bu özet referans bazlı projection satırı taşımaz.", "",
        "## 4. Korunan disclosure sınırı", "",
        "Türetme yalnız açık seçimden oluşan strict reference subset oluşturur. Seçilen referansın status, upstream karar, projection listesi ve tüm kapalı alan değerleri kaynak kapsülle birebir korunmalıdır. Bloke referans için projection listesi boş kalır; olumlu alt metadata eklenemez. Seçilmemiş referansın kaydı, adı veya projection bilgisi yeni kapsüle ya da bu ledger'a kopyalanmaz.", "",
        "Türetilmiş ZIP mevcut Phase33 biçimini korur: reference-capsule.json, reference-summary.md, bundle-manifest.json, README.txt. İç JSON, summary ve manifest mevcut Phase33 sahip yardımcılarıyla bağlanır; README'nin mevcut güven açıklaması değiştirilmez. Türetme ilişkisi yalnız dış ledger'dadır; yeni kapsül şemasına köken veya onay alanı eklenmez.", "",
        "Bu özetin kapalı ledger doğrulaması iki kapsülün içeriğini bağımsız açmaz. İlişki inspector'ı kaynak ve derived kapsülü mevcut Phase33 güvenli okuyucusu ile ayrı ayrı inceler; selected sonuç ve projection değerlerini karşılaştırır. content_consistent yalnız iki kapsülün iç bütünlüğü ve subset ilişkisidir; özgün kaynak/guard veya producer doğruluğu değildir.", "",
        "## 5. Sabit türetme sınırları", "",
        "| Sınır | Değer |", "| --- | ---: |",
    ])
    for key in sorted(request["derivation_constraints"]):
        lines.append(_row((_md(key), _md(request["derivation_constraints"][key]))))
    lines.extend([
        "", "Kaynak Phase33'ün daha sıkı ZIP/model sınırları korunur. Sınır aşımında truncation veya unknown/default veriyle tamamlama yoktur. Output yeni/boş dizin olmalı; mevcut kaynak kapsül veya eski artefact üzerine yazılmaz. ZIP extraction, kaynak dosya taraması veya Phase31/32 guard çalışması yapılmaz.", "",
        "## 6. Güven, mahremiyet ve açık kabuller", "",
        "demo_only=true; " + "; ".join(_md(flag) + "=false" for flag in FALSE_FLAGS) + ".", "",
        "Ledger sınırlamaları: " + ", ".join(_md(item) for item in ledger["limitations"]), "",
        "source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false korunur. Native/compiler/module closure, component ownership, producer/human, build/runtime, hukukî/müşteri/production/release otoritesi kazanılmaz. Kayıtlı upstream fresh kodları yeni gözlem veya canlı tazelik/TTL garantisi değildir.", "",
        "Bu özet yalnız kapsül ZIP kimliklerini, seçilen referansları ve toplam sayımları taşır. Kaynak path/root, physical identity, raw Rust/Phase31/32 baseline, credential, exception, insan notu, projection payload'ı veya seçilmeyen referans bilgisi içermez. Kimlik/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.", "",
        "NOT_RUN: hostile/duplicate JSON ve invalid UTF-8; yanlış digest/ID, sahte veya çelişkili kapsül, bloke projection enjeksiyonu ve omitted metadata sızıntısı saldırıları; duplicate ZIP/ZIP bomb/path traversal/symlink/compression/limit; permission/partial write/crash/power loss/repeat determinism; ikinci offline host/source-absence kabulü, producer/signature, Phase31 guard doğruluğu, gerçek source freshness, compiler/module closure, ownership/native/human/legal/customer/release. Koruma kodu bu kabul kapılarının geçtiğini göstermez. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("derivation_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_summary",)
