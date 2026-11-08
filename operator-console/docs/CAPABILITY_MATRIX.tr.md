# Mevcut yetenekler ve açık kabul kapıları

Bu matris mevcut kaynak ve teslim kayıtlarını özetler. **Konsolda kullanılabilir olmak, cihazda kurulu/koruyor veya bağımsız doğrulanmış olmak değildir.** Statik katalog `availability` ve `verification` alanlarını ayrı tutar. Kurum/cihaz sağlığı, lisans hakkı, SLA veya ticari uygunluk kararı üretmez.

## Ürün ve bileşenler

| Giriş | Bugün konsolda mevcut | Kaynak üründe/serviste ayrı olan | Henüz sunulmayan veya kanıtlanmayan |
|---|---|---|---|
| HostBasedFirewall | Örnek/API cihazının bildirdiği durum, ayrıntı, iki cihaz bildirimi karşılaştırması ve seçili ürün raporu. | Windows odaklı yerel WinDivert/politika/dashboard/servis kaynak ürünü; bu konsol bunları çalıştırmaz. | Gerçek Windows kabulü, yayıncı imzalı dağıtım ve canlı enforcement bu kaynak tesliminden kanıtlanmaz; merkezden policy push yok. |
| Termivar | Desteklenen yerel assessment/ayrı incomplete tanı JSON'u, JSON-only manifest ilişkisi ve hazır comparison incelemesi. | Termivar'ın kendi kaynak/CLI değerlendirme ve rapor üretme yolu. | Konsolda scan/runtime/target isteği yok; artefakt parse, producer/target/findings/remediation doğrulaması değil. |
| Policy Impact Workbench | Mevcut CLI preview'sinin base/candidate/adapter/preview kimlikleri, sınırlı senaryo farkları ve eksik kanıt açıklaması. | Saf source evaluator ve yürütülemeyen precondition/rollout sözleşmeleri; ayrı draft/staged lab. | Gerçek revision/lineage otoritesi, desired/executor, cihaz uygulama veya verification yok. Lab `unbound`/`not_established` kalır. |
| Security Platform | Tenant/device/product inventory, rol kapsamlı audit görünümü; örnek kip ve mevcut GET adapter'ı. | Ayrı FastAPI/PostgreSQL kimlik, enrollment/credential ve snapshot servisleri. | Frontend yeni auth/enrollment/snapshot yetkisi vermez. Gerçek IdP/kurumsal üretim dağıtımı ve canlı frontend API kabulü yapılmadı. |
| Antivirus | Planlanan ürün açıklaması: `planned/unavailable`. | Henüz etkin motor sunulmuyor. | Malware detection, tarama, kurulum, gerçek zamanlı AV koruması ve lisans/abonelik eylemi yok. |

Ürün Merkezi/rehber yalnız mevcut sayfalara bağlanır. Demo cihazlar gerçek filo, yerel dosya bir cihaz snapshot'ı, dolu rapor güncel koruma kanıtı değildir. Büyük ekran kodunun lazy ayrılması ayrı bir yükleme değişikliğidir; yeni güvenlik yeteneği eklemez.

## İlk ücretli kurumsal ürün için kapanmamış kapılar

Aşağıdakiler yeni uydurulmuş satış politikaları değildir; mevcut kabul/threat model/otorite kayıtlarının açıklarıdır. Bu matris yapılmamış işi başarısız testle, verilmemiş kararı eksik kodla karıştırmaz.

| Kapı | Belgelenmiş mevcut durum | Neden bu teslimatla kapanmaz? |
|---|---|---|
| Gerçek kurumsal IdP ve canlı API/operatör entegrasyonu | **Yapılmadı / not_run.** Fixture issuer/TLS/DB sonuçları tarihsel; kurumsal IdP ve frontend canlı bağlantısı kabul edilmedi. | UI, token üretmez veya SSO kurmaz. Gerçek provider/audience/JWKS/TLS/Host ve işletim bağının kabulü ayrı. [ACCEPTANCE](../../docs/ACCEPTANCE.tr.md), [OPERATOR_CONSOLE](../../docs/OPERATOR_CONSOLE.tr.md). |
| İmzalı artifact ve yetkili Windows ortamı | **Sağlanmadı/NOT_RUN.** Hedef build/mimari, iki gerçek hesap/SYSTEM, yayıncı artifact'ı ve kurtarma/işlem kapsamı seçilmiş kabul girdileri değil. | Derleme veya hash, yayıncı imzası/OS application-control izni/gerçek hesap kabulü değildir. [Windows planı](../../docs/WINDOWS_ACCEPTANCE_PLAN.tr.md). |
| Gerçek HBF yaşam döngüsü ve enforcement | **12 vaka NOT_RUN; symlink dalı SKIP.** SCM/reboot/UAC/native profiles/driver drop-reinject/NAT/uyku-VPN ve 24–72 saat kabulü açık. | Kaynak testleri, SNIFF veya kısa süreç gözlemi gerçek filo/performans/kesinti kabulü sayılmaz. [Windows matrisi](../../docs/WINDOWS_ACCEPTANCE_PLAN.tr.md), [HBF kabulü](../../../HostBasedFirewall-main/WINDOWS_ACCEPTANCE.tr.md). |
| Gerçek policy revision/lineage otoritesi ve sorumlusu | **Kararlaştırılmadı / not_proven.** Yetkili writer sınırı, bütün trial/backup/recovery yazıcılarının bağı ve config commit/runtime activation kabul sahibi ayrı seçilmeli. | Lab draft/staged revision, inventory sequence veya legacy hash gerçek cihaz revizyonu değildir. [Kaynak/otorite matrisi](../../docs/POLICY_REVISION_SOURCES.tr.md). |
| Restore/reimage/clone sonrası güven | **not_proven / rollback_protection=not_established.** Yeniden bağlama yetkilisi ve güvenilir referans kararı açık. | Tutarlı eski kopyanın geri getirilmesi yalnız içerik/hash ile her durumda saptanamaz; bu UI attestation sağlamaz. [Revision lab kabulü](../../docs/POLICY_REVISION_LAB_ACCEPTANCE.tr.md). |
| Üretim DB sürekliliği ve ölçek işletimi | **Yapılmadı / not_run.** Üretim HA, backup/restore/felaket tatbikatı ve çok-worker dağıtık limitler dış kabulde. | Sahip olunan yerel PostgreSQL stop/start fixture'ı üretim kurtarma tatbikatı değildir. [ACCEPTANCE](../../docs/ACCEPTANCE.tr.md), [THREAT_MODEL](../../docs/THREAT_MODEL.tr.md). |
| Kimlik/anahtar/credential işletimi | Gerçek IdP token ömrü/logout/anahtar rotasyonu ve yayıncı/TLS materyali işletimi bu kayıtta kabul edilmiş değil. | Yerel üyelik iptali uygulanmış olsa da servis insan token'ı için merkezi IdP logout/revocation listesi sunmaz; JWKS dosya değişimi çalışan verifier'ı kendiliğinden yenilemez. [THREAT_MODEL](../../docs/THREAT_MODEL.tr.md), [API V1](../../docs/API_V1.tr.md). |
| Ticari ve işletimsel taahhütler | Bu kaynak teslimi fiyat, müşteri sözleşmesi, SLA, sertifika veya ilk ücretli kurumsal satış uygunluğu kararı tanımlamaz. | Bunların kabul edilmiş olduğu çıkarılamaz; yeni şart/taahhüt burada üretilmez. Teknik ürün gösterimi operasyonel onay değildir. |

Merkezî policy/enforcement, scanner yürütme ve AV motoru ayrıca **mevcut konsol yeteneği değildir**; bir satış varsayımıyla etkinleştirilmez. Gerçek kapsam/otorite ve kullanıcı kararları olmadan bu açıkların kapanmış olduğu raporlanmaz. Bu faz yeni canlı kabul, ticari teklif veya sonraki iş başlatmaz.

## Kanıt düzeyleri

- **Uygulandı:** Kaynakta mevcut UI/adapter davranışı; dosya açma, metadata sınırları ve normal gezinme gibi dar işlevler.
- **Manuel gözlendi:** Yalnız teslim kaydında gerçekten belirtilen örnek tarayıcı akışları.
- **NOT_RUN / not_performed / SKIP:** Yapılmamış kabul veya platform dalı; PASS değildir.
- **Kararlaştırılmadı / sağlanmadı / not_proven:** Gerçek otorite/ortam/sorumlu girdisi veya güven sınırı kurulmamış; örnek veriyle doldurulmaz.

Tarihsel **506 passed / 2 skipped**, yeni frontend veya enterprise kabulü değildir. Bu fazda test/runner/coverage ve canlı IdP/PG/Windows/VM/driver/scanner işleri kullanıcı talimatıyla bekletilir. Gerçek yeni build ve manuel kayıt [DELIVERY](DELIVERY.tr.md) içindedir.
