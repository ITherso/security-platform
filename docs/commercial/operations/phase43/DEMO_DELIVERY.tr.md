# Phase43 demo teslim kaydı

**OFFLINE DEMONSTRATION — PORTABLE TASK REQUEST ONLY — NO TASK DISPATCH OR RESPONSE AUTHORIZED**

Tarih: **2026-11-15**. Bu ilk kayıt yalnız kaynak hazırlığını açıklar. Phase43 ürün CLI dispatch sayısı **0/2**; assembly ve inspector **PENDING**. Çıktı, exit code, hash, boyut, manuel inceleme veya tamamlanma sonucu henüz kaydedilmemiştir. İki gerçek çağrıdan sonra yalnız README ile bu belge güncellenebilir; diğer sözleşme belgeleri ve kod generation öncesinde dondurulur.

## Gerçek kaynak ve seçilecek görev

Kaynak `outputs/phase42-deferred-intake/` exact beşlisidir. Bunlar başlangıçtaki fiziksel dosya ölçümleridir; Phase43 output'u değildir:

| Kaynak | Byte | SHA256 |
| --- | ---: | --- |
| deferred-intake-register.json | 6294 | 6465bab021f525b47d4fafd5a0ddc68020989b60e82bce3ec70f6bfaa4f8ff16 |
| intake-classification.json | 2432 | 0ad99132b85355b52717d502a295ccb75fbc5074d02622c63a7f4133802b0e7d |
| intake-source-receipt.json | 4518 | 0915a855ec4474972f5af6e79ff7142186d959cda0de4bb1621621fda5b0b639 |
| intake-summary.md | 17453 | e78e79e65dfae68fb0e2798622da8f3203fc6dcf531995a7de57f828aa1b28fd |
| manifest.json | 5796 | fbe94605564f06a11165cc9fb71229100b609e2c7d0248e4772af53ddb81b6cc |

Eski inspection-summary.json aggregate raporu kaynak gruba eklenmez. Üretici önce gerçek payload/hash, sonra owner model/relationship/classification/canonical Markdown/full manifest eşliğini doğrulamalıdır. Bu işlem henüz ürün çağrısı olarak çalıştırılmamıştır.

Gerçek kaynakta seçilecek F0001 bağı:

| Alan | Kaynaktaki değer |
| --- | --- |
| task_id | F0001 |
| candidate_id | CAND0002 |
| reference_id | rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81 |
| file_id | candidate-file-9a67f54741d040e044cb2e94b227515bd0c9b595e8f6eae0d896e70ea664ec9a |
| binding_digest | 221a67c41a4c3492ac4983e0a5af337aa5c42508a2391226f7ed0e84d7197bae |
| slot_status / response_status | awaiting_external_response / unsubmitted |
| candidate_present / candidate_response | false / null |
| classification | awaiting_submission / not_evaluated_no_candidate |
| observation_verified / task_completed | false / false |

Binding güncel Phase42 register/manifest veya parent Phase41 slots kimliğinden yeniden hesaplanmaz. Original Phase40 preimage'ı yoktur; iç eşlik original binding kriptografisi, task ownership/membership/necessity veya producer yetkisini bağımsız kanıtlamaz.

Hedef demo sayacı kaynaktan türetilmelidir: selected1, unsubmitted1, ortak response definitions7, submitted0, verified0, completed0. Bunlar henüz Phase43 üretim sonucu olarak ölçülmemiştir ve fixture olarak kodlanmaz. Source count register8/classification8/parent slots7/template7/queue7/handoff7 altı kapsamı ayrı korumalıdır; parent distinct file/candidate2 kapsamı küçültülmemelidir. Portable capsule packet/projection export0 olmalı; CAND0001 present metadata'sı, observed source byte/hash, locator değeri, candidate payload ve analist kimliği bulunmamalıdır.

## Yalnız tanımı taşınacak yedi alan

| Alan | Owner tür tanımı |
| --- | --- |
| task_id | string |
| binding_digest | sha256 |
| reported_presence | present_or_missing |
| observation_recorded_at | timestamp_string |
| observation_method | string |
| source_locator_description | string |
| evidence_sha256_if_available | sha256_or_null |

Producer literal tanımı gerçek owner submission_contract ile karşılaştırmalıdır. Tanımlar doldurulmuş response veya dosya toplama talimatı değildir; timestamp grammar/timezone/freshness ve locator semantics eklenmez. Future decoder dolu nesne veya None ile çalıştırılmaz; sahte Phase41 snapshot oluşturulmaz.

## Çağrı bütçesi ve planlanan komutlar

Her dispatch önceden kaydedilir. Hata bütçeyi tüketir; retry, üçüncü çağrı, helper execution, AST/import smoke/preflight/--help/test/build veya eski ürün CLI yoktur. Phase41 insan tekrar istisnası taşınmaz.

| Sıra | Ürün işlemi | Dispatch | Gerçek exit code |
| ---: | --- | --- | --- |
| 1 | assemble_task_exchange.py | PENDING | Henüz yok |
| 2 | inspect_task_exchange.py | PENDING; yalnız ilk exit0/tam5/manuel inceleme sonrası | Henüz yok |

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_exchange/assemble_task_exchange.py --register outputs/phase42-deferred-intake/deferred-intake-register.json --classification outputs/phase42-deferred-intake/intake-classification.json --receipt outputs/phase42-deferred-intake/intake-source-receipt.json --source-summary outputs/phase42-deferred-intake/intake-summary.md --source-manifest outputs/phase42-deferred-intake/manifest.json --request security-platform-phase43-source/tools/commercial_task_exchange/examples/demo_task_exchange_request.json --output-dir outputs/phase43-task-exchange
```

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_exchange/inspect_task_exchange.py --capsule outputs/phase43-task-exchange/task-exchange-capsule.zip --index outputs/phase43-task-exchange/task-exchange-index.json --receipt outputs/phase43-task-exchange/task-exchange-source-receipt.json --summary outputs/phase43-task-exchange/task-exchange-summary.md --manifest outputs/phase43-task-exchange/manifest.json --output outputs/phase43-task-exchange/inspection-summary.json
```

İlk çağrıdan sonra ikinci çağrıya geçmeden gerçek source identity, F0001 tuple/digest, exact4 üye, exact7 tanım, packet/projection ve locator/payload yokluğu, null/false/integer0,18 false trust/demo_only ve capsule/index/receipt/Markdown/manifest ilişkileri metadata üzerinden dar manuel incelenecektir. Bu inceleme henüz **PENDING**'dir; otomatik test veya gerçek task/source kabulü değildir.

## Henüz oluşmayan çıktı ve paket ölçümleri

Beklenen altı operasyonel ad: task-exchange-capsule.zip, task-exchange-index.json, task-exchange-source-receipt.json, task-exchange-summary.md, manifest.json, inspection-summary.json. Byte/SHA256 tablosu gerçek dosyalardan sonra eklenecektir. İç capsule'ın task-request.json/response-contract.json/README.txt/capsule-manifest.json üyelerinin kimlikleri de henüz ölçülmemiştir. Inner manifest ilk üçünü bağlar ve self-excluded'dır; fixed1980 epoch gözlem veya trusted time değildir.

Inspector yalnız yeni ilk5 output'u ve iç capsule'ı okumalıdır. Kapsam five_new_task_exchange_outputs_and_capsule_internal_correspondence_only; gerçek content_consistent sonucu henüz yoktur. Old Phase42 source read/dispatch/assignment/response/observation/producer/recipient/human/secondhost olmak üzere dokuz yerel işlem alanı false olmalıdır. 18 nested source trust false/demo_only=true korunmalıdır; source modelinde17 workflow alanı varmış gibi gösterilmez. Tutarlı hash/structure producer authentication, authorization veya source truth değildir.

## İzole kaynak ve koruma kaydı

Fiziksel worktree `security-platform-phase43-source/`, branch feat/offline-portable-task-exchange; base commit3dc85d100305ad5e299706e7920a007aa53ad1c0/tree194767a84cd50b6496f9494b8f0de48597239476. Generation source commit/tree henüz belirlenmemiştir. Orijinal security-platform dalı/HEAD'i ve foreign35 source +48 Altay output dosyası değiştirilmez. Otomatik merge/cherry-pick yapılmaz. 489 eski output, orijinal459 source, worktree canonical459,21 orijinal dist asset ve60030-byte wheel ayrı karşılaştırma kapsamlarıdır. Wheel SHA256 59ad0bfee4d5427e4dc197e0c535cc3d2ade4c3c621d4919fe9d2c3a995bbf06; final koruma sonucu dış metadata'da gerçek ölçümle verilir.

Yeni checkout458/459 original raw source byte'ına eşittir. Lisansın tek checkout LF farkı açıktır: orijinal TERMIVAR_LICENSE.txt1085B/d308383be39c28054876444bc46a410a5e753c7df982afce644fab1e7e9f754d,21CRLF; worktree1064B/e085606a102514117a74d1782047303654200dabb82f4655f0ec60731f4c9a34,0CRLF ve pinned Git blob ile eşit. Orijinal.replace(CRLF,LF)==worktree'dir. Hiçbiri geliştirmede yeniden yazılmamıştır; original fiziksel459 ve worktree canonical459 namespace'leri ayrıdır. Tüm459 original raw hash'in yeni checkout'ta eşit olduğu iddia edilmez.

Dış kaynak ZIP Termivar-Offline-Task-Exchange-phase43-2026-11-15.zip yalnız yeni15 source/docs +gerçek6 output=21 logical üye hedefler. Physical worktree prefix'i ZIP'e girmez; logical security-platform/... kullanılır. İç portable capsule dış ZIP'te operational output olarak bulunabilir; capsule'ın kendisi nested ZIP içermez. Önceki source/input/ZIP/native/wheel/cache/private/foreign dosyalar eklenmez. Yeni asset yoktur;21 eski asset ve wheel kopyalanmaz.

Dört authoritative dış metadata outputs/phase43-task-exchange-source-manifest.json, -asset-manifest.json, -delivery-manifest.json, -closure.json'dur. Dördü dış ZIP dışında kalır; source manifest self üyesi veya SHA döngüsü yoktur. Altı curated review nesnesi metadata'ya gömülür. Gerçek ZIP/metadata byte/hash/üye sayısı, worktree commit/tree, kaynak/output/foreign/asset/wheel final koruma ölçümleri henüz **PENDING**'dir. Oluşmayan dosyaya başarı/hash/boyut yazılmaz.

## Açık NOT_RUN kapıları

- Gerçek ikinci host import ve gerçek analistin request alması; recipient authentication/authorization.
- Doldurulmuş future response, Phase42 future candidate decoder, response submission/ingestion.
- Producer identity, dijital imza, anti-replay, trusted timestamp ve source locator doğrulaması.
- Source reobservation/evidence collection; task assignment/acceptance/completion.
- Hostile JSON/adversarial ZIP/modified capsule/wrong digest/duplicate member/symlink/traversal/ZIP bomb/limit aşımı.
- Permission/crash/partial write ve repeat determinism.
- Phase31 guard, Rust compiler/module closure, component ownership, native scanner/runtime.
- Human/legal/customer/production/release ve Phase19 UI kabulü.

Test/runner/coverage/typecheck/build/install/package manager/Cargo/rust-analyzer/AST/import smoke/preflight/--help/eski CLI/helper execution/network/DNS/live/API/IdP/PG/VM/driver/service/admin/PDF/push/deploy yoktur. Phase19 file:// engeli server/hosting/farklı browser ile aşılmaz. İzinli iki çağrı, dar inceleme ve ölçülmüş teknik teslimden sonra durulur; Phase44 veya yeni mikro özellik başlatılmaz. Bu hazırlık kaydı **COMPLETED** iddiası değildir.
