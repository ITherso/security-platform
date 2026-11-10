# Termivar — paylaşılmamış demo müşteri handoff taslağı

**Demonstration only — No real system assessed.**

`case_id=DEMO-TERMIVAR-015`; `demo_only=true`. Bu kimlik dahili demo dosya kimliğidir, gerçek değerlendirme run kimliği değildir. **Belge müşteriye gönderilmedi; gerçek teslim, kabul veya GO kaydı yoktur.** Aşağıdaki açıklamalar mevcut sentetik belgelerin nasıl sınırlandırılacağını gösterir. Paylaşılması onaylanmış müşteri bulgusu bulunmaz; bu, bir gerçek sistemde bulgu bulunmadığı sonucu değildir.

## 1. Değerlendirme kimliği ve kapsamı

| Alan | Demo taslağı |
| --- | --- |
| Belge türü | İnsan tarafından yazılmış demo handoff; native Termivar renderer çıktısı değil |
| Müşteri / kurum / gerçek çalışma kimliği | `not_provided` |
| Yetki kaydı / onaylı hedef / izinli faaliyet | `not_provided` |
| Kapsam, hariçler ve çalışma penceresi | `not_provided`; gerçek bir değerlendirme yapılmadı |
| Kabul edilmiş istek / zaman bütçesi | `not_provided`; kaynak varsayılanları müşteri kabulü sayılmaz |

## 2. Yöntem ve değerlendirme sınırları

Önceden mevcut sentetik JSON kaynakları offline okunarak bu açıklama hazırlandı. CLI, scanner, test/build, canlı hedef, native bundle verifier veya yeni karşılaştırma çalıştırılmadı. Belge/byte eşleşmesi, uzman incelemesi veya bağımsız güvenlik doğrulaması değildir.

Kaynaklar üç ayrı kümedir: A, complete assessment ve kısmi manifest; C, ayrı sentetik karşılaştırma; D, elle yazılmış incomplete diagnostic. Aynı müşteri, koşu, zaman çizgisi veya retest altında birleştirilmez.

## 3. Tamamlanan ve tamamlanamayan çalışmalar

| Kaynak kümesi | Belgeden okunabilen bilgi | Sınır |
| --- | --- | --- |
| A | `web-review`, `venom-rendered-assessment/v1`, kaynak status `complete`, 1 subject / 4 informational item | Yeni veya gerçek müşteri çalışması yapılmadı. Complete bütün kapsamın incelendiğini veya güvenliği kanıtlamaz |
| C | `termivar-report-comparison/v1`, dört grubun her birinde 1 kaynak kayıt | Ayrı sentetik document-processing örneği; A değerlendirmesinin retest'i değil |
| D | `web-assessment/v2`, authored `incomplete`; item projection `unavailable` | Phase11'de elle hazırlanmış fixture; CLI/runtime çıktısı değil. Kullanılamayan item projection için sıfır bulgu yazılamaz |

A rendered dosyası gerçek hedef, çalışma başlangıç/bitişi, onaylı kapsam/bütçe veya bütün kullanım sayaçlarını sağlamıyor. Bunlar tahmin edilmedi. D'deki authored limit/kullanım değerleri ölçülmüş müşteri çalışması olarak aktarılmadı.

## 4. Uzman tarafından gözden geçirilmiş sonuçlar

Bu demo dosyasında **uzman tarafından gözden geçirilmiş veya müşteri paylaşımı için onaylanmış sonuç yoktur**. Dört kaynak kayıt `informational` / `observation` etiketlidir; doğrulanmış zafiyetlere dönüştürülmez. Kaynak severity alanları `null`dur; risk sıfır/low sonucu veya yeni puan verilmez. Kaynak confidence alanı doğruluk, istismar olasılığı veya CVSS olarak yorumlanmaz.

## 5. İnceleme bekleyen ve sonuçlandırılamayan alanlar

Dört kaynak gözlemin tamamı uzman incelemesi ve paylaşım kararı bekler. Gerçek kapsam ilişkisi, gerekli mevcut kanıt erişimi, uygulama bağlamı ve müşteriye dahil etme kararı henüz belirlenmemiştir. Bu nedenle tek tek gözlem başlığı, teknik öneri ve kanıt listesi müşteri bulgusu olarak bu taslağa alınmadı. Bu durum kayıtların gerekçeli biçimde hariç bırakıldığı kararı da değildir.

D incomplete örneği temiz sonuç veya tamamlanmış boş assessment değildir. Tamamlanmamış, erişilemeyen veya kaynakta bulunmayan kontrol kapsamı başarılı sayılmaz. Bu dosya bunları yeni yürütme veya incelemeyle tamamlamaz.

## 6. Kaynak ve kanıt referansları

Aşağıdaki referanslar yalnız mevcut örneklerin belge kimliğidir; bu handoff'a eklenmiş veya müşteriye aktarılmış ham kanıt değildir.

| Referans | Kaynak türü / tam dosya SHA256 |
| --- | --- |
| `ART-A1` — [assessment.json](../../examples/assessment.json) | `venom-rendered-assessment/v1`; `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `ART-A2` — [manifest.json](../../examples/manifest.json) | `termivar-report-bundle/v1`; `c77ce74508e8efaff7ebf1b0203331b4295d468c726e4acd7bad709eb85813df` |
| `ART-C1` — [comparison.json](../../examples/comparison.json) | `termivar-report-comparison/v1`; `291f5e7b407a247cb786119a249fe6f3cb9f5526e6700605c4a0008bee91a1d0` |
| `ART-D1` — [incomplete-diagnostic.json](../../examples/incomplete-diagnostic.json) | Elle yazılmış `web-assessment/v2` fixture; `85881c1d3883bb719cd05e7fbd63f564188371ddab58be94eb7e56c9e84d4f0a` |

A2'nin A1 için JSON uzunluğu, hash'i ve özet alanları eşleşir. Manifestin bildirdiği HTML sağlanmadığından **tam bundle doğrulaması yapılmış değildir**. Hash/manifest/parse üretici kimliği, kaynak özgünlüğü, gerçek scope yetkisi, bulgu veya düzeltme doğrulaması sayılmaz. Native producer alanındaki alpha.2 sürümü, incelenen güncel source sürümü veya yeni bir executable kabulüyle karıştırılmaz. Ayrıntılı kaynak geçmişi [Phase14 örnek provenance kaydındadır](../../examples/README.tr.md).

## 7. Teknik takip önerileri

İleride gerçek bir değerlendirme istenecekse önce kapsam/yetki, çalışma sınırları, kanıt/veri erişimi ve insan incelemesi için ayrı karar kaydı gerekir. Uygun uzman mevcut kanıtın yeterliliğini, uygulama bağlamını ve kaynak önerilerinin paylaşılabilirliğini gerekçeli biçimde değerlendirmelidir. Bu, şu anda canlı istek, ek tarama, hedef değişikliği veya yeniden doğrulama başlatma izni değildir. Düzeltme uygulanmış veya başarıyla doğrulanmış sayılmaz.

## 8. Önceki raporla karşılaştırma

C1'in before/after hash'leri ayrı `comparison-before.json` / `comparison-after.json` örneklerine bağlıdır; A1'e bağlı değildir. Kaynakta `only_in_after`, `only_in_before`, `changed`, `unchanged` gruplarında birer kayıt bulunur; changed öğesinde bildirilen alan `redacted_summary`'dir.

`only_in_before` düzeltilmiş/çözülmüş değildir; `only_in_after` bir durumun yeni ortaya çıktığını kanıtlamaz; `changed` otomatik risk artışı/azalışı değildir; `unchanged` eşit kapsam veya güvenlik değildir. `operator-declared` kapsam beyanı bağımsız kapsam doğrulaması değildir; coverage eşdeğerliği ve kaynak özgünlüğü kurulmuş değildir. Bu demo gerçek retest veya remediation sonucu sunmaz.

## 9. Veri ve yorumlama sınırlamaları

İç değerlendirme notları, uzman karar gerekçeleri, rol atamaları, native öğe fingerprint/evidence listeleri ve ham request/response/headers/payload bu handoff'a aktarılmadı. Credential, cookie/token ve hedef adresi eklenmedi. Bir kaynak bağlantısı bulunması o kanıtın paylaşıldığı veya ona erişim verildiği anlamına gelmez. Bu, müşteri taslağı ile **Internal Review Record** arasındaki somut ayrımdır.

Gerçek alıcı, veri minimizasyonu/redaksiyon onayı, erişim ve aktarım yöntemi, saklama süresi/yeri, silme/yedek ve karar sahipleri `pending_decision` / `not_provided` kalır. Bu belge gerçek erişim kontrolü, güvenli kasa, şifreleme veya silme sistemi oluşturmaz. Tam kapsam, tüm zafiyetler, güvenli/temiz sistem, uygunluk, SLA veya müşteri memnuniyeti iddiası yoktur.

## 10. Gerçek teslim ve kabul alanları

| Alan | Mevcut değer |
| --- | --- |
| Gerçek alıcı / paylaşım kararı referansı | `not_provided` / `not_provided` |
| Teslim tarihi / teslim kanıtı | `not_provided` / `not_provided` |
| Onay kaydı / onay zamanı | `not_provided` / `not_provided` |
| Gerçek müşteri kabulü / memnuniyeti | `not_validated` / `not_validated` |
| Düzeltme tamamlanması / yeniden değerlendirme | `not_verified` / `not_provided` |

Bu alanların boş olması teslim veya kabul gerçekleştiği anlamına gelmez. [Phase14 teslim standardı](../../DELIVERABLE_SPEC.tr.md), [pilot kapsamı](../../PILOT_SCOPE.tr.md) ve [açık pilot koşulları](../../PILOT_READINESS.tr.md) korunur. Bu paylaşılmamış demo taslağıyla gerçek değerlendirme, müşteri teması veya yeni bir faz başlatılmaz.
