# Operatör konsolu

[Güvenlik Konsolu](../operator-console/README.md), mevcut envanter API'si için bağımsız React + TypeScript + Vite frontend'idir. Kaynaklar `operator-console/`, statik build `operator-console/dist/` altındadır. Backend, HTTP/auth/rol/credential, DB/Alembic, HBF, sender, policy core/revision laboratuvarı ve üretim wheel yüzeyleri bu çalışmanın dışında tutulur.

İlk açılışta kalıcı **“Örnek veri — gerçek cihazlara bağlı değil”** etiketi vardır. Kurgusal iki tenant, raporlu/raporsuz/eski/eksik ürünlü cihazlar ve örnek audit aynı DTO normalizasyonundan geçer. Normal/boş/hata örnek senaryoları ürün gezinmesi içindir; gerçek auth veya güvenlik kabulü kanıtı değildir. Örnek kip platforma bağlanmaz; CDN/font/analitik/telemetri veya token keşfi yoktur.

Genel görünüm, yalnız yüklenen sayfanın cihaz/veri durumlarını özetler. Arama/sıralama/filtre ve sayfalama yüklenen kayıt sınırını korur. Ayrıntı ürün state'lerini ayrı gösterir; API'nin sağlamadığı filo toplamı, güvenlik skoru, koruma yüzdesi veya tehdit grafiği üretilmez. Audit güncel tenant_admin üyeliği gerektirir; arayüz rol seçicisi yetki vermez.

## Çalıştırma

Node **24.22.1**, pnpm **11.25.0**, `pnpm-lock.yaml`:

```powershell
cd .\operator-console
pnpm install --frozen-lockfile --ignore-scripts
pnpm typecheck
pnpm build
..\.venv\Scripts\python.exe .\serve.py --port 8787
```

Statik yerel önizleme yalnız `http://127.0.0.1:8787/` üzerinde örnek veri sunar; API proxy'si değildir. `pnpm dev` ve `pnpm preview` loopback/strict port/CORS kapalı/proxy'siz kalır. Önceki buildless dosya kopyalama akışı React/Vite build kanıtı değildir. Gerçekleşen kurulum/build/typecheck ve yeni elle önizleme sonuçları [DELIVERY](../operator-console/docs/DELIVERY.tr.md) içinde ayrı tutulur.

## Mevcut API'ye sonraki açık bağlantı

Adapter yalnız dört operatör GET'ini uygular: erişilebilir tenant'lar, tenant cihaz listesi, cihaz ayrıntısı ve tenant audit'i. Mevcut API'nin toplam 14 operation'ı korunur; mutation/device/operasyon yolları UI adapter'ına eklenmez. Konsol iki olay yolunu (`POST /api/v1/device/events` ve `GET /api/v1/tenants/{tenant_id}/devices/{device_id}/events`) henüz kullanmaz. Olaylarla ilgili tek konsol değişikliği audit görünümündedir: yerel `set-event-retention` komutunun yazdığı `tenant_event_retention_set` eylemini tanır ve etiketler. Gerçek alan ve rol eşlemesi [API_UI_MAPPING](../operator-console/docs/API_UI_MAPPING.tr.md) belgesindedir.

Bağlantı paneli login/SSO değildir. API adresi ve dışarıdan sağlanan mevcut operatör access token, ayrı Bağlan eylemiyle kullanılabilir. Hedef sayfanın aynı HTTPS origin'indeki sabit `/api/v1` tabanıdır; userinfo/query/fragment, keyfî origin veya path kabul edilmez. Token yalnız açık sayfanın belleğindedir; bağlanınca giriş alanı temizlenir. URL, cookie, localStorage/sessionStorage/IndexedDB, env/build, log ve dışa aktarım token deposu değildir. Bağlantı/kip/adres/token değişimi özel veriyi ve eski istekleri temizler; sayfa yenilenince canlı oturum geri kurulmaz.

Token'dan rol/tenant yetkisi çıkarılmaz. Mevcut API güncel üyeliği her istekte denetler; GET adapter'ı bearer'ın gerçek yetkilerini daraltmaz. 401 özel veriyi ve bağlantıyı temizler; 403 ilgili görünümde erişim reddidir. Hata boş listeye veya sağlıklı duruma çevrilmez; canlı hatada örnek kayda sessiz dönüş yapılmaz.

GET isteklerinde `credentials:omit`, `cache:no-store`, `redirect:error`, açık Authorization, **512 KiB** yanıt ve fetch+gövde için **12 saniye** sınırı vardır. Runtime DTO denetimi ve safe-integer sınırı korunur; BIGINT sayılar yuvarlanmaz. Eski istekler bağlam/istek kimliğiyle yeni tenant/görünüme yazamaz. Ürün verisi için polling/focus-refresh/websocket/prefetch/otomatik retry yoktur. React düz metin render eder; rapor HTML'i veya haricî link önizlemesi eklenmez.

## Dağıtım ve ürün anlamı

Dağıtım yöneticisi Vite `dist/` statik varlıklarını mevcut HTTPS reverse proxy üzerinden aynı origin'de sunabilir. API yolları mevcut uygulamaya gitmeye devam eder. Yeni backend route/CORS izni, kimlik atlayan proxy veya TLS gevşetmesi eklenmez; self CSP/no-store/nosniff/no-referrer/framing sınırı korunur. Geliştirme sunucusu üretim sunumu değildir; bu belge public deploy yapıldığını söylemez.

Erişim, alım tazeliği, kaynak zamanı ve ürün çalışma beyanı bağımsız bilgilerdir. `self_reported/not_verified` başarılı TLS ile yükselmez. Termivar özeti scanner çalışması/merkezden tarama kanıtı değildir. AV planned/unavailable kullanıma hazır ürün değildir. Snapshot sequence veya legacy hash policy CAS/applied/verified kanıtı olmaz. Ayrıntılar [PRODUCT_STATES](../operator-console/docs/PRODUCT_STATES.tr.md) içinde açıklanır.

## Doğrulama durumu

Adapter uygulanması **gerçek API bağlantısı kabulü değildir**. Bu tur gerçek token aranmaz/üretilmez, IdP/backend başlatılmaz ve canlı bağlantı denenmez. Kullanıcı yönlendirmesiyle test dosyası/runner eklenmez veya çalıştırılmaz. Eski **506 passed / 2 skipped** yalnız tarihsel backend/laboratuvar kaydıdır; yeni UI sonucu değildir. Windows 12 vaka NOT_RUN ve önceki symlink SKIP devam eder. Yeni build/typecheck ve varsa gerçek örnek ekran görüntüleri test/canlı kabulden ayrı raporlanır.
