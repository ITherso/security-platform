# Blocker ve aşama görünürlüğü

**DEMONSTRATION ONLY — OFFLINE CASE PORTFOLIO — NO CLIENT OR EXECUTION VERIFIED**

Triage yalnız mevcut seçili vaka paketlerinin bekleyen karar ve aşamalarını
gösterir. Yeni risk skoru, güvenlik puanı, SLA, son tarih, owner, görev atama,
tamamlanma yüzdesi veya otomatik öncelik üretmez. Metin benzerliğiyle blocker
birleştirilmez; mevcut Phase22 kodları aynen kullanılır.

Yedi kaynak blocker kategorisi:

- `authorization_missing`
- `execution_binding_missing`
- `producer_not_verified`
- `human_review_pending`
- `data_handling_pending`
- `delivery_not_authorized`
- `runtime_acceptance_not_performed`

Bir paket birden fazla kategoride yer alabilir. Bu nedenle blocker toplamları
paket sayısını aşabilir. Sayılar yalnız seçili paketlerde bir kodun kaç kez
bildirildiğini gösterir; bağımsız müşteri, gerçek sistem veya zafiyet sayısı
değildir. Sayım üyeleri mevcut raw ZIP hash'leriyle ilişkilendirilir; yeni vaka
veya run ID oluşturulmaz.

| Kaynak aşaması | Korunan anlam |
| --- | --- |
| `scope_planning` | Plan artefact'ı var; çalışma yetkisi anlamına gelmez |
| `assessment_reported` | Bağımsız assessment beyanı var; planın yürütülmesi değil |
| `observation_intake` | Sınırlı observation metadata bağları; uzman incelemesi değil |
| `analyst_review` | İnceleme bekliyor; boş overlay gerçek karar değil |
| `client_handoff` | Mevcut demo taslak; müşteri teslimi/onayı değil |
| `traceability` | Plan–assessment execution bağı kurulmamış |

Mevcut tek demo, dört `unreviewed`, dört `unknown` scope ve dört
`pending_decision` inclusion bildirir. Portföy bu anlamları korur; observation
ayrıntıları, fingerprint'ler veya serbest reviewer metinlerini yeniden dağıtmaz.
Handoff'un önceki Phase18 dönemindeki Phase16 builder provenance sınırı kaynak
case'in sınırlı facts/stage metadata'sıyla korunur; yeni builder veya gerçek
müşteri işlemi varsayılmaz.

JSON/Markdown/HTML aynı kapalı modelden oluşturulur. Native HTML ayrıntıları
JavaScript gerektirmez; görsel tarayıcı/klavye/dar ekran kabulü ayrı ve bu turda
yapılmadıysa **NOT_RUN**'dır. HTML, kaynak byte kimliğini güvenlik sertifikası
gibi sunmaz; sadece seçili paket durumunu görünür kılar.

Çoklu-vaka kodu en fazla 25 paketi destekleyecek şekilde yazılmıştır; gerçek
üretim yalnız mevcut tek sentetik ZIP'i kullanır. Çoklu-vaka, duplicate ve
conflict davranışları bu tek örnekle çalışma zamanı kabulü kazanmaz.
