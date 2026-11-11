"""Pure metadata-only portfolio views, with no scripts or source file access."""
from __future__ import annotations

import base64
import hashlib
from html import escape

from .portfolio_contracts import (
    DEMO_LABEL, InputError, PortfolioIndex, portfolio_to_dict, validate_portfolio,
)


MAX_MARKDOWN_BYTES = 128 * 1024
MAX_HTML_BYTES = 512 * 1024
MAX_RENDERED_CASES = 25

_STAGES = {
    "scope_planning": "Kapsam planlama",
    "assessment_reported": "Assessment beyanı",
    "observation_intake": "Observation intake",
    "analyst_review": "Uzman inceleme hazırlığı",
    "client_handoff": "Müşteri teslim taslağı",
    "traceability": "Yürütme bağı",
}
_STATUSES = {
    "artifact_present": "Artefact mevcut",
    "artifact_missing": "Artefact eksik",
    "content_consistent": "İçerik ilişkisi tutarlı",
    "content_inconsistent": "İçerik ilişkisi tutarsız",
    "relationship_not_established": "İlişki kurulmamış",
    "human_review_pending": "Uzman incelemesi bekliyor",
    "delivery_not_authorized": "Teslim yetkisi yok",
}
_BLOCKERS = {
    "authorization_missing": "Çalışma yetkisi eksik",
    "execution_binding_missing": "Plan–assessment yürütme bağı yok",
    "producer_not_verified": "Üretici doğrulanmamış",
    "human_review_pending": "Uzman incelemesi bekliyor",
    "data_handling_pending": "Veri işleme kararı bekliyor",
    "delivery_not_authorized": "Müşteri teslimi yetkilendirilmemiş",
    "runtime_acceptance_not_performed": "Çalışma zamanı kabulü yapılmamış",
}
_FLAG_STATEMENT = (
    "demo_only=true; execution_binding=not_established; "
    "plan_execution_verified=false; scope_fulfillment_verified=false; "
    "authorization_verified=false; human_review_verified=false; "
    "producer_verified=false; release_authorized=false; "
    "execution_authorized=false; production_ready=false."
)


def _checked(index: PortfolioIndex) -> PortfolioIndex:
    if type(index) is not PortfolioIndex:
        raise InputError("portfolio_renderer_invalid_model")
    closed = validate_portfolio(portfolio_to_dict(index))
    if not 1 <= len(closed.cases) <= MAX_RENDERED_CASES:
        raise InputError("portfolio_renderer_record_limit")
    return closed


def _label(labels: dict[str, str], value: str) -> str:
    if value not in labels:
        raise InputError("portfolio_renderer_unknown_metadata_code")
    return labels[value]


def _m(value: object) -> str:
    """Render body text without raw HTML, Markdown links or auto-URL syntax."""
    return "".join(
        "&#" + str(ord(char)) + ";"
        if char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" else char
        for char in str(value)
    )


def _h(value: object) -> str:
    return escape(str(value), quote=True)


def _single_example_note(case_count: int) -> str:
    if case_count == 1:
        return (
            "Bu portföy yalnız bir mevcut sentetik vaka paketi içerir. "
            "Çoklu-vaka çalışma zamanı kabulü bu tek örnekle doğrulanmış sayılmaz."
        )
    return (
        "Bu portföy yalnız açıkça seçilmiş sentetik paketleri kapsar. "
        "Paket sayısı, farklı müşteri veya bağımsız gerçek değerlendirme sayısı değildir."
    )


def render_markdown(index: PortfolioIndex) -> bytes:
    index = _checked(index)
    lines = [
        "# Çevrimdışı vaka portföyü", "", DEMO_LABEL, "",
        "- Portföy organizasyon referansı: " + _m(index.portfolio_reference),
        "- Seçili vaka paketi sayısı: " + str(len(index.cases)),
        "- Seçili kaynak ZIP toplamı: " + str(sum(case.bundle_byte_length for case in index.cases)) + " bayt",
        "", _single_example_note(len(index.cases)), "",
        "Bu sayılar yalnız seçili paketleri kapsar; müşteri, gerçek değerlendirme, zafiyet "
        "veya doğrulanmış güvenlik durumu sayısı değildir. Paket başına birden fazla blocker "
        "bulunabilir; blocker grup toplamları paket sayısını aşabilir.", "",
        "## Açık blocker grupları", "",
    ]
    for row in index.blocker_summary:
        lines.append("- " + _label(_BLOCKERS, row.code) + ": " + str(row.case_bundle_count) +
                     " paket — " + _m(row.code))
    lines.extend(["", "## Aşama durumlarının paket sayıları", ""])
    for row in index.stage_summary:
        lines.append("- " + _label(_STAGES, row.stage) + " / " + _label(_STATUSES, row.status) +
                     ": " + str(row.case_bundle_count) + " paket")
    lines.extend(["", "## Seçili vaka paketleri", ""])
    for case in index.cases:
        lines.extend([
            "### " + _m(case.case_reference), "",
            "Vaka referansı kaynağın organizasyon etiketidir; run veya müşteri kimliği değildir.", "",
        ])
        if case.display_label is not None:
            lines.append("- Sentetik görüntüleme etiketi: " + _m(case.display_label))
        lines.extend([
            "- Vaka sözleşmesi: " + _m(case.case_contract),
            "- Kaynak ZIP boyutu: " + str(case.bundle_byte_length) + " bayt",
            "- Paket içi tutarlılık sonucu: " + _m(case.internal_content_status),
        ])
        if index.display_preferences.show_source_hashes:
            lines.append("- Kaynak ZIP SHA256: " + _m(case.bundle_sha256))
        else:
            lines.append("- Tam kaynak SHA256, görüntüleme tercihiyle bu özette gösterilmiyor; JSON indeksinde korunur.")
        lines.extend([
            "- Kaynak indeksi kayıt sayısı: " + str(case.source_index_record_count),
            "- Bildirilen observation sayısı: " + str(case.observation_count),
            "- execution_binding=not_established",
            "- original_sources_read=false; source_relationships_rechecked=false; source_files_embedded=false.",
            "", "Aşamalar:", "",
        ])
        for stage in case.stages:
            lines.append("- " + _label(_STAGES, stage.stage) + ": " + _label(_STATUSES, stage.status) +
                         " — " + _m(stage.status))
        facts = case.workflow_facts
        lines.extend([
            "", "İnceleme hazırlığı metadata'sı:", "",
            "- Plan önkoşulu: " + _m(facts.plan_precondition),
            "- Bağımsız assessment beyanı: " + _m(facts.assessment_status),
            "- Observation / unreviewed / unknown scope / pending inclusion: " + _m(
                " / ".join(str(value) for value in (facts.observation_count, facts.unreviewed_count,
                                                    facts.unknown_scope_count, facts.pending_inclusion_count))),
            "- Overlay karar sayısı: " + str(facts.overlay_decision_count),
            "- Reconciled observation sayısı: " + str(facts.reconciled_observation_count),
            "- Handoff input bağı: " + _m(facts.handoff_input_binding),
            "- Handoff manifest kapsamı: " + _m(facts.handoff_manifest_scope),
            "", "Kaynak blocker'lar:", "",
        ])
        lines.extend("- " + _label(_BLOCKERS, code) + " — " + _m(code) for code in case.blockers)
        lines.extend(["", _FLAG_STATEMENT, ""])
    lines.extend([
        "## Güven ve veri sınırı", "",
        "Paket iç tutarlılığı, üretici veya uzman kimliği doğrulaması değildir. Orijinal kaynak "
        "dosyaları yeniden okunmaz; kaynak ilişkileri yeniden kontrol edilmiş sayılmaz. "
        "Portföye alınmak çalışma yetkisi, planın yürütülmesi veya müşteri teslim onayı vermez.", "",
        "Planlanan limitler tüketim değildir. Assessment complete beyanı planın tamamlandığını "
        "göstermez. Boş overlay uzman incelemesi değildir. Mevcut handoff taslağı gerçek teslim değildir.", "",
        "Ham kaynak JSON, assessment/HTTP/evidence, hedef URL/IP/domain, dosya yolu, credential, "
        "müşteri/kişi kimliği veya serbest uzman notları bu görünümde taşınmaz. Bu veri minimizasyonu "
        "otomatik secret detection, redaksiyon veya anonimlik garantisi değildir.", "",
        _FLAG_STATEMENT, "",
        "## NOT_RUN — açık kabul kapıları", "",
        "İki bağımsız vaka, duplicate/conflict, malformed/hostile JSON/ZIP/manifest, ZIP bomb/path "
        "traversal, sınır aşımı, symlink/reparse/race/permission/crash, tekrarlı determinism, "
        "gerçek müşteri/uzman/üretici/kurum ve bağımsız tarayıcı görsel kabulü bu sentetik özetle "
        "doğrulanmış sayılmaz. Bu çıktı otomatik test veya güvenlik kabulü değildir.", "",
    ])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if len(raw) > MAX_MARKDOWN_BYTES:
        raise InputError("portfolio_markdown_size_limit")
    return raw


_CSS = """\
:root{color-scheme:light;--ink:#1b2b3d;--muted:#556477;--line:#d7e0e9;--paper:#fff;--bg:#eef2f6;--amber:#805315;--amber-bg:#fff5df;--slate:#22364d}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.55 system-ui,-apple-system,BlinkMacSystemFont,'Segoe UI',sans-serif}
main{max-width:1200px;margin:0 auto;padding:36px 24px 52px}h1,h2,h3,p{margin-top:0}h1{font-size:clamp(2rem,4vw,3rem);line-height:1.15;letter-spacing:-.035em;margin-bottom:14px}h2{font-size:1.32rem;letter-spacing:-.015em;margin-bottom:10px}h3{font-size:1.02rem;margin-bottom:9px}
.eyebrow{color:var(--muted);font-weight:700;letter-spacing:.11em;font-size:.75rem;text-transform:uppercase;margin-bottom:12px}.lead{max-width:850px;color:var(--muted);font-size:1.05rem}.reference{font-size:.84rem;color:var(--muted);overflow-wrap:anywhere}
.banner{border:1px solid #e4c687;background:var(--amber-bg);color:#624417;border-radius:12px;padding:15px 18px;margin:24px 0;overflow-wrap:anywhere}.banner strong{display:block;font-size:.78rem;letter-spacing:.035em}.banner p{margin:7px 0 0;font-size:.92rem}
.metrics{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px;margin:0 0 24px}.metric{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:19px 22px}.metric span{display:block;color:var(--muted);font-size:.84rem}.metric strong{display:block;font-size:2.35rem;line-height:1.15;margin:8px 0 3px;font-weight:700}
.section{background:var(--paper);border:1px solid var(--line);border-radius:16px;padding:23px;margin-bottom:22px}.section-note{color:var(--muted);font-size:.9rem;max-width:900px}.table-scroll{overflow-x:auto;border-radius:7px}table{border-collapse:collapse;width:100%;font-size:.9rem}caption{text-align:left;color:var(--muted);font-size:.84rem;margin-bottom:12px}th,td{padding:12px 10px;border-bottom:1px solid var(--line);text-align:left;vertical-align:top}thead th{color:var(--muted);font-weight:650;font-size:.78rem;text-transform:uppercase;letter-spacing:.045em}tbody th{font-weight:600}tbody tr:last-child>*{border-bottom:0}.case-list{min-width:680px}.count{text-align:right;white-space:nowrap;font-variant-numeric:tabular-nums}.code{font-size:.76rem;color:var(--muted);overflow-wrap:anywhere}.pill{display:inline-block;padding:3px 8px;border:1px solid #d4dce6;background:#f4f6f9;border-radius:7px;font-size:.79rem;white-space:normal}.pill-warn{border-color:#e3cca4;background:#fff7e9;color:#73521f}
.two-col{display:grid;grid-template-columns:1fr 1fr;gap:20px}.case-card{border:1px solid var(--line);border-radius:13px;margin-top:16px;background:#fff}.case-card>summary{padding:17px 20px;cursor:pointer;overflow-wrap:anywhere;font-weight:650}.case-card>summary .hint{display:inline-block;color:var(--muted);font-weight:400;font-size:.8rem;margin-left:12px}.case-body{padding:0 20px 22px;border-top:1px solid var(--line)}.case-body>p:first-child{margin-top:18px}.case-body dl{display:grid;grid-template-columns:minmax(150px,1fr) 2fr;gap:8px 16px;font-size:.88rem;margin:16px 0}.case-body dt{color:var(--muted)}.case-body dd{margin:0;overflow-wrap:anywhere}.case-body .stage-table th{width:45%}.tags{display:flex;flex-wrap:wrap;gap:8px;padding:0;list-style:none;margin:12px 0 18px}.tags li{background:var(--amber-bg);border:1px solid #ead6b0;border-radius:8px;color:#73521f;padding:6px 9px;font-size:.8rem}.identity{margin-top:16px;background:#f5f7fa;border-radius:9px;padding:11px 14px}.identity summary{cursor:pointer;font-size:.85rem;font-weight:600}.hash{display:block;margin:10px 0;overflow-wrap:anywhere;font:12px/1.65 ui-monospace,SFMono-Regular,Consolas,monospace}.small{font-size:.82rem;color:var(--muted)}.trust{background:var(--slate);color:#fff}.trust h2{color:#fff}.trust p{color:#dce5f0}.trust .flags{color:#dce5f0;font:11px/1.7 ui-monospace,SFMono-Regular,Consolas,monospace;overflow-wrap:anywhere;margin-bottom:0}.fact-grid{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:8px;margin:16px 0}.fact-grid div{padding:11px;background:#f4f6f9;border:1px solid #e2e7ed;border-radius:8px}.fact-grid strong{display:block;font-size:1.25rem}.fact-grid span{font-size:.74rem;color:var(--muted)}footer{font-size:.8rem;color:var(--muted);padding:0 4px}
summary:focus-visible,.table-scroll:focus-visible{outline:3px solid #a56f22;outline-offset:4px}summary:hover{background:#f6f8fa}details[open]>summary{border-radius:13px 13px 0 0}.identity[open]>summary{border-radius:0}
@media(max-width:760px){main{padding:22px 14px 35px}.section{padding:18px}.metrics{gap:9px}.metric{padding:15px 13px}.metric strong{font-size:1.95rem}.two-col{grid-template-columns:1fr}.case-body{padding:0 15px 18px}.case-card>summary{padding:15px}.fact-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.case-body dl{grid-template-columns:1fr;gap:2px}.case-body dd{margin-bottom:8px}}
@media(max-width:440px){.metrics{grid-template-columns:1fr}.metric{display:grid;grid-template-columns:1fr auto;gap:5px 12px}.metric strong{grid-column:2;grid-row:1/3;margin:0;align-self:center}.metric .small{grid-column:1}.case-card>summary .hint{display:block;margin-left:18px;margin-top:4px}}
"""


def _html_case(case, preferences) -> str:
    facts = case.workflow_facts
    opened = " open" if preferences.expand_case_details else ""
    parts = [
        '<details class="case-card"' + opened + '><summary>' + _h(case.case_reference) +
        '<span class="hint">Sınırlı paket ayrıntısı</span></summary><div class="case-body">',
        '<p class="small">Vaka referansı kaynak organizasyon etiketidir; müşteri veya çalışma kimliği değildir.</p><dl>',
    ]
    if case.display_label is not None:
        parts.append('<dt>Sentetik görüntüleme etiketi</dt><dd>' + _h(case.display_label) + '</dd>')
    parts.extend([
        '<dt>Vaka sözleşmesi</dt><dd><code>' + _h(case.case_contract) + '</code></dd>',
        '<dt>Kaynak ZIP boyutu</dt><dd>' + str(case.bundle_byte_length) + ' bayt</dd>',
        '<dt>Paket içi tutarlılık</dt><dd>İçerik ilişkisi tutarlı <span class="code">' + _h(case.internal_content_status) + '</span></dd>',
        '<dt>Kaynak indeksi kaydı</dt><dd>' + str(case.source_index_record_count) + '</dd>',
        '<dt>Plan–assessment bağı</dt><dd>Kurulmamış <span class="code">not_established</span></dd>',
        '</dl><h3>İş akışı aşamaları</h3><table class="stage-table"><caption>Paketten alınan mevcut durumlar</caption><tbody>',
    ])
    for stage in case.stages:
        parts.append('<tr><th scope="row">' + _h(_label(_STAGES, stage.stage)) + '</th><td>' +
                     _h(_label(_STATUSES, stage.status)) + '<div class="code">' + _h(stage.status) + '</div></td></tr>')
    parts.extend(['</tbody></table><h3>İnceleme hazırlığı metadata’sı</h3><div class="fact-grid">'])
    for name, count in (("Observation", facts.observation_count), ("İncelenmemiş", facts.unreviewed_count),
                        ("Kapsamı bilinmeyen", facts.unknown_scope_count), ("Dahil etme kararı bekleyen", facts.pending_inclusion_count)):
        parts.append('<div><strong>' + str(count) + '</strong><span>' + _h(name) + '</span></div>')
    parts.extend([
        '</div><p class="small">Overlay karar sayısı: ' + str(facts.overlay_decision_count) +
        '. Boş overlay uzman incelemesi değildir. Assessment’ın ' + _h(facts.assessment_status) +
        ' beyanı planın tamamlandığını göstermez.</p>',
        '<h3>Açık karar ve kanıt gereksinimleri</h3><ul class="tags">',
    ])
    parts.extend('<li>' + _h(_label(_BLOCKERS, code)) + '</li>' for code in case.blockers)
    parts.append('</ul><p class="small">Mevcut handoff taslağı müşteriye teslim veya release onayı değildir. '
                 'Orijinal kaynaklar okunmadı; kaynak ilişkileri yeniden kontrol edilmedi.</p>')
    if preferences.show_source_hashes:
        parts.extend([
            '<details class="identity"><summary>Tam kaynak ZIP içerik kimliği</summary><code class="hash">' +
            _h(case.bundle_sha256) + '</code><p class="small">SHA256 seçili paket baytlarını tanımlar. '
            'Üretici kimliği, imza veya değerlendirme yetkisi değildir.</p></details>',
        ])
    else:
        parts.append('<p class="small">Tam SHA256 görünümü kapalı. İçerik kimliği JSON indeksinde korunur.</p>')
    parts.append('</div></details>')
    return "".join(parts)


def render_html(index: PortfolioIndex) -> bytes:
    index = _checked(index)
    css_digest = base64.b64encode(hashlib.sha256(_CSS.encode("utf-8")).digest()).decode("ascii")
    csp = ("default-src 'none'; script-src 'none'; style-src 'sha256-" + css_digest +
           "'; base-uri 'none'; form-action 'none'; object-src 'none'; frame-src 'none'; "
           "connect-src 'none'; img-src 'none'; font-src 'none'")
    stage_count = sum(len(case.stages) for case in index.cases)
    open_categories = sum(row.case_bundle_count > 0 for row in index.blocker_summary)
    parts = [
        '<!doctype html><html lang="tr"><head><meta charset="utf-8">',
        '<meta name="viewport" content="width=device-width, initial-scale=1">',
        '<meta http-equiv="Content-Security-Policy" content="' + _h(csp) + '">',
        '<title>Termivar | Çevrimdışı vaka portföyü</title><style>' + _CSS + '</style></head><body><main>',
        '<header><p class="eyebrow">Termivar · Offline çalışma alanı</p><h1>Vaka portföyü</h1>',
        '<p class="lead">Seçili vaka paketlerinin aşamalarını ve açık karar kapılarını aynı görünümde inceleyin.</p>',
        '<p class="reference">Portföy organizasyon referansı: ' + _h(index.portfolio_reference) + '</p></header>',
        '<aside class="banner" aria-label="Demo ve güven sınırı"><strong>' + _h(DEMO_LABEL) +
        '</strong><p>' + _h(_single_example_note(len(index.cases))) + '</p></aside>',
        '<section class="metrics" aria-label="Seçili paketlerin özeti">',
        '<div class="metric"><span>Seçili vaka paketi</span><strong>' + str(len(index.cases)) +
        '</strong><span class="small">Yalnız bu portföye alınan ZIP’ler</span></div>',
        '<div class="metric"><span>Aşama kaydı</span><strong>' + str(stage_count) +
        '</strong><span class="small">Paketlerin bildirdiği durumlar</span></div>',
        '<div class="metric"><span>Açık blocker kategorisi</span><strong>' + str(open_categories) +
        '</strong><span class="small">Güvenlik puanı değildir</span></div></section>',
        '<section class="section"><h2>Karar ve kanıt bekleyen paketler</h2>',
        '<p class="section-note">Bir pakette birden fazla blocker olabilir. Bu grupların toplamı paket sayısını aşabilir. '
        'Sayılar müşteri, gerçek değerlendirme, zafiyet veya güvenli sistem sayısı değildir.</p>',
        '<div class="table-scroll" role="region" aria-label="Blocker grupları" tabindex="0"><table>',
        '<thead><tr><th scope="col">Kaynak blocker</th><th scope="col" class="count">Bildiren paket</th></tr></thead><tbody>',
    ]
    for row in index.blocker_summary:
        parts.append('<tr><th scope="row">' + _h(_label(_BLOCKERS, row.code)) +
                     '<div class="code">' + _h(row.code) + '</div></th><td class="count">' +
                     str(row.case_bundle_count) + '</td></tr>')
    parts.extend([
        '</tbody></table></div></section><section class="section"><h2>Aşamaların portföy görünümü</h2>',
        '<p class="section-note">Mevcut aşama durumları, çalışma başarısı veya uzman onayı olarak yorumlanmaz.</p>',
        '<div class="table-scroll" role="region" aria-label="Aşama grupları" tabindex="0"><table>',
        '<thead><tr><th scope="col">Aşama</th><th scope="col">Bildirilen durum</th><th scope="col" class="count">Paket</th></tr></thead><tbody>',
    ])
    for row in index.stage_summary:
        parts.append('<tr><th scope="row">' + _h(_label(_STAGES, row.stage)) + '</th><td>' +
                     _h(_label(_STATUSES, row.status)) + '<div class="code">' + _h(row.status) +
                     '</div></td><td class="count">' + str(row.case_bundle_count) + '</td></tr>')
    parts.extend([
        '</tbody></table></div></section><section class="section"><h2>Seçili vaka paketleri</h2>',
        '<p class="section-note">Vaka referansları kaynak organizasyon etiketidir. Farklı müşteri veya bağımsız çalışma kimliği oluşturmaz.</p>',
        '<div class="table-scroll" role="region" aria-label="Vaka paketi listesi" tabindex="0"><table class="case-list">',
        '<thead><tr><th scope="col">Vaka referansı</th><th scope="col">Paket içi tutarlılık</th>',
        '<th scope="col">Açık blocker</th><th scope="col">Yürütme bağı</th></tr></thead><tbody>',
    ])
    for case in index.cases:
        parts.append('<tr><th scope="row">' + _h(case.case_reference) +
                     ('' if case.display_label is None else '<div class="code">' + _h(case.display_label) + '</div>') +
                     '</th><td><span class="pill">İçerik ilişkisi tutarlı</span></td><td>' + str(len(case.blockers)) +
                     '</td><td><span class="pill pill-warn">Kurulmamış</span></td></tr>')
    parts.extend(['</tbody></table></div>'])
    parts.extend(_html_case(case, index.display_preferences) for case in index.cases)
    parts.extend([
        '</section><section class="section trust"><h2>Güven sınırı</h2>',
        '<p>Paket içi tutarlılık üretici, uzman veya kurum doğrulaması değildir. Orijinal kaynak dosyalar '
        'yeniden okunmaz; kaynak ilişkileri yeniden kontrol edilmiş sayılmaz. Portföye alınmak çalışma yetkisi, '
        'planın uygulanması veya müşteri teslim onayı vermez.</p>',
        '<p>Bu görünüm izinli metadata ile sınırlıdır. Ham assessment, hedef bilgisi, credential, iç dosya yolu '
        've serbest uzman notları içermez. Veri minimizasyonu otomatik sır tespiti veya anonimlik garantisi değildir.</p>',
        '<p class="flags">' + _h(_FLAG_STATEMENT) + '</p></section>',
        '<footer>Çevrimdışı durum indeksi · Yalnız seçili sentetik paketler · Güvenlik sertifikası veya müşteri teslim onayı değildir.</footer>',
        '</main></body></html>',
    ])
    raw = "".join(parts).encode("utf-8", "strict")
    if len(raw) > MAX_HTML_BYTES:
        raise InputError("portfolio_html_size_limit")
    return raw


__all__ = ("render_markdown", "render_html", "MAX_MARKDOWN_BYTES", "MAX_HTML_BYTES")
