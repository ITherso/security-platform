# Phase42 — Deferred intake kapalı sözleşmeleri

**OFFLINE DEMONSTRATION — DEFERRED RESPONSE INTAKE ONLY — NO CANDIDATE RESPONSE RECEIVED**

Bağımsız consumer mevcut unsubmitted template'i yanıtsız intake ve classification'a dönüştürür. Future candidate decoder ayrı memory-only API'dir; demo positive/negative/None decoder çağrısı yapmaz. Yapısal uyum gözlem doğruluğu veya submission yetkisi değildir.

## Şemalar ve exact alanlar

Request `termivar-offline-deferred-intake-request/v1`: schema_version/mode demo/request_reference/source_phase41_slots_sha256/source_phase41_manifest_sha256/selected_task_ids/candidate_source existing_unsubmitted_template.1–8 unique gerçek task; wrongdigest/unknown/duplicate fail-closed/all-or-nothing. Request ve assembly CLI candidate payload/path almaz; original F kimliği korunur.

Common4 schema_version/demo_label/demo_only true/exact18 nested false trust_flags'tır. Intake `termivar-offline-deferred-intake-register/v1` common + currentSHA2/request/reference_packets/intake_entries/counts/limitations taşır. Entry exact10 task_id/reference_id/candidate_id/file_id/binding_digest/slot_status/response_status/candidate_present/candidate_classification/candidate_response. Actual demo awaiting_external_response/unsubmitted/false/no_candidate_supplied/null'dur; gerçek source slot/template null değerlerinden türetilir. None decoder'a verilmez.

Classification `termivar-offline-deferred-intake-classification/v1` common + currentSHA2/intake_register_sha256/task_classifications/counts/limitations. Row exact6 task_id/binding_digest/intake_status/structural_result/observation_verified/task_completed; awaiting_submission/not_evaluated_no_candidate/false/false. Canonical ilk JSON actual byte hash'i classification ile bağlanır. İlk JSON'da olmayan candidate ikinci modelde üretilmez.

Receipt `termivar-offline-deferred-intake-source-receipt/v1` common + source_artifacts/currentSHA2/source_schema_versions/source_counts/content_scope/limitations'dır. Beş gerçek name/bytes/sha256/schema_version descriptor; Markdown schema null. Content scope five_Phase41_artifact_internal_correspondence_only.

Source counts exact `{slots_counts:source7,template_counts:source7,phase40_counts:{queue_counts:original7,handoff_counts:original7}}` dört ayrı payda taşır. Phase40 queue/handoff whole projection kapsamı tek missing task nedeniyle daraltılmaz; distinct file2/candidate2 korunur. Yeni exact8 counts selected_task_count/selected_reference_count/intake_entry_count/awaiting_submission_count/candidate_present_count/structurally_compatible_count/observation_verified_count/completed_task_count; son4 integer0. Null/false/0/unknown birbirine çevrilmez.

Manifest schema termivar-offline-deferred-intake-manifest/v1; inspection schema termivar-offline-deferred-intake-inspection/v1. Manifest ilk4 actual payload kimliği/canonicalactualregisterSHA bağını taşır; kendisini ve inspection'ı hash'lemez. Inspector yalnız yeni5 output'un iç ilişkisini değerlendirir.

## Source adapter ve saf API

ValidatedPhase41Source exact tuple5bytes/frozen/slots/repr-hidden; constructor/read memory-only owner revalidation'dır. Load beş açık dosyayı bounded/stable fiziksel birer kez okur. Actual4payload/manifest eşliği önce, owner strict3/relationships/exacttemplate_from_slots/canonicalrawslots/qualifiedcorrectedMD/full4argmanifest sonra gerekir. read_source→slots/template/receipt/descriptors4tuple. Flat owner class kimliği korunur; qualified generic helper kullanılır. Phase40 snapshot/aggregate rapor yanlış source gruba uygulanmaz; eski CLI/build_response_slots ve eski source verileri açılmaz.

build_deferred_intake(source,request)→ValidatedDeferredIntake; read_deferred_intake(exact)→closedcopy; build_intake_classification(snapshot)→closedmodel; make_source_receipt(source,snapshot)→closedreceipt. validate_intake/classification/receipt ve validate_relationships üç kapalı kopyayı verir. Future decode_candidate_response exact eski owner ValidatedResponseSlots kullanır; fullsourcegroup proof değildir.

Current41 slots291…/manifest0d67… ile parent40 queueFD86/manifestE611 ayrıdır. Inherited binding221… parent40 queue ile hesaplanmıştır; current291 ile yeniden türetilmez. Source adapter orijinal owner bağını doğrular, builder kopyalar. Yeni wire parent preimage içermez; new-only inspector original binding kriptografisini bağımsız doğrulayamaz. [Binding ve future decoder](TASK_BINDING_AND_CLASSIFICATION.tr.md) ayrıntıyı açıklar.

## Full packet ve limitler

Yalnız task-associated old5-field reference paketleri, bütün11 projection alanı/source sıra/tür/null ile korunur. Present CAND0001 paket bağlamında kalır; ona yeni entry yoktur. Bloke/eşleşmeyen olumlu child metadata/globalcatalog aktarılmaz. Workflow_flags veya source17 mirası yoktur; exact18 trustfalse/demo true korunur.

Request32K/source256-128-64-128-64K/total1MiB; output intake256K/classification128K/receipt64K/summary128K/manifest64K; task8/ref8/proj64/string512/depth12/nodes20.000 ve daha sıkı owner sınırları. Strict UTF-8/JSON, duplicate/unknown/schema/type/float/NaN/Infinity/bool-as-int/SHA/binding ret; yeni boş output/overwrite-silme yok. Report açıklamaları da512 sınırındadır; limit gevşetilmez. Kodda guard olması hostile/runtime kabulü değildir. [Trust](TRUST_AND_DISCLOSURE.tr.md), [actual teslim](DEMO_DELIVERY.tr.md).
