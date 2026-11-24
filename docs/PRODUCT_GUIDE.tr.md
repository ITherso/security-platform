# Termivar Platform — ürün kılavuzu

Termivar Platform 0.1.0'ı değerlendirmek, kurmak ve göstermek için başlangıç noktası budur. Bugün neyin uygulandığını, nasıl çalıştırılacağını ve neyin hazır olmadığını anlatır. Ayrıntılı Türkçe başvuru belgeleri sondadır. English: [PRODUCT_GUIDE.md](PRODUCT_GUIDE.md).

Görünen ad 2026-11-23'ten beri Termivar'dır; teknik adlar değişmedi: Python paketi `security_platform`, `security-platform` komutu, `SP_` ayarları, ürün kimlikleri (`hostbasedfirewall`, `termivar`, `antivirus`) ve veritabanı adları.

## Ürün nedir?

Termivar Platform, güvenlik operasyonu bileşenlerinden oluşur. Her sonuç kanıt düzeyini açıkça taşır:

- Cihaz bildirimi "cihazın bildirdiği" olarak kalır.
- Hash eşleşmesi yalnız "tutarlı byte" anlamına gelir.
- Gösterilmek hiçbir şeyi "doğrulanmış", "onaylanmış" veya "yetkilendirilmiş" yapmaz.

| Bileşen | Bugün ne yapar | Demo durumu |
| --- | --- | --- |
| **Operatör konsolu** (`operator-console/`) | Türkçe/İngilizce, salt okunur web konsolu. Açıkça etiketli örnek veriyle açılır. Kapsadıkları: cihaz envanteri, iki cihazın karşılaştırılması, durum raporu taslağı, politika etki incelemesi, Termivar Web değerlendirme ve karşılaştırma incelemesi. Yerel JSON dosyalarını yalnız tarayıcıda okur. | Derlenmiş konsol varsa hazır ([3. bölüm](#3-operatör-konsolu-örnek-veri)). |
| **Çevrimdışı politika etki önizlemesi** (`security-policy`) | Base ve candidate firewall politikasını, yerel HostBasedFirewall evaluator kaynağıyla açık senaryolar üzerinde karşılaştırır. Fixture CAS önkoşullarını kontrol eder. Yürütülemeyen bir rollout'u simüle eder. | Hazır, çevrimdışı. |
| **Çevrimdışı Termivar Web analist zinciri** (`tools/commercial_*`, faz 16–44) | Termivar Web değerlendirmesini intake, analist inceleme paketi, tek dosyalık HTML inceleme masası ve müşteri teslim taslağı adımlarından geçirir. Sonraki fazlar şunları ekler: vaka paketi, portföy, kapsam/izlenebilirlik, bileşim, lisans/bağımlılık kanıtı, korumalı referans kapsülü ve minimal görev kapsülü alışverişi/uzlaştırması. | Tek komutla yeniden üretilebilir ([5. bölüm](#5-termivar-web-çevrimdışı-analist-zinciri)). |
| **Envanter API'si** (`security-platform` servisi) | FastAPI/PostgreSQL. Tenant üyeliklerini, tek kullanımlık cihaz kaydını, cihaz kimlik bilgilerini ve cihazın bildirdiği son ürün durumunu tutar. Operatörler RS256 RFC 9068 erişim token'ıyla kimlik doğrular. | PostgreSQL, IdP ve TLS gerekir ([6. bölüm](#6-envanter-apisi-ileri-düzey)). |
| **Cihaz göndericisi** (`security-snapshot`) | Dışa aktarılmış HostBasedFirewall ekosistem özetini bir kez gönderir. Açıkça istenirse cihaz kimlik bilgisini yeniler. | Envanter API'si gerekir. |

Ürün şunları **yapmaz**:

- hedef taramak,
- firewall politikası göndermek veya uygulamak,
- uzaktan komut çalıştırmak,
- antivirüs motoru sunmak,
- cihazları otomatik kaydetmek,
- cihaz bildiriminin doğruluğunu kanıtlamak.

HostBasedFirewall ve Termivar Web ayrı ürünlerdir. Bu depo onların çıktılarını veya kaynaklarını okur, kendilerini dağıtmaz.

## 1. Kurulum

Gerekenler:

- Python 3.12 veya sonrası (Windows x64 / Python 3.14 üzerinde doğrulandı).
- Tek seferlik `pip install` için ağ erişimi.
- Zincir çalıştırıcısı için `PATH` üzerinde `git`.

İsteğe bağlı:

- Konsolu derlemek için Node 24 ve pnpm 11.
- Envanter API'si için PostgreSQL 16 veya sonrası.

```powershell
python -m venv .venv
./.venv/Scripts/python.exe -m pip install -c requirements-lock.txt -e '.[test]'
./.venv/Scripts/python.exe -m pip check
```

Linux/macOS'ta `.venv/bin/python` kullanın. Bütün komutlar depo kökünden, venv yorumlayıcısıyla çalıştırılır.

## 2. Tek komutluk çevrimdışı demo

```powershell
python -B scripts/run_demo.py
```

Gerçek komut satırı araçlarını commit'li örnek girdilerle çalıştırır. Çıktılar yeni bir `demo-output/run-<UTC zaman>/` dizinine yazılır (git dışında). Hiçbir şey simüle edilmez.

`DEMO_SUMMARY.md` her adımı şu durumlardan biriyle listeler:

- `PASSED`
- `FAILED`
- `NOT_RUN`: dış girdi verilmedi.
- `READY`: konsol başlatılabilir.

Zincir çalıştırıcısı depo içindeki bir workspace'i kabul etmez. Bu yüzden analist zincirinin workspace'i sistemin geçici dizininde oluşturulur. Workspace deponun bir kopyasını ve bütün faz çıktılarını içerir. Yolu yazdırılır ve özete kaydedilir. İnceleme için korunur; işiniz bitince silin. `--output-dir` depo dışında verilirse workspace oraya oluşturulur.

| Seçenek | Açtığı adım |
| --- | --- |
| `--hbf-root <HostBasedFirewall kaynak dizini>` | Gerçek evaluator ile politika önizlemesi |
| `--termivar-root <6a2639348c2366d0bf71b9a34e5484d40aa393a3 commit'indeki Termivar checkout'u>` | Zincirin 20–30. fazları |
| `--phase30-delivery-zip <Termivar-Offline-Module-Candidates-phase30-2026-11-12.zip>` | `--termivar-root` ile birlikte 31–44. fazlar |

Çıkış kodu 0, hiçbir adımın başarısız olmadığını gösterir.

2026-11-20'de üç seçenek de verilerek ölçülen sonuç:

- Üç politika adımı `PASSED`.
- Analist zincirinin 29 fazı, kayıtlı 168 dosyanın 168'ini 31 saniyede byte byte aynı üretti.
- Bu checkout'ta derlenmiş konsol olmadığı için konsol adımı `NOT_RUN`.

`would_pause` veya `precondition_evidence_missing` gibi politika sonuçları örnek verinin beklenen çıktısıdır, hata değildir.

## 3. Operatör konsolu (örnek veri)

Konsol, derlenmiş bir `operator-console/dist/` dizini ister; bu dizin git'te tutulmaz. Paketlenmiş konsol derlemesini kullanın veya Node/pnpm ile derleyin ([operator-console/README.md](../operator-console/README.md)).

```powershell
python -B operator-console/serve.py --port 8787
```

`http://127.0.0.1:8787/` adresini açın; `Ctrl+C` ile durdurun.

Önizleme sunucusu:

- yalnız loopback'e bağlanır,
- kullanımdaki portu reddeder,
- yalnız build manifestindeki dosyaları sunar,
- katı CSP gönderir.

Önerilen 10 dakikalık gösterim:

1. **Ürün Merkezi**: ürün kataloğu ve sınırlar.
2. **Cihazlar**: bir cihazı açın; kayıt, sunucu alındısı ve ürün beyanı bölümleri ayrıdır. Cihazı **Durum raporu**na ekleyip önizlemeyi açın.
3. **Karşılaştırma**: iki cihaz ayrıntısını açıp karşılaştırın.
4. **Politika önizlemeleri**: yerleşik örneği veya [4. bölümde](#4-politika-etki-önizlemesi) üretilen `policy-preview.json` dosyasını yükleyin.
5. **Termivar Web değerlendirmeleri**: tamamlanmış ve eksik örnekleri, **Rapor karşılaştırması** sekmesinde de karşılaştırma örneğini yükleyin.
6. **Dil / Language** menüsünden İngilizceye geçin.

Konsol hiçbir cihaza veya tarayıcıya bağlanmaz. Canlı API kipi için envanter API'sinin aynı HTTPS origin'inde olması ve dışarıda üretilmiş bir operatör token'ı gerekir. Bu kip gerçek bir IdP ile kabul edilmedi.

## 4. Politika etki önizlemesi

```powershell
New-Item -ItemType Directory -Force demo-output | Out-Null   # çıktı dizini önceden var olmalıdır
python -B -m security_platform.policy_contracts.cli preview --input examples/policy-preview.json --hbf-root <HostBasedFirewall kaynak dizini> --output demo-output/policy-preview.json
python -B -m security_platform.policy_contracts.cli check-preconditions --input examples/policy-preconditions.json --output demo-output/policy-preconditions.json
python -B -m security_platform.policy_contracts.cli validate-rollout --input examples/policy-rollout.json --evaluation-time 2030-01-01T00:30:00Z --output demo-output/policy-rollout.json
```

Kurulumdan sonra aynı araç `security-policy` adıyla da kullanılabilir.

**Çıkış kodları:**

- **0**: çıktı dosyası yazıldı. Dosyadaki `status` ve `blocker_codes` alanlarını okuyun.
- **1**: girdi reddedildi. stderr'de sabit bir kod görünür; mevcut çıktı dosyası değişmez. 1 ile dönen durumlar:
  - şema hatası (`policy_input_invalid`),
  - açıkça verilen `--hbf-root` yüklenemezse (`evaluator_unavailable`),
  - evaluator yüklüyken geçersiz politika (`invalid_policy_bundle`),
  - evaluator yüklüyken geçersiz senaryo (`invalid_scenario`),
  - evaluator yüklüyken aynı ağ iki zone'da bulunursa (`ambiguous_equal_prefix_zones`).

Politika, senaryo ve zone kontrolleri evaluator gerektirir. `--hbf-root` verilmezse şema açısından geçerli her istek `blocked` / `evaluator_unavailable` olarak yazılır.

Örneklerin sonuçları:

- Önizleme örneği ALLOW → DENY değişikliğini gösterir.
- Önkoşul ve rollout örneklerinde gerçek revision kanıtı bilerek yoktur; sonuçları `precondition_evidence_missing` ve `would_pause` olur.
- `execution_authorized` her zaman `false` kalır.

**`--hbf-root` altındaki evaluator, aracın çalıştırdığı yerel Python kodudur.** Yalnız güvendiğiniz bir HostBasedFirewall checkout'unu gösterin.

## 5. Termivar Web çevrimdışı analist zinciri

```powershell
python -B scripts/run_offline_chain.py --workspace <depo dışında yeni boş dizin> [--termivar-root <Termivar checkout'u>] [--phase30-delivery-zip <Phase30 teslim ZIP'i>]
```

Çalıştırıcı şunları yapar:

1. Araçların gerektirdiği sabit workspace düzenini kurar: deponun gerçek bir kopyası ve `outputs/`.
2. Her fazın belgelenmiş komutlarını sırayla çalıştırır.
3. Üretilen her dosyayı [examples/offline-chain/](../examples/offline-chain/README.md) içindeki kayıtlı SHA-256 değerleriyle karşılaştırır.

| Verilen girdiler | Çalışan fazlar |
| --- | --- |
| Yalnız depo | 16–19 (değerlendirme intake'i → teslim → inceleme paketi → HTML inceleme masası → uzlaştırılmış müşteri taslağı) |
| `--termivar-root` | 16–30 |
| `--termivar-root` ve `--phase30-delivery-zip` | 16–44 |

Gerekli girdisi verilmeyen fazlar `NOT_RUN` olur. Workspace'in bulunduğu dosya sistemi hard link desteklemelidir (Windows'ta NTFS).

Tam eşleşen bir çalıştırma, mevcut araç ve girdilerin kayıtlı demo çıktılarını birebir yeniden ürettiğini gösterir. Herhangi bir bulgunun doğru olduğunu kanıtlamaz; yetkili bir değerlendirme de değildir.

**Analist kararlarının müşteri taslağına geçmesi:** İnceleme masasında verilen kararlar reviewer ve zaman taşımaz. Teslim oluşturucu da bu kararları müşteri taslağına almaz. Kararı kimin, ne zaman beyan ettiğini kaydetmek için [commercial_review_attribution](../tools/commercial_review_attribution/README.md) aracını `finalize_desk` ile `reconcile_review` arasında çalıştırın. Bu araç:

- hiçbir şeyi doğrulanmış saymaz,
- karar değiştirmez,
- overlay'deki her karara aynı reviewer referansını ve zamanı yazar.

Faz araçları yalnız commit'li demo veri setiyle çalışır ([10. bölüm](#10-bilinen-sınırlar-ve-açık-engeller)).

## 6. Envanter API'si (ileri düzey)

Gerekenler:

- ayrı migration ve runtime rolleri olan PostgreSQL,
- RFC 9068 `at+jwt` erişim token'ı üreten bir RS256 IdP ve onun public JWKS dosyası,
- bir TLS sertifikası.

Eksik ayar servisi durdurur; kimlik doğrulamasız bir kip yoktur.

| Değişken | Anlam |
| --- | --- |
| `SP_DATABASE_URL` / `SP_MIGRATION_DATABASE_URL` | Runtime ve şema sahibi `postgresql+psycopg://` URL'leri |
| `SP_OPERATOR_ISSUER`, `SP_OPERATOR_AUDIENCE`, `SP_JWKS_FILE` | Sabit HTTPS issuer, audience ve yerel public JWKS |
| `SP_ALLOWED_HOSTS` | Host başlığı izin listesi |
| `SP_CREDENTIAL_TTL_SECONDS` | Cihaz kimlik bilgisi ömrü. Varsayılan 86400, en fazla 30 gün. Yenileme bu süreden uzun ömür isteyemez. |
| `SP_MAX_DEVICES_PER_TENANT` | Aktif (iptal edilmemiş) cihaz sınırı |
| `SP_MAX_AUDIT_EVENTS_PER_TENANT` | Audit sınırı. Cihazdan gelen olay önce en eski cihaz olayını siler; tekrarlanan cihaz işlemleri yönetim geçmişini silemez. Yönetim olayları en eski olayı siler. |
| `SP_REQUESTS_PER_MINUTE` | İstemci IP'si başına istek bütçesi |

Komut sırası `migrate`, `create-tenant`, `set-membership`, `serve` şeklindedir ([README](../README.md#kurulum)). Ayrıntılar:

- API sözleşmesi: [API_V1.tr.md](API_V1.tr.md)
- Roller ve haklar: [OPERATIONS.tr.md](OPERATIONS.tr.md)

`python -B scripts/demo_acceptance.py`, uçtan uca kabul testini çalıştırır: iki tenant, üç cihaz, yerel test CA'sı ve JWKS. Test, workspace PostgreSQL fixture'ına karşı çalışır. Bu fixture'ı yöneten `scripts/managed_postgres.py` yalnız Windows'ta çalışan bir test altyapısıdır, üretim kurulumu değildir.

**Cihaz kimlik bilgilerinin süresi dolar.** Süre dolmadan yenileyin:

```powershell
security-snapshot --rotate-credential --credential-file <özel device.json> [--ca-file <CA paketi>]
```

Yeni sır aynı korumalı dosyaya atomik olarak yazılır ve hiçbir yerde yazdırılmaz. Sunucu eski sırrı aynı işlemde iptal eder. Bu yüzden yanıt kaybolursa cihaz iptal edilip yeniden kaydedilmelidir.

Özel veya kurumsal CA için `--ca-file` kullanın. Sertifika ve hostname doğrulaması hiçbir zaman kapatılmaz.

## 7. Testler

```powershell
python -B -m pytest -q -p no:cacheprovider
```

- `integration` ve `e2e` testleri PostgreSQL fixture'ı ister ([OPERATIONS.tr.md](OPERATIONS.tr.md)). Fixture yoksa bağlantı hatasıyla düşerler; bunları geçmiş saymayın.
- Windows'ta bir POSIX izin testi atlanır. Symlink oluşturulamıyorsa bir symlink testi de atlanır.
- Tam zincir testi yalnız `SP_TERMIVAR_ROOT` ve `SP_PHASE30_DELIVERY_ZIP` tanımlıysa çalışır.

## 8. Sorun giderme

| Belirti | Neden | Ne yapmalı |
| --- | --- | --- |
| `serve.py` `preview_build_unavailable` veriyor | Derlenmiş konsol yok veya `build-manifest.json` ile uyuşmuyor | Paketlenmiş konsolu kullanın veya `pnpm build` çalıştırın |
| `preview_port_unavailable` | Port kullanımda | Başka bir `--port` seçin |
| `security-policy` exit 1 / `evaluator_unavailable` | `--hbf-root` yüklenebilir bir HostBasedFirewall kökü değil | HostBasedFirewall checkout kökünü verin |
| `security-policy` exit 1 / `policy_input_invalid` veya başka bir kod | Şema veya politika kuralı | `examples/` ile karşılaştırın; hata durumunda çıktı ezilmez |
| `offline_chain: workspace_inside_repository` / `workspace_not_empty` | Workspace depo içinde veya dolu | Depo dışında yeni bir dizin kullanın |
| `offline_chain: result=FAILED … MISMATCH` | Sabitlenmiş bir dosya veya araç davranışı değişti | `W/run-logs/` dizinini okuyun; kayıtlı hash'leri yenileriyle değiştirmeyin |
| `task_reconciliation: rejected: <kod>` | Sabit ret kodu ([IMPORT_AND_VALIDATION](commercial/operations/phase44/IMPORT_AND_VALIDATION.tr.md)) | Kodun gösterdiği girdiyi düzeltin |
| `serve` `Missing required setting: …` veriyor | Gerekli ortam değişkeni yok | [6. bölümdeki](#6-envanter-apisi-ileri-düzey) değişkenleri ayarlayın |
| Entegrasyon testleri bağlantı zaman aşımı veriyor | PostgreSQL fixture'ı çalışmıyor | Fixture'ı başlatın ([OPERATIONS.tr.md](OPERATIONS.tr.md)) veya bu testleri çalıştırılmamış sayın |

## 9. Güvenlik notları

- **Sırlar:** Sırlar argümanlardan değil, yalnız korumalı dosyalardan veya ortam değişkenlerinden okunur. Hatalar sabit kodlarla bildirilir; yol, token veya politika içeriği yazdırılmaz.
- **Operatör erişimi:** Erişim yalnız issuer/subject anahtarlı DB üyeliğinden gelir. Token'daki rol, tenant veya e-posta claim'leri yetki vermez.
- **HTTP sınırı:** HTTPS zorunludur; tek istisna, açık test bayrağıyla yalnız loopback'tir. Ayrıca Host izin listesi, origin kontrolü, istek bütçesi ve gövde boyutu/derinlik sınırları uygulanır.
- **Çevrimdışı araçlar:** Yalnız katı JSON, sınırlı boyut ve göreli yol kabul ederler. Arşivi diske açmazlar, çıktıyı ezmezler ve deterministik çalışırlar.
- **Evaluator kaynağı:** Politika önizlemesi seçtiğiniz evaluator kaynağını çalıştırır. `--hbf-root` dizinini güvenilir kod olarak ele alın.
- **Konsol:** Dosya ve token'ı yalnız sayfa belleğinde tutar ve katı CSP uygular.

Bu özellikler depodaki otomatik testlerle sınanır. Bağımsız sızma testi, üretim dağıtım incelemesi veya üçüncü taraf denetimi yapılmamıştır.

## 10. Bilinen sınırlar ve açık engeller

En yüksek etkiden başlayarak:

1. **Üretim IdP'si, dağıtımı ve veritabanı işletimi yok.** Envanter API'si yalnız yerel fixture'larla kabul edildi: test issuer/JWKS, yerel TLS CA'sı ve taşınabilir PostgreSQL. Gerçek bir IdP, konsolun canlı kipi için ters vekil, yedekleme, yüksek erişilebilirlik ve izleme sağlanmaz.
2. **Konsolun yeni içe aktarma sınırları henüz derlenmedi.** Bu sürümdeki kaynak değişikliği konsolun içe aktarma sınırlarını yükseltiyor; böylece 100'den fazla bulgulu Termivar Web değerlendirmeleri ve CLI'nin üst sınırındaki politika önizlemeleri açılabilecek. Bu değişiklik Node bulunmadığı için derlenmedi. Büyük gerçek dosyalarla göstermeden önce `pnpm typecheck` ve `pnpm build` çalıştırıp yeniden kontrol edin.
3. **Analist zinciri yalnız demo veri setiyle çalışır.**
   - Intake yalnız örnekteki yetenek ve kategori kümesini kabul eder.
   - Kapsam planlayıcısı tek bir sabit Termivar commit'ini kabul eder.
   - Sonraki fazlar önceki çıktıların hash'lerini sabitler.

   Müşterinin kendi Termivar Web çıktısını işlemek için bu izin listelerinin ve sabitlerin incelenmiş veri girdilerine dönüştürülmesi gerekir.
4. **Vaka paketi (faz 22) karar içeren vakaları reddeder.** Müşteri taslağı atfedilmiş kararları taşıyabilir. Vaka ve portföy görünümleri ise yalnız incelenmemiş vakaları gösterir.
5. **Kimlik bilgisi yaşam döngüsü manueldir.** Yenileme açık ve elle yapılan bir işlemdir. Yanıt kaybolursa cihaz yeniden kaydedilmelidir. İptal edilmiş cihaz satırları saklanır; bunları silen bir komut yoktur. Bir tenant'ta yaklaşık 10.000'den fazla cihaz satırı birikirse sayfalı cihaz listesi en yeni cihazlara ulaşamaz. Bu cihazlara kimlikleriyle ve audit kaydı üzerinden erişilebilir.
6. **Ürün lisansı ve ticari şartlar yok.** Bu karar ürün sahibinindir.
7. **Windows kabulü yapılmadı.** Gerçek HostBasedFirewall yaşam döngüsü, enforcement ve imzalı artefakt kabulü `NOT_RUN` durumundadır ([WINDOWS_ACCEPTANCE_PLAN.tr.md](WINDOWS_ACCEPTANCE_PLAN.tr.md)).

## Başvuru belgeleri

- **Envanter API'si:** [API_V1.tr.md](API_V1.tr.md), [ARCHITECTURE.tr.md](ARCHITECTURE.tr.md), [THREAT_MODEL.tr.md](THREAT_MODEL.tr.md), [OPERATIONS.tr.md](OPERATIONS.tr.md), [ACCEPTANCE.tr.md](ACCEPTANCE.tr.md)
- **Politika:** [POLICY_CONTRACT_V1.tr.md](POLICY_CONTRACT_V1.tr.md), [POLICY_PREVIEW_ACCEPTANCE.tr.md](POLICY_PREVIEW_ACCEPTANCE.tr.md)
- **Konsol:** [operator-console/README.md](../operator-console/README.md), [quick start (EN)](../operator-console/docs/QUICKSTART.en.md), [yetenek matrisi](../operator-console/docs/CAPABILITY_MATRIX.tr.md)
- **Ticari pilot paketi ve analist operasyonları:** [docs/commercial/README.tr.md](commercial/README.tr.md) ve `docs/commercial/operations/phaseNN/`.

Faz dosyaları tarihsel teslim kayıtlarıdır. İçlerindeki "yeniden çalıştırma" veya "bütçe kapandı" notları o fazın nasıl teslim edildiğini anlatır; araçların kullanımını kısıtlamaz.
