# Müşteri teslim taslağı — Termivar destekli değerlendirme

Bu boş şablon **Client Handoff** içindir; iç defterin kopyası değildir. Yalnız `client_inclusion: include_with_limits` kararı bulunan, paylaşım kapsamı belirlenmiş açıklamalar eklenir. `pending_decision` veya `exclude_with_reason` kayıtlarının iç notları/kanıtları otomatik aktarılmaz. Credential, token, cookie, ham HTTP, örnek payload, gereksiz hedef ayrıntısı ve özel dosya yolları eklenmez. Açıklamalar da hassas veri için ayrıca gözden geçirilir. Bu metin erişim kontrolü veya güvenli paylaşım sistemi sağlamaz.

Şablon bir rapor sonucu, teslim izni veya yapılmış uzman incelemesi değildir. Doldurulmamış alanlar `not_provided` / `pending_decision` kalır. `demo_only` ayrı işarettir; demo kopyasına **Demonstration only — No real system assessed.** etiketi eklenir. Gerçek kişi, tarih, imza veya müşteri kabulü uydurulmaz.

## 1. Değerlendirme kimliği ve kapsamı

| Alan | Değer / paylaşılması uygun kayıt referansı |
| --- | --- |
| case_id / handoff_document_ref / document_revision | not_provided / not_provided / not_provided |
| demo_only | pending_decision |
| customer_organization_ref | not_provided |
| assessment_purpose | not_provided |
| authorized_scope_summary / authorization_record_ref | not_provided / not_provided |
| exclusions / third_party_boundaries | not_provided / not_provided |
| operating_window | not_provided |

Kapsam metni ve kaynak referansı, çalışma yetkisini tek başına kanıtlamaz. Tam hedef/kimlik ayrıntıları yalnız gerekli ve paylaşımı uygun olduğunda eklenir.

## 2. Yöntem ve değerlendirme sınırları

| Alan | Değer |
| --- | --- |
| selected_source_or_binary_identity_ref | not_provided — historical generation ile mevcut incelemeyi ayırın |
| actual_profile / selected_capabilities | not_provided / not_provided |
| permitted_actions / excluded_methods | not_provided / not_provided |
| approved_request_budget / approved_time_budget | not_provided / not_provided |
| actual_usage_record_ref / methodology_limits | not_provided / not_provided |

Kaynak varsayılan limitler kabul edilmiş kapsam veya ölçülmüş kullanım değildir. Bütçeler insan inceleme süresi ya da bütün uygulamanın kapsandığı garantisi değildir. Kullanılmayan veya desteklenmeyen alanlar dahil sayılmaz.

## 3. Tamamlanan ve tamamlanamayan çalışmalar

| Çalışma / kaynak referansı | Kaynaktaki gerçek tamamlanma durumu | Tamamlanan sınırlı iş | Eksik/erişilemeyen alan ve etkisi |
| --- | --- | --- | --- |
| not_provided | not_provided | not_provided | not_provided |

Complete assessment, eksiksiz kapsam veya güvenli sistem anlamına gelmez. Incomplete/failed diagnostic ve unavailable item projection ayrı gösterilir; unavailable alan için sıfır bulgu yazılmaz. Önceden yazılmış fixture veya bağımsız comparison aynı assessment koşusuna bağlanmaz.

## 4. Uzman tarafından gözden geçirilmiş sonuçlar, varsa

Yalnız gerçekten incelenmiş ve `include_with_limits` kararıyla paylaşılabilen kayıtlar için bu tabloyu çoğaltın. Hiçbiri yoksa `not_provided — tamamlanmış uzman incelemesi sonucu sunulmuyor` yazın; otomatik gözlemleri doğrulanmış zafiyete çevirmeyin.

| Alan | Müşteriye sunulmasına karar verilmiş bilgi |
| --- | --- |
| handoff_item_ref / case_id | not_provided / not_provided |
| source_artifact_ref / observation_ref | not_provided / not_provided — bölüm 6'daki aynı kaynak bağlantısı |
| source_disposition / source_claim_basis | not_provided / not_provided — değiştirilmeden |
| source_severity / source_confidence_ppm | not_provided / not_provided — native null atanmamıştır; confidence doğruluk değildir |
| review_status / decision_record_ref | unreviewed / not_provided — iç notun kendisi paylaşılmaz |
| client_inclusion | pending_decision |
| approved_client_explanation / explicit_limits | not_provided / not_provided |

İnsan review_status sözlüğü: `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery`. Bunlar native Termivar disposition'ları değildir. `reviewed_for_delivery` bağımsız zafiyet/etki/düzeltme doğrulaması veya genel teslim onayı değildir. `NeedsReview` doğrulanmış zafiyet; `KnowledgeOnly` temiz sonuç veya yeni sonuç sınıfı değildir.

## 5. İnceleme bekleyen ve sonuçlandırılamayan alanlar

| Paylaşılması uygun kayıt referansı | Bekleyen/sonuçlandırılamayan konu | Kanıt/kapsam sınırı | Gerekli insan kararı veya ayrı işlem |
| --- | --- | --- | --- |
| not_provided | not_provided | not_provided | not_provided |

İç defterdeki her bekleyen veya hariç tutulan not müşteriye otomatik kopyalanmaz. Paylaşılması uygun açıklama ayrıca seçilir; müşteri yorumunu etkileyen eksik kapsam gizlenmez. Yetersiz kanıt olumlu veya temiz sonuca çevrilmez.

## 6. Kaynak ve kanıt referansları

| Alan | Paylaşılabilir referans / gerçek mevcut değer |
| --- | --- |
| case_id | not_provided |
| source_artifact_ref / source_artifact | not_provided / not_provided — özel yol veya sır içermeyen referans |
| source_artifact_sha256 / byte_length | not_provided / not_provided — gerçekten mevcut ölçüm |
| source_schema / source_provenance_ref | not_provided / not_provided |
| observation_ref / source_json_pointer | not_provided / not_provided — mevcut fingerprint ve kaynak konumu |
| evidence_reference / evidence_access_limits | not_provided / not_provided — direct/control/candidate ayrımı korunur |
| integrity_checks_actually_performed / unchecked_parts | not_provided / not_provided |

Gerekli her öğe için tabloyu çoğaltın. İç referans, ham kanıtın müşteriye kopyalandığı veya incelendiği anlamına gelmez. Hash, manifest varlığı veya JSON parse başarısı producer kimliği, yetki, bulgu doğruluğu ya da düzeltme kanıtı değildir. Yalnız JSON+manifest varsa eksik HTML/full-bundle kontrolü açıkça belirtilir; yapılmamış verify sonucu yazılmaz.

## 7. Teknik takip önerileri

| Paylaşılabilir öğe referansı | Kaynak önerisi | Ayrı insan takip önerisi ve gerekçesi | Sorumlu rol / gerekli ayrı yetki | Gerçek tamamlanma kanıtı |
| --- | --- | --- | --- | --- |
| not_provided | not_provided | not_provided | not_provided | not_provided |

Öneri uygulanmış veya etkili düzeltme değildir. Canlı işlem, yeni test veya yeniden değerlendirme yalnız gelecekte ayrı yetkilendirilecek iş olarak belirtilir; bu belge başlatmaz.

## 8. Önceki raporla karşılaştırma, destekleniyorsa

| Alan | Değer |
| --- | --- |
| comparison_artifact_ref / sha256 | not_provided / not_provided |
| before_artifact_ref / exact_byte_sha256 | not_provided / not_provided |
| after_artifact_ref / exact_byte_sha256 | not_provided / not_provided |
| relationship_to_this_assessment | not_provided — bağımsız fixture gerçek retest değildir |
| operator_scope_statement_ref / coverage_limits | not_provided / not_provided |
| imported_groups / approved_explanation | not_provided / not_provided — mevcut gruplar aynen; yeniden hesaplama yok |

Uygun kaynak yoksa karşılaştırmanın neden sunulmadığı açıklanır. `only_in_before` düzeltilmiş, `only_in_after` yeni oluşmuş zafiyet değildir. `changed` otomatik risk değişimi; `unchanged` bütün güvenliğin veya kapsamın aynı kalması değildir. İthal etiketler bağımsız onaylanmış sayılmaz.

## 9. Veri ve yorumlama sınırlamaları

| Alan | Değer |
| --- | --- |
| shared_data_categories / approved_redactions_ref | not_provided / not_provided |
| access_transfer_retention_deletion_decision_ref | not_provided |
| decision_owner / unresolved_data_decisions | not_provided / pending_decision |
| remaining_evidence_or_interpretation_limits | not_provided |

Onaylanmamış saklama süresi, hukuki dayanak veya paylaşım hakkı uydurulmaz. Kaynak sonuçları, insan incelemesi, bütünlük ve müşteri kabulü ayrı konulardır. İç notlar, credential ve ham kanıt otomatik paylaşılmaz. Çalışma bütün açıklara karşı koruma, eksiksiz tespit veya güvenli sistem sertifikası sağlamaz.

## 10. Gerçek teslim ve onay bilgileri için boş alan

| Alan | Yalnız gerçekten mevcut kayıt |
| --- | --- |
| manual_delivery_gate_ref / gate_status | not_provided / blocked |
| delivery_owner / intended_authorized_recipient_ref | not_provided / not_provided |
| actual_delivery_evidence_ref / delivered_at | not_provided / not_provided |
| customer_acceptance_evidence_ref / accepted_at | not_provided / not_provided |
| follow_up_agreement_ref / closure_evidence_ref | not_provided / not_provided |

Gate yalnız `ready_for_manual_review`, `blocked`, `pending_decision`, `not_applicable` olabilir. Manuel incelemeye hazır etiketi gerçek teslim veya GO değildir. Gerçek teslim/kabul kanıtı yoksa gerçekleşmiş gibi yazılmaz; bu şablon imza ya da müşteri onayı yaratmaz.

Hazırlama dayanakları: [teslim standardı](../../DELIVERABLE_SPEC.tr.md), [inceleme politikası](../OBSERVATION_REVIEW_POLICY.tr.md), [manuel teslim kapısı](../DELIVERY_GATE.tr.md). Bu bağlantılar iç hazırlık referanslarıdır; bütün iç kayıtlar müşteri paketine otomatik dahil değildir.
