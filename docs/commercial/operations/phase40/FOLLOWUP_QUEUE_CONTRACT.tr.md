# Phase40 — Follow-up queue sözleşmesi

**OFFLINE DEMONSTRATION — RECORDED MISSING EVIDENCE FOLLOW-UP ONLY — NO OBSERVATION OR ASSIGNMENT AUTHORIZED**

Ürün, mevcut Phase39 witness metadata'sında kayıtlı missing gözlemi gerçek supporting bağa sahip bir takip talebine dönüştürür. Dosya aramaz, yeniden okumaz veya toplamaz. `recorded_missing_source ≠ current_physical_file_missing`.

## Sürümler ve kapalı alanlar

| Artefact | Schema |
| --- | --- |
| Request | `termivar-offline-evidence-followup-request/v1` |
| Queue | `termivar-offline-evidence-followup-queue/v1` |
| Handoff | `termivar-offline-evidence-analyst-handoff/v1` |
| Receipt | `termivar-offline-evidence-followup-source-receipt/v1` |
| Manifest | `termivar-offline-evidence-followup-manifest/v1` |
| Inspection | `termivar-offline-evidence-followup-inspection/v1` |

Yeni modellerin common alanları `schema_version`, exact `demo_label`, `demo_only=true`, exact 18 nested false alanlı `trust_flags` nesnesidir. Unknown schema/field/type kabul edilmez; bunlar yetki veya runtime kabulü sürümleri değildir.

Request exact altı alan: schema, mode demo, request_reference, source_phase39_witnesses_sha256, source_phase39_manifest_sha256, requested_reference_ids. 1–8 benzersiz ID gerçek source WITNESSES results kümesinde bulunur. Unknown/duplicate/digest uyuşmazlığı bütün isteği reddeder. Path/candidate/observation/insan/assignment/authorization alanı yoktur.

Queue common + current iki digest + request + reference_packets + followup_tasks + counts + limitations'dır. Her reference packet eski witness result'ın exact beş alanıdır: reference_id, disclosure_status, matched_file_ids, supporting_projection_bindings, projections. Canonical reference sırası, matched file kaynak sırası ve bütün 11-alan projection listesi korunur. Full paket yalnız missing projection'lara daraltılmaz; bloke veya eşleşmeyen source katalog kopyalanmaz.

Task exact sekiz alanı: task_id, reference_id, candidate_id, file_id, recorded_source_file_presence, followup_kind, task_status, fulfillment_status. Son dört değer sırasıyla `missing`, `request_fresh_source_observation`, `prepared_unassigned`, `not_observed` olarak sabittir. `(reference,candidate,file)` sırasındaki F0001…F0064 yerel deterministik sıra etiketidir. Talep ataması, onayı veya fulfilment değildir.

## Missing ve binding invariant'ları

Her selected missing projection'ın aynı referans/candidate/file supporting triple'ı bulunur. Kaynakta olmayan veya required supporting kümesinde bulunmayan missing için yeni bağ uydurulmaz; bütün request fail-closed reddedilir. Aynı triple iki task oluşturmaz. Aynı File ID'nin ayrı gerçek reference bağlamı korunur. Ayrı geçerli candidate bağları kaybolmaz; duplicate/çelişkili/ambiguous eşleme sessiz seçilmez. Present projection takip işi üretmez. Null byte/hash, null olarak kalır; integer0/boş string/sahte digest değildir.

Saf API `build_followup_queue(validated_source,request)` immutable `ValidatedFollowupQueue` döndürür; `read_followup_queue` exact snapshot'tan yeniden doğrulanmış kapalı kopya sağlar. Yeni queue wire doğrulaması, özgün source'un bağımsız doğrulandığı anlamına gelmez. Owner source-bound adapter olmadan caller trusted etiketi yetki sağlamaz.

## Üç sayım paydası

Queue ve handoff exact yedi alanı: selected_reference_count, selected_projection_count, recorded_present_projection_count, recorded_missing_projection_count, pending_task_count, distinct_file_count, distinct_candidate_count. Pending gerçek benzersiz task bağlarından; diğer sayımlar ve distinct file/candidate kendi seçili bütün projection paketlerinden türetilir. Yalnız missing task'lardaki distinct sayılmaz. Global envanter değildir.

Handoff aynı queue işlerini taşır; reference_packets yalnız işi olan referansların bütün paketleridir. Kendi yedi sayımı yeniden türetilir; işi olmayan referanslar handoff'a geçirilmez. Hiç task yoksa handoff packet/task listeleri ve sayımları sıfırdır. Queue'nun canonical JSON bytes SHA256'ı handoff.queue_sha256 ile bağlanır; hash üretici imzası değildir.

Receipt source_counts, gerçek Phase39 **QUERY.counts** altı alanıdır: required_file_count, matched_reference_count, matched_projection_count, matched_candidate_count, matched_present_projection_count, matched_absence_projection_count. Eski receipt inherited visible6, pair10/global9 sayımları değildir. Full packet unrequired dosya taşıyabilir; selected distinct files source required_file_count ile sınırlandırılmaz. Receipt common + beş source_artifacts + current iki digest + source_schema_versions + source_counts + content_scope + limitations'dır; kapsam `five_Phase39_artifact_internal_correspondence_only`.

## Immutable input ve kapalı doğrulama

`ValidatedPhase39Source` exact beş bytes tuple, frozen/slots/repr-hidden'dır. Yalnız load_source beş fiziksel input'u stabil/bounded okur. Constructor ve read_source memory-only gerçek dört payload/manifest kimliği, old owner üç model/çapraz ilişki/query_from_witnesses, qualified Markdown ve dört argümanlı manifest eşliğini doğrular. Aggregate inspector tam source reader değildir; Phase38 snapshot sınıfı yeniden kullanılmaz. Aynı owner sınıfı flat/qualified iki sınıf kimliğine ayrılmaz.

Request32K; source query/witness/receipt/MD/manifest128/256/64/128/64K; toplam1MiB. Yeni queue256K/handoff128K/receipt64K/summary128K/manifest64K; refs8/projections64/tasks64/depth12/nodes20.000/text512 ve daha sıkı owner sınırları korunur. Strict UTF-8/JSON, duplicate/unknown field/schema, float/NaN/Infinity/bool-as-int/digest/type/binding ret; overwrite/silme veya kısmi başarı yoktur. Bu korumaların hostile/runtime kabulü ayrıca yapılmış sayılmaz.

[Handoff](ANALYST_HANDOFF.tr.md), [trust](DISCLOSURE_AND_TRUST.tr.md), [gerçek teslim kaydı](DEMO_DELIVERY.tr.md).
