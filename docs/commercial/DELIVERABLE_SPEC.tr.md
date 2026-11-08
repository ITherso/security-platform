# Termivar değerlendirme teslimatı standardı

Bu belge, **Termivar Web & API Security Assessment** için önerilen müşteri teslimatını tanımlar. Bir değerlendirme sonucu, otomatik rapor üretici veya tamamlanmış ücretli pilot değildir. İlk teslimat modeli, kapsamı önceden belirlenmiş çalışma ve ayrı uzman incelemesidir. Kaynak incelemesi, canlı çalışma güvenilirliğini veya müşteri kabulünü kanıtlamaz.

Örnek teslimat: [örnek rapor](examples/DEMONSTRATION_REPORT.tr.md), [artefakt kaydı](examples/README.tr.md). Her örnek rehber ve rapor şu etiketi taşır: **Demonstration only — No real system assessed.** Orijinal JSON'lara etiket veya yeni alan eklenmez; bu kayıt onların örnek niteliğini açıklar.

## 1. Teslimatın yapısı

| Bölüm | Zorunlu içerik | Eksik olduğunda yazılacak durum |
| --- | --- | --- |
| Belge kimliği | İnsan raporunun sürümü, hazırlanma zamanı, çalışma kaydı, hazırlayan ve inceleyen için ayrı alan | Atanmayan kişi veya zaman `not_recorded`; kaynakta olmayan run kimliği üretilmez |
| Yönetici özeti | Kapsam, çalışmanın tamamlanma durumu, inceleme durumu, karar bekleyen konular ve önemli sınırlar | Eksik çalışma açıkça belirtilir; boş liste temiz sonuç değildir |
| Değerlendirme kapsamı | Onaylı uygulama/API sınırı, origin/endpoint ve izin verilen eylemler, hariç tutulan alanlar, çalışma penceresi ve yetki kaydının referansı | Kaynak raporundan hedef veya yetkilendirme türetilmez; `not_established` |
| Yöntem ve sınırlar | Kullanılan kaynak/binary sürümü ve özellikleri, seçili profil ve ek işler, onaylı istek/zaman bütçeleri, gözlenen kullanım ve kesilme nedenleri | Bütçe ile kullanım ayrı; bulunmayan sayaç veya zaman sıfır yapılmaz |
| İncelemeye alınmış öğeler | Kaynak etiketleri, insan inceleme durumu, gözlem, kanıt bağlantıları, sınır ve takip adımı | Kaynak öğesi uzman tarafından doğrulanmış gibi sunulmaz |
| Kanıt dizini | Artefakt dosyası ve SHA256'sı, öğe fingerprint'i, rapor içi referanslar, sağlanan/redakte edilen/sağlanmayan kanıt | Opaque referans, ham kanıtın teslim edildiği anlamına gelmez |
| Bilinmeyen/eksik işler | Tamamlanmama, desteklenmeyen bölüm, atlanan kapsam, eksik veri ve etkisi | `unknown`, `unavailable` veya `not_evaluated`; başarıya çevrilmez |
| Teknik takip | Kaynak önerisi ile uzmanın önerisi ayrı; uygulama uyumluluğu, sorumlu ve ayrı yetkili yeniden değerlendirme gereği | Öneri, uygulanmış veya doğrulanmış düzeltme sayılmaz |
| Karşılaştırma | Seçilen iki artefaktın byte hash'leri, kapsam beyanı, dört kaynak grubu, kapsam eşitliğinin sınırları | İlgisiz örnekler bağlanmaz; girdi yoksa `not_available` |
| Emek ve kapanış | Hazırlık, yürütme, kanıt inceleme, raporlama, takip ve destek için ayrı gerçek süre kayıtları; teslim ve kabul durumu | Ölçülmeyen süre, maliyet ve müşteri kabulü `not_recorded` / `not_validated` |

Kişi, tarih, kapsam onayı ve yorum alanları insan raporuna aittir; native JSON şemasına eklenmez. Rapor sürümü, native `run_schema` ile karıştırılmaz. Bu standardın gerektirdiği bazı işletim kayıtları mevcut rendered JSON'da yoktur; pilotta ayrı ve kontrollü tutulmaları gerekir.

## 2. Durumlar ve iddia sınırı

Çalışmanın tamamlanması, kaynak öğesinin disposition'ı, insan incelemesi, dosya bütünlüğü ve yeniden değerlendirme sonucu ayrı eksenlerdir. Tek bir “başarılı/güvenli” göstergesi altında birleştirilmez.

| Kaynak alanı veya durum | Raporda korunacak anlam |
| --- | --- |
| `informational` / `observation` | Sınırlı gözlem; zafiyet iddiası değildir |
| `needs_review` / `differential` | Yetkili insan incelemesi gerektiren aday/ilişki; doğrulanmış zafiyet değildir |
| `confirmed` / `verifier_transition` | Native sözleşmede ayrı verifier bağlantısı gerektiren kaynak iddiası; içe aktarma veya uzman raporu yazımı bu yetkiyi üretmez |
| `KnowledgeOnly` | Runtime'da hipotez geçişi uygulamayan doğrulama hedefi; JSON'a yeni disposition veya sayaç olarak eklenmez, yalnız mevcut kaynak kaydı destekliyorsa açıklanır |
| `severity: null` | Atanmamış; low, sıfır risk veya risksiz olarak çevrilmez |
| `confidence_ppm` | Kaynağın güven alanı; CVSS, iş etkisi, istismar olasılığı veya ürün doğruluk yüzdesi değildir |
| `status: complete` | İlgili typed değerlendirme tamamlanma durumu; kapsamlı test, kaynak doğruluğu veya uygulama güvenliği belgesi değildir |

Bu ayrımın kaynakları: [disposition sözleşmesi](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/assessment_item.rs#L104-L126), [KnowledgeOnly runtime bağlaması](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/decision_loop/policy.rs#L685-L701) ve [renderer sınırları](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L150-L163). İncelenen kaynak, mevcut native pasif header/cookie yeteneklerinin yalnız `Informational` ürettiğini ve mevcut native assessment capability'lerinin `Confirmed` üretmediğini açıklar. İthal bir etiket, yeni çalıştırma veya doğrulama kanıtı değildir.

İnsan incelemesinin önerilen ayrı alanları: `review_status` (`not_performed`, `needs_additional_evidence`, `reviewed`), inceleyen, tarih, incelenen kanıtlar, gerekçe ve kalan belirsizlik. Bunlar **önerilen belge alanlarıdır**, Termivar'ın mevcut wire enumları değildir. `reviewed`, tek başına istismar, etkin düzeltme veya güvenli uygulama anlamına gelmez. Müşterinin işlem önceliği gerekçesi ayrıca yazılır; source severity veya disposition sessizce değiştirilmez.

## 3. Her öğe için kayıt

Öğe kaydı aşağıdaki alanları birlikte taşır:

1. Yerel insan raporu sıra numarası ve kaynak dosya/hash referansı.
2. Kaynaktaki `capability_id`, `fingerprint`, opaque `subject_reference`, başlık ve redakte özet. Subject referansı hedef adresi veya etkilenenlik kanıtı değildir.
3. Kaynak `disposition`, `claim_basis`, `severity`, `confidence_ppm`, varsa `category` ve `cwe`. Kaynak serbest metinleri paylaşım öncesi hassas veri açısından gözden geçirilir.
4. `evidence_references`, `control_evidence_references`, `candidate_evidence_references` ve `evidence_count`; varsa case/outcome/verification stage bağlantısı. Kontrol ve aday bağlantıları kaybolmaz.
5. İnsan incelemesi durumu, hangi kanıta erişildiği, neyin değerlendirilemediği ve ayrı takip ihtiyacı.
6. Kaynağın `remediation.id/summary` önerisi ve varsa ayrıca yazılmış uzman önerisi. İkisi de düzeltmenin uygulandığını kanıtlamaz.

Native öğe alanları [renderer DTO'sunda](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting.rs#L18308-L18330) tanımlıdır. Desteklenen importer; observation, differential ve verifier-transition ilişkilerini [ayrı denetler](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs#L444-L485). Kanıt referanslarının benzersizliği, ortak 256 referans üst sınırı, toplamla ilişkisi ve verifier stage denetimi [aynı kaynaktadır](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs#L611-L650).

Her öğenin evidence_count değeri toplanıp bağımsız kanıt sayısı ilan edilmez; öğeler aynı opaque referansları paylaşabilir. Ham request/response, tam URL/query, credential veya kişisel veri, rendered JSON'da varmış gibi anlatılmaz. Paylaşılması gereken ek kanıt için asgari veri, redaksiyon, erişim ve saklama kararı ayrıca alınır. Kaynak referansı tek başına o kanıta erişim veya yeniden test yetkisi vermez.

## 4. Tamamlanma ve kapsam eksikleri

Tamamlanmamış veya runtime başladıktan sonra failed olan `web-review`, tamamlanmış raporun boş hali değildir. Kaynak ayrı `web-assessment/v2` diagnostic zarfı üretir, assessment items unavailable olur ve istenen rapor artefaktı yaratılmaz. [Tamamlanma sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L599-L603).

Teslimat, diagnostic varsa disposition'ı, tamamlanmama nedenlerini, projection durumunu ve mevcut bütçe/kullanım kayıtlarını açıkça aktarır. Tanımlanmamış item listesi için “0 bulgu” yazılmaz. Yeni kapsam veya yeniden yürütme gereği açıklanır; çalıştırma ayrıca yetkilendirilmeden başlatılmaz. Rendered assessment'ta hedef, başlama/bitiş zamanı veya tüm kullanım sayaçları yoksa bunlar ayrı çalışma kaydından sağlanır; yokluğu gizlenmez.

## 5. Dosyalar ve bütünlük

Önerilen teslimat: insan tarafından hazırlanan Markdown rapor, izin verilen ve redakte edilmiş native JSON artefaktları, dosya/hash dizini ve varsa ayrı kapsam/çalışma kaydı. Bu tur yeni PDF üretimi veya HTML çalıştırılması yapılmaz. Native renderer'ın JSON/CSV/HTML/Markdown biçimleri bulunması, bu hazırlık turunda bunların üretildiği anlamına gelmez; [biçim ve limit kaynağı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L605-L625).

Native bundle tam olarak `assessment.html`, `assessment.json`, `manifest.json` içerir. Manifest en fazla 64 KiB; her rapor payload'ı en fazla 16 MiB'dır. Verifier, pozitif payload uzunluğu, lowercase SHA256, sabit ad/format/media type, SemVer producer version (en fazla 128 byte), 1–1024 subject ve en fazla 4096 item sınırlarını denetler. [Manifest denetimi](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/report_verify.rs#L313-L355), [tam bundle denetiminin kapsamı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L359-L408).

Yalnız JSON ve manifest sağlanmışsa teslimat **kısmi JSON-entry eşleşmesi** olarak kaydedilir; tam bundle veya `report verify` başarısı denmez. Tam bundle için de hash eşleşmesi imza, producer kimliği, tarama yetkisi, bulgu doğruluğu, HTML/JSON anlamsal eşitliği veya düzeltme doğrulaması değildir. [Bütünlük sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419).

## 6. Önceki değerlendirmeyle karşılaştırma

Karşılaştırma ayrı bir artefakttır. Kaynak iki açıkça seçilmiş, desteklenen complete assessment JSON'u okur; `--same-scope` operatörün kapsam beyanıdır. Byte hash'leri seçilen dosyaları tanımlar, kaynak kimliğini veya kapsam eşitliğini kanıtlamaz. [Girdi sınırı ve kapsam beyanı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L437-L487).

| Kaynak grubu | Teslimatta kullanılacak ifade | Çıkarılmayacak sonuç |
| --- | --- | --- |
| `only_in_after` | Yalnız seçilen sonraki belgede | Yeni ortaya çıkmış zafiyet |
| `only_in_before` | Yalnız seçilen önceki belgede | Düzeltilmiş veya güvenli |
| `changed` | Eşleşen kimliğin desteklenen projection alanları farklı | Güvenlik durumunun iyileşmesi/kötüleşmesi |
| `unchanged` | Karşılaştırılan projection alanları eşit | Eşit kapsama veya güvenliğe sahip iki değerlendirme |

Kaynak etiketleri ve öneriler bağımsız onaylanmadan taşınır; yeni CVSS, hedef kimliği veya kanıt üretilmez. [Yorum sınırları](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L560-L597). Başka bir örneğin before/after digestleri ana raporun digest'iyle uyuşmuyorsa bu raporun retest'i olarak bağlanmaz. Gerçek yeniden değerlendirme için ayrı kapsam, yetki, yöntem farkları ve çalışma kaydı gerekir.

## 7. Efor kaydı ve teslimat kontrolü

İşletim kaydı; kapsam hazırlığı, veri/credential hazırlığı, yürütme, durdurma/yeniden başlatma, kanıt incelemesi, rapor yazımı, müşteri açıklaması, yeniden değerlendirme ve destek sürelerini ayrı ölçer. İstek ve byte sayaçları insan çalışma saati değildir. Eksik kayıt için tahmini yüzde tasarruf, doğruluk, fiyat veya yatırım getirisi üretilmez.

Teslimat incelemesinde şu sorular cevaplanır: Kapsam ve hariçler açık mı? Her yorumun kaynak/kanıt referansı var mı? Kaynak iddiası ile insan incelemesi ayrılıyor mu? Eksik işler temiz sonuca dönüşmüş mü? Teknik ekip takip adımını ve yetki sınırını anlayabiliyor mu? Karşılaştırma gerçekten doğru iki dosyaya mı bağlı? Ölçülmüş emek ve destek gereği kayıtlı mı? Müşteri memnuniyeti ve ödeme isteği için veri yoksa `not_validated` yazılmış mı?

Bu standarda uygun örnek hazırlanması; ücretli pilot kabulü, canlı değerlendirme, production, gerçek Windows/IdP/revision kabulü veya müşteri onayı yerine geçmez. Açık pilot kapıları [PILOT_READINESS.tr.md](PILOT_READINESS.tr.md) ve yetki/kapsam kararları [PILOT_SCOPE.tr.md](PILOT_SCOPE.tr.md) içinde ele alınır.
