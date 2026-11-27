# Sürekli entegrasyon (GitHub Actions)

`.github/workflows/ci.yml`; `main` dalına push, her pull request ve elle başlatma (`workflow_dispatch`) ile çalışır. İzin yalnız `contents: read`'dir. Aynı dal veya PR için yeni koşu eskisini iptal eder ve her işin `timeout-minutes` sınırı vardır. Yalnız GitHub'ın kendi eylemleri kullanılır (`actions/checkout`, `setup-python`, `setup-node`, `upload-artifact`, hepsi `@v7`). Checkout kimlik bilgisini saklamaz (`persist-credentials: false`); `run` betiklerinde `${{ }}` ifadesi yoktur.

**Durum:** İş akışı GitHub'da henüz hiç çalışmadı. Aşağıdaki sonuçlar bu Windows makinesindeki yerel doğrulamalardır; ilk gerçek koşu sahibin push'u ile olacak.

## İşler

| İnceleme kapısı | İş ve adım |
|---|---|
| Python birim testleri | `backend`: tam `pytest`; hiçbir test seçilmez, atlatılmaz veya `xfail` yapılmaz |
| Gerçek PostgreSQL entegrasyonu | `backend`: `postgres:18` servis konteyneri ve `scripts/ci/ci_database.py setup` |
| API ve tenant izolasyonu e2e | `backend`: `tests/integration` ve `tests/e2e`; `junit_summary.py --no-skips-in` bu paketlerdeki tek bir skip'i bile hata sayar |
| Migration upgrade/downgrade | `backend`: `ci_database.py migrations`; `upgrade head` → `downgrade base` → `upgrade head`, her adımdan sonra şema kontrolü |
| TS typecheck, konsol testleri, production build | `console`: `pnpm run typecheck`, `pnpm run test`, `pnpm run build` (vite build + `build.py`) |
| Bağımlılık ve güvenlik denetimi | `dependency-audit`: iki Python kilidi için `pip-audit`, konsol için `pnpm audit --prod` |

### backend ayrıntıları

- Servis `postgres:18`'dir. Süper kullanıcısı `sp_test_bootstrap`, initdb seçenekleri managed_postgres ile aynıdır (`--encoding=UTF8 --locale=C --auth-host=scram-sha-256`). `POSTGRES_PASSWORD`, iş bitince yok olan konteynerin atılabilir parolasıdır; secret değildir.
- `ci_database.py setup` yalnız `GITHUB_ACTIONS=true` iken çalışır. Var olan bir yapılandırma dosyası, `sp_migration`/`sp_runtime` rolleri veya `security_platform_test` veritabanı görürse durur. Uygulama rollerinin parolaları her koşuda yeniden üretilir ve `::add-mask::` ile loglarda gizlenir. Betik managed_postgres'in log ayarlarını `ALTER SYSTEM` ile uygular, onun `_bootstrap()` işlevini çağırır ve testlerin okuduğu `../.tooling/platform-test-env.json` dosyasını yazar (0600 izinli, var olanın üzerine yazmaz).
- `migrations` tek bir Alembic head ister. `downgrade base` sonrasında `alembic_version` dışında nesne kalmamalı; `upgrade head` sonrasında her tablo `sp_migration`'a ait olmalıdır.
- `grant` managed_postgres'in `TABLE_GRANTS` yetkilerini verir. Ardından `sp_runtime` rolünü denetler: süper kullanıcı, CREATEDB, CREATEROLE, BYPASSRLS, REPLICATION ve INHERIT yetkileri, rol üyeliği ve CREATE izni olmamalı; her tablodaki yetki kümesi tam beklenen küme olmalıdır.
- JUnit raporu `pytest-junit` artefaktı olarak 30 gün saklanır. `junit_summary.py` sayıları, başarısız testlerin kimliklerini ve skip nedenlerini iş özetine yazar; hata mesajlarını kopyalamaz. Artefakt maskelenmez; içindeki fixture değerleri iş bitince geçersiz olur.
- `SP_HBF_SOURCE` ayarlanmaz, çünkü HostBasedFirewall kaynağı bu depoda yok. Değişken boş değerle verilirse `test_preview_core` testleri skip yerine fail olur.

## Beklenen sonuç: backend kırmızı kalır

Hiçbir test gizlenmedi. İş şu üç nedenle kırmızı kalır:

1. **8 kapı testi bilerek başarısızdır.** Sahip korunan yüzeyin yeniden kesimini (re-cut) onaylayana kadar böyle kalırlar. CI için baseline, hash veya `approved_exceptions` değiştirilmez.
   - `tests/policy_contracts/test_surface_preservation.py`: `test_openapi_paths_methods_security_and_schemas_match_audited_baseline`, `test_existing_auth_snapshot_sender_and_transaction_sources_are_unchanged`, `test_no_additional_api_auth_or_migration_files_exist`, `test_alembic_head_and_database_models_have_no_policy_storage`
   - `tests/policy_revision_lab/test_lab_surface_preservation.py`: `test_all_committed_application_policy_core_and_packaging_sources_are_unchanged`, `test_no_application_module_or_migration_has_been_added`, `test_seventeen_http_paths_and_auth_security_schemas_are_identical`, `test_application_alembic_head_and_models_have_no_lab_storage`
2. **43 error:** `tests/policy_revision_lab/test_endpoint_store.py` (40) ve `test_cli_reporting.py` (3). Bu dosyaların conftest'i açık bir `SP_HBF_SOURCE` değeri ister.
3. **90 skip bekleniyor.** 88'inde HBF kaynağı yok (bunların 55'i `test_controller_store.py`'de). 1'inde Phase42/43 çıktıları yok. 1'i, tam offline zincirin istediği `SP_TERMIVAR_ROOT` ve `SP_PHASE30_DELIVERY_ZIP` olmadığı için atlanır.

**Yerel CI benzeri ölçüm.** Koşul: Windows, 75e60ba'nın `git archive` kopyası ve CI dosyaları, HBF yok, atılabilir `security_platform_ci` veritabanı. Sonuç: **2686 test; 2497 passed, 12 failed, 43 errors, 134 skipped**, 101 saniye.

Bu sonucun bir kısmı kopyadan kaynaklanır ve CI'da tekrarlanmaz:
- 3 `tests/offline_chain` failure: kopyada `.git` yok.
- 1 `test_security_review` failure: veritabanının adı farklı.
- 43 `tests/commercial_review_attribution` skip: `git ls-files` çalışamıyor.

Ayrıca 1 POSIX chmod testi Windows'ta atlanır, Linux'ta çalışır. GitHub'da beklenen sonuç **8 failed, 43 errors, 90 skipped, 2545 passed**'dir. Bu bir tahmindir, ölçülmedi.

Yeşil için üç koşulun hepsi gerekir:
- (a) re-cut onayı;
- (b) HBF kaynağı: `74a88ed336cb8a0a2fab16e20389c9410590c292` commit'i ikinci bir `actions/checkout` ile `HostBasedFirewall-main` yoluna alınır ve `SP_HBF_SOURCE` ile gösterilir. Depo özelse sahibin oluşturacağı salt okunur bir token gerekir; bu iş akışında token yok.
- (c) Aşağıdaki fixture'a Linux desteği.

(b) sağlanıp (c) sağlanmazsa `test_controller_store.py`'nin 55 testi skip yerine error verir.

## policy_revision_lab fixture'ı neden CI'da çalışmaz

`tests/policy_revision_lab/pg_fixture.py` managed_postgres'in kendi kümesini ister:
- `_validate_config` iki alan bekler: `bin_dir` (`.tooling/postgresql-18.6/pgsql/bin`) ve `cluster_dir` (`.tooling/test-pg-data-<32 hex>`).
- `_owned_server`, sunucunun `data_directory` değerinin bu küme olmasını şart koşar.
- `start` `pg_ctl.exe`, `postgres.exe` ve `initdb.exe` dosyalarını, ayrıca tam `postgres (PostgreSQL) 18.6` sürüm metnini ister. Debian/Ubuntu derlemeleri bu metne ek yapar.

CI yapılandırmasında bu alanlar yoktur ve managed_postgres yapılandırmayı reddeder. Linux desteği korunan bir dosyada, `scripts/managed_postgres.py`'de değişiklik ister; karar sahibindir.

## Python kilidi ve `--require-hashes`

`requirements-lock.txt` hash içermediği için `--require-hashes` kullanılamıyor. CI bunun yerine `pip install --no-deps --only-binary=:all:` ve ardından `pip check` çalıştırır: kilitteki 33 sürümün tam olarak kendisi, yalnız wheel olarak kurulur.

Hash'e geçmek için:
1. Güvenilir bir makinede kilidi hash'leriyle yeniden üretin (ör. `pip-compile --generate-hashes`); Linux ve Windows wheel'leri dahil olmalı.
2. Üretilen kilidi gözden geçirin.
3. Kurulum adımını `--require-hashes` ile çalıştırın.

`requirements-lock.txt` ve `requirements-build-lock.txt` korunan yüzey dosyalarıdır; değişiklikleri re-cut onayı ister. Diğer yol ayrı, hash'li bir CI kilididir; o zaman iki dosyanın birlikte güncel tutulması gerekir.

## Bağımlılık denetimi ve bulgular

- `pip-audit==2.10.1` kendi sanal ortamında şu seçeneklerle çalışır: `--strict --disable-pip --no-deps -r requirements-lock.txt -r requirements-build-lock.txt`. Bilinen herhangi bir açıkta, ayrıca denetlenemeyen bir pakette başarısız olur. pip-audit aracının kendisi hash'siz kurulur.
- `pnpm audit --prod` yalnız üretim bağımlılıklarını (`react`, `react-dom`) denetler. `low` ve üzeri her bulguda ve kayıt (registry) hatasında başarısız olur. Geliştirme bağımlılıkları (vite, typescript) bu adımda denetlenmez; gerektiğinde `pnpm audit` elle çalıştırılır.
- Bulgu çıkarsa önce düzeltilmiş sürüme yükseltin:
  - Python kilitleri korunan dosyalardır; yükseltme re-cut onayı ister.
  - Konsolda `pnpm-lock.yaml` güncellenir; typecheck, test ve build yeniden çalıştırılır.
- Düzeltme yoksa veya açık bu kullanımı etkilemiyorsa sahibin onayladığı bir istisna gerekir: tarihli, gerekçeli ve bitiş tarihi olan. İstisna `pip-audit --ignore-vuln <ID>` ile ya da pnpm'in `auditConfig.ignoreGhsas` ayarıyla tanımlanır. `continue-on-error` kullanılmaz, iş de kaldırılmaz.

## Linux taşınabilirlik taraması

- **Satır sonları:** `.gitattributes` `* text=auto eol=lf` içerir. `git ls-files --eol` çıktısında 770 dosya hem index'te hem çalışma ağacında LF'dir; 4 dosya metin değildir. Kapı testleri hash'i CRLF→LF normalize ederek alır, bu yüzden Linux'ta da aynı 8 sonuç beklenir.
- **Büyük/küçük harf:** `tests`, `tools`, `scripts` ve `src` içindeki yol benzeri metinlerde tam adı bulunmayan ama farklı harf büyüklüğüyle eşleşen 0 aday çıktı (sezgisel bir tarama).
- **Geçici dizinler ve dosya izinleri:** Windows'ta `Documents` altında çalışan testler POSIX'te pytest `tmp_path` kullanır: `test_manual_client`, `test_api`, `test_client_ca_rotation`, `test_client_transport`, `test_inventory_flow` ve policy_revision_lab conftest'i. `private_files`'ın POSIX dalı, her üst dizinin root'a veya kullanıcıya ait olmasını ve grup ya da herkes tarafından yazılamamasını ister; tek istisna root'a ait sticky dizinlerdir. `/tmp` (1777, root) ve pytest'in 0700 izinli dizinleri bu kurala uyar. Bu dal bu makinede hiç çalışmadı; ilk doğrulaması GitHub'da olacak.
- **Platforma göre değişen testler:** `test_world_readable_credentials_are_refused` Windows'ta atlanır, Linux'ta çalışır. e2e testinde süreç Windows'ta `taskkill` ile, Linux'ta `terminate`/`kill` ile durdurulur.
- **git kullanımı:** `tests/commercial_review_attribution` ve `tests/offline_chain` `git ls-files` kullanır; bu, `actions/checkout`'un sığ klonunda da çalışır.

## Kapsam dışı ve doğrulanmamış olanlar

- Windows ajanının CI'ı ayrı özel depoya aittir (`windows-latest` üzerinde `cargo test`); bu depoda değildir.
- Ajanı ve Platform'u birlikte koşturan depolar arası bir e2e, sahibin oluşturacağı bir token gerektirir; kurulmadı.
- CI Python 3.14 kullanır (yerel ortam 3.14.7). pyproject'in izin verdiği 3.12 ve 3.13 test edilmiyor.
- Yerelde çalıştırılmayanlar:
  - `setup`'ın süper kullanıcıyla çalışan kısmı (yalnız taze konteynerde çalışır);
  - `pip-audit` ve `pnpm audit`;
  - Python 3.14 için Linux wheel'lerinin (`--only-binary`) varlığı;
  - runner'da corepack'in pnpm 11.25.0 indirmesi.

## Yerel doğrulama (2026-11-27)

| Kontrol | Sonuç |
|---|---|
| YAML: PyYAML yok; alt küme ayrıştırıcısı, iş akışı kuralları, yollar ve komutlar | 143 kontrol, 0 sorun |
| `ci_database.py`, süper kullanıcı gerektirmeyen kontroller (red koşulları, yapılandırma alanları, log ayarı sorgusu) | 30/30 |
| `migrations` ve `grant`, `security_platform_ci` üzerinde | ikisi de exit 0; head `0005_stage3_detection` |
| `tests/integration` ve `tests/e2e`, bu veritabanında | 270 passed, 1 failed (veritabanı adı; CI'da `security_platform_test`) |
| Konsol (Node 24.22.1, pnpm 11.25.0) | typecheck exit 0; test 16/16; build (scratch klasöre) exit 0 |
