"""Human-readable bounded Markdown from the closed traceability model."""
from __future__ import annotations

from .contracts import DEMO_LABEL, InputError
from .traceability import (
    HUMAN_REQUIREMENTS, LINKAGE_EXPLANATION, MISSING_EVIDENCE, NOT_RUN,
    TRUST_LIMITATIONS, TraceabilityLedger, ledger_to_dict,
)


def _text(value: object) -> str:
    """Emit body text with punctuation entities, inhibiting links and raw HTML."""
    return "".join(
        "&#" + str(ord(char)) + ";" if char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~"
        else char for char in str(value)
    )


def _value(value: object) -> str:
    return "not_reported" if value is None else _text(value)


def render_summary(ledger: TraceabilityLedger) -> bytes:
    data = ledger_to_dict(ledger)
    plan = data["plan_intent"]
    assessment = data["assessment_reported"]
    binding = data["source_binding"]
    lines = [
        "# Plan ve assessment izlenebilirlik özeti", "", DEMO_LABEL, "",
        "Plan ile assessment'ın aynı değerlendirme çalışmasına ait olduğu kanıtlanmamıştır. "
        "Bu belge yalnız seçilmiş dosyaların kaynakça desteklenen metadata ilişkilerini açıklar.", "",
        "## A. Plan intent — değerlendirilmek istenen", "",
        "- Plan içerik kimliği: " + _text(plan["plan_id"]),
        "- Proposal kimliği: " + _text(plan["proposal_id"]),
        "- Profil: " + _text(plan["profile"]),
        "- Sentetik origin: " + _text(plan["scope"]["origin"]),
        "- Sentetik kök URL: " + _text(plan["scope"]["root_url"]),
        "- Bildirilen yöntemler: " + _text(", ".join(plan["scope"]["requested_methods"])),
        "- Teknik kaynak uyumu: " + _text(plan["technical_status"]),
        "- Önkoşul sonucu: " + _text(plan["precondition_result"]),
        "- Authorization / data handling: " + _text(plan["authorization_status"] + " / " + plan["data_handling_status"]),
        "", "Planın içerik kimliği, raw plan dosyasının SHA256 değeri ve beyan edilen "
        "proposal SHA256'sı farklı kimliklerdir. Orijinal proposal bu araçta açılmaz. "
        "Beyan edilen native kaynak pinleri güncel checkout veya binary attestation'ı değildir.", "",
        "## B. Assessment reported — artefact'ın bildirdiği", "",
        "- Profil: " + _text(assessment["profile"]),
        "- Beyan edilen assessment durumu: " + _text(assessment["status"]),
        "- Beyan edilen subject / item sayısı: " + _text(str(assessment["subject_count"]) + " / " + str(assessment["item_count"])),
        "- Hedef origin / run kimliği: not_reported / not_reported",
        "", "Complete, bağımsız assessment artefact'ının bildirdiği durumdur; planın "
        "tamamlandığını göstermez. Run schema bir sürüm etiketidir. Opaque subject "
        "etiketi hedef URL veya origin değildir. Ham HTTP/başlık/açıklama/credential taşınmaz.", "",
    ]
    for item in assessment["items"]:
        lines.extend([
            "- " + _text(item["source_pointer"] + ": " + item["capability_id"]),
            "  - Namespace / disposition / claim basis: " +
            _text(item["namespace"] + " / " + item["disposition"] + " / " + item["claim_basis"]),
            "  - Kaynak fingerprint etiketi: " + _text(item["fingerprint"]),
            "  - Subject etiketi / evidence referans sayısı: " +
            _text(item["subject_reference"] + " / " + str(item["evidence_reference_count"])),
        ])
    lines.extend([
        "", "## Capability kimlik eşlemesi", "",
        "Aşağıdaki sınıflar yürütme, kapsama veya bulgu doğrulaması değildir. "
        "Eşleme yalnız aynı namespace'teki aynı kaynak kimliğiyle yapılır; isim benzerliği kullanılmaz.", "",
    ])
    for row in data["capability_mappings"]:
        lines.extend([
            "- " + _text(row["namespace"] + " / " + row["capability_id"] + ": " + row["status"]),
            "  - " + _text(row["explanation"]),
            "  - Assessment pointer'ları: " +
            _text(", ".join(row["observation_pointers"]) if row["observation_pointers"] else "not_reported"),
        ])
    lines.extend([
        "", "### Katalogdaki ayrı namespace sınırları", "",
        "Bu kayıtlar katalog sınırını açıklar; capability eşleme listesinin observation'ları "
        "değildir. Seçilmemiş kayıtlar istenmiş kontrol veya başarısız çalışma olarak sayılmaz.", "",
    ])
    for row in data["catalog_namespace_boundaries"]:
        lines.extend([
            "- " + _text(row["namespace"] + " / " + row["capability_id"] + ": " + row["status"]),
            "  - Tür / planda seçilmiş: " + _text(row["kind"] + " / " + str(row["selected_in_plan"]).lower()),
            "  - " + _text(row["explanation"]),
        ])
    lines.extend([
        "", "Katalog sınırlıdır; seçilmemiş tüm yetenekleri rapora tamamlanmış kontrol "
        "olarak eklemez. GraphQL metadata family ve CLI surface, assessment-item "
        "kimliğine dönüştürülmez. Observation bulunmaması başarısız tarama veya güvenli sistem kanıtı değildir.",
        "", "## Kapsam ve bütçe karşılaştırması", "",
        "Planlanan limitler tüketim değildir. Kaynakta olmayan değerler türetilmez. "
        "Subject sayısı request tüketimiyle, complete durumu plan önkoşuluyla eşitlenmez.", "",
    ])
    for row in data["scope_budget_comparison"]:
        lines.extend([
            "- " + _text(row["field"] + ": " + row["status"]),
            "  - Planlanan / assessment'ta bildirilen: " + _value(row["planned_value"]) + " / " + _value(row["assessment_reported_value"]),
            "  - " + _text(row["explanation"]),
        ])
    lines.extend([
        "", "## Assessment → Phase17 observation dosya bağı", "",
        "- Sınırlı sonuç: " + _text(binding["status"]),
        "- Assessment byte SHA256: " + _text(binding["source_assessment_sha256"]),
        "- Fingerprint tekrar bildirimi: " + _text(str(binding["fingerprint_reuse_reported"]).lower()),
        "- Assessment manifesti: " + _text(binding["assessment_manifest_status"]),
        "- Plan manifesti: " + _text(binding["plan_manifest_validation_scope"]),
        "", "Yalnız açıkça seçilen plan/preflight/catalog payload'ları, assessment JSON "
        "entry'si ve Phase17 handoff/mapping byte bağlantıları incelenir. Planın Markdown "
        "özeti ve assessment HTML payload'ı açılmaz. Tam bundle veya üretici doğrulaması yoktur.", "",
    ])
    for row in binding["observation_links"]:
        lines.append("- " + _text(row["observation_id"] + " → " + row["source_pointer"] + " / " + row["capability_id"]))
    lines.extend([
        "", "Pointer ve fingerprint'ler kaynak konumunu açıklar; tekrarlanan fingerprint'ler "
        "birleştirilmez. Bu dosya ilişkisi planın yürütülmesiyle aynı ilişki değildir.", "",
        "## C. Execution linkage — kurulmamış çalışma bağı", "",
        "execution_binding=not_established", "", LINKAGE_EXPLANATION, "",
        "demo_only=true; plan_execution_verified=false; scope_fulfillment_verified=false; "
        "authorization_verified=false; human_review_verified=false; producer_verified=false; "
        "release_authorized=false; execution_authorized=false; production_ready=false.",
        "", "## Eksik kanıt, insan kararı ve blocker'lar", "",
    ])
    lines.extend("- Eksik kanıt: " + _text(item) for item in MISSING_EVIDENCE)
    lines.extend("- İnsan/kurum kararı: " + _text(item) + " — pending_decision" for item in HUMAN_REQUIREMENTS)
    lines.extend("- Blocker: " + _text(item) for item in ledger.blockers)
    lines.extend(["", "## Açıkça seçilen kaynakların byte kimlikleri", ""])
    for source in data["source_files"]:
        lines.append("- " + _text(source["role"] + ": " + source["schema_version"] + " / " +
                                    str(source["byte_length"]) + " byte / SHA256 " + source["sha256"]))
    lines.extend([
        "", "Hashler yalnız içerik bağlantısıdır; imza, producer identity, gerçek yetki, "
        "uzman incelemesi veya çalışma zamanı kabulü değildir.", "", "## Güven sınırları", "",
    ])
    lines.extend("- " + _text(item) for item in TRUST_LIMITATIONS)
    lines.extend(["", "## NOT_RUN — yapılmayan kabuller", ""])
    lines.extend("- " + _text(item) for item in NOT_RUN)
    lines.extend([
        "", "Yalnız sentetik dosyalar incelenir. Kaynak/çıktı okuması otomatik test veya "
        "güvenlik kabulü değildir. Native scanner, yeni assessment, gerçek hedef, ağ/DNS, "
        "gerçek uzman kararı veya müşteri teslimi başlatılmaz.", "",
    ])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if len(raw) > 128 * 1024:
        raise InputError("traceability_summary_size_limit")
    return raw


__all__ = ("render_summary",)
