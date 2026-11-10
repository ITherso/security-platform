# Gözlem inceleme defteri — iç kayıt şablonu

**Internal Review Record.** Her gerçek kaynak gözlem için aşağıdaki kaydı çoğaltın. Otomatik gözlem, insan incelemesi ve müşteri paylaşım kararı ayrı tutulur. Hariç bırakmak kaydı silmez; eski gerekçeyi koruyup yeni karar referansı ekleyin. Credential, token, cookie veya ham HTTP içeriği buraya yapıştırılmaz; gerekirse kontrollü kanıt referansı kullanılır.

## Defter bağlamı

| Alan | Değer |
| --- | --- |
| case_id / case_record_ref | not_provided / not_provided |
| ledger_ref / ledger_revision | not_provided / not_provided |
| demo_only | pending_decision — gate durumundan ayrı |

## Kaynak gözlem — değişmeden aktarın

| Alan | Değer |
| --- | --- |
| case_id | not_provided |
| source_artifact_ref | not_provided |
| source_artifact | not_provided — mevcut dosya referansı |
| source_artifact_sha256 | not_provided — tam dosya byte SHA256 |
| source_contract / completion_state | not_provided / not_provided |
| observation_ref | not_provided — kaynaktaki mevcut fingerprint/kimlik; yeni fingerprint üretmeyin |
| source_json_pointer | not_provided — örneğin gerçek kayıt konumu; index tahmin etmeyin |
| source_capability_id / subject_reference | not_provided / not_provided |
| source_title / redacted_observation_summary | not_provided / not_provided |
| source_disposition / source_claim_basis | not_provided / not_provided — native değer aynen |
| source_severity | not_provided — native `null` ise aynen `null` / atanmamış kaydedin |
| source_confidence_ppm | not_provided — doğruluk, CVSS veya risk puanı değildir |
| evidence_reference | not_provided — mevcut direct/control/candidate referanslarını ayrı gösterin |
| source_evidence_count | not_provided — öğeler arasında bağımsız kanıt sayısı diye toplamayın |
| source_case_reference / outcome_reference / verification_stage | not_provided / not_provided / not_provided — native null'ları koruyun |
| source_recommendation_ref / summary | not_provided / not_provided — uzman önerisinden ayrı |

`not_provided`, bu şablonda henüz aktarılmamış bilgi demektir; native JSON'a yeni enum/alan olarak yazılmaz. Kaynakta `null` ile alanın hiç bulunmamasını karıştırmayın. `NeedsReview` doğrulanmış zafiyet değildir. `KnowledgeOnly` varsa runtime yetki bağlamıdır; yeni disposition veya temiz sonuç üretmez.

## İnsan incelemesi — kaynak alanlarını değiştirmeyin

| Alan | Değer |
| --- | --- |
| scope_status | unknown — yalnız `in_scope`, `out_of_scope`, `unknown` |
| scope_basis_ref | not_provided — scope listesi tek başına yetki kanıtı değildir |
| evidence_available_to_reviewer / controlled_ref | not_provided |
| evidence_actually_reviewed_ref | not_provided — referansın varlığı incelendi demek değildir |
| evidence_limitations | not_provided — erişilemeyen, redakte veya iddiayı desteklemeyen alanları açıklayın |
| review_status | unreviewed |
| review_reason | not_provided |
| decision_id / decision_record_ref | not_provided / not_provided |
| client_inclusion | pending_decision |
| client_inclusion_reason / approved_client_wording_ref | not_provided / not_provided |
| follow_up | not_provided — gerekiyorsa ayrı yetkili gelecek insan işlemi; başlatılmış değildir |
| follow_up_owner | not_provided |
| reviewer | not_provided |
| reviewed_at | not_provided |
| supersedes_decision_ref / retained_history_ref | not_provided / not_provided |

`review_status`: `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery`. Bunlar insan belge değerleridir, Termivar native sonuç sınıfları değildir. `reviewed_for_delivery` bağımsız zafiyet veya düzeltme doğrulaması değildir. Gerçek inceleyen ve inceleme kanıtı yoksa tamamlanmış inceleme seçilmez.

`client_inclusion`: `pending_decision`, `include_with_limits`, `exclude_with_reason`. Dahil etme paylaşım kararıdır; teknik doğrulama değildir. Hariç bırakma için gerekçe ve geçmiş korunur. Bu kararı native disposition'ı değiştirerek uygulamayın.

Phase14'ün önerdiği eski insan etiketleri (`not_performed`, `needs_additional_evidence`, `reviewed`) bu operasyon sözlüğüne otomatik eşlenmez; gerçek kayıt ve gerekçe üzerinden yeni karar gerekir. Eski belgeler değiştirilmez.

Eksik diagnostic'te unavailable item projection'dan gözlem satırı veya sıfır bulgu türetmeyin; eksikliği [vaka kaydına](CASE_RECORD.template.md) bağlayın. Demo kopyasında **Demonstration only — No real system assessed.** etiketini ekleyin.

Kaynaklar: [inceleme politikası](../OBSERVATION_REVIEW_POLICY.tr.md), [Phase14 kaynak/kanıt ayrımı](../../DELIVERABLE_SPEC.tr.md), [karar kaydı](REVIEW_DECISION.template.md).
