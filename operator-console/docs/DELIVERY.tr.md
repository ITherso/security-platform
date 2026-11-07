# Operatör konsolu teslim kaydı

React + TypeScript + Vite ile bağımsız, Türkçe ve salt okunur frontend tamamlandı. İlk açılış açıkça örnek veridir. Gerçek API adapter'ı mevcut dört GET'e bağlıdır; gerçek bağlantı kabulü yapılmadı.

## Kaynak ve paket kimliği

Korunan backend temeli `f2400c3744937b0a82bbba63c77f274721f8d61b`; değişmeyen HBF `74a88ed336cb8a0a2fab16e20389c9410590c292` sürüm 1.4.3'tür. Bu tur yalnız `operator-console/**`, ana README ve konsol belgesini değiştirir. Backend, auth/rol/credential, DB/Alembic, sender/snapshot, policy core, revision laboratuvarı ve üretim wheel'i korunur.

Yeni commit, kaynak ZIP boyutu/SHA256 ve tam dosya farkı dış `delivery-manifest.json` ile `evidence/operator-console/platform-console-changes.patch` içinde kaydedilir. Arşivin kendi hash'i kaynağa gömülmez. Eski phase4 birleşik paket 1.458.787 bayt / `196fe6b3f79eaeb7a19550c83ebed2205c5bd6484f1b01943f1b516f1b78564e` kimliğiyle ayrı korunur; bu hash yeni teslimatı tanımlamaz.

## Derleme/typecheck

7 Kasım 2026'da Node **24.22.1**, pnpm **11.25.0** kullanıldı. Kilitli kurulum `pnpm install --frozen-lockfile --ignore-scripts` tamamlandı. `pnpm typecheck` ve `pnpm build` başarıyla tamamlandı. Script'ler yalnız Vite, TypeScript ve statik manifest üretir; test/coverage/pytest/Playwright/Vitest başlatmaz.

Üretim build'i üç dosyadır: `index.html`, `assets/console.js`, `assets/console.css`. `dist/build-manifest.json`, gerçek boyut/SHA256 değerlerini ve varlık kümesi özetini taşır. Son varlık kümesi SHA256:

`ec564e510ca0003c2dc500686ddeeb840fb4726d773d5057a54da5ff5c867029`

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
