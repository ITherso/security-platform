# Offline Missing-Evidence Follow-up Queue & Analyst Handoff

**OFFLINE DEMONSTRATION — RECORDED MISSING EVIDENCE FOLLOW-UP ONLY — NO OBSERVATION OR ASSIGNMENT AUTHORIZED**

Bu bağımsız offline araç, doğrulanmış Phase39 witness paketlerindeki kayıtlı `missing` projection'ları gerçek reference/candidate/file supporting bağlarına dayanan takip taleplerine dönüştürür. Seçilen referansların bütün izinli paketleri korunur; ayrı analyst handoff aynı işleri ve bu işlere ait bütün referans paketlerini taşır. `recorded_missing_source ≠ current_physical_file_missing`.

**Kaynak hazırlığı, 2026-11-14:** Phase40 ürün çağrısı **0**. Yeni queue/handoff/receipt/inspector sonucu ve yeni output/ZIP boyutu veya SHA256 başarı kaydı değildir. Gerçek Phase39 kaynak metadata'sının beklenen bir pending talebi desteklemesi, yeni ürünün çalıştığı anlamına gelmez. Actual kayıt için [DEMO_DELIVERY](../../docs/commercial/operations/phase40/DEMO_DELIVERY.tr.md) kullanılır.

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

## İzinli exact iki ürün çağrısı

Aşağıdakiler hazırlanan komutlardır; çalışmış başarı kaydı değildir. Phase40 en fazla iki yeni ürün çağrısı kullanır; başarısız çağrı da tüketilir. İkinci çağrı yalnız ilk exit 0, eksiksiz ilk beş output ve queue/handoff/receipt/MD/manifest dar manuel incelemesinden sonra çalışabilir. Retry/üçüncü/preflight/helper execution/test runner veya eski CLI yoktur. Eski fazların kapalı bütçeleri ve Phase24/29 istisnaları yeniden açılmaz.

```text
python -I -B security-platform/tools/commercial_evidence_followup/assemble_evidence_followup.py --query outputs/phase39-cohort-query/cohort-query.json --witnesses outputs/phase39-cohort-query/cohort-witnesses.json --receipt outputs/phase39-cohort-query/cohort-source-receipt.json --source-summary outputs/phase39-cohort-query/cohort-summary.md --source-manifest outputs/phase39-cohort-query/manifest.json --request security-platform/tools/commercial_evidence_followup/examples/demo_followup_request.json --output-dir outputs/phase40-evidence-followup
```

```text
python -I -B security-platform/tools/commercial_evidence_followup/inspect_evidence_followup.py --queue outputs/phase40-evidence-followup/evidence-followup-queue.json --handoff outputs/phase40-evidence-followup/analyst-handoff.json --receipt outputs/phase40-evidence-followup/followup-source-receipt.json --summary outputs/phase40-evidence-followup/followup-summary.md --manifest outputs/phase40-evidence-followup/manifest.json --output outputs/phase40-evidence-followup/inspection-summary.json
```

Assembly ilk beş output'u yeni/boş dizinde üretir: queue, handoff, receipt, Markdown, manifest. Manifest ilk dört gerçek payload'ı bağlar; kendi digest'i ve inspection çıktısı kapsam dışıdır. Inspector yalnız bu beş yeni dosyayı okur; canonical queue bytes/hash, task tekilliği/missing bağı, queue–handoff tam task eşliği ve whole-packet/null/count/MD/manifest ilişkisini denetler. `content_consistent` yalnız `five_new_evidence_followup_outputs_internal_correspondence_only` kapsamındadır. Original Phase39/source observation/takip gerekliliği bağımsız doğrulanmaz; görev gönderme/atama/fulfillment veya collection authority oluşmaz.

## Limit, bağımlılık ve açık kabuller

Request 32 KiB; source QUERY/WITNESSES/RECEIPT/MD/manifest 128/256/64/128/64 KiB, toplam fiziksel input 1 MiB. Yeni queue/handoff/receipt/summary/manifest 256/128/64/128/64 KiB. Reference8/projection64/task64/depth12/node20.000/text512. Daha sıkı owner limitleri korunur. Strict UTF-8/JSON; duplicate/unknown/schema/type/float/NaN/Infinity/bool-as-int/digest/binding ret kuralları kapalıdır. Overwrite/otomatik silme veya truncate başarı yolu yoktur. Variable Markdown inert escaped text'tir; path/URL/script/HTML çalıştırılmaz.

Yeni delta kaynak paketi standalone binary veya production wheel değildir. Korunmuş Phase39 owner contract/renderer/manifest ve kapalı yardımcı kod/import zinciri gerekir; eski çalışma verisi/CSV/kapsül/native kaynaklar açılmaz. Gerçek ikinci offline host kabulü yapılmış değildir. Backend/operator-console/API/GUI/DB/servis/scheduler yoktur. Herhangi bir browser/UI işi bu turun kapsamı değildir; Phase19 file:// kabul engeli açık kalır.

NOT_RUN: hostile/duplicate JSON/invalid UTF-8/BOM, yanlış digest/schema/unknown reference, duplicate/ambiguous projection binding, birden fazla/sıfır missing record, değiştirilmiş witness, limit/permission/crash/partial write/repeat determinism/ikinci offline host; gerçek analist görev kabulü/ataması, source reobservation/dosya toplama, source freshness/Phase31 guard, compiler/module closure/ownership/native/producer/human/legal/customer/release. Test/runner/coverage/typecheck/build/install/package manager ve canlı kabul yapılmaz. Kaynak koruma kodu runtime kabulü değildir; hash imza/attestation değildir; kimlikler hassas olabilir, minimizasyon anonimlik sağlamaz.

Belgeler: [queue sözleşmesi](../../docs/commercial/operations/phase40/FOLLOWUP_QUEUE_CONTRACT.tr.md), [analist handoff](../../docs/commercial/operations/phase40/ANALYST_HANDOFF.tr.md), [disclosure/trust](../../docs/commercial/operations/phase40/DISCLOSURE_AND_TRUST.tr.md), [teslim](../../docs/commercial/operations/phase40/DEMO_DELIVERY.tr.md).

Kaynak ZIP `Termivar-Offline-Evidence-Followup-phase40-2026-11-14.zip`. Ölçülen ZIP/source/asset/delivery kimliklerinin otoritesi [source manifest](../../../outputs/phase40-evidence-followup-source-manifest.json), [asset manifest](../../../outputs/phase40-evidence-followup-asset-manifest.json), [delivery manifest](../../../outputs/phase40-evidence-followup-delivery-manifest.json) ve [closure](../../../outputs/phase40-evidence-followup-closure.json) kayıtlarıdır; öz hash döngüsü oluşturulmaz. Altı operasyonel review nesnesi source/delivery manifestlerine gömülür; ayrı altı review dosyası veya özel working-state/prompt paket girdisi değildir. Asset manifest dış metadata'dır: korunmuş 21 asset'in byte/SHA eşliği ve `new_assets=[]`; asset ZIP'e kopyalanmaz. Phase7–39/backend/native/HBF/Altay/auth/DB/rol/credential/wheel/lock/lisans değişmez. İki izinli çağrı, dar inceleme ve ölçülmüş teslim kapanınca durulur; Phase41/yeni mikro özellik/test/native/release başlatılmaz.
