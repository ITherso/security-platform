# Termivar Web & API Security Assessment — ilk ürün teklifi

Durum: **ticari hazırlık taslağı; ücretli pilot onayı veya satın alınabilir SaaS taahhüdü değil.** Talep, müşteri memnuniyeti ve ödeme isteği `not_validated`. Bu fazda satış, müşteri görüşmesi, hedef değerlendirmesi veya teknik kabul yapılmadı.

## Ürün ve çözülen problem

Termivar Web & API Security Assessment, açıkça yetkilendirilmiş bir web/API kapsamını Termivar Web'in desteklenen yollarıyla değerlendirme, ortaya çıkan kayıtları uzman tarafından inceleme ve kapsam/belirsizlikleri koruyan anlaşılır bir raporla teslim etme **hizmet modeli adayıdır**. Müşterinin işi; hangi kaydın gözlem, hangisinin inceleme adayı olduğunu anlamak, eksik çalışmayı görmek ve sonraki değerlendirmeyle değişimi takip edebilmektir.

Mevcut teknoloji; kapsamı ve kaynak tüketimi sınırlı CLI değerlendirmesi, tipli assessment/evidence modeli, rapor üretimi ve hazır raporların çevrimdışı karşılaştırılmasıdır. İnsan incelemesi, teslim toplantısı ve takip planı bu belgede tanımlanan işletim sürecidir; otomatik çalışan yeni ürün özellikleri veya hâlihazırda verilmiş hizmet değildir. Kaynak **experimental / not production-ready** olarak tanımlanır ve bağımsız güvenlik denetimi tamamlanmış değildir. Kaynaktaki işlev, üretim güvenilirliği kanıtı olarak sunulmaz. [Kaynak README, 12–20 ve 70–80](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/README.md#L12-L80), [iddia envanteri](CAPABILITY_CLAIMS.tr.md).

## İlk müşteri: küçük siber güvenlik danışmanlık şirketleri

Bu seçim **ürün/kapsam uyumu hipotezidir**, doğrulanmış pazar talebi değildir. Yeni pazar araştırması veya müşteri görüşmesi yapılmadı.

| Aday | Sorun hipotezi | Mevcut teknolojiyle uyum | Açık belirsizlik |
|---|---|---|---|
| **A — küçük siber güvenlik danışmanlık şirketleri; birincil** | Tekrarlanan işlerde kapsam, kanıt, uzman incelemesi ve rapor değişim takibini düzenlemek. | Uzmanın zaten sürecin sahibi olduğu bir model, `NeedsReview` ve eksik kapsamın yorumlanmasına daha uygundur. CLI ve dosya tabanlı teslim, otonom SaaS gerektirmeden sınırlı pilotla değerlendirilebilir. | Mevcut araçlarına ek değer, eğitim/entegrasyon yükü, rapor kullanışlılığı, kapasite ve ödeme isteği `not_validated`. |
| B — küçük yazılım/SaaS ekipleri; ikincil | Kendi web/API projelerindeki gözlemleri anlamak ve tekrar değerlendirmede değişimleri izlemek. | Teknik ekip raporu kullanabilir; ancak yanlış yorumları önlemek için dış uzman incelemesi ve açıklama ihtiyacı varsayılır. | Self-service kullanım, destek ihtiyacı, değerlendirme yetkisi, satın alma isteği ve gerçek kullanım sıklığı `not_validated`. |

A profili, ürünün bugünkü inceleme ağırlıklı sınırıyla daha yakın olduğu için seçildi. Bu; A'nın daha büyük pazar, daha kârlı veya daha çok ödeme yapacağı iddiası değildir. İlk uygun pilotun amacı bu hipotezi ölçmek olur; burada pilot başlatılmaz.

## Dahil edilmesi tasarlanan işler

1. Hedef sahibinin yetkisi, tam hedef listesi, hariçler, değerlendirme penceresi ve durdurma sorumluları üzerinden yazılı kapsam hazırlığı.
2. Seçilmiş ve kimliği kayıtlı Termivar Web build'iyle desteklenen değerlendirme yolunun, onaylı sınırlar içinde operatör tarafından çalıştırılması. **Bu teslimatta çalıştırılmadı.**
3. Üretilen assessment'ın tamamlanma/eksiklik durumu, evidence referansları ve kayıt sınıflarının uzman tarafından incelenmesi. `NeedsReview` doğrudan zafiyet ilan edilmez; `KnowledgeOnly` bir yetki sınırıdır. İnsan değerlendirmesi kaynak kaydı değiştirmeyen ayrı not olarak tutulur.
4. Yönetici özeti, yöntem/kapsam, incelenen kayıtlar, sınırlamalar, takip maddeleri ve ham kaynakla ilişkisi açık bir teslim raporu.
5. Önceki ve sonraki kaynaklar gerçekten uygunsa, operatörün kapsam beyanı ayrıca kayıtlı çevrimdışı rapor karşılaştırması. Kaybolan kayıt düzeltilmiş sayılmaz.
6. Açıklama/düzeltme takibi için sınırları belirlenmiş bir görüşme veya soru listesi; aktif yeniden doğrulama ve yeni değerlendirme ayrıca kapsamlandırılır.

Ürün çıktısının standardı [DELIVERABLE_SPEC](DELIVERABLE_SPEC.tr.md), saha yetkisi ve sınırları [PILOT_SCOPE](PILOT_SCOPE.tr.md) içindedir. Bu adımların tanımlanmış olması, uzman kadrosu veya hizmet kapasitesinin hazır olduğu anlamına gelmez.

## Teknik kapsamın sınırı

| Alan | İlk teklifin yaklaşımı |
|---|---|
| Temel web değerlendirmesi | Açık `web-review`, exact-origin kapsam ve mevcut pasif/düşük riskli inceleme yolları esas alınır. Sınırsız crawler, tam uygulama kapsamı veya bütün zafiyet sınıflarını tarama sözü verilmez. |
| Web/API inceleme uzantıları | OpenAPI, REST, GraphQL ve authorization gibi kaynakta mevcut yollar **aynı şey değildir**. Her biri için seçilen binary'de derlenmiş özellik, runtime opt-in, girdi ve ayrı kapsam kabulü gerekir. İlk pilot kayıt formunda açıkça seçilmeyen uzantı dahil değildir. Genel bir “her API'yi test eder” iddiası yoktur. |
| Kimlik doğrulamalı veya ileri inceleme | Supplied-session, OAuth/OIDC, OAST ve diğer geliştirme uzantıları ilk temel teklife otomatik girmez. Derleme, sürüm, yetki ve işletim sınırları [envanterde](CAPABILITY_CLAIMS.tr.md) ayrı gösterilir. |
| Bütçe | `web-review` kaynak varsayılanları 256 paylaşılan broker isteği / 300 saniye / 16 MiB toplam yanıt gibi teknik üst sınırlardır. Bunlar fiyat, teslim süresi, başarı veya kapsama sözü değildir; bazı opt-in child yollarının ek muhasebesi ayrıca dikkate alınır. CLI'da keyfî profil/bütçe override'ı varmış gibi sunulmaz. Ayrıntı [PILOT_SCOPE](PILOT_SCOPE.tr.md). |
| Kayıtların anlamı | Temel native web-review `Confirmed` üretemez. Modelde bir `Confirmed` etiketi bulunabilmesi bu teklifin zafiyet doğruladığı anlamına gelmez. `Success`, işlem hedefinin başarısıdır; zafiyet kararı değildir. |
| Rapor dili | Native HTML/Markdown sunum dili ve platformun TR/EN arayüzü ayrıdır. Türkçe müşteri anlatımı uzman tarafından hazırlanan ayrı metindir; native rapor motorunda TR yerelleştirme özelliği olduğu iddia edilmez. |

Teknik kapsamın tamamı pinli kaynaklar ve gerekli doğrulama kapılarıyla [CAPABILITY_CLAIMS](CAPABILITY_CLAIMS.tr.md) içinde sınıflandırılır. Kaynak hattı `6a2639348c2366d0bf71b9a34e5484d40aa393a3` / `0.10.0-alpha.3`; tarihsel alpha.2 çıktıları ve seçilecek executable bu kimlikle karıştırılmaz.

## Dahil olmayan işler

- Otonom, çok kiracılı, üretime hazır SaaS; müşteri portalı, hesap açma, ödeme, faturalama veya otomatik zamanlama.
- Eksiksiz pentest, istismar/etki kanıtı, sosyal mühendislik, hizmet engelleme, sınırsız brute force, malware veya kapsam dışı hedefler.
- Otomatik düzeltme, canlı sistemi değiştirme, firewall/policy uygulama veya uzaktan cihaz yönetimi.
- Kaynakta bulunmayan API protokolü/yöntemi, interaktif browser/OIDC/MFA iş akışları veya kapsam kabulü yapılmamış kimlik doğrulamalı inceleme.
- Sertifika, mevzuat uygunluk kararı, “güvenli/temiz” sonucu, bulgu sayısı, doğruluk veya süre/maliyet tasarrufu garantisi.
- 7/24 operasyon, müdahale veya üzerinde anlaşılmamış destek/yanıt süresi taahhüdü.

## Müşteriden ve hizmet sahibinden gereken girdiler

| Girdi | Pilot öncesi beklenen kayıt |
|---|---|
| Yetki ve varlık sahipliği | Yetkilendiren taraf ve yetkisinin temeli, tam origin/resource/API tanımı, üçüncü taraf/CDN/IdP sınırları, hariç tutulan yollar/işlemler. |
| İşletim bağlamı | Sorumlu teknik irtibat ve durdurma kanalı, zaman penceresi, izleme ve hassas iş akışları; GET'in dahi etkisiz olduğu varsayılmaz. |
| Teknik hedef bilgisi | Uygulama/API sayısı, hedef ortam, varsa kabul edilmiş OpenAPI/context girdilerinin sürümü; hangi build/feature yolunun kullanılacağı. Sır içerikleri teklif belgesine veya manifest'e yazılmaz. |
| Önceki değerlendirme | Karşılaştırma istenirse desteklenen tamamlanmış kaynaklar, gerçek kapsam farkları ve operatör seçimi; yalnız dosya hash'i kapsam eşitliğini kanıtlamaz. |
| Veri işleme | Kimler erişecek, nerede tutulacak/aktarılacak, ne kadar süre saklanacak, silme/yedek ve olay sorumluları. Henüz onaylanmış saklama günü veya aktarım kanalı yok. |
| Uzman ve kabul sahibi | İncelemeyi yapacak uzman, rapor kalite kontrolü ve kapanış/kabul rolü; atanmış oldukları varsayılmaz. |

Güvenilir build/özellik kabulü, uzman incelemesi kapasitesi, yetki, veri işleme ve kurumsal kararlar kapanmadan gerçek pilot için “hazır” sonucu verilmez. [Açık kapılar](PILOT_READINESS.tr.md). Önceden bekletilmiş HBF Windows, IdP ve gerçek revision otoritesi kararları bu belgeyle yeniden istenmez.

## Teslim edilecekler

- Kapsam/yöntem ve tamamlanma kaydıyla birlikte kaynak JSON; uygun ve gerçekten üretilmişse native rapor/bundle dosyaları ve manifest.
- Kaynağa dayanan, insan inceleme durumunu ayrı gösteren yönetici/teknik rapor; eksik alanlar ve kanıt erişim sınırları açık.
- Her takip konusu için kaynak referansı, gerekli uzman kararı, yapılacak iş, sorumlu rol ve kapanış kanıtı alanı. Gerçek düzeltme veya yeniden doğrulama yapılmadıysa durum açık kalır.
- Uygun tamamlanmış önce/sonra kaynakları varsa ayrı karşılaştırma ve yorum sınırı; yoksa neden üretilmediği.
- Uzman emeği, destek soruları ve yeniden işleme sürelerini kaydetmek için manuel ölçüm kaydı. Bu fazda gerçek müşteri ölçümü yoktur.

Mevcut artefact'lardan hazırlanmış [sentetik teslimat](examples/README.tr.md) yalnız formatı ve yorum sınırlarını gösterir: **Demonstration only — No real system assessed.** Gerçek bulgu, müşteri kabulü veya tam bundle doğrulaması örneği değildir.

## Üç teklif seviyesi ve maliyet değişkenleri

| Seviye | Kapsam taslağı | Bugünkü durum |
|---|---|---|
| **Assessment** | Tek, açıkça sınırlandırılmış kapsam; desteklenen değerlendirme, uzman incelemesi, rapor ve tanımlı takip. | İlk pilot için aday hizmet modeli; henüz pilot/satış onayı yok. |
| **Continuous Review** | Ayrı kabul edilen dönemlerde tekrar assessment, uzman incelemesi ve uygun raporların değişim takibi. | Manuel planlama ve her çalışmada yeniden kapsam/yetki değerlendirmesi. Mevcut üründe bu teklife ait otomatik scheduler/polling veya abonelik uygulaması yok. |
| **Enterprise Integration — Future** | Gelecekte ortak Termivar ekosistemi, envanter ve uygun ürün entegrasyonlarının kapsamlandırılması. | Gelecek paket; bugün satın alınabilir veya production-ready değildir. SSO/çok kiracılı SaaS/enforcement taahhüdü içermez. |

Fiyat ve ciro tahmini üretilmedi. Fiyatlandırma öncesi ölçülecek değişkenler: uygulama/origin/API ve kaynak sayısı; seçilen inceleme yolları ve kapsam karmaşıklığı; erişim/kurulum hazırlığı; uzman inceleme ve rapor emeği; kanıt/veri işleme yükü; destek ve açıklama görüşmeleri; yeniden değerlendirme sayısı/sıklığı; karşılaştırılabilirlik analizi ve teslimat revizyonları. Teknik istek bütçesi tek başına işçilik veya maliyet ölçüsü değildir. Gerçek maliyet/kapasite ölçümü `not_validated`.

## Ekosistemdeki konum

| Bileşen | Bu teklif içindeki konumu |
|---|---|
| **Termivar Web** | İlk ticari web/API değerlendirme ürünü adayı; uzman liderliğinde ayrı, dar kapsamlı pilot hazırlanabilir. |
| Termivar Platform | Ortak yönetim temeli ve mevcut envanter/yerel inceleme konsolu; production/API/IdP kabulü bekliyor. İlk bağımsız Termivar Web hizmeti bu kabulün tamamlanmasına bağlanmaz. |
| HostBasedFirewall | Ayrı endpoint ürünü; gerçek Windows kabulü bekliyor. Termivar Web assessment hizmetine kurulu firewall veya policy enforcement olarak eklenmez. |
| Policy Impact Workbench | Önceden üretilmiş offline preview inceleyicisi; uygulama/yürütme yetkisi yok. |
| Antivirus | Planlanan ürün; çalışan motor sunulmuyor. |

Bu ayrım mevcut platform `aa643d40797998d5f615cb5ba5b71b972596abc9` [ürün kataloğu](../../operator-console/src/features/productHub/productCatalog.ts) ve [yetenek matrisiyle](../../operator-console/docs/CAPABILITY_MATRIX.tr.md) aynıdır. Bütün ekosistemin hazır olması ilk Termivar Web adayının şartı yapılmaz; kullanılan Termivar Web yolu ve hizmet işletiminin kendi açık kapıları da tamamlanmış gösterilmez.
