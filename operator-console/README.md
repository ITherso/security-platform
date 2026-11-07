# Güvenlik Konsolu

Mevcut merkezî envanter API'si için bağımsız, salt okunur React + TypeScript + Vite frontend'i. İlk açılış her zaman **“Örnek veri — gerçek cihazlara bağlı değil”** kipindedir. API bağlantı adapter'ı yalnız mevcut tenant/cihaz/liste/ayrıntı/audit GET sözleşmelerini kullanır; **gerçek API bağlantı kabulü bu turda yapılmaz**.

Node **24.22.1**, pnpm **11.25.0** ve `pnpm-lock.yaml` kullanılır. Platform kökünden:

```powershell
cd .\operator-console
pnpm install --frozen-lockfile --ignore-scripts
pnpm typecheck
pnpm build
..\.venv\Scripts\python.exe .\serve.py --port 8787
```

Yerel production-build önizlemesi `http://127.0.0.1:8787/` adresindedir; yalnız örnek veri içindir. `pnpm dev` / `pnpm preview` da loopback, strict port, CORS kapalı ve proxy'siz yapılandırılır. `Ctrl+C` ile kapatın. Sunucuyu yeniden build sonrası yeniden başlatın. Kurulum/typecheck/build'in gerçekleşen sonucu [teslim kaydında](docs/DELIVERY.tr.md) ayrıca belirtilir; bu komut listesi test veya canlı kabul sonucu değildir.

Sonraki açık yapılandırmada canlı bağlantı yalnız sayfanın aynı HTTPS origin'indeki `/api/v1` tabanına, dışarıdan sağlanan mevcut operatör access token ve ayrı Bağlan eylemiyle yapılabilir. Panel login/SSO/token üretme servisi değildir. Token yalnız sayfa belleğinde tutulur; hiçbir kalıcı tarayıcı deposuna, URL'ye veya build ortamına yazılmaz. Yanıtlar 512 KiB/12 saniye ile sınırlıdır; runtime DTO ve safe-integer denetimi uyumsuz veriyi açık hata yapar.

Kayıt/iptal, credential/snapshot, policy push/apply, scan, uzaktan komut veya enforcement eylemi yoktur. UI GET sınırlaması bearer'ın sunucudaki yetkilerini daraltmaz; tenant/rol kararı mevcut API'nindir. Planlanan AV etkin ürün değildir; self_reported/not_verified korunur.

- [Kurulum ve bağlantı](docs/SETUP.tr.md)
- [Gerçek API–UI eşlemesi](docs/API_UI_MAPPING.tr.md)
- [Ürün durumlarının anlamı](docs/PRODUCT_STATES.tr.md)
- [Seçili cihazlar — ürün bildirim özeti](docs/REPORTS.tr.md)
- [Teslim, build ve elle önizleme kaydı](docs/DELIVERY.tr.md)

Kullanıcı yönlendirmesiyle bu tur test yazılmaz veya çalıştırılmaz. Eski **506 passed / 2 skipped** yalnız tarihsel temeldir; yeni UI sonucu değildir. Windows vakaları, IdP/canlı API ve gerçek policy revision otoritesi beklemede kalır.

Runtime dependency notices are retained in THIRD_PARTY_NOTICES.txt and in the built JavaScript license comment.

Durum raporu, yalnız açılıp görüntülenen ayrıntılardan en fazla 20 cihaz/256 KiB UTF-8 bellek taslağı hazırlar. Aynı cihazın güncellenmesi açık eylemdir; bağlam değişince taslak temizlenir. Ad/kimlik gösterme varsayılan kapalıdır. Çıktı tarayıcı yazdır/PDF akışıdır; yeni fetch/export servisi, otomatik kayıt veya PDF tamamlanma iddiası yoktur. Bu rapor tüm kurum envanteri veya doğrulanmış güvenlik durumu değildir.
