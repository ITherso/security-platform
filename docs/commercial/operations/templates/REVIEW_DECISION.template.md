# Gözlem karar kaydı — iç kullanım şablonu

**Internal Review Record.** Bir mevcut gözleme ilişkin insan kararını kaydeder. Kaynak sonucunu değiştirmez, yeni teknik doğrulama veya gerçek çalışma izni üretmez. Aynı gözlem için yeni karar verildiğinde önceki kayıt silinmez; supersedes bağlantısıyla geçmiş korunur.

## Kaynak ve defter bağlantısı

| Alan | Değer |
| --- | --- |
| case_id / case_record_ref | not_provided / not_provided |
| decision_id | not_provided |
| observation_ledger_ref | not_provided |
| source_artifact_ref / source_artifact | not_provided / not_provided |
| source_artifact_sha256 | not_provided — mevcut tam byte SHA256 |
| observation_ref | not_provided — kaynaktaki mevcut fingerprint/kimlik |
| source_json_pointer | not_provided |
| source_disposition / source_claim_basis | not_provided / not_provided |
| source_severity / source_confidence_ppm | not_provided / not_provided |
| source_evidence_reference | not_provided — direct/control/candidate ayrımını koruyun |
| source_recommendation_ref | not_provided |
| demo_only | pending_decision — teslim kapısından ayrı |

Kaynak severity `null` ise atanmamıştır; low veya sıfır risk değildir. Confidence doğruluk yüzdesi değildir. Native etiket ve hash'i insan yorumuyla değiştirmeyin; kaynak artefakt yoksa mevcutmuş gibi karar bağlamayın.

## İncelemenin dayanağı ve kararı

| Alan | Değer |
| --- | --- |
| scope_status | unknown — `in_scope` / `out_of_scope` / `unknown` |
| scope_basis_ref | not_provided |
| evidence_actually_available_ref | not_provided |
| evidence_actually_reviewed_ref | not_provided |
| evidence_limitations / missing_context | not_provided |
| review_status | unreviewed |
| review_reason | not_provided — hangi mevcut kanıt hangi açıklamayı destekliyor? |
| claims_not_supported_by_evidence | not_provided |
| client_inclusion | pending_decision |
| client_inclusion_reason | not_provided |
| client_safe_wording_ref | not_provided — iç notların otomatik kopyası değildir |
| redaction_or_exclusion_reason | not_provided |
| follow_up / required_separate_authorization_ref | not_provided / not_provided |
| reviewer / reviewed_at | not_provided / not_provided |
| supersedes_decision_ref / retained_history_ref | not_provided / not_provided |

Yalnız şu insan `review_status` değerlerini kullanın: `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery`. İnceleme yapılmadıysa `unreviewed` kalır. `reviewed_for_delivery`, bağımsız zafiyet/etki/düzeltme doğrulaması veya genel teslim onayı değildir. Phase14'teki eski öneri insan etiketleri otomatik onaya çevrilmez.

Yalnız şu paylaşım değerlerini kullanın: `pending_decision`, `include_with_limits`, `exclude_with_reason`. Dahil etme, belirtilen sınırlarla neyin paylaşılacağına ilişkindir. Hariç bırakma kaydı silmez; gerekçe, kaynak bağlantısı ve karar geçmişi iç defterde kalır. Yetersiz kanıt `inconclusive` veya `needs_manual_review` olarak açık kalabilir; boşluk temiz sonuç değildir.

## İlgili teslim ve takip kayıtları

| Alan | Değer |
| --- | --- |
| client_handoff_item_ref | not_provided — yalnız paylaşım kararı sonrası güvenli açıklama |
| delivery_checklist_ref | not_provided |
| associated_delivery_gate | blocked — dış yetki ve işletimsel kanıt burada verilmez |
| decision_follow_up_owner | not_provided |
| follow_up_completion_evidence_ref | not_provided |

Gate yalnız `ready_for_manual_review`, `blocked`, `pending_decision`, `not_applicable` olabilir; inceleme için hazır olmak gerçek teslim/GO değildir. Yeni canlı işlem veya yeniden tarama önerisi yalnız ayrı yetkili gelecek iş olarak kaydedilir. Demo kopyasında **Demonstration only — No real system assessed.** etiketini ekleyin.

Kaynaklar: [gözlem politikası](../OBSERVATION_REVIEW_POLICY.tr.md), [manuel teslim kapısı](../DELIVERY_GATE.tr.md), [teslim standardı](../../DELIVERABLE_SPEC.tr.md).
