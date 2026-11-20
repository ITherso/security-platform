# Politika etki inceleme çalışma alanı

**Politika önizlemeleri**, mevcut `security-policy` CLI'nin önceden ürettiği paket politikası önizlemesini yerel tarayıcıda okur. Tarayıcı politika değerlendirmez, HBF kaynak kodu yüklemez ve cihazın etkin politikasını bilmez. Yeni bir evaluator, cihaz bağlantısı veya gönderme/uygulama yolu yoktur. [English guide](POLICY_REVIEW_WORKBENCH.en.md).

## Dosyayı açma ve inceleme

1. Gezinmeden **Politika önizlemeleri** alanını açın. **Politika önizleme dosyası aç** ile tek yerel JSON çıktı dosyası seçin. CLI'nin `--output` dosyası gerekir; base/candidate içeren `--input` belgesi desteklenen çıktı değildir.
2. Sözleşme, sonuç durumu, kapsam ve ayrı kimlikleri okuyun. `ok`, yalnız verilen senaryoların önizlendiğini söyler. `blocked`, karar üretimi için blocker bulunduğunu söyler; başarılı karar gibi okunmaz.
3. Yalnız yüklenmiş senaryolarda arayın ve değişim filtresini kullanın. Bir senaryoyu seçerek base/candidate kararını, ilk eşleşen politikayı ve mevcut sınırlı açıklamayı inceleyin. Aynı karar, aynı koruma anlamına gelmez.
4. Kaynak/hedef gibi ayrıntılar başlangıçta gizlidir. **Ayrıntıları göster** seçimi yalnız bu import içindir. Yeni dosya veya temizleme bu tercihi taşımaz. Tam fingerprint gerekiyorsa ilgili açık genişletmeyi kullanın.
5. Yeni dosya seçebilir veya bellekten temizleyebilirsiniz. Geçersiz yeni dosya, önceki başarılı sonucu yeni dosyanın sonucuymuş gibi bırakmaz.

Sayfa ve TR/EN değişimi geçerli importu korur. Tenant, örnek/API kaynağı, örnek senaryosu veya bağlantı oturumu değişimi ve mevcut erişim temizliği hassas yerel importu konservatif temizler. Sayfayı yeniden yüklemek importu geri getirmez. Rapor taslağı, iki cihaz karşılaştırması ve cihaz ayrıntısı gezinmesi bu alanın veri kaynağı değildir; politika rapora otomatik eklenmez.

## Desteklenen gerçek çıktı

İlk desteklenen tür, `contract_version="sp-hbf-preview/v1"` olan doğrudan **PreviewOutcome** JSON'udur. Bu çıktı kökte `schema_version` taşımaz; CLI girdi zarfındaki sürümle karıştırılmamalıdır. Başarılı ve geçerli bloke sonuçlar desteklenir. Dosya en fazla **512 KiB**, geçerli UTF-8 ve desteklenen kapalı alan/tür/sayı/metin sınırlarına uygun olmalıdır. Duplicate key, geçersiz sayı, desteklenmeyen sürüm ve gerekli kimliklerin eksik/bozuk olması açık hatadır. Geçerli bir bloke sonuçta sözleşmenin izin verdiği `null` kimlikler eksik başarı kanıtıyla doldurulmaz.

`strictJson` ayrıştırıcısı kapalı `sp-hbf-preview-v1` profilini kullanır: derinlik **12**, düğüm **50.000**, tek metin **2.048 UTF-16 kod birimi** (1.024 karakterlik CLI metin alanı karakter başına iki birim gerektirebilir), dizi başına **100** eleman, nesne başına **32** anahtar ve **160.000** token. Alanlara özgü daha dar sınırlar da uygulanır (32 senaryo, değerlendirme başına 64 trace satırı, satır başına 4 gerekçe). Profil, CLI üst sınırları olan 32 senaryo x 2 değerlendirme x 64 trace satırından (yaklaşık 42.000 düğüm ve 128.000 token) boyutlandırılmıştır; bu tür çıktılar 512 KiB tarayıcı sınırı içinde ayrıştırma bütçeleri yüzünden reddedilmez. Daha büyük dosyalar dosya çok büyük hatasıyla reddedilir; veri sessizce kesilmez. CLI'nin **8 MiB** çıktı sınırı tarayıcı import sınırı değildir.

`check-preconditions` ve `validate-rollout` ayrı CLI çıktı türleridir; bu importer onları önizlemeye birleştirmez. PreviewOutcome, controller revision, endpoint revision, ayrı CAS sonucu veya rollout sonucu içermez. Bu alanların anlamı **Mevcut sonuçta bulunmuyor** olur; `consistent_fixture_only`, `precondition_evidence_missing` veya `would_pause` sonucu varmış gibi uydurulmaz. Kaynak dosyada bulunmayan ek bağlam için başka dosya, backend veya evaluator aranmaz.

Önizleme çıktısı başarılı durumda en fazla 32 senaryo, değerlendirme başına en fazla 64 trace satırı ve trace toplamı/tamlık bilgisini taşıyabilir. Sınırlı trace bütün politikanın tam kanıtı değildir. Eksik profil/saat veya gerekli ülke bağlamı için CLI `insufficient_context` üretebilir; UI kesin karar tamamlamaz.

## Kimlikler ve kararların anlamı

| Alan | Neyi tanımlar? |
|---|---|
| `legacy_base_version` | Mevcut HBF temel snapshot hash'i; uyumluluk bilgisi. |
| `base_fingerprint` | Normalize temel bundle ve sürümlü gösterimi. |
| `candidate_fingerprint` | Normalize aday bundle ve sürümlü gösterimi. |
| `adapter_fingerprint` | Kaynak manifest'i, adapter/evaluator sözleşmesi ve runtime kimliği. |
| `preview_fingerprint` | Base/candidate/adapter, açık senaryolar ve normalize sonuçlara bağlı önizleme kimliği. |

Fingerprint'ler birbirinin yerine geçmez; kısaltılmış metin tekil kimlik veya güven kanıtı değildir. Biçim denetimi, fingerprint içeriğini yeniden hesaplama, imza doğrulama veya üretici attestation'ı değildir. Eşit legacy hash aynı davranışı kanıtlamaz: aynı ağın eşit prefix ile farklı zone'larda bulunması legacy resolver'ın zone sırasına bağlı sonucunu gizleyebilir. Mevcut CLI bu belirsizliği bloke eder; workbench eski hash davranışını düzeltmez veya yeniden değerlendirmez. [Asıl politika sözleşmesi](../../docs/POLICY_CONTRACT_V1.tr.md).

`ALLOW→DENY`, yalnız belirtilen senaryo için aday kararın değiştiğini söyler. `DENY→ALLOW` daha güvenli olduğu anlamına gelmez; ALLOW gerçek bağlantı başarısı değildir. DENY her durumda doğru, daha az DENY daha iyi veya eşit karar eşit koruma diye yorumlanmaz. `DENY_TEMP` gerçek timer/blok oluşturmaz; NAT alanı uygulanmış paket değişikliği değil politika niyetidir. Politika adı, koşul veya açıklama sonuçta yoksa tahmin edilmez. Skor, risk sıralaması veya otomatik düzeltme üretilmez.

Sabit güven alanları `authorization=not_evaluated`, `execution_authorized=false`, `verification=not_performed`, `scope=packet_policy_preview_only` olarak korunur. Native Windows uygulama kuralları, whitelist, bağlantı durumu, IP/domain listeleri, geçici bloklar, NAT tablosu ve sürücü davranışı bu kapsamdan çıkarılamaz. Sonuç **Dağıtıma hazır**, **Uygulandı**, **Doğrulandı** veya **Güvenli** diye yükseltilmez.

## Bellek ve hassas veri

Dosya yalnız açık kullanıcı seçimiyle File API üzerinden okunur. JSON kod, HTML, modül veya komut olarak çalıştırılmaz; içerikteki yol/URL takip edilmez. Ağ yüklemesi, API isteği, kalıcı tarayıcı deposu, audit/telemetri, ham console log, kopyalama/export veya yeni veri toplama yoktur. Yalnız doğrulanan alanlardan kapalı immutable UI modeli hazırlanır; ham dosya global store'a eklenmez. Dosya adı başlığa/URL'ye otomatik yazılmaz.

Gizli ayrıntılar CSS ile saklanmış DOM metni veya attribute olarak tutulmaz; görünürlük seçimine göre render edilir. Temizleme, model ve türetilmiş ayrıntıları bırakmaz. Bu yerel sunum sınırı şifreleme, anonimleştirme veya tarayıcı/işletim sistemi belleğinin adli olarak silinmesi garantisi değildir. Güvenilir olmayan dosya içeriğini kendi yetki/onayınız veya güncel cihaz verisi saymayın.

## Gerçek CLI'den sentetik örnek

**Örnek politika önizlemesi — gerçek cihaz değerlendirmesi değildir.** [Örneklerin üretim kaydı](../src/features/policyReview/examples/README.md), iki sentetik inputu ve mevcut CLI'nin değiştirilmeden ürettiği iki outputu içerir. Workbench'e `preview-output.json` veya `preview-missing-context-output.json` açılır. Input dosyaları CLI içindir. Başarılı örnek bir `ALLOW→DENY` ve bir `ALLOW→ALLOW`; bloke örnek `insufficient_context` içerir. Örnek, hatalı kullanıcı dosyasının yerine otomatik geçmez ve gerçek cihaz verisiyle birleşmez.

CLI, açıkça seçilen güvenilir yerel HBF kaynak diziniyle mevcut evaluator'ı çalıştırma sorumluluğundadır. Workbench yalnız üretilmiş sonucu görüntüler. CLI exit `0`, bloke sonuç dahil çıktı dosyasının yazıldığını söyler; uygulama veya güvenlik kabulü değildir. Örnek üretimi normal çevrimdışı CLI kullanımıdır, yazılım testi/runner çalışması değildir.

Typecheck/build ve manuel ürün gözlemleri [teslim kaydında](DELIVERY.tr.md) ayrı tutulur. Bu tur test/runner/coverage, canlı API/IdP/PG, gerçek cihaz/Windows kabulü, native uygulama, print/PDF, push/release veya deploy yapılmaz. Tarihsel test sayıları yeni workbench kabulü değildir; gerçek policy revision/lineage otoritesi ve Windows kapıları değişmez.
