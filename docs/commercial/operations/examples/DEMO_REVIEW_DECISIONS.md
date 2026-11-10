# Demo inceleme karar kayıtları — Internal Review Record

**Demonstration only — No real system assessed.**

`case_id=DEMO-TERMIVAR-015`; `demo_only=true`. Bu dosya dört **bekleyen karar kaydını** somut olarak doldurur; karar verilmiş veya uzman incelemesi tamamlanmış gibi göstermez. Metadata, tam byte SHA256 ve JSON pointer kontrolü yalnız belge izlenebilirliği içindir. Ham kanıt, gerçek kapsam veya teknik etki uzman tarafından incelenmedi.

Her kayıt [ledger](DEMO_OBSERVATION_LEDGER.md) içindeki ilgili `observation_ref`e bağlıdır: `ART-A1` / [assessment.json](../../examples/assessment.json), tam dosya SHA256 `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9`. Aşağıdaki OBS etiketleri dahili sıra etiketleridir; gerçek kaynak kimliği fingerprint ve pointer'dır.

## OBS-01

| Alan | Doldurulmuş kayıt |
| --- | --- |
| `observation_ref` | `sha256:32adc97266dff2c8c11116f202bc894adcab02b7a9f1c315f988f1878bd10004` + `/items/0` + yukarıdaki A1 byte hash'i |
| Kaynak etiketleri | `informational` / `observation`; severity `null`; Referrer-Policy kaynak gözlemi |
| `scope_status` / `review_status` | `unknown` / `unreviewed` |
| `decision_id` / `reviewer` / `reviewed_at` | `not_provided` / `not_provided` / `not_provided` |
| `client_inclusion` | `pending_decision` |
| `review_reason` | Kapsam ilişkisi ve opaque evidence içerikleri uzman tarafından değerlendirilmedi; dahil etme/hariç tutma kararı yok |
| Kararın mevcut dayanağı / sınırı | Ledger'de kaydedilen kaynak metadata'sı var; teknik doğrulama ve ham kanıt incelemesi yok |
| `follow_up` | Yetkili uzman kapsam ve paylaşılabilir kanıt üzerinden disclosure bağlamını değerlendirmeli; gerekçeli karar ayrı kaydedilmeli |
| Handoff bağlantısı | [İnceleme bekleyen alanlar](DEMO_CLIENT_HANDOFF.md#5-inceleme-bekleyen-ve-sonuçlandırılamayan-alanlar); müşteri bulgusu olarak dahil edilmedi, bu bir hariç tutma kararı da değil |

## OBS-02

| Alan | Doldurulmuş kayıt |
| --- | --- |
| `observation_ref` | `sha256:423a41c26f6479fa1d15e672819aea23926e3dee76902559fe92cbc564ddf53a` + `/items/1` + yukarıdaki A1 byte hash'i |
| Kaynak etiketleri | `informational` / `observation`; severity `null`; X-Content-Type-Options kaynak gözlemi |
| `scope_status` / `review_status` | `unknown` / `unreviewed` |
| `decision_id` / `reviewer` / `reviewed_at` | `not_provided` / `not_provided` / `not_provided` |
| `client_inclusion` | `pending_decision` |
| `review_reason` | Response/content bağlamı, kapsam ve kanıt erişimi incelenmedi; kaynak gözlem zafiyet kararı yapılmadı |
| Kararın mevcut dayanağı / sınırı | Kaynak metadata'sı ve opaque referans listesi var; MIME etkisi veya istismar kanıtı incelenmedi |
| `follow_up` | Yetkili uzman mevcut kanıtın yeterliliğini ve content uyumluluğunu değerlendirmeli; paylaşım kararı ile teknik doğrulamayı ayrı açıklamalı |
| Handoff bağlantısı | [İnceleme bekleyen alanlar](DEMO_CLIENT_HANDOFF.md#5-inceleme-bekleyen-ve-sonuçlandırılamayan-alanlar); bekliyor, dahil/hariç kararı yok |

## OBS-03

| Alan | Doldurulmuş kayıt |
| --- | --- |
| `observation_ref` | `sha256:e0e9548ae2581d2522aac9b1cdce9ade61e4010d02308c716f252a15cbb7addb` + `/items/2` + yukarıdaki A1 byte hash'i |
| Kaynak etiketleri | `informational` / `observation`; severity `null`; Permissions-Policy kaynak gözlemi |
| `scope_status` / `review_status` | `unknown` / `unreviewed` |
| `decision_id` / `reviewer` / `reviewed_at` | `not_provided` / `not_provided` / `not_provided` |
| `client_inclusion` | `pending_decision` |
| `review_reason` | Uygulamanın browser feature ihtiyacı ve kanıt ilişkisi uzman tarafından incelenmedi |
| Kararın mevcut dayanağı / sınırı | Kaynak informational metadata'sı var; feature etkisi veya müşteri kapsamı bağımsız belirlenmedi |
| `follow_up` | Yetkili uzman kapsam/kanıt ve gerekli browser feature bağlamını incelemeli; gerekçe ve kalan belirsizliklerle ayrı karar kaydı oluşturmalı |
| Handoff bağlantısı | [İnceleme bekleyen alanlar](DEMO_CLIENT_HANDOFF.md#5-inceleme-bekleyen-ve-sonuçlandırılamayan-alanlar); bekliyor, dahil/hariç kararı yok |

## OBS-04

| Alan | Doldurulmuş kayıt |
| --- | --- |
| `observation_ref` | `sha256:fa8c2374a132316b67a492e8ab213f26b389c9fecefcdf39685026c75fde46f2` + `/items/3` + yukarıdaki A1 byte hash'i |
| Kaynak etiketleri | `informational` / `observation`; severity `null`; Content-Security-Policy kaynak gözlemi |
| `scope_status` / `review_status` | `unknown` / `unreviewed` |
| `decision_id` / `reviewer` / `reviewed_at` | `not_provided` / `not_provided` / `not_provided` |
| `client_inclusion` | `pending_decision` |
| `review_reason` | CSP gözleminin kanıt/kapsam bağı, uygulama bağlamı ve paylaşım uygunluğu uzman tarafından değerlendirilmedi |
| Kararın mevcut dayanağı / sınırı | Kaynak metadata'sı var; XSS, etki, sömürülebilirlik veya uygulanmış düzeltme kanıtı yok |
| `follow_up` | Yetkili uzman uygun mevcut kanıtı ve uygulama bağlamını incelemeli; ek işlem gerekiyorsa ayrıca kapsam/yetki kararı kaydetmeli |
| Handoff bağlantısı | [İnceleme bekleyen alanlar](DEMO_CLIENT_HANDOFF.md#5-inceleme-bekleyen-ve-sonuçlandırılamayan-alanlar); bekliyor, dahil/hariç kararı yok |

## Karar verilmemiş alanların etkisi

Dört kaydın `review_status=unreviewed`, `scope_status=unknown`, `client_inclusion=pending_decision` durumları değişmez. İnsan incelemesi gerçekleştirilmeden `informational_only`, `inconclusive` veya `reviewed_for_delivery` gibi bir insan sonucu seçilmez. Kaynak `informational` değeri insan `informational_only` kararı değildir. Gerçek karar verilmediği için imza, uzman adı, karar zamanı ve `decision_id` uydurulmadı; bu eksiklikler iç kayıttan silinmez.

Phase15'in altılı belge sözlüğü Phase14'ün önerilen insan sözlüğünden ayrıdır; [teslim standardı](../../DELIVERABLE_SPEC.tr.md) değiştirilmedi ve native JSON'a alan eklenmedi. Hiçbir durum otomatik eşlenmedi. Bir gün rapora dahil etme kararı verilmesi dahi zafiyetin bağımsız doğrulandığı anlamına gelmez.

C1/C2/C3 için A1'e retest, risk artışı/azalışı veya remediation kararı yoktur. D1'in unavailable item projection'ı için sıfır bulgu/temiz kararı yoktur. Bunlar dört A1 kaydını olumlu/olumsuz kapatmaz; [case index](DEMO_CASE_INDEX.md) içinde ayrı kaynak kümeleri olarak kalır.

İç kayıtta scope, kanıt erişimi ve gerekçe soruları saklanır. [Handoff taslağı](DEMO_CLIENT_HANDOFF.md) bunları müşteriyle paylaşılmış kararlar, rol atamaları veya ham kanıt olarak taşımıyor. Erişim, redaksiyon, paylaşım ve saklama kararlarının sahibi `not_provided`, kararları `pending_decision`; belge hazırlığı güvenli paylaşım altyapısı veya gerçek erişim kontrolü oluşturmaz.
