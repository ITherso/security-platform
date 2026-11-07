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
