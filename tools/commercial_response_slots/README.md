# Offline Task Response Slots & Response Template

**OFFLINE DEMONSTRATION — TASK-BOUND RESPONSE SLOTS ONLY — NO RESPONSE OR OBSERVATION RECEIVED**

Bu bağımsız araç, doğrulanmış Phase40 pending görevleri için exact task-bound yanıt yuvaları ve gelecekte kullanılabilecek kapalı response alan tanımları üretir. `response_slot_created ≠ observation_received`; `binding_digest ≠ producer_signature`. Gerçek response kabul etmez, yeni kaynak gözlemi yapmaz, dosya toplamaz, analist atamaz veya görev kapatmaz.

**Kaynak hazırlığı, 2026-11-14:** Phase41 ürün çağrısı **0**. Yeni slots/template/receipt/inspector sonucu ve output/ZIP kimliği başarı kaydı değildir. Gerçek F0001 görevinin bu kabiliyeti destekleyen metadata taşıması yeni ürünün çalıştığı anlamına gelmez. Actual sonuçlar [DEMO_DELIVERY](../../docs/commercial/operations/phase41/DEMO_DELIVERY.tr.md) kaydına yazılır; kod freeze sonrası yalnız README ve teslim belgesi güncellenir.

## Gerçek beşli ve immutable Phase40 adapter

Yalnız `outputs/phase40-evidence-followup/` altındaki queue/handoff/receipt/Markdown/manifest açıktır. `ValidatedPhase40Source` exact beş immutable bytes tuple, frozen/slots/repr-hidden'dır. `load_source(queue_path,handoff_path,receipt_path,summary_path,manifest_path,budget)` bounded ve stabil fiziksel okuma yapar. `read_source(snapshot)` memory-only yeniden doğrulamayla `(queue,handoff,receipt,source_artifacts)` dört tuple'ını ve kapalı kopyaları döndürür.

Gerçek dört payload manifest byte/hash bağı önce kontrol edilir; sonra old owner üç JSON ve `validate_relationships`, qualified owner `render_followup_summary(queue,handoff,receipt)` byte eşliği ve `manifest_data(queue,handoff,receipt,payloads)` dört argümanlı full manifest eşliği gerekir. Canonical Phase40 queue kimliği korunur. Caller trusted etiketi yetki değildir. Phase39 snapshot, queue-only `ValidatedFollowupQueue` ve aggregate inspector tam Phase40 source grubu yerine kullanılamaz. Aynı owner sınıfı iki import kimliğine ayrılmaz; eski CLI import/çalıştırması yoktur.

Current kimlikler gerçek Phase40 queue `fd86dd…` ve manifest `e611c5…` byte SHA256'ıdır. Bunlar source içine kaydedilmiş parent39 witnesses `97d962…` / manifest `aaab43…` pinleri değildir. Tam kaynak boyut/SHA256 tablosu teslim belgesindedir. Phase39/38/37 dosyaları, CSV/kapsül/guard/native kaynaklar yeniden açılmaz; JSON path/URL'si yeni okuma yetkisi sağlamaz.

## Strict request, gerçek task ve binding digest

`termivar-offline-response-slot-request/v1` exact altı alan: schema_version, mode demo, request_reference, source_phase40_queue_sha256, source_phase40_manifest_sha256, selected_task_ids. 1–8 benzersiz gerçek source queue ID'si ve yalnız prepared_unassigned/not_observed task seçilir. Unknown/duplicate/digest/state uyuşmazlığı all-or-nothing reddedilir. Path/observation/analist/authorization/risk alanı yoktur.

`build_response_slots(validated_source,request)` immutable `ValidatedResponseSlots` üretir; `read_response_slots` exact snapshot'tan kapalı kopya sağlar. Source-bound builder task üyeliği/durumunu gerçek queue'dan doğrular. Wire-only reader özgün source task membership/necessity'yi bağımsız kanıtlamaz. Original F task kimliği korunur; selected packet altkümesinden eski task builder çalıştırılıp yeniden F0001 atanmaz.

`derive_task_binding(source_queue_sha256,task_record)` exact eski sekiz alanlı gerçek task'ı doğrular. SHA256 preimage yalnız şu beş anahtarlı canonical JSON'dur: source_phase40_queue_sha256, task_id, reference_id, candidate_id, file_id. Owner sorted-key/indent2/UTF-8/LF encoding kullanılır; task liste sırası girdiye eklenmez. Digest secret/token, dijital imza, anti-replay, producer authentication veya authorization değildir. Duplicate/çelişkili binding reddedilir.

## Slots, template ve gerçek null değerler

Slots schema `termivar-offline-task-response-slots/v1`; template `termivar-offline-task-response-template/v1`; receipt `termivar-offline-response-slot-source-receipt/v1`. Common4 schema/demo-label/demo-only true/exact18 nested false trust_flags'tır.

Her slot exact11 alan: task_id/reference_id/candidate_id/file_id/binding_digest/followup_kind/task_status/fulfillment_status/slot_status/submission/submission_contract. İlk durumlar request_fresh_source_observation, prepared_unassigned, not_observed, awaiting_external_response ve **submission=null**. Task-associated reference'ların whole beş alanlı packet'ı ve bütün 11-alan projection listesi source sıra/tür/null değerleriyle korunur. CAND0001 present için görev veya slot üretilmez; present projection aynı full packet'ta kalır.

submission_contract ve template.required_fields aynı exact yedi field-name→type-definition sözlüğüdür:

| Gelecekteki alan | Tür tanımı |
| --- | --- |
| task_id | string |
| binding_digest | sha256 |
| reported_presence | present_or_missing |
| observation_recorded_at | timestamp_string |
| observation_method | string |
| source_locator_description | string |
| evidence_sha256_if_available | sha256_or_null |

Bunlar gerçek observation değerleri değildir. Locator eski metadata'da yoksa türetilemez; yetkili kişi ileride sağlamalıdır. Bu turda future response parser/ingestion yoktur. Her template entry task_id/binding_digest/required_fields/response_status unsubmitted/**response=null** taşır. Template.slots_sha256 canonical ilk yeni JSON'un gerçek byte kimliğidir; imza değildir. Submitted/observed/assigned/accepted/completed örnek durumları oluşturulmaz.

## Ayrı kapsamlar ve bulunmayan workflow alanları

Slots/template yedi sayımı selected_task_count, selected_reference_count, response_slot_count, unsubmitted_slot_count, submitted_response_count, assigned_task_count, observed_task_count'tur. Son üçü integer0'dır; null response veya sıfır-byte file değildir. Completed count/durum eklenmez.

Receipt source_counts **{queue_counts: gerçek original7, handoff_counts: gerçek original7}** yapısını korur; tek task yüzünden source distinct_file_count2 bire indirilmez. Receipt ayrıca selected_task_count, beş gerçek source descriptor ve `content_scope=five_Phase40_artifact_internal_correspondence_only` taşır.

Beş gerçek Phase40 input modelinde **workflow_flags veya 17 workflow alanı yoktur**. Görev metninin kaynakta bulunma koşulu gereği yeni modeller workflow_flags taşımaz. Bu 17 flat false alan yalnız kapsam dışı eski altıncı aggregate inspector'da bulunur; o dosya input olarak okunmaz ve alanlar inherited source kanıtı gibi üretilmez. Yeni inspector aynı adları sadece kendi yerel yetki/kabul sınırları olarak false bildirebilir; original_Phase40_files_read=false ayrıca yeni local sınırdır. Exact18 trust false ve demo_only true korunur.

## İzinli exact iki ürün çağrısı

Aşağıdakiler hazırlanan komutlardır; çalışmış başarı kaydı değildir. Her dispatch önceden kaydedilir. İkinci çağrı yalnız ilk exit0, eksiksiz beş output ve slots/template/receipt/MD/manifest dar manuel inceleme sonrası çalışabilir. En fazla iki çağrı; failure tüketilir. Retry/üçüncü/preflight/helper/import smoke/AST/--help/eski CLI/test yoktur. Eski kapalı faz bütçeleri yeniden açılmaz.

```text
python -I -B security-platform/tools/commercial_response_slots/assemble_response_slots.py --queue outputs/phase40-evidence-followup/evidence-followup-queue.json --handoff outputs/phase40-evidence-followup/analyst-handoff.json --receipt outputs/phase40-evidence-followup/followup-source-receipt.json --source-summary outputs/phase40-evidence-followup/followup-summary.md --source-manifest outputs/phase40-evidence-followup/manifest.json --request security-platform/tools/commercial_response_slots/examples/demo_slot_request.json --output-dir outputs/phase41-response-slots
```

```text
python -I -B security-platform/tools/commercial_response_slots/inspect_response_slots.py --slots outputs/phase41-response-slots/task-response-slots.json --template outputs/phase41-response-slots/response-template.json --receipt outputs/phase41-response-slots/response-slot-source-receipt.json --summary outputs/phase41-response-slots/response-slot-summary.md --manifest outputs/phase41-response-slots/manifest.json --output outputs/phase41-response-slots/inspection-summary.json
```

İlk çağrı yeni boş output dizininde slots/template/receipt/summary/manifest üretir. Manifest gerçek ilk dört payload'ı bağlar; kendi hash'i/inspection kapsam dışıdır. Inspector yalnız beş yeni dosyayı okuyarak closed models, gerçek gösterilen tuple'dan digest, slot/template eşliği, null/unsubmitted/count/full-packet, canonical actual slotsSHA, receipt/Markdown/dört payload manifest ilişkisini inceler. `content_consistent` yeni beş dosyanın iç tutarlılığıdır; özgün source/observation veya task membership/necessity bağımsız doğrulaması değildir.

## Limitler ve açık kabuller

Request32K; source queue/handoff/receipt/MD/manifest256/128/64/128/64K; toplam1MiB. Yeni slots256K/template128K/receipt64K/summary128K/manifest64K; selected task8/ref8/proj64/depth12/node20.000/text512 ve daha sıkı owner limitleri korunur. Strict UTF-8/JSON, duplicate/unknown/schema/type/float/NaN/Infinity/bool-as-int/digest/enum/task/binding ret kuralları kapalıdır. Overwrite/otomatik silme/partial success yoktur. Değişken Markdown inert escaped text'tir; URL/path/HTML/script çalıştırılmaz.

NOT_RUN: hostile/duplicate JSON/UTF-8/BOM, wrong digest/duplicate/unknown task/çelişkili binding/modified queue-handoff, fake/filled response, gerçek response parsing, task atama/kabul/iptal/tamamlama, locator doğrulaması/source reobservation/evidence collection, limit/permission/crash/partial write/repeat determinism/ikinci host; Phase31 guard/source freshness/compiler/module closure/ownership/native/producer/human/legal/customer/release. Future type tanımları intake kabulü değildir. Test/runner/coverage/typecheck/build/install/native/network/live işlemleri yoktur. Phase19 file:// UI kabulü açık kalır; engel server/hosting/browser ile aşılmaz.

Yeni delta standalone binary/production wheel değildir; korunmuş Phase40 owner contract/renderer/manifest ve kapalı import zincirine ihtiyaç duyar. Eski kaynak veri/CLI/native çalışması veya gerçek ikinci host kabulü değildir. Hash imza/attestation değildir; ID/hash hassas olabilir, minimizasyon anonimlik/şifreleme sağlamaz.

Belgeler: [slot sözleşmesi](../../docs/commercial/operations/phase41/RESPONSE_SLOT_CONTRACT.tr.md), [task binding](../../docs/commercial/operations/phase41/TASK_BINDING.tr.md), [intake/disclosure](../../docs/commercial/operations/phase41/INTAKE_AND_DISCLOSURE.tr.md), [teslim](../../docs/commercial/operations/phase41/DEMO_DELIVERY.tr.md).

ZIP `Termivar-Offline-Response-Slots-phase41-2026-11-14.zip` yalnız yeni15 source/belge ve altı gerçek output kapsamındadır; ölçülmemiş üye/boyut/hash iddia edilmez. Dört teslim metadata'sının **tamamı ZIP dışındadır**, source manifest self üyesi yoktur. Ölçülen kimliklerin otoritesi [source manifest](../../../outputs/phase41-response-slots-source-manifest.json), [asset manifest](../../../outputs/phase41-response-slots-asset-manifest.json), [delivery manifest](../../../outputs/phase41-response-slots-delivery-manifest.json) ve [closure](../../../outputs/phase41-response-slots-closure.json) kayıtlarıdır; öz hash döngüsü kurulmaz. Altı review kaydı manifestlere gömülür; ayrı review/private working-state/prompt paketlenmez. 21 eski asset saltokunur eşlenir; new_assets=[] ve asset kopyası yoktur. Phase7–40/backend/native/HBF/Altay/auth/DB/rol/credential/wheel/lock/lisans korunur. İki izinli çağrı ve ölçülmüş teslim kapanınca durulur; Phase42/yeni mikro özellik/üçüncü çağrı/test/native/release başlatılmaz.
