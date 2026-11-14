# Phase38 co-reference sözleşmeleri

**OFFLINE DEMONSTRATION — DISCLOSED CO-REFERENCE ONLY — NO PHYSICAL FILE OR SOURCE RELATIONSHIP VERIFIED**

Yeni sözleşme yalnız mevcut görünür File ID referans kümelerinin pairwise kesişimidir. Mevcut Phase37 owner source doğrulaması olmadan gerçek kaynak bağlı join üretilmez. Yeni graph/evaluator/resolver/guard/risk veya yetki sistemi kurulmaz.

## Request ve source grubu

`termivar-offline-co-reference-request/v1` tam altı alan taşır: `schema_version`, `mode`, `request_reference`, `source_index_sha256`, `source_manifest_sha256`, `requested_file_ids`. Mode demo; 2–8 farklı, geçerli metadata File ID. Duplicate, wrong digest, unknown schema/field/type kapalı hatadır. Yeni reference/candidate/path/risk/override/include-blocked/force-match yoktur. Biçimsel geçerli unknown/nonvisible kimlik ortak `not_in_disclosed_index` semantiğini korur.

Source index/manifest digest'leri beş gerçek Phase37 input'una bağlıdır; eski embedded Phase36/35 hash'leri değildir. Beş ordered source descriptor `name`, positive bounded `bytes`, `sha256`, `schema_version` taşır; MD schema null. Source counts yalnız Phase37 visible index'in file/reference/candidate/projection/present/absence altı paydasıdır. Eski global inbox veya bloke aggregate sayımları yeni modele taşınmaz.

## Join v1 ve gerekli kapalı packet eki

`termivar-offline-disclosed-co-reference/v1` common schema/demo label/demo_only true/nested 18 false trust_flags; gerçek source digest/schema/descriptor/visible counts; requested file IDs; file results; pair results; `reference_packets`; join counts ve sınırlamaları taşır. Tam request'in yerel `request_reference` alanı dış manifestte tutulur; saf join yalnız source bağları ve File ID seçimi gerektirir.

File result tam `file_id`, status, `visible_reference_ids`; status matched veya `not_in_disclosed_index`. File sırası request sırasıdır. Pair result tam `left_file_id`, `right_file_id`, `relationship_status`, `shared_reference_ids`, `supporting_projection_bindings`. Çiftler lexicographic kanonik kombinasyonlardır. Her unordered çift bir kez bulunur; 8 file için en fazla 28 çift.

Pair status shared/no-shared/not-in-disclosed-index kapalı enum'udur. Shared durum her iki visible kümeyi, ortak provided referansı ve her iki file için gerçek projection üçlülerini gerektirir. Supporting binding yalnız `(reference_id,candidate_id,file_id)`; source projection ID yoksa uydurulmaz. Duplicate binding aynı çiftte reddedilir. Aynı gerçek üçlü farklı çiftlerde tekrar edebilir; occurrence ile unique sayımı ayrıdır.

`reference_packets` yeni wire'da açıkça gerekli ektir: yalnız pair shared-reference union'ının bütün eski provided paketleri, sorted reference ID sırası ve orijinal projection sırasıyla korunur. Paket mevcut dört reference alanı ve bütün 11-alan projection listesidir. Bu ek yeni beş-output inspector'ın whole-packet eşliğini kaynak dosyaları açmadan incelemesini sağlar. Unshared full catalog veya bloke kimlik/metadata kopyalanmaz. Constructor'ın bu iç wire kontrolü özgün kaynak/producer kanıtı değildir.

Join sayımları tam on alan: requested/matched/not-in-disclosed file; pair/shared/no-shared/not-in-disclosed pair; unique shared reference; supporting binding occurrence; unique supporting binding üçlüsü. Bir pair'de en fazla 64 supporting binding, toplam en fazla 1792 occurrence ve en fazla 64 unique üçlü sınırı vardır; model byte/node limitleri ayrıca korunur.

## Lookup, receipt ve saf API

`build_co_reference_join(validated_index, requested_file_ids)` gerçek immutable beş-dosya `ValidatedPhase37Source` kullanır, `ValidatedCoReferenceJoin` döndürür. Mevcut Phase37 `ValidatedFileIndex` ve `lookup_disclosed_files` tam provided paketleri için yeniden kullanılır; source identity gerçek artefact byte'larından gelir, canonical yeniden serialize edilen index hash'inden değil.

`build_co_reference_lookup(validated_index, validated_join)` aynı gerçek source grubuna bağlı join'i yeniden türetip eşler; yalnız shared union referansları bir kez, bütün projection'larıyla döndürür. `termivar-offline-co-reference-lookup/v1` result tam dört alan taşır: `reference_id`, `disclosure_status`, `matched_file_ids`, `projections`. Ek projection_count veya reference limitation alanı uydurulmaz; projection kendi eski interpretation alanlarını korur. Matched IDs request sırasını izler. Lookup altı sayımı reference/projection/candidate/present/absence ve shared referanslara katılan unique matched file'dır.

`termivar-offline-co-reference-source-receipt/v1` common, beş source descriptor, gerçek source digest/schema, visible altı source count, `content_scope=five_Phase37_artifact_internal_correspondence_only`, sınırlamalar taşır. Full catalog/audit kopyası veya bloke aggregate yoktur. Dış manifest `termivar-offline-co-reference-manifest/v1`, inspector `termivar-offline-co-reference-inspection/v1`; manifest ilk dört gerçek payload ve tam request'i bağlar, kendisini kapsamaz.

## Limit ve güven sınırı

Request 32 KiB; source index/lookup/receipt 256/128/64 KiB, MD 128 KiB/manifest 64 KiB, toplam açık girdi 1 MiB. Join 256 KiB, lookup/MD 128 KiB, receipt/manifest 64 KiB; file 2–8/pair 28/reference 8/projection 64/depth 12/node 20.000/text 512. Daha sıkı owner limitleri korunur. Strict UTF-8/JSON, duplicate/unknown schema/field/type, wrong digest/binding/enum ve float/NaN/Infinity/bool-as-int reddi; truncation/overwrite/otomatik silme/partial-write başarısı yoktur.

Co-reference physical/content/security/causal/source/compiler/ownership ilişkisi değildir. 18 nested false değer ve demo-only korunur. Actual komutlar ve kimlikler teslim kaydındadır; koruma kodu hostile/no-shared/unknown/multi-reference runtime kabulü değildir.
