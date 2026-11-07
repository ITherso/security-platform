# Operatör konsolu teslim kaydı

React + TypeScript + Vite ile bağımsız, Türkçe ve salt okunur frontend tamamlandı. İlk açılış açıkça örnek veridir. Gerçek API adapter'ı mevcut dört GET'e bağlıdır; gerçek bağlantı kabulü yapılmadı.

## Kaynak ve paket kimliği

Korunan backend temeli `f2400c3744937b0a82bbba63c77f274721f8d61b`; değişmeyen HBF `74a88ed336cb8a0a2fab16e20389c9410590c292` sürüm 1.4.3'tür. Bu tur yalnız `operator-console/**`, ana README ve konsol belgesini değiştirir. Backend, auth/rol/credential, DB/Alembic, sender/snapshot, policy core, revision laboratuvarı ve üretim wheel'i korunur.

Yeni commit, kaynak ZIP boyutu/SHA256 ve tam dosya farkı dış `delivery-manifest.json` ile `evidence/operator-console/platform-console-changes.patch` içinde kaydedilir. Arşivin kendi hash'i kaynağa gömülmez. Eski phase4 birleşik paket 1.458.787 bayt / `196fe6b3f79eaeb7a19550c83ebed2205c5bd6484f1b01943f1b516f1b78564e` kimliğiyle ayrı korunur; bu hash yeni teslimatı tanımlamaz.

## Derleme/typecheck

7 Kasım 2026'da Node **24.22.1**, pnpm **11.25.0** kullanıldı. Kilitli kurulum `pnpm install --frozen-lockfile --ignore-scripts` tamamlandı. `pnpm typecheck` ve `pnpm build` başarıyla tamamlandı. Script'ler yalnız Vite, TypeScript ve statik manifest üretir; test/coverage/pytest/Playwright/Vitest başlatmaz.

Üretim build'i üç dosyadır: `index.html`, `assets/console.js`, `assets/console.css`. `dist/build-manifest.json`, gerçek boyut/SHA256 değerlerini ve varlık kümesi özetini taşır. Son varlık kümesi SHA256:

`0f2bc69b2a9c2cab014ddd28b53f9330e5e6bfac071395d4d6a3bdad68978f66`

Bu özet bütünlük kaydıdır; imza veya güvenlik kabulü değildir. Python önizlemesi doğrulanmış varlıkları belleğe alarak yalnız `127.0.0.1:8787` üzerinde sundu; HTTP 200 gözlendi. İş bitiminde önizleme durduruldu. Hazır `dist/` ile yeniden açmak için yalnız `python serve.py --port 8787` yeterlidir.

## Elle ürün önizlemesi

Gerçek yerel tarayıcıda örnek verilerle genel görünüm, cihaz araması, durum filtresi, sıralama, ikinci sayfa, cihaz ayrıntısı/geri dönüş, ürünler ve audit incelendi. İkinci şirketin görüntüleyici rolünde audit erişim açıklaması gözlendi. Normal/boş/hata senaryoları ayrı etiketlendi; hata halinde sayaçlar sıfır yerine bilinmeyen olarak gösterildi.

390×844 dar ekran önizlemesinde menü açma/kapama ve içerik akışı incelendi. Sayfa yatay taşması giderildi; tablo kendi içinde kayar. Geçici tarayıcı ölçüsü geri alındı. Klavye Tab odağı ve Escape ile ayrıntı kapatma gözlendi. Bu, kapsamlı erişilebilirlik veya cihaz uyumluluk kabulü değildir.

Gerçek ekran görüntüleri teslimde `evidence/operator-console/operator-console-*.png` altındadır: `overview`, `overview-full`, `detail`, `products`, `audit`, `empty`, `error`, `mobile`, `keyboard`, `sort`. Son tarih sıralaması düzeltmesi sonrasında typecheck/build ve örnek verili sıralama önizlemesi tekrar tamamlandı; eski ekran görüntüleri aynı görünümün önceki build gözlemidir. Ayrıntılı gerçekleşen çalışma `console-delivery-status.json` dosyasındadır. Örnek veriler gerçek tenant/cihaz/credential faaliyeti kanıtı değildir; hiçbir gerçek token veya canlı API kullanılmadı.

## Çalıştırılmayan testler ve canlı kabul

- Kullanıcının yönlendirmesiyle bu tur test dosyası veya runner eklenmedi; mevcut/yeni testler çalıştırılmadı.
- Eski **506 passed / 2 skipped** yalnız tarihsel backend/laboratuvar temelidir; konsol sonucu değildir. Eski fresh-package hash'i eski platform kaynağına aittir.
- Gerçek IdP, canlı API, CORS/sertifika ve operatör oturumu kabulü yapılmadı. Adapter uygulandı; gerçek bağlantı kabul edilmedi.
- Windows 12 vaka **NOT_RUN**, önceki native symlink **SKIP** kalır. Gerçek revision kaynağı/sorumlusu belirlenmedi.
- Policy apply/push, scanner yürütme, driver/native enforcement, VM/servis/UAC/reboot veya uzaktan komut eklenmedi.
- Public deploy, GitHub push/release, EXE ve production wheel yeniden üretimi yapılmadı.

[Kurulum](SETUP.tr.md), [API–UI eşlemesi](API_UI_MAPPING.tr.md), [ürün durumları](PRODUCT_STATES.tr.md).

Dağıtılan React, react-dom ve scheduler MIT metinleri THIRD_PARTY_NOTICES.txt içinde ve derlenmiş JavaScript yorumunda korunur. Son build bu lisans yorumunu ekler; uygulama davranışı ve görünümü değişmez.

## Ürün Phase6 — seçili cihaz raporu

Yukarıdaki build ve elle önizleme gözlemleri önceki Phase5 konsol teslimine aittir; yeni rapor akışının kabulü değildir. Gerçek başlangıç `62e970ffbbae7f68c6a7d4750cb03bfbc5666e4f` olarak yerel git ve teslim manifestinden okunmuştur. Prompttaki `3e7a6d5`/eski arşiv kimliği güncel Phase5 kaydı yerine kullanılmaz.

Phase5 dosyaları yeni paket yazılmadan ayrı kopyalarla korunmuştur:

| Korunan dosya | Bayt | SHA256 |
|---|---:|---|
| `Security-Ecosystem-phase5-2026-11-07.zip` | 4.584.218 | `a81dc8357686ffa859a3866c6cddb68d8a256932e6850f31413c5ff3501dc991` |
| `Security-Operator-Console-phase5-2026-11-07.zip` | 3.038.060 | `0eb92266425dc11047fdd7c5295130e1ecabfe3ca3f82bf8949f3439ec900eb2` |
| `Security-Platform-phase5-0.1.0-source.zip` | 323.663 | `b7ea0ed20222d123c4afb1c12e7631a87ddfe1f082bd552fd40319b7da027ef7` |

`phase5-delivery-manifest.json` ve `phase5-console-delivery-status.json` aynı teslimin önceki kanıtlarını korur. Bu eski hash'ler yeni rapor build/paket kimliği değildir.

- Kilitli kurulum, strict typecheck ve production build tamamlandı; test çalıştırılmadı. Üç varlığın yeni küme SHA256 değeri `eda1b228051c70f8dbcdc2a368ad3b28e5529ef36dc1d66835f6488b8d0cdf7e`.
- Örnek verili gerçek tarayıcıda ekleme, açık güncelleme, gezinmede koruma, kaldırma, temizleme, adları açma/gizleme, sabit önizleme ve şirket değişiminde temizlenme gözlendi. 390×844 dar ekran ve iki cihazlı uzun ekran akışı incelendi; geçici ölçü geri alındı. İki cihazdan biri ürün raporu olmayan geçerli kayıttır. Bu gözlemler test paketi değildir. Son build ayrıca erişimle ilişkili 404 için taslağı temizler ve eski ayrıntı yanıtını rapor generation bilgisiyle engeller; canlı API dalı çalıştırılmadı.
- Yazdır düğmesiyle yerleşik akış istendi; uygulama içi tarayıcıda yazdırma iletişim kutusu denetlenemedi ve sayfa etkileşimi bekledi. İlgili kendi önizleme sekmesi kapatılıp normal düzenleme yeni örnek sekmesinde sürdürüldü. Yerleşik baskı önizlemesine ve gerçek sayfa bölünmesine erişilemedi; A4 baskı düzeni kaynakta uygulanmıştır fakat kağıt/PDF görünümü doğrulanmadı.
- Örnek PDF kaydedilmedi. Ekran görüntüleri yalnız HTML ürün önizlemesidir; PDF/baskı kabulü değildir.
- Yeni kaynak/konsol/birleşik paket boyutu ve SHA256 değerleri dış `delivery-manifest.json` içinde gerçek arşivlerden ölçülür. Kaynağa kendi arşiv hash’i gömülmez. `operator-console-report-*.png` dosyaları bu ürün turunun ekranlarıdır; önceki konsol ekranları Phase5 gözlemidir.

Bu tur da test dosyası/runner eklenmez ve test çalıştırılmaz. 506/2 tarihsel; gerçek API/token/IdP/PG/Windows işlemleri yapılmaz. Windows 12 NOT_RUN, symlink SKIP ve gerçek revision otoritesi kapıları değişmez. Rapor akışı ürün sunumudur; merkezi snapshot/revision/receipt, bağımsız doğrulama veya execution yetkisi oluşturmaz. `window.print()`/`afterprint` dosyanın kaydedildiği veya baskının tamamlandığına kanıt değildir. [Rapor sınırları](REPORTS.tr.md).

## Ürün Phase7 — Türkçe/İngilizce

Başlangıç `2825072f2e8bc78154586537da476a09b7dce691`, yerel git ve teslim manifestinden okunmuştur. Önceki rapor tesliminin dosyaları yeniden paketlemeden önce boyut/SHA256 doğrulamasıyla ayrı korunmuştur:

| Korunan dosya | Bayt | SHA256 |
|---|---:|---|
| `Security-Ecosystem-phase6-2026-11-07.zip` | 6.693.357 | `f68f69ab21650a86a9ba64f0c43eb183991c9e414c287e1c1f3458c11d264dea` |
| `Security-Operator-Console-phase6-2026-11-07.zip` | 5.128.139 | `1c59ab9120f3234d10a7cb5613a656e00eb659b73643f2bab51e4db5b52a5d9e` |
| `Security-Platform-phase6-0.1.0-source.zip` | 347.754 | `233492097980134634fe8f101bee74b29a19a6d987d55d9b14569d7c5c33d79e` |

`phase6-delivery-manifest.json` ve `phase6-console-delivery-status.json` önceki çalışma kaydını korur. Bu eski hash'ler yeni TR/EN build veya kaynak paketinin kimliği değildir.

- Frozen lockfile/ignore-scripts kurulumu, strict typecheck ve production build tamamlandı. Yeni varlık kümesi SHA256 `659174d7813eed58c347fc1ff9db94d49e2531a7b7b2d6db8c3009ef4e9d18a2`; test çalıştırılmadı. Sözlük anahtar ve parametre biçimleri mevcut TypeScript denetiminde kontrol edilir; ayrı test/script eklenmedi.
- Gerçek yerel tarayıcıda örnek verilerle TR→EN→TR; genel görünüm, cihaz ayrıntısı, ürünler, audit, bağlantı paneli, boş/hata görünümleri ve İngilizce HTML rapor önizlemesi incelendi. Kaynak cihaz/kurum adları değişmedi; UTC tarihleri farklı locale ile aynı anı gösterdi. Son tarih biçimleyici ayrıca geçersiz takvim tarihini normalize edip göstermeden reddeder; İngilizce genel görünüm son build ile tekrar açıldı.
- Dil değişirken seçili kurum, İzmir araması, stale filtresi, son kabul sıralaması ve ikinci sayfa korundu. Ayrıntı penceresinde dil seçimi aynı cihazı korudu. Rapor taslağı ve ad/kimlik tercihi kaldı; hazır İngilizce önizlemede Türkçe seçilince taslağa dönüldü, eski önizleme yazdırılabilir bırakılmadı. 390×844 İngilizce hata görünümü okundu; sayfa yatay taşması gözlenmedi ve geçici ölçü geri alındı. Seçim odağı korundu, document.lang en olarak görüldü. Sayfa yenilenince Türkçe başlangıç gözlendi. Bunlar sınırlı elle ürün gözlemleridir; kapsamlı erişilebilirlik/cihaz kabulü değildir.
- Altı gerçek TR/EN ekran görüntüsü `operator-console-locale-*.png` adıyla teslim edilir. İngilizce genel görünüm son build, diğer ekranlar yalnız son tarih doğrulama sıkılaştırması öncesindeki aynı UI görünümüdür. Yeni kaynak/konsol/birleşik paket boyutları ve SHA256 değerleri dış manifestte gerçek arşivlerden ölçülür; önceki hash yeni teslimata taşınmaz.

Bu tur native yazdırma önizlemesi veya PDF üretimi denenmez; önceki “native printpreview görülmedi / PDF kaydedilmedi” bilgisi korunur. Yeni test/runner/koşusu, canlı API/token/PG/IdP/Windows işlemi veya revision kabulü yoktur. 506/2 yalnız tarihsel temel; Windows 12 NOT_RUN ve symlink SKIP değişmez. Backend/HBF/wheel, kilitli runtime sürümleri, tarih sıralaması düzeltmesi ve MIT bildirimleri korunur. [Yerelleştirme](LOCALIZATION.tr.md), [English quick start](QUICKSTART.en.md).

## Ürün Phase8 — aynı sayfada önceki/sonraki ayrıntı

Başlangıç platform kaynağı `acbac544d9ebaea9f34147aed16d6654417c257e`; çalışma dalı `feat/operator-console-detail-navigation` olarak ayrıdır. Korunan Phase7 kopyaları değiştirilmez. Aşağıdaki kimlikler mevcut snapshot dosyalarının boyut/SHA256 değerleridir; yeni Phase8 arşivinin kimliği veya yeniden yapılmış bağımsız Phase7 kabulü değildir:

| Korunan dosya | Bayt | SHA256 |
|---|---:|---|
| `Security-Ecosystem-phase7-2026-11-07.zip` | 8.231.270 | `24ab130c3bc0c54266bb7746ce2d4dabea01c238f54e39a07bf8d2b5fb562f02` |
| `Security-Operator-Console-phase7-2026-11-07.zip` | 6.646.748 | `e777d4d6185e769131bea8530bdf36dcbb1032c8ede00d230c391539dbb1071e` |
| `Security-Platform-phase7-0.1.0-source.zip` | 371.716 | `5eb824c8ad09a1139b9b451bfbd488ac9642cf81340173ca8911594b2c7107fa` |

`phase7-delivery-manifest.json` ve `phase7-console-delivery-status.json` diğer iki korunan kayıt dosyasıdır. Tam paket/dosya kimlikleri dış teslim manifestinde tutulur; önceki hash'ler yeni çıktıya taşınmaz.

Dar ürün kapsamı, mevcut cihaz ayrıntısı penceresinde yalnız ekrandaki filtrelenmiş/sıralanmış yüklü sayfa içinde önceki/sonraki geçişidir. İlk/son kayıtta durur; başa sarma, komşu prefetch'i, başka sayfa okuma veya yeni API yolu yoktur. Seçilen hedef mevcut ayrıntı GET'iyle açık kullanıcı eyleminde okunur. Kapatınca arama/filtre/sıralama/sayfa, dil değişince hedef korunur; rapora ekleme/güncelleme otomatikleşmez.

Kaynakta mevcut abort ile epoch/sequence/generation/tenant/hedef denetimleri, geç başarı ve hata yanıtlarını etkin bağlama sınırlayan korumalar bulunur. Diyaloğu ilk açan kontrolün odak referansı saklanır; artık mevcut değilse arama alanı/ana içerik gibi güvenli dönüş hedefi kullanılır. Bunlar kaynakta uygulanan davranışlardır; yeni gezinme akışının canlı API, kontrollü gecikmiş yanıt/async hata ve erişim-hata dalları çalışma zamanında denenmedi. İlk açan kontrole dönüşün gerçek elle gözlemi de aşağıdaki bekleyen sonuçlardan ayrıdır.

- Frozen-lockfile/ignore-scripts kurulumu, strict typecheck ve production build tamamlandı. Son build 40 modül ve üç statik varlık üretir; küme SHA256 `aa77219fbd1de284a951caabb0c7d01d5f53be9bd9c98fc543e7f073aca476a4`. Test veya runner çalıştırılmadı.
- Gerçek yerel örnek tarayıcıda filtreli/sıralı sayfadan ayrıntı açma, önceki/sonraki ve ilk/son/tek cihaz sınırı gözlendi. Son build ile `DEMO` araması + stale filtresi + son kabul sırası, iki cihaz arasında geçiş, TR/EN dilinde aynı hedef, ilk açan İzmir satırına Escape ve kapat düğmesiyle dönüş tekrar incelendi. Liste kaydırması önce/sonra aynı `318.6666564941406` CSS px değerinde kaldı. İkinci sayfanın tek cihazında iki geçiş de kapalıydı; pencere kapatılınca `6–6` liste kapsamı kaldı. Önceki beş cihazlı görünümde ilk/son sınırı da incelendi; bu önceki UI derlemi gözlemidir.
- Açık eylemle eklenen tek İzmir rapor kaydı, başka cihazlar incelenince aynı sayıda ve aynı kayıt olarak kaldı; kimlik seçimi varsayılan kapalıydı. Yeni hedef eski ürün/zaman bilgileriyle gösterilmez; yükleme, geç yanıt/hata, 401/403/404 ve bağlamsız ayrıntı dallarındaki korumalar kaynakta uygulanmıştır. Kontrollü gecikme/hata veya canlı erişim dalı çalıştırılmadı; yeni fixture/hata enjeksiyon düzeneği yoktur.
- 390×844 ölçü ayarı mevcut ve yeni önizleme sekmesinde etkili olmadı; okunan gerçek ölçü `1280×720` kaldı. Geçici override geri alındı ve geçici sekme kapatıldı. Bu tur 390px dar görünüm **gözlenmedi**; CSS sarma kuralları kaynakta bulunur. Phase7 dar ekran gözlemi bu yeni işin sonucu sayılmaz.
- Üç gerçek ekran görüntüsü `operator-console-navigation-tr.png`, `operator-console-navigation-en.png`, `operator-console-navigation-last-page.png` son build'e aittir. Görsel içerik değiştirilmeden PNG olarak kodlanır. Son yerel HTTP okuması 200 döndü; kendi başlatılan önizleme sunucusu durduruldu. Yeni kaynak/konsol/birleşik paket boyutu ve SHA256 değerleri dış teslim manifestinde gerçek arşivlerden hesaplanır; eski hash yeni teslimata taşınmaz.

Bu kayıtlar sınırlı elle ürün gözlemleridir; otomatik test veya canlı kabul değildir. Önceki Phase7 kayıtları kendi teslimlerine aittir. Testler, canlı API/token/IdP/PG, yönetim/Windows ve native print/PDF işleri bekletilmeye devam eder. Önceki PDF kaydedilmeme ve native baskı önizlemesine erişilememe kaydı değişmez. Backend/HBF/wheel, yetki yüzeyi, tarihsel test sayıları ve revision kapıları genişletilmez.
