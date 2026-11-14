# Phase39 cohort query ve witness sözleşmeleri

**OFFLINE DEMONSTRATION — DISCLOSED COHORT MATCH ONLY — NO CURRENT FILE OR SOURCE RELATIONSHIP VERIFIED**

Yeni işlev, görünür metadata File ID kümesi üzerinde doğrudan N-way ALL-OF ve her file için kayıtlı presence assertion'ıdır. Pairwise join transitif genişletilmez, yeni gözlem veya genel evaluator/query framework oluşturulmaz.

## Strict request ve gerçek enum

`termivar-offline-disclosed-cohort-query-request/v1` tam altı alan: `schema_version`, `mode`, `request_reference`, `source_phase38_join_sha256`, `source_phase38_manifest_sha256`, `required_file_assertions`. Mode demo. Assertions 2–8 farklı source-owned File ID; her kayıt tam `file_id`, `expected_source_file_presence` taşır. Owner enum **present/missing**; missing kayıtlı absence'dır, absent yeni enum olarak eklenmez.

Yalnız eski Phase38 JOIN `requested_file_ids` kapsamındaki File ID'ler sorgulanır. Duplicate/unknown ID, unknown presence/schema/field/type veya yanlış current source digest kapalı hatadır. Scope içindeki görünürlük ve koşul eşleşmesi, fiziksel file varlığı değildir. Request yeni candidate/reference/path/observation/override veya sorgu dili taşımaz.

## Query v1 ve kapalı witness zarfı

`termivar-offline-disclosed-cohort-query/v1` common dört alanı (schema/demo label/demo-only true/nested 18 false trust_flags), current Phase38 iki digest'i, tam request, `query_status`, sorted unique `matched_reference_ids`, altı `counts` ve sabit `limitations` taşır. Status yalnız `matched_in_disclosed_scope` veya `no_match_in_disclosed_scope`; ikincisi görünür source kapsamı dışına ilişkin oracle değildir.

Görevde witness'ın referans alanları tanımlıdır. Üst zarf için gerekli dar ve açık seçim: `termivar-offline-disclosed-cohort-witnesses/v1` common + `source_phase38_join_sha256` + `source_phase38_manifest_sha256` + aynı yeni strict `request` + `results` + `counts` + `limitations`. Bu zarf yalnız yeni request'i tekrar eder; ham source catalog veya global packet kopyası taşımaz.

Her witness result tam beş alan: `reference_id`, `disclosure_status`, `matched_file_ids`, `supporting_projection_bindings`, `projections`. Yalnız provided ve sorted unique reference. Matched file listesi bütün assertion ID'lerini request sırasında içerir. Supporting binding gerçek `(reference_id,candidate_id,file_id)`; required file projection'larından tüm gerçek üçlüler kanonik sırayla korunur, duplicate reddedilir. Yeni projection/witness ID yoktur.

Projection listesi referansın bütün 11-alan source izinli paketidir; sadece assertion'a uyan projection'larla filtrelenmez, orijinal sıra/tür/değer korunur. Required file'ın bütün ilgili projection presence değerleri assertion ile aynı olmalıdır; çelişki rastgele seçilmez. Source-bound builder bütün packet'ı korur. Yeni beş-output inspector bu wire ilişkisini inceler; özgün source completeness veya başka eşleşme yokluğunu bağımsız kanıtlayamaz.

Query ve witness altı count alanı aynıdır: `required_file_count`, `matched_reference_count`, `matched_projection_count`, `matched_candidate_count`, `matched_present_projection_count`, `matched_absence_projection_count`. Projection sayımı supporting üçlü sayısı değil bütün dönen paket toplamıdır. Query status ve matched ID listesi witness results ile eşleşir. Boş eşleşme kaynakta/dünyada hiçbir ilişki yok anlamına gelmez.

## Immutable source ve saf API

`load_co_reference_source(join_path,lookup_path,receipt_path,summary_path,manifest_path,budget)` yeni exact frozen/slots/repr-hidden `ValidatedCoReferenceSource` üretir. Beş immutable byte'ın strict owner ilişkileri, gerçek eski manifest request'i, Markdown ve dört payload manifest byte eşliği doğrulanır. Public `read_co_reference_source` `(join,lookup,receipt,actual_descriptors,validated_manifest_request)` beşlisidir. Phase38 aggregate inspector raporu tam model sayılmaz; eski `ValidatedPhase37Source` farklı input grubudur.

`build_cohort_query(validated_source,request)` immutable source grubu tüketir ve `ValidatedCohortQuery` döndürür. `build_cohort_witnesses(validated_source,validated_query)` aynı source-bound query'yi yeniden türetip wire eşliğiyle gerçek witnesses üretir. Caller'ın trusted/validated/allow alanı otorite değildir. Standalone yeni query constructor'ının iç wire doğrulaması source truth/producer kanıtı değildir.

## Receipt, schema ve limitler

`termivar-offline-cohort-source-receipt/v1` common, beş actual Phase38 `{name,bytes,sha256,schema_version}` descriptor'ı, current iki digest, fixed beş-name schema haritası, inherited visible altı source count, `content_scope=five_Phase38_artifact_internal_correspondence_only`, sınırlamalar taşır. Source counts eski JOIN.source_counts kapsamıdır; JOIN.counts onlu pair sayımı veya global bloke toplamları değildir. Dış manifest `termivar-offline-cohort-manifest/v1`, inspector `termivar-offline-cohort-inspection/v1`; manifest ilk dört payload'ı bağlar, kendisini kapsamaz.

Request 32 KiB; source JOIN/LOOKUP/RECEIPT 256/128/64 KiB, MD 128 KiB, manifest 64 KiB, toplam fiziksel input 1 MiB. Query/MD 128 KiB, witnesses 256 KiB, receipt/manifest 64 KiB; required file 2–8/match ref 8/projection 64/depth 12/node 20.000/text 512. Owner daha sıkı sınırları, strict UTF-8/JSON/duplicate/unknown schema-field-type, float/NaN/Infinity/bool-as-int/digest/presence/binding reddi korunur. Yeni/boş output; truncation/overwrite/partial-write başarısı yoktur. Bu sözleşme belgesi runtime hostile kabulü değildir; actual kapsam teslim kaydındadır.
