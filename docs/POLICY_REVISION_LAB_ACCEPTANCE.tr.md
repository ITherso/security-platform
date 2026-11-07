# Kalıcı revizyon laboratuvarı kabulü

Bu tur, gerçek depolardaki sentetik draft/staged CAS protokolünü ve Windows kabul hazırlığını sınar. HBF yazıcı entegrasyonu, production desired kaynağı, canlı Windows kabulü veya uzaktan yürütücü değildir. Kalıcı lab CAS sonucu, gerçek cihazın politika revizyon kaynağının hazır olduğu sonucuna yükseltilmez.

## Korunan başlangıç

Dördüncü promptun belirttiği `137989…` arşivinden sonra yalnız taze paket testlerinin kaynak yolu düzeltmeleri ve belgeleri teslim edilmişti. Bu turun fiilî başlangıç arşivi `Security-Ecosystem-2026-11-07.zip`, **1.314.143 bayt**, SHA256 **5543b96bff7caabd6d44459aebac189eb357be6e1e46900ec0ed7a13f962fbff** olarak bağımsız kontrol edildi. HBF `1.4.3/74a88ed`; merkez `0.1.0/35f784b` idi. `299d56b` üretim policy core'u, `e30a004` paket test yolu düzeltmesini, `35f784b` onu açıklayan belgeleri kapsar; inventory read-coherence `9c2ce8c` gerçek policy CAS kanıtı değildir.

Önceki sonuçlar tarihsel başlangıç olarak korunur: **344 passed, 1 POSIX-only skip, 1 mevcut uyarı; 23,07 saniye**; bunun içinde **160 policy_contracts, 2,16 saniye**. Aynı teslim edilmiş kaynak ZIP'lerinin taze açılmış `HostBasedFirewall/` dizilimiyle **160 passed / 0 skipped, 2,94 saniye** sonucu vardı. HBF odaklı regresyonu **200 passed + 23 alt test**, önceki tam HBF sonucu **2106 + 47**, UI 8 ve izole gerçek oturum 11 idi. Bunlar dördüncü tur lab sonucuyla yeniden adlandırılmaz.

## Yeni alan ve yetkisizliğin anlamı

Yeni kod `tools/policy_revision_lab/` altındadır; uygulama paketi, HTTP router'ı, startup veya wheel entrypoint'i değildir. PostgreSQL kayıtları yalnız `controller_draft/draft_revision`, SQLite kayıtları yalnız `endpoint_staged/staged_revision` üretir. Fixture tenant/subject UUID'si şirket üyeliği veya gerçek cihaz kimliği yetkisi sağlamaz.

Sabit alanlar `authority=unbound`, `operational_binding=absent`, `identity_source=fixture`, `rollback_protection=not_established`, `authorization=not_evaluated`, `execution_authorized=false`, `verification=not_performed` olarak kalır. `controller_desired_revision` ve `device_policy_revision` null'dır. Report gerçek precondition alanlarını doldurmaz; `precondition_evidence_missing`, `would_pause` ve execution/Windows/auth/verification blocker'ları korunur.

Her başarılı yeni operation_id revision'ı artırır; aynı içerikle yeni işlem de yeni revision'dır. Exact retry, request digest'i eşitse ilk committed sonucu verir; head ilerlemiş olsa da eski sonuç güncel head diye sunulmaz. Revision/lineage ile metadata zamanı ayrı anlam taşır. Bounded journal sınırında yeni yazı reddedilir; geçmişi sessizce budama veya yeni lineage ile reset yoktur. Tutarlı eski bir depo kopyası, dış güvenilir referans olmadan ayırt edilemeyebilir; yerel hash/journal zinciri anti-rollback veya attestation garantisi değildir.

## Depolar ve açık yerel CLI

`EndpointStore.init` yeni özel dizini açıkça yaratır; `open` eksik/bozuk depoyu yaratmaz. `endpoint.sqlite3`, marker ve SQLite yan dosyaları mevcut private-file/path/owner-DACL kontrollerinin sınırındadır. Mevcut boş dizin bile sessizce sahiplenilmez. HBF config'i kullanılmaz. Windows'ta desteklenmeyen güvenlik denetimi başarı sayılmaz.

Controller, mevcut taşınabilir test kümesinde ayrı işaretli lab DB/rolü ister. Uygulama runtime/migration hesabı draft yazıcısı değildir; uygulama DSN'si veya ortam değişkenine fallback yapılmaz. Ayrı provisioning helper'ı yalnız çalışma alanına ait test cluster'ını doğrulayıp ayrı lab alanını hazırlar. CLI production hedefini başlatmaz, migrate etmez veya provision etmez. Hassas config içeriği, parola veya DSN stdout/argv'ye konulmaz.

Test helper'ı `tests/policy_revision_lab/pg_fixture.py`, mevcut owned portable cluster'ın kimliğini doğrular. Yeni rastgele `sp_policy_lab_<uuid>` DB'si bootstrap hesabına, `lab` veri şeması ayrı `spl_<uuid>` login rolüne aittir; bootstrap-owned `lab_identity.area` işareti data writer için SELECT-only'dir. Rol superuser/createdb/createrole/inherit/replication/bypassrls değildir; PUBLIC DB CONNECT/CREATE kaldırılır. Uygulama hesabına hak eklenmez. Gerçek hedef/rol testleri aşağıdaki kabul kaydında ayrıca belirtilir.

Önceden private-file guard'ını geçen, var olan özel parent altında yeni config için yalnız test provisioning komutu:

```powershell
./.venv/Scripts/python.exe tests/policy_revision_lab/pg_fixture.py --config C:/path/to/existing-private-parent/new-controller-target.json
```

İkili ve cluster hazırlığı mevcut [OPERATIONS.tr.md](OPERATIONS.tr.md) içindedir. Helper çalışma alanına ait hazır test cluster'ını bulamazsa hata verir; production DSN'siyle devam edilmez. Verilen yol sır değildir; üretilen config sırrı dosyada kalır ve içeriği yazdırılmaz. Bilinmeyen/dolu alan, yabancı DB veya daha önceki config sahiplenilmez; hata bir otomatik temizleme/migration izni değildir.

CLI kaynak kökünden çalışır. Kullanıcının seçtiği özel, sahipli parent altındaki **henüz var olmayan** endpoint lab dizini ile açık binding/request dosyaları gerekir. `--hbf-root`, güvenilir operatörün seçtiği kaynak dizinidir; policy belgesinden türetilmez. İki projeyi birleşik arşivden açtıysanız kaynak yolu `../HostBasedFirewall`, geliştirme çalışma alanında `../HostBasedFirewall-main` olabilir.

Örnek binding, yalnız sentetik bir akıştır; gerçek tenant/device yetkisi değildir:

```json
{
  "kind": "endpoint_staged",
  "tenant_id": "11111111-1111-4111-8111-111111111111",
  "subject_id": "22222222-2222-4222-8222-222222222222",
  "product_id": "hostbasedfirewall",
  "enforcement_scope": "packet_policy"
}
```

Seçilmiş özel root ve yerel dosyalarla:

```powershell
$labRoot = 'C:/path/to/private-parent/new-endpoint-lab'
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli init --backend endpoint --location $labRoot --binding-file ./binding.json --hbf-root ../HostBasedFirewall --output ./lab-init-result.json
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli append --backend endpoint --location $labRoot --binding-file ./binding.json --hbf-root ../HostBasedFirewall --input ./append-request.json --output ./lab-append-result.json
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli check --backend endpoint --location $labRoot --binding-file ./binding.json --hbf-root ../HostBasedFirewall --output ./lab-check-result.json
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli report --backend endpoint --location $labRoot --binding-file ./binding.json --hbf-root ../HostBasedFirewall --output ./lab-report.json
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli windows-report --input tests/fixtures/policy_revision_lab/windows-not-run.json --output ./windows-format-result.json
```

Placeholder parent yolunu gerçek private owner/DACL denetimini geçen konumla değiştirin; workspace yolu bu makinedeki parent izinleri nedeniyle reddedilebilir. Output dosyası HBF kaynağının, endpoint store'un veya input dosyasının içine/alias'ına yazılmaz. `append-request.json`, `AppendRequest` biçiminde aynı binding, yeni UUID `operation_id`, init/read cevabındaki `expected_lineage`, güncel `expected_revision`, güncel `base_fingerprint` ve açık `bundle` ister. Boş head için revision 0/base null; ilk commit 1'dir. İlk işlemden sonra null base/revision 0 tekrar kullanılamaz. `read`, aynı açık backend/location/binding/source/output bayraklarıyla head'i döndürür. Controller için `--backend controller`, kind `controller_draft` ve ayrı provisioning helper'ının ürettiği özel config dosyası `--location` olarak kullanılır; bağlantı sırrı CLI bayrağı değildir.

## Gerçek çalıştırma kaydı

Son birleşik koşu **506 passed, 2 skipped, 1 mevcut bağımlılık uyarısı; 94,21 saniye** ile tamamlandı. Yeni lab alanı **162 passed / 1 symlink SKIP**; korunan önceki alan **344 passed / 1 POSIX-only SKIP** olarak ayrı sayılır. Bu 506 sayısı eski 344/160 başlangıcını değiştirmez. İki skip başarıya çevrilmez; 12 gerçek Windows vakası NOT_RUN kalır.

| Kontrol | Durum | Kaydedilmiş sonuç |
|---|---|---|
| Windows biçim doğrulayıcısı | PASS | `test_windows_evidence.py`: 51 passed; sentetik/real bildirilen PASS bile yalnız format sonucu; I/O/OS/ağ/saat/hash/imza tripwire'ları |
| Gate 12 yüzey koruması | PASS | `test_lab_surface_preservation.py`: 7 passed; 48 committed platform/core/migration/packaging kaynağı, 219 HBF dosyası, gerçek 12 router/OpenAPI yolu ve exact wheel entrypoint'leri |
| Bu iki odaklı dosya | PASS | 58 passed, 0,97 saniye |
| Açık lab CLI | PASS | Root çalıştırması: 10 passed, 0,64 saniye; gerçek native SQLite init/append/read/check/report/retry ve Windows formatı |
| SQLite/model transaction kabulü | PASS / SKIP | 39 passed, 1 SKIP: bağımsız süreç CAS/retry/crash/response-loss/old-clone ve native owner-DACL; Windows symlink yaratımı WinError1314 nedeniyle atlandı, symlink kabulü sayılmaz |
| Gerçek PostgreSQL ayrı lab DB kabulü | PASS | 55 passed; gerçek ayrı bağlantı/bariyer, transaction, process death/response-loss, owned PostgreSQL 18.6 stop/start, ayrı DB/rol sınırları ve son 8 bounded-corrupt-metadata testi birleşik koşuda geçti |
| Dördüncü tur birleşik platform regresyonu | PASS / SKIP | 506 passed, 2 skipped, 1 mevcut uyarı; 94,21 saniye. Yeni lab 55 PG + 39 SQLite + 51 Windows format + 10 CLI + 7 yüzey = 162 passed; SQLite symlink WinError1314 ve eski POSIX chmod testi ayrı skip |
| Canlı Windows vakaları | NOT_RUN | 12 gerçek plan; hedef/account/SID/OS/artifact/gözlem/inceleyen seçilmedi |

Odaklı komut:

```powershell
./.venv/Scripts/python.exe -m pytest tests/policy_revision_lab/test_windows_evidence.py tests/policy_revision_lab/test_lab_surface_preservation.py -q --tb=short
```

Birleşik koşu komutu ve kanıtlar:

```powershell
./.venv/Scripts/python.exe -m pytest -q --tb=short --junitxml=reports/phase4-platform-junit.xml
```

`reports/phase4-platform-junit.xml`, çalışma alanındaki `platform-final-tests.log` ve `reports/policy-revision-lab-acceptance.json` gerçek sonucu kaydeder. JSON projeksiyonu PASS ile SKIP'i ve canlı NOT_RUN vakalarını ayrı tutar. PostgreSQL 16 MiB sınırı bütün DB/WAL disk boyutu iddiası değildir: journal'ın aggregate request/result payload sınırıdır; SQLite kendi DB/journal/marker bütçesini ayrıca sınırlar.

Taze kaynak paketi kontrolü ayrı kaydedilir: `fresh-package-acceptance.json`, test edilen kaynak commit/arşiv hash'lerini, `policy_contracts` sonucunu ve `-m 'not integration'` seçimiyle taşınabilir lab sonucunu verir. Teslim edilen kaynak arşivleri bu hash'lerle eşleştirilir. Taze açılmış ağaçtaki 55 PostgreSQL testinin bu seçimde deselect edilmesi gerçek fresh-PG kabulü değildir; gerçek PG kabulü yukarıdaki 506 testlik çalışma alanı koşusundadır. Symlink dalının SKIP sonucu ayrı korunur. Birleşik ZIP kanıt dosyaları `evidence/platform/` altındadır.

## Zorunlu 12 kapı

| Gate | Kabul | Durum ve kanıt |
|---:|---|---|
| 1 | İki depoda lineage/head/bundle restart; open yaratmaz | PASS — PG/SQLite init-open-restart ve missing/corrupt state retleri |
| 2 | Ayrı PG bağlantıları/bariyer ve bağımsız iki SQLite süreç; tek CAS kazanır | PASS — gerçek ayrı PG backend bağlantıları ve bağımsız SQLite süreç yarışları |
| 3 | operation_id yarışı, farklı içerik conflict, restart/head ilerlemesinde exact retry | PASS — iki backend idempotency/race ve exact committed-result testleri |
| 4 | ABA; eski revision, yanlış lineage/base/tenant/device/product/scope reddi | PASS — ABA yeni commit numaraları ve immutable binding/CAS retleri |
| 5 | Commit öncesi kesinti ve commit sonrası cevap kaybı; artifact/head/journal tutarlılığı | PASS — gerçek writer process death ve exact retry; fiziksel güç kaybı değildir |
| 6 | Gerçek PG test cluster restart ve SQLite reopen; güç kaybı iddiası yok | PASS — owned PG18.6 gerçek stop/start, SQLite yeniden açma; lineage/head/orijinal sonuç korundu |
| 7 | Payload/hash/head corruption; ordered zones ve ambiguity reddi | PASS — iki backend tam journal kontrolü; PG oversized metadata dahil; eşit-prefix belirsizlik reddi |
| 8 | Tutarlı eski clone'da anti-rollback sınırı, sahte rollback detection yok | PASS — eski tutarlı kopya fixture'ı açılabilir; rollback_protection=not_established korunur |
| 9 | Lab revision gerçek CAS'e yükseltilmez; report blocker'ları | PASS — 10 CLI/non-promotion testi; null gerçek revision, precondition_evidence_missing ve would_pause sabit |
| 10 | Path/izin, yabancı PG hedefi/alanı reddi; HBF/API/OS değişikliği yok | PASS: native owner/DACL, broad-reader/hardlink, bilinmeyen alan ve yabancı PG hedef/rol retleri. SKIP: gerçek Windows symlink yaratımı WinError1314; bu dal kanıtlanmadı |
| 11 | Windows şeması yalnız biçim; eksik/sentetik kanıt gerçek kabul PASS yapmaz | PASS — 51 Windows format testi; gerçek vakalar NOT_RUN |
| 12 | 12 HTTP path, auth/credential/snapshot/sender, Alembic, policy core/wheel ve HBF yüzeyi korunur | PASS — 7 yeni yüzey testi; baseline `35f784b/74a88ed`, fixture yeniden üretilmez |

Gate 10'un symlink dalı SKIP kaldığından “12 kapının tamamı eksiksiz geçti” iddiası kurulmaz. PASS yalnız belirtilen sınırı kapatır; SKIP/BLOCKED/FAIL/NOT_RUN başarıya çevrilmez. Bu koşuda izole PostgreSQL kabulü geçti; başka ortamda test cluster'ı yoksa ilgili kapı BLOCKED olur ve production bağlantısıyla aşılmaz. Gerçek Windows ortamının henüz sağlanmaması bu offline lab'ı üretim IdP ile bağlama gerekçesi değildir.

## Açık kalan gerçek kaynak ve kullanıcı kararları

Gerçek controller desired ve endpoint device policy revision kaynakları **not_proven** durumundadır. Bütün yazıcılar, trial/backup/recovery dahil tek yetkili commit sınırına bağlanmadan lab revizyonu bu alanlara kopyalanamaz. Config diski, runtime evaluator ve native enforcement ayrı kabul ister. Tutarlı restore/reimage/clone sonrası kimlik/lineage yeniden bağlama ve güvenilir dış referans politikası yoktur; anti-rollback/attestation garantisi kurulmadı.

[POLICY_REVISION_SOURCES.tr.md](POLICY_REVISION_SOURCES.tr.md) kaynak/otorite matrisini, [WINDOWS_ACCEPTANCE_PLAN.tr.md](WINDOWS_ACCEPTANCE_PLAN.tr.md) gerçek ortam ve insan kapılarını verir. Kullanıcı tarafından gerçek hedef, hesaplar/SYSTEM, artifact, kurtarma yolu, işlem yetkisi ve policy otoritesi seçilmeden canlı kabul yapılmaz. HBF writer entegrasyonu, production desired veya remote executor otomatik sonraki iş değildir; bu tur burada durur.
