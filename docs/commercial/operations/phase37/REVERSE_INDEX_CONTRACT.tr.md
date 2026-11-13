# Phase37 disclosed file index ve lookup sözleşmeleri

**OFFLINE DEMONSTRATION — DISCLOSED METADATA ONLY — NO CURRENT SOURCE VERIFICATION**

Yeni araç yalnız gerçek Phase36 sahibiyle doğrulanmış inbox disclosure metadata'sını ters yönde ilişkilendirir: File ID → görünür referans → bütün izinli projection paketi. `lookup_disclosure ⊆ validated_inbox_disclosure`. Yeni guard, fiziksel file lookup, evaluator, resolver veya kullanıcı yetkisi yoktur.

## Common ve gerçek source bağı

Yeni common tam dört alan taşır: `schema_version`, `demo_label`, `demo_only=true`, `trust_flags`. Kapalı `trust_flags` nesnesinde Phase36'nın aynı 18 false alanı bulunur; eski top-level flag düzeni yeni modele gizlice kopyalanmaz ve olumluya yükseltilmez.

Beş gerçek Phase36 source descriptor'ı sabit sırada `name`, pozitif bounded `bytes`, `sha256`, `schema_version` taşır: inbox, query, receipt, Markdown, manifest. Markdown schema null'dır. Yeni source inbox/manifest SHA256 değerleri gerçek Phase36 dosya byte'larıdır; inbox içine kaydedilmiş Phase35 provenance kimliği yeni source kimliği değildir.

## Strict request

`termivar-offline-disclosed-file-lookup-request/v1` tam altı alan:

| Alan | Anlam |
| --- | --- |
| `schema_version` | Yalnız desteklenen request v1 |
| `mode` | Yalnız `demo` |
| `request_reference` | Yerel bounded demo kimliği; kullanıcı yetkisi değildir |
| `source_inbox_sha256` | Gerçek Phase36 typed-inbox dosyası SHA256 beklentisi |
| `source_manifest_sha256` | Gerçek Phase36 manifest dosyası SHA256 beklentisi |
| `requested_file_ids` | 1–8 farklı, geçerli biçimli açık metadata File ID |

Duplicate, geçersiz biçim, unknown field/schema/type veya yanlış source digest kapalı hatadır. Biçimsel geçerli fakat görünür indekste bulunmayan File ID reddedilmek yerine ortak `not_in_disclosed_index`, `reference_ids=[]` sonucu verir; fiziksel varlık veya bloke kayıt nedeni açıklanmaz.

## Index ve immutable API

`termivar-offline-disclosed-file-index/v1` common, gerçek source inbox/manifest digest'leri, source inbox schema, beş descriptor, full source counts, `disclosed_references`, `file_records`, visible counts ve sınırlamaları taşır. `disclosed_references` yalnız provided referansların dört reference alanı ve bütün mevcut 11-alan projection paketidir. Bloke/kapsam dışı kayıtların ID veya olumlu metadata'sı indekse alınmaz; yalnız aggregate source sayımı bulunabilir.

Her file record tam `file_id`, sorted unique `reference_ids`, sorted unique `candidate_ids`, sorted `projection_bindings` taşır. Her binding mevcut `(reference_id,candidate_id,file_id)` üçlüsüdür; source projection ID yoksa uydurulmaz. Gerçek reference/projection_links/metadata bağları zorunludur; duplicate veya aynı File ID için çelişkili metadata sessizce birleştirilmez.

`build_disclosed_file_index(ValidatedPhase36Source) -> ValidatedFileIndex` gerçek beş-artefact owner doğrulamasından geçmiş immutable source grubu tüketir. `ValidatedFileIndex` exact immutable closed JSON byte'ıdır; constructor ve public okuma validator'ı tekrar uygular. Caller'ın trusted/allow işareti otorite değildir. Boş visible küme için eski owner inbox validator gevşetilmez; source ayrı geçerli kalır, yeni indeks kendi boş görünür kapsamını açık işler.

Visible counts tam altı alan: file/reference/candidate/projection/present projection/absence projection. Full source counts mevcut dokuz reference/projection/unique candidate/file/present/absence paydasını korur. Source aggregate withheld sayısı olumlu file disclosure değildir.

## Lookup ve receipt

`lookup_disclosed_files(validated_index, requested_file_ids)` yalnız exact index snapshot'ı üzerinde saf file/reference/count sonuçları üretir. `build_file_lookup` strict request/source digest wrapper'ıdır. `termivar-offline-disclosed-file-lookup/v1` common, request, source digest'leri, `file_results`, `reference_results`, sekiz lookup sayımı ve sınırlamaları taşır.

File sonucu yalnız File ID/status/reference listesi; status matched veya `not_in_disclosed_index`. Reference sonucu mevcut dört reference alanı, bütün izinli projection listesi ve `matched_file_ids` taşır. Reference sonuçları sorted unique'tir; eşleşen istenen File ID'ler request sırasını korur. Tek File ID eşleşse bile diğer izinli projection'lar kaybolmaz. Shared-file ilişkisinde bütün gerçek görünür referanslar korunur.

`termivar-offline-file-index-source-receipt/v1` common, beş descriptor, gerçek source digest/schema, source/visible counts, `content_scope=five_Phase36_artifact_internal_correspondence_only` ve sınırlamaları taşır; projection payload audit kopyası değildir. Dış manifest `termivar-offline-file-index-manifest/v1`, inspector `termivar-offline-file-index-inspection/v1`; manifest ilk dört gerçek output'u bağlar, kendisini kapsamaz.

## Limitler ve kabul sınırı

Request 32 KiB; gerçek source inbox/query/receipt 256/128/64 KiB, Markdown 128 KiB/manifest 64 KiB; toplam açık girdi 1 MiB. Yeni index 256 KiB, lookup/MD 128 KiB, receipt/manifest 64 KiB; reference 8/projection ve visible file 64/requested file 8/depth 12/node 20.000/text 512. Daha sıkı owner sınırı korunur. Strict UTF-8/JSON, duplicate/unknown schema/field/type, float/NaN/Infinity/bool-as-int ve geçersiz bağ reddi; truncation, overwrite, otomatik silme veya partial-write başarısı yoktur.

File ID inode/Windows file identity/path veya evrensel kimlik değildir. İç tutarlılık source freshness/producer/guard/compiler/ownership/insan/hukukî/release kanıtı değildir. Actual komut/byte kimlikleri yalnız teslim kaydındadır; koruma kodu hostile/shared/single-file/unknown runtime kabulü değildir.
