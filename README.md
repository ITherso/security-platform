# Security Platform 0.1.0 — deneysel kaynak teslimatı

## Buradan başlayın / Start here

Ürünün ne olduğu, kurulum, tek komutluk çevrimdışı demo, sorun giderme, güvenlik notları ve açık engeller: **[Ürün kılavuzu](docs/PRODUCT_GUIDE.tr.md)** · **[Product guide (English)](docs/PRODUCT_GUIDE.md)**.

```powershell
python -B scripts/run_demo.py
```

Bu komut gerçek CLI'leri commit'li örnek girdilerle çalıştırır. Sonuçları git dışındaki `demo-output/` altına yazar ve her adımı `PASSED`, `FAILED`, `NOT_RUN` veya `READY` olarak raporlar. İsteğe bağlı `--hbf-root`, `--termivar-root` ve `--phase30-delivery-zip` seçenekleri politika önizlemesini ve analist zincirinin 20–44. fazlarını açar. Sonuçlar örnek veriye aittir; gerçek bir sistemin değerlendirmesi, doğrulama veya onay değildir.

Aşağıdaki bölümler ayrıntılı başvuru ve tarihsel teslim notlarıdır.

## Bileşenler

Türkçe/İngilizce, salt okunur [operatör konsolu](operator-console/README.md), açıkça etiketlenen örnek veriyle bağımsız çalışır. React/TypeScript kaynakları, kilitli bağımlılıklar ve yerel kurulum yönergesi `operator-console/` altındadır. Gerçek API adapter'ı mevcut dört operatör GET'iyle sınırlıdır; canlı bağlantı kabulü yapılmadı. Derlenmiş konsol (`operator-console/dist/`) git'te tutulmaz; paketlenmiş konsol derlemesi veya Node/pnpm ile build gerekir.

Bağımsız FastAPI/PostgreSQL hizmeti: şirket üyeliklerini, tek kullanımlık cihaz kaydını, cihazların bildirdiği son ürün durumunu ve cihazın kendi beyanı olan süreç/sensör olaylarını tutar. Operatör yalnız güncel DB üyeliğinin izin verdiği tenant'a erişir; cihaz bearer kimliği yalnız kendi snapshot'ını, olaylarını ve credential yaşam döngüsünü kullanır.

Bu sürüm envanter, durum aktarımı ve cihazın kendi beyanı olan olayların (süreç başlangıcı/bitişi, sensör durumu) alımıdır; olaylar `self_reported`/`not_verified` kalır, uyarı kuralı ve konsol görünümü henüz yoktur. Firewall politika gönderimi, uzaktan shell, Termivar tarama yürütmesi, antivirüs motoru, otomatik enrollment veya ajan daemon'u içermez. Cihazın kimliğinin doğrulanması, bildirdiği korumanın, raporun veya olayların doğru olduğunu kanıtlamaz.

Ek çevrimdışı araç, mevcut HBF değerlendiricisiyle açık senaryoları karşılaştırır ve yürütülemeyen politika sözleşmeleri üretir. Ayrı içerik kimlikleri, iki CAS önkoşulu ve raporlanan receipt tutarlılığı saf fonksiyonlarla kontrol edilir. Bu araç HTTP/DB yüzeyini veya cihaz yetkilerini genişletmez.

Konsolun [politika etki inceleme alanı](operator-console/docs/POLICY_REVIEW_WORKBENCH.tr.md) ([English](operator-console/docs/POLICY_REVIEW_WORKBENCH.en.md)), bu CLI'nin önceden ürettiği sürümlü preview dosyasını yerel olarak görüntüler. Evaluator'ı tarayıcıya taşımaz; cihaz/uygulama yetkisi veya eksik revision/CAS kanıtı oluşturmaz.

[Termivar değerlendirme alanı](operator-console/docs/TERMIVAR_REVIEW.tr.md) ([English](operator-console/docs/TERMIVAR_REVIEW.en.md)), desteklenen yerel assessment ve ayrı incomplete tanı artefaktlarını salt okunur inceler. Yeni scanner veya backend importer değildir; isteğe bağlı manifest kontrolü yalnız seçilen JSON girdisine ilişkindir, tam bundle/üretici doğrulaması değildir.

Bu alanın [karşılaştırma görünümü](operator-console/docs/TERMIVAR_COMPARISON.tr.md) ([English](operator-console/docs/TERMIVAR_COMPARISON.en.md)) hazır `termivar-report-comparison/v1` JSON'unu okur. Dört grup yalnız rapor projection farklarını anlatır; tarayıcı yeni karşılaştırma üretmez ve bir öğenin kaybolmasını remediation kanıtı saymaz.

[Ürün Merkezi ve demo rehberi](operator-console/docs/PRODUCT_HUB.tr.md) ([English](operator-console/docs/PRODUCT_HUB.en.md)) beş mevcut ürün/bileşenin kapsamını ve gerçek sayfa bağlantılarını toplar. [Yetenek matrisi](operator-console/docs/CAPABILITY_MATRIX.tr.md) kullanılabilir UI ile yapılmamış/kararlaştırılmamış kurumsal kabul kapılarını, [yükleme kaydı](operator-console/docs/FRONTEND_LOADING.tr.md) gerçek frontend byte ölçümlerini ayrı tutar. Yeni marka, fiyat, lisans/SLA veya production onayı oluşturulmaz.

İlk ticari ürün adayı için [Termivar pilot hazırlık paketi](docs/commercial/README.tr.md); hedef müşteri hipotezini, kaynak destekli iddiaları, teslimat standardını ve açık kabul kararlarını tanımlar. Bu dokümantasyon satış, müşteri iletişimi, canlı değerlendirme veya üretime çıkış yetkisi değildir.

## Korunan başlangıç

Yanındaki HostBasedFirewall kaynağının sürümü 1.4.3 olarak korundu. Platform başlangıcı yerel `94037a261b63e2443f04d56356cd525a3d3445df` commit'idir. Korunan ilk aşama arşivi `HostBasedFirewall-phase1-2026-11-07-source.zip` SHA256 değeri `bb4e4c876ae56047aa114023bbf1059fc9f979908f7f65f0fbe849713b332261` olarak kaydedildi. Başlangıcın doğrulanmış sonuçları **2106 Python testi + 47 alt test**, **8 fixture Edge paketi** ve **11 gerçek izole localhost oturum/UI import kontrolüdür**. Yeni EXE veya GitHub push yapılmadı.

Yerel ürün merkezi, importer, dedup ve 50 özet sınırı bu projede yeniden uygulanmaz. Mapper mevcut açıkça alınmış özeti dönüştürür; firewall runtime'ını, COM'u veya WinDivert'i import etmez. Kaynak ve kabul ayrıntıları [ACCEPTANCE.tr.md](docs/ACCEPTANCE.tr.md) içindedir.

İkinci aşamadaki dar yerel UI bağlantısı mevcut authenticated `GET /ecosystem` özetini **Ürün özetini indir** düğmesiyle `ecosystem-overview.json` olarak indirir. Bu açık yerel indirme merkezî gönderim, enrollment veya backend yazımı başlatmaz. İndirilen dosya aşağıdaki manuel sender'ın `--snapshot-file` girdisidir; son kaynak commit'i başlangıç commit'inden ayrı teslimat manifestinde yer alır.

Köprü sonrası yerel firewall commit'i `74a88ed336cb8a0a2fab16e20389c9410590c292` olarak kaydedildi; ilk aşama arşivi korunur. Köprüyle sekiz UI paketi ve 11 gerçek oturum kontrolü tekrar geçti. Python/server dosyaları değişmedi.

## Kurulum

Python 3.12 veya sonrası gerekir; bu çalışma Windows x64 Python 3.14 ve gerçek PostgreSQL 18.6 üzerinde doğrulandı. Proje bağımlılıkları firewall ortamından ayrıdır:

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -c requirements-lock.txt -e '.[test]'
./.venv/Scripts/python.exe -m pip check
```

Build bağımlılığı `requirements-build-lock.txt` ve `pyproject.toml` içinde `setuptools==84.2.1` olarak sabittir. Kaynak kurulumu yanında wheel kurulumu da migration kaynaklarını taşır: `alembic.ini` ve migration dosyaları kurulum prefix'inin `share/security-platform` dizinine girer. CLI kaynak ağacını veya bu kurulu kaynağı seçer; eksikse sessiz alternatif şema oluşturmaz. Gerçek oluşturulmuş wheel ayrı hedefe kurulup kodun oradan import edildiği ve CLI migration'ın gerçek PostgreSQL'e çalıştığı doğrulandı; wheel yayımlanmadı.

Wheel'i yerelde yeniden üretmek için:

```powershell
./.venv/Scripts/python.exe -m pip install -r requirements-build-lock.txt
./.venv/Scripts/python.exe -m pip wheel --no-deps --no-build-isolation . --wheel-dir ../.tooling/platform-wheels
```

Bu Windows ortamında Docker bulunmadığı için PostgreSQL kabulü çalışma alanına ait taşınabilir kümede yapılır. Resmî ikili yerleşimi ve korunan bağlantı dosyası [OPERATIONS.tr.md](docs/OPERATIONS.tr.md) içindedir. Hazırlanmış ikililerle:

```powershell
./.venv/Scripts/python.exe scripts/managed_postgres.py start
$fixtureConfig = Get-Content -LiteralPath ../.tooling/platform-test-env.json -Raw | ConvertFrom-Json
if (-not $fixtureConfig.ready) { throw 'PostgreSQL fixture hazır değil' }
$env:SP_MIGRATION_DATABASE_URL = $fixtureConfig.migration_url
$env:SP_DATABASE_URL = $fixtureConfig.runtime_url
./.venv/Scripts/python.exe -m security_platform.cli migrate
./.venv/Scripts/python.exe scripts/managed_postgres.py grant
```

Bağlantı dosyasını veya ortam değişkenlerini yazdırmayın. Migration hesabı şema sahibidir; web hizmeti ayrı runtime hesabını kullanır. Runtime hesabıyla audit UPDATE veya DDL yapılamaz. Bounded retention için audit DELETE vardır; DB credential'ı ele geçirilirse audit silinebilir. Değişmez audit iddiası yoktur.

## İnsan kimliği ve yerel bootstrap

Gerçek üretim kimlik sağlayıcısı bu teslimatta yapılandırılmış değildir. Uygulama bir IdP veya parola sistemi kurmaz. Desteklenen profil, sabit HTTPS issuer/audience ve yerel public JWKS ile doğrulanan **RS256 RFC 9068 erişim token'ıdır**. Token türü `at+jwt` veya `application/at+jwt` olmalıdır. ID token kabul edilmez; zorunlu claim'ler ve anahtar rotasyonu [API_V1.tr.md](docs/API_V1.tr.md) içindedir. Eksik ayarlar auth'u kapatan bir kipe geçmez.

Gerçek sağlayıcıya ait değerler ve public JWKS dosyası sağlandıktan sonra:

```powershell
$env:SP_OPERATOR_ISSUER = 'https://your-trusted-issuer.example'
$env:SP_OPERATOR_AUDIENCE = 'your-security-platform-api'
$env:SP_JWKS_FILE = (Resolve-Path './secrets/operator-jwks.json').Path
$env:SP_ALLOWED_HOSTS = '127.0.0.1,localhost'
./.venv/Scripts/python.exe -m security_platform.cli create-tenant --name 'Örnek Şirket'
./.venv/Scripts/python.exe -m security_platform.cli set-membership --tenant-id TENANT_UUID --issuer $env:SP_OPERATOR_ISSUER --subject OPERATOR_SUBJECT --role tenant_admin
```

Issuer/subject insan kimliğinin anahtarıdır. E-posta alan adı veya token'daki `roles`, `tenant`, `is_admin` üyelik oluşturmaz. CLI'ın döndürdüğü tenant UUID'sini ve sağlayıcıdaki gerçek subject'i kullanın; örnek adları token veya parola olarak kullanmayın.

TLS sertifikası ve özel anahtarı ayrı korunan dosyalarda sağlayıp sunucuyu başlatın:

```powershell
./.venv/Scripts/python.exe -m security_platform.cli serve --host 127.0.0.1 --port 8443 --ssl-certfile ./secrets/server-cert.pem --ssl-keyfile ./secrets/server-key.pem
```

CLI `proxy_headers=False` ve kapalı access log ile çalışır. Açık `SP_ALLOW_LOOPBACK_HTTP=true` yalnız loopback test istisnasıdır; auth ve tenant sınırları kalır. Üretimde HTTPS gerekir. CORS/Host kontrolü yetkilendirme yerine geçmez.

## Cihaz kaydı ve elle tek gönderim

Tenant admin kayıt hakkını API üzerinden üretir; cihaz bu hakkı yalnız `/api/v1/enroll` için kullanır. API örnekleri sırları argv'ye koymadan korunan dosyalardan okur: [API_V1.tr.md](docs/API_V1.tr.md). Kayıt cevabındaki credential yalnız bir kez verilir. Cevap kaybolursa yönetici yarım cihaz kaydını iptal edip yeni hak üretir; eski hakla yeni sır alınmaz.

Mevcut yerel ürün merkezinden yetkili biçimde dışa aktarılmış `ecosystem-export.json` dosyasını, ayrı korunan credential dosyası ve state diziniyle gönderin:

```powershell
./.venv/Scripts/security-snapshot.exe --snapshot-file ./local-state/ecosystem-overview.json --credential-file "$env:USERPROFILE/Documents/SecurityPlatformPrivate/device.json" --state-dir "$env:USERPROFILE/Documents/SecurityPlatformPrivate/device-state" --initialize-state
```

`--initialize-state` yalnız yeni kaydedilmiş cihaz için açık başlangıçtır. Sonraki gönderimlerde bu bayrağı kaldırın. Cevap kaybında pending mesaj diskte aynı UUID/sıra/içerikle saklanır; yeniden denemede `--snapshot-file` verilmeyebilir. Eksik state sessizce sıra 1'e dönmez. Credential yenilenince aynı cihaz/base URL için state korunur; kaybolmuş state'i tekrar initialize etmek sunucu sırasını sıfırlamaz.

Credential/state dizini owner/DACL veya POSIX izin denetimini geçmelidir. Paylaşılan ya da başka kullanıcılara yazılabilir parent içeren workspace yolları reddedilebilir; örnekte kullanıcıya ait Documents altında ayrı özel dizin seçilir. Bu dizin ve credential dosyası API belgesindeki private-file yardımcılarıyla hazırlanır.

İstemci TLS doğrular, redirect izlemez, proxy ortamını kullanmaz, yanıtı 4 KiB ve bağlantı/okuma sürelerini sınırlar. Varsayılan güven kümesi certifi'dır. Özel/kurumsal CA için `--ca-file` yalnız verilen PEM paketine güvenir. Sertifika ve hostname doğrulaması açık kalır; `verify=False` kullanılmaz. İstemci enrollment yapmaz, credential'ı kendiliğinden yenilemez ve firewall dosyalarına yazmaz.

Credential süresi (`SP_CREDENTIAL_TTL_SECONDS`, varsayılan 24 saat) dolmadan açık yenileme yapılır:

```powershell
./.venv/Scripts/security-snapshot.exe --rotate-credential --credential-file "$env:USERPROFILE/Documents/SecurityPlatformPrivate/device.json"
```

Yeni sır aynı korumalı dosyaya atomik yazılır ve yazdırılmaz. Sunucu eski sırrı aynı işlemde iptal ettiği için kaybolan yanıt kurtarılamaz; cihaz iptal edilip yeniden kaydedilir. İptal edilmiş cihazlar cihaz kapasitesinden düşer. Ayrıntılar [API_V1.tr.md](docs/API_V1.tr.md) içindedir.

## Çevrimdışı politika önizlemesi

Yalnız açık girdi ve çıktı dosyalarıyla çalışır. Aşağıdaki yollar proje köküne göredir; `../HostBasedFirewall-main` bu çalışma alanındaki açıkça seçilmiş yerel kaynak dizinidir. Birleşik ZIP'i açtıysanız `--hbf-root ../HostBasedFirewall` kullanın. Test fixture'ları iki klasör adını da bulur; ayrıca açık `SP_HBF_SOURCE` desteklenir. Geçersiz açık test yolu sessizce atlanmaz.

```powershell
New-Item -ItemType Directory -Force demo-output | Out-Null
./.venv/Scripts/python.exe -m security_platform.policy_contracts.cli preview --input examples/policy-preview.json --hbf-root ../HostBasedFirewall-main --output demo-output/preview-result.json
./.venv/Scripts/python.exe -m security_platform.policy_contracts.cli check-preconditions --input examples/policy-preconditions.json --output demo-output/preconditions-result.json
./.venv/Scripts/python.exe -m security_platform.policy_contracts.cli validate-rollout --input examples/policy-rollout.json --evaluation-time 2030-01-01T00:30:00Z --output demo-output/rollout-result.json
```

Kurulu wheel aynı aracı `security-policy` olarak sunar. Preview örneği açık WORK profili ve 09:30 yerel senaryo saatiyle ALLOW→DENY farkını hesaplar. `--hbf-root` verilmezse çıktı `blocked`/`evaluator_unavailable` olarak yazılır. Açıkça verilen kök yüklenemezse komut çıkış kodu 1 ve stderr `evaluator_unavailable` verir, çıktı yazılmaz. `--hbf-root` ile çalıştırıldığında geçersiz politika, senaryo veya zone girdisi (`invalid_policy_bundle`, `invalid_scenario`, `input_limit_exceeded`, `ambiguous_equal_prefix_zones`) da çıkış kodu 1 verir. Bu kontroller evaluator gerektirir; `--hbf-root` olmadan şema açısından geçerli her istek `blocked`/`evaluator_unavailable` olarak yazılır. Gerekli bağlam eksikse yazılan sonuç `insufficient_context` olur. Aynı CIDR'ın farklı zone'larda bulunması iki girdide de reddedilir. Mevcut yerel hash/trial protokolü korunur; eşit-prefix sıra sorununun yerel enforcement motorunda düzeltildiği iddia edilmez.

CAS ve rollout örnekleri sentetik UUID ve fingerprint yer tutucuları içerir; gerçek bir önizlemenin veya cihazın kanıtı değildir. Mevcut üründe kalıcı policy revision/lineage kaynağı bulunmadığı için örneklerde bu alanlar `null` bırakılır: CAS `precondition_evidence_missing`, rollout `would_pause` üretir. Timestamp veya inventory sequence bu eksiği doldurmaz. Eşleşen fixture beyanları bile `verified` veya uygulama yetkisine dönüşmez.

CLI çıkış kodu 0 yalnız belirtilen çıktı dosyasının yazıldığını bildirir; JSON içindeki `blocked`, `would_wait`, `would_pause` ve blocker alanlarını okuyun. Geçersiz girdi çıkış kodu 1 üretir ve mevcut çıktıyı değiştirmez. Politika IP/nesneleri ve trace yalnız açık çıktı dosyasında tutulur; konsola, audit'e veya envanter telemetrisine aktarılmaz. Dosyaları kullanıcı seçtiği konumda korumalıdır. Kaynak loader'ı yerel operatörün seçtiği güvenilir Python kaynağını çalıştırır; sandbox veya üretici doğrulaması sağlamaz.

## Sözleşme ve kabul

- [API V1 ve statik OpenAPI](docs/API_V1.tr.md): 14 dar endpoint, olay sözleşmesi ve üç ayrı bearer türü.
- [Mimari](docs/ARCHITECTURE.tr.md): transaction, tenant ilişkileri, sıra ve kaynak anlamı.
- [Tehdit modeli](docs/THREAT_MODEL.tr.md): güven sınırları ve kalan riskler.
- [İşletim](docs/OPERATIONS.tr.md): portable PostgreSQL, roller, migration, olay saklama ve günlük temizlik, TLS ve durdurma.
- [Kabul matrisi](docs/ACCEPTANCE.tr.md): 27 kapı; `passed`, `failed`, `not_run` ayrımı.
- [Politika sözleşmesi](docs/POLICY_CONTRACT_V1.tr.md): sıralı zone'lar, açık bağlam, fingerprint, fixture CAS ve yürütülemeyen rollout.
- [Politika kabul kaydı](docs/POLICY_PREVIEW_ACCEPTANCE.tr.md): 22 ayrı kapı ve canlı uygulamanın açık sınırları.

```powershell
./.venv/Scripts/python.exe -m pytest -q --tb=short
```

Gerçek DB testleri hazır fixture gerektirir; atlanan DB testini başarı saymayın. Windows'ta native owner/DACL testleri çalışır; POSIX chmod kontrolü ayrı atlanır. Fiziksel cihaz, üretim IdP, canlı Windows sürücüsü/servis/reboot ve yayıncı imzası bu merkezî hizmetin fixture kabulünden çıkarılamaz.

Üçüncü turun tarihsel birleşik koşusu **344 passed, 1 POSIX-only skipped, 1 mevcut bağımlılık uyarısı** ile 23,07 saniyede geçti. Bunun içindeki **160 politika sözleşmesi testi** ayrıca 2,16 saniyede geçti. Aynı kaynaklar taze dışa aktarılıp ZIP'teki `HostBasedFirewall` klasör adıyla da 160 passed / 0 skipped olarak doğrulandı. Gerçek PostgreSQL, migration kaynaklarının seçimi ve ayrı süreç TLS E2E birleşik koşuya dahildir; üretim release kabulü değildir.

## Kalıcı revizyon laboratuvarı

`tools/policy_revision_lab/` üretim wheel'ine ve sunucu başlangıcına bağlanmayan ayrı yerel test aracıdır. PostgreSQL'de atanmamış `controller_draft/draft_revision`, özel SQLite dizininde sentetik `endpoint_staged/staged_revision` tutar. Bu kayıtlar gerçek controller desired veya cihaz policy revision kaynağı değildir; `authority=unbound`, `operational_binding=absent`, gerçek revision alanları `null` ve yürütme yetkisi `false` kalır.

CLI yalnız açık `init`, `append`, `read`, `check`, `report` ve Windows biçim kontrolü sunar:

```powershell
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli --help
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli windows-report --input tests/fixtures/policy_revision_lab/windows-not-run.json --output demo-output/windows-format-result.json
```

Sentetik binding ve A/B bundle örnekleri `tests/fixtures/policy_revision_lab/` altındadır. Endpoint init için henüz var olmayan, owner/DACL denetimini geçen özel bir lab dizini seçilir; controller yalnız ayrı test helper'ının hazırladığı işaretli lab DB/config dosyasını kabul eder. Uygulama DSN'sine fallback veya uygulama hesabına yeni hak yoktur. Depolar commit öncesi/sonrası kesinti, exact retry, yarış ve bozulma retlerini sınamak içindir. Tutarlı eski kopya, dış güvenilir referans olmadan saptanamayabilir; anti-rollback/attestation garantisi yoktur.

[Lab kabulü ve CLI örnekleri](docs/POLICY_REVISION_LAB_ACCEPTANCE.tr.md), [gerçek yazıcı/otorite matrisi](docs/POLICY_REVISION_SOURCES.tr.md) ve [Windows kabul planı](docs/WINDOWS_ACCEPTANCE_PLAN.tr.md) ayrı kapsamları açıklar. Windows şeması yalnız bildirilen biçim/tutarlılığı kontrol eder; 12 gerçek vaka `NOT_RUN` kalır.

Dördüncü turun güncel birleşik koşusu **506 passed, 2 skipped, 1 mevcut bağımlılık uyarısı** ile 94,21 saniyede geçti. Yeni lab testlerinden **162 passed / 1 symlink SKIP**; kalan 344 passed / 1 POSIX skip korunan platform temelidir. PostgreSQL, ayrı lab DB/rol, gerçek sunucu restart ve işlem/cevap kaybı yarışlarıyla test edildi. SQLite native DACL kontrolleri geçti; symlink yaratımı WinError1314 nedeniyle sınanamadı. Bu atlama başarıya çevrilmedi; gerçek Windows kabulü veya fiziksel güç kaybı denenmedi.

Sonraki ayrı karar kapısı: **gerçek controller/endpoint policy revision ve lineage kaynağı, kullanıcı tarafından sağlanacak Windows kabul ortamı ve yetkilendirilmiş yürütücünün tasarımı**. Bu kaynak teslimatı bunları uygulamaz; dağıtım planı yürütülemez.
