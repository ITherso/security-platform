# Phase32 tüketici sözleşmesi

**DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION**

Public saf API `create_reference_metadata_response(validated_snapshot, request)` yalnız gerçek owning doğrulamasından geçen immutable snapshot'tan kapalı response üretir. File I/O adapter/CLI sınırındadır; bu API candidate veya kaynak dosyası açmaz. Snapshot'ın constructor'ı ve public okuyucusu gerçek dört byte girdisini doğrular; `validated`/`allow` marker'ı kabul edilmez.

## Request

`termivar-offline-reference-metadata-request/v1`: `schema_version`, yalnız `mode=demo`, yerel `request_id`, `expected_ledger_sha256`, `expected_reuse_sha256`, `reference_ids`. ID listesi 1–8 farklı external reference'tır. Beklenen hash'ler gerçek Phase31 dosya byte kimliklerine bağlanır. Bilinmeyen/duplicate ID tüm isteği reddeder. Dosya yolu, candidate override, production veya partial-reference alanı yoktur.

## Response

`termivar-offline-reference-metadata-response/v1`: ortak demo/güven alanları, yalnız dört upstream girdinin sürüm/byte/SHA256 kimliklerini taşıyan path'siz `source_reference`, `request_id`, `results`, `counts`, `limitations`.

Her result yalnız `reference_id`, `status`, `upstream_reference_decision`, `projections`, `limitation_codes` taşır. Sonuçlar request sırasını korur. Durumlar `provided_limited_metadata`, `withheld_by_existing_guard`, `unavailable_in_existing_scope`; bunlar güvenlik veya kullanıcı yetkilendirme kararı değildir.

Projection yalnız `reference_id`, `candidate_id`, `file_id`, `upstream_projection_kind`, `source_file_presence`, `observed_byte_size`, `observed_sha256`, `phase31_current_observation_id`, `phase31_comparison_id`, `upstream_comparison_status`, `interpretation_limitations` taşır. Present byte/hash bilinir; absence için ikisi de `null` kalır. Null bilinen sıfır değildir. Upstream `fresh_*` türleri kayıtlı Phase31 kodlarıdır; yeni gözlem veya güncel tazelik iddiası değildir.

Bloke ve kapsam dışı result `projections=[]` taşır. Bloke candidate'ın olumlu metadata'sı başka alana taşınmaz. İzinli tek reference'ın bütün ilgili projection'ları birlikte bulunmalıdır; eksik/çelişkili projection sessizce düşürülmez.

## Selection ve renderer

`termivar-offline-reference-metadata-selection/v1`: ortak alanlar, request'in kapalı kopyası, `selections`, `counts`, `limitations`. Her seçim reference ID, upstream karar, response durumu, sunulan projection sayısı ve sınırlama kodlarını taşır; projection metadata'sını tekrar kopyalamaz.

Reference, candidate ve benzersiz file sayımları ayrıdır. Aynı file'ın farklı reference/candidate ilişkileri korunur; file metadata'sı aynı kimlikte çelişemez. `render_summary(response, selection)` önce yeni `validate_documents` çalıştırır, yalnız bu iki küçültülmüş modelden inert Markdown üretir; eski model/file/guard lookup yapmaz.

## Strict sınırlar

Request 32 KiB; Phase31 JSON başına 1 MiB, Markdown 256 KiB, manifest 128 KiB; açık girdi toplamı 4 MiB. Yeni JSON 512 KiB, Markdown/manifest 128 KiB. Yeni ağaç depth 12, node 20.000, genel string 512 karakter; ID/kod 128, SHA256 64 karakter; integer 0..2^53−1. Strict UTF-8, duplicate/unknown alan/sürüm ve float/NaN/Infinity/bool-as-int reddi vardır. Eski owning JSON/model sınırları gevşetilmez. Limit aşımı truncation üretmez.

Ortak banner ve `demo_only=true` korunur; `reference_context_revalidated`, `independent_observation_verified`, `source_files_reobserved` dahil 17 güven alanı false'tur. Request kimliği yetki veya credential değildir. Kaynak dosyası durumu bu çağrıda yeniden gözlenmez.
