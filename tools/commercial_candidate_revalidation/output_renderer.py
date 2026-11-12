"""Pure bounded metadata summary; never relabel historical success as current."""
from __future__ import annotations

import html

from .revalidation_contracts import FALSE_FLAGS, InputError, validate_documents


MAX_SUMMARY_BYTES = 256 * 1024
_PUNCTUATION = frozenset("\\`*_{}[]()#+-.!|>~:/@<>\"'=&")
_BASELINE_ROLES = ("evidence", "triage", "coverage", "summary", "manifest")


def _md(value: object) -> str:
    return "".join(" " if char in "\r\n\t" else "&#" + str(ord(char)) + ";" if char in _PUNCTUATION
                   else html.escape(char, quote=True) for char in str(value))


def _value(value: object, absent: str = "Değer kaydedilmedi") -> str:
    if value is None:
        return absent
    if type(value) is bool:
        return "true" if value else "false"
    return _md(value)


def _items(values) -> str:
    return ", ".join(_md(value) for value in values) or "—"


def _row(values) -> str:
    return "| " + " | ".join(values) + " |"


def render_summary(ledger: dict, reuse: dict) -> bytes:
    validate_documents(ledger, reuse)
    counts, reuse_counts = ledger["counts"], reuse["counts"]
    source = ledger["source_reference"]
    lines = [
        "# Candidate gözlemleri ve sınırlı evidence reuse", "", _md(ledger["demo_label"]), "",
        "Historical gözlem değişmeden kalır; current gözlem bu çağrıda ayrı kaydedilir. Guard yalnız bu yeni aracın metadata tüketimine uygulanır. Eski ecosystem tüketicileri değiştirilmedi. Equal bytes, aynı fiziksel dosya, bütün kaynak bağlamının güncelliği veya Rust module resolution değildir.", "",
        "## 1. Kaynak ve okuma kapsamı", "",
        "- Yerel review referansı: " + _md(source["review_reference"]),
        "- Phase30 candidate referansı: " + _md(source["phase30_candidate_reference"]),
        "- Termivar / Phase24 platform pin beyanı: " + _md(source["source_commits"]["termivar"]) + " / " + _md(source["source_commits"]["platform"]),
        "- Tarihsel izinli file / seçilen file: " + str(counts["historical_file_count"]) + " / " + str(counts["selected_file_count"]),
        "- Yeni current observation: " + str(counts["current_observation_count"]),
        "- Current present / güvenli missing file: " + str(counts["current_present_file_count"]) + " / " + str(counts["current_missing_file_count"]),
        "- Current hash okuma baytı: " + str(counts["current_observed_bytes"]),
        "- Yeniden incelenmeyen tarihsel file: " + str(counts["not_revalidated_file_count"]),
        "- Korunan candidate / external reference: " + str(counts["baseline_candidate_count"]) + " / " + str(counts["baseline_external_reference_count"]), "",
        "Scope önceki allowlist'in alt kümesidir; yeni candidate veya yol yetkisi vermez. Seçilen file'ın bütün eski izinli candidate bağları korunur, aynı dosya bir kez okunur. CAND0004 gibi eski not-allowlisted binding, aynı filename veya başka candidate'ın izniyle current erişim kazanmaz. Pin beyanı producer/Git attestation değildir; kaynak platform pin'i frozen runtime pin'inden ayrıdır.", "",
        "## 2. Değişmemiş historical observations", "",
        "| Historical ID | File / candidate bağları | Root-relative path | Eski presence / read | Eski byte | Eski SHA256 | Eski physical identity |",
        "| --- | --- | --- | --- | ---: | --- | --- |",
    ]
    for row in ledger["historical_observations"]:
        old = row["observation"]
        lines.append(_row((_md(row["observation_id"]), _md(row["file_id"]) + " / " + _items(row["candidate_ids"]),
                           _md(old["path"]), _md(old["source_file_presence"]) + " / " + _md(old["read_status"]),
                           _value(old["observed_byte_size"]), _value(old["observed_sha256"]),
                           _md(row["historical_physical_identity"]))))
    lines.extend([
        "", "Historical SHA, baseline artefact digest'i ve file/candidate/reference bağları korunur; yeni hash veya zaman alanıyla yenilenmiş gibi gösterilmez. Eski not-allowlisted candidate için historical file observation uydurulmaz. not_recorded kimlik alanı bugünkü inode/handle ile doldurulmaz.", "",
        "## 3. Yeni current gözlemler ve üç hash rolü", "",
        "| Current ID / file | Baseline SHA256 | Ayrı current expected SHA256 | Yeni observed byte / SHA256 | Presence / read | Read stability | Current physical identity |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in ledger["current_observations"]:
        lines.append(_row((_md(row["observation_id"]) + " / " + _md(row["file_id"]),
                           _value(row["baseline_sha256"]), _value(row["current_expected_sha256"], "Ek current hash beklentisi verilmedi"),
                           _value(row["current_observed_byte_size"]) + " / " + _value(row["current_observed_sha256"]),
                           _md(row["source_file_presence"]) + " / " + _md(row["read_status"]),
                           _md(row["read_stability"]), _md(row["physical_identity"]))))
    if not ledger["current_observations"]:
        lines.append("| — | — | — | — | Current gözlem yok | — | not_exported |")
    lines.extend([
        "", "baseline_sha256 tarihsel değerdir; current_expected_sha256 bu scope'un ayrı beklentisidir; current_observed_sha256 yeni başarılı okumadan gelir. Null expectation eski mandatory-hash reader'ını bypass etmez. Current expectation uyuşmazlığı veya güvenlik/permission/race hatası changed/missing diye yutulmaz; başarılı ledger yayımlanmaz. Güvenli absence gözleminde current byte/hash null kalır.", "",
        "## 4. Baseline–current comparison", "",
        "| Karşılaştırma durumu | File |", "| --- | ---: |",
    ])
    for row in counts["by_comparison_status"]:
        lines.append(_row((_md(row["status"]), str(row["file_count"]))))
    lines.extend([
        "", "| File | Historical ID | Current ID | Comparison | Bytes equal | Identity comparison | Nedenler |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in ledger["comparisons"]:
        lines.append(_row((_md(row["file_id"]), _md(row["historical_observation_id"]),
                           _value(row["current_observation_id"], "Current okuma seçilmedi"), _md(row["comparison_status"]),
                           _value(row["bytes_equal"], "Byte eşliği karşılaştırılmadı"), _md(row["identity_comparison"]),
                           _items(row["reason_codes"]))))
    lines.extend([
        "", "Byte eşitliği yalnız boyut ve SHA256 eşliğidir. Tarihsel fiziksel kimlik not_recorded olduğu için identity_comparison=not_comparable kalır. Absence re-observation byte eşitliği iddiası değildir. İki güvenli gözlem arasındaki fark ile tek read sırasında kimlik değişimi farklıdır; ikincisi güvenlik hatasıdır. not_revalidated ve revalidation_inconclusive normal eski başarı fallback'i değildir.", "",
        "## 5. Yalnız bu tool için current-only reuse guard", "",
        "- Metadata projection izinli / blocked file: " + str(reuse_counts["reusable_file_count"]) + " / " + str(reuse_counts["blocked_file_count"]),
        "- Current byte / current absence projection file: " + str(reuse_counts["fresh_byte_projection_file_count"]) + " / " + str(reuse_counts["fresh_absence_projection_file_count"]),
        "- Reuse izinli / blocked candidate: " + str(reuse_counts["reusable_candidate_count"]) + " / " + str(reuse_counts["blocked_candidate_count"]), "",
        "Guard caller'ın equal etiketine güvenmez; historical/current kapalı metadata'dan yeniden karşılaştırır. Yalnız bytes_reobserved_equal current byte metadata projection'ına, absence_reobserved current absence projection'ına izin verir. Diğer beş durumda projection null/blocked olur; historical başarı döndürülmez. İzin verilen metadata kaynak zinciri veya compiler kanıtı değildir.", "",
        "| File | Comparison | Metadata reuse | Guard durumu | Current projection kind / current ID | Current presence / byte / SHA256 |",
        "| --- | --- | --- | --- | --- | --- |",
    ])
    for row in reuse["files"]:
        projection = row["projection"]
        kind = "Projection yok; historical fallback yok" if projection is None else _md(projection["projection_kind"]) + " / " + _md(projection["current_observation_id"])
        metadata = "—" if projection is None else (_md(projection["source_file_presence"]) + " / " + _value(projection["current_observed_byte_size"]) + " / " + _value(projection["current_observed_sha256"]))
        lines.append(_row((_md(row["file_id"]), _md(row["comparison_status"]), _value(row["reuse_allowed"]),
                           _md(row["reuse_status"]), kind, metadata)))
    lines.extend([
        "", "| Candidate | Eski allowlist / candidate durumu | File | Comparison | Metadata reuse / guard | Current ID | Nedenler |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in reuse["candidates"]:
        lines.append(_row((_md(row["candidate_id"]), _md(row["baseline_allowlist_status"]) + " / " + _md(row["baseline_candidate_status"]),
                           _value(row["file_id"], "Eski file observation yok"), _md(row["comparison_status"]),
                           _value(row["reuse_allowed"]) + " / " + _md(row["reuse_status"]),
                           _value(row["current_observation_id"], "Current gözlem yok"), _items(row["reason_codes"]))))
    lines.extend([
        "", "Reference context yeniden incelenmedi. Eski path-context/condition/Phase24 membership/ownership alanları current candidate hash'inden tazelenmez. Guard anlık gözlemdir; TTL tanımlı değildir, polling/watcher veya gelecekte geçerlilik garantisi yoktur. Önceki ecosystem tüketicilerine genel staleness enforcement uygulanmış sayılmaz.", "",
        "## 6. Eski candidate ve reference etkisi", "",
        "- İzlenen reference: " + str(reuse_counts["reference_count"]),
        "- Candidate değişimi gözlenen reference: " + str(reuse_counts["references_with_change_count"]),
        "- Blocked reuse içeren reference: " + str(reuse_counts["references_with_blocked_reuse_count"]),
        "- Candidate gözlemleri yeniden kaydedilmiş, context doğrulanmamış reference: " + str(reuse_counts["references_reobserved_with_context_unverified_count"]),
        "- Eski candidate kapsamı dışındaki reference: " + str(reuse_counts["outside_scope_reference_count"]), "",
        "Bir changed, blocked veya yeniden incelenmemiş candidate başka eşit candidate tarafından maskelenmez. File, candidate ve reference paydaları ayrıdır; changed ve blocked reference sayaçları örtüşebilir. outside_scope sağlıklı/unchanged/unaffected değildir; bu referanslar hakkında güncel dosya gözlemi yoktur. Eski resolved_file=false korunur; yeni module/ownership edge üretilmez.", "",
        "| Phase29 reference | Eski parent / modül | Impact | Candidate'lar | Reusable / blocked candidate | Changed / unknown candidate | Comparison durumları |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ])
    for row in reuse["reference_impact"]:
        ref = row["reference"]
        lines.append(_row((_md(ref["reference_id"]), _md(ref["source_file_reference"]) + " / " + _value(ref["declared_module_name"]),
                           _md(row["impact_status"]), _items(row["candidate_ids"]),
                           _items(row["reusable_candidate_ids"]) + " / " + _items(row["blocked_candidate_ids"]),
                           _items(row["changed_candidate_ids"]) + " / " + _items(row["unknown_candidate_ids"]),
                           _items(row["comparison_statuses"]))))
    lines.extend([
        "", "## 7. Byte kimliği, mahremiyet ve açık kabul kapıları", "",
        "| Baseline rol | Sözleşme | Byte | SHA256 |", "| --- | --- | ---: | --- |",
    ])
    for role in _BASELINE_ROLES:
        row = source["baseline_sources"][role]
        lines.append(_row((_md(role), _value(row["schema_version"], "Markdown / şema yok"), str(row["bytes"]), _md(row["sha256"]))))
    package = source["source_package"]
    lines.extend([
        "", "- Phase30 kaynak ZIP byte kimliği: " + str(package["bytes"]) + " / " + _md(package["sha256"]),
        "- ZIP binary hash'i archive parsing/extraction veya üye/producer attestation değildir.", "",
        "demo_only=true; " + "; ".join(flag + "=false" for flag in FALSE_FLAGS) + ".", "",
        "Tarihsel metadata ve yeni projection raw Rust/JSON metni, snippet, absolute source root veya dev/inode/handle/time kimliği içermez. Relpath/ID/hash hassas olabilir; metadata allowlist secret detection veya anonimlik garantisi değildir. Body decode/lexer/module discovery yoktur.", "",
        "Inspector yalnız ledger/reuse/Markdown/manifest dört yeni dosyanın model/ref/count ve gerçek byte/hash iç tutarlılığını denetler. Eski artefact/ZIP/candidate/Rust dosyası yeniden açılmaz; lexer çalıştırılmaz. content_consistent bağımsız filesystem observation, devam eden freshness, producer/Git veya compiler/build/release kabulü değildir.", "",
        "Scope 128 KiB; metadata 8 MiB, kaynak ZIP 2 MiB; current dosya 512 KiB / toplam 4 MiB / hash parçası 64 KiB; yeni JSON 2 MiB / Markdown 256 KiB / manifest 128 KiB sınırındadır. Limit aşımı sessiz truncation veya historical fallback üretmez.", "",
        "NOT_RUN: changed/disappeared/appeared; hostile JSON/UTF-8; yanlış candidate/root/digest/current expectation; link/reparse/hardlink; permission/TOCTOU/race; limit/crash/partial write/power-loss; determinism; çoklu reference shared-file; Rust AST/module resolution/closure; build/runtime; producer/Git/ownership ve insan/uzman/hukukî/release kabulü. Koruma veya saf geçiş kodu bu dalların çalıştırıldığı anlamına gelmez. Önceki açık kapılar korunur.", "",
        "Ledger sınırlamaları: " + _items(ledger["limitations"]),
        "Reuse sınırlamaları: " + _items(reuse["limitations"]), "",
    ])
    raw = ("\n".join(lines) + "\n").encode("utf-8", errors="strict")
    if len(raw) > MAX_SUMMARY_BYTES:
        raise InputError("candidate_revalidation_summary_byte_limit_exceeded")
    return raw


__all__ = ("render_summary",)
