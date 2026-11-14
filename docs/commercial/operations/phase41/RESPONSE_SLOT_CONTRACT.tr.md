# Phase41 — Task-bound response slot sözleşmeleri

**OFFLINE DEMONSTRATION — TASK-BOUND RESPONSE SLOTS ONLY — NO RESPONSE OR OBSERVATION RECEIVED**

Ürün, mevcut pending görevden gelecekte yanıt verilebilecek kapalı bir intake yuvası üretir. Gerçek response almaz ve yeni observation kabul etmez. response_slot_created observation_received değildir.

## Şemalar ve kaynak

| Artefact | Schema |
| --- | --- |
| Request | termivar-offline-response-slot-request/v1 |
| Slots | termivar-offline-task-response-slots/v1 |
| Template | termivar-offline-task-response-template/v1 |
| Receipt | termivar-offline-response-slot-source-receipt/v1 |
| Manifest | termivar-offline-response-slot-manifest/v1 |
| Inspection | termivar-offline-response-slot-inspection/v1 |

Common4: schema_version, exact demo_label, demo_only=true, exact18 nested false trust_flags. Beş gerçek Phase40 input modelinde workflow_flags/17 workflow alanı bulunmaz; koşullu owner kuralı gereği yeni modellerde üretilmez. Eski altıncı aggregate inspector local alanları kaynak mirası sayılmaz.

Request exact6 schema/mode demo/request_reference/current Phase40 queue ve manifest SHA256/selected_task_ids'tir. 1–8 benzersiz gerçek task ID, prepared_unassigned/not_observed seçilir. Wrong digest/unknown/duplicate/state uyuşmazlığı all-or-nothing reddedilir. Path/observation/analyst/authorization/risk alanı yoktur.

`ValidatedPhase40Source` exact beş immutable bytes tuple; frozen/slots/repr-hidden ve memory-only revalidation'dır. Load bounded/stable fiziksel beşli okur. Gerçek dört payload manifest kimliği önce; owner üç model/relationships, qualified Markdown/full dört argümanlı manifest eşliği sonra doğrulanır. Reader `(queue,handoff,receipt,source_artifacts)` kopyalarını döndürür. Phase39 snapshot, queue-only wire ve aggregate rapor full source reader değildir; aynı owner class iki import kimliğine ayrılmaz. Eski CLI/Phase39/CSV/kapsül/guard/native input açılmaz.

## Exact slots modeli

Slots common4 + source_phase40_queue_sha256 + source_phase40_manifest_sha256 + request + reference_packets + response_slots + counts + limitations'dır. Reference packets yalnız selected task-associated referansların bütün eski beş alanını ve bütün11 projection listesini source sıra/tür/null ile taşır. CAND0001 present paket içinde korunabilir; ona yeni task/slot üretilmez.

Her slot exact11 alan: task_id, reference_id, candidate_id, file_id, binding_digest, followup_kind, task_status, fulfillment_status, slot_status, submission, submission_contract. Sabit durumlar request_fresh_source_observation/prepared_unassigned/not_observed/awaiting_external_response ve submission=null'dır. Gerçek source task ID korunur; altküme üzerinden eski missing task türeticisiyle yeniden numaralandırılmaz. Slot'un supported missing tuple/full packet bağı gerekir. Wire doğrulaması original source üyeliğini bağımsız kanıtlamaz.

submission_contract exact yedi field-name→type-description sözlüğüdür: task_id:string; binding_digest:sha256; reported_presence:present_or_missing; observation_recorded_at:timestamp_string; observation_method:string; source_locator_description:string; evidence_sha256_if_available:sha256_or_null. Bunlar future alan türleridir, sahte observation değerleri değildir. Locator eski metadata'dan uydurulmaz; yetkili kişi ileride sağlamalıdır. Bu turda response ingestion parser yoktur.

## Template ve receipt

Template common4 + current Phase40 SHA2 + slots_sha256 + request_reference + template_entries + counts + limitations'dır. Her entry task_id/binding_digest/required_fields/response_status/response taşır; required_fields slot submission_contract ile exact eşit, status unsubmitted, response=null'dır. slots_sha256 canonical ilk JSON'un gerçek byte hash'idir. Filled response, submitted/observed/assigned/accepted/completed durumları oluşturulmaz.

Receipt common4 + source_artifacts + current SHA2 + source_counts + selected_task_count + content_scope + limitations'dır. Beş descriptor exact name/bytes/sha256/schema_version; Markdown schema null. Source counts exact nested `{queue_counts: original7, handoff_counts: original7}` yapısıdır. Tek task yüzünden distinct_file_count2 bire inmez. Content scope five_Phase40_artifact_internal_correspondence_only'dir. Current queue/manifest hash'leri parent39 witnesses/manifest pinleriyle karıştırılmaz.

Slots ve template exact7 sayımı: selected_task_count, selected_reference_count, response_slot_count, unsubmitted_slot_count, submitted_response_count, assigned_task_count, observed_task_count. Son üçü integer0; null response/boş dosya veya sıfır-byte gözlem değildir. Completed count/state üretilmez.

## Saf API ve limit

build_response_slots(source,request)→immutable snapshot; read_response_slots(snapshot)→closed copy; build_response_template(snapshot)→closed template; make_source_receipt(source,snapshot)→closed receipt. validate_slots/template/receipt ve validate_relationships üç kopyayı döndürür. Binding algoritması [TASK_BINDING](TASK_BINDING.tr.md) belgesindedir.

Request32K/source256-128-64-128-64K/total1MiB; output slots256K/template128K/receipt64K/MD128K/manifest64K. Task8/ref8/proj64/depth12/nodes20.000/text512 ve daha sıkı owner limitleri korunur. Strict UTF-8/JSON; duplicate/unknown/schema/type/float/NaN/Infinity/bool-as-int/digest/task/binding/enum ret. Yeni genel parser/DB/API/GUI/servis/dependency yoktur. Overwrite veya otomatik silme yoktur. Bu korumaların hostile/runtime kabulü ayrıca yapılmış sayılmaz.

Yeni inspector yalnız beş yeni output'un canonical actual slots hash/full models/task-binding/template/null/full packet/count/receipt/MD/manifest iç eşliğini inceler; Phase40 dosyalarına dönmez. content_consistent kaynak observation veya producer/assignment/insan kabulü değildir. [Intake/trust](INTAKE_AND_DISCLOSURE.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).
