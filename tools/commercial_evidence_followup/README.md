# Offline Missing-Evidence Follow-up Queue & Analyst Handoff

**OFFLINE DEMONSTRATION — RECORDED MISSING EVIDENCE FOLLOW-UP ONLY — NO OBSERVATION OR ASSIGNMENT AUTHORIZED**

Bu bağımsız offline araç, doğrulanmış Phase39 witness paketlerindeki kayıtlı `missing` projection'ları gerçek reference/candidate/file supporting bağlarına dayanan takip taleplerine dönüştürür. Seçilen referansların bütün izinli paketleri korunur; ayrı analyst handoff aynı işleri ve bu işlere ait bütün referans paketlerini taşır. `recorded_missing_source ≠ current_physical_file_missing`.

**2026-11-14:** İki izinli Phase40 ürün çağrısı tamamlandı: assembly **exit 0**, inspector **exit 0**. Bütçe **2/2 tüketildi ve kapandı; kalan 0**. Gerçek source witness'tan tek pending talep **F0001 / CAND0002 / recorded missing** türetildi; durumları **prepared_unassigned / not_observed** kaldı. CAND0001 present için iş oluşturulmadı. Görev gönderilmedi, atanmadı veya tamamlanmadı; kaynak yeniden gözlenmedi.

Altı gerçek output'un boyut/SHA256 kimliği ve task'ın tam bağı [DEMO_DELIVERY](../../docs/commercial/operations/phase40/DEMO_DELIVERY.tr.md) kaydındadır. Üretim source commit'i `de2172dbf05f64aad08d4bcebd8c8fc890dd74d9`, tree `6599d3f8d5c222f5d7476ced2416efbad271587b`. Üretim sonrasında yalnız README ve teslim belgesi actual sonuçlarla güncellendi; dokuz kod/örnek dosyası ve diğer üç belge generation snapshot'ıyla korundu. Çağrılar sonrası saltokunur koruma incelemesinde **453/453 eski artefact, 415/415 korunan source, 21/21 asset, 9/9 kod/örnek ve 60030 bayt wheel değişmedi; uyuşmazlık 0**. İlk çıktılarda 20 ve ayrı incelemede 18, ikinci altı-output incelemesinde 15 metadata karşılığı eşleşti; bunlar runtime kabulü değildir.

## Gerçek source grubu ve immutable adapter

Yalnız `outputs/phase39-cohort-query/` altındaki açık QUERY, WITNESSES, RECEIPT, Markdown ve manifest okunur. Yeni `ValidatedPhase39Source(artifact_bytes)` exact beşli bytes tuple, frozen/slots/repr-hidden kayıttır. `load_source(query_path,witnesses_path,receipt_path,summary_path,manifest_path,budget)` stabil ve bounded fiziksel okuma yapar. `read_source(snapshot)` memory-only yeniden doğrulayarak `(query,witnesses,receipt,source_artifacts)` dört tuple'ını ve bağımsız model kopyalarını döndürür.

Adapter önce gerçek dört payload byte/hash'ini eski manifestle bağlar; gerçek owner kapalı validator'ları ve `validate_relationships`, `query_from_witnesses` tam query eşliği, qualified owner `render_cohort_summary` byte eşliği ve `manifest_data(query,witnesses,receipt,payloads)` **dört argümanlı** tam manifest eşliği gerekir. Caller trusted/validated etiketi yetki sağlamaz. Phase39 aggregate inspector raporu immutable tam model değildir; Phase38'in `ValidatedCoReferenceSource` sınıfı bu beşli için kullanılmaz.

Request'teki `source_phase39_witnesses_sha256`, gerçek ikinci source dosyası WITNESSES'ın `97d962…` kimliğidir; ilk QUERY'nin `a51eb6…` hash'i değildir. `source_phase39_manifest_sha256` current manifest `aaab43…` kimliğidir. Phase39 modellerine gömülü eski Phase38 JOIN/manifest pinleri lineage olarak kalır; current Phase39 kimlikleri yerine geçirilmez. Tam ölçülmüş kaynak kimlikleri teslim belgesindedir. Phase38/37 dosyaları, eski kapsül, CSV, guard, native kaynak veya eski CLI açılmaz.

## Strict request ve missing iş türetimi

`termivar-offline-evidence-followup-request/v1` exact altı alan: `schema_version`, `mode=demo`, `request_reference`, iki current Phase39 SHA256, `requested_reference_ids`. 1–8 benzersiz reference source WITNESSES results içinde bulunmalı; unknown/duplicate/schema/digest uyuşmazlığında bütün request reddedilir. Yeni path/candidate/observation/reviewer/assignment/authorization alanı yoktur.

`build_followup_queue(validated_source,request)` yalnız source-bound snapshot'tan `ValidatedFollowupQueue` üretir. Seçilen her packet, eski witness result'ın bütün beş alanını korur: `reference_id`, `disclosure_status`, `matched_file_ids`, `supporting_projection_bindings`, `projections`. Bütün 11-alan projection listesi özgün sıra ve türleriyle taşınır; missing satırlara kırpılmaz.

Her gerçek missing projection'ın exact `(reference_id,candidate_id,file_id)` supporting triple'ı bulunmalıdır. Eşleşmeyen veya supporting kümesinin dışında kalan bir missing projection bütün isteği reddeder; sessizce atılmaz. Aynı triple için iki task yoktur. Ayrı geçerli candidate bağları korunur; duplicate/çelişkili/ambiguous eşleme fail-closed'dur. Shared File ID farklı referanslarda aynı bağlam sayılmaz. Present için task üretilmez; null byte/hash korunur.

Task'ın exact sekiz alanı: `task_id`, `reference_id`, `candidate_id`, `file_id`, `recorded_source_file_presence=missing`, `followup_kind=request_fresh_source_observation`, `task_status=prepared_unassigned`, `fulfillment_status=not_observed`. Yerel deterministik `(reference,candidate,file)` sırasındaki `F0001…F0064` kimliği global kimlik/imza değildir. Araç talep göndermez, atamaz, onaylamaz, kabul etmez, tamamlamaz veya yeni gözlem almaz.

## Queue, handoff ve receipt ayrı kapsamlar

Queue `termivar-offline-evidence-followup-queue/v1`; handoff `termivar-offline-evidence-analyst-handoff/v1`; receipt `termivar-offline-evidence-followup-source-receipt/v1`. Common alanlar schema/demo-label/demo-only true ve kapalı **18 nested false `trust_flags`** nesnesidir.

Queue yedi sayımı: `selected_reference_count`, `selected_projection_count`, `recorded_present_projection_count`, `recorded_missing_projection_count`, `pending_task_count`, `distinct_file_count`, `distinct_candidate_count`. Distinct file/candidate bütün seçili projection paketlerinden gelir; pending yalnız benzersiz gerçek task bağlarını sayar. Bu değerler global envanter değildir.

`build_analyst_handoff(validated_queue)` aynı task ID/bağ/durumlarını taşır; yalnız işi olan referansların bütün paketlerini seçer. Handoff'un aynı yedi sayımı kendi paket/task kapsamından yeniden türetilir; işi olmayan referanslar queue'da kalabilir, handoff'a kopyalanmaz. Hiç iş yoksa handoff task/packet listeleri ve sayımları sıfırdır. `queue_sha256`, doğrulanmış canonical queue JSON'unun gerçek byte kimliğidir; producer imzası değildir.

Receipt'in `source_counts` alanı gerçek **Phase39 QUERY.counts altılısıdır**: required file/matched reference/projection/candidate/present/absence. Eski receipt'in inherited visible altılısı, pair onlusu veya eski global sayım kullanılmaz. Full packets ek unrequired File ID taşıyabileceği için selected distinct files, source required file sayısıyla sınırlandırılmaz. Receipt source artifacts beş gerçek `{name,bytes,sha256,schema_version}` kaydı; Markdown schema null; `content_scope=five_Phase39_artifact_internal_correspondence_only`.

## Tamamlanan exact iki ürün çağrısı

Aşağıdakiler gerçek generation kaydındaki tamamlanan tarihsel iki çağrıdır; yeniden çalıştırma izni değildir. İkinci çağrı ilk exit 0, eksiksiz ilk beş output ve queue/handoff/receipt/MD/manifest dar manuel incelemesinden sonra çalıştı. Actual exit kodları **[0,0]**, kapalı **2/2 bütçe**, kalan çağrı **0**. Retry/üçüncü/preflight/helper execution/test runner veya eski CLI yoktur. Eski fazların kapalı bütçeleri ve Phase24/29 istisnaları yeniden açılmaz.

```text
python -I -B security-platform/tools/commercial_evidence_followup/assemble_evidence_followup.py --query outputs/phase39-cohort-query/cohort-query.json --witnesses outputs/phase39-cohort-query/cohort-witnesses.json --receipt outputs/phase39-cohort-query/cohort-source-receipt.json --source-summary outputs/phase39-cohort-query/cohort-summary.md --source-manifest outputs/phase39-cohort-query/manifest.json --request security-platform/tools/commercial_evidence_followup/examples/demo_followup_request.json --output-dir outputs/phase40-evidence-followup
```

```text
python -I -B security-platform/tools/commercial_evidence_followup/inspect_evidence_followup.py --queue outputs/phase40-evidence-followup/evidence-followup-queue.json --handoff outputs/phase40-evidence-followup/analyst-handoff.json --receipt outputs/phase40-evidence-followup/followup-source-receipt.json --summary outputs/phase40-evidence-followup/followup-summary.md --manifest outputs/phase40-evidence-followup/manifest.json --output outputs/phase40-evidence-followup/inspection-summary.json
```

Assembly ilk beş output'u yeni dizinde üretti: queue, handoff, receipt, Markdown, manifest. Manifest ilk dört gerçek payload'ı bağladı; kendi digest'i ve inspection çıktısı kapsam dışıdır. Inspector **internal_content_status=content_consistent** raporladı; kapsam yalnız `five_new_evidence_followup_outputs_internal_correspondence_only`. `original_Phase39_files_read=false`, `source_missing_observation_independently_verified=false`, `source_followup_necessity_independently_verified=false`, `source_import_independently_verified=false`. Görev gönderme/atama/fulfillment, collection authorization ve human acceptance alanları false kaldı.

Queue ve handoff kendi yedi sayımında **1 reference / 2 bütün projection / 1 recorded present / 1 recorded missing / 1 pending / 2 distinct file / 2 distinct candidate** taşıdı. Source QUERY altılısı ayrıca **2 required / 1 matched reference / 2 projection / 2 candidate / 1 present / 1 absence** kaldı. Handoff whole beş alanlı reference paketini ve bütün 11-alan iki projection'ı kaynak sırası/türleriyle korudu; missing byte/hash JSON null kaldı. Canonical queue SHA256, gerçek queue dosyası SHA256 ve manifest ilk payload hash'i **fd86dda8259efe31c661cd8f4ca4732e1a000f65854ff66c69fa346ae0ba71ec** ile aynı. Exact18 nested false ve demo-only true korundu; bu iç tutarlılık source observation veya task gerekliliğinin bağımsız kanıtı değildir.

## Limit, bağımlılık ve açık kabuller

Request 32 KiB; source QUERY/WITNESSES/RECEIPT/MD/manifest 128/256/64/128/64 KiB, toplam fiziksel input 1 MiB. Yeni queue/handoff/receipt/summary/manifest 256/128/64/128/64 KiB. Reference8/projection64/task64/depth12/node20.000/text512. Daha sıkı owner limitleri korunur. Strict UTF-8/JSON; duplicate/unknown/schema/type/float/NaN/Infinity/bool-as-int/digest/binding ret kuralları kapalıdır. Overwrite/otomatik silme veya truncate başarı yolu yoktur. Variable Markdown inert escaped text'tir; path/URL/script/HTML çalıştırılmaz.

Yeni delta kaynak paketi standalone binary veya production wheel değildir. Korunmuş Phase39 owner contract/renderer/manifest ve kapalı yardımcı kod/import zinciri gerekir; eski çalışma verisi/CSV/kapsül/native kaynaklar açılmaz. Gerçek ikinci offline host kabulü yapılmış değildir. Backend/operator-console/API/GUI/DB/servis/scheduler yoktur. Herhangi bir browser/UI işi bu turun kapsamı değildir; Phase19 file:// kabul engeli açık kalır.

NOT_RUN: hostile/duplicate JSON/invalid UTF-8/BOM, yanlış digest/schema/unknown reference, duplicate/ambiguous projection binding, birden fazla/sıfır missing record, değiştirilmiş witness, limit/permission/crash/partial write/repeat determinism/ikinci offline host; gerçek analist görev kabulü/ataması, source reobservation/dosya toplama, source freshness/Phase31 guard, compiler/module closure/ownership/native/producer/human/legal/customer/release. Test/runner/coverage/typecheck/build/install/package manager ve canlı kabul yapılmaz. Kaynak koruma kodu runtime kabulü değildir; hash imza/attestation değildir; kimlikler hassas olabilir, minimizasyon anonimlik sağlamaz.

Belgeler: [queue sözleşmesi](../../docs/commercial/operations/phase40/FOLLOWUP_QUEUE_CONTRACT.tr.md), [analist handoff](../../docs/commercial/operations/phase40/ANALYST_HANDOFF.tr.md), [disclosure/trust](../../docs/commercial/operations/phase40/DISCLOSURE_AND_TRUST.tr.md), [teslim](../../docs/commercial/operations/phase40/DEMO_DELIVERY.tr.md).

Kaynak ZIP `Termivar-Offline-Evidence-Followup-phase40-2026-11-14.zip`. Ölçülen ZIP/source/asset/delivery kimliklerinin otoritesi [source manifest](../../../outputs/phase40-evidence-followup-source-manifest.json), [asset manifest](../../../outputs/phase40-evidence-followup-asset-manifest.json), [delivery manifest](../../../outputs/phase40-evidence-followup-delivery-manifest.json) ve [closure](../../../outputs/phase40-evidence-followup-closure.json) kayıtlarıdır; öz hash döngüsü oluşturulmaz. Altı operasyonel review nesnesi source/delivery manifestlerine gömülür; ayrı altı review dosyası veya özel working-state/prompt paket girdisi değildir. Asset manifest dış metadata'dır: korunmuş 21 asset'in byte/SHA eşliği ve `new_assets=[]`; asset ZIP'e kopyalanmaz. Phase7–39/backend/native/HBF/Altay/auth/DB/rol/credential/wheel/lock/lisans değişmez. İki izinli çağrı ve dar actual inceleme tamamlandı; ölçülmüş teslim kapanınca durulur. Phase41/yeni mikro özellik/test/native/release başlatılmaz.
