# Phase44 güven sınırı, veri açıklama kuralları ve bilinen sınırlamalar

**OFFLINE DEMONSTRATION — UNTRUSTED CAPSULE RECONCILIATION ONLY — NO TASK DISPATCH, ASSIGNMENT, APPROVAL, EXECUTION OR SUBMISSION**

## Güven sınırı

İçe alınan capsule, ZIP yapısı ve hash'leri geçerli olsa bile güvenilmeyen girdi olarak kalır. Tutarlı bir sahte capsule, üyeleri birlikte değiştirilip yeniden hash'lenerek üretilebilir. Bu yüzden şu eşleşmelerin hiçbiri güven kurmaz:

- Phase43 owner reader'ın kabul etmesi
- İç manifestin eşleşmesi
- Yerel kayıtlarla `MATCH` sonucu

Bu eşleşmeler yalnız yerel byte, model ve kayıt eşliğidir. Şunları göstermez:

- Üretici kimlik doğrulaması
- Dijital imza
- Anti-replay veya güvenilir zaman damgası
- Güvenli aktarım
- Kaynak provenance'ı
- Gerçek dünya gözlemi

Bu yetenekler uygulanmadı ve doğrulanmadı.

Yerel referans kayıtları (Phase42 register grubu, Phase43 çıktıları) da kayıtlı metadata'dır. Kaynak doğruluğu değildir. Orijinal Phase40 binding preimage'ı yeniden kurulmaz.

Phase44 hiçbir görevi göndermez, almaz, yürütmez, atamaz, onaylamaz, tamamlamaz ve gönderime sunmaz. En iyi sonuç `STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW` olur ve bu durumda bile manuel inceleme zorunludur (`REQUIRED`).

## Veri açıklama (minimizasyon) kuralları

- **Geçersiz string'ler yazılmaz.** Capsule'daki bir string değer yalnız owner validator'dan geçtiyse rapora yazılır. Geçersiz string için yalnız uzunluk ve SHA256 kaydedilir; desteklenmeyen şema string'i de buna dahildir. Liste ve nesne değerleri hiç yazılmaz. Integer, boolean ve null değerler geçersiz olsalar bile yazılır, çünkü serbest metin taşımazlar. Bilinmeyen alanların değeri hiç yazılmaz; adı yalnız güvenli kalıba uyuyorsa listelenir.
- **Güvensiz üye adları yazılmaz.** Güvenli kalıba uymayan üye adı (traversal, mutlak yol, kontrol karakteri vb.) yalnız uzunluk ve SHA256 ile kaydedilir.
- **Yerel değerler için tek kural vardır.** Yerel değer üç durumda yazılır: capsule değerine eşitse, daha önce Phase43 kaydında açıklanmışsa ya da açıkça verilen bir yerel girdi dosyasının byte kimliğiyse. Üçüncü durum Phase42 register ve manifest SHA256 değerleri içindir; bunlar her çalıştırmada `local_reference` ve `manifest.json` `inputs` alanlarına provenance olarak zaten yazılır. Diğer durumlarda değer `WITHHELD_NOT_PREVIOUSLY_DISCLOSED` olarak gizlenir. Uyuşmazlık bulgusunun metni de yerel değeri tekrar etmez, yalnız karşılaştırma satırına işaret eder.
- **Reddedilen capsule'da yerel kayıtlara bakılmaz.** Bütün satırlar `NOT_COMPARABLE / NOT_AVAILABLE` olur.
- **Talep edilmeyen yerel görevler çıktıya girmez.** Builder yerel kayıt verisini yalnız karşılaştırma `local_value`, `local_reference` ve manifest `inputs` alanlarına yazar. Yerel görevlere yalnız capsule'ın beyan ettiği görev kimlikleriyle bakılır. Inspector bu alanları yapısal olarak denetler. Çıktı byte'larında substring araması yapmaz, çünkü capsule kaynaklı metin yerel bir kimliğe benzeyebilir.
- **Hassas anahtarlar çıktıda bulunmaz.** Çıktılarda `candidate_response`, `observed_sha256`, `observed_byte_size`, `projections`, `reference_packets`, `source_locator` veya analist kimliği anahtarları yoktur.

Minimizasyon anonimleştirme veya şifreleme değildir. Task, reference, candidate ve file kimlikleri ile digest'ler yine hassas olabilir.

## Bilinen sınırlamalar

- **Tanılama Phase43 kurallarını yansıtır, onları belirlemez.** Phase44'ün alan bazlı tanılaması Phase43 owner validator'larını alan alan çağırır. Görev alanlarının hangi validator'a gittiği eşlemesi `capsule_claims._TASK_RULES` içindedir. Kapalı envelope alan listesi `ENVELOPE_FIELDS` içindedir ve owner'ın kabul ettiği her envelope ile karşılaştırılır. Uyumluluk kararını yalnız owner reader verir. Tanılama ile owner reader çelişirse sonuç fail-closed reddir (`DIAGNOSTIC_OWNER_DISAGREEMENT`).
- **Bazı container ihlallerinin ayrı bir Phase44 bulgusu yoktur.** Canonical olmayan local header, izin bitleri, `create_system` farkı ve öndeki ya da sondaki byte'lar bu gruptadır. Bunlar yalnız owner reader'ın `OWNER_READER_REJECTED` bulgusuyla ve owner kodu ile raporlanır. Central directory'deki extra alanı ve ZIP64 işaretleri ise ayrıca `MEMBER_ZIP64_OR_EXTRA_FIELD` bulgusu üretir.
- **Bulgu sayısı sınırlıdır.** Bir rapor en fazla 400 bulgu listeler. İlk 16 üyeden sonraki duplicate adlar tek bir `MEMBER_DUPLICATE:unlisted_members` bulgusunda toplanır. Sınır yine de aşılırsa en önemli 399 bulgu tutulur ve engelleyici `FINDINGS_TRUNCATED` bulgusu eklenir. Böylece aşırı sayıda bulgu üreten bir arşiv için de her zaman bir ret raporu üretilir. Phase43 owner JSON sınırını (2^53−1) aşan beyan edilmiş ZIP boyutları `null` ve `DECLARED_SIZE_UNREPRESENTABLE` olarak raporlanır.
- **Büyük capsule dosyası için rapor yoktur.** 131072 byte'tan büyük capsule dosyası CLI tarafından okunmadan reddedilir; çıkış kodu 2'dir ve rapor yazılmaz. Bayt düzeyinde API (`reconcile_capsule`) aynı durumda `SIZE_LIMIT_EXCEEDED` raporu üretir.
- **Bazı kontroller yalnız sayılarla yapılır.** `counts`, `tasks` owner tarafından geçerli bulunmadan değerlendirilmez (`NOT_EVALUATED`). Tutarsız sayı beyanı ayrıca `TASK_COUNT_DECLARATION_MISMATCH` ile raporlanır.
- **Yerel görev bulunamazsa sonuç `UNAVAILABLE` olur.** Yerel kayıtta olmayan bir görev `MISMATCH` sayılmaz. Farklı bir capsule'ın kimliği Phase43 capsule düzeyindeki satırlarda (`capsule_sha256`, `task_id_list`) ayrıca `MISMATCH` olarak görünür.
- **Inspector bağımsızlığı sınırlıdır.** Inspector, builder'ın mutabakat motorunu yeniden üretim adımında kullanır. Bağımsızlığı şu ek kontrollerden gelir: ayrı kural koduyla yeniden türetilen uygunluk, owner reader'ın tekrar çalıştırılması, açıklama denetimi, girdi ve çıktı kimlikleri. Açıklama denetimi, yazılan her yerel değeri satır bazında yerel kayıttan ayrıca hesaplanan değerle karşılaştırır. Yazılmayan (`WITHHELD` veya `NOT_AVAILABLE`) satırların sonucu ise yerel kayıttan yeniden hesaplanmaz; bu satırlar yalnız yeniden üretim adımında builder'ın motoruyla karşılaştırılır. Ortak bir kusur iki tarafta da aynı şekilde var olabilir.

## NOT_RUN

Aşağıdakilerin hiçbiri çalıştırılmadı:

- Gerçek ikinci host aktarımı veya alıcı kimlik doğrulaması
- Üretici kimliği, imza, anti-replay, güvenilir zaman damgası
- Görev gönderimi, ataması, onayı, yürütmesi, tamamlanması
- Response gönderimi veya ingestion, Phase42 future decoder
- Kaynak yeniden gözlemi veya kanıt toplama
- Phase31 guard, Rust derleyicisi veya native çalışma ortamı
- İnsan, hukuk, müşteri, production veya release kabulü
- Ağ, servis, VM, sürücü veya yönetici işlemi, push, release, deploy
