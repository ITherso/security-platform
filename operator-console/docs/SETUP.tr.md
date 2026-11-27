# Kurulum ve yerel çalışma

Bu dizin, Termivar Platform backend'inden bağımsız React + TypeScript + Vite frontend'idir. Python wheel, API, veri tabanı veya HBF kurulumu gerektirmeyen örnek veri kipiyle açılır. Bu tur gerçek operatör token'ı üretilmez/aranmaz, IdP veya backend başlatılmaz ve canlı bağlantı kabulü yapılmaz.

## Araç sürümleri ve komutlar

Seçilen araçlar **Node 24.22.1** (`engines: >=24.22.1 <25`) ve **pnpm 11.25.0** (`packageManager`) değerleridir. Lockfile `pnpm-lock.yaml` dosyasıdır. Seçilen doğrudan paket sürümleri React/react-dom 19.3.1, Vite 8.3.6, TypeScript 5.9.3, React/DOM tipleri 19.3.0 ve Node tipleri 24.10.1'dir. Kilitli kurulum, typecheck ve build gerçekleşen teslim kaydında ayrı raporlandı. Rastgele en güncel sürüm veya farklı paket yöneticisiyle yeniden çözümleme yapılmamalıdır.

Platform kökünden frontend dizinine geçin:

```powershell
cd .\operator-console
pnpm install --frozen-lockfile --ignore-scripts
pnpm typecheck
pnpm test
pnpm build
..\.venv\Scripts\python.exe .\serve.py --port 8787
```

Kurulum lockfile'ı esas alır; dependency lifecycle script'leri kapalıdır. `typecheck`, TypeScript tür denetimi (`src` ve `tests`); `build`, production statik varlık üretimidir. Bunlar test sonucu değildir. `test`, `tests/*.test.ts` davranış testlerini yeni bağımlılık olmadan çalıştırır: kurulu Vite dosyaları SSR modül yükleyicisiyle (`ssrLoadModule`) yükler, Node'un yerleşik `node:test` ve `node:assert` modülleri sınar. Vite bu sırada yapılandırma dosyası okumaz, middleware kipindedir; port açmaz, HMR, dosya izleyicisi ve bağımlılık ön paketlemesi kullanmaz ve diske yazmaz ([`tests/run.mjs`](../tests/run.mjs)). `serve.py`, Vite'ın `dist/` çıktısını `http://127.0.0.1:8787/` adresinde değişmez yerel önizleme olarak sunar. Çalışan sunucu yeniden build'i kendiliğinden almaz; `Ctrl+C` ile durdurup yeniden başlatın. Gözlemlenen URL ve build sonucu [teslim kaydında](DELIVERY.tr.md) bulunur.

Geliştirme için `pnpm dev`, Vite build önizlemesi için `pnpm preview` kullanılabilir. Dev/preview yapılandırması yalnız loopback, strict port, CORS kapalı ve proxy'sizdir. `0.0.0.0`, public tunnel veya genel allowedHosts/CORS kullanmayın. Vite'ın [server.host/allowedHosts/strictPort belgesi](https://vite.dev/config/server-options), bu ayarların kapsamını açıklar. Geliştirme sunucusu üretim dağıtımı değildir. Ürün API'si için arka plan polling eklenmez; geliştirme araçlarının HMR bağlantısı ürün verisi aboneliği değildir.

`build.py`, Vite çıktısının üç sabit dosyası için bütünlük manifestini üretir; TypeScript derleyicisinin yerini almaz. `serve.py` bu manifestle doğrulanmış Vite varlıklarını sunar. Çıktı kaynak TypeScript/TSX yerine derlenmiş statik varlıklardır.

## Varsayılan örnek veri

Sayfa ilk açıldığında her zaman **“Örnek veri — gerçek cihazlara bağlı değil”** kipindedir. İki kurgusal tenant ve mevcut DTO şekline uyan örnek cihaz/ürün/audit verisi kullanılır. Token aranmaz; platform keşfi, otomatik bağlantı, arka plan yenileme veya telemetri çağrısı yapılmaz. Görseller, ikonlar ve stiller yereldir.

Örnek senaryo seçicisi normal/boş/hata görünümlerini açar. Boş senaryo gerçek API'de kayıt bulunmadığını, hata senaryosu gerçek bir kimlik/yetki veya bağlantı arızasını kanıtlamaz. Örnek ve API verisi aynı DTO doğrulama/normalizasyonundan geçer; canlı hata durumunda örneğe sessiz dönüş yoktur.

## Sonraki açık yapılandırma için API bağlantısı

Bu panel login/SSO değildir. Mevcut sağlayıcınızdan dışarıda alınmış **operatör API access token** ve API adresi, ancak operatörün ayrı **Bağlan** eylemiyle kullanılabilir. Device/enrollment sırları kabul edilecek bir operatör giriş yöntemi değildir. Konsol token üretmez, yenilemez, keşfetmez ve token claim'lerinden tenant/rol yetkisi çıkarmaz.

Sırsız adres örneği:

```text
Konsol:    https://console.example.invalid/
API tabanı: https://console.example.invalid/api/v1
```

Örnek adres bağlantı kurulmuş bir dağıtım değildir. Gerçek kullanımda hedef tam olarak sayfanın **aynı HTTPS origin'i** ve sabit `/api/v1` tabanı olmalıdır. Userinfo, token/query/fragment veya başka API yolu/origin kabul edilmez. HTTP yerel önizleme yalnız örnek veri içindir. CORS/sertifika sorunu için `no-cors`, TLS doğrulamasını kapatma veya kimlik atlayan proxy çözümü eklenmez.

Token yalnız açık sayfanın oturum belleğindedir. Bağlanınca parola tipi token alanı temizlenir. `localStorage`, `sessionStorage`, IndexedDB, cookie, URL/query/hash, `.env`, Vite build değişkeni, bundle, log ve dışa aktarım token deposu değildir. Adres/token/kip değişimi veya bağlantıyı kesme özel verileri ve eski istekleri temizler; sayfa yenilenince canlı oturum kendiliğinden geri gelmez. Konsolun GET sınırlaması token'ın API'deki gerçek yetkilerini daraltmaz.

## Taşıma ve veri sınırları

Adapter yalnız [altı operatör GET'ini](API_UI_MAPPING.tr.md) kullanır: tenant listesi, cihaz listesi, cihaz ayrıntısı, audit, cihaz olay zaman çizelgesi ve uyarı listesi. İstekler açık `Authorization` başlığı, `credentials: omit`, `cache: no-store`, `redirect: error` ve fetch + body için toplam **12 saniye** sınırıyla yapılır. Tek JSON yanıtının okunan gövdesi en fazla **512 KiB**'dır; boyut/süre/biçim aşımı görünür hatadır. API'nin `next_offset`, `next_before_seq` ve `next_before` değerleri doğrulandıktan sonra aynı sabit route üzerinde izin verilen query'ye çevrilir; yanıttan keyfî URL takip edilmez. Fetch/CORS/redirect davranışının dayanağı [WHATWG Fetch Standardı](https://fetch.spec.whatwg.org/)dır; bu frontend tarayıcının erişim sınırını kaldırmaz.

Runtime doğrulama gerekli alanları, null/enum ilişkilerini, UUID/tenant/device bağını ve tam sayı kesinliğini denetler. Backend BIGINT sayaçları `2^63−1` değerine kadar çıkabilse de frontend yalnız JavaScript'in tam temsil ettiği **0…2^53−1** aralığını kabul eder; pozitif sequence alanlarında alt sınır 1'dir. Büyük/uygunsuz sayılar yuvarlanmaz veya sıfır yapılmaz: ilgili yanıt kapalı hata üretir. Ek alanlar yetki veya olumlu güven sonucuna çevrilmez. Bilinmeyen güven/koruma enum'u sağlıklı kabul edilmez.

Tenant/görünüm değişiminde eski istekler iptal edilir; bağlam/istek kimliği geç dönen cevabın yeni ekrana yazılmasını engeller. 401 bağlantıyı ve özel veriyi temizler; 403 ilgili görünümde erişim reddidir. Ağ hatası tek başına kesin 401/CORS teşhisi değildir. Kullanıcı eylemi dışındaki polling, focus-refresh, websocket, prefetch ve otomatik retry bulunmaz.

## Statik dağıtım

Build çıktısı mevcut HTTPS reverse proxy üzerinden aynı origin'de sunulabilir. `/api/v1/…` yönlendirmesi mevcut API'de kalır; yeni backend endpoint/static route veya CORS gevşetmesi gerekmez. Mevcut Host/TLS/Origin ve rol doğrulamaları korunur. Statik host'ta self script/style/connect, `frame-ancestors 'none'`, `object-src 'none'`, `form-action 'none'`, no-store, nosniff ve no-referrer sınırları uygulanmalıdır. Bu belge dağıtım yapıldığı iddiası değildir.

Ürün anlamları için [PRODUCT_STATES](PRODUCT_STATES.tr.md), gerçekleşen çalışma ve bekleyen kanıtlar için [DELIVERY](DELIVERY.tr.md) dosyalarını okuyun.

## Seçili cihazların durum raporu

Ek runtime bağımlılığı veya backend kurulumu gerekmez. Görüntülenen cihaz ayrıntısından **Durum raporuna ekle** ile en fazla 20 cihaz/256 KiB UTF-8 bellek taslağı oluşturulur. [Rapor kullanımı](REPORTS.tr.md) ad/kimlik tercihini, bağlam değişiminde temizlenmeyi ve sabit önizlemeyi açıklar. Tek çıktı yolu kullanıcı eylemiyle tarayıcının yazdır/PDF akışıdır; HTML/JSON/CSV indirme, otomatik dosya kaydı veya yeni API isteği yoktur. Dosyanın gerçekten kaydedilmesi tarayıcıda kullanıcının seçimine bağlıdır; build veya ekran görüntüsü PDF kaydı kanıtı değildir.
