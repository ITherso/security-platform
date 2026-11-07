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
- [İki cihazın bildirimlerini karşılaştırma](docs/DEVICE_COMPARISON.tr.md)
- [Türkçe/İngilizce yerelleştirme](docs/LOCALIZATION.tr.md)
- [English quick start](docs/QUICKSTART.en.md)
- [Teslim, build ve elle önizleme kaydı](docs/DELIVERY.tr.md)

Kullanıcı yönlendirmesiyle bu tur test yazılmaz veya çalıştırılmaz. Eski **506 passed / 2 skipped** yalnız tarihsel temeldir; yeni UI sonucu değildir. Windows vakaları, IdP/canlı API ve gerçek policy revision otoritesi beklemede kalır.

Runtime dependency notices are retained in THIRD_PARTY_NOTICES.txt and in the built JavaScript license comment.

Durum raporu, yalnız açılıp görüntülenen ayrıntılardan en fazla 20 cihaz/256 KiB UTF-8 bellek taslağı hazırlar. Aynı cihazın güncellenmesi açık eylemdir; bağlam değişince taslak temizlenir. Ad/kimlik gösterme varsayılan kapalıdır. Çıktı tarayıcı yazdır/PDF akışıdır; yeni fetch/export servisi, otomatik kayıt veya PDF tamamlanma iddiası yoktur. Bu rapor tüm kurum envanteri veya doğrulanmış güvenlik durumu değildir.

Üst çubuktan Türkçe/English seçilebilir; ilk açılış Türkçe ve tercih yalnız sayfa belleğindedir. Dil değişimi veri/bağlantı bağlamını, arama/filtre/sayfayı veya taslağı değiştirmez ve istek yapmaz. Yalnız hazır rapor önizlemesi geçersizleşir; yeni önizleme kendi dilini sabitler. Tarih/sayı sunumu tr-TR/en-GB ve her iki dilde UTC'dir. Veri adları, kimlikler, durum kodları ve güven anlamları çevrilmez/değiştirilmez. Yeni native printpreview/PDF veya test kabulü iddia edilmez.

Cihaz ayrıntısındaki önceki/sonraki geçişi yalnız mevcut sayfanın görüntülenen, filtrelenmiş ve sıralanmış cihazlarını kapsar. İlk/son kayıtta durur; başa sarmaz, komşuyu önceden okumaz veya başka sayfa çekmez. Seçilen komşunun ayrıntısı mevcut GET ile kullanıcı eylemi üzerine okunur. Pencere kapanınca liste araması/filtre/sıralama/sayfa korunur; dil değişimi hedef cihazı değiştirmez. Geçiş rapora otomatik ekleme veya güncelleme yapmaz.

Karşılaştırma, yalnız ayrıntısı açılmış iki cihazın sabit kopyasını tutar: en fazla 32 KiB/kayıt ve 64 KiB toplam. Üçüncü cihaz için taraf değiştirme, mevcut kopyayı yenileme ve temizleme açık eylemlerdir; normal gezinti/dil seçimi korur, kaynak/erişim bağlamı değişimi temizler. Eksik/unknown “aynı” sayılmaz; kapsamı kanıtlanmayan Termivar sayıları karşılaştırılamaz. Bu görünüm gerçek koruma eşdeğerliği/skor veya yeni istek/export/rapor otomasyonu değildir.
