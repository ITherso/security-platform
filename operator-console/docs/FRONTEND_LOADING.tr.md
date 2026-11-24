# Ekran bazlı frontend yüklemesi

Bu fazın amacı, Termivar Web assessment/comparison, politika önizlemesi ve uygun büyük ekranların kodunu operatör o ekranı açmadan başlangıç JavaScript'ine taşımamaktır. React/Vite ve mevcut kilitli bağımlılıklar korunur. Lazy yükleme bir güvenlik özelliği veya daha hızlı render/bağlantı garantisi değildir; gerçek build byte'ları ve manuel gözlemler ayrı kaydedilir.

## Phase12 gerçek başlangıç ölçümü

Phase13 değişikliklerinden önce mevcut `dist/build-manifest.json` ve üç dosyanın gerçek boyut/SHA256 değerleri okundu ve eşleşti. Kaynak başlangıcı `f8785b0ba7ca31b7179ee44770b0ae74f3271a4c`.

| Önceki varlık | Gerçek bayt | SHA256 |
|---|---:|---|
| `index.html` | 504 | `17e3ffae88b0919d25b08930938555a15c0c66ee6ef41ed8e508ff14a82b34e8` |
| `assets/console.js` | 598925 | `717939c3f4403d79946a4efd9239824ea7afde4545128c362cdc8ca6645c7867` |
| `assets/console.css` | 72445 | `cfd3ca797823ea3c60d9b98f8480b62ed0d16323c6692196e6f62eadd8d719a8` |

Önceki varlık kümesi SHA256 `fc73e68e140746b6a7601b86564d023a49d6c2b2440e6130f6b750b9335090ba`. **598925 bayt**, lisans bildirimi dahil gerçek entry JS dosyasıdır. Önceki Vite **595,53 kB** değeri lisans eklenmeden önceki yuvarlanmış build çıktısıdır; birebir byte ölçümü yerine kullanılmaz.

Kaynak git dışındaki `outputs/phase13-loading-before.json` bu ölçümleri; `phase13-loading-before-manifest.json` ham manifest'in exact byte kopyasını korur. Bu dosya okuma kaydı network waterfall, parse/paint/CPU süresi, cache-hit veya performans benchmark'ı değildir. Başlangıç static-import JS toplamı ile tek entry dosya boyutu aynı metrik sayılmamalıdır.

## Gerçek Phase13 build ölçümü

| Metrik | Phase12 önce | Phase13 sonra |
|---|---:|---|
| Entry JS (lisans dahil) | 598925 bayt | 509632 bayt |
| Başlangıç static-import closure JS toplamı | 598925 bayt | 509632 bayt; **89293 bayt / %14,91 daha az** |
| Başlangıç CSS | 72445 bayt | 51025 bayt |
| Tüm JS | 598925 bayt | 696080 bayt; bunun **186448 baytı** başlangıç static closure dışında |
| Tüm CSS | 72445 bayt | 77929 bayt |
| Tüm runtime varlıkları | 671874 bayt / 3 dosya | 774520 bayt / **21 dosya** (16 JS, 4 CSS, 1 HTML) |
| Ekran bazında ayrı varlıklar | Ayrı lazy ekran chunk'ı yok | Termivar assessment/comparison, policy, ürün/detail/audit, report/preview ve cihaz comparison ekranları; parser/örnek modülleri de ayrı chunk'larda |
| 500 kB chunk uyarısı | Pre-license entry 595,53 kB; uyarı vardı | Pre-license entry **506,24 kB**; uyarı sürüyor, limit değiştirilmedi |
| Ekran açılışında yükleme/hata görünümü | Bu before kaydında ölçülmedi | Device detail, cihaz comparison, Termivar comparison ve policy açılırken gerçek yükleme fallback'i görüldü; hata enjeksiyonu yapılmadı |

Son frozen-lockfile/ignore-scripts/offline kurulum, strict typecheck ve production build başarılıdır: **94 modül**. Manifest v2 asset-set SHA256 `619a81349f5a92f050e6e9bf98f9fe883b2aeb7f3f2e229507ef31c909e51a18`. `outputs/phase13-loading-after.json`, gerçek build byte'larından ve statik import closure'ından yukarıdaki karşılaştırmayı kaydeder. Yeni entry `assets/console.js` **509632 bayt**, SHA256 `785d2101de2402fc19945a88f9ad64c155f72950b5851f709e56748105b57640`.

Başlangıç JS'i azaldı, fakat **tüm JS toplamı 97155 bayt arttı**. Yeni Ürün Merkezi/rehber ve yükleme kodları ile her JS chunk'ında korunan tam lisans bildirimi bu toplama dahildir; büyümenin her etkene düşen payı ayrıca ölçülmedi. Bu sonuç bütün uygulamanın daha küçük olduğu, daha hızlı render ettiği veya network süresinin azaldığı iddiası değildir. Cache, transfer sıkıştırması, parse/paint/CPU ve kullanıcı gecikmesi ölçülmedi. Hedef, ilgili ekranlar/reader/örnek kodunun başlangıç static closure'ından gerçekten ayrılmasıdır; uyarı gizlenmedi.

## Manifest v2 ve sunum sınırı

`dist/build-manifest.json`, `schema_version=2`, `kind`, `asset_set_sha256`, `files[{path,bytes,sha256}]`, `entry_files`, `initial_files` ve `module_graph[{path,imports,dynamic_imports,css}]` alanlarını taşır. `initial_files`, entry'den erişilen **statik** import closure'ı ve HTML'dir; dinamik ekran/örnek/reader chunk'ları başlangıç toplamına eklenmez. Kaynak dosya yolları Vite grafiği doğrulandıktan sonra runtime manifest'ine alınmaz. Manifest identity kanıtı imza/üretici attestation değildir.

Üretim/sunucu hattı en fazla **32 runtime dosyası**, dosya başına **2 MiB**, toplam **8 MiB**, manifest **64 KiB** ve **128 graph edge** sınırını uygular. Yalnız manifest'teki izinli JS/CSS/HTML varlıkları boyut/hash eşleşmesiyle sunulur; dizin listesi/proje dosyası/API proxy eklenmez. Hashli CSS adları ve değişen chunk envanteri desteklenir; her JS'te lisans metni korunur. Vite `modulePreload=false` ile yapılandırılmıştır; yeni lazy ekran önden alma/polling eklenmez.

## Veri/güven sınırı

Dinamik modül yolları uygulamanın belirlediği sabit ekran modülleridir; JSON/dosya adı/URL/tenant/token modül seçemez. Yerel JS/CSS chunk isteği uygulama kodunu indirir; API cihaz GET'i, yeni veri toplama, prefetch/polling veya scanner isteği değildir. Bir ekrana açık gezinmenin o sayfanın mevcut veri davranışını başlatması ayrı konudur; auth/tenant kuralları değişmez.

Paylaşılan store/token tek uygulama oturumudur; lazy ekrana özel kopya yetki kaynağı kurulmaz. Locale değişimi sırf dil için ekranı yeniden kurup import/rapor/karşılaştırma durumunu silmez. Tenant/mode/session değişiminde mevcut sequence/generation/erişim temizliği korunur. Kaynakta Suspense yükleme durumu, ekran hata sınırı ve Ürün Merkezi'ne dönme eylemi vardır. Reader modülünün yüklenememesi üç yerel importer'da `reader_unavailable` ile bozuk JSON'dan ayrılır; source format/katalog doğrulayıcılarının anlamı genişletilmez. Bu davranışların kaynakta uygulanması, manuel gözlem ve kontrollü yarış/canlı kabul ayrı kanıt düzeyleridir.

Son build'in sınırlı manuel örnek incelemesinde device detail, cihaz comparison, Termivar comparison ve policy açılırken yükleme fallback'i görüldü. Üç rehber mevcut sayfalara açık gezinmeyle ulaştı; dil değişiminde adım ve rapor/cihaz comparison seçimleri kaldı. Bunlar görünür ürün davranışıdır, request timing kanıtı değildir. Tarayıcı network timing kaydı alınamadı; kontrollü yavaşlatma, chunk failure, geç yanıt/yarış veya gerçek API kabulü yapılmadı. Post-await context guard'ları yalnız kaynak incelemesi olarak kaydedilir.

Aşama 2 adım 4 iki sabit lazy ekran modülü ekledi: `features/events/AlertsPage` (Uyarılar) ve `features/events/DeviceTimeline` (cihaz ayrıntısındaki zaman çizelgesi), ortak `events.css` ile. Yukarıdaki Phase13 ölçümleri bu modülleri içermez. Taşınabilir Node 24.22.1 ile alınan son build (2026-11-24, bulgu düzeltmelerinden ve Termivar ad değişikliğinden sonra) 99 modül ve **24 runtime dosyası** üretir; `build.py` sınırları tutar: 24/32 dosya, 35/128 graph edge. Yeni lazy chunk'lar lisans başlığıyla `AlertsPage` 10753, `DeviceTimeline` 8813 ve `events.css` 2296 bayttır; entry `assets/console.js` 546055 bayt, tüm runtime varlıkları 833080 bayttır. Başlangıç static closure'ı yine `console.js`, ana CSS ve `index.html`'dir; iki ekran yalnız açılınca yüklenir. Asset-set SHA256 `9c5fe1c9a5f1035f145a689f104253ae6030b0354d21b3e83500540fe2f53626` (`dist/build-manifest.json`). Ad değişikliğinden önceki build'in (`98bd260c…`) değerleri artık `dist/` ile eşleşmez. Bu bir byte kaydıdır; yükleme hızı ölçülmedi.

Önizleme sunucusu manuel inceleme sonunda Ctrl+C ile durduruldu ve 8787 portunda dinleyici kalmadığı gözlendi. Gerçek build ile source guard incelemesi, browser'ın hangi chunk'ı ne zaman istediğinin veya daha hızlı kullanıcı deneyiminin kabulü değildir. İlgili çalışma [Phase13 DELIVERY](DELIVERY.tr.md) içinde build/manuel/çalıştırılmayan kabul olarak ayrılır; bu belge test başlatma talimatı değildir.
