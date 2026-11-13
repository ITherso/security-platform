"""Pure inert text renderers for the closed portable capsule model."""
from __future__ import annotations

import html

from capsule_contracts import (
    DEMO_LABEL,
    FALSE_FLAGS,
    MAX_MEMBER_BYTES,
    InputError,
    validate_capsule,
)


README_BYTES = (
    "OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION\n"
    "\n"
    "This portable ZIP contains exactly reference-capsule.json, reference-summary.md, "
    "bundle-manifest.json and README.txt. Inspect it in memory; do not extract members.\n"
    "The independent offline inspector needs only its four new local Python modules "
    "and the Python standard library. Phase31/32 tools and original source files "
    "are not required for internal capsule inspection or explicit reference lookup.\n"
    "Only the closed, minimized capsule model is available. A withheld reference "
    "has no projections, including positive metadata from any of its subfiles.\n"
    "Byte/hash and model correspondence establish internal content integrity only. "
    "They do not establish a digital signature, producer identity, user authority, "
    "current filesystem state, source freshness, upstream guard truth, compiler or "
    "ownership verification, legal acceptance, production readiness or release approval.\n"
    "Source files were not reobserved. Recorded upstream fresh codes describe "
    "earlier metadata only. All verification and authorization flags remain false.\n"
    "Identifiers and hashes can be sensitive. Minimization is not encryption or "
    "anonymization. No source path, credential, raw source or historical baseline "
    "is included. No network, sender, scanner or source lookup is provided.\n"
).encode("utf-8")

_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_RESULT_LABELS = {
    "provided_limited_metadata": "Sınırlı metadata taşındı",
    "withheld_by_existing_guard": "Mevcut referans engeli nedeniyle metadata taşınmadı",
    "unavailable_in_existing_scope": "Mevcut kapsamda sunulabilir metadata yok",
}
_COUNT_LABELS = {
    "requested_reference_count": "İstenen referans",
    "provided_reference_count": "Sınırlı metadata verilen referans",
    "withheld_reference_count": "Mevcut guard nedeniyle metadata verilmeyen referans",
    "unavailable_reference_count": "Mevcut kapsamda metadata bulunmayan referans",
    "projection_count": "Taşınan projection ilişkisi",
    "unique_candidate_count": "Taşınan benzersiz candidate",
    "unique_file_count": "Taşınan benzersiz file",
    "present_projection_count": "Kayıtlı present projection ilişkisi",
    "absence_projection_count": "Kayıtlı absence projection ilişkisi",
}
_SOURCE_ROLES = ("response", "selection", "summary", "manifest")


def _md(value: object) -> str:
    return "".join(
        " " if char in "\r\n\t"
        else "&#" + str(ord(char)) + ";" if char in _PUNCTUATION
        else html.escape(char, quote=True)
        for char in str(value)
    )


def _value(value: object) -> str:
    return "null — kayıtlı değer yok" if value is None else _md(value)


def _items(values: list) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def _bounded(lines: list[str]) -> bytes:
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_MEMBER_BYTES:
        raise InputError("capsule_summary_member_byte_limit_exceeded")
    return raw


def render_capsule_summary(capsule: dict) -> bytes:
    """Render only the validated closed capsule; perform no file or guard access."""
    capsule = validate_capsule(capsule)
    lines = [
        "# Offline guarded reference capsule", "", _md(DEMO_LABEL), "",
        "Bu kapsül eski Phase32 metadata'sının küçültülmüş, taşınabilir bir kopyasıdır. Kaynak dosyalar bu çağrıda yeniden gözlenmedi. İç byte/model eşliği güncel kaynak, üretici kimliği, kullanıcı yetkisi veya güvenlik kabulü değildir.", "",
        "## 1. Kapsül kimliği ve kapsamı", "",
        "- Yerel demo kapsül kimliği: " + _md(capsule["capsule_reference"]),
        "- Kapsül sözleşmesi: " + _md(capsule["schema_version"]),
        "- Dört Phase32 artefact kimliğine bağlı snapshot: "
        + _md(capsule["source_bindings"]["snapshot_id"]),
        "- Yalnız açıkça istenen ve kapsülde yer alan referanslar gösterilir. Başka referans veya kaynak dosyası sorgulanmaz.",
        "- Snapshot ve SHA256 içerik bağıdır; dijital imza, producer attestation veya yeni source observation değildir.", "",
        "| Sayım | Adet |", "| --- | ---: |",
    ]
    for key, label in _COUNT_LABELS.items():
        lines.append(_row((label, _md(capsule["counts"][key]))))
    lines.extend([
        "", "Referans, projection ilişkisi, benzersiz candidate ve benzersiz file sayımları ayrı paydalardır. Aynı file birden fazla ilişkide görünürse tekil file sayımı bir kez yapılır. Sayımlar yeni kaynak taraması değildir.", "",
        "## 2. Referans düzeyindeki disclosure sonuçları", "",
        "| İstenen reference | Kayıtlı upstream karar | Kapsüldeki durum | Projection |",
        "| --- | --- | --- | ---: |",
    ])
    for result in capsule["results"]:
        lines.append(_row((
            _md(result["reference_id"]),
            _md(result["upstream_reference_decision"]),
            _RESULT_LABELS[result["status"]] + " / " + _md(result["status"]),
            str(len(result["projections"])),
        )))
    lines.extend([
        "", "Mevcut referans engeli bütün alt projection'ları kapatır. Olumlu bir alt dosya kaydı bu engeli aşmaz; bloke veya kapsam dışı referansta projection listesi boştur. Bloke dosyanın olumlu hash/byte bilgisi başka bir metadata bölümüne taşınmaz. Bu durumlar yeni kullanıcı yetkisi veya risk kararı değildir.", "",
        "## 3. Yalnız taşınmasına izin verilen metadata", "",
        "Upstream fresh_candidate_byte_metadata_only ve fresh_absence_metadata_only yalnız kayıtlı Phase31 projection kodlarıdır. Kapsül açılışı veya lookup yeni gözlem yapmaz. Absence byte/hash alanları null kalır; null bilinen sıfır byte ile aynı değildir.", "",
    ])
    for result in capsule["results"]:
        lines.extend(["### " + _md(result["reference_id"]), ""])
        if not result["projections"]:
            lines.extend([_RESULT_LABELS[result["status"]] + "; projection taşınmadı.", ""])
        else:
            lines.extend([
                "| Candidate | File kimliği | Kayıtlı presence | Kayıtlı byte | Kayıtlı SHA256 | Upstream projection kodu |",
                "| --- | --- | --- | ---: | --- | --- |",
            ])
            for projection in result["projections"]:
                lines.append(_row((
                    _md(projection["candidate_id"]), _md(projection["file_id"]),
                    _md(projection["source_file_presence"]), _value(projection["observed_byte_size"]),
                    _value(projection["observed_sha256"]), _md(projection["upstream_projection_kind"]),
                )))
            lines.extend([
                "", "| Reference | Phase31 current observation kimliği | Phase31 comparison kimliği | Kayıtlı comparison durumu | Yorumlama sınırları |",
                "| --- | --- | --- | --- | --- |",
            ])
            for projection in result["projections"]:
                lines.append(_row((
                    _md(projection["reference_id"]), _md(projection["phase31_current_observation_id"]),
                    _md(projection["phase31_comparison_id"]), _md(projection["upstream_comparison_status"]),
                    _items(projection["interpretation_limitations"]),
                )))
            lines.append("")
        lines.extend(["Referans sınırlama kodları: " + _items(result["limitation_codes"]), ""])
    lines.extend([
        "## 4. Kayıtlı Phase32 artefact bağları", "",
        "Bu tabloda dosya yolu veya ham Phase32 içeriği yoktur. Sözleşme kimliği, byte sayısı ve SHA256 yalnız kapsülün dayandığı eski artefact kimlikleridir. Portatif inspector bu eski dosyaları açmaz veya özgünlüklerini bağımsız doğrulamaz.", "",
        "| Kaynak rolü | Kayıtlı sözleşme | Kayıtlı byte | Kayıtlı SHA256 |",
        "| --- | --- | ---: | --- |",
    ])
    for role in _SOURCE_ROLES:
        source = capsule["source_bindings"]["sources"][role]
        lines.append(_row((_md(role), _value(source["schema_version"]),
                           _md(source["bytes"]), _md(source["sha256"]))))
    lines.extend([
        "", "## 5. Sabit iç inceleme sınırları", "",
        "| Sınır | Değer |", "| --- | ---: |",
    ])
    for key in sorted(capsule["inspection_constraints"]):
        lines.append(_row((_md(key), _md(capsule["inspection_constraints"][key]))))
    lines.extend([
        "", "Kapsül ZIP'i tam dört sabit üye taşır: reference-capsule.json, reference-summary.md, bundle-manifest.json ve README.txt. Inspector ZIP'i diske çıkarmaz. İç manifest kendi hash'ini içermez; diğer üç üyenin gerçek byte/hash bağını taşır. Sınır aşımında truncation yapılmaz.", "",
        "## 6. Güven ve mahremiyet sınırı", "",
        "demo_only=true; " + "; ".join(_md(flag) + "=false" for flag in FALSE_FLAGS) + ".", "",
        "Kapsül sınırlamaları: " + _items(capsule["limitations"]), "",
        "source_files_reobserved=false, reference_context_revalidated=false, independent_observation_verified=false ve upstream_guard_independently_verified=false kalır. İç kapsül incelemesi özgün kaynak veya Phase31 guard doğrulaması değildir. Compiler/module closure, ownership, producer/human, build/runtime, hukukî, production veya release otoritesi kazanılmaz. Canlı tazelik veya TTL garantisi yoktur.", "",
        "Kapsül/lookup kaynak yolu, root, physical identity, tam baseline, raw Rust/JSON, credential, exception veya review notu taşımaz. Kimlik/hash hassas olabilir; minimizasyon anonimlik veya şifreleme değildir. Kapsül güvenlik sertifikası veya onaylı müşteri teslimi değildir.", "",
        "NOT_RUN: hostile/duplicate JSON ve geçersiz UTF-8; değiştirilmiş kaynak/sahte guard/unknown status/enjekte projection/yanlış ID; duplicate ZIP, ZIP bomb/ratio, symlink/path traversal, bozuk manifest veya limit aşımı; crash/partial write/power loss/repeat determinism; gerçek source freshness, upstream guard doğruluğu, compiler/module closure, ownership/producer attestation/native/human/legal/customer/release kabulü. Kodda koruma bulunması bu dalların kabul edildiğini göstermez. Test/runner/coverage/typecheck/build ve Phase19 UI kabulü beklemededir.", "",
    ])
    return _bounded(lines)


def render_assembly_summary(capsule: dict) -> bytes:
    """Add a fixed assembly boundary to the same closed-model summary."""
    summary = render_capsule_summary(capsule)
    suffix = (
        "\n## Assembly kaydının sınırı\n\n"
        "Bu belge yalnız kapsüldeki dar modelden türetilir; ham Phase32 response/selection/summary/manifest içeriğini tekrarlamaz. Kapsülün iç ZIP manifesti ile dış assembly manifesti ayrı byte bağlarıdır. Kapsül ZIP'i ve kaynak teslim ZIP'i farklı artefact'lardır; biri diğerinin kimliği yerine gösterilemez.\n"
    ).encode("utf-8")
    result = summary + suffix
    if len(result) > MAX_MEMBER_BYTES:
        raise InputError("capsule_assembly_summary_byte_limit_exceeded")
    return result


__all__ = ("README_BYTES", "render_capsule_summary", "render_assembly_summary")
