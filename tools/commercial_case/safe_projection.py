"""Pure allowlist projection and Markdown; never follow source references."""
from __future__ import annotations

from .case_contracts import (
    CaseEvidence, CaseProjection, DEMO_LABEL, InputError,
    projection_to_dict, validate_projection,
)
from .workflow_status import derive_blockers, derive_workflow


CASE_README_BYTES = (DEMO_LABEL + "\n\n" +
    "This ZIP is a portable demo case-status projection, not a full evidence archive.\n"
    "Only five fixed metadata/text members are included. Original source artifacts,\n"
    "target values, local paths, raw assessment/HTTP/evidence and private notes are absent.\n"
    "Without original source files, their external relationships cannot be independently\n"
    "rechecked. An inspector checks this bundle's internal content consistency only.\n"
    "Hashes are not signatures, producer authentication or an authorization record.\n"
    "execution_binding=not_established; demo_only=true.\n"
    "plan_execution_verified=false; scope_fulfillment_verified=false; authorization_verified=false.\n"
    "human_review_verified=false; producer_verified=false; release_authorized=false.\n"
    "execution_authorized=false; production_ready=false.\n"
    "An empty decision overlay is not expert review. No client delivery is authorized.\n"
    "Existing handoff drafts are prior Phase18-era Phase16 builder artifacts; matching\n"
    "input bytes do not establish a new Phase19 builder execution or any real delivery.\n"
    "No native scanner, target, network or customer action is started by this bundle.\n"
    "Hostile JSON/ZIP/path/race/crash and repeated determinism acceptance are NOT_RUN.\n"
    "This is neither encryption, automatic redaction nor a secret-scanning guarantee.\n"
).encode("utf-8")

_STAGE_LABELS = {
    "scope_planning": "Kapsam planlama", "assessment_reported": "Assessment beyanı",
    "observation_intake": "Observation intake", "analyst_review": "Uzman inceleme hazırlığı",
    "client_handoff": "Müşteri teslim taslağı", "traceability": "Plan–assessment izlenebilirliği",
}


def build_projection(case_reference: str, evidence: CaseEvidence) -> CaseProjection:
    if type(evidence) is not CaseEvidence:
        raise InputError("case_invalid_evidence")
    projection = CaseProjection(case_reference, evidence.artifacts,
        evidence.relationships, evidence.observations, evidence.facts,
        derive_workflow(evidence), derive_blockers(evidence))
    # A closed reparse applies the same contract as the independent ZIP reader.
    return validate_projection(projection_to_dict(projection))


def _text(value: object) -> str:
    return "".join("&#" + str(ord(char)) + ";"
                   if char in "!\"#$%&'()*+,-./:;<=>?@[\\]^_`{|}~" else char
                   for char in str(value))


def render_case_summary(projection: CaseProjection) -> bytes:
    projection = validate_projection(projection_to_dict(projection))
    facts = projection.facts
    lines = ["# Çevrimdışı vaka durum özeti", "", DEMO_LABEL, "",
        "Bu paket kaynakların tam delil arşivi değildir. Yalnız izinli metadata ve durum "
        "projeksiyonu taşır; orijinal kaynaklar olmadan dış ilişkiler yeniden doğrulanamaz.", "",
        "- Sentetik organizasyon referansı: " + _text(projection.case_reference),
        "- execution_binding=not_established", "",
        "## Aşamalar", ""]
    for row in projection.stages:
        lines.extend(["- " + _text(_STAGE_LABELS[row.stage] + ": " + row.status),
                      "  - Kaynak rolleri: " + _text(", ".join(row.source_roles)),
                      "  - Sınırlar: " + _text(", ".join(row.limitations))])
    lines.extend(["", "## Kaynakların bildirdiği sınırlı durum", "",
        "- Plan önkoşulu: " + _text(facts.plan_precondition),
        "- Bağımsız assessment beyanı: " + _text(facts.assessment_status),
        "- Observation / incelenmemiş / kapsamı bilinmeyen / dahil etme kararı bekleyen: " +
        _text(" / ".join(str(n) for n in (facts.observation_count, facts.unreviewed_count,
                     facts.unknown_scope_count, facts.pending_inclusion_count))),
        "- Overlay karar sayısı: " + _text(facts.overlay_decision_count),
        "- Reconciled observation sayısı: " + _text(facts.reconciled_observation_count),
        "- Handoff input bağı: " + _text(facts.handoff_input_binding),
        "- Handoff manifest kapsamı: " + _text(facts.handoff_manifest_scope), "",
        "Handoff taslakları önceki Phase18 dönemindeki Phase16 builder çıktılarını temsil eder. "
        "Aynı input byte'ları, Phase19'da yeni builder çalıştığını veya gerçek müşteri teslimini göstermez. "
        "Boş overlay uzman incelemesi veya onay değildir.", "",
        "## Ayrı kaynak gözlemleri", ""])
    for row in projection.observations:
        lines.extend(["- " + _text(row.observation_id + " → " + row.source_pointer + " / " + row.capability_id),
            "  - Fingerprint etiketi: " + _text(row.fingerprint),
            "  - Disposition / review / scope / inclusion: " + _text(
                " / ".join((row.disposition, row.review_status, row.scope_status, row.client_inclusion)))])
    lines.extend(["", "Fingerprint etiketleri üretici veya bulgu doğrulaması değildir; eşit etiketli "
                  "farklı observation'lar ayrı kaynak konumlarıyla korunur.", "",
                  "## Kaynak ilişkileri", ""])
    for row in projection.relationships:
        lines.extend(["- " + _text(row.relationship_id + " / " + row.kind + ": " + row.status),
            "  - Roller: " + _text(", ".join(row.source_roles)),
            "  - Sınırlar: " + _text(", ".join(row.limitations))])
    lines.extend(["", "Dosya byte/hash, assessment observation ve review packet bağları, planın "
        "assessment ile yürütüldüğü bağından ayrıdır. İlk ilişkilerin tutarlı olması sonuncuyu kurmaz.", "",
        "## Açık karar ve engeller", ""])
    lines.extend("- " + _text(code) for code in projection.blockers)
    lines.extend(["", "Gerçek yetki, scope owner, veri işleme, producer, uzman, runtime ve müşteri "
        "kararları bu paket tarafından verilmez. Otomatik iş atama veya uzaktan eylem yoktur.", "",
        "## Kaynak içerik kimlikleri", ""])
    for row in projection.artifacts:
        lines.append("- " + _text(row.role + " / " + row.contract + " / " + row.status +
            " / " + str(row.byte_length) + " byte / SHA256 " + str(row.sha256)))
    lines.extend(["", "İç dosya yolları, hedef URL/IP/domain, ham assessment/HTTP/evidence, credential "
        "ve serbest uzman notları bu projeksiyona alınmaz. Kaynak dosyalar ZIP'e kopyalanmaz. "
        "Hash, signature veya attestation yerine geçmez. Otomatik redaksiyon, sır taraması, "
        "şifreleme veya güvenli silme garantisi yoktur.", "",
        "demo_only=true; plan_execution_verified=false; scope_fulfillment_verified=false; "
        "authorization_verified=false; human_review_verified=false; producer_verified=false; "
        "release_authorized=false; execution_authorized=false; production_ready=false.", "",
        "## NOT_RUN — açık kabul kapıları", "",
        "Malformed/duplicate/hostile JSON, değiştirilmiş pointer/mapping/manifest, unknown schema, "
        "ZIP bomb/compression abuse/path traversal, symlink/reparse/race/permission/crash/partial-write "
        "ve tekrarlı determinism kabulü yapılmadı. Gerçek producer/uzman/kurum/çalışma/müşteri "
        "doğrulaması ve teslimi yapılmadı. Bu sentetik üretim/okuma akışı otomatik test veya güvenlik "
        "kabulü değildir. Native scanner, ağ, gerçek hedef veya sonraki faz başlatılmaz.", ""])
    raw = "\n".join(lines).encode("utf-8", "strict")
    if len(raw) > 128 * 1024:
        raise InputError("case_summary_size_limit")
    return raw
