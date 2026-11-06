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

Audit DELETE yalnız uygulamanın tenant'a göre sınırlandırdığı eski kayıt temizliği için kullanılır; genel audit değiştirme/silme endpointi yoktur. Runtime DB credential'ının ele geçirilmesi, saldırganın SQL üzerinden audit kayıtlarını silmesine izin verebilir. Bu tasarım DB credential'ına veya DB yöneticisine karşı değişmez/kriptografik audit sağlamaz. Tenant sorgu kapsamı ve birleşik foreign key'ler ayrıca gerçek PostgreSQL üzerinde test edilir; mevcut uygulama RLS kullandığını iddia etmez.

Migration sonrasında `grant` yeniden çalıştırılır. Araç tabloların migration hesabına ait olduğunu ve beklenen tablo kümesinin mevcut olduğunu denetler; bütün tablolara geniş `ALL` yetkisi vermez. Yeni migration yeni runtime ihtiyacı eklerse grant sözleşmesi ayrıca incelenmelidir.

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
