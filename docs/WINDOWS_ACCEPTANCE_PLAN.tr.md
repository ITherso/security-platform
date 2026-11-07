# Windows kabul hazırlığı: çalıştırılmamış gerçek vaka planı

Bu belge bir runbook ve kanıt biçimidir. Bu turda canlı Windows kurulum/UAC/SCM/driver/reboot/policy işlemi, OS güvenlik ayarı veya trafik deneyi yapılmadı. Gerçek vakaların tamamı **NOT_RUN** durumundadır. Kaynak incelemesi ve sentetik testler, canlı kabul sonucuna çevrilmez.

İncelenen kaynak HBF `1.4.3/74a88ed`; merkez başlangıcı `0.1.0/35f784b` olarak sabittir. Kaynak commit'i bilinmektedir; seçilmiş gerçek dağıtım artifact'ı, Windows build/mimari, VM/fiziksel hedef, gerçek hesap/SID, gözlem ve inceleyen henüz verilmedi. [windows-not-run.json](../tests/fixtures/policy_revision_lab/windows-not-run.json) bu alanları `null` veya boş dizi tutar. Temsili kişi/SID veya sahte onay gerçek şablona konulmaz.

## Kullanıcının sağlayacağı ayrı karar kapıları

| Kapı | Gereken gerçek girdi | Bu turdaki durum |
|---|---|---|
| İzole hedef ve kimlik | Sahip olunan Windows VM/cihaz, hedef build/mimari, iki gerçek hesap, admin ve SYSTEM bağlamına yetkili erişim; gerçek SID'ler | NOT_RUN / sağlanmadı |
| Kurtarma ve işlem yetkisi | VM snapshot'ı veya yedek, yerel konsol, kurtarma yolu; seçilmiş kurulum/reboot/driver/test trafiği kapsamı ve yetkisi | NOT_RUN / sağlanmadı |
| Policy otoritesi | Kaynağın sahibi, bütün yazıcıların revizyona bağlanması; config commit ve runtime activation için ayrı kabul ölçütü | not_proven |
| Restore/reimage/clone | Kimlik/lineage yeniden bağlama yetkilisi ve eski tutarlı kopyalar için kurum politikası | not_proven |
| Merkezî desired yetkisi | İleride desired yazımı ve incelemesine izin veren kurumsal yetki sahibi | sağlanmadı; bu tur desired yok |
| Üretim IdP ve yayın | Gerçek IdP profili, yayıncı sertifikası, imzalı artifact, Windows application-control izni ve dağıtım kabul materyalleri | NOT_RUN / sağlanmadı |

IdP veya yayıncı sertifikasının henüz sağlanmaması offline lab'ı engellemez. Bu materyaller varmış veya kabul edilmiş gibi gösterilmez. İmza, Windows uygulama denetimi izni ve yönetici yetkisi ayrı koşullardır. Koruma kapatma, dosya yeniden adlandırma veya kural atlatma kabul hazırlığının parçası değildir.

## Hedef ve vaka matrisi

Önce kesin build/mimari/VM veya fiziksel hedef ve artifact seçilir. Aşağıdaki eylemler ancak daha sonraki ayrı yetkilendirilmiş işte uygulanır; bu belge bunları başlatmaz.

| Vaka | Sonraki dar deney ve ayrılacak kanıt | Durum |
|---|---|---|
| WIN-01-ARTIFACT | Gerçek uygulama ve Setup yayıncı imzası; hash, sertifika zinciri ve OS izin kararı ayrı | NOT_RUN |
| WIN-02-IDENTITY-ACL | İki gerçek hesap/SYSTEM ile Program Files/ProgramData owner-DACL, düşük yetkili yazma ve scope sınırı | NOT_RUN |
| WIN-03-UAC | Consent iptali, elevated açılış, değiştirilmiş/yerine konmuş executable kimliğinin reddi | NOT_RUN |
| WIN-04-PROCESS-RACE | Sadece sahip olunan disposable süreçler; stale PID/creation, aynı anda iki süreç, yanlış child'a dokunmama | NOT_RUN |
| WIN-05-SCM-REBOOT | Gerçek imzalı kurulumda start/stop/restart, tek engine, beklenmeyen child failure ve insan reboot'u | NOT_RUN |
| WIN-06-POLICY-ACTIVATION | Disk commit, evaluator activation ve sahip olunan servis üzerindeki dar enforcement üç ayrı gözlem | NOT_RUN |
| WIN-07-TRIAL-RECOVERY | Confirm/cancel/expiry, prepared/restoring kesintisi ve bozuk normal audit fallback'i | NOT_RUN |
| WIN-08-BACKUP-RESTORE | Çok dosya restore, native hata, compensating rollback ve unrelated edit'in korunması | NOT_RUN |
| WIN-09-NATIVE-PROFILES | Sahip olunan `.exe` için yön/profil kuralları, gerçek HOME/PUBLIC değişimi ve yeni bağlantı | NOT_RUN |
| WIN-10-DRIVER-TRAFFIC | Sniff/loopback gözlemi, drop/reinject, geçici engel ve NAT ayrı; sadece yetkili kontrollü hedefler | NOT_RUN |
| WIN-11-INTERRUPTION-RESTORE | Process crash, reboot, varsa ayrı onaylı güç kaybı; tutarlı eski restore/clone ve yeniden bağlama | NOT_RUN |
| WIN-12-SOAK-PHYSICAL | Önceden seçilmiş 24–72 saat/iş yükü/eşikler; uyku/VPN/NAT ve fiziksel hedefler ayrı | NOT_RUN |

VM sonucu fiziksel filo kabulü değildir. Process kill, API/server restart veya SQLite reopen fiziksel güç kaybı kabulü değildir. Kısa CPU/RSS ölçümü performans kabulü olmaz. Loopback/SNIFF/RECV_ONLY ile paket görmek drop/reinject veya canlı engelleme kanıtı değildir. ALLOW başka native DENY kurallarını geçersiz kılmaz.

Başarısızlıkta durma ölçütü önceden kaydedilir: artifact/kimlik değişimi, kurtarma konsoluna erişim kaybı, yetkisiz süreç veya ilgisiz trafik etkisi, config recovery'nin pending kalması, sahip olunan kaynak sınırının aşılması. Sonraki adımın sahibi gerçek gözlemi incelemeden deney otomatik ilerlemez. Bu tur hiçbir kişi adına inceleme/onay kaydı oluşturmaz.

## Sıkı kanıt şeması

`tools/policy_revision_lab/windows_evidence.py`, `WindowsEvidenceReport` ve `validate_windows_evidence()` sağlar. `schema_version` tam integer `1` olmalıdır; bool/float/string dönüşümü kabul edilmez. Bilinmeyen alanlar reddedilir. DTO'lar frozen ve derin tuple temsillidir; `model_copy`/`model_construct` girdileri tekrar doğrulanır.

Üst alanlar: `schema_version`, `evidence_origin` (`real` veya `synthetic`) ve 1–64 `cases`. Her vakanın alanları:

| Alan | Anlam ve biçim |
|---|---|
| `case_id` | 1–64 karakter, benzersiz ASCII vaka kimliği |
| `source_commit`, `artifact_sha256` | 40 ve 64 küçük hexadecimal karakter; NOT_RUN planında bilinmeyen değer null kalır |
| `windows_build`, `architecture`, `environment` | Bildirilen build, x64/arm64/x86 ve vm/physical; hedef seçilmemişse null |
| `accounts` | En çok 8 gerçek bildirilen `account_name`, SID ve standard_user/administrator/SYSTEM bağlamı; şablonda boş |
| `preconditions`, `action`, `expected` | Önceden yazılan plan; sırasıyla 1–16 koşul ve bounded metinler |
| `observed` | Sonradan bildirilen gözlem; NOT_RUN için null |
| `evidence_refs` | En çok 32 lexical relative referans, SHA256 ve log/screenshot/artifact/signature_report/operator_note/self_report türü |
| `status` | NOT_RUN, PASS, FAIL, SKIP veya BLOCKED; tamamı bildirilen durumdur |
| `reviewer`, `review_status` | Bildirilen inceleyen; not_reviewed veya reported_reviewed. Kimliği doğrulanmaz; NOT_RUN için null/not_reviewed |

NOT_RUN, gözlem/kanıt/inceleme iddiası taşıyamaz. Diğer durumlar doldurulmuş context ve evidence referansı ister; bunun varlığı doğruluk kanıtı değildir. Aynı referans için çelişen hash, yinelenen case ID/SID, artifact hash tutarsızlığı ve göreli yol kaçışı biçim hatasıdır. Referanslar açılmaz, hash yeniden hesaplanmaz, imza veya Windows/SID sorgulanmaz. Bu yalnız biçim/tutarlılık denetimidir; bir dosyanın var olduğu bile iddia edilmez.

Kaynak kökünde açık input/output ile format raporu:

```powershell
./.venv/Scripts/python.exe -m tools.policy_revision_lab.cli windows-report --input tests/fixtures/policy_revision_lab/windows-not-run.json --output ./windows-format-result.json
```

`windows-synthetic-format.json`, gerçekten yapılmış test olmayan açık sentetik PASS/inceleyen/hash örneğidir. `evidence_origin` dış raporda real diye yazılsa bile validator gerçekliği doğrulamaz. Her başarılı biçim raporunda sabit alanlar kalır:

```json
{
  "status": "format_consistent",
  "validation_scope": "format_consistency_only",
  "windows_acceptance": "not_evaluated",
  "independent_verification": "not_performed",
  "reviewer_identity": "not_authenticated",
  "authorization": "not_evaluated",
  "execution_authorized": false,
  "real_acceptance_established": false
}
```

`reported_status_counts.PASS`, yalnız input'taki PASS beyanlarının sayısıdır; geçmiş test sayısı veya gerçek Windows kabulü değildir. İmza raporu, hash, self-report veya sentetik fixture tek başına independent verification'a yükseltilmez. Gelecekteki gerçek raporlara token, credential, argv/env dökümü veya gereksiz kişisel ağ verisi eklenmemelidir.

## Mevcut araçların sonraki aşamadaki yan etkileri

HBF `WINDOWS_ACCEPTANCE.tr.md`, `LONG_OBSERVATION.tr.md`, `SERVICE_INSTALLATION.tr.md` ve `packaging/DISTRIBUTION_HARDENING.tr.md` kendi kapsamlarında okunmalıdır. `src/windows_validation.py` default readiness OS sorguları yapar; `--connections-check` geçici soket açar; `--loopback-check` driver açabilir/yükleyebilir. Boot doğrulaması insan reboot'u ister. Soak aracı zaten çalışan engine'i gözler; gözlem tamamlanması tek başına enforcement/performans kabulü değildir. Bu araçların hiçbiri bu hazırlık işi kapsamında çalıştırılmadı.

Gerçek writer entegrasyonunun açıkları [POLICY_REVISION_SOURCES.tr.md](POLICY_REVISION_SOURCES.tr.md), laboratuvar kabulünün sınırlı anlamı [POLICY_REVISION_LAB_ACCEPTANCE.tr.md](POLICY_REVISION_LAB_ACCEPTANCE.tr.md) içindedir. Sonraki adım, kullanıcı tarafından sağlanmış gerçek ortam ve yetkiyle ayrıca kararlaştırılır; otomatik uygulama işi değildir.

## Bu hazırlığın test kaydı

Son birleşik koşu 506 passed / 2 skipped / 1 mevcut uyarı, 94,21 saniyedir; bunun 51 testi yalnız bu Windows biçim doğrulayıcısını sınar. Yeni lab'ın 162 geçen testi ve native owner/DACL fixture sonuçları gerçek Windows kabulü değildir. Backend symlink yaratım deneyi WinError1314 nedeniyle SKIP kaldı; eski POSIX mode kontrolü ikinci ayrı skip'tir. Bu runbook'taki 12 gerçek vaka hâlâ NOT_RUN, gerçek gözlem ve inceleyen alanları hâlâ boştur. Depo process kill ve owned PostgreSQL restart kanıtı fiziksel güç kaybı/SCM/reboot kanıtına çevrilmez.
