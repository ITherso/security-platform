# Offline Portable Task Exchange

**OFFLINE DEMONSTRATION — PORTABLE TASK REQUEST ONLY — NO TASK DISPATCH OR RESPONSE AUTHORIZED**

Phase43, doğrulanmış Phase42 Deferred Intake grubundaki açıkça seçilen yanıtsız işleri minimal görev taleplerine dönüştürür. Alıcı, kaynak workspace dosyalarını açmadan portable capsule'ın kapalı sözleşmelerini ve iç byte/hash ilişkilerini okuyabilir. Paket oluşturmak görev göndermek, yapısal doğrulama kaynak gözlemi veya yetkili yanıt almak değildir.

**2026-11-15 hazırlık kaydı:** Phase43 ürün CLI çağrısı **0/2**. Assembly, dar çıktı incelemesi ve inspector henüz yapılmadı; gerçek exit code, çıktı boyutu/hash veya teknik tamamlanma sonucu yoktur. [Demo teslim kaydı](../../docs/commercial/operations/phase43/DEMO_DELIVERY.tr.md) gerçek çağrılardan sonra güncellenecektir. Kodun bulunması runtime veya kabul kanıtı değildir.

## Üretici ve bağımsız alıcı sınırı

Üretici `ValidatedPhase42Source` ile exact beş immutable byte'ı tutar. `load_source(register,classification,receipt,summary,manifest,budget)` bounded/stable fiziksel okumadan sonra gerçek dört payload manifestini, eski owner'ın kapalı modellerini, classification türetimini, canonical register'ı ve qualified Markdown/full manifest eşliğini doğrular. `read_source(snapshot)` yalnız bellekte yeniden doğrulayıp bağımsız modeller döndürür. Aggregate inspection raporu kaynak snapshot yerine kullanılamaz. Eski Phase41/40 verisi açılmaz; eski CLI/builder veya future candidate decoder çalıştırılmaz.

`phase42_adapter` dar binary okuma ve exception bridge sağlar. Korunan IO sınıfının transitif import zinciri eski helper tanımlarını içerebilir; bu, eski CLI entrypoint veya builder yürütüldüğü anlamına gelmez. Üretici kaynak deltası eski owner koduna ihtiyaç duyar.

Alıcının runtime bağımlılık grafiği yalnız Python standart kütüphanesi ve yeni `exchange_contracts.py`, `portable_capsule.py`, `recipient_reader.py` dosyalarıdır. `inspect_task_exchange_capsule(exact_bytes)` immutable `ValidatedPortableTaskRequest` döndürür; `read_portable_task_request(snapshot)` kapalı envelope/response contract ve dört iç üyenin kimliğini kopyalar. Reader hiçbir Phase42 dosyasını açmaz, ZIP'i diske çıkartmaz. Gerçek başka host üzerinde çalışma **NOT_RUN**'dır.

## Sözleşmeler ve minimum disclosure

Request `termivar-offline-task-exchange-request/v1` exact6 alanlıdır: schema_version, mode demo, request_reference, source_phase42_register_sha256, source_phase42_manifest_sha256, selected_task_ids. 1–8 unique ve gerçek pending task seçilir; yanlış digest, unknown/duplicate task veya uygun olmayan tek kayıt bütün talebi reddeder. Global F0001…F0064 kimlikleri yeniden numaralanmaz.

Portable envelope `termivar-offline-portable-task-request/v1` exact10 üst alan ve her görevde exact10 alan taşır. Task alanları task_id/reference_id/candidate_id/file_id/binding_digest/slot_status/response_status/candidate_present/observation_verified/task_completed'dır. Awaiting/unsubmitted ve false durumları korunur. Full reference packet, projection listesi, present CAND0001 metadata'sı, source observed byte/hash, ham kaynak/candidate, source locator değeri veya analist kimliği taşınmaz. Dosya locator'ı gerekiyorsa daha sonra ayrıca yetkili insan tarafından sağlanmalıdır; Phase43 bunu istemez veya üretmez.

Future response contract `termivar-offline-portable-response-contract/v1`, yalnız mevcut owner'ın yedi alan tanımını taşır: task_id:string, binding_digest:sha256, reported_presence:present_or_missing, observation_recorded_at:timestamp_string, observation_method:string, source_locator_description:string, evidence_sha256_if_available:sha256_or_null. Üretici literal tanımları gerçek `submission_contract()` ile karşılaştırır. Yeni timestamp grammar, timezone/freshness veya locator semantics yoktur. Doldurulmuş response ve candidate decoding yoktur; eski decoder exact Phase41 `ValidatedResponseSlots` ister ve bu fazda None ile bile çağrılmaz.

Exchange index ve source receipt, capsule kimliği ile kaynak kimliklerini ayrı tutar. Receipt beş gerçek Phase42 dosyasının byte/hash/şema kimliklerini taşır; bu dosya kimlikleri hedef source gözlemi değildir. Kaynak sayaçlarının altı kapsamı ayrı korunur: Phase42 register_counts ve classification_counts; parent Phase41 slots_counts ve template_counts; parent Phase40 queue_counts ve handoff_counts. Parent distinct file/candidate paydaları tek task nedeniyle küçültülmez. Yeni altı sayaç seçilmiş task, yanıtsız request, ortak field definition ve submitted/verified/completed sayılarını taşır; definition count bütün paket için7'dir, task sayısıyla çarpılmaz; son üç sayı integer0'dır.

Güncel Phase42 register SHA256 `6465bab021f525b47d4fafd5a0ddc68020989b60e82bce3ec70f6bfaa4f8ff16`, manifest SHA256 `fbe94605564f06a11165cc9fb71229100b609e2c7d0248e4772af53ddb81b6cc`'dir. İç Phase41 slots/manifest pinleri ebeveyndir. Inherited binding `221a67c41a4c3492ac4983e0a5af337aa5c42508a2391226f7ed0e84d7197bae` kaynakla eşit kopyalanır; güncel register6465 veya eski slots291 ile yeniden türetilmez. Orijinal Phase40 preimage'ı yoktur; original binding kriptografisi ve task membership bağımsız yeniden kanıtlanmaz.

## İç capsule ve dış kaynak teslimi

Portable capsule exact dört üyedir: `task-request.json`, `response-contract.json`, `README.txt`, `capsule-manifest.json`. İç manifest ilk üçün gerçek byte/SHA256 ilişkisini bağlar, kendisini hash'lemez. Canonical JSON UTF-8/LF/sorted keys/indent2'dir. Canonical ZIP, ZIP_STORED/fixed1980-01-01/Unix regular0600/empty extra-comment/flags0 kullanır. Epoch konteyner metadata'sıdır; gözlem zamanı veya güvenilir timestamp değildir. Reader bounded member okumaları, CRC, kapalı şema, manifest ve bütün canonical ZIP byte eşliğini inceler; farklı local-header/trailing/Zip64 biçimleri dahil canonical olmayan kapsülleri reddeder. No extraction/path opening.

İç capsule içinde ek üye/nested ZIP/directory/symlink/encryption/duplicate/traversal yoktur. Dış `Termivar-Offline-Task-Exchange-phase43-2026-11-15.zip`, yeni15 kaynak/belge ile gerçek6 operasyonel çıktıyı, dolayısıyla portable capsule'ı taşır. Mantıksal21 üye hedefi gerçek listeden ölçülmelidir. Fiziksel `security-platform-phase43-source/...` ile arşiv içi `security-platform/...` yolları ayrıdır. Dört source/asset/delivery/closure metadata dosyasının tamamı dış ZIP dışında kalır; self-hash döngüsü yoktur. Altı küratörlü inceleme haritası metadata içinde tutulur; ayrı review/private prompt/state eklenmez. İki arşivin de SHA256 değeri byte kimliğidir; producer authentication veya gerçek recipient kabulü değildir.

## İzinli iki ürün komutu

Aşağıdaki komutlar henüz çalıştırılmamıştır. Her dispatch önceden kaydedilir; hata bütçeyi tüketir. İkinci komut yalnız ilk exit0, ilk beş output tam ve gerçek dar manuel inceleme başarılıysa yapılır. Retry/üçüncü çağrı/helper/preflight/import smoke/AST/--help/test/build yoktur; Phase41 insan istisnası taşınmaz.

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_exchange/assemble_task_exchange.py --register outputs/phase42-deferred-intake/deferred-intake-register.json --classification outputs/phase42-deferred-intake/intake-classification.json --receipt outputs/phase42-deferred-intake/intake-source-receipt.json --source-summary outputs/phase42-deferred-intake/intake-summary.md --source-manifest outputs/phase42-deferred-intake/manifest.json --request security-platform-phase43-source/tools/commercial_task_exchange/examples/demo_task_exchange_request.json --output-dir outputs/phase43-task-exchange
```

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_exchange/inspect_task_exchange.py --capsule outputs/phase43-task-exchange/task-exchange-capsule.zip --index outputs/phase43-task-exchange/task-exchange-index.json --receipt outputs/phase43-task-exchange/task-exchange-source-receipt.json --summary outputs/phase43-task-exchange/task-exchange-summary.md --manifest outputs/phase43-task-exchange/manifest.json --output outputs/phase43-task-exchange/inspection-summary.json
```

Assembly ilk5 capsule/index/receipt/Markdown/manifest üretir. Inspector yalnız bu beş yeni output'u ve capsule'ın dört üyesini değerlendirir; eski Phase42 dosyalarını yeniden açmaz. Kapsam `five_new_task_exchange_outputs_and_capsule_internal_correspondence_only`; content_consistent yalnız yeni output ilişkileridir. Canonical/manifest/hash kontrolü source truth, original binding proof, producer veya recipient yetkisi değildir; tutarlı değişiklikler yeniden hash'lenebilir.

## Koruma ve açık kabul kapıları

Çalışma yalnız `feat/offline-portable-task-exchange` izole worktree'sinde, base `3dc85d100305ad5e299706e7920a007aa53ad1c0` / tree `194767a84cd50b6496f9494b8f0de48597239476` üzerinden yapılır. Orijinal repository branch/HEAD, foreign35 source ve48 Altay output dosyası kapsam dışıdır. 489 eski output, orijinal459 source,21 dist asset ve60030-byte production wheel ayrı baseline kapsamlarıdır; final eşlik ölçümü dış metadata'da raporlanır. Asset/wheel yeni worktree veya ZIP'e kopyalanmaz; new_assets=[].

Worktree checkout'unda458/459 dosya orijinal raw byte ile eşittir. Tek LF checkout farkı `docs/commercial/examples/TERMIVAR_LICENSE.txt`: orijinal1085B/SHA256 d308383be39c28054876444bc46a410a5e753c7df982afce644fab1e7e9f754d (21 CRLF), yeni checkout1064B/SHA256 e085606a102514117a74d1782047303654200dabb82f4655f0ec60731f4c9a34 (pinned Git blob). Orijinalin CRLF→LF dönüşümü worktree byte'ına eşittir; geliştirmede lisans dosyası yeniden yazılmamıştır. Orijinal fiziksel459 ve worktree canonical459 baselineları ayrı tutulur; tüm459 original raw byte'ın yeni checkout'a eşit olduğu iddia edilmez. Otomatik merge/cherry-pick yapılmaz.

Exact18 nested trust flag false ve demo_only=true korunur; kaynakta bulunmayan17 workflow alanı uydurulmaz. Inspector'ın dokuz yerel false alanı kendi işlem sınırıdır. Yeni pozitif source/producer/recipient/response authority sonucu yoktur. Minimizasyon anonimleştirme veya şifreleme değildir.

NOT_RUN: gerçek ikinci host/analist alımı; recipient authentication/authorization; filled future response/decoder/submission/ingestion; producer identity/imza/anti-replay/trusted timestamp; source locator/reobservation/evidence collection; assignment/acceptance/completion; hostile JSON/adversarial ZIP/modified capsule/wrong digest/duplicate/symlink/traversal/bomb/limit; permission/crash/partialwrite/repeatdeterminism; Phase31 guard; Rust compiler/module closure/component ownership/native runtime; human/legal/customer/production/release/Phase19 UI. Test/runner/coverage/typecheck/build/install/import smoke/AST/preflight/network/live/admin/PDF/push/deploy yapılmaz. Phase19 file:// engeli aşılmaz. Ölçülmüş Phase43 teknik teslimden sonra durulur; Phase44 başlatılmaz.

Belgeler: [sözleşmeler](../../docs/commercial/operations/phase43/TASK_EXCHANGE_CONTRACT.tr.md), [veri minimizasyonu](../../docs/commercial/operations/phase43/MINIMAL_DISCLOSURE.tr.md), [recipient doğrulama](../../docs/commercial/operations/phase43/RECIPIENT_VALIDATION.tr.md), [demo teslim](../../docs/commercial/operations/phase43/DEMO_DELIVERY.tr.md). Son kaynak ZIP ve dört metadata'nın byte/SHA256 kimlikleri birbirine döngü kurmadan dış teslim kayıtlarında ölçülür.
