# Vaka kaydı — elle doldurulacak iç kayıt

**Internal Review Record.** Bu form çalışma, tarama, müşteri teslimi veya veri erişim yetkisi vermez. Boş değerleri gerçek kanıt olmadan tamamlamayın. `not_provided` veri/kanıt bulunmadığını, `pending_decision` karar verilmediğini gösterir; ikisi onay değildir.

## Vaka ve kapsam

| Alan | Değer / mevcut kayıt referansı |
| --- | --- |
| case_id | not_provided |
| case_record_ref | not_provided |
| customer_organization_ref | not_provided |
| assessment_purpose | not_provided |
| demo_only | pending_decision — gerçek veya demo bağlamını açıkça seçin; gate durumu değildir |
| authorization_record_ref | not_provided — credential veya imza içeriği yazmayın |
| authorization_limits | not_provided |
| authorization_gate | blocked |
| permitted_scope_ref / özeti | not_provided — ayrıca yetki kanıtı gerekir |
| excluded_scope / üçüncü taraf sınırları | not_provided |
| permitted_actions | not_provided |
| operating_window | not_provided |
| approved_request_budget | not_provided — source default kabul edilmiş limit değildir |
| approved_time_budget | not_provided |
| other_approved_limits / provider kapsamı | not_provided |
| stop_conditions / stop_contact_ref | not_provided |
| expected_deliverables | not_provided |
| data_handling_decision_ref | not_provided |
| retention_access_deletion_decision | pending_decision — süre, hukuki dayanak veya erişim yetkisi uydurmayın |

## Roller ve gerçek zaman kayıtları

| Alan | Değer |
| --- | --- |
| assessment_operator | not_provided |
| analyst_reviewer | not_provided |
| delivery_owner | not_provided |
| customer_acceptance_owner | not_provided |
| case_opened_at | not_provided |
| authorized_execution_started_at / ended_at | not_provided |
| review_started_at / ended_at | not_provided |
| preparation / review / reporting / support effort | not_provided — ayrı gerçek süreler; sayaçlardan saat türetmeyin |

## Artefakt kaydı — her mevcut dosya için bu tabloyu çoğaltın

| Alan | Değer |
| --- | --- |
| case_id | not_provided |
| source_artifact_ref | not_provided — vaka içi dosya referansı |
| source_artifact | not_provided — mevcut kontrollü dosya referansı; sır veya gereksiz özel yol eklemeyin |
| source_type | not_provided — mevcut assessment / manifest / comparison / diagnostic niteliği |
| contract_schema_version | not_provided — dosyada gerçekten görülen değer |
| source_commit_or_provenance_ref | not_provided — historical generation ile incelenen checkout'u ayırın |
| artifact_origin_description | not_provided — gerçek çıktı / mevcut fixture / elle yazılmış örnek ayrımı |
| source_artifact_sha256 | not_provided — mevcut tam dosya byte hash'i; öğe fingerprint'i değildir |
| source_artifact_bytes | not_provided — ölçülmemişse sayı yazmayın |
| hash_measurement_record_ref / measured_at | not_provided |
| completion_or_diagnostic_state | not_provided — dosyadaki native durum aynen |
| manifest_artifact_ref / presence | not_provided |
| integrity_checks_actually_performed / record_ref | not_provided — yapılmamış verify veya full-bundle kontrolü yazmayın |
| integrity_result / unchecked_parts | not_verified / not_provided |
| source_authenticity_evidence_ref | not_provided — hash, manifest ve parse başarısı kimlik doğrulamaz |
| relationship_to_primary_assessment | not_provided — bağımsız comparison/diagnostic'i aynı koşuya bağlamayın |
| client_sharing_decision_ref | not_provided |

Assessment öğeleri ledger'a `case_id` + `source_artifact_ref` + `source_artifact_sha256` + mevcut `observation_ref`/fingerprint + JSON pointer ile bağlanır. Dosyada item yoksa kimlik uydurmayın; diagnostic eksikliğini öğe dışı vaka kaydı olarak tutun. Native `complete`, exhaustive coverage veya güvenli sistem demek değildir; unavailable projection sıfır bulgu değildir.

## İnceleme, teslim ve kapanış bağlantıları

| Alan | Değer |
| --- | --- |
| observation_ledger_ref | not_provided |
| review_decision_refs | not_provided |
| unresolved_evidence_or_scope_questions | not_provided |
| delivery_checklist_ref | not_provided |
| overall_delivery_gate | blocked |
| client_handoff_draft_ref | not_provided |
| actual_delivery_evidence_ref / delivered_at | not_provided |
| actual_customer_acceptance_ref / accepted_at | not_provided |
| follow_up_owner / separately_authorized_actions | not_provided |
| closure_decision_ref / closed_at | not_provided |

Gate sözlüğü yalnız `ready_for_manual_review`, `blocked`, `pending_decision`, `not_applicable` değerlerinden oluşur. `ready_for_manual_review` inceleme kuyruğuna hazır demektir; satış/pilot/üretim GO'su veya gerçek teslim kanıtı değildir. `demo_only` ayrı işarettir; gerçek yetki boşluğunu kapatmaz. Demo kopyasında **Demonstration only — No real system assessed.** etiketini ekleyin.

Kaynaklar: [Phase14 teslim standardı](../../DELIVERABLE_SPEC.tr.md), [pilot kapsamı](../../PILOT_SCOPE.tr.md), [gözlem politikası](../OBSERVATION_REVIEW_POLICY.tr.md), [manuel teslim kapısı](../DELIVERY_GATE.tr.md).
