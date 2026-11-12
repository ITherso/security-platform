# Offline guarded reference metadata consumer

**DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION**

Bu bağımsız offline araç, açıkça istenen Phase29 reference ID'leri için Phase31'in doğrulanmış mevcut guard kararını tüketir. Referans düzeyinde engel varsa olumlu alt dosya projection'ı da yayımlanmaz. İzinli referanslardan yalnız candidate/file kimlikleri, kayıtlı gözlem/karar kimlikleri, presence, byte/hash ve sabit sınırlama kodları çıkarılır. Kaynak dosyalar bu çağrıda yeniden okunmaz.

`provided_limited_metadata`, `withheld_by_existing_guard` ve `unavailable_in_existing_scope` tüketici sonuçlarıdır; kullanıcı yetkisi, dosyanın şu anki durumu veya compiler doğrulaması değildir. Upstream `fresh_candidate_byte_metadata_only` ve `fresh_absence_metadata_only` adları geçmiş Phase31 karar kodlarıdır; burada yeni bir freshness sonucu üretilmez.

## API ve doğrulama sınırı

`create_reference_metadata_response(validated_snapshot, request)` yalnız `ValidatedSnapshot` sınıfının tam tipini kabul eder. Snapshot dört immutable byte dizisini taşır; doğrudan constructor da gerçek owning doğrulamasını yapar. Public okuma aynı immutable byte'ları yeniden doğrular ve bağımsız model kopyaları döndürür. `validated=true`, `allow=true` veya caller'ın değiştirdiği comparison etiketi otorite değildir.

Giriş sırası: iki JSON için owning strict parse; Phase31 `validate_documents(ledger, reuse)`; gerçek `render_summary(ledger, reuse)` byte eşliği; gerçek üç payload için owning `manifest_data` eşliği. Tam kapalı baseline giriş doğrulaması için korunur; minimizasyon yalnız doğrulanmış modelden yeni çıktıya geçerken yapılır. Kaynak ZIP'i, native/candidate/Rust/Phase24 dosyaları ve eski CLI'lar açılmaz.

Referans `candidate_reuse_blocked` veya `candidate_change_observed` ise `projections=[]`; `outside_scope` ise açık kapsam dışı sonuç. `candidate_observations_reobserved` için bütün ilgili projection'lar mevcut `get_reusable_projection(ledger, file_id)` yolundan alınır. Beklenmeyen `None`, bilinmeyen durum veya çelişkili bağ bütün response'u reddeder; tek referansta kısmi başarı yoktur. Aynı request içinde referansların sonuçları farklı olabilir.

## Request ve sınırlar

`termivar-offline-reference-metadata-request/v1`: yalnız `mode=demo`, yerel `request_id`, gerçek upstream byte'larına bağlanan `expected_ledger_sha256` / `expected_reuse_sha256` ve 1–8 farklı `rust-ref-…` ID. Bilinmeyen/duplicate ID reddedilir. Request path, aday ekleme, guard override, production veya partial-reference seçeneği taşımaz.

Request 32 KiB; Phase31 JSON başına 1 MiB, Markdown 256 KiB, manifest 128 KiB; tüm açık girdiler 4 MiB. Yeni JSON başına 512 KiB, Markdown 128 KiB, manifest 128 KiB. Yeni model ağacı depth 12 / 20.000 node / genel string 512 karakter, ID ve kod alanları 128 karakter, SHA256 64 karakter sınırındadır. Strict UTF-8; duplicate/unknown key ve sürüm reddi; float/NaN/Infinity/bool-as-int reddi; integer en fazla 2^53−1. Eski gömülü modellerin owning sınırları korunur. Limit aşımında truncation yoktur.

## İki komutluk sınırlı çalışma

Kaynak hazırlığı sırasında yeni ürün çağrısı **0**; aşağıdaki komutların sonucu henüz bu README'de iddia edilmez. Root bütçesi en fazla iki çağrıdır. İkinci çağrı yalnız ilk assembly exit 0 ve eksiksiz dört gerçek çıktı sonrası çalıştırılır. Başarısız çağrı tüketilir; retry veya üçüncü çağrı yoktur. Phase20–31 ve eski insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_reference_metadata/assemble_metadata.py --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json --source-summary outputs/phase31-candidate-revalidation/revalidation-summary.md --source-manifest outputs/phase31-candidate-revalidation/manifest.json --request security-platform/tools/commercial_reference_metadata/examples/demo_metadata_request.json --output-dir outputs/phase32-reference-metadata
```

```text
python -I -B security-platform/tools/commercial_reference_metadata/inspect_metadata.py --response outputs/phase32-reference-metadata/reference-metadata-response.json --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json --summary outputs/phase32-reference-metadata/metadata-summary.md --manifest outputs/phase32-reference-metadata/manifest.json --output outputs/phase32-reference-metadata/inspection-summary.json
```

Output yeni ve boş bir dizin olmalıdır; overwrite veya otomatik silme yoktur. Assembly üç payload (`reference-metadata-response.json`, `metadata-selection-ledger.json`, `metadata-summary.md`) ve en son manifest üretir. Inspector dört yeni açık dosyayı okur, `inspection-summary.json` üretir. Manifest kendisini ve inspector çıktısını kapsamaz.

## Güven, mahremiyet ve bağımlılıklar

Response/selection/Markdown yalnız istenen reference'ları taşır; diğer bağlam ID'lerini listelemez. Bloke referansa ait olumlu hash/size başka alana kopyalanmaz. Relative/absolute path, root/pin, physical identity, tam baseline, historical içerik, raw Rust/JSON veya exception metni tüketici çıktısına taşınmaz. ID/hash hassas olabilir; minimizasyon anonimlik veya şifreleme değildir.

`reference_context_revalidated=false`, `independent_observation_verified=false`, `source_files_reobserved=false` dahil 17 güven alanı false kalır. Envanter/delta, ownership/module closure, producer/human, build/runtime, hukukî ve release kabulü kazanılmaz. Kaynaklı gözlem zamanının bugüne kadar geçerli kaldığı iddia edilmez; TTL veya canlı tazelik garantisi yoktur.

Inspector yalnız iki yeni model, yeniden türetilen Markdown ve üç payload byte/hash bağını inceler. `content_consistent`, Phase31 guard'ının veya kaynak gözlemlerinin bağımsız yeniden doğrulanması değildir. Inspector eski upstream veya kaynak dosyalarını açmaz.

Bu kaynak dizini tek başına dağıtılabilir runtime/wheel değildir. Aynı korunmuş `security-platform/tools` ağacındaki Phase31 `commercial_candidate_revalidation` ve onun mevcut owning yardımcılarına bağlıdır. Yeni kaynak ZIP'i eski artefact gruplarını, native/binary/wheel/cache/DB'yi içermez; dört açık Phase31 girdisi ayrıca gereklidir. Yeni dependency/servis/endpoint/GUI yoktur.

Belgeler: [sözleşme](../../docs/commercial/operations/phase32/CONSUMER_CONTRACT.tr.md), [guard entegrasyonu](../../docs/commercial/operations/phase32/GUARD_INTEGRATION.tr.md), [güven ve mahremiyet](../../docs/commercial/operations/phase32/TRUST_AND_PRIVACY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase32/DEMO_DELIVERY.tr.md).

NOT_RUN: hostile JSON/UTF-8, duplicate/yanlış reference, digest uyuşmazlığı, bozuk upstream/guard/projection, limit/path/link/race/crash, shared-file/determinism, gerçek source değişimi, native/compiler/ownership/producer/uzman/hukukî/release kabulü. Kaynak incelemesi bu dalların çalıştırıldığı anlamına gelmez. Test/runner/coverage/typecheck/build veya tarayıcı çalışması yapılmaz.
