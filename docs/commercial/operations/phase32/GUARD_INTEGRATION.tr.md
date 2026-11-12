# Phase32 mevcut guard entegrasyonu

**DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION**

Phase31'in gerçek sahibi `commercial_candidate_revalidation` korunur. Kullanılan sözleşme `revalidation_contracts.validate_documents(ledger, reuse)`; saf projection yolu `evidence_reuse_guard.get_reusable_projection(ledger, file_id)`; mevcut modeller `build_reuse(ledger)` ve `build_reference_impact(ledger, file_decisions)` semantiğini taşır. Caller'ın verdiği olumlu comparison etiketi kabul otoritesi değildir. Yeni staleness evaluator veya paralel guard yazılmaz.

## Snapshot sınırı

Adapter yalnız dört açık Phase31 dosyasını okur: ledger, reuse, summary, manifest. İki JSON owning strict parse edilir; `validate_documents` tam kapalı baseline dahil uygulanır; `render_summary` byte eşliği ve `manifest_data` gerçek üç payload eşliği kontrol edilir. Builder/renderer/manifest tek başına validator sayılmaz. Snapshot yalnız immutable bytes taşır; doğrudan constructor da doğrular. Public okuma aynı bytes'ı yeniden doğrular, bağımsız model kopyaları verir. Doğrulama öncesi baseline küçültülmez.

Bu işlem source byte gözlemlerini bağımsız doğrulamaz; kapalı metadata ve korunmuş saf türetim zincirini doğrular. Eski kaynak ZIP'i/candidate/Rust/Phase24 dosyaları veya eski CLI açılmaz.

## Referans bütünlüğü

| Mevcut reference kararı | Yeni tüketici sonucu | Projection |
|---|---|---|
| `candidate_reuse_blocked` | `withheld_by_existing_guard` | Boş; olumlu alt dosya da yayımlanmaz |
| `candidate_change_observed` | `withheld_by_existing_guard` | Boş; yeni kaynak kararı üretilmez |
| `outside_scope` | `unavailable_in_existing_scope` | Boş; kapsam dışı başarılı/sağlıklı sayılmaz |
| `candidate_observations_reobserved` | `provided_limited_metadata` | İlgili bütün kayıtlar existing getter üzerinden |

İzinli reference için getter `None` döndürürse, bağlar uyuşmazsa veya durum tanınmıyorsa bütün response reddedilir. Tek reference'ın aday kümesi kısmi başarı halinde yayımlanmaz. Ayrı reference'lar aynı request içinde farklı sonuç taşıyabilir.

Mevcut örneğin amacı `authorization_review` altında bir olumlu dosya gözleminin diğer candidate engelini aşmasını önlemektir. Bu source bağlamı beklenen demoyu açıklar; yeni ürün çağrıları gerçekleşmeden gerçek filtreleme sonucu ilan edilmez. Request yalnız üç açık ID içerir; diğer reference'lar response'a taşınmaz veya taranmış gibi sunulmaz.

Getter'ın döndürdüğü geniş projection'dan yalnız kapalı disclosure alanları seçilir. Path, root/pin, read stability, physical/historical metadata ve ham dict kopyalanmaz. Aynı file için tekrar eden ilişkiler benzersiz file sayımını şişirmez; metadata uyuşmazlığı reddedilir.

`fresh_candidate_byte_metadata_only` ve `fresh_absence_metadata_only` yalnız **kayıtlı upstream projection kodlarıdır**. Phase32 current/source dosyası okumaz, reference context'i yenilemez; yeni timestamp/TTL/tazelik otoritesi eklemez.

Inspector yalnız dört yeni dosyada model/selection/Markdown/manifest ilişkisini denetler. Phase31 guard'ı veya dosya gözlemini yeniden doğrulamaz; `content_consistent` bu dar anlamı taşır. Hostile request/model/digest, bilinmeyen durum, projection eksikliği, shared-file, race ve gerçek source değişimi çalıştırılmadıkça NOT_RUN'dır.
