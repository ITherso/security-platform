# Phase42 — Task binding ve yapısal classification

**OFFLINE DEMONSTRATION — DEFERRED RESPONSE INTAKE ONLY — NO CANDIDATE RESPONSE RECEIVED**

Gerçek demo yanıtsız source template'i tüketir: candidate_present=false/candidate_response=null/no_candidate_supplied. Classification awaiting_submission/not_evaluated_no_candidate/observation_verified=false/task_completed=false kalır. Dolu candidate değerlendirmesiyle yanıtsızlık sınıflandırması ayrı yollardır; demo decoder'a None da göndermez.

## Inherited binding ve current source kimliği

Current Phase41 slots hash'i291caf… ve manifest0d67… gerçek input rolleridir. Orijinal binding221a67… eski parent40 queueFD86 preimage'ından türetilmiştir. Current slots hash'i ile digest yeniden hesaplanmaz. Full immutable source adapter owner'ın orijinal slots binding'ini doğrular ve source-bound builder gerçek source task/reference/candidate/file/digest'i kopyalar. Yeni register entry exact10 alanı parent preimage taşımadığından yalnız yeni5 dosyayı okuyan inspector bu kriptografik bağı bağımsız yeniden türetemez. Intake/classification digest eşliği ve packet support kontrolü original source üyeliği/necessity/producer proof değildir.

Future decoder exact eski flat response_slot_builder.ValidatedResponseSlots ve owner read_response_slots bağlamını kullanır. Wire-only snapshot full beşli sourcegroup yetkisi değildir; owner ret kuralları gevşetilmez. Binding matching observation verified/authorized submission, imza/token/anti-replay veya source freshness değildir.

## Exact yedi alan ve işlem sırası

| Future alan | Dar yapısal sınır |
| --- | --- |
| task_id | Exact string, original F0001…F0064 |
| binding_digest |64 lowercase hex SHA256 |
| reported_presence | present veya missing |
| observation_recorded_at |1…512 karakter nonempty strict UTF-8 string |
| observation_method |1…512 karakter nonempty strict UTF-8 string |
| source_locator_description |1…512 karakter nonempty strict UTF-8 string |
| evidence_sha256_if_available | Lowercase hex SHA256 veya null |

Exact dict7 dışında bytes/JSON text/path/serbest metadata/ikinci format yoktur. Önce field set, sonra type, bounded value, task lookup ve digest match kontrol edilir. Owner timestamp_string yalnız tür etiketi sağlar; yeni ISO/RFC/timezone/clock/freshness veya locator semantiği varsayılmaz. Reported presence ile evidenceSHA arasında ek koşul üretilmez. Bool/int/string coercion yoktur. Candidate rawpayload/log/store veya yanlış candidate hash'i sonuç olarak taşınmaz.

## Future memory sonucu ve actual wire farklıdır

Future result exact6 task_id/binding_digest/intake_status candidate_supplied/structural_result/observation_verified false/task_completed false'dur. Yapısal eşleşme structurally_compatible_unverified olarak kalır. Ret nedenleri yalnız unknown_task/binding_mismatch/invalid_field_set/invalid_field_type/invalid_field_value/duplicate_task_candidate'dır; source dosyası var/yok kararı değildir.

Field-set/type/value hatasında iki ID null'dur. Unknown task için valid-format ID tutulabilir fakat digest null kalır. Known slot mismatch/compatible durumunda yalnız gerçek source task/digest döner; yanlış candidate digest echo edilmez. Ambiguous bağlamda benzersiz digest yoktur. Defensive duplicate_task_candidate yolunu çalıştırmak için owner snapshot duplicate ret kuralı zayıflatılmaz. Bu nullable future result, actual deferred classification'ın nonnull gerçek source ID ve deferred status sözleşmesine eklenmez.

Tek dict stateless API, JSON oluşturulduktan sonra kaybolan duplicate key bilgisini geri getiremez; çağrılar arası duplicate/replay geçmişi tutmaz. Gelecekte JSON parse eden caller owner strict parser sorumluluğunu korur. Global registry, authority veya anti-replay sistemi oluşturulmaz.

## Çalıştırma ve güven sınırı

Pozitif structural compatibility, dolu negatif candidate, wrongbinding/unknowntask/duplicate/type-value senaryoları **runtime NOT_RUN**'dır. Demo ve inspector candidate_decoder çağırmaz; source slot submission=null ve template response=null/unsubmitted doğrudan tüketilir. Future decoder kaynağının bulunması gerçek submission kabul testi değildir.

Intake register canonical gerçek SHA256'ı classification.intake_register_sha256 ve manifest ilk payload'ına bağlanır; producer authentication veya source truth sağlamaz. Whole packet/projection11/source sıra/tür/null korunur. Null candidate, false candidate_present ve integer0 sayaç farklıdır; unknown'a çevrilmez. Source17 workflow mirası uydurulmaz;18 nested false trust ve demo true kalır. [Sözleşme](DEFERRED_INTAKE_CONTRACT.tr.md), [trust](TRUST_AND_DISCLOSURE.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).
