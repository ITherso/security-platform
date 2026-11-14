# Offline Deferred Response Intake

**OFFLINE DEMONSTRATION — DEFERRED RESPONSE INTAKE ONLY — NO CANDIDATE RESPONSE RECEIVED**

Araç, Phase41'in unsubmitted template'ini bağımsız bir tüketiciyle okuyup yanıtsız task-bound intake kaydı ve classification üretir. Ayrıca future memory-only candidate structural decoder kaynağı içerir. Demo bu decoder'ı pozitif/negatif candidate veya None ile çağırmaz. `structurally_valid ≠ observation_verified`; `task_binding_matched ≠ authorized_submission`; `response=null ≠ source_file_missing_now`.

**Kaynak hazırlığı, 2026-11-14:** Phase42 ürün çağrısı **0**. Yeni intake/classification/receipt/inspector başarısı, output/ZIP ölçüsü veya hash'i iddia edilmez. F0001 source metadata'sının yanıtsız durumu yeni ürünün çalıştığı anlamına gelmez. Actual sonuçlar [DEMO_DELIVERY](../../docs/commercial/operations/phase42/DEMO_DELIVERY.tr.md) kaydına yazılır; kaynak freeze sonrası yalnız README ve teslim belgesi güncellenir.

## Immutable Phase41 source grubu

Yalnız `outputs/phase41-response-slots/` altındaki slots/template/receipt/Markdown/manifest beşlisi okunur. `ValidatedPhase41Source` exact tuple5bytes/frozen/slots/repr-hidden'dır. `load_source(slots_path,template_path,receipt_path,summary_path,manifest_path,budget)` bounded/stable fiziksel beşli okur; `read_source(snapshot)` memory-only yeniden doğrulayarak `(slots,template,receipt,source_artifacts)` dört tuple'ını ve bağımsız kopyaları döndürür. Caller trusted/validated etiketi veya aggregate inspector tam model yerine kullanılamaz; eski Phase40 snapshot yanlış gruba uygulanmaz.

Önce gerçek dört payload manifest byte/hash eşliği, sonra owner strict üç model/validate_relationships/exact template_from_slots, canonical actual slots bytes, qualified corrected owner Markdown ve dört argümanlı full manifest eşliği gerekir. Owner class/import kimliği tek flat route'tur; generic renderer/manifest qualified kullanılır. Eski CLI/build_response_slots çalıştırılmaz; Phase40/39 input, CSV/kapsül/guard/Rust/native açılmaz.

Current Phase41 slots SHA256 `291caf1d486ad50bab53a784adffa5b7b4bebd02e0ced53c85ae310f7eee9173`; current manifest SHA256 `0d67de7226e61efa9c1af7236e8f01d7458df9adab13e0217e8150af2565c0e4`. İçerideki parent40 queueFD86/manifestE611 pinleri current identity değildir. Inherited binding221a67… parent40 queueFD86 ile türetilmiştir; current slots291 ile yeniden hesaplanmaz. Full source adapter eski owner bağını doğrular; source-bound builder exact digest/tuple'ı kopyalar. Yeni wire parent preimage'ı taşımaz; new-only inspector original binding kriptografisini veya task membership/necessity'yi bağımsız yeniden kanıtlayamaz.

## Request ve gerçek unsubmitted tüketimi

Request `termivar-offline-deferred-intake-request/v1` exact7: schema_version, mode demo, request_reference, source_phase41_slots_sha256, source_phase41_manifest_sha256, selected_task_ids, candidate_source existing_unsubmitted_template.1–8 unique gerçek source task; unknown/duplicate/wrongdigest all-or-nothing reddedilir. Request/assembly CLI dış candidate path/payload almaz. Original global F kimliği/sırası korunur; task yeniden numaralanmaz.

build_deferred_intake(source,request)→immutable ValidatedDeferredIntake; read_deferred_intake(exact_snapshot)→closed copy; build_intake_classification(snapshot)→closed classification; make_source_receipt(source,snapshot)→closed receipt. Demo doğrudan source slot submission=null ve template response=null/unsubmitted ilişkisini tüketir. Decoder'a None göndermek yanıtsız sınıflandırma yolu değildir.

Register schema `termivar-offline-deferred-intake-register/v1`; common4 schema/demo-label/demo-only true/exact18 nested false trust_flags + currentSHA2/request/reference_packets/intake_entries/counts/limitations. Entry exact10: task_id/reference_id/candidate_id/file_id/binding_digest/slot_status/response_status/candidate_present/candidate_classification/candidate_response. Sabit demo awaiting_external_response/unsubmitted/**false/no_candidate_supplied/null** değerlerini gerçek kaynaktan korur.

Classification `termivar-offline-deferred-intake-classification/v1`; common + currentSHA2/intake_register_sha256/task_classifications/counts/limitations. Task row exact6 task_id/binding_digest/intake_status/structural_result/observation_verified/task_completed; awaiting_submission/not_evaluated_no_candidate/**false/false**. Canonical register hash'i gerçek ilk JSON bytes'ına bağlanır; candidate olmadan uyumluluk veya gözlem kabulü üretilmez.

## Future decoder: uygulanmış kaynak, çalıştırılmamış candidate yolları

decode_candidate_response(validated_slots,candidate_object), exact eski flat `response_slot_builder.ValidatedResponseSlots` wire snapshot'ı ve exact dict7 alır. Full source-group proof değildir. İkinci JSON/bytes/path formatı yoktur; raw future payload output/log/store'a taşınmaz. Owner submission_contract yedi alanı ve tür tanımları esas alınır:

| Alan | Yapısal sınır |
| --- | --- |
| task_id | Original F0001…F0064 string |
| binding_digest | Lowercase hex SHA256 |
| reported_presence | present veya missing |
| observation_recorded_at | Nonempty1…512 strict UTF-8 string |
| observation_method | Nonempty1…512 strict UTF-8 string |
| source_locator_description | Nonempty1…512 strict UTF-8 string |
| evidence_sha256_if_available | Lowercase hex SHA256 veya null |

Timestamp tür adı dışında owner grammar sağlamaz; ISO/RFC/timezone/clock/freshness veya locator anlamı doğrulanmaz. Presence ile evidence digest arasında ek koşul uydurulmaz. Exact field set→type→bounded value→source task lookup→source digest match sırası vardır; bool/int coercion yoktur. Yapısal uyum structurally_compatible_unverified kalır; observation verified değildir.

Future memory result exact6 task_id/binding_digest/intake_status candidate_supplied/structural_result/observation_verified false/task_completed false. Kapalı ret nedenleri unknown_task, binding_mismatch, invalid_field_set, invalid_field_type, invalid_field_value, duplicate_task_candidate. Field/type/value hatasında iki ID null; unknown task valid ID'si tutulabilir/digest null; known slot mismatch veya compatible sonucunda yalnız gerçek source task/digest döner, yanlış candidate hash'i echo edilmez. Nullable future result ile gerçek deferred wire'ın nonnull source ID'leri ayrı sözleşmelerdir. Defensive duplicate-context dalı için owner snapshot'ın duplicate ret kuralı gevşetilmez.

Tek dict alan API postconstruction duplicate JSON key'lerini veya çağrılar arası replay/duplicate geçmişini bilemez; global registry/anti-replay yoktur. İleride JSON parse eden caller owner strict wire parser sorumluluğunu korur. Dolu pozitif ve dolu negatif decoder yolları **NOT_RUN**; demo/inspector hiçbir candidate ve None ile decoder çalıştırmaz.

## Full packets, dört source sayım grubu ve trust

Task-associated reference paketleri source exact5 alanını ve bütün11-alan projection listesini özgün sıra/tür/null ile korur. Present CAND0001 aynı full packet'ta kalır; ona yeni intake entry yoktur. Missing byte/hash null, count0/false veya sıfır-byte file değildir. Bloke/eşleşmeyen olumlu child metadata taşınmaz.

Receipt `termivar-offline-deferred-intake-source-receipt/v1`; source_artifacts5/currentSHA2/source_schema_versions/source_counts/content_scope/limitations taşır; Markdown schema null. `source_counts={slots_counts:source7,template_counts:source7,phase40_counts:{queue_counts:original7,handoff_counts:original7}}`. Dört payda flatten edilmez; parent distinct_file_count2 tek task nedeniyle1 yapılmaz. Content scope five_Phase41_artifact_internal_correspondence_only.

Yeni exact8 counts selected_task_count/selected_reference_count/intake_entry_count/awaiting_submission_count/candidate_present_count/structurally_compatible_count/observation_verified_count/completed_task_count; son4 integer0. Null/false/integer0/unknown ayrıdır. Source modelinde workflow_flags/17 workflow alanı yoktur; miras uydurulmaz. Yeni inspector'ın local false işlem sınırları source17 inheritance değildir. Exact18 trust false/demo_only true korunur.

## İzinli exact iki ürün çağrısı

Aşağıdakiler hazırlanan komutlardır; actual başarı değildir. Her dispatch önceden kaydedilir. İkinci çağrı yalnız ilk exit0, eksiksiz ilk5 ve task/binding/null/no_candidate/fullpacket/trust/receipt/MD/manifest dar inceleme sonrası yapılabilir. En fazla2 çağrı; failure tüketilir. Retry/üçüncü/helper/preflight/import smoke/AST/--help/test/eski CLI yoktur. Phase41 insan istisnası bu faza taşınmaz.

```text
python -I -B security-platform/tools/commercial_deferred_intake/assemble_deferred_intake.py --slots outputs/phase41-response-slots/task-response-slots.json --template outputs/phase41-response-slots/response-template.json --receipt outputs/phase41-response-slots/response-slot-source-receipt.json --source-summary outputs/phase41-response-slots/response-slot-summary.md --source-manifest outputs/phase41-response-slots/manifest.json --request security-platform/tools/commercial_deferred_intake/examples/demo_intake_request.json --output-dir outputs/phase42-deferred-intake
```

```text
python -I -B security-platform/tools/commercial_deferred_intake/inspect_deferred_intake.py --intake outputs/phase42-deferred-intake/deferred-intake-register.json --classification outputs/phase42-deferred-intake/intake-classification.json --receipt outputs/phase42-deferred-intake/intake-source-receipt.json --summary outputs/phase42-deferred-intake/intake-summary.md --manifest outputs/phase42-deferred-intake/manifest.json --output outputs/phase42-deferred-intake/inspection-summary.json
```

İlk output5 intake/classification/receipt/summary/manifest'tir. Manifest gerçek ilk4 payload'ı bağlar; kendi hash'i/inspection kapsam dışıdır. Inspector yalnız yeni5 output'un closed models/task/digest eşliği, packet support/null/false/0/count/canonical actual registerSHA/receipt/MD/manifest ilişkisini denetler. content_consistent yalnız iç tutarlılıktır; original source binding preimage/observation/task necessity/candidate decoder yürütme kanıtı değildir. Report string'leri owner512 karakter sınırını korur; bu limit gevşetilmez.

## Limit ve açık kabul kapıları

Request32K; source slots/template/receipt/MD/manifest256/128/64/128/64K; toplam1MiB. Yeni intake256K/classification128K/receipt64K/summary128K/manifest64K; task8/ref8/proj64/string512/depth12/nodes20.000 ve daha sıkı owner limitleri. Strict UTF-8/JSON; duplicate/unknown/schema/type/NaN/Infinity/float/bool-as-int/SHA/binding ret. Yeni boş output/overwrite ve otomatik silme yoktur. Markdown bütün input dict alanlarında explicit sıra kullanır; insertion order bağımlılığı ve aktif HTML/path/URL/script yoktur.

NOT_RUN: candidate positive/negative decoding, binding mismatch/unknown task/duplicate candidate/type-schema/hostileJSON/UTF8/BOM/wrongdigest/modifiedsource, limit/permission/crash/partialwrite/repeatdeterminism/ikincihost; producer/anti-replay/source reobservation/evidence collection/analyst assignment-acceptance-completion/source freshness/Phase31 guard/compiler/module closure/ownership/native/human/legal/customer/release/production/Phase19 UI. Test/build/install/import-smoke/AST/network/live işlem yoktur. file:// engeli server/hosting/browser ile aşılmaz. Decoder kaynağının bulunması future response kabulü değildir.

Belgeler: [sözleşme](../../docs/commercial/operations/phase42/DEFERRED_INTAKE_CONTRACT.tr.md), [binding/classification](../../docs/commercial/operations/phase42/TASK_BINDING_AND_CLASSIFICATION.tr.md), [trust/disclosure](../../docs/commercial/operations/phase42/TRUST_AND_DISCLOSURE.tr.md), [teslim](../../docs/commercial/operations/phase42/DEMO_DELIVERY.tr.md).

Yeni delta korunmuş owner kod/import zincirine ihtiyaç duyar; standalone binary veya production wheel/ikinci host kabulü değildir. ZIP `Termivar-Offline-Deferred-Intake-phase42-2026-11-14.zip` kapsamı yeni15 source/belge+actual6 output'tur; ölçülmemiş boyut/üye/hash iddia edilmez. Source/asset/delivery/closure dört metadata'nın tamamı ZIP dışında, noSMself/nohashcycle'dır. Ölçülen kimliklerin otoritesi [source manifest](../../../outputs/phase42-deferred-intake-source-manifest.json), [asset manifest](../../../outputs/phase42-deferred-intake-asset-manifest.json), [delivery manifest](../../../outputs/phase42-deferred-intake-delivery-manifest.json), [closure](../../../outputs/phase42-deferred-intake-closure.json).6 review map metadata'ya gömülür; ayrı review/private prompt/state yoktur.21 asset saltokunur korunur/new_assets=[]/asset kopyası yoktur. Eski input/ZIP/CSV/kapsül/Rust/native/wheel/binary/cache/DB/dependency kodu paketlenmez. Phase7–41/backend/auth/native/HBF/Altay/wheel/lock/lisans korunur. İzinli2 çağrı ve ölçülmüş kapanış sonrası durulur; Phase43/yeni özellik/üçüncü çağrı/test/native/release yoktur.
