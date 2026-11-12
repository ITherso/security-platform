"""Pure minimized Markdown; never load a snapshot, guard or source file."""
from __future__ import annotations

import html

from .consumer_contracts import FALSE_FLAGS, MAX_SUMMARY_BYTES, InputError, validate_documents


_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_RESULT_LABELS = {
    "provided_limited_metadata": "Sınırlı metadata sağlandı",
    "withheld_by_existing_guard": "Mevcut referans engeli nedeniyle yayımlanmadı",
    "unavailable_in_existing_scope": "Mevcut kapsamda sunulabilir metadata yok",
}
_COUNT_LABELS = {
    "requested_reference_count": "İstenen referans",
    "provided_reference_count": "Sınırlı metadata verilen referans",
    "withheld_reference_count": "Mevcut guard nedeniyle metadata verilmeyen referans",
    "unavailable_reference_count": "Mevcut kapsamda metadata bulunmayan referans",
    "projection_count": "Sunulan projection ilişkisi",
    "unique_candidate_count": "Sunulan benzersiz candidate",
    "unique_file_count": "Sunulan benzersiz file",
    "present_projection_count": "Kayıtlı present projection ilişkisi",
    "absence_projection_count": "Kayıtlı absence projection ilişkisi",
}


def _md(value: object) -> str:
    return "".join(" " if char in "\r\n\t" else "&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _value(value: object) -> str:
    if value is None:
        return "null — raporlanmış byte/hash yok"
    return _md(value)


def _items(values: list) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def render_summary(response: dict, selection: dict) -> bytes:
    """Render only the two new allowlisted models after full correspondence QA."""
    validate_documents(response, selection)
    lines = [
        "# İstenen referanslar için sınırlı metadata", "", _md(response["demo_label"]), "",
        "Bu çağrıda kaynak dosyalar yeniden gözlenmedi. Sonuçlar Phase31'in kayıtlı guard kararından tüketilmiştir. Metadata sağlanması bugünkü dosya durumu, kullanıcı yetkisi, compiler/module resolution veya çalışma izni değildir.", "",
        "## 1. Açık istek ve veri sınırı", "",
        "- Yerel request kimliği: " + _md(response["request_id"]),
        "- Dört upstream artefact byte kimliğine bağlı metadata snapshot kimliği: "
        + _md(response["source_reference"]["snapshot_id"]),
        "- Yalnız açıkça istenen referansların minimize sonuçları gösterilir. Diğer bağlam referansları için inceleme veya güncel durum iddiası yoktur.",
        "- Snapshot kimliği içerik bağıdır; producer imzası, yetki veya yeni source gözlemi değildir.", "",
        "| Sayım | Adet |", "| --- | ---: |",
    ]
    for key, label in _COUNT_LABELS.items():
        lines.append(_row((label, _md(response["counts"][key]))))
    lines.extend([
        "", "Referans, candidate, projection ilişkisi ve benzersiz file paydaları ayrıdır. Aynı file farklı ilişkilerde görünürse tekil file sayımı bir kez yapılır. Bu sayımlar yalnız sunulan metadata kapsamını anlatır; kaynak dosya taraması değildir.", "",
        "## 2. Referans düzeyindeki sonuçlar", "",
        "| İstenen reference | Kayıtlı upstream reference kararı | Tüketici sonucu | Sunulan projection |",
        "| --- | --- | --- | ---: |",
    ])
    for result in response["results"]:
        lines.append(_row((_md(result["reference_id"]), _md(result["upstream_reference_decision"]),
                           _RESULT_LABELS[result["status"]] + " / " + _md(result["status"]),
                           str(len(result["projections"])))))
    lines.extend([
        "", "Mevcut referans engeli varsa olumlu alt dosya projection'ı da yayımlanmaz. Bloke veya kapsam dışı sonuçta projection listesi boştur; olumlu byte/hash başka alana kopyalanmaz. Tek referansta kısmi başarı yoktur. Bunlar mevcut guard'ın tüketici sonuçlarıdır; yeni güvenlik veya freshness kararı değildir.", "",
        "## 3. Yalnız sunulmasına izin verilen dar metadata", "",
        "Upstream fresh_candidate_byte_metadata_only ve fresh_absence_metadata_only yalnız kayıtlı Phase31 projection kodlarıdır. Bu çağrıda yeniden okuma yapıldığını veya dosyanın şimdi değişmemiş olduğunu söylemez. Absence byte/hash null kalır; bilinen sıfır byte ile aynı değildir.", "",
    ])
    for result in response["results"]:
        lines.extend(["### " + _md(result["reference_id"]), ""])
        if not result["projections"]:
            lines.extend([_RESULT_LABELS[result["status"]] + "; projection yayımlanmadı.", ""])
        else:
            lines.extend([
                "| Candidate | File kimliği | Kayıtlı presence | Kayıtlı byte | Kayıtlı SHA256 | Upstream projection kodu |",
                "| --- | --- | --- | ---: | --- | --- |",
            ])
            for projection in result["projections"]:
                lines.append(_row((_md(projection["candidate_id"]), _md(projection["file_id"]),
                                   _md(projection["source_file_presence"]), _value(projection["observed_byte_size"]),
                                   _value(projection["observed_sha256"]), _md(projection["upstream_projection_kind"]))))
            lines.extend([
                "", "| Candidate | Phase31 current observation kimliği | Phase31 comparison kimliği | Kayıtlı comparison durumu | Yorumlama sınırları |",
                "| --- | --- | --- | --- | --- |",
            ])
            for projection in result["projections"]:
                lines.append(_row((_md(projection["candidate_id"]), _md(projection["phase31_current_observation_id"]),
                                   _md(projection["phase31_comparison_id"]), _md(projection["upstream_comparison_status"]),
                                   _items(projection["interpretation_limitations"]))))
            lines.append("")
        lines.extend(["Referans sınırlama kodları: " + _items(result["limitation_codes"]), ""])
    lines.extend([
        "## 4. Seçim kaydı ve sınırlamalar", "",
        "Seçim kaydı yalnız reference kararı, response durumu, sunulan projection sayısı ve sınırlama kodlarını taşır; projection metadata'sını tekrar kopyalamaz.", "",
        "| İstenen reference | Upstream karar | Response durumu | Projection adedi | Sınırlama kodları |",
        "| --- | --- | --- | ---: | --- |",
    ])
    for row in selection["selections"]:
        lines.append(_row((_md(row["reference_id"]), _md(row["upstream_reference_decision"]),
                           _md(row["response_status"]), _md(row["provided_projection_count"]),
                           _items(row["limitation_codes"]))))
    lines.extend([
        "", "Response sınırlamaları: " + _items(response["limitations"]),
        "Seçim sınırlamaları: " + _items(selection["limitations"]), "",
        "## 5. Güven, mahremiyet ve inceleme sınırı", "",
        "demo_only=true; " + "; ".join(_md(flag) + "=false" for flag in FALSE_FLAGS) + ".", "",
        "reference_context_revalidated=false, independent_observation_verified=false ve source_files_reobserved=false kalır. Envanter/delta, component ownership, dependency/module closure, producer/human, build/runtime, hukukî ve release kabulü kazanılmaz. Upstream gözlemden bugüne tazelik, TTL veya canlı durum garantisi yoktur.", "",
        "Tüketiciye relative/absolute kaynak yolu, root/pin, physical identity, tam historical baseline, raw Rust/JSON veya exception metni taşınmaz. Yalnız istenen referans ve yayımlanabilir dar metadata gösterilir. Kimlik/hash hassas olabilir; minimizasyon anonimlik, şifreleme, imza veya attestation değildir.", "",
        "Inspector yalnız dört yeni response/selection/Markdown/manifest dosyasındaki kapalı modelleri, sayımları, türetilen Markdown'ı ve üç payload byte/hash bağını inceler. Phase31 guard'ını, eski baseline'ı veya kaynak dosya gözlemlerini bağımsız yeniden doğrulamaz. content_consistent yalnız yeni artefact iç tutarlılığıdır.", "",
        "NOT_RUN: hostile JSON/UTF-8, duplicate/bilinmeyen reference ID, digest uyuşmazlığı, bozuk upstream/guard/projection, limit/path/link/race/crash, shared-file/determinism ve gerçek source değişimi; native/compiler/Rust resolution, ownership, producer, uzman/hukukî/release kabulü. Kaynak incelemesi bu dalların çalıştırıldığı anlamına gelmez. Test/runner/coverage/typecheck/build veya tarayıcı çalışması yapılmaz.", "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("reference_metadata_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_summary",)
