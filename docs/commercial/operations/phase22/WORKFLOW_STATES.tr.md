# Vaka aşamaları ve açık kararlar

**DEMONSTRATION ONLY — NO REAL SYSTEM ASSESSED OR CLIENT DELIVERY AUTHORIZED**

İş durumu yalnız seçili gerçek dosyaların metadata'sından türetilir. Aşamalar
birbirinin yerine geçmez. `artifact_present`, `artifact_missing`,
`content_consistent`, `content_inconsistent`, `relationship_not_established`,
`human_review_pending`, `delivery_not_authorized` sağlık/başarı puanı değildir.

| Aşama | Mevcut demo'nun sınırlı anlamı |
| --- | --- |
| Scope planning | Plan mevcut; precondition `pending_authorization`; gerçek yetki yok |
| Assessment reported | Bağımsız sentetik `complete` beyanı mevcut; producer doğrulanmadı |
| Observation intake | Dört observation metadata'sı kaynağıyla bağlı; uzman incelemesi değil |
| Analyst review | Boş overlay; dört `unreviewed`, dört `unknown` scope, dört `pending_decision` inclusion |
| Client handoff | Önceki onaylanmamış demo taslak; release yetkisi yok |
| Traceability | Plan → assessment execution bağı `not_established` |

Assessment'ın `complete` beyanı planın tamamlandığını göstermez. Observation
bulunmaması temiz/güvenli sistem sonucu değildir. İki kaynakta aynı profil,
capability, fingerprint, dosya hash'i veya input bulunması aynı run'a kanıt
değildir. Plan limitleri gerçekleşmiş request/time tüketimine dönüştürülmez.

Mevcut kaynaklarda karşılığı olan yedi açık blocker:

- `authorization_missing`: gerçek çalışma yetkisi sağlanmadı.
- `execution_binding_missing`: plan ile assessment arasında güvenilir run bağı yok.
- `producer_not_verified`: hash ilişkisi üretici doğrulaması değil.
- `human_review_pending`: boş overlay ve incelenmemiş kayıtlar insan kararı değil.
- `data_handling_pending`: veri işleme kararı yok.
- `delivery_not_authorized`: demo ve release engelleri devam ediyor.
- `runtime_acceptance_not_performed`: native/runtime güvenlik kabulü yapılmadı.

Bu kodlar kullanıcı adına kapatılmaz. Başka ürünlerde aynı problemin bulunduğu
varsayılmaz. Yeni iş atama, reviewer/owner uydurma veya uzaktan eylem yoktur.

`demo_only=true`; `execution_binding=not_established` kalır.
`plan_execution_verified`, `scope_fulfillment_verified`, `authorization_verified`,
`human_review_verified`, `producer_verified`, `release_authorized`,
`execution_authorized`, `production_ready` false'tur. Bir paketin iç tutarlılığı
bu alanları değiştirmez. Gerçek uzman/kurum/müşteri kararları ve runtime kabulü
ayrı kapılar olarak açıktır.
