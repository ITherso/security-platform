# Örnek müşteri teslimatı — belge yorumlama gösterimi

**Demonstration only — No real system assessed.**

Bu, önceden var olan benign/sentetik artefaktların insan tarafından hazırlanmış açıklamasıdır. Bu tur hiçbir gerçek sistem değerlendirilmedi; Termivar/CLI/scanner, sunucu, test veya rapor motoru çalıştırılmadı. Uzman güvenlik incelemesi, müşteri kabulü veya düzeltme doğrulaması yapılmış değildir. Şema ve byte kimliği [artefakt kaydında](README.tr.md) ayrı verilir; JSON'lar değiştirilmemiştir.

## Yönetici özeti

Ana kaynak [assessment.json](assessment.json), tek subject ve dört `informational` / `observation` öğesi bildiren complete v1 artefakttır. Dördü de header/policy gözlemidir. Bunlar dört doğrulanmış zafiyet değildir. Kaynakta `needs_review` ve `confirmed` öğesi yoktur; bu durum uygulamanın güvenli olduğunu veya başka sorun bulunmadığını göstermez.

Bu teslimatta gerçek hedef, müşteri, onay kaydı, çalışma penceresi, ticari kapsam veya inceleyen uzman bulunmaz. Ana JSON, rapor içi opaque subject/evidence referansları içerir; ham HTTP kanıtları içermez. Kaynaktaki dört öneri uygulama bağlamı ve uyumluluk incelenmeden doğrudan değişiklik talimatına çevrilmemiştir.

| Ayrı durum | Bu örnekteki değer |
| --- | --- |
| Native ana artefakt | `venom-rendered-assessment/v1`, `status: complete`, `profile: web-review` |
| Kaynak öğeleri | 4 informational, 0 needs_review, 0 confirmed |
| Severity | 4 öğede `null` / atanmamış |
| İnsan güvenlik incelemesi | `not_performed` |
| Gerçek müşteri yetki/kapsam kaydı | `not_available` |
| Tam bundle verification | `not_performed`; HTML teslim edilmemiştir |
| Üretici kaynağına kimlik doğrulama | `not_established` |
| Düzeltme veya retest doğrulaması | `not_performed` |
| Müşteri kabulü / memnuniyet / ödeme isteği | `not_validated` |

## Kapsam ve yöntem

Bu belgenin kapsamı, mevcut dosyaların anlamını açıklamaktır. Ana artefaktın native geçmiş kaydı, repository-owned sayısal loopback fixture üzerinde eski bir development çalışması bildirir; bu tarihsel kaydı bu tur yeniden üretmedik. Public hedef veya müşteri sistemi değerlendirmesi değildir. Tam tarihsel kaynak [README L1–26](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-bundle/README.md#L1-L26) içindedir.

Native kaynak checkout'u `6a2639348c2366d0bf71b9a34e5484d40aa393a3` idi. Ana artefakt ve manifest bu checkout'taki mevcut örnekle birebir aynıdır. Manifest `producer.version: 0.10.0-alpha.2` bildirir; bu, yeni binary çalıştırıldığı veya üretici kimliğinin doğrulandığı anlamına gelmez. İnsan raporu sürümü bu gösterim için 1'dir; kaynak run kimliği veya gerçek inceleyen kişi uydurulmamıştır.

## İncelemeye alınacak öğeler

Aşağıdaki Türkçe ifadeler kaynak gözlemlerin açıklamasıdır; gerçek sistem üzerinde yapılmış uzman değerlendirmesi değildir. Bu insan raporunda her satırın inceleme durumu `review_status: not_performed` olarak kaydedilir; bu alan native JSON'da bulunmaz. Kaynağın her öğesinde `subject_reference: subject-0000`, `severity: null`, `claim_basis: observation` bulunur. Her öğenin case/outcome/verification_stage alanı `null`; kontrol ve aday evidence listeleri boştur. Kaynak `confidence_ppm: 1000000` bildirir; bu sayı ürün doğruluk oranı veya istismar olasılığı olarak kullanılmaz.

| No | Kaynak capability ve gözlem | Kaynağın önerisinin özeti | Takip sınırı |
| --- | --- | --- | --- |
| 01 | `web.passive.referrer-policy.missing@1` — uygun HTML yanıtında Referrer-Policy gözlenmemiş | Uygulamanın cross-origin bilgi paylaşma gereksinimine uygun Referrer-Policy belirlenmesi | Hedef/yanıt burada yok; gerekli paylaşım davranışı, tüm yanıtlar ve etkisi incelenmedi |
| 02 | `web.passive.x-content-type-options.missing@1` — uygun document yanıtında X-Content-Type-Options gözlenmemiş | Sunulan içerikle uyumlu yerlerde `nosniff` kullanılması | MIME davranışı ve uygulama uyumluluğu değerlendirilmedi |
| 03 | `web.passive.permissions-policy.missing@1` — uygun HTML yanıtında Permissions-Policy gözlenmemiş | Gereken tarayıcı özellikleri incelenerek politika belirlenmesi | Gerçek özellik ihtiyacı ve kullanıcı akışları değerlendirilmedi |
| 04 | `web.passive.csp.missing@1` — uygun HTML yanıtında Content-Security-Policy gözlenmemiş | Uygulama document'i için CSP tanımlanması ve doğrulanması | Uygulamanın kaynakları, inline davranışı ve CSP uyumluluğu değerlendirilmedi; XSS doğrulandığı anlamına gelmez |

Kaynak önerileri `assessment.json` içindeki `remediation` alanlarıdır. Bu gösterimde yeni risk puanı, müşteri önceliği, zafiyet başlığı, etki veya uygulandığı iddia edilen düzeltme eklenmemiştir. Gerçek pilotta uzman; kanıt erişimini, uygulama bağlamını, etki belirsizliğini ve önerinin güvenli uygulanmasını ayrıca kaydeder. Aktif doğrulama için ayrı kapsam/eylem yetkisi gerekir.

## Kanıt ve referans dizini

Ana dosya 3907 byte; SHA256 `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9`.

| No | Fingerprint (`sha256:` öneki ile) | Kaynaktaki direct evidence referansları |
| --- | --- | --- |
| 01 | `32adc97266dff2c8c11116f202bc894adcab02b7a9f1c315f988f1878bd10004` | evidence-0000, evidence-0001, evidence-0002, evidence-0005, evidence-0006, evidence-0007 |
| 02 | `423a41c26f6479fa1d15e672819aea23926e3dee76902559fe92cbc564ddf53a` | evidence-0001, evidence-0002, evidence-0003, evidence-0005, evidence-0006, evidence-0007 |
| 03 | `e0e9548ae2581d2522aac9b1cdce9ade61e4010d02308c716f252a15cbb7addb` | evidence-0001, evidence-0002, evidence-0005, evidence-0006, evidence-0007, evidence-0008 |
| 04 | `fa8c2374a132316b67a492e8ab213f26b389c9fecefcdf39685026c75fde46f2` | evidence-0001, evidence-0002, evidence-0004, evidence-0005, evidence-0006, evidence-0007 |

Her öğe `evidence_count: 6` bildirir. Listelerde toplam 24 bağlantı ve ortak 9 farklı opaque evidence referansı vardır; bunlar 24 bağımsız kanıt veya teslim edilmiş 9 ham kayıt değildir. Ham request/response içeriği, zamanı ve hedef konumu bu pakette yoktur. Referanslar çözülüp teknik kanıt incelenmedi.

## Manifest ve eksik dosya

[manifest.json](manifest.json), ana JSON için aynı 3907 byte ve aynı SHA256 ile 1 subject / 4 item özeti bildirir. Bu tur statik byte ölçümü ve alan okuması bu bağlamayı kontrol etmek için kullanıldı; native `report verify` çalıştırılmadı.

Manifest ayrıca `assessment.html` için 8000 byte ve `a43070ee91860782a1eb47cd081b5fe628423a847bcc172e1a039cb6055cf1c1` bildirir. **HTML bu örnek teslimata dahil değildir; okunmadı, çalıştırılmadı, render edilmedi veya doğrulanmadı.** Bu nedenle burada tam bundle, `integrity_match` sonucu veya HTML/JSON anlamsal eşitliği iddiası yoktur. Hash bağlaması imza, özgün üretici, yetkili tarama veya doğru güvenlik sonucu kanıtı değildir.

## Bilinmeyen ve tamamlanmamış alanlar

Ana rendered JSON; gerçek hedef/scope onayını, başlangıç/bitiş zamanını, principal bağlamını, bütün yöntem ve bütçe kullanımını, ham kanıtları veya insan incelemesini taşımaz. Bu alanlar bu gösterimde `not_available` kalır. Kaynak `status: complete` bunların var olduğu anlamına gelmez; sıfır öğeli complete bir belge de temiz sonuç sayılmaz.

Ayrı [incomplete-diagnostic.json](incomplete-diagnostic.json), Phase11'de elle yazılmış sentetik `web-assessment/v2` örneğinin değiştirilmemiş kopyasıdır; çalıştırılmış CLI veya scanner çıktısı değildir. `disposition: incomplete`, nedenler `subject_execution_incomplete` / `wall_time_limit`, `projection_status: unavailable` ve `incomplete_assessment_items_withheld` bildirir. Bir pending subject, sıfır executed subject ve sıfır request içerir. Bunlar örnek alan değerleridir, bu tur ölçülmüş kullanım değildir. Burada **bulgu sayısı verilmez**; unavailable öğeler “0 bulgu” yapılmaz. Ana complete raporun devamı veya aynı çalışmanın kaydı olarak ilişkilendirilmez.

## Ayrı karşılaştırma gösterimi

[comparison.json](comparison.json), önceden üretilmiş bağımsız native belge işleme örneğidir. Yanındaki [comparison-before.json](comparison-before.json) ve [comparison-after.json](comparison-after.json) aynı örneğin orijinal sentetik girdilerinin kopyalarıdır. Bu tur karşılaştırıcı çalıştırılmadı.

| Kaynak grup | Sayı | Örneğin anlamı |
| --- | ---: | --- |
| `only_in_after` | 1 | Sentetik kimlik yalnız after belgesinde |
| `only_in_before` | 1 | Farklı sentetik kimlik yalnız before belgesinde |
| `changed` | 1 | Paylaşılan kimliğin yalnız `redacted_summary` alanı kasıtlı değiştirilmiş |
| `unchanged` | 1 | Paylaşılan kimliğin karşılaştırılan projection alanları eşit |

Before SHA256 `33f709237ffea142d892891d818815251c1cb35d888abe155f7175e15d7d481f`; after SHA256 `5ea44cfd6dbab132aa96e62813c32c12e35f0bf32c09b43a102a16e9ff7bbe64`. İkisi de ana assessment SHA256'sından farklıdır. **Bu karşılaştırma ana raporun yeniden değerlendirmesi değildir.** Her iki kaynak özeti 1 subject / 3 item bildirir; dört grup dört ayrı karşılaştırma kaydıdır, iki raporun toplam bulgu sayısı değildir.

Kaynak `scope_assurance: operator-declared`, `coverage_equivalence: not-established`, `source_authenticity: not-established-by-parsing` bildirir. Önceden görülen bir öğenin yokluğu düzeltmeyi; sonradan görünmesi yeni oluşumu; unchanged grubu güvenliği veya eşit kapsamı kanıtlamaz. Kaynakta değişmiş özet güvenlik değişikliği değildir. Dört grup, müşteri uygulamasına ait trend veya başarı metriği olarak kullanılmaz.

## Teknik takip ve efor kaydı

Gerçek pilotta önce ayrı yetki/kapsam kaydı, uygulama akışları ve paylaşılabilir kanıt erişimi belirlenir. Sonra uygun uzman, kaynak gözlemlerinin bağlamını ve uyumlu header/policy seçeneklerini inceler. Yapılan değişiklikler ve yeniden değerlendirme, ayrı yetkili çalışma olarak kaydedilir. Bu belge bu faaliyetleri başlatmaz.

| Efor alanı | Bu örnekte kayıt |
| --- | --- |
| Hazırlık ve kapsam belirleme | Gerçek pilot yapılmadı; süre `not_recorded` |
| Canlı yürütme ve kaynak kullanımı | Bu tur yapılmadı; tarihsel fixture kullanımı yeni ölçüm değildir |
| Uzman kanıt incelemesi | `not_performed`; süre `not_recorded` |
| Belge açıklaması / raporlama | İnsan tarafından hazırlanmış gösterim; süre `not_recorded` |
| Düzeltme, yeniden değerlendirme ve destek | `not_performed`; süre `not_recorded` |
| Müşteri kabulü ve ödeme isteği | `not_validated` |

Ölçülmemiş saat, maliyet, doğruluk, süre tasarrufu veya ödeme isteği tahmin edilmedi. Bu gösterim anlaşılır bir teslimat formatını somutlaştırır; ücretli pilot, müşteri uzman incelemesi, production güvenilirliği veya güvenlik etkinliği kabulü değildir.
