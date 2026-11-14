# Phase41 — Deterministik task binding

**OFFLINE DEMONSTRATION — TASK-BOUND RESPONSE SLOTS ONLY — NO RESPONSE OR OBSERVATION RECEIVED**

`binding_digest`, gelecekteki yanıtı belirli bir source queue ve gerçek task kimliği/bağıyla eşleştirmek için kullanılan deterministik metadata anahtarıdır. Secret/token, imza, producer authentication, anti-replay veya authorization değildir.

## Exact preimage

Saf `derive_task_binding(source_queue_sha256,task_record)` exact original sekiz alanlı task kaydını doğrular; yalnız recorded missing/request_fresh_source_observation/prepared_unassigned/not_observed kabul edilir. Digest girdisi exact beş anahtarlı JSON nesnesidir:

```text
source_phase40_queue_sha256
task_id
reference_id
candidate_id
file_id
```

Yeni schema alanı veya liste sıra indeksi preimage'a eklenmez. Gerçek current Phase40 queue SHA256 kullanılır; parent39 witnesses/manifest hash'i veya yeni slot dosya hash'i değildir. Owner canonical JSON encoding sorted keys, indent2, UTF-8 ve LF ile bytes üretir; bunların SHA256'ı digest'tir. Aynı gerçek task ve queue kimliği liste sırasından bağımsız aynı girdiye sahiptir. Kaynak queue byte'ı değişirse kimliği de değişebilir; bu yeni source gözlemi veya güvenilir üretici kanıtı sağlamaz.

Source-bound builder exact source task ID/durum/tuple üyeliğini gerçek doğrulanmış Phase40 queue'dan alır. Original F kimliği korunur; seçilen reference packet üzerinden eski follow-up task üreticisini tekrar çalıştırıp F0001 ile başlatılmaz. Gerçek source görevleri altkümeye göre yeniden numaralandırılmaz. Duplicate/çelişkili binding reddedilir. Yeni wire-only reader bu açık tuple/digest/full packet ilişkisini doğrular; özgün queue üyeliği veya task gerekliliğini bağımsız kanıtlamaz.

## İki farklı hash bağı

| Kimlik | Neyi bağlar | Yetki sınırı |
| --- | --- | --- |
| source_phase40_queue_sha256 | Gerçek source queue byte'ı | Güncellik/producer doğrulaması değildir |
| source_phase40_manifest_sha256 | Gerçek source manifest byte'ı | Eski parent hash'i değildir |
| binding_digest | Queue kimliği + gerçek task/reference/candidate/file tuple | İmza/token/anti-replay değildir |
| template.slots_sha256 | Canonical yeni slots JSON'unun gerçek byte'ı | Yanıt alındığı veya görevin atandığı anlamına gelmez |

Yeni manifest ilk dört payload gerçek byte/hash'ini tutar; kendi hash'i ve inspection sonucu kapsam dışıdır. Inspector canonical slots hash'inin actual dosyaya eşliğini ve her slot/template digest bağını inceleyebilir. Phase40 source dosyalarını yeniden açmaz. Tutarlı dosyalar birlikte değiştirilip yeniden hash'lenebilir; hash eşliği source truth, tamlık, imza veya Git attestation değildir.

## Yanıt ve insan sınırı

Slot awaiting_external_response/submission=null, template unsubmitted/response=null kalır. Digest varlığı observation_recorded_at veya locator değeri üretmez. Gerçek yanıt parser'ı, anti-replay deposu/nonce, credential, reviewer kimliği, atama/iptal/tamamlama işlemi yoktur. Future response alanları sadece tür tanımıdır; yetkili locator daha sonra uygun insan süreciyle sağlanmalıdır.

Task count'ları kaynak inventory sayımı değildir; source queue/handoff yedileri aynen nested korunur. Yeni submitted/assigned/observed sayımları integer0; null response/gözlem ile karıştırılmaz. Exact18 trust flag false kalır. Kaynakta bulunmayan workflow_flags/17 alan uydurulmaz; yeni inspector'ın yerel flat false sınırları kaynak inheritance değildir.

NOT_RUN: repeat determinism/çelişkili task binding/unknown-duplicate task/wrong digest/modified queue-handoff/hostile JSON, filled external response veya gerçek parser, locator doğrulaması, analist atama/kabul/iptal/tamamlama, source reobservation/evidence collection, ikinci host, guard/source freshness/compiler/module closure/ownership/native/producer/human/legal/customer/release. Canonical algoritmanın kaynakta bulunması bu runtime kabullerinin çalıştığı anlamına gelmez. [Sözleşme](RESPONSE_SLOT_CONTRACT.tr.md), [intake](INTAKE_AND_DISCLOSURE.tr.md), [teslim](DEMO_DELIVERY.tr.md).
