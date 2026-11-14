# Phase43 görev alışverişi sözleşmeleri

**OFFLINE DEMONSTRATION — PORTABLE TASK REQUEST ONLY — NO TASK DISPATCH OR RESPONSE AUTHORIZED**

Bu v1 araç, Phase42'nin gerçek register/classification/receipt/Markdown/manifest beşlisinden yalnız seçilmiş yanıtsız görevleri dışa aktarır. `ValidatedPhase42Source` exact beş immutable byte taşır; fiziksel okumadan sonra payload manifesti, owner validator'ları, classification türetimi ve qualified Markdown/full manifest eşliği gerekir. `read_source()` yeniden doğrulamayı bellekte yapar. Aggregate inspection raporu kaynak modeli değildir. Eski Phase41/40 dosyası veya eski CLI kullanılmaz.

## Kapalı request ve envelope

`termivar-offline-task-exchange-request/v1` exact altı alanlıdır:

| Alan | Sınır |
| --- | --- |
| schema_version | Exact v1 literal |
| mode | demo |
| request_reference | Bounded yerel kimlik |
| source_phase42_register_sha256 | Güncel gerçek register'ın lowercase SHA256 değeri |
| source_phase42_manifest_sha256 | Güncel gerçek manifest'in lowercase SHA256 değeri |
| selected_task_ids | 1–8 unique, kaynakta mevcut F0001…F0064 |

Yanlış digest, duplicate/unknown task veya tek bir uygun olmayan seçim bütün request'i reddeder. Seçilen kayıt candidate_present=false, candidate_response=null ve unsubmitted olmalıdır; classification observation_verified=false/task_completed=false bağını korur. Yeni task numarası, source locator, observation, filepath, analyst identity veya authorization alanı yoktur.

`termivar-offline-portable-task-request/v1` exact on üst alan taşır: schema_version, demo_label, demo_only, trust_flags, source_phase42_register_sha256, source_phase42_manifest_sha256, request_reference, tasks, counts, limitations. Her görev exact on alanlıdır:

| Alan | Kaynak bağı veya sabit durum |
| --- | --- |
| task_id | Kaynaktaki original global F kimliği |
| reference_id | Seçilmiş görevin rust-ref- SHA256 kimliği |
| candidate_id | Seçilmiş görevin bounded candidate kimliği |
| file_id | Seçilmiş görevin candidate-file- SHA256 kimliği |
| binding_digest | Inherited lowercase SHA256; kaynaktan eşit kopya |
| slot_status | awaiting_external_response |
| response_status | unsubmitted |
| candidate_present | false |
| observation_verified | false |
| task_completed | false |

Task ID/digest/reference-candidate-file tuple tekildir ve original sıralı task kimlikleri korunur. Envelope içinde reference_packets, projections, observed_byte_size/observed_sha256, candidate_response, source locator veya başka açık uçlu alan yoktur. Closed model yalnız doğrulanmış alanları kopyalar.

## Gelecekteki yanıtın alan tanımları

`termivar-offline-portable-response-contract/v1` common dört alan ile field_definitions ve limitations taşır. Tanımlar bütün paket için tek ortak sözleşmedir:

| Alan | Gerçek owner tür tanımı |
| --- | --- |
| task_id | string |
| binding_digest | sha256 |
| reported_presence | present_or_missing |
| observation_recorded_at | timestamp_string |
| observation_method | string |
| source_locator_description | string |
| evidence_sha256_if_available | sha256_or_null |

Producer, yeni dar v1 literalini mevcut owner `slot_contracts.submission_contract()` sonucu ile karşılaştırır. Recipient eski owner import etmeden bu exact v1 tanımını okur. Tanımlar doldurulmuş response veya evidence toplama talimatı değildir. Yeni timestamp grammar/timezone/freshness, locator semantics, authorization veya anti-replay iddiası yoktur. Eski `decode_candidate_response` exact Phase41 `ValidatedResponseSlots` ister; Phase42 snapshot veya sahte eski snapshot verilmez ve Phase43 onu dolu nesne ya da None ile çalıştırmaz.

## Index, receipt ve sayaçların paydası

`termivar-offline-task-exchange-index/v1`, common dört alan, source_phase42_register_sha256, source_phase42_manifest_sha256, capsule_sha256, task_ids, counts, limitations taşır. capsule_sha256 gerçek portable ZIP byte'ına aittir; source manifest SHA256 yerine kullanılamaz.

Yeni exact altı sayaç selected_task_count, unsubmitted_request_count, response_field_definition_count, submitted_response_count, verified_observation_count, completed_task_count'tır. İlk ikisi seçilmiş görevlerden türetilir. Ortak definition count7'dir; 7×task sayısı değildir. Son üç değer integer0'dır; false veya null değildir.

`termivar-offline-task-exchange-source-receipt/v1`, common dört alan ile source_artifacts, iki güncel Phase42 SHA256, source_schema_versions, source_counts, content_scope ve limitations taşır. Beş descriptor gerçek byte/SHA256/şema kimliğidir; Markdown şeması null'dır. content_scope `five_Phase42_artifact_internal_correspondence_only` olur. Kaynak gövdeleri veya reference packet receipt'e kopyalanmaz. Altı kaynak sayım kapsamı exact iç içe korunur:

```text
source_counts
  register_counts                 Phase42 exact8
  classification_counts           Phase42 exact8
  phase41_counts
    slots_counts                  parent Phase41 exact7
    template_counts               parent Phase41 exact7
    phase40_counts
      queue_counts                parent Phase40 exact7
      handoff_counts              parent Phase40 exact7
```

Bu paydalar flatten/toplama yoluyla birleştirilmez. Parent distinct file/candidate2 kapsamı, tek task export edildiği için1 yapılmaz. `validate_relationships(envelope,index,receipt)` üç kapalı kopya döndürür; source SHA/IDs/count/subset ilişkilerini inceler. Gerçek capsule byte/hash bağı ayrıca manifest/inspector tarafından kurulur.

## Kimlik ve trust sınırı

Güncel register6465bab021f525b47d4fafd5a0ddc68020989b60e82bce3ec70f6bfaa4f8ff16 ile manifestfbe94605564f06a11165cc9fb71229100b609e2c7d0248e4772af53ddb81b6cc, ebeveyn Phase41 slots291caf…/manifest0d67de… kimliklerinden ayrıdır. binding_digest221a67c41a4c3492ac4983e0a5af337aa5c42508a2391226f7ed0e84d7197bae güncel register/manifest veya eski slots hash'iyle yeniden türetilmez. Orijinal Phase40 preimage'ı mevcut değildir; source-bound eşlik original binding kriptografisini, task membership/necessity veya ownership'i bağımsız kanıtlamaz.

Common alanlar exact schema_version/demo_label/demo_only=true/trust_flags'tır. Kaynağın exact18 nested trust flag'i false korunur; bulunmayan17 workflow alanı miras alınmaz. Inspector'ın yerel false işlem alanları ayrı kapsamdır. Yapısal request geçerliliği source observation, producer authentication, recipient authorization, dispatch veya response acceptance değildir. Tutarlı içerik yeniden hash'lenebilir.

## Dar sınırlar

Request32KiB; kaynak register/classification/receipt/Markdown/manifest256/128/64/128/64KiB; fiziksel input toplam1MiB. Capsule raw/uncompressed128KiB; index128KiB; receipt64KiB; summary128KiB; manifest64KiB. JSON string512 karakter/depth12/nodes20000; task8. Strict UTF-8/BOM ret, duplicate key, unknown schema/field, float/NaN/Infinity, bool-as-int, invalid digest/enum ve duplicate task fail-closed'dur. Canonical JSON ensure_ascii=False/sorted keys/indent2/LF kullanır. Markdown değişkenleri inert escape edilir ve tüm sözlük dolaşımları explicit/sorted sıradadır. Kodun bu retleri içermesi hostile testlerin çalıştırıldığını göstermez.

Kullanım ve gerçek çağrı durumu [README](../../../../tools/commercial_task_exchange/README.md) ve [DEMO_DELIVERY](DEMO_DELIVERY.tr.md) içinde; recipient yapısal sınırı [RECIPIENT_VALIDATION](RECIPIENT_VALIDATION.tr.md) belgesindedir.
