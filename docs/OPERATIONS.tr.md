# Yerel PostgreSQL ve işletim sınırı

Merkezî hizmetin PostgreSQL veritabanı mevcut HostBasedFirewall çalışma alanından ayrıdır. `scripts/managed_postgres.py`, yalnız bu çalışma alanına ait taşınabilir test kümesini başlatır, durumunu doğrular, uygulama haklarını verir ve durdurur. Windows servisi kurmaz, yönetici hesabı istemez veya firewall/proxy/işletim sistemi güvenlik ilkesi değiştirmez. Uygulamanın kimlik doğrulamasını kapatmaz.

Bu Windows ortamında Docker bulunmadığından tekrarlanabilir kabul yolu taşınabilir PostgreSQL'dir. Docker tabanlı alternatif bu oturumda doğrulanmadı.

## Bağımlılık ve dosya yerleşimi

PostgreSQL 18.6 Windows x64 ikilileri resmî [EDB dağıtım adresinden](https://get.enterprisedb.com/postgresql/postgresql-18.6-1-windows-x64-binaries.zip) alınmıştır. İndirilen dosyanın bu çalışmadaki yerel SHA256 değeri:

```text
fbe23da234ee31547bf8a36d29dfd81e82b849df2d2b78d2eecb43d360252f8c
```

`postgres.exe --version` çıktısı `postgres (PostgreSQL) 18.6` olarak doğrulandı. Bu yerel hash ve sürüm kontrolü, bağımsız yayımlanmış imza veya yayıncı attestation doğrulaması olarak sunulmaz. Arşiv/ikili dosyalar kaynak paketine eklenmez. Windows Uygulama Denetimi çalıştırmayı engellerse araç hata verir; ilke kapatma veya engeli aşma yolu eklenmez.

Beklenen yerleşim, `security-platform` klasörünün bir üst dizinindeki `.tooling` altındadır:

```text
.tooling/postgresql-18.6/pgsql/bin/initdb.exe
.tooling/postgresql-18.6/pgsql/bin/pg_ctl.exe
.tooling/postgresql-18.6/pgsql/bin/postgres.exe
.tooling/test-pg-data-<rastgele kimlik>/
.tooling/platform-test-private/
.tooling/platform-test-env.json
```

Küme adı rastgele üretilir. Veri ve kimlik dosyaları reparse/symlink kontrolünden geçer; araç başka bir cluster yolunu veya uzak bağlantı adresini kabul etmez. `status` ve `stop`, bağlantı kurulan sunucunun gerçek veri dizinini özel bootstrap hesabıyla doğrular. Runtime hesabına `data_directory` gibi ayrıcalıklı ayarları okuma yetkisi verilmez.

## Başlatma, migration ve haklar

Komutlar `security-platform` kökünde, proje bağımlılıklarının kurulu olduğu ortamda çalıştırılır:

```powershell
./.venv/Scripts/python.exe scripts/managed_postgres.py start
./.venv/Scripts/python.exe scripts/managed_postgres.py status
```

Araç yalnız `127.0.0.1` üzerinde boş bir port seçer. `--port 55439` gibi açık bir port da verilebilir; kullanımda olan porta veya yabancı sunucuya bağlanıp onu sahiplenmez. `initdb` yerel/host kimlik doğrulamasını `scram-sha-256` olarak kurar; ağ HBA kuralı yalnız IPv4 loopback'i kabul eder. Bu yerel DB fixture'ı için TLS açılmaz. Uygulamanın üretim HTTPS ve operatör token doğrulama kuralları ayrı kalır.

Sırlar argv veya stdout'a yazılmaz. `initdb` parolayı korunan dosyadan, SQL rol kurulumu bellekteki sürücü bağlantısından alır. `.tooling/platform-test-env.json`, mevcut kullanıcı/SYSTEM/Administrators erişimiyle korunan yerel dosyadır. `migration_url`, `runtime_url`, `SP_MIGRATION_DATABASE_URL`, `SP_DATABASE_URL` ve `ready` alanları içerir. İçeriğini yazdırmayın, hata raporuna veya kaynak deposuna eklemeyin. `ready=true` ve `status` başarılı olmadan bağımlı test başlatmayın.

PowerShell'de dosyayı içeriğini göstermeden okumak için:

```powershell
$fixtureConfig = Get-Content -LiteralPath ../.tooling/platform-test-env.json -Raw | ConvertFrom-Json
if (-not $fixtureConfig.ready) { throw 'PostgreSQL fixture hazır değil' }
$env:SP_MIGRATION_DATABASE_URL = $fixtureConfig.migration_url
$env:SP_DATABASE_URL = $fixtureConfig.runtime_url
./.venv/Scripts/python.exe -m alembic upgrade head
./.venv/Scripts/python.exe scripts/managed_postgres.py grant
```

`SP_MIGRATION_DATABASE_URL` yalnız migration ve korunan yerel yönetim CLI'ının owner hesabını seçer. Uygulama sunucusu ayrı `SP_DATABASE_URL` runtime hesabıyla başlatılır; owner hesabı web hizmetinin bağlantı hesabı yapılmaz. Operatör issuer, audience, public JWKS dosyası ve host/TLS ayarları ayrıca yapılandırılmalıdır; `.env.example` bu yüzden eksik bırakılmıştır.

Kurulu wheel kullanılıyorsa `security-platform migrate` veya `python -m security_platform.cli migrate` aynı migration kaynaklarını kurulum prefix'inin `share/security-platform` dizininden bulur. Editable source ağacı da desteklenir. Wheel kaynakları, kurulu kod import'u ve gerçek PostgreSQL CLI migration yolu `reports/wheel-acceptance.json` ile ayrıca doğrulandı; bu bir yayın işlemi değildir.

Olay ve uyarı tabloları doluyken `0005_stage3_detection` migration'ı bu iki tabloyu baştan sona okur ve bitene kadar kilitler. Bu migration'ı aşağıdaki "Dolu veritabanında migration (0005) ve geri dönüş" bölümündeki sırayla çalıştırın.

Gerçek sağlayıcının bu API için ürettiği erişim token'ları ve onun public JWKS dosyası yapılandırıldıktan sonra yerel deneme şu şekilde açılabilir:

```powershell
$env:SP_OPERATOR_ISSUER = 'https://your-trusted-issuer.example'
$env:SP_OPERATOR_AUDIENCE = 'your-security-platform-api'
$env:SP_JWKS_FILE = (Resolve-Path './secrets/operator-jwks.json').Path
$env:SP_ALLOWED_HOSTS = '127.0.0.1,localhost'
$env:SP_ALLOW_LOOPBACK_HTTP = 'true'
./.venv/Scripts/python.exe -m security_platform.cli serve --host 127.0.0.1 --port 8091
```

Issuer/audience örnek değerleri gerçek sağlayıcı bilgileriyle değiştirilmelidir. Public JWKS dosyası operatör imzalarını doğrulamak içindir; özel anahtar veya token değildir. CLI `access_log=False` ve `proxy_headers=False` kullanır. `SP_ALLOW_LOOPBACK_HTTP=true` yalnız açık yerel test istisnasıdır; auth ve tenant denetimleri devam eder. Üretimde aynı CLI'a `--ssl-certfile` ve `--ssl-keyfile` verilir, HTTP istisnası kapalı tutulur ve gerçek Host sınırı belirlenir. Test issuer anahtarları üretim kimlik sağlayıcısı olarak sunulmaz.

## Hesaplar ve DB yetkileri

| Hesap | Kapsam |
|---|---|
| `sp_test_bootstrap` | Yalnız sahip olunan taşınabilir kümenin ilk DB/rol kurulumu ve kontrolü. Özel parola dosyası uygulama ayarlarına taşınmaz. Bu test kümesinde superuser'dır; runtime/RLS kanıtı olarak kullanılmaz. |
| `sp_migration` | Uygulama DB'si, `public` şeması ve migration tablolarının sahibi. Login vardır; superuser, CREATEDB, CREATEROLE, BYPASSRLS veya replication yetkisi yoktur. |
| `sp_runtime` | Ayrı login; şema/tablo sahibi değildir. Superuser, CREATEDB, CREATEROLE, BYPASSRLS, replication, rol üyeliği veya şema CREATE yetkisi yoktur. `NOINHERIT` kullanır. |

Runtime hakları mevcut tablo sözleşmesine göre açıkça verilir:

| Tablo | Runtime hakkı |
|---|---|
| `tenants` | SELECT; kota işlemlerindeki satır kilidi için yalnız `UPDATE(id)` |
| `principals`, `memberships`, `alembic_version` | SELECT |
| `enrollment_grants`, `device_credentials`, `product_states` | SELECT, INSERT, UPDATE, DELETE |
| `devices` | SELECT, INSERT, UPDATE |
| `audit_events` | SELECT, INSERT, DELETE; UPDATE verilmez |
| `endpoint_events` | SELECT, INSERT, DELETE; UPDATE verilmez |
| `device_event_cursors` | SELECT, INSERT, UPDATE (imleç satır kilidi dahil); DELETE verilmez |
| `alerts` | SELECT, INSERT, UPDATE (alışta açma ve güncelleme, onaylama/kapatma satır kilidi dahil), DELETE (yalnız `alerts prune`) |

Olay satırlarındaki DELETE yalnız alış sırasındaki cihaz başına üst sınır ve `events prune` saklaması içindir; olay satırı güncellenemez. Uyarı satırlarındaki DELETE (0006'dan beri) yalnız `alerts prune` saklaması içindir; `events prune` uyarılara dokunmaz. Runtime hesabı tenant'ın `event_retention_days` ve `alert_retention_days` değerlerini değiştiremez (`tenants` üzerinde yalnız `UPDATE(id)` vardır).

Audit DELETE yalnız uygulamanın tenant'a göre sınırlandırdığı eski kayıt temizliği için kullanılır; genel audit değiştirme/silme endpointi yoktur. Runtime DB credential'ının ele geçirilmesi, saldırganın SQL üzerinden audit kayıtlarını silmesine izin verebilir. Bu tasarım DB credential'ına veya DB yöneticisine karşı değişmez/kriptografik audit sağlamaz. Tenant sorgu kapsamı ve birleşik foreign key'ler ayrıca gerçek PostgreSQL üzerinde test edilir; mevcut uygulama RLS kullandığını iddia etmez.

Migration sonrasında `grant` yeniden çalıştırılır. Araç tabloların migration hesabına ait olduğunu ve beklenen tablo kümesinin mevcut olduğunu denetler; bütün tablolara geniş `ALL` yetkisi vermez. Yeni migration yeni runtime ihtiyacı eklerse grant sözleşmesi ayrıca incelenmelidir. `0002_endpoint_events` migration'ı `endpoint_events` ve `device_event_cursors` tablolarını ve `tenants.event_retention_days` sütununu ekler; bu migration'dan sonra `grant` çalıştırılmadan olay uç noktaları runtime hesabıyla çalışmaz (503). `0003_alerts` migration'ı `alerts` tablosunu ve `device_event_cursors.suppressed_alerts` sütununu (mevcut imleçlerde 0) ekler. Kurallar olay alımının içinde çalıştığı için bu migration'dan sonra `grant` çalıştırılmadan bir kurala uyan her olay batch'i ve uyarı yolları 503 alır. `0006_alert_retention` migration'ı `tenants.alert_retention_days` sütununu (mevcut tenant'larda 60), `audit_events.details` sütununu ve `ix_alert_tenant_closed` indeksini ekler; runtime hesabına `alerts` üzerinde DELETE gerekir. Bu migration'dan sonra `grant` çalıştırılmazsa `alerts prune` silinecek uyarısı olan her tenant'ta başarısız olur ve 1 ile çıkar.

## Olay saklama ve günlük temizlik

Olaylar iki sınırla tutulur:

- **Cihaz başına üst sınır**, alış sırasında: `SP_MAX_EVENTS_PER_DEVICE` (varsayılan 250000, aralık 1000–10000000). Aşılınca cihazın en eski satırları aynı işlemde silinir. Varsayılan, normal kullanımda 30 günlük saklama belirleyici olsun diye bu büyüklükte seçilmiştir.
- **Zamana göre saklama**, tenant başına gün: varsayılan 30, en az 1, en çok 90. Silmeyi yalnız operatörün zamanladığı komut yapar.

Üst sınırın sildiği satırların tam sayısı cihaz imlecinde `cap_deleted_events` olarak birikir ve cihazın olay zaman çizelgesi cevabında görünür. `events prune` bu sayacı değiştirmez; zamana göre silinen satırlar ona katılmaz. Sayaç yalnız sunucu tarafındaki silmeyi gösterir; cihazda kaybolan olaylar `event_seq` boşluğu olarak görünür. Dürüst bir ajan üzerinden yetkisiz yerel bir kullanıcı da kısa ömürlü süreç seliyle sınırı tetikleyebilir ([tehdit modeli](THREAT_MODEL.tr.md)).

Bir alış en çok batch'teki olay sayısı + 5000 satır siler ve batch'in kendi olaylarını silmez. `SP_MAX_EVENTS_PER_DEVICE` düşürüldüğünde (veya daha yüksek bir değerden değişken kaldırılıp varsayılan 250000'e dönüldüğünde) fazlası tek istekte silinmez. Sınırın üstündeki bir cihazın her batch'i kendi satırlarını ekler ve en çok batch + 5000 eski satır siler; böylece fazlalık batch başına 5000 azalır ve `stored_events` yaklaşık fazlalık / 5000 batch içinde yeni sınıra iner. Örneğin 2.000.000 satır tutan bir cihazın sınırı 100.000'e indirilirse fazlalık 1.900.000'dir ve cihaz, batch boyutundan bağımsız olarak 1.900.000 / 5000 = 380 batch sonra sınıra ulaşır. Bu silmeler de `cap_deleted_events` sayacına eklenir. Bu sürede cihaz sınırdan fazla satır tutar, fakat her istek kısa kalır ve 5 saniyelik ifade zaman aşımına takılmaz. Olay göndermeyen cihazın fazlası yalnız `events prune` zamana göre sildikçe azalır. Disk alanı hesabını bu geçiş süresine göre yapın.

Tenant'ın saklama gününü korunan yerel yönetim CLI'ı migration/owner hesabıyla (`SP_MIGRATION_DATABASE_URL`) ayarlar. Değişiklik audit'e `tenant_event_retention_set` olarak yazılır:

```powershell
./.venv/Scripts/python.exe -m security_platform.cli set-event-retention --tenant-id TENANT_UUID --days 30
```

Temizlik komutu `serve` gibi yalnız runtime hesabıyla (`SP_DATABASE_URL`) çalışır. Owner hesabına geri düşmez; owner bağlantısı verilirse reddeder:

```powershell
./.venv/Scripts/python.exe -m security_platform.cli events prune
```

Komut her tenant için sunucunun alış zamanı (`received_at`) şimdiden tenant'ın gün sayısı kadar eski olan olayları siler. Cihaz saati (`observed_at`) kullanılmaz. Silme en çok 5000 satırlık parçalar hâlinde, her parça kendi kısa transaction'ında yapılır; böylece hiçbir ifade 5 saniyelik zaman aşımına yaklaşmaz ve olay alımı uzun süre beklemez. Etkilenen cihazların `stored_events` sayısı aynı transaction'larda düzeltilir. Çıktı yalnız sayılardan oluşan tek satır JSON'dur: `{"tenants": …, "deleted_events": …, "devices": …, "failed_tenants": …}`. Tenant veya cihaz kimliği ve bağlantı bilgisi yazılmaz.

Hatalar tenant başına ele alınır. Bir parça kilit veya ifade zaman aşımına ya da başka bir veritabanı hatasına düşerse yalnız o parçanın transaction'ı geri alınır; daha önce tamamlanan parçalar silinmiş kalır ve sayılara katılır. O tenant bu çalıştırmada atlanır, `failed_tenants` bir artar ve komut sıradaki tenant'la devam eder. En az bir tenant başarısız olursa komut sayıları yine stdout'a yazar, stderr'e `events prune incomplete: N tenant(s) failed and were skipped; ...` iletisini yazar ve 1 ile çıkar; sonraki çalıştırma atlanan tenant'ları yeniden dener. Bağlantı, runtime rol denetimi veya tenant listesi başlangıçta başarısız olursa hiçbir satır silinmemiştir; komut genel `Database operation failed; no success was recorded.` iletisiyle 1 döndürür.

Komutu günde bir kez, etkileşimli oturum gerektirmeyen bir görevle zamanlayın. `/RU` ile birlikte `/RP` veya `/NP` verilmeden oluşturulan görev, oluşturan kullanıcının etkileşimli oturumuna bağlıdır ve yalnız o kullanıcı oturum açıkken çalışır; sunucuda oturum kapatılınca temizlik sessizce hiç çalışmaz. Görev hesabı yönetici olmayan ayrı bir hesap olmalı ve korunan runtime veritabanı bağlantı dosyasını (aşağıda `runtime.json`) okuyabilmelidir. Görevin ortamı `SP_DATABASE_URL` değerini sağlamalıdır; değeri komut satırına veya görev tanımına düz metin olarak yazmayın. Windows Görev Zamanlayıcı ile örnek (yollar ve hesap adı örnektir):

```powershell
schtasks /Create /TN "SecurityPlatform\EventsPrune" /SC DAILY /ST 03:30 /RU "SUNUCU\sp-prune" /RP /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\SecurityPlatform\events-prune.ps1"
```

`/RP` değersiz verilince parola komut satırına yazılmaz; `schtasks` parolayı sorar ve görev için Windows'ta saklar. Parola saklanmasını istemiyorsanız `/RP` yerine `/NP` kullanın: görev o hesapla etkileşimsiz çalışır, fakat yalnız yerel kaynaklara erişir. Bu belgedeki yerel diskteki `runtime.json` ve loopback PostgreSQL bağlantısı için bu yeterlidir. `-ExecutionPolicy Bypass` yalnız bu PowerShell süreci için geçerlidir; istemci Windows sürümlerindeki varsayılan `Restricted` ilkesi betiği aksi hâlde çalıştırmaz.

`events-prune.ps1` yalnız görev hesabının okuyabildiği bir konumda tutulur ve runtime bağlantısını korunan bir dosyadan okur:

```powershell
$ErrorActionPreference = 'Stop'
$runtime = Get-Content -LiteralPath 'C:\SecurityPlatform\private\runtime.json' -Raw | ConvertFrom-Json
if (-not $runtime.runtime_url) { exit 2 }
$env:SP_DATABASE_URL = $runtime.runtime_url
& 'C:\SecurityPlatform\.venv\Scripts\python.exe' -m security_platform.cli events prune
if ($null -eq $LASTEXITCODE) { exit 1 }
exit $LASTEXITCODE
```

İlk satırdaki `$ErrorActionPreference = 'Stop'`, bağlantı dosyası okunamadığında veya Python başlatılamadığında (yol yanlış, sanal ortam taşınmış ya da görev hesabı ona erişemiyor) betiği durdurur; PowerShell bu durumda `1` ile çıkar. Bağlantı adresi boşsa betik komutu hiç çağırmadan `2` ile çıkar. Komut bir çıkış kodu bırakmadıysa (`$LASTEXITCODE` boş) sonuç başarısızlık (`1`) sayılır; boş değerle `exit` çağrısı `0`, yani başarı döndürürdü. Böylece betik başlayıp temizliği yapamadığında görevin son sonucu `0` olmaz.

Görevin son çalışma zamanını ve sonucunu düzenli denetleyin. `0` başarıdır; başka her değer temizliğin tamamlanmadığını gösterir (`events prune` bir tenant'ı atladığında veya veritabanına ulaşamadığında `1` döner; betik, Python başlatılamadığında veya bağlantı dosyası okunamadığında `1`, bağlantı adresi boş olduğunda `2` ile çıkar):

```powershell
Get-ScheduledTaskInfo -TaskPath '\SecurityPlatform\' -TaskName 'EventsPrune' | Select-Object LastRunTime, LastTaskResult
schtasks /Query /TN "SecurityPlatform\EventsPrune" /V /FO LIST
```

İlk komutta `LastTaskResult`, ikincisinde son çalışma sonucu alanı (İngilizce sistemlerde `Last Result`) bu değeri gösterir. Görev hiç başlamazsa (ör. görev devre dışı bırakıldıysa veya saklı parolanın süresi dolduysa) son sonuç önceki değerinde, çoğunlukla `0`'da kalır; bu yüzden `LastRunTime` değerinin son 24 saat içinde olduğunu da denetleyin.

Komut çalıştırılmazsa yalnız cihaz başına üst sınır korur; zamana göre saklama uygulanmaz.

## Uyarı saklama ve günlük temizlik

Kapalı uyarılar tenant başına bir gün sayısıyla tutulur (`0006_alert_retention`). Kurallar:

- Ölçüt uyarının kapatıldığı andır (`closed_at`, sunucu saati). Açılış ve son eşleşme zamanı kullanılmaz.
- Gün sayısı varsayılan 60, en az 30, en çok 3650'dir. Migration mevcut tenant'lara 60 yazar.
- `open` ve `acknowledged` uyarılar hiçbir zaman silinmez. Komut yalnız `closed` uyarıları okur.
- Sessizlik dönemi kuralı: kapalı bir `agent_silent` uyarısı, cihaz iptal edilmemişse ve cihazın son alış zamanından türeyen sessizlik anahtarı uyarının anahtarıyla hâlâ aynıysa yaşı ne olursa olsun kalır. Silinseydi sonraki `sweep` aynı sessizlik için yeni bir uyarı açardı. Cihaz yeniden rapor gönderince anahtar değişir; eski uyarı sonraki çalıştırmada silinir. İptal edilmiş cihazın uyarıları diğerleri gibi silinir.
- Bu kuralın sınırlı bir sonucu vardır: bir daha hiç rapor göndermeyen ve iptal edilmeyen her sessiz cihaz, son sessizlik döneminin tek kapalı `agent_silent` uyarısını süresiz tutar. Cihaz iptal edilirse bu uyarı sonraki çalıştırmada silinir.

Tenant'ın gün sayısını korunan yerel yönetim CLI'ı migration/owner hesabıyla (`SP_MIGRATION_DATABASE_URL`) ayarlar. Değişiklik audit'e `tenant_alert_retention_set` olarak yazılır. Aralık dışı değer `Invalid alert retention` iletisiyle 1 döndürür ve hiçbir şey yazmaz:

```powershell
./.venv/Scripts/python.exe -m security_platform.cli set-alert-retention --tenant-id TENANT_UUID --days 60
```

Temizlik komutu `events prune` gibi yalnız runtime hesabıyla (`SP_DATABASE_URL`) çalışır. Owner hesabına geri düşmez; owner bağlantısı verilirse `alerts prune requires the separate unprivileged runtime database role` iletisiyle 1 döndürür:

```powershell
./.venv/Scripts/python.exe -m security_platform.cli alerts prune
```

Komut her tenant için `closed_at` değeri şimdiden tenant'ın gün sayısı kadar eski olan kapalı uyarıları `ix_alert_tenant_closed` indeksiyle siler. Silme en çok 5000 satırlık parçalar hâlinde, her parça kendi kısa transaction'ında yapılır. Parçanın satırları `(closed_at, id)` sırasıyla kilitlenir; iki çalıştırma birbirini döngüsel olarak beklemez. Kalan sessizlik uyarıları sonraki parçaları durdurmaz. Çıktı yalnız sayılardan oluşan tek satır JSON'dur: `{"tenants": …, "deleted_alerts": …, "episode_alerts_kept": …, "failed_tenants": …}`. `episode_alerts_kept` bu çalıştırmada sessizlik dönemi kuralıyla tutulan uyarı sayısıdır; aynı uyarı her çalıştırmada yeniden sayılır. Tenant, cihaz veya uyarı kimliği ve bağlantı bilgisi yazılmaz.

Hatalar `events prune` gibi tenant başına ele alınır. Başarısız bir parça yalnız kendini geri alır; önceki parçalar silinmiş kalır ve sayılır. O tenant bu çalıştırmada atlanır ve `failed_tenants` bir artar. En az bir tenant başarısız olursa komut sayıları yine stdout'a yazar, stderr'e `alerts prune incomplete: N tenant(s) failed and were skipped; ...` iletisini yazar ve 1 ile çıkar. Bağlantı, runtime rol denetimi veya tenant listesi başlangıçta başarısız olursa hiçbir satır silinmemiştir; komut `Database operation failed; no success was recorded.` iletisiyle 1 döndürür.

Her çalıştırma her tenant için tek bir `alerts_pruned` audit kaydı yazar, silinecek uyarı olmasa da. Kayıt tenant satırı kilidiyle kendi transaction'ında yazılır. Bu çalıştırmanın sayıları `audit_events.details` sütunundadır: `{"deleted_alerts": …, "episode_alerts_kept": …, "complete": true|false}`. Bir parça başarısız olduysa `complete` `false` olur. Audit API'si `details` alanını döndürmez; konsol yalnız eylemi gösterir. Sayılar veritabanından okunur. Kayıtlar tenant'ın audit sınırına sayılır. Komut sınırı `serve` gibi `SP_MAX_AUDIT_EVENTS_PER_TENANT` değerinden okur (varsayılan 10000, aralık 10–1000000). Yerel yönetim komutları da (`create-tenant`, `set-membership`, `revoke-membership`, `set-event-retention`, `set-alert-retention`) aynı değeri okur. Aralık dışı veya tam sayı olmayan değerle komut veritabanına bağlanmadan 1 döndürür. Servisin sınırı yükseltildiyse aynı değeri görev betiğinde de verin (`$env:SP_MAX_AUDIT_EVENTS_PER_TENANT`). Verilmezse sınır 10000 olur ve her çalıştırma, 10000'i aşan tenant'ların en eski audit kayıtlarını siler, silinecek uyarı olmasa da. Testte 20000 sınırla 10.050 audit kaydı tutan bir tenant'tan hiçbir kayıt silinmedi; değişken verilmeden tek çalıştırma en eski 51 kaydı sildi ve tenant 10000 kayıtta kaldı. Günde bir çalıştırma tenant başına yılda 365 kayıt ekler. Audit sınırına ulaşmış bir tenant'ta her yeni kayıt en eski audit kaydını siler. Bu, `tenant_created` veya `membership_set` gibi eski yönetim kayıtlarının da zamanla düşmesi demektir; bu kayıtları uzun süre tutmak gerekiyorsa sınırı yükseltin.

Bilinen boşluk: silmeden sonra audit kaydı yazılamazsa (ör. tenant satırı kilitliyse) silinen uyarılar silinmiş kalır, fakat o çalıştırmanın kaydı olmaz. Tenant başarısız sayılır ve komut 1 döndürür. Sonraki çalıştırmanın kaydı yalnız kendi sayılarını taşır.

Komutu günde bir kez, `events prune` için anlatılan kurallarla zamanlayın: etkileşimli oturum gerektirmeyen görev, yönetici olmayan ayrı hesap, korunan `runtime.json`. Örnek (yollar ve hesap adı örnektir):

```powershell
schtasks /Create /TN "SecurityPlatform\AlertsPrune" /SC DAILY /ST 03:45 /RU "SUNUCU\sp-prune" /RP /TR "powershell.exe -NoProfile -ExecutionPolicy Bypass -File C:\SecurityPlatform\alerts-prune.ps1"
```

`alerts-prune.ps1`, `events-prune.ps1` ile aynıdır; yalnız çağrılan komut değişir. Çıkış kodları da aynıdır:

```powershell
$ErrorActionPreference = 'Stop'
$runtime = Get-Content -LiteralPath 'C:\SecurityPlatform\private\runtime.json' -Raw | ConvertFrom-Json
if (-not $runtime.runtime_url) { exit 2 }
$env:SP_DATABASE_URL = $runtime.runtime_url
& 'C:\SecurityPlatform\.venv\Scripts\python.exe' -m security_platform.cli alerts prune
if ($null -eq $LASTEXITCODE) { exit 1 }
exit $LASTEXITCODE
```

Görevin son çalışma zamanını ve sonucunu `EventsPrune` gibi denetleyin; `LastRunTime` son 24 saat içinde, `LastTaskResult` `0` olmalıdır:

```powershell
Get-ScheduledTaskInfo -TaskPath '\SecurityPlatform\' -TaskName 'AlertsPrune' | Select-Object LastRunTime, LastTaskResult
```

`sweep` ile aynı anda çalışabilir. Testte sırayla ve eşzamanlı çalıştırmada aynı sessizlik dönemi için ikinci bir uyarı açılmadı.

Ölçülen süreler (Round 1'in taşınabilir PostgreSQL 18.6 kümesi, varsayılan ayarlar; i7-13700H, 32 GB, NVMe, Windows 11). Veri: 3 tenant, 4000 cihaz, 30.000 audit kaydı. Uyarıların %60'ı 120 güne yayılmış kapalı, %10'u onaylanmış, %30'u açık; gün sayısı 60:

| Uyarı | İlk çalıştırma | Silinen | İkinci çalıştırma (silinecek yok) |
|---|---|---|---|
| 200.000 | 1,89 sn | 60.001 | 1,34 sn |
| 1.000.000 | 4,12 sn | 300.009 | 1,61 sn |

Süreler komutun tamamıdır; yaklaşık 0,9 saniyesi Python sürecinin başlamasıdır. Audit kayıt sayısı 30.000'de kaldı: tenant başına sınır en eski kaydı çıkarır.

Komut çalıştırılmazsa kapalı uyarılar silinmez ve birikir.

## Uyarı sınırı

Uyarı kuralları olay alımının içinde çalışır ([API V1](API_V1.tr.md), "Uyarılar"). Kötü niyetli ama kayıtlı bir cihazın operatörleri uyarıya boğmaması için cihaz başına kapanmamış (`open` veya `acknowledged`) uyarı sayısı sınırlıdır:

- `SP_MAX_OPEN_ALERTS_PER_DEVICE` (varsayılan 500, aralık 10–100000; aralık dışı veya tam sayı olmayan değerle servis başlamaz). Cihaz bu sayıda kapanmamış uyarı tutarken yeni bir uyarı açacak eşleşme hiçbir şey açmaz; cihaz imlecindeki `suppressed_alerts` sayacı batch ve anahtar başına bir artar ve olay zaman çizelgesi cevabında görünür. Açık bir uyarının güncellenmesi hiçbir zaman bastırılmaz. `tenant_admin`'in kapattığı her uyarı bir yer açar.
- Sınır düşürülürse mevcut uyarılar kapanmaz veya silinmez; cihaz sınırın altına inene kadar yeni anahtarlar bastırılır.
- Kapalı uyarılar tenant'ın uyarı saklama süresi (varsayılan 60 gün) dolunca `alerts prune` ile silinir; açık ve onaylanmış uyarılar silinmez. Disk alanı hesabında cihaz başına en çok bu sınır kadar kapanmamış uyarı ve saklama süresi içinde kapatılan uyarılar düşünülmelidir. `alerts prune` zamanlanmazsa kapalı uyarılar birikir.

`suppressed_alerts` toplam bir sayaçtır ve hiç azalmaz. Değeri artıyorsa cihaz sınırdadır: operatörün o cihazın uyarılarını incelemesi ve kapatması gerekir. Sayaç cihazın kendi beyanından türeyen bir sunucu sayımıdır; kötü niyetli bir cihaz sınırı bilerek doldurabilir ([tehdit modeli](THREAT_MODEL.tr.md)).

## Dolu veritabanında migration (0005) ve geri dönüş

`0005_stage3_detection`, olay ve uyarı tablolarını baştan sona okuyan ilk migration'dır. `endpoint_events` tablosunda olay türü CHECK'ini dokuz türe genişletir; yeni CHECK doğrulanırken bütün satırlar taranır. Ardından `ix_endpoint_events_process_identity` indeksini kurar ve tabloyu bir kez daha okur. `alerts` tablosunda kural ve olay sırası CHECK'lerini değiştirir, `first_event_seq` ve `last_event_seq` sütunlarındaki NOT NULL kuralını kaldırır ve `ix_alert_silence_episode` indeksini kurar. Yeni tablo eklemez; runtime hakları değişmez.

`migrations/env.py` migration'ı tek transaction'da çalıştırır ve her ifadeye 5 saniyelik `statement_timeout` ile 3 saniyelik `lock_timeout` verir. 0005 yalnız kendi ifadeleri için `statement_timeout` sınırını kaldırır; büyük tablodaki tarama bu yüzden iptal edilmez. `lock_timeout` 3 saniye kalır: bir ifade kilidini 3 saniyede alamazsa bütün migration geri alınır. Transaction iki tabloyu COMMIT'e kadar ACCESS EXCLUSIVE kilidiyle tutar: `endpoint_events` tablosunu ilk `ALTER TABLE endpoint_events` ifadesinden, `alerts` tablosunu ilk `ALTER TABLE alerts` ifadesinden başlayarak. Bu sürede iki tabloya dokunan her sorgu bekler; olay alımı, olay zaman çizelgesi ve uyarı görünümleri bunlardandır. Runtime bağlantıları da 3 saniyelik `lock_timeout` ile açılır. Bekleme bu süreyi aşarsa sorgu iptal edilir ve API isteği 503 (`database_unavailable`) alır.

Aşağıdaki ölçümlerde kilit süresi 5 milyon olayda 3 saniyelik sınıra yaklaştı. 10 milyon olayda sınırı aştı; aynı anda çalışan olay yazma ve zaman çizelgesi sorguları kilit zaman aşımıyla başarısız oldu. Açık kalan bir istek veya komut da migration'ı 3 saniyelik beklemeye düşürüp geri aldırabilir. Bu yüzden migration bir bakım penceresinde çalıştırılır: `serve`, `events prune` ve `sweep` durdurulur, önce yedek alınır. Komutlar yukarıdaki gibi `security-platform` kökünde çalıştırılır. Ölçümler yalnız bu migration içindir; sonraki migration'lar kendi ölçümünü gerektirir.

**1. Ön kontrol.** Owner bağlantısını PostgreSQL araçları için ortam değişkenlerine aktarın. Parola komut satırına veya ekrana yazılmaz; yalnız bu PowerShell oturumunun ortamında durur ve adım 6'da silinir. `PGPASSWORD` yerine korunan bir [parola dosyası](https://www.postgresql.org/docs/18/libpq-pgpass.html) da kullanılabilir. Araçlar taşınabilir kümenin ikilileridir. Başka bir PostgreSQL kurulumunda sunucuyla aynı ana sürümdeki `psql`, `pg_dump` ve `pg_restore` kullanılır; bağlantı değerleri de o kurulumun korunan dosyasından aynı şekilde okunur.

```powershell
$fixtureConfig = Get-Content -LiteralPath ../.tooling/platform-test-env.json -Raw | ConvertFrom-Json
if (-not $fixtureConfig.ready) { throw 'PostgreSQL fixture hazır değil' }
$env:SP_MIGRATION_DATABASE_URL = $fixtureConfig.migration_url
$pgBin = '../.tooling/postgresql-18.6/pgsql/bin'
$owner = [System.Uri]($fixtureConfig.migration_url -replace '^postgresql\+psycopg://', 'postgresql://')
$ownerUser, $ownerPassword = $owner.UserInfo.Split(':', 2)
$env:PGHOST = $owner.Host
$env:PGPORT = [string]$owner.Port
$env:PGDATABASE = $owner.AbsolutePath.TrimStart('/')
$env:PGUSER = [System.Uri]::UnescapeDataString($ownerUser)
$env:PGPASSWORD = [System.Uri]::UnescapeDataString($ownerPassword)
Remove-Variable owner, ownerUser, ownerPassword
& "$pgBin/psql.exe" -X -v ON_ERROR_STOP=1 -c "SELECT (SELECT sum(stored_events) FROM device_event_cursors) AS olay, pg_size_pretty(pg_total_relation_size('endpoint_events')) AS olay_tablosu, pg_size_pretty(pg_database_size(current_database())) AS veritabani"
& "$pgBin/psql.exe" -X -v ON_ERROR_STOP=1 -c "SELECT count(*) AS edr_cihaz, count(*) FILTER (WHERE d.last_received_at < now() - interval '15 minutes') AS sessiz_15_dk FROM devices AS d JOIN product_states AS p ON p.tenant_id = d.tenant_id AND p.device_id = d.id AND p.product_id = 'edr_agent' AND p.snapshot_sequence = d.last_sequence WHERE d.revoked_at IS NULL AND d.last_received_at IS NOT NULL"
```

İlk sorgu olay sayısını ve boyutları verir; bunları aşağıdaki ölçümlerle karşılaştırarak pencerenin süresini kabaca tahmin edin. İkinci sorgu, son snapshot'ında Altay EDR ajanı bulunan iptal edilmemiş cihazları ve bunlardan 15 dakikadan uzun süredir snapshot göndermeyenleri sayar. `sessiz_15_dk` değerini not edin; adım 6'da gerekir. 15 dakika, `SP_SILENCE_ALERT_SECONDS` ayarının varsayılanıdır (900 saniye); ayarı değiştirdiyseniz aralığı ona göre yazın.

**2. Durdurma.** Önce `serve` sürecini durdurun: ön planda çalışıyorsa Ctrl+C ile, bir hizmet yöneticisiyle çalışıyorsa onun durdurma komutuyla. Sonra `events prune` görevini devre dışı bırakın. `sweep` için bir görev zamanladıysanız onu da kendi adıyla aynı komutla devre dışı bırakın; bu belge `sweep` için örnek görev vermez. Görevi devre dışı bırakmak çalışan bir örneği sonlandırmaz; bu yüzden asıl denetim veritabanındaki oturumlardır:

```powershell
Disable-ScheduledTask -TaskPath '\SecurityPlatform\' -TaskName 'EventsPrune'
& "$pgBin/psql.exe" -X -v ON_ERROR_STOP=1 -c "SELECT usename, application_name, state, count(*) FROM pg_stat_activity WHERE datname = current_database() AND pid <> pg_backend_pid() GROUP BY 1, 2, 3 ORDER BY 1, 2, 3"
```

Sorguda runtime hesabının (bu belgede `sp_runtime`) satırı kalmamalıdır. Bu hesabın oturumları `serve`, `events prune` veya `sweep` süreçleridir; uygulama bağlantı adı vermediği için `application_name` boştur. Owner hesabı başka hesapların oturumlarında `state` değerini göremez; hesap adı yeterlidir. Owner hesabının başka bir oturumu çoğunlukla açık bırakılmış bir `psql` penceresidir; onu da kapatın.

**Cihazların pencere boyunca gördüğü.** `serve` kapalıyken cihazlar merkeze bağlanamaz. HBF snapshot göndericisi hata verir ve bekleyen mesajı korur; sonraki çalıştırmada aynı mesajı gönderir ([mimari](ARCHITECTURE.tr.md)). Altay EDR ajanı olaylarını giden kutusundan, aynı anda yalnız bir batch olarak gönderir (dur ve bekle); giden kutusunun birikimi, ajan yeniden bağlandığında snapshot'taki `outbox_backlog` sayacında görünür ([API V1](API_V1.tr.md)). Bu depodaki belgeler ajanın yeniden deneme aralığını ve giden kutusunun kapasitesini vermez. Giden kutusundan atılan kayıtlar sonradan `event_seq` boşluğu olarak görünür ve `event_loss` uyarısı açar. Snapshot kabul edilmediği için cihazlar son kabulden 90 saniye sonra `stale` görünür; operatör konsolu da API'ye ulaşamaz. Pencereyi kısa tutun.

**Zamanlanmış komutlar neden kapalı kalır.** Çalışan bir `events prune` veya `sweep` parçası olay ya da uyarı tablosunda kilit tutar. Migration'ın kilit isteği onu bekler; kilidi 3 saniyede alamazsa migration geri alınır. Migration kilidi 3 saniyeden uzun tutarsa da bu komutların parçaları kilit zaman aşımına düşer ve tenant o çalıştırmada atlanır (`failed_tenants`). `sweep` pencereden sonra yanlış uyarı da açabilir. Tarama yalnız sunucu saatine bakar: son snapshot'ında Altay EDR ajanı bulunan bir cihaz eşikten uzun süre snapshot göndermemişse, o sessizlik dönemi için bir `agent_silent` uyarısı açar. Eşik, `SP_SILENCE_ALERT_SECONDS` (varsayılan 900, aralık 300–86400) ile V3 snapshot'taki heartbeat aralığının üç katından büyük olanıdır. Tarama nedeni ayırt etmez; sunucunun bakım için kapalı kalması da cihaz sessizliği gibi görünür (`services/sweep.py`). Pencere eşikten uzun sürer ve tarama cihazlar yeniden bağlanmadan çalışırsa her EDR cihazı için bir uyarı açılır.

**3. Yedek.** Yedeği owner hesabıyla PostgreSQL'in özel arşiv biçiminde alın. Dosya, cihaz credential kayıtları ve audit dahil veritabanının tamamını içerir. Kaynak deposuna koymayın; yalnız yönetici hesabının okuyabildiği bir klasörde tutun (yol örnektir). Yedek bitmeden migration'ı başlatmayın: `pg_dump` yedek boyunca iki tabloda da paylaşımlı kilit tutar ve migration'ın ilk `ALTER TABLE` ifadesi 3 saniye bekleyip düşer.

```powershell
$dump = 'C:\SecurityPlatform\backup\before-0005.dump'
& "$pgBin/pg_dump.exe" --format=custom --file $dump
if ($LASTEXITCODE -ne 0) { throw 'pg_dump başarısız' }
& "$pgBin/pg_restore.exe" --list $dump | Measure-Object -Line
```

`pg_restore --list` arşivin okunabildiğini gösterir; komut arşiv listesinin satır sayısını yazar. Ölçümde 5,4 milyon olaylı, 2575 MB'lık veritabanının yedeği 22,58 saniye sürdü ve 216 MB'lık (226.680.523 bayt) bir dosya üretti. 10,8 milyon olaylı, 4945 MB'lık veritabanının yedeği iki ölçümde 44,63 ve 45,14 saniye sürdü ve 431 MB'lık (452.086.444 bayt) bir dosya üretti. Sıkıştırılmış boyut veriye bağlıdır; bu sentetik veri iyi sıkıştı, gerçek veride dosya daha büyük olabilir.

**4. Migration.** Belgelenen komutla çalıştırın; ardından yukarıdaki genel kural gereği `grant` çalıştırın (0005 hakları değiştirmez):

```powershell
./.venv/Scripts/python.exe -m alembic upgrade head
./.venv/Scripts/python.exe scripts/managed_postgres.py grant
```

Kurulu wheel'de `security-platform migrate` aynı migration'ı çalıştırır. Başarılı çalıştırma bir şey yazmaz ve 0 ile çıkar. Hata olduğunda `python -m alembic` kilidini alamayan ifadeyi ve PostgreSQL hatasını gösterir (aşağıda "3 saniyelik kilit beklemesi"). `security-platform migrate` ise her veritabanı hatasında yalnız `Database operation failed; no success was recorded.` yazar ve 1 ile çıkar; nedeni görmek için aynı sürümün kaynak ağacında `python -m alembic upgrade head` çalıştırın. Başarısız deneme hiçbir şeyi değiştirmez; yeniden çalıştırmak güvenlidir.

**5. Doğrulama.**

```powershell
./.venv/Scripts/python.exe -m alembic current
& "$pgBin/psql.exe" -X -v ON_ERROR_STOP=1 -c "SELECT conname, convalidated, pg_get_constraintdef(oid) LIKE '%agent_silent%' OR pg_get_constraintdef(oid) LIKE '%coverage_gap%' AS asama3 FROM pg_constraint WHERE conname IN ('ck_endpoint_event_kind', 'ck_alert_rule', 'ck_alert_event_seq') ORDER BY conname"
& "$pgBin/psql.exe" -X -v ON_ERROR_STOP=1 -c "SELECT c.relname, i.indisvalid FROM pg_index AS i JOIN pg_class AS c ON c.oid = i.indexrelid WHERE c.relname IN ('ix_endpoint_events_process_identity', 'ix_alert_silence_episode') ORDER BY c.relname"
```

Beklenen: `alembic current` çıktısı `0005_stage3_detection (head)` olur (bu sürümle `0006_alert_retention (head)`; aşağıda "0006 notu"). Üç CHECK satırında `convalidated` ve `asama3` `t`, iki indeks satırında `indisvalid` `t` olur. 0004'te `asama3` üç satırda da `f` olur ve indeks sorgusu satır döndürmez.

**6. Yeniden açma.** `serve` sürecini yeni kod sürümüyle, owner bilgileri bulunmayan ayrı bir PowerShell oturumunda başlatın (yukarıdaki `serve` komutu; o oturumda yalnız `SP_DATABASE_URL` ve operatör ayarları bulunur). Bu oturumdaki `PGPASSWORD` ve `SP_MIGRATION_DATABASE_URL` uzun ömürlü `serve` sürecinin ortamına geçmemelidir. `GET /readyz` cevabının `200 {status:ready}` olduğunu denetleyin. Uygulama açılışta yalnız `alembic_version` tablosunun okunabildiğini denetler, sürümü karşılaştırmaz. Yeni kod 0004 şemasında da açılır, fakat V2 olayları veritabanı CHECK'ine takılır ve bu istekler 503 alır; bu yüzden `serve` sürecini adım 5'teki doğrulamadan önce başlatmayın. Cihazlar bekleyen mesajlarını gönderir. `events prune` görevini yeniden etkinleştirin; pencere görevin saatine denk geldiyse komutu bir kez elle de çalıştırabilirsiniz. `sweep` görevini ise ancak bu oturumda adım 1'deki ikinci sorgu yeniden en çok not ettiğiniz `sessiz_15_dk` değerini gösterdiğinde, yani cihazlar yeniden snapshot gönderdiğinde etkinleştirin. Son olarak bu oturumdaki owner bilgilerini silin:

```powershell
Enable-ScheduledTask -TaskPath '\SecurityPlatform\' -TaskName 'EventsPrune'
Remove-Item Env:PGPASSWORD, Env:PGUSER, Env:PGHOST, Env:PGPORT, Env:PGDATABASE, Env:SP_MIGRATION_DATABASE_URL
Remove-Variable fixtureConfig
```

**Ölçülen süreler (yol gösterici).** Ölçümler 2026-11-27'de, bu belgedeki taşınabilir PostgreSQL 18.6 kümesinde ayrı, atılabilir bir veritabanında yapıldı. Küme varsayılan ayarlarla çalışıyordu (`shared_buffers` 32 MB, `maintenance_work_mem` 64 MB, `max_parallel_maintenance_workers` 2). Makine: Intel Core i7-13700H (14 çekirdek), 32 GB RAM, NVMe SSD, Windows 11. Veri, migration hesabıyla küme içinde SQL ile üretilmiş sentetik veridir: üç tenant; cihazların %1'i iptal edilmiş; olaylar 30 güne yayılmış V1 süreç olaylarıdır (%50 `process_started`, %48 `process_stopped`, %2 `sensor_state`; yük metni ortalama 185 bayt). Uyarıların %60'ı kapalı, %10'u onaylanmış, %30'u açıktır. Bazı koşularda önceki bir geri dönüşten kalan V2 biçimli süreç olayları da vardı (1,08 milyonluk veride 40.000, 5,4 milyonluk veride 200.000 `process_started` olayı); süreç kimliği indeksi yalnız bu satırları içerir. Veri ölçümden en çok birkaç dakika önce yazılmıştı, yani işletim sistemi önbelleği sıcaktı. Bazı koşularda aynı kümenin başka veritabanlarında 9'a kadar istemci bağlantısı açıktı (aynı makinede çalışan başka testler). Sayılar yol göstericidir: farklı donanımda, soğuk önbellekte, ayarlanmış bir sunucuda veya gerçek veride süreler değişir. Kendi verinizin olay sayısını ve boyutunu adım 1'deki sorguyla ölçüp karşılaştırın.

Yükseltme (`0004_edr_agent_product` → `0005_stage3_detection`):

| Veri | Koşu | Toplam süre | `endpoint_events` kilidi | `alerts` kilidi | En uzun ifadeler | Aynı anda çalışan sorgular |
|---|---|---|---|---|---|---|
| 1.000.000–1.080.000 olay, 500 cihaz, 20.000 uyarı; olay tablosu 459–513 MB, veritabanı 482–538 MB | 2 | 1,50–1,59 sn | 0,58–0,65 sn | 0,22–0,24 sn | CHECK doğrulaması 0,34 sn; indeks 0,19 sn | En çok 0,64 sn bekledi; hepsi başarılı |
| 5.000.000–5.400.000 olay, 2.000 cihaz, 100.000 uyarı; olay tablosu 2173–2486 MB, veritabanı 2252–2576 MB | 4 | 2,75–3,84 sn (`security-platform migrate`: 3,56 sn) | 1,86–2,85 sn | 0,87–1,35 sn | CHECK doğrulaması 1,50–1,57 sn; indeks 0,92–1,11 sn | En çok 2,84 sn bekledi; hepsi başarılı |
| 10.000.000 olay, 4.000 cihaz, 200.000 uyarı; olay tablosu 4278 MB, veritabanı 4427 MB | 1 | 4,86 sn | 3,94 sn | 1,48 sn | CHECK doğrulaması 2,46 sn; indeks 1,23 sn | Olay yazma ve zaman çizelgesi 3,01 sn sonra kilit zaman aşımı; uyarı okuma 1,42 sn bekledi |

Toplam süre süreç başlangıcını da içerir (bu makinede yaklaşık 0,9 saniye). Kilit süresi, kilidi alan ilk ifadenin başlangıcından COMMIT'in dönüşüne kadardır; ifade günlüğü olmayan koşularda yaklaşık 0,11 saniyelik `pg_locks` örneklemesiyle ölçüldü. "Aynı anda çalışan sorgular", sunucunun bağlantı ayarlarıyla (5 saniye ifade, 3 saniye kilit sınırı) runtime hesabından sürekli çalıştırılan kısa SQL transaction'larıdır: olay yazma (alımın sırasıyla cihaz satırı ve imleç satırı `FOR UPDATE`, sonra `endpoint_events` INSERT; her deneme geri alındı), bir cihazın en yeni 51 olayı ve tenant'ın en yeni 50 uyarısı. HTTP isteği değildirler; uygulamada aynı kilit hatası 503 olur. Yalnız `devices` tablosunu okuyan yoklama hiçbir koşuda 0,01 saniyeden uzun sürmedi.

**3 saniyelik kilit beklemesi.** Migration bir kilidi 3 saniyede alamazsa PostgreSQL ifadeyi iptal eder ve bütün transaction geri alınır: sürüm `0004_edr_agent_product` kalır, CHECK'ler ve indeksler değişmez (aşağıdaki ilk iki ölçümde sürüm, CHECK'ler ve indeksler denemeden sonra yeniden okundu; üçüncüsünde sürüm). `python -m alembic upgrade head` çıktısında hata şöyle görünür:

```text
sqlalchemy.exc.OperationalError: (psycopg.errors.LockNotAvailable) canceling statement due to lock timeout
```

Hemen ardından gelen `[SQL: ...]` satırları kilidini alamayan ifadeyi gösterir: `ALTER TABLE endpoint_events DROP CONSTRAINT ck_endpoint_event_kind` olay tablosunu, `ALTER TABLE alerts DROP CONSTRAINT ck_alert_rule` uyarı tablosunu bekledi demektir. `security-platform migrate` aynı durumda yalnız `Database operation failed; no success was recorded.` yazar ve 1 ile çıkar; tabloyu ve nedeni göstermez. Ölçülen durumlar:

- Olay tablosunu okumuş açık bir transaction varken (1 milyon olay) `python -m alembic upgrade head` 4,39 saniye, `security-platform migrate` 4,03 saniye sonra 1 ile çıktı. Kuyrukta bekleyen ACCESS EXCLUSIVE isteği, ondan sonra gelen olay yazma ve zaman çizelgesi sorgularını da bekletti: en çok 2,97 saniye, kendi 3 saniyelik sınırlarının hemen altında.
- Uyarı tablosunu okumuş açık bir transaction varken (5 milyon olay) migration olay tablosunun kilidini aldı ve CHECK'i doğruladı (1,67 saniye). Ardından uyarı tablosunun kilidini 3 saniye bekleyip düştü; komut 5,78 saniye sonra 1 ile çıktı. Olay tablosu geri alınana kadar yaklaşık 4,7 saniye kilitli kaldı; olay yazma ve zaman çizelgesi sorguları 3,01 saniye sonra kilit zaman aşımıyla başarısız oldu. Geç düşen bir deneme, o ana kadar kilitlediği tabloyu geri alınana kadar tutar.
- `pg_dump` çalışırken (10,8 milyon olay) başlatılan migration 4,11 saniye sonra 1 ile çıktı; yedek tamamlandı.

Kilit beklemesinde önce kilidi tutanı bulun:

```powershell
& "$pgBin/psql.exe" -X -v ON_ERROR_STOP=1 -c "SELECT l.pid, a.usename, a.application_name, l.relation::regclass AS tablo, l.mode, l.granted FROM pg_locks AS l LEFT JOIN pg_stat_activity AS a ON a.pid = l.pid WHERE l.relation IN ('endpoint_events'::regclass, 'alerts'::regclass) AND l.pid <> pg_backend_pid() ORDER BY l.pid"
```

`sp_runtime` satırı durdurulmamış bir `serve`, `events prune` veya `sweep` sürecidir; `pg_dump` kendi adıyla görünür; owner hesabının bir satırı çoğunlukla açık kalmış bir `psql` transaction'ıdır. O süreci durdurun veya transaction'ı bitirin; sorgu satır döndürmediğinde aynı komutu yeniden çalıştırın. Başarısız deneme hiçbir şeyi değiştirmediği için adım 3'teki yedek geçerli kalır. `migrations/env.py` içindeki 3 saniyelik sınırı yükseltmeyin: migration bu kez kuyrukta bekler ve arkasındaki her isteği de bekletir.

**Geri dönüş.** İki yol vardır. İkisi de adım 2'deki durdurmayı ister ve sonunda `serve` Aşama 3 öncesi kod sürümüyle başlatılır.

*Alembic ile 0004'e dönüş.* `security-platform migrate` yalnız en son sürüme yükseltir; geri dönüş alembic ile yapılır:

```powershell
./.venv/Scripts/python.exe -m alembic downgrade 0004_edr_agent_product
```

Komut, 0004 CHECK'lerinin kabul etmediği satırları kalıcı olarak siler: V2'ye özgü altı türün olaylarını (`scan_detected`, `behavior_match`, `persistence_change`, `agent_state`, `tamper_signal`, `coverage_gap`) ve altı yeni kuralın uyarılarını (`scan_detection`, `behavior_match`, `persistence_added`, `capability_down`, `tamper_signal`, `agent_silent`), durumları ne olursa olsun. Etkilenen cihazların `stored_events` değeri silinen olay sayısı kadar düşer. NOT NULL ve CHECK'ler 0002 ve 0003'teki hâline döner, iki indeks kaldırılır. Üç V1 türündeki V2 biçimli olaylar kalır. Silinen satırlar yalnız yedekten geri gelir; bu yüzden geri dönüşten önce 0005 durumunun da yedeğini alın (adım 3). Kilitler yükseltmeden farklıdır. İlk ifade silmeyi yapar; olay tablosu bu sırada okunabilir ve yazılabilir kalır. İfade biterken etkilenen cihazların imleç satırlarını kilitler ve bu cihazların olay alımı COMMIT'e kadar bekler. Ardından iki indeks kaldırılır ve iki tablo COMMIT'e kadar ACCESS EXCLUSIVE ile kilitlenir. Silme ifadesi, silinecek satır olmasa da bütün olay tablosunu tarar. Doğrulamada `alembic current` çıktısı `0004_edr_agent_product` olur; adım 5'teki CHECK sorgusunda `asama3` üç satırda da `f` olur ve indeks sorgusu satır döndürmez. Ölçülen süreler:

| Veri | Koşu | Toplam süre | Silinen V2 satırları | İki tablonun kilidi | En uzun ifadeler | Aynı anda çalışan sorgular |
|---|---|---|---|---|---|---|
| 1.100.000–1.188.000 olay, 22.500 uyarı; veritabanı 544–603 MB | 2 | 1,52–1,55 sn | 20.000–21.000 olay, 2.500 uyarı | 0,28–0,33 sn | Silme 0,28 sn; CHECK doğrulaması 0,26 sn | En çok 0,29 sn bekledi; hepsi başarılı |
| 5.400.000–5.500.000 olay, 100.000–110.000 uyarı; veritabanı 2543–2594 MB | 4 | 4,22–5,02 sn | 0–100.000 olay, 0–10.000 uyarı | 1,64–1,88 sn | Silme 1,45–1,74 sn (silinecek satır olmayan koşuda 1,74 sn); CHECK doğrulaması 1,48–1,71 sn | En çok 1,81 sn bekledi; hepsi başarılı |
| 11.000.000 olay, 220.000 uyarı; veritabanı 5003 MB | 1 | 8,19 sn | 200.000 olay, 20.000 uyarı | 3,11 sn | Silme 4,01 sn; CHECK doğrulaması 2,79 sn | Olay yazma (imleç satır kilidinde), zaman çizelgesi ve uyarı okuma 3,01 sn sonra kilit zaman aşımı |

*Yedekten geri yükleme.* Veritabanını adım 3'teki yedeğin anına döndürür:

```powershell
& "$pgBin/pg_restore.exe" --clean --if-exists --single-transaction --exit-on-error --dbname $env:PGDATABASE $dump
if ($LASTEXITCODE -ne 0) { throw 'pg_restore başarısız' }
```

`--clean --if-exists` yedekteki nesneleri önce kaldırıp yeniden kurar. `--single-transaction` ile geri yükleme ya tamamen uygulanır ya hiç uygulanmaz; `--exit-on-error` ilk hatada durur. Yedekten sonra yazılan her şey kaybolur: olaylar, uyarılar, snapshot'lar, audit kayıtları ve credential rotasyonları. Yedekten sonra credential'ı yenilenen bir cihazın yeni sırrı geri yüklenen veritabanında yoktur. Ölçümde 5,4 milyon olaylı yedek, 0005'e yükseltilip V2 satırları eklenmiş veritabanının üzerine 76,32 saniyede geri yüklendi. Sonuçta sürüm `0004_edr_agent_product` oldu; olay ve uyarı sayıları ile runtime hakları yedektekiyle aynıydı. 10,8 milyon olaylı yedeğin 0005'e yükseltilmiş veritabanının üzerine geri yüklenmesi 154,84 saniye sürdü; sürüm yine `0004_edr_agent_product` oldu ve 0005 indeksleri kalmadı. Geri yükleme, alembic ile dönüşten çok daha uzun sürer, fakat yedeğin anını eksiksiz geri getirir.

### 0006 notu (uyarı saklama)

`0006_alert_retention` küçük bir migration'dır. `tenants` tablosuna `alert_retention_days` (varsayılan 60, CHECK 30–3650), `audit_events` tablosuna `details` (JSONB, nesne, en çok 1024 bayt, CHECK) ekler ve `alerts` üzerinde `ix_alert_tenant_closed` kısmi indeksini kurar. Var olan satırları değiştirmez. Runtime hesabına `alerts` üzerinde DELETE gerekir; bu yüzden migration'dan sonra `grant` çalıştırılır.

İlk üç ifade kilitleri sabit sırayla alır: `tenants` (ACCESS EXCLUSIVE), `alerts` (SHARE), `audit_events` (ACCESS EXCLUSIVE). Sıra, onaylama ve kapatmanın sırasıyla aynıdır: tenant satırı, uyarı satırı, audit. Kilitler COMMIT'e kadar tutulur. SHARE kilidi uyarı okumalarını bekletmez; uyarı yazmaları ve tenant okumaları bekler. `statement_timeout` 0005'teki gibi yalnız bu migration'ın ifadeleri için kaldırılır; 3 saniyelik `lock_timeout` değişmez.

Ölçümler (yukarıdaki makine ve veri, 3 tenant, 4000 cihaz, 30.000 audit kaydı):

| Uyarı (veritabanı) | Koşu | Kilitten COMMIT'e | İndeks kurulumu | Komutun tamamı | Aynı anda çalışan sorgular |
|---|---|---|---|---|---|
| 200.000 (146 MB) | 2 | 0,15 ve 0,22 sn | 0,14 ve 0,21 sn | 1,1–1,2 sn | Tenant okuma ve uyarı yazma en çok 0,22 sn bekledi; uyarı listesi ve cihaz okuma en çok 0,006 sn; hepsi başarılı |
| 1.000.000 (681 MB) | 2 | 0,49 ve 0,57 sn | 0,48 ve 0,56 sn | 1,45–1,46 sn | Tenant okuma ve uyarı yazma en çok 0,56 sn bekledi; uyarı listesi en çok 0,004 sn; hepsi başarılı |

1.000.000 uyarıda açık bir uyarı okuması sürerken yapılan üçüncü yükseltme de başarılı oldu (kilit 0,59 sn). Geri dönüş iki boyutta da kilidi 0,01 saniye tuttu ve 0,9 saniye sürdü.

Kilit tutulursa: `tenants` tablosunu okumuş ve 6 saniye açık kalan bir runtime transaction'ı varken migration 4,12 saniye sonra `LOCK TABLE tenants` ifadesinde kilit zaman aşımıyla 1 ile çıktı. Sürüm `0005_stage3_detection` kaldı; hiçbir şey değişmedi. Bu sürede tenant okumaları en çok 2,99 saniye bekledi, hiçbiri başarısız olmadı. Uyarı okuma ve yazmaları etkilenmedi. Açık transaction'ı bitirip komutu yeniden çalıştırmak güvenlidir.

Uygulama:

1. Yedek alın (yukarıdaki adım 3).
2. `AlertsPrune` ve `sweep` görevlerini devre dışı bırakın.
3. `serve` bu boyutlarda durdurulmak zorunda değildir. Eski kod 0006 şemasında çalışır: denemede tenant ve üyelik oluşturma, olay saklama ayarı ve audit okuma çalıştı; yeni sütunlar varsayılan değerleriyle doldu. Eski `serve` migration sırasında çalışmayı sürdürür.
4. `migrate`, ardından `grant` çalıştırın.
5. Bundan sonra `serve` sürecini yeni kodla yeniden başlatın ve görevleri etkinleştirin. Yeni kod yeni sütunları okur; migration'dan önce başlatılmaz. `grant` yapılmadan `alerts prune` silinecek uyarısı olan her tenant'ta başarısız olur ve 1 döndürür.

Bu sürümle 0004'ten yapılan yükseltme 0005 ve 0006'yı aynı transaction'da uygular; bu durumda yukarıdaki 0005 adımları (`serve` durdurulmuş) geçerlidir ve adım 5'te `alembic current` `0006_alert_retention (head)` gösterir.

Geri dönüş `alembic downgrade 0005_stage3_detection` ile yapılır. Üç tabloyu (bu kez `alerts` de ACCESS EXCLUSIVE) kilitler, `alerts_pruned` ve `tenant_alert_retention_set` audit kayıtlarını siler, indeksi ve iki sütunu kaldırır. 0004'e dönüş de önce bu adımı uygular. Silinen uyarılar geri dönüşle geri gelmez; yalnız yedekten gelir.

## Test, günlük ve durdurma

Test çıktısında sürücü bağlantı bilgilerini göstermemek için `pytest --tb=short` kullanılır. Secret içeren config veya exception locals yazdırılmaz. PostgreSQL statement/parameter logları kapalıdır; native hata mesajları sabit tür/SQLSTATE ile sınırlanır. Windows'ta `pg_ctl`'ın ayrılan çocuk süreci stdout handle'ını taşıyabildiği için araç pipe yerine dosya tabanlı bounded capture kullanır.

```powershell
./.venv/Scripts/python.exe -m pytest tests/unit/test_managed_postgres.py -q --tb=short
./.venv/Scripts/python.exe scripts/managed_postgres.py stop
./.venv/Scripts/python.exe scripts/managed_postgres.py start
```

`stop`, yalnız doğrulanmış bu kümeye fast shutdown uygular. Veri dizini, roller ve sır dosyaları korunur; sonraki start aynı fixture'ı kullanır. Testler başka oturumlarda bu DB'yi kullanırken stop çalıştırmayın. Otomatik veya recursive veri silme komutu yoktur. Saklama/temizlik kararı exact çalışma alanı ve süreç sahipliği doğrulanarak ayrıca verilir.

Bu yardımcı aracın birim testleri yabancı metadata/yol/URL, reparse, beklenmeyen dinleyiciye stop göndermeme, secret çıktı koruması ve pg_ctl capture davranışını sınar. Gerçek DB migration, concurrency, tenant izolasyonu ve HTTP kabul sonuçları [ACCEPTANCE.tr.md](ACCEPTANCE.tr.md) içinde ayrı kaydedilir.

PostgreSQL davranışları için birincil kaynaklar: [initdb](https://www.postgresql.org/docs/18/app-initdb.html), [pg_ctl](https://www.postgresql.org/docs/18/app-pg-ctl.html), [SCRAM parola doğrulaması](https://www.postgresql.org/docs/18/auth-password.html), [GRANT](https://www.postgresql.org/docs/18/sql-grant.html), [parola dosyaları](https://www.postgresql.org/docs/18/libpq-pgpass.html).
