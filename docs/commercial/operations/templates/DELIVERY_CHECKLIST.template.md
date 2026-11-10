# Manuel teslim kontrol kaydı — iç kullanım

**Internal Review Record.** Bu liste bir karar motoru değildir. Kutuların veya metin alanlarının doldurulması dış yetkiyi, uzman incelemesini, veri kararını veya teslim kanıtını üretmez. Gerekli dış kanıt yoksa kapı `blocked` ya da `pending_decision` kalır; gerçek satış/pilot/üretim GO'su verilmez.

| Alan | Değer |
| --- | --- |
| case_id / case_record_ref | not_provided / not_provided |
| checklist_ref / revision | not_provided / not_provided |
| observation_ledger_ref / decision_refs | not_provided / not_provided |
| client_handoff_draft_ref | not_provided |
| demo_only | pending_decision — ayrı işaret; gate değeri değildir |
| checker / checked_at | not_provided / not_provided |

Yalnız dört gate değeri kullanılır: `ready_for_manual_review`, `blocked`, `pending_decision`, `not_applicable`. `not_applicable` yalnız gerekçeli gerçek kapsam kararıyla seçilir. `ready_for_manual_review` manuel incelemeye hazır demektir; teslim, müşteri onayı veya teknik kabul değildir.

## Kontroller

Her satır için somut mevcut kanıt ve karar sahibini girin; eksikliği açıklayın. Kaynak gözlemlerinin zinciri `case_id` → `source_artifact_ref` + tam byte SHA256 → mevcut fingerprint/`observation_ref` + JSON pointer → karar kaydı → paylaşılması uygun handoff öğesi olarak korunur.

| No | Kontrol ve aranacak mevcut kayıt | Gate | Kanıt/karar referansı ve eksik | Karar sahibi |
| --- | --- | --- | --- | --- |
| 1 | Değerlendirme kapsamı, yetki, izinli eylemler ve hariçler | blocked | not_provided | not_provided |
| 2 | Her kaynak artefaktın provenance, sözleşme ve byte kimliği; tarihsel fixture ayrımı | pending_decision | not_provided | not_provided |
| 3 | Complete/diagnostic/failed ayrımı, bütçe/kapsam eksikleri; unavailable hiçbir zaman sıfır bulgu değildir | pending_decision | not_provided | not_provided |
| 4 | Her gözlem için gerçek uzman inceleme durumu, dayanak ve inceleyen; tamamlanmamış işler görünür | blocked | not_provided | not_provided |
| 5 | Müşteriye sunulacak her iddia için source/decision bağı; yorum, native sonuç ve doğrulama ayrı | blocked | not_provided | not_provided |
| 6 | Hassas veri minimizasyonu ve paylaşım kararı; sır/ham HTTP/iç notlar otomatik taşınmamış | pending_decision | not_provided | not_provided |
| 7 | Manifest/hash bilgisinin yapılan gerçek kontrol kadar anlatılması; eksik HTML/full-bundle ve authenticity sınırı | pending_decision | not_provided | not_provided |
| 8 | Comparison varsa doğru before/after hash'leri ve kapsam beyanı; bağımsız fixture retest sayılmamış | pending_decision | not_provided | not_provided |
| 9 | Saklama, erişim, aktarım ve silme kararları ile sahipleri | pending_decision | not_provided | not_provided |
| 10 | Gerçek teslim sahibi ve paylaşılması uygun alıcı/kanal kararının belirlenmesi | blocked | not_provided | not_provided |
| 11 | Gerçek müşteri kabul süreci ve kayıt yöntemi; gerçekleşmemiş kabul varsayılmamış | pending_decision | not_provided | not_provided |
| 12 | Gerekli teknik/kurumsal/hukuki kararlar ve kullanılan yola ait açık kabul kapıları | blocked | not_provided | not_provided |

## Sonuç ve takip

| Alan | Değer |
| --- | --- |
| overall_delivery_gate | blocked |
| unresolved_blockers / evidence_refs | not_provided — yukarıdaki eksiklere ayrı referans verin |
| pending_decisions / owners | not_provided |
| manual_review_reason | not_provided |
| decision_owner / decision_recorded_at | not_provided / not_provided |
| client_inclusion_decision_refs | not_provided |
| actual_delivery_evidence_ref / delivered_at | not_provided / not_provided |
| actual_customer_acceptance_ref / accepted_at | not_provided / not_provided |
| follow_up / closure_record_ref | not_provided / not_provided |

İncelemesi bitmemiş veya excluded kayıtlar silinmez; müşteri handoff'unda neyin hangi sınırla görüneceği ayrıca belirlenir. `only_in_before` düzeltme, `changed` otomatik risk değişimi, `unchanged` aynı güvenlik düzeyi değildir. Hash/manifest/parse başarısı producer kimliği veya bulgu doğruluğu değildir. Bu dosya gerçek teslim yapılmış gibi `delivered` durumu yaratmaz.

Demo kopyasında **Demonstration only — No real system assessed.** etiketini ekleyin; demo kaydının incelenebilirliği gerçek müşteri kapılarını kapatmaz.

Kaynaklar: [manuel teslim kapısı](../DELIVERY_GATE.tr.md), [veri işleme kararları](../DATA_HANDLING.tr.md), [Phase14 açık pilot kapıları](../../PILOT_READINESS.tr.md), [teslim standardı](../../DELIVERABLE_SPEC.tr.md).
