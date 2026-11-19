# Phase44 mutabakat sözleşmesi ve veri modeli

**OFFLINE DEMONSTRATION — UNTRUSTED CAPSULE RECONCILIATION ONLY — NO TASK DISPATCH, ASSIGNMENT, APPROVAL, EXECUTION OR SUBMISSION**

Phase44, Phase43'ün dışa aktardığı bir portable capsule'ı yerel ve **güvenilmeyen** bir inbox kaydına alır. Ardından deterministik bir mutabakat raporu üretir. Bu belgede yeni v1 modellerin gerçek alanları anlatılıyor. Phase43 sözleşmesinin kuralları Phase43 owner modüllerinde (`exchange_contracts.py`, `portable_capsule.py`, `recipient_reader.py`) kalır. Phase44 bu kuralların ikinci bir kopyasını tanımlamaz.

## Sürümlü şemalar

| Model | Şema | Dosya |
| --- | --- | --- |
| Mutabakat isteği | `termivar-offline-task-capsule-reconciliation-request/v1` | `examples/demo_reconciliation_request.json` |
| Mutabakat raporu | `termivar-offline-task-capsule-reconciliation-report/v1` | `capsule-reconciliation-report.json` |
| Güvenilmeyen inbox kaydı | `termivar-offline-untrusted-task-inbox-record/v1` | `task-inbox-record.json` |
| Çıktı manifesti | `termivar-offline-task-capsule-reconciliation-manifest/v1` | `manifest.json` |
| Bağımsız inceleme | `termivar-offline-task-capsule-reconciliation-inspection/v1` | `inspection-summary.json` |

Rapor, inbox, manifest ve inceleme modellerinin tamamı kapalıdır; bilinmeyen alan reddedilir. Hepsi şu ortak alanları taşır: `schema_version`, `demo_label`, `demo_only=true`, `trust_state=UNTRUSTED_IMPORT_NOT_AUTHENTICATED`, 14 alanlı `non_claims` ve sabit `limitations` listesi. `non_claims` içindeki her değer `false`'tur. Bu alanlar: producer_authenticated, cryptographic_trust_established, secure_transport_verified, source_provenance_verified, real_world_observation_verified, task_dispatched, task_assigned, task_approved, task_accepted, task_executed, task_completed, response_submitted, external_submission_performed, production_acceptance. JSON, Phase43 owner `json_bytes` ile canonical yazılır: UTF-8, LF, sıralı anahtar, indent2.

## İstek

İstek tam altı alanlıdır: `schema_version`, `mode` (yalnız `demo`), `request_reference`, `local_reference_mode`, `expected_local_phase42_register_sha256`, `expected_local_phase43_index_sha256`.

`local_reference_mode` şu değerlerden birini alır:

- `NO_LOCAL_RECORDS`
- `PHASE42_TASK_RECORDS_ONLY`
- `PHASE43_DISCLOSURE_RECORDS_ONLY`
- `PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS`

Kullanılan yerel grubun pini SHA256 olmak zorundadır; kullanılmayan grubun pini `null` olmalıdır. Pin, gerçek yerel dosyanın hash'iyle eşleşmezse girdi reddedilir ve hiçbir şey yayımlanmaz. İstek capsule'ın hash'ini pinlemez: içe alınan capsule incelenen nesnedir, güvenilen bir girdi değildir.

## Ayrı tutulan bilgi türleri

| Tür | Raporda nerede | Anlamı |
| --- | --- | --- |
| Doğrulanmış yapısal olgular | `archive`, `members`, `required_members`, `member_contents`, `manifest_correspondence`, `phase43_reader` | Byte, ZIP üye metadata'sı ve owner reader kararı. Güven değildir. |
| Capsule'ın beyan ettiği olgular | `envelope_fields`, `tasks`, `task_declaration`, `capsule_identity.declared_*` | Capsule'ın söyledikleri. String değerler yalnız owner validator'dan geçtiyse yazılır. Değer açıklama kuralı aşağıdadır. |
| Temsil edilen kimlik | `capsule_identity.represented_*` | Yalnız Phase43 owner reader kabul ettiğinde `ESTABLISHED_BY_PHASE43_OWNER_READER`, aksi halde `NOT_ESTABLISHED`. |
| Yerel olarak mutabakatı yapılmış olgular | `local_reconciliation` | Phase42 görev kayıtları ve Phase43 açıklama kayıtlarıyla alan bazında karşılaştırma. |
| Uyuşmazlıklar | `MISMATCH` satırları ve `IDENTITY_MISMATCH` / `DISCLOSURE_MISMATCH` / `AMBIGUOUS_BINDING_OWNER` bulguları | Capsule değeri yerel kayıttan farklı. |
| Erişilemeyen bilgi | `UNAVAILABLE` / `NOT_COMPARABLE` satırları, `LOCAL_*` bulguları | Yerel kayıt verilmedi, bulunamadı veya capsule yapısal olarak reddedildi. |
| Manuel inceleme gereksinimi | `eligibility.manual_review_requirement=REQUIRED` | Her durumda zorunludur. |

## Alan durumu: eksik, null, boş, false ve 0 birleştirilmez

Her alan kaydı şunları taşır: `path`, `presence` (`PRESENT`/`ABSENT`/`NOT_EVALUATED`), `value_kind` (`STRING`, `INTEGER`, `BOOLEAN`, `NULL`, `ARRAY`, `OBJECT`, `ABSENT`, `NOT_EVALUATED`), `state`, `value_disclosure`, `value`, `string_length`, `string_sha256`, `item_count`, `owner_rule_code`.

`state` şu değerlerden birini alır:

- `VALID`: owner validator kabul etti.
- `INVALID`: owner validator reddetti; kural kodu `owner_rule_code` alanına yazılır.
- `NULL`
- `EMPTY_STRING`
- `EMPTY_ARRAY`
- `EMPTY_OBJECT`
- `ABSENT`
- `NOT_EVALUATED`: değerlendirme bağımlı bir alana bağlı. Örneğin `counts`, ancak `tasks` owner tarafından geçerli bulunduğunda değerlendirilir.

Örnekler:

- Eksik alan: `presence=ABSENT, state=ABSENT`.
- `null`: `state=NULL, value_kind=NULL`.
- `""`: `EMPTY_STRING`.
- `[]`: `EMPTY_ARRAY`.
- `0` bir boolean alanında: `INVALID, value_kind=INTEGER, value=0`.
- `false` aynı alanda: `VALID, value_kind=BOOLEAN, value=false`.

`field_presence_summary` alan yollarını gruplar: `present_valid`, `absent`, `null`, `empty_string`, `empty_array`, `empty_object`, `invalid`, `not_evaluated`, `unexpected`. Phase43'te hiçbir alan null veya boş olamadığı için `NULL` ve `EMPTY_*` durumları da sözleşme ihlalidir. Yine de ayrı raporlanırlar.

Değer açıklama kuralı:

- Boolean, integer ve null değerler, alan `INVALID` olsa bile `ECHOED` olarak yazılır. Bu türler serbest metin taşımaz; integer'lar owner parser sınırıyla (2^53−1) sınırlıdır. Owner-geçerli string'ler ve boş string de yazılır.
- Geçersiz string yazılmaz (`WITHHELD_INVALID_STRING`); yalnız uzunluğu ve SHA256'sı kaydedilir. Desteklenmeyen bir `schema_version` string'i de bu kurala uyar: `declared_schema` yalnız desteklenen şemada dolu, aksi halde `null` olur.
- `task_declaration.declared_task_count`, `counts.selected_task_count` bir integer ise beyan edildiği gibi yazılır.
- Liste ve nesneler yazılmaz (`WITHHELD_COMPOSITE`); yalnız öğe sayısı kaydedilir.
- Bilinmeyen alanların değeri hiçbir zaman yazılmaz. Adları yalnız `[a-z][a-z0-9_]{0,63}` kalıbına uyuyorsa (en fazla 16 ad) listelenir. Diğerleri yalnız sayılır.

## Karşılaştırma satırları

Her satır şunları taşır: `subject`, `field`, `reference_source` (`PHASE42_LOCAL_TASK_RECORD` / `PHASE43_LOCAL_DISCLOSURE_RECORD`), `capsule_value`, `capsule_value_state`, `local_value`, `local_value_disclosure` (`ECHOED` / `WITHHELD_NOT_PREVIOUSLY_DISCLOSED` / `NOT_AVAILABLE`) ve `result`.

| Sonuç | Anlamı |
| --- | --- |
| `MATCH` | Capsule değeri owner-geçerli ve tip dahil yerel değere eşit. |
| `MISMATCH` | Capsule değeri owner-geçerli ama yerel değerden farklı. |
| `UNAVAILABLE` | Yerel kayıt grubu verilmedi veya görev ya da binding yerel kayıtta yok. |
| `NOT_COMPARABLE` | Capsule yapısal olarak reddedildi; yerel kayıtlara hiç bakılmadı. |

Phase42 satırları şunları karşılaştırır:

- Capsule düzeyinde: `source_phase42_register_sha256` ve `source_phase42_manifest_sha256`.
- Görev düzeyinde: Phase43'ün on görev alanı, `binding_tuple` (reference/candidate/file/binding), `binding_digest_owner_task` ve `binding_triple_owner_task`. Son iki alan ters aramadır: binding başka bir yerel göreve aitse sonuç `MISMATCH` olur ve `AMBIGUOUS_BINDING_OWNER` bulgusu üretilir.

Phase43 satırları şunları karşılaştırır:

- Capsule düzeyinde: capsule SHA256, dört iç üyenin SHA256 değerleri, iki kaynak digest'i, `request_reference` ve `task_id_list`.
- Görev düzeyinde: on görev alanı ve `binding_tuple`.

## Uygunluk (eligibility)

Öncelik sırası:

1. Phase43 owner reader capsule'ı reddettiyse ya da yapısal kategoride `BLOCKING` bir bulgu varsa: `STRUCTURAL_REJECTION`.
2. Herhangi bir satır `MISMATCH` ise: `IDENTITY_MISMATCH`.
3. Herhangi bir satır `UNAVAILABLE` veya `NOT_COMPARABLE` ise: `LOCAL_RECONCILIATION_UNAVAILABLE`.
4. Diğer durumlarda: `STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW`.

Yapısal kategoriler: INPUT_SIZE, ARCHIVE_STRUCTURE, MEMBER_NAME, MEMBER_METADATA, MEMBER_CONTENT, SCHEMA, MANIFEST_CORRESPONDENCE, FIELD_STRUCTURE, TASK_DECLARATION, OWNER_READER.

`manual_review` yalnız 4. durumda `ELIGIBLE_FOR_MANUAL_REVIEW` olur, diğer durumlarda `NOT_ELIGIBLE`'dır. `manual_review_requirement` her zaman `REQUIRED`'dır. `basis_finding_ids` kararı doğuran bulguları listeler. Güvenilir, onaylı, atanmış, kabul edilmiş, yürütülmüş, tamamlanmış veya production-ready anlamına gelen bir durum yoktur.

Inbox yaşam döngüsü uygunluk durumuna bire bir eşlenir:

| Uygunluk | Inbox aşaması |
| --- | --- |
| `STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW` | `QUARANTINED_AWAITING_MANUAL_REVIEW` |
| `IDENTITY_MISMATCH` | `QUARANTINED_HELD_IDENTITY_MISMATCH` |
| `LOCAL_RECONCILIATION_UNAVAILABLE` | `QUARANTINED_HELD_LOCAL_RECONCILIATION_UNAVAILABLE` |
| `STRUCTURAL_REJECTION` | `REJECTED_NOT_ADMITTED` |

Reddedilen capsule'ın görevleri inbox'a alınmaz (`admitted_tasks=[]`). Diğer durumlarda görevler `fact_origin=CAPSULE_DECLARED_STRUCTURALLY_VALID_NOT_AUTHENTICATED` ve görev başına mutabakat özetiyle karantinada tutulur.

## Bulgular

Her bulgu şunları taşır: `finding_id`, `rule`, `category`, `severity` (`BLOCKING`/`WARNING`/`INFORMATIONAL`), `subject`, `observed_condition`, `expected_condition` ve `remediation`.

Kimlik formatı `P44-<RULE>:<subject>` şeklindedir. Subject kontrollü bir sözlükten gelir:

- `capsule`, `phase42`, `phase43`
- beklenen üye adı, `member#<konum>`, `unlisted_members`
- `<üye>:<alan yolu>` (örneğin `task-request.json:tasks[0].candidate_id`)
- `task:<id>:<phase42|phase43>` ve `task:<id>.<alan>:<phase42|phase43>` Bir raporda en fazla 400 bulgu bulunur; aşılırsa `FINDINGS_TRUNCATED` eklenir. Bu yüzden aynı girdi için kimlik sabittir. Bulgular önem derecesine, sonra kimliğe göre sıralanır. Katalog `reconciliation_findings.py` dosyasındadır. İyileştirme metinleri bir işlemin yapıldığını söylemez, yalnız ne yapılabileceğini önerir. `MANUAL_REVIEW_REQUIRED` bilgilendirme bulgusu her raporda bulunur.
