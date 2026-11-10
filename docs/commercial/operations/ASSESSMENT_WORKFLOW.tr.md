# Kaynak gözlemden teslim dosyasına altı aşamalı iş akışı

Bu iş akışı elle tutulan **Internal Review Record** ile ayrı **Client Handoff** dosyasını birbirine bağlar. Bir rolün adı yazılması atama değildir; bir formun doldurulması yetki veya kabul oluşturmaz. Gerçek sahip, kanıt veya karar yoksa `not_provided` / `pending_decision` kalır. Bu fazda yalnız mevcut sentetik dosyalar üzerinde belge hazırlığı vardır; hiçbir değerlendirme veya yeniden tarama çalıştırılmaz.

Ürün sınırı [Phase14 teklifinde](../PRODUCT_OFFERING.tr.md), yetki ve bütçe [pilot kapsamında](../PILOT_SCOPE.tr.md), gerçek pilot önkoşulları [hazırlık kaydında](../PILOT_READINESS.tr.md) tanımlıdır. Aşağıdaki aşamalar bunların nasıl kaydedileceğini açıklar.

## Aşamalar ve durdurma noktaları

| Aşama | Giriş | Somut çıktı | Durdurma koşulu | Sorumlu rol — atanması gerekir |
| --- | --- | --- | --- | --- |
| **A — Kapsam kaydı** | Hizmet amacı, kapsam/yetki kaydı varsa, planlanan yöntem ve veri kararı | [Vaka kaydı](templates/CASE_RECORD.template.md): dahili case_id, kurum ref'i, amaç, yetki durumu, izinli hedef/faaliyet/hariçler, request/zaman bütçesi, beklenen çıktılar, veri kararları ve rol alanları | Yetki/varlık ilişkisi belirsiz; hedef veya faaliyet kabul edilmemiş; durdurma kanalı/veri kararı eksik. Gerçek çalışma başlamaz. | Kapsam sahibi, operatör ve veri kararı sahibi; şu an atanmış sayılmaz. |
| **B — Kaynak artefact kaydı** | Açıkça seçilmiş mevcut dosyalar; mevcut provenance ve önceki doğrulama kayıtları | Vaka içi artefact dizini: tür, dosya ref'i, sözleşme, commit/provenance, completion, manifest, ölçülmüş byte kimliği, yapılan/yapılmayan doğrulama ve ilişki grubu | Eksik/uyumsuz kaynak, belirsiz ilişki veya çözülemeyen kimlik farkı. Dosya elde olması değerlendirme yetkisi oluşturmaz. | Kaynak kayıt sorumlusu; gerektiğinde teknik inceleyici. |
| **C — Gözlem inceleme defteri** | Kaynakta gerçekten bulunan öğeler ve kontrollü kanıt erişimi varsa | [Observation ledger](templates/OBSERVATION_LEDGER.template.md): her öğe için kaynak fingerprint/pointer ve kaynak sınıfı; ayrı review_status, eksikler, kapsam ve takip | Kaynak gözlem bulunamıyor, kanıt eksik/çelişkili veya gerçek inceleme yapılmadı. Onay verilmez; `unreviewed`, gerekiyorsa gerekçeli `needs_manual_review` / `inconclusive` kaydı. | Atanmış güvenlik inceleyicisi; source metadata okuyan kişi otomatik uzman sayılmaz. |
| **D — Teslim kararı** | Ledger, gerçek inceleme gerekçesi ve paylaşım için gerekli karar kanıtı | [Karar kaydı](templates/REVIEW_DECISION.template.md): decision_id, ilgili kaynak/öğe, inceleyen/zaman varsa, gerekçe, sınırlama, client_inclusion ve takip | İnceleme/kanıt/karar sahibi yok; iddia kaynağı aşar; paylaşım kararı eksik. Varsayılan `client_inclusion=pending_decision`. | Gerçek inceleyici ve teslim/iddia kontrolü sahibi; atanmamışsa karar açık. |
| **E — Müşteri paketi hazırlığı** | Paylaşımına karar verilmiş içerik, veri minimizasyonu ve teslim kapısı kayıtları | Ayrı [TR](templates/CLIENT_HANDOFF.template.tr.md) / [EN](templates/CLIENT_HANDOFF.template.en.md) handoff taslağı; desteklenen açıklamalar, kapsam, eksik işler ve kontrollü referanslar | [Veri rehberi](DATA_HANDLING.tr.md) veya [manuel teslim kapısı](DELIVERY_GATE.tr.md) açık; iddia desteklenmiyor; gereksiz hassas veri/iç not var. Taslak paylaşılmaz. | Rapor hazırlayan, veri inceleyicisi ve teslim sahibi; kanıtlarıyla atanmalı. |
| **F — Kapanış ve takip** | Gerçek teslim/alındı ve kabul kaydı varsa; kalan iş listesi | Teslim edilen sürüm ve byte kimliği, gerçekten kullanılan kanal/alıcı ref'i, teslim/kabul kanıtı, açık takipler ve veri kapanış kararları | Teslim veya müşteri kabul kanıtı yok; veri/kurumsal karar eksik; retest yapılmadı. `delivered`, kabul edildi veya düzeltildi yazılmaz. | Teslim ve kapanış sahibi; müşteri kabul rolü ayrıca belirlenmeli. |

Bu tablo yeni faaliyet izni değildir. İleride gerçek çalışma için dış yetki veya teknik kabul gerektiğinde durum [teslim kapısında](DELIVERY_GATE.tr.md) `blocked` ya da `pending_decision` olur. Bir aşamadan çıkmak diğer kapıları geçirmez. Teknik bütçeler ile uzman emeği ayrı kaydedilir; source default ve hard cap müşteri onayı yerine geçmez. Şu an hiçbir build veya gerçek hedef seçilmedi.

## İç dosyada tutulacak iz zinciri

1. **Vaka:** `case_id`, bu operasyon dosyasının dahili kimliğidir. Source run/schema veya müşteri onayı gibi sunulmaz. Müşteri ref'i, yetki/kurum/kişi, zaman, rol ve veri politikası bilinmiyorsa açık durum yazılır.
2. **Artefact:** vaka dizinindeki yerel `source_artifact_ref`, mevcut dosya ref'i ve tam dosya SHA256/byte bilgisine bağlanır. Şema adı JSON'daki gerçek alandır; dosya adı veya uzantıdan türetilmez. Dosya ölçümü ile native verifier sonucu ayrı yazılır. Ölçüm yapılmadıysa `source_artifact_sha256=not_provided`; doğrulanmamış bütünlük sonucu `integrity_result=not_verified` kalır.
3. **Gözlem:** mevcut fingerprint + kaynak dosya + gerçek JSON pointer birlikte korunur. Dahili ledger satır etiketi kaynak kimliğini değiştirmez. Pointer tek başına değişen dosyalarda sabit değildir; byte kimliği bağlamı gerekir. Opaque evidence ref'i ham kanıtın kendisi veya teslim edildiğinin kanıtı değildir.
4. **Karar:** `decision_id`, ledger satırı ve artefact sürümüne bağlanan insan belge kaydıdır. Gerekçe, incelenen mevcut kanıt, sınırlama, dahil etme kararı ve varsa önceki karara ref ayrı tutulur. Hariç bırakılan kayıt silinmez; düzeltmeler önceki sürüme bağlanır. Markdown geçmişi değiştirilemez audit log veya elektronik imza değildir.
5. **Teslim taslağı:** iç kayıttan yalnız paylaşılmasına karar verilen açıklamalar alınır. Handoff'un kontrollü kaynak ref'i, iç gerekçenin tamamını, credential'ı veya ham HTTP kanıtını taşımak zorunda değildir. Her gerçek paylaşım için alıcı/veri/sürüm kararı gerekir.
6. **Gerçek kapanış:** gönderim/alındı/kabul kaydı varsa ilişkilendirilir. Dosyanın hazırlanmış olması gönderildiği anlamına gelmez. Memnuniyet ve ödeme isteği ölçülmediyse `not_validated`; canlı düzeltme/retest yapılmadıysa tamamlanmış sayılmaz.

Kaynak öğe ilişkileri [Phase14 teslim standardına](../DELIVERABLE_SPEC.tr.md) ve pinli [renderer DTO'suna](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting.rs#L18308-L18330) dayanır. İnsan kayıt alanları native JSON'a eklenmez. Severity `null` ise atanmamıştır; source confidence, ürün doğruluk yüzdesi değildir.

## Kaynak kaydı ile gerçek incelemeyi ayırma

[İnceleme politikası](OBSERVATION_REVIEW_POLICY.tr.md), bu kitin altı insan durumunu tanımlar. Phase14'ün `not_performed / needs_additional_evidence / reviewed` önerisi korunmuştur; Phase15'in farklı belge sözlüğüne otomatik eşlenmez. Önceki kaydın kanıtı okunmadan `reviewed` değerinden `reviewed_for_delivery` sonucu üretilmez. Bu kitin demosunda gerçek uzman incelemesi yoktur; dört kaynak gözlem `unreviewed` kalır.

`informational`, `needs_review`, `confirmed` kaynak sınıfları; insan `review_status`, `client_inclusion`, artefact completion ve gate status ile karıştırılmaz. Native mevcut assessment capability'leri `Confirmed` üretmez; bunu bir belge kaydı yükseltemez. [Kaynak sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L155-L163). `KnowledgeOnly` yeni sonuç sınıfı değil runtime yetki bağlamıdır; ek bir müşteri bulgusu oluşturmaz.

## Demo boyunca izlenecek ayrı kaynak kümeleri

[Vaka indeksi](examples/DEMO_CASE_INDEX.md) şu belge ilişkisini gösterir. Ortak `DEMO-TERMIVAR-015` klasör kimliği bu kaynakları aynı koşu haline getirmez:

| Küme | Artefact ref'leri | İzinli belge yorumu | Açık sınır |
| --- | --- | --- | --- |
| A — ana örnek | ART-A1 assessment, ART-A2 manifest | Dört mevcut informational observation, ledger ve karar kaydına bağlanır. | Gerçek uzman incelemesi yok; yalnız JSON-entry byte bağlaması. HTML yok, native tam bundle verify yapılmadı. |
| C — bağımsız comparison | ART-C1 comparison, ART-C2 before, ART-C3 after | Kaynakta bulunan dört grup ayrı örnek olarak açıklanır. | A'nın retest'i veya gerçek güvenlik değişimi değildir; only-in-before düzeltilmiş sayılmaz. |
| D — ayrı diagnostic | ART-D1 incomplete | Unavailable item projection'ın temiz sonuç olmadığını gösterir. | Mevcut elle yazılmış Phase11 fixture'ıdır, CLI çıktısı değildir; A'nın eksik devamı değildir. |

Kaynak kopyalar ve tam byte kimlikleri [korunmuş provenance](../examples/README.tr.md) kaydındadır. Manifest/hash, üretici özgünlüğünü, yetkiyi veya bulgu doğruluğunu kanıtlamaz; [native doğrulama sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419). [Karşılaştırma yorum sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L567-L573), kaybolan/değişen/eşit projection için güvenlik hükmü verilmesini engeller.

## Kitin bu fazdaki kapanışı

Şablonların gerekli alanları taşıması, demo satırların gerçek kaynak öğelerle bağlanması ve iç kayıt/handoff ayrımının okunabilmesi manuel belge incelemesidir. Yazılım testi, gerçek uzman güvenlik incelemesi, müşteri kullanılabilirlik kabulü veya pilot GO değildir. Gerçek teslim, müşteri kabulü, saklama ve bağımsız doğrulama kapıları açık bırakılır. Bu kit teslim edildikten sonra yeni assessment, satış veya faz başlatılmaz.
