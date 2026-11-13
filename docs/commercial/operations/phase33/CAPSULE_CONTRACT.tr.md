# Phase33 kapsül sözleşmesi

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

Yeni ürün, mevcut Phase32 wire metadata'sının kapalı bir portatif projeksiyonudur. Assembly eski sahibi doğrular; portatif inspector yalnız yeni kapsülün iç bütünlüğünü değerlendirir. Bunlar ayrı güven sınırlarıdır. Yeni evaluator, resolver veya kullanıcı yetki sistemi kurulmaz.

## Request

`termivar-offline-guarded-reference-capsule-request/v1` tam yedi alanı kabul eder:

| Alan | Anlam |
| --- | --- |
| `schema_version` | Yalnız desteklenen request v1 |
| `mode` | Yalnız `demo` |
| `capsule_reference` | Sınırlı yerel demo kimliği; credential veya kaynak path değildir |
| `source_response_sha256` | Gerçek Phase32 response byte'larının SHA256 beklentisi |
| `source_selection_sha256` | Gerçek Phase32 selection byte'larının SHA256 beklentisi |
| `requested_reference_ids` | Phase32 response içinde bulunan 1–8 farklı açık reference ID |
| `inspection_constraints` | Aşağıdaki dokuz sabit sınır; caller yükseltemez veya genişletemez |

Duplicate/bilinmeyen ID, unknown alan/version, digest uyuşmazlığı ve demo dışı mode kapalı hatadır. Request yeni path, candidate, source loader, override veya partial-reference izni taşımaz.

`inspection_constraints`: `max_archive_bytes=262144`, `max_member_bytes=131072`, `max_expanded_bytes=262144`, `max_compression_ratio=20`, `max_references=8`, `max_projections=64`, `max_json_depth=12`, `max_json_nodes=20000`, `max_text_chars=512`.

## Capsule

`termivar-offline-guarded-reference-capsule/v1` kapalı modelinde demo kimliği/etiketi, `source_bindings`, `requested_reference_ids`, `results`, yeniden türetilmiş `counts`, sabit `limitations`, aynı `inspection_constraints`, `demo_only=true` ve 18 false güven alanı bulunur. Caller'ın eklediği bir allow veya verified işareti kabul otoritesi değildir.

`source_bindings` tam `snapshot_id` ve `sources` taşır. Snapshot `phase32-artifact-snapshot-<SHA256>` biçiminde dört descriptor'a bağlı içerik kimliğidir. `sources` yalnız `response`, `selection`, `summary`, `manifest` rolleridir; her descriptor `schema_version`, `bytes`, `sha256` taşır. Summary sözleşmesi `null`; diğer roller gerçek Phase32 v1 kimlikleridir. Dosya yolu veya ham kaynak içerik taşınmaz. Kaynak hash'i üretici imzası değildir.

Her referans sonucu yalnız `reference_id`, mevcut `status`, `upstream_reference_decision`, `projections`, `limitation_codes` taşır. Desteklenen durumlar `provided_limited_metadata`, `withheld_by_existing_guard`, `unavailable_in_existing_scope`. Bloke/kapsam dışı referansın projection listesi boştur; tek referansta alt dosya başarısı engeli aşmaz. İzinli projection yalnız mevcut 11 alanı taşır; [disclosure sınırı](DISCLOSURE_BOUNDARY.tr.md) alanları açıklar.

Sayımlar: requested/provided/withheld/unavailable reference sayıları; projection ilişkisi; unique candidate; unique file; present ve absence projection sayıları. Aynı file farklı ilişkilerde görünürse file ve ilişki paydaları karıştırılmaz. Absence byte/hash `null`; bilinen sıfır değildir.

## Sabit ZIP ve lookup

Kapsül ZIP'i tam şu sıradaki dört üyeden oluşur: `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt`. Inner manifest diğer üç üyenin gerçek byte/SHA256 bağını taşır, kendi hash'ini taşımaz. Summary yalnız kapalı capsule JSON'undan deterministik türetilir. README sabit byte dizisidir. ZIP üye sırası ve metadata politikası sabittir; tekrar-determinism gerçek çalıştırılmadıkça kabul edilmiş sayılmaz.

`termivar-offline-reference-capsule-lookup/v1` yalnız kullanıcı tarafından açıkça istenen capsule reference ID'leri için sonuç üretir. Sonuç mevcut disclosure durumunu, izinli projection'ları ve aynı güven/güncellik sınırlarını korur. Unknown veya duplicate lookup ID kapalı hatadır. Bloke referans sorgusu durumu döndürür, olumlu candidate metadata'sı döndürmez. Lookup kaynak repo, Phase31/32, başka ZIP, internet veya source path okumaz.

Strict UTF-8/JSON; duplicate/unknown alan/version, float/NaN/Infinity ve bool-as-integer reddi. Dokuz sabit sınır aşılırsa truncation yapılmaz. Kapsül içeriği güncel filesystem, producer attestation, gerçek guard doğruluğu veya release kabulü değildir. Kaynak hazırlığı sırasında yeni ürün çağrısı 0; bu belge runtime negatif kabul sonucu iddia etmez.
