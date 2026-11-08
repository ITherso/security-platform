# Ürün Merkezi

**Ürün Merkezi / Product Hub**, Security Ecosystem'deki mevcut ürün ve çalışma alanlarına tek yerden ulaşmayı sağlar. Statik, tipli frontend kataloğudur; bir cihazın ürün kurulumunu, sağlığını, korunmasını, lisans hakkını veya bağımsız doğrulanmasını hesaplamaz. [English guide](PRODUCT_HUB.en.md), [yetenek matrisi](CAPABILITY_MATRIX.tr.md).

## Beş giriş ve mevcut bağlantıları

| Tür / sabit ID | Ürün veya bileşen | Mevcut konsol hedefi | Kaynak ve sınır |
|---|---|---|---|
| product `hostbasedfirewall` | HostBasedFirewall | Cihazlar (`devices`) | Örnek ya da açık API kipindeki cihazın bildirdiği HBF durumu. Yerel Windows ürünü ayrı çalışır; merkezden policy push/enforcement ve tamamlanmış gerçek Windows kabulü yoktur. |
| product `termivar` | Termivar | Değerlendirme incelemesi (`termivarReview`), aynı alanda karşılaştırma | Önceden hazırlanmış desteklenen yerel JSON. Konsol scanner başlatmaz; artefakt açılması hedefi/üreticiyi doğrulamaz. |
| component `policy-impact-workbench` | Policy Impact Workbench | Politika önizlemeleri (`policyReview`) | Önceden üretilmiş CLI preview sonucu. Gerçek policy revision/lineage otoritesi, uygulanma veya doğrulama yoktur. |
| component `security-platform` | Security Platform | Genel bakış (`overview`) | Mevcut tenant/device/product inventory ve audit sözleşmeleri. Örnek kip çalışır, gerçek API adapter'ı uygulanmıştır; kurumsal IdP/production canlı kabulü yapılmadı. |
| product `antivirus` | Antivirus | Ürünler (`products`) | Yalnız planlanan ürün bilgisi; `planned/unavailable`. Motor, tarama, zararlı yazılım tespiti veya gerçek zamanlı AV koruması yoktur. |

İlk dört girişin `availability=available_workspace`, AV'nin `availability=planned_unavailable` olması **konsol özelliğinin bulunabilirliğidir**. Ayrı `verification=not_verified` korunur. Bu değerler installed/protected/verified anlamına gelmez. İki component ID yalnız frontend kataloğuna aittir; backend'in üç ürünlü DTO'suna yeni ürün eklemez.

Kart bağlantısı mevcut sayfaya gider. İlgili sayfa API kipinde normal mevcut GET'ini yapabilir; katalog yeni endpoint, izin veya client eklemez. Kur/etkinleştir/satın al/tara/koruma aç gibi çalışmayan eylemler, ödeme veya müşteri kayıt ekranı yoktur. Kaynak marka ve teknik ID'ler çevrilmez.

## Platformu keşfet: yalnız demo rehberi

Rehber mevcut ekranları tanıtır; ikinci uygulama, otomatik demo oynatıcı veya veri toplayıcı değildir. Başlatmak için örnek veri kipi, seçilmiş bir DEMO tenant ve tamamlanmış/boşta mevcut yükleme gerekir. API/kapalı bağlantı bağlamını sessizce örneğe çevirmez; token, istemci veya oturumu değiştirmez. Gerekirse mevcut bağlantı panelinden örnek kipi ayrıca ve açıkça seçilir.

Her biri beş adımdan oluşan üç sabit akış:

| Akış ID | Kullanıcının inceleyeceği mevcut özellikler |
|---|---|
| `endpoint` | Örnek cihaz listesi, kullanıcının açacağı cihaz ayrıntısı, bildirilen HBF durumu, mevcut cihaz karşılaştırması/ürün raporu. |
| `termivar` | Assessment çalışma alanı, kullanıcının açıkça yükleyeceği sentetik örnek, kapsam/eksik kontroller, mevcut comparison görünümü ve only-in-before'ın remediation olmaması. |
| `policy` | Policy Impact Workbench, kullanıcının açacağı sentetik preview, ayrı base/candidate/adapter kimlikleri ve CAS/revision eksikliği. |

Başlat/sonraki/önceki eylemleri yalnız rehberin akış/adım bilgisini değiştirir. **Adımın ekranına git** ayrı, açık gezinme eylemidir. Rehber dosya/örnek açmaz, cihaz ayrıntısını otomatik getirmez, tarama/karşılaştırma çalıştırmaz ve veri kopyalamaz. Hedef sayfanın mevcut kontrolları normal şekilde kullanıcı tarafından kullanılır. Görünmeyen elemanı zorla açma veya gizli bilgi okumak için DOM manipülasyonu yoktur.

Kapatma normal sayfanın kullanımını bırakır. Rehber yalnız bellektedir; dil değişimi adım konumunu korur, tenant/mode/session değişimi ve mevcut erişim temizliği uygun olmayan rehberi kapatır, reload sıfırlar. Kalıcı depolama, analytics veya dış ağ çağrısı eklenmez. Yerel lazy JS/CSS yüklemesi yalnız uygulama kodudur; gerçek cihaz API çağrısı değildir. [Yükleme sınırları](FRONTEND_LOADING.tr.md).

## Güven anlamları değişmez

`self_reported`, `not_verified`, `unknown`, `stale`, `revoked` ve `planned/unavailable` tanıtım veya rehberle daha olumlu duruma çevrilmez. Yeni bildirim koruma kanıtı, revoked cihaz kaydı firewall'ın kapalı olduğu kanıtı, Termivar raporu çalışan scanner kanıtı değildir. Preview firewall kuralı uygulamaz; comparison'da öğenin kaybolması düzeltme kanıtı değildir.

Bu belge müşteri sözleşmesi, SLA, sertifika, fiyat/satış teklifi veya production readiness onayı değildir. İlk ücretli kurumsal ürün için kapanmamış teknik/işletimsel kapılar [matriste](CAPABILITY_MATRIX.tr.md) gerçek durumlarıyla ayrılır. Testler ve canlı kabul bekletilmeye devam eder; gerçek kurulum/typecheck/build ve sınırlı manuel gözlemler [Phase13 teslim kaydındadır](DELIVERY.tr.md).
