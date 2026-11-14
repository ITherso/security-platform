# Offline disclosed ALL-OF cohort query

**OFFLINE DEMONSTRATION — DISCLOSED COHORT MATCH ONLY — NO CURRENT FILE OR SOURCE RELATIONSHIP VERIFIED**

Bu bağımsız offline araç Phase38'in doğrulanmış görünür metadata'sında 2–8 File ID için doğrudan N-way **ALL-OF** kesişimi ve her File ID'nin kayıtlı presence koşulunu sorgular. Eşleşen provided referansın bütün izinli projection'ları ve gerçek supporting üçlüleri witness olarak döner. Pairwise co-reference transitif varsayılmaz; yeni guard/evaluator/query framework veya source observation oluşturulmaz.

**2026-11-14** tarihinde iki izinli Phase39 çağrısı tamamlandı: ALL-OF cohort assembly **exit 0**, içerik inspector'ı **exit 0**. Bütçe **2/2 tüketildi ve kapandı; kalan 0**. Gerçek present/missing assertion'larıyla **2 required File ID → 1 matched provided referans → 2 gerçek supporting üçlü / bütün 2 projection (1 present/1 absence)** üretildi. Status `matched_in_disclosed_scope`; kayıtlı presence güncel fiziksel dosya durumu olarak sunulmadı.

Altı gerçek çıktı `outputs/phase39-cohort-query/` altında üretildi; tam byte/SHA256 kimlikleri, supporting üçlüler ve gözlemler [teslim kaydındadır](../../docs/commercial/operations/phase39/DEMO_DELIVERY.tr.md). Üretim source commit'i `3a8ad2e02415666099f25400752685a9ea51d519`, tree `ad832dcf941664ea444d338b9c44d478f8223845`. Üretim sonrası yalnız README ve teslim belgesi actual sonuçlarla güncellendi; dokuz kod/örnek dosyası ve diğer üç belge değişmedi.

## Gerçek source grubu ve yeni immutable adapter

Yalnız beş açık Phase38 input'u: JOIN, LOOKUP, RECEIPT, Markdown, manifest. `source_phase38_join_sha256` ve `source_phase38_manifest_sha256` bunların gerçek byte kimlikleridir. Eski JOIN'in içindeki `source_index_sha256`/`source_manifest_sha256` Phase37'ye aittir; current Phase38 kimlikleri yerine kullanılamaz.

Yeni dar `load_co_reference_source(join_path,lookup_path,receipt_path,summary_path,manifest_path,budget)` exact frozen/slots/repr-hidden `ValidatedCoReferenceSource` üretir. `read_co_reference_source` beşli `(join,lookup,receipt,actual_source_descriptors,validated_manifest_request)` döndürür. Constructor/read beş gerçek immutable byte'ı yeniden owning doğrular; caller validated/trusted/allow etiketi otorite değildir. Phase38'deki aggregate inspector raporu tam JOIN modeli sayılmaz; eski `ValidatedPhase37Source` bu yeni beşli için kullanılmaz.

Sıra: bounded beş fiziksel input okuması; strict owner üç-model parse/cross-relation; gerçek eski manifest request'i; owner Markdown byte eşliği; dört gerçek payload identity; owner `manifest_data(join,lookup,receipt,payloads,request)` tam beş-argüman eşliği. Ancak sonra yeni snapshot kullanılabilir. İkinci parser/guard framework yazılmaz. Phase37 dosyaları/CSV/kapsül/guard/native veya eski CLI açılmaz.

## Strict request, query ve witness

Request `termivar-offline-disclosed-cohort-query-request/v1` tam altı alan taşır: `schema_version`, `mode`, `request_reference`, iki current Phase38 SHA256 alanı, `required_file_assertions`. Yalnız demo; 2–8 farklı source-owned File ID. Her assertion tam `file_id`/`expected_source_file_presence`; gerçek enum **present/missing**. `missing` kayıtlı absence'dır; yeni `absent` enum'u eklenmez. ID eski JOIN'in `requested_file_ids` kapsamında olmalı; duplicate/unknown/digest/presence uyuşmazlığı kapalı kurallarla işlenir. Yeni candidate/reference/path/gözlem/override veya sorgu dili yoktur.

`build_cohort_query(validated_source,request)` gerçek immutable source grubundan doğrudan bütün required file visible-ref kümelerinin kesişimini alır. Her required file için gerçek projection/binding ve tam source packet gerekir; aynı file'a ilişkin bütün kaynak presence değerleri assertion'la eşleşmelidir. Çelişki rastgele seçilmez. Status `matched_in_disclosed_scope` veya `no_match_in_disclosed_scope`; no-match fiziksel yokluk veya başka source'ta ilişkisizlik değildir.

Query `termivar-offline-disclosed-cohort-query/v1`; witness `termivar-offline-disclosed-cohort-witnesses/v1`; receipt `termivar-offline-cohort-source-receipt/v1`. Common schema/demo label/demo-only true/nested 18 false trust_flags'tır. Gerekli witness zarfı açık ve kapalıdır: common + current iki digest + yeni strict request + results/counts + limitations. Ham source catalog tekrarı yoktur. Her witness result tam beş alan: reference ID/disclosure status/matched File ID'ler/gerçek supporting üçlüler/bütün 11-alan projection listesi. Sadece koşula uyan projection'lar filtrelenmez; source sıra ve türler korunur.

Query/witness altı sayımı required file; matched reference/projection/candidate/present/absence'dır. Projection sayımı yalnız supporting üçlüleri değil bütün dönen paketleri sayar. Receipt'in source_counts altılısı Phase38 JOIN'in inherited visible indeks kapsamıdır; join'in on pair sayımı veya eski global bloke toplamları değildir. Bloke kimlik/olumlu metadata veya eşleşmeyen full packet kopyalanmaz.

## Tamamlanan exact iki ürün çağrısı

Aşağıdakiler gerçek generation kaydındaki tamamlanmış iki çağrıdır; yeniden çalıştırma izni değildir. İkinci çağrı ilk exit 0 ve eksiksiz beş output'un query/witness/receipt/MD manuel incelemesinden sonra çalıştı. Actual exit kodları **[0,0]**, kapalı **2/2 bütçe**, kalan çağrı **0**. Retry/üçüncü/preflight helper/test runner/eski CLI yoktur. Phase20–38 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_cohort_query/assemble_cohort_query.py --join outputs/phase38-co-reference/co-reference-join.json --source-lookup outputs/phase38-co-reference/co-reference-lookup.json --receipt outputs/phase38-co-reference/co-reference-source-receipt.json --source-summary outputs/phase38-co-reference/co-reference-summary.md --source-manifest outputs/phase38-co-reference/manifest.json --request security-platform/tools/commercial_cohort_query/examples/demo_cohort_request.json --output-dir outputs/phase39-cohort-query
```

```text
python -I -B security-platform/tools/commercial_cohort_query/inspect_cohort_query.py --query outputs/phase39-cohort-query/cohort-query.json --witnesses outputs/phase39-cohort-query/cohort-witnesses.json --receipt outputs/phase39-cohort-query/cohort-source-receipt.json --summary outputs/phase39-cohort-query/cohort-summary.md --manifest outputs/phase39-cohort-query/manifest.json --output outputs/phase39-cohort-query/inspection-summary.json
```

Assembly ilk beş output'u üretti. Manifest gerçek ilk dört payload'ı bağlar, kendisini/inspection çıktısını kapsamaz. Inspector `internal_content_status=content_consistent`, kapsam `five_new_cohort_outputs_internal_correspondence_only` raporladı. `original_Phase38_files_read=false`, `source_cohort_match_independently_verified=false`, `source_no_other_matches_independently_verified=false`, `source_import_independently_verified=false`; yalnız yeni beş dosyanın iç tutarlılığıdır. Source match, full-source completeness veya başka eşleşme bulunmadığı bağımsız kanıtlanmadı. Source-bound builder'ın bütün packet koruması ile inspector'ın yeni wire ilişkisi farklı güven sınırlarıdır.

Witness gerçek required üçlüleri ve kaynak paketin bütün projection sırasını/türlerini korudu; missing byte/hash JSON null kaldı. Receipt'in inherited visible source altı sayımı (2 file/1 reference/2 candidate/2 projection/1 present/1 absence) query'nin required/matched altı sayımından ayrıdır. Nested 18 false ve demo-only true korundu. ALL-OF no-match, 3+ dosyada transitive pair yanılsaması, çelişkili presence veya adversarial/ikinci host runtime kabulü yapılmadı.

## Limit, kod bağımlılığı ve NOT_RUN

Request 32 KiB; source JOIN/LOOKUP/RECEIPT 256/128/64 KiB, MD 128 KiB, manifest 64 KiB; toplam fiziksel input 1 MiB. Query/MD 128 KiB, witnesses 256 KiB, receipt/manifest 64 KiB; assertions 2–8/reference 8/projection 64/depth 12/node 20.000/text 512. Daha sıkı owner limitleri korunur. Strict UTF-8/JSON; duplicate/unknown schema/field/type, float/NaN/Infinity/bool-as-int, yanlış digest/File ID/binding/presence reddi; truncate/overwrite/partial-write başarısı yoktur. JSON URL/path yeni input yetkisi değildir.

Bu delta kaynak paketi standalone binary veya production wheel değildir. Korunmuş Phase38 owner contract/renderer/manifest ve eski kapalı wire/güvenli okuma yardımcı kodu gerekir; bu bağımlılık eski runtime/input verilerine erişmek değildir. Yeni source ZIP eski dependency kodunu, Phase38 inputlarını, CSV/kapsül/native/binary/wheel/cache/DB veya özel çalışma dosyalarını kopyalamaz. Gerçek ikinci host kabulü NOT_RUN'dır. Backend/operator-console/API/GUI/DB/servis/scheduler entegrasyonu yoktur.

18 nested false ve demo-only true korunur. `cohort_condition_matched ≠ physical_file_state_verified`; present/missing geçmiş kayıttır. Producer/source freshness/guard/compiler/module closure/ownership/native/human/legal/customer/production/release yetkisi kazanılmaz. Eski fresh kodu yeni gözlem/TTL garantisi değildir. Kimlik/hash hassas olabilir; minimizasyon şifreleme/anonimlik değildir.

NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest/File ID/unknown/nonvisible, çelişkili presence, ALL-OF no-match, üç veya daha fazla file'da transitive pair yanılsaması, duplicate/bozuk binding/sahte witness, modified JOIN/LOOKUP, limit/permission/crash/partial write/repeat determinism/ikinci offline host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Koruma kodu runtime kabulü değildir. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir; file:// kısıtı aşılmaz.

Belgeler: [sözleşmeler](../../docs/commercial/operations/phase39/COHORT_QUERY_CONTRACT.tr.md), [witness/disclosure](../../docs/commercial/operations/phase39/WITNESS_AND_DISCLOSURE.tr.md), [güven sınırı](../../docs/commercial/operations/phase39/TRUST_BOUNDARY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase39/DEMO_DELIVERY.tr.md).

Kaynak teslim adı `Termivar-Offline-Cohort-Query-phase39-2026-11-14.zip`. Ölçülen ZIP boyutu/üye/SHA256 kimliklerinin otoritesi [source manifest](../../../outputs/phase39-cohort-query-source-manifest.json), [delivery manifest](../../../outputs/phase39-cohort-query-delivery-manifest.json) ve [closure](../../../outputs/phase39-delivery-closure.json) kayıtlarıdır; öz hash döngüsü oluşturulmaz. Operasyonel altı review kaydı manifestlere gömülüdür; özel working-state veya altı ayrı review dosyası paket girdisi değildir. Phase7–38 ve korunan runtime değişmez. İzinli iki çağrı tamamlandı; ölçülmüş teslim kapanınca Phase40/yeni mikro özellik/test/native/release başlatılmaz.
