# Tehdit modeli ve kalan riskler

V1'in koruduğu varlıklar tenant üyeliği, cihaz kimliği, son ürün durumu, cihazın kendi beyanı olan süreç ve sensör olayları, kayıt hakkı, credential digest'leri ve sınırlı audit'tir. Kimliğin doğrulanması cihazın dürüst veya güvenli olduğunu, rapor üreticisini, bildirdiği olayları veya canlı firewall kararını kanıtlamaz. Fiziksel cihaz attestation'ı ve merkezden müdahale bu sürümde yoktur.

## Aktörler ve güven sınırları

| Aktör | Yetki ve sınır |
|---|---|
| Tenant viewer | Kendi güncel üyeliğindeki cihaz/ürün durumunu okur. |
| Tenant admin | Kendi tenant'ında grant, iptal ve audit; başka tenant yetkisi token claim'inden türemez. |
| Enrollment grant sahibi | Süresi içinde tek cihaz kaydı; operatör veya snapshot yetkisi yoktur. |
| Cihaz bearer sahibi | Tek cihazın snapshot'ı, olay batch'leri ve credential rotasyonu. Bearer çalınırsa cihaz adına beyan ve olay üretilebilir. |
| Yerel yönetici/migration hesabı | Tenant/üyelik ve şema yönetimi; web runtime hesabından ayrıdır. |
| DB yöneticisi veya ele geçirilmiş sunucu | DB ve uygulama tenant sınırını değiştirebilir; bu aktöre karşı kriptografik izolasyon/değişmezlik yoktur. |

## Tehdit, kontrol ve artık risk

| Tehdit | Uygulanan kontrol | Artık risk / kabul sınırı |
|---|---|---|
| Tenant ID/UUID tahmini, başka şirket nesnesi | Güncel `(issuer, subject)` üyeliği, sorgularda zorunlu tenant kapsamı, birleşik FK ve tutarlı yabancı nesne 404 | RLS uygulanmış olduğu iddia edilmez. Runtime DB anahtarı veya sunucu ele geçirilirse SQL ile birden fazla tenant'a erişilebilir. |
| Token'da sahte admin/tenant/e-posta | Yetki token claim'inden değil DB üyeliğinden gelir; üyelik iptali yeni istekte uygulanır | IdP subject/issuer güvenilir olmalıdır. IdP'nin kendisi veya imza anahtarı ele geçirilirse bu sınır aşılabilir. |
| ID token/algoritma karışıklığı | Sabit RS256, API audience/issuer, at+jwt türü, mandatory claim ve zaman doğrulaması | Yalnız belgelenen dar profil desteklenir; üretim sağlayıcısı kurulmuş/doğrulanmış değildir. |
| JWKS URL'siyle SSRF/anahtar değiştirme | Sabit public dosya, kapalı key seçimi; jku/x5u/jwk/crit reddi, ağ discovery yok | Public dosyanın güvenilir yönetim/izinleri dağıtım sorumluluğudur. Anahtar rotasyonu restart ister. |
| Grant veya credential tekrar kullanımı | Yüksek entropili opaque sır, digest-only DB, süre/iptal ve transaction içi yeniden kontrol | Bearer kopyalanırsa iptale/süre bitimine kadar yetki verir; donanım kimliği değildir. |
| Paralel enrollment/rotasyon/iptal yarışı | Tenant/cihaz/credential row lock, tek commit, mutation ve audit atomikliği | Commit öncesinde başlamış tüm fiziksel ağ eylemleri geri alınamaz. Kaybolan enrollment/rotation cevabı yeni kayıt gerektirebilir. |
| Eski veya değişmiş snapshot | Strict DTO, kanonik digest, son sıra/UUID karşılaştırması ve atomik tam değişim | Retry penceresi yalnız son mesajdır; sınırsız tarihsel UUID deposu yoktur. Yetkili ama kötü niyetli cihaz daha yüksek sırayla yalan durum bildirebilir. |
| Gelecek cihaz saati veya tekrar ile sahte online | Sunucu `received_at`, tekrarın aynı cevabı koruması, kaynak yaşı/future durumunun ayrılması | Kaynağın kendi saat doğruluğu doğrulanmaz. Recent bağlantı, sağlıklı koruma demek değildir. |
| Sahte, eksik veya oynanmış olay | Olay yalnız kimliği doğrulanmış cihazdan alınır; tenant ve cihaz yalnız credential'dan gelir. Her olay `self_reported`/`not_verified` kalır, sunucu bunu yükseltmez. Saklama ve tazelik kararını cihaz saati değil sunucu `received_at` verir | Kimliği doğrulanmış ama kötü niyetli veya ele geçirilmiş bir cihaz sahte olay gönderebilir, olay atlayabilir, `event_seq` boşluğu bırakabilir ve `observed_at` saatini istediği gibi yazabilir. Olaylar kanıt değil, cihazın beyanıdır. Olay alımı cihazı `recent` göstermez. |
| Olayla kişisel veri sızıntısı | Kapalı sözleşme: komut satırı, kullanıcı adı/SID, dosya içeriği/özeti, ağ verisi veya serbest metin alanı yoktur. `Users` bileşeninden sonraki bileşenin ilk `:` işaretinden önceki adının `*` olması zorunludur; maskelenmemiş yol 422 ile reddedilir | Maskeleme bir sözleşme kuralıdır, DLP değildir. Yalnız bütünüyle `Users` olan bileşenden hemen sonraki ad (ilk `:` öncesi) ASCII büyük/küçük harf duyarsız denetlenir. Doğrudan `Users` altındaki dosyanın adı da `*` olur; NTFS akış adı (`\Users\*:payload.exe`) tespit için korunur ve kişisel bilgi taşıyabilir. Klasör veya dosya adlarındaki kişisel bilgi, profil dışı konumlar (ör. `D:\ahmet\araç.exe`), Win32'nin eşdeğer saydığı başka yazımlar (sondaki nokta/boşluk, `Users::$INDEX_ALLOCATION` gibi akış nitelikli dizin yazımları, ASCII olmayan büyük/küçük harf eşdeğerleri) ve maskeyi uygulamayan kötü niyetli bir ajan tanınmaz. |
| Olay seliyle depolama tüketimi | 16 KiB/2048 düğüm gövde, batch başına 200 olay, olay başına 4 KiB saklanan metin, süreç/IP başına dakikada 120 istek, cihaz başına satır üst sınırı (`SP_MAX_EVENTS_PER_DEVICE`, varsayılan 250000) ve sınırın sildiği satırların cihaz imlecindeki sayacı (`cap_deleted_events`), tenant başına gün tabanlı saklama | Zamana göre saklama yalnız `events prune` zamanlanırsa uygulanır. Üst sınır dolunca cihazın en eski olayları silinir. Bunu yalnız kötü niyetli bir cihaz değil, dürüst bir ajan üzerinden yetkisiz yerel bir kullanıcı da tetikleyebilir: kısa ömürlü süreç seli (ör. bir `cmd /c exit` döngüsü) sunucudaki eski geçmişi dışarı iter. Bu silme `cap_deleted_events` ile görünür (zaman çizelgesi cevabında döner) ve uyarı kurallarıyla birlikte (Aşama 2, 4. adım) yeniden değerlendirilir. Çok sayıda cihaz toplam depolamayı yine büyütür. |
| Olay tekrarı veya sıra bozma | Cihaz başına imleç, kanonik içerik özeti, tam tekrarın saklanan aynı cevabı alması, diğer çakışmaların 409 olması, (tenant, cihaz, `event_seq`) birincil anahtarı | Tekrar penceresi yalnız son batch'tir. Kötü niyetli cihaz daha yüksek sırayla yeni olay uydurabilir. |
| Ham rapor/kanıt/hedef veya hata sızıntısı | Kapalı DTO, saf sayısal mapper, sabit hata kodları, access log kapalı, audit'te sınırlı alanlar | Görünen ad/etiket kullanıcı beyanıdır. Log/DB yöneticisi ve uygulama dışı debug/trace ayarları ayrı sorumluluktur. Testlerde canary kapsamı doğrulanır; her olası gizli verinin otomatik tanınması iddia edilmez. |
| Ağ MITM, sahte proxy header veya redirect | HTTPS, CLI'da proxy_headers=False, istemcide verify=True/trust_env=False/redirect kapalı, yanlış sertifika reddi | Üretim sertifika/IdP işletimi bu yerel fixture kabulüyle tamamlanmaz. CLI özel CA bayrağı sunmaz; fixture CA test bağlamı programatik ve doğrulamalıdır. |
| Büyük/yavaş/tekrarlı JSON ve istek baskısı | 16 KiB gerçek byte sınırı, chunk/depth/node/time sınırı, strict tip, süreç/IP bütçesi | Dağıtık DDoS, çok worker arasında ortak rate state ve ağ katmanı kapasitesi çözülmüş değildir. |
| Audit değişimi veya sınırsız geçmiş | Başarılı mutasyonla aynı transaction; tenant'a göre bounded retention; runtime UPDATE yok | Runtime DELETE retention için vardır. Ele geçirilmiş runtime DB credential'ı audit silebilir; DB yöneticisine karşı imzalı/değişmez kayıt yoktur. |
| İstemci sır/state dosyasını başka kullanıcının değiştirmesi | Windows native owner/DACL veya POSIX owner/mode, parent/reparse/hardlink denetimi, özel dosyada atomik yazma ve yerel kilit | Mevcut kullanıcının hesabı, yönetici veya SYSTEM ele geçirilirse sırlar/state korunamaz. Uygun private path sağlamak gerekir. |
| Merkez kesilmesinin yerel korumayı değiştirmesi | Ayrı proje, saf mapper, açık tek sender; firewall runtime/config yazımı yok | Kesinti testi fixture sender ve dosya bütünlüğünü kapsar. Canlı Windows enforcement kesintisi ayrıca denenmemiştir. |

## İşletim kararları

Üretim varsayılanı TLS'dir. HTTP yalnız açık test ayarı, loopback istemci ve loopback Host birlikteyse kabul edilir; auth kapanmaz. CORS veya Host tek başına tenant yetkisi sayılmaz. Uvicorn doğrudan TLS girişinde trusted proxy header'ı kabul etmez. Bir reverse proxy kullanılacaksa yeni güven sınırı ayrıca tasarlanmalıdır; bu paketin varsayılanını sessizce değiştirmeyin.

Operatör token ömrü en fazla bir saat ve 30 saniye toleranstır. Token `jti` değeri zorunludur, fakat bu servis insan token'ları için merkezi IdP logout/revocation listesi uygulamaz. Yerel üyelik iptali DB'de hemen yetkiyi kapatır; IdP token süresinin ve anahtar rotasyonunun işletimi ayrıca gerekir.

Zamana göre olay saklaması operatörün günlük zamanlayacağı `events prune` komutuna bağlıdır; komut yalnız runtime hesabıyla çalışır ve owner bağlantısını reddeder. Çalıştırılmazsa yalnız cihaz başına üst sınır korur.

DB runtime startup kontrolü superuser/CREATEDB/CREATEROLE/BYPASSRLS, tablo/sistem şema sahipliği ve etkin ayrıcalıklı role geçiş yollarını reddeder. Migration credential'ı web ortamına taşınmamalıdır. PostgreSQL fixture'ın bootstrap hesabı yalnız sahip olunan küme içindir; superuser testlerini runtime izolasyonu kanıtı saymayın.

DB credential'ları, operator access token, grant, device secret, client state ve TLS özel anahtarları kaynak paketine girmez. İstemci sırları argv, URL veya normal stdout'a yazılmaz. Grant/credential'ın başarılı cevabında bir defa verilmesi zorunlu istisnadır; bu cevapları kullanıcı veya araç ayrıca loglamamalıdır.

## Bu kabulün dışında kalanlar

- Üretim IdP bağlantısı, gerçek kullanıcı giriş deneyimi, gerçek sertifika dağıtımı ve anahtar yönetimi.
- Fiziksel Windows filosu, mTLS/TPM/attestation, kötü amaçlı cihaz beyanının tespiti.
- Canlı WinDivert/SCM/UAC/reboot, VPN/uyku ve 24–72 saat yerel kabul.
- Merkezî politika uygulama, shell/izolasyon, scanner yürütme, antivirüs motoru ve lisanslama.
- Olayların doğruluğunun kanıtlanması, uyarı kuralları ve konsolun olay görünümleri (sonraki Aşama 2 adımları).
- DB backup/restore ve felaket kurtarmanın üretim tatbikatı; HA/çok worker dağıtık limitler.

Bir sonraki çalışma kapısı yalnız sürümlü politika önizleme ve kontrollü dağıtım sözleşmesidir. Komut yetkisi eklenmeden önce bu kimlik/tenant kabulü ve açık yerel Windows maddeleri tekrar değerlendirilmelidir.
