# Saf politika önizleme sözleşmesi V1

Bu sürüm, açıkça verilen HBF paket politikalarını ve sınırlı örnek senaryoları karşılaştırır. Sonuç bir aday niyet ve yürütülemeyen dağıtım planıdır. Yeni HTTP endpoint, DB tablosu, migration, cihaz yetkisi, receiver veya policy push eklenmez.

Çekirdek fonksiyonlara bütün girdiler açıkça verilir. Çekirdek ağ, disk, sistem saati, ortam değişkeni, Windows profili, GeoIP dosyası, servis veya COM okumaz. Dosya okuma, kaynak manifest'i hazırlama ve seçilen çıktı dosyasını yazma offline CLI sınırındadır.

## Girdi ve sürümler

`PolicyBundle`, strict ve derinlemesine değişmez bir belgedir. Bilinmeyen alan, yanlış scalar tipi, duplicate JSON key ve sonlu olmayan sayı kabul edilmez.

| Alan | V1 anlamı |
|---|---|
| `schema_version` | Strict integer `1`; boolean kabul edilmez. |
| `contract_version` | `sp-hbf-bundle/v1`. |
| `canonicalization_version` | `sp-json-canonical/v1`. |
| `normalization_version` | `hbf-source-normalization/v1`. |
| `ordered_zones` | `{name, cidrs}` elemanlarından oluşan sıralı dizi; zone sözlüğünün tek sıralama kaynağı. |
| `objects` | HBF nesneleri; `zones` burada tekrar verilmez. |
| `policies` | Sıralı politika listesi, default action ve desteklenen HBF alanları. |

Zone, CIDR ve politika dizileri canonicalization sırasında sıralanmaz. JSON nesne anahtarlarının sıralanması, ancak davranışı etkileyen sıra açık dizilere taşındıktan sonra uygulanır. JSONB anahtar sırasından kaynak zone sırası türetilmez.

HBF doğrulayıcılarının sınırları ayrıca geçerlidir. Yerel ek sınırlar: bundle başına 50.000 düğüm, derinlik 20 ve toplam 2 MiB anahtar/metin bütçesi; en fazla 500 politika, 32 senaryo ve senaryo değerlendirmesi başına 64 trace satırı. Kesilmiş trace için toplam satır sayısı ve tamlık bilgisi ayrı tutulur. CLI zarfı en fazla 5 MiB, derinlik 24 ve 110.000 düğüm; çıktı en fazla 8 MiB'dir. Büyük CLI zarfı, içindeki bundle sınırını genişletmez.

## Kaynak semantiği ve korunmuş legacy sorunu

HBF `policy_version(objects, policies)` JSON anahtarlarını sıralar. Eşit prefix uzunluğuna sahip aynı ağ iki ayrı zone'da bulunursa mevcut zone resolver insertion order'a bağlı sonuç verebilir. Dolayısıyla aynı legacy hash, bu koşulda aynı karar davranışını kanıtlamaz.

Bu tur legacy hash'i veya yerel motorun tie-break davranışını değiştirmez. Adapter, hem base hem candidate içindeki CIDR'leri HBF ile uyumlu normalizasyonla karşılaştırır. `(IP ailesi, normalize ağ adresi, prefix uzunluğu)` aynı olup zone adı farklıysa `ambiguous_equal_prefix_zones` üretir. Host bitleri veya eşdeğer IPv6 yazımı bu kontrolü aşmaz. Aynı zone içindeki tekrar, farklı IP aileleri ve farklı prefix uzunluklarındaki longest-prefix örtüşmesi bu belirsizlik değildir.

`PolicyWorkspace.preview().version`, temel snapshot sürümüdür; adayın kimliği olarak kullanılmaz. HTTP preview'nin örtülü yerel saat ve PUBLIC profili bu sözleşmeye taşınmaz. Trial/backup CAS'i ve recovery günlükleri mevcut protokolleriyle korunur.

## Ayrı içerik kimlikleri

| Alan | Bağlanan içerik |
|---|---|
| `legacy_base_version` | Mevcut HBF temel snapshot hash'i; opaque uyumluluk bilgisi. |
| `base_fingerprint` | Normalize base bundle, ordered zones, politika sırası, default action ve sözleşme sürümleri. |
| `candidate_fingerprint` | Aynı gösterimle aday bundle. |
| `adapter_fingerprint` | Adapter/evaluator sözleşmesi, açık kaynak manifest'i ve gerekli runtime sürümleri. |
| `preview_fingerprint` | Base, candidate, adapter, açık senaryolar, kapsam ve normalize karar/trace sonucu. |

Namespace'ler sırasıyla `sp-hbf-bundle-v1:sha256:…`, `sp-hbf-adapter-v1:sha256:…` ve `sp-hbf-preview-v1:sha256:…` biçimindedir. Legacy değer 64 hexadecimal karakter olarak ayrı kalır. Aynı ürün sürüm dizgesi, aynı adapter kimliği anlamına gelmez.

V1 canonical byte gösterimi UTF-8 `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)` sonucudur; RFC 8785 uyumluluğu iddiası yoktur. Dizi sırası korunur. Bundle hash'i normalize `PolicyBundle.model_dump(mode="json")` belgesinin tamamını; adapter hash'i `AdapterIdentity` belgesinin tamamını kapsar. Preview hash'inin girdisi tam olarak şu alanlardır:

```text
contract_version = sp-hbf-preview/v1
base_fingerprint
candidate_fingerprint
adapter_fingerprint
results = ScenarioComparison kayıtlarının sıralı JSON gösterimi
authorization = not_evaluated
execution_authorized = false
verification = not_performed
scope = packet_policy_preview_only
```

Her `results` kaydı açık senaryoyu, base/candidate kararlarını, sınırlı trace'i, trace toplamı/tamlığını ve karar/ilk-eşleşme değişim işaretlerini taşır. Böylece senaryo ve normalize sonuç da hash'e bağlıdır. `legacy_base_version`, bir timestamp veya rastgele plan ID'si bu girdiye ayrıca eklenmez; legacy kimlik yeni base fingerprint'inin yerine kullanılamaz.

Manifest, HBF `config_store.py`, `document_limits.py`, `policy_objects.py`, `policy_engine.py` ve platform `errors.py`, `immutable.py`, `models.py`, `fingerprints.py`, `zone_safety.py`, `preview.py`, `hbf_bridge.py` dosyalarının gerçek byte kimliklerini bağlar. Python implementation/sürümü ve Pydantic sürümü ayrıca kapsanır. CLI yalnız açıkça seçilmiş, desteklenen HBF kaynak dizininden bu kimliği hazırlar; politika belgesi modül, dosya yolu veya komut seçemez. Kaynak yükleme, yerel operatörün güvenilir kod seçimidir; kötü amaçlı kaynak için sandbox veya üretici doğrulaması değildir. Saf fonksiyon hazır adapter kimliğini alır. Rastgele ID, üretim zamanı, sistem saati ve örtülü saat dilimi önizleme fingerprint'ine girmez.

Bu değerler içerik kimliğidir. İmza, üretici kimliği, izin, onay, güncellik veya uygulanma kanıtı değildir. Geçersiz girdinin diagnostik kimliğinin bulunması, girdiyi kabul edilmiş artefact yapmaz. Belirsiz veya bloke önizleme başarılı preview kimliği üretmez.

## Senaryo ve evaluator sınırı

Her `PreviewScenario`, `scenario_id`, kaynak/hedef IP, TCP/UDP, hedef port ve gerekli bağlamı taşır. `network_profile` açık HOME/WORK/PUBLIC değeridir; `evaluation_local_time`, açık `HH:MM:SS[.ffffff]` değeridir. Ülke koşulları için gereken `src_geo` ayrıca sağlanır. Bu alanların bağlam için eksik olması `insufficient_context` üretir; eksik profil PUBLIC'e tamamlanmaz.

Yerel saat, senaryo girdisidir. Cihaz saatinin veya saat diliminin doğrulanması değildir; UTC'den örtülü dönüşüm yapılmaz. Base ve candidate aynı senaryo, profil, saat ve adapter ile değerlendirilir. Mevcut saf HBF evaluator'ı kullanılır; merkezde ikinci veya yaklaşık bir karar motoru yoktur. Evaluator yoksa `evaluator_unavailable` döner.

Başarılı önizleme, karar değişimini, ilk eşleşen politikayı ve sınırlı trace'i gösterir. Kapsam yalnız `packet_policy_preview_only` değeridir. Native Windows uygulama kuralları, IP/domain listeleri, geçici engeller, whitelist, bağlantı durumu, NAT tablosu ve gerçek sürücü davranışı bu karşılaştırmanın dışındadır. `DENY_TEMP` timer veya blok oluşturmaz; NAT bilgisi yalnız politika niyetidir.

Çıktıdaki sabit güven alanları:

```json
{
  "authorization": "not_evaluated",
  "execution_authorized": false,
  "verification": "not_performed",
  "scope": "packet_policy_preview_only"
}
```

Dış DTO bu alanları approved/verified/true yapamaz. `status=ok`, belirtilen sınırlı önizlemenin üretildiğini söyler; uygulama veya yetki onayı değildir.

## Kaynak, aday niyet ve beyan ayrımı

| Kavram | Sınır |
|---|---|
| `source` | Açıkça sağlanan base belge ve kimlikleri; üretici/güncellik kendiliğinden doğrulanmaz. |
| `proposed_desired` | Önizlenen aday niyet; etkin merkezi atama oluşturmaz. |
| `desired` | Gelecekte yetkilendirilip dayanıklı kaydedilecek niyet; bu tur yoktur. |
| `received_reported` | Artefact'ın alındığına ilişkin bağlı cihaz beyanı; uygulanma değildir. |
| `applied_reported` | Belirli bileşen/kapsam için etkinleştirme beyanı; bağımsız doğrulama değildir. |
| `verified` | Tanımlı kapsam ve güvenilir doğrulama yöntemi gerektirir; bu tur operasyonel olarak gerçekleşmez. |

Saf receipt denetimi yalnız biçim, bağ ve tutarlılık kontrolüdür. Tenant, cihaz, ürün, enforcement kapsamı, plan/revision, aday fingerprint ve kaynak revision bağları tutarlı olmalıdır. Bearer kimliği, hash eşitliği veya readback beyanı bu kontrolü bağımsız doğrulamaya yükseltmez. Paket politika motoru ve native Windows kuralları tek applied alanında birleştirilmez.

`PolicyReceipt`, yalnız `received_reported` veya `applied_reported` türünü ve reported success/failure değerini taşır. `applied_reported` için bir `resulting_revision` beyanı gerekir; `received_reported` bu sonuç revision'ını taşıyamaz. Bu alan gerçekte uygulama yapıldığının kanıtı değildir. `validate_receipt(receipt, expectation, now=...)`, zaman penceresini, eskimeyi, gelecek zamanı ve bütün bağları açık girdilerle denetler. Başarılı biçim sonucu `receipt_consistent_fixture_only` değeridir; eksik kanıt veya uyuşmazlık ayrıca raporlanır.

## Ayrı CAS önkoşulları

Controller CAS, beklenen merkezi niyet revision/lineage'ını; endpoint CAS ise cihazın beklenen kaynak politika revision/lineage'ını denetler. Buna base, candidate, adapter ve preview kimlikleri ile tenant/cihaz/ürün/enforcement kapsamı bağlanır.

İçeriğin `A → B → A` biçiminde geri dönmesi eski revision'ı geçerli yapmaz. İçerik hash'i geçmişi tek başına bağlamaz. Mevcut HBF ve envanter hizmeti dayanıklı policy revision/lineage üretmediği için bu veri uydurulmaz. Snapshot mesaj sırası, timestamp veya restart'ta sıfırlanan sayaç policy revision yerine kullanılmaz.

Eksik kanıt `precondition_evidence_missing`, uyumsuz bağ/revision `precondition_conflict` sonucudur. Tam eşleşen fixture sonucu `consistent_fixture_only` olabilir; gerçek DB atomik CAS'i veya canlı endpoint kabulü değildir. Base, candidate, adapter veya senaryo değişirse eski preview yeni öneriye taşınamaz.

Offline girdide tenant/cihaz UUID'si bulunması DB üyeliğini veya cihazın varlığını doğrulamaz. Elle hazırlanmış JSON aktör/TenantContext bilgisi yetki kanıtı değildir. Örnek precondition ve rollout dosyalarındaki UUID/fingerprint/revision değerleri fixture verisidir; mevcut envanterden türetilmiş gerçek dağıtım yetkisi değildir.

## Yürütülemeyen dağıtım planı

`ProposedRollout` tek tenant, HBF ürün/kapsamı, değişmez ve tekrarsız hedef listesi, cihaz başına base/CAS bağları, candidate/preview kimlikleri, pilot alt kümesi ve sonraki grupları taşır. Geçerlilik zamanı dışarıdan verilir. Önceki artefact referansı yalnız geri dönüş önerisidir.

En fazla 128 hedef, 16 pilot cihaz, 16 sonraki grup ve grup başına 32 cihaz kabul edilir. Pilot ve gruplar, hedef kümesini tekrarsız ve eksiksiz bölmelidir. Plan geçerliliği en fazla 86.400 saniyedir; bu süre bir yürütme veya cihaz kabul garantisi değildir. Gözlem sayısı en fazla 128, receipt sayısı en fazla 256'dır.

Plan hedeflerini ağdan çekmez, grupları sonradan genişletmez, job veya atama oluşturmaz. Eksik/eski/çakışan beyan, çözülmemiş Windows kabulü ve mevcut olmayan yürütme yolu açık blocker'dır. Saf simülasyon yalnız `would_wait` veya `would_pause` döndürür. Pilotun `applied_reported` beyanı sonraki grubu açmaz ve `verified` sayılmaz.

Sabit blocker'lar `execution_not_implemented`, `windows_acceptance_missing`, `authorization_not_evaluated`, `verification_not_performed` değerleridir. Bunlar dış girdiden kaldırılamaz. Çıktı `execution_plan=not_created`, `next_batch=null`, `rollback=references_only` değerlerini korur. Gerçek `desired` kaydı, gönderim işi veya sonraki gruba geçiş oluşturulmaz.

## Açık dosyalarla offline CLI

Mevcut inventory komutları korunur. Yeni yerel giriş `security-policy` veya aşağıdaki modüldür:

```powershell
.venv\Scripts\python.exe -m security_platform.policy_contracts.cli preview `
  --input examples\policy-preview.json `
  --hbf-root ..\HostBasedFirewall-main `
  --output reports\policy-preview.json

.venv\Scripts\python.exe -m security_platform.policy_contracts.cli check-preconditions `
  --input examples\policy-preconditions.json `
  --output reports\policy-preconditions.json

.venv\Scripts\python.exe -m security_platform.policy_contracts.cli validate-rollout `
  --input examples\policy-rollout.json `
  --evaluation-time 2030-01-01T00:30:00Z `
  --output reports\policy-rollout.json
```

Çıktının parent dizini önceden bulunmalıdır. Preview zarfı `{schema_version, base, candidate, scenarios}`; rollout zarfı `{schema_version, plan, observations, receipts}` alanlarını kullanır. Precondition girdisi expected/observed bağlarını taşır. `--hbf-root` verilmezse önizleme evaluator-unavailable olarak bloke edilir.

CLI stdout'a yalnız sabit `output_written` ve `execution_authorized=false` bildirir. **Exit 0 yalnız çıktı dosyasının yazıldığını gösterir; blocked sonucu da dosyaya yazılabilir.** Kararı okumak için seçilmiş çıktıdaki status/blocker alanlarına bakılmalıdır. Geçersiz girdi exit 1 ve sabit hata kodu verir; yarım başarılı çıktı bırakılmaz. Giriş dosyasının üzerine çıktı yazılmaz; bütün çıktı serialize edilip boyut kontrolünden geçtikten sonra seçilmiş dosya atomik değiştirilir.

`--apply`, `--push`, `--execute`, receiver, polling veya arka plan bağlantısı yoktur. Çıktı politika IP'leri/nesneleri içerebilir; yalnız açıkça seçilen yerel dosyada tutulur. Envanter snapshot'ına, audit'e, Termivar özet deposuna veya normal loga otomatik taşınmaz.

## Korunan yüzey ve açık kapılar

[Yüzey baseline'ı](../tests/fixtures/policy_surface_baseline_v1.json), security-platform `2755336` kaynaklarını ve önizleme turundan önce kabul edilen `9c2ce8c` inventory okuma düzeltmesini ayrı kaydeder. Sonraki sahip onaylı değişiklikler (`cae7c18`; Aşama 2: `171960c`, `45e0482`, `90be449`) `approved_exceptions` altında gerekçeleriyle kayıtlıdır. İki dependency kilidi dahil 40 platform dosyası, gerçek OpenAPI/router yüzeyi, mevcut snapshot ve sender sözleşmesi, Alembic head ve sekiz HBF legacy/recovery/evaluator dosyası kontrol edilir. HBF başlangıcı `74a88ed` olarak kayıtlıdır. Bu baseline bir imza veya yetki kaynağı değildir.

Kalıcı policy revision/lineage kaynağı, gerçek Windows'ta 24–72 saatlik kabul, canlı WinDivert/SCM/reboot/UAC, üretim IdP/sertifika işletimi, imzalı installer ve yetkilendirilmiş dağıtım yürütücüsü bu turda tamamlanmaz. Bu sözleşmeden sonraki yürütme tasarımı ayrı karar gerektirir.
