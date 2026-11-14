# Phase43 bağımsız recipient yapısal doğrulaması

**OFFLINE DEMONSTRATION — PORTABLE TASK REQUEST ONLY — NO TASK DISPATCH OR RESPONSE AUTHORIZED**

Alıcı API'si `inspect_task_exchange_capsule(capsule_bytes) -> ValidatedPortableTaskRequest` exact immutable bytes alır. Snapshot frozen/slots/reprFalse'dır; caller'ın trusted etiketi kullanılmaz. Oluşturma ve `read_portable_task_request(snapshot)` bellekte yeniden doğrulama yapar; read kapalı envelope/response contract ve dört gerçek iç üyenin byte/hash kimliğini bağımsız kopyalar. ZIP diske çıkartılmaz ve Phase42 kaynak dosyaları açılmaz.

Runtime grafiği yalnız Python standart kütüphanesi ve yeni üç modüldür: exchange_contracts.py, portable_capsule.py, recipient_reader.py. Reader eski owner, kaynak adapter, InputBudget, publication veya CLI import etmez. Canonical writer reader'ı import etmez; döngü yoktur. Üretici ve dış inspector IO bağımlılıkları bu recipient grafiğinin dışında kalır. Üretici eski owner tanımlarını kullanabilir; eski entrypoint yürütülmesi değildir. Gerçek ikinci host kurulumu/çalışması **NOT_RUN**'dır; bu kaynak sınırı o kabulün yerine geçmez.

## Exact dört üye ve canonical konteyner

`termivar-offline-task-exchange-capsule/v1` exact şu sırayı kullanır:

| Üye | Sözleşme ve sınır |
| --- | --- |
| task-request.json | Kapalı portable task request;64KiB |
| response-contract.json | Yalnız yedi alan tanımı;32KiB |
| README.txt | Sabit UTF-8/LF kapsam metni;4KiB |
| capsule-manifest.json | İlk üç üyenin gerçek byte/SHA256 ilişkisi;32KiB |

Toplam açılmış içerik ve raw ZIP ayrı ayrı128KiB ile sınırlıdır. İç manifest common demo/trust alanlarını, ilk üç üyenin kimliklerini, manifest_self_excluded=true ve yerel integrity_scope'u taşır; kendi hash'ini içermez. Ortak18 trust false ve demo_only=true korunur. İç üyelerin hash'i source truth veya imza değildir.

Tek canonical ZIP biçimi ZIP_STORED, allowZip64=False, fixed1980-01-01, Unix regular0600/create_system3, empty extra/comment ve flags0'dır. Bu epoch yalnız konteyner metadata'sıdır; source observation zamanı, saat doğruluğu veya trusted timestamp değildir. JSON ensure_ascii=False/sorted keys/indent2/LF byte'ıdır; README exact statik byte'tır.

Reader `ZipFile(BytesIO(...))` üzerinde exact isim/sıra ile declared ve actual boyutları denetler; sınırlı member okumaları, CRC ve manifest karşılaştırması yapar. Duplicate/NUL/orig_filename mismatch, traversal, directory/DOS directory, symlink/nonregular, encryption, compression, ZIP/member extra-comment ve boyut aşımı reddedilir. Canonical JSON ve README byte'ları incelenir. Reader aynı pure writer ile canonical ZIP'i yeniden kurup bütün raw byte ile karşılaştırır; alternatif local header, trailing veri veya Zip64 metadata varyantlarını kabul etmez. Extraction, source locator açma veya arşiv üyesini dosya path'i olarak takip etme yoktur.

## Kapalı request ve response alanları

Envelope'ın exact10 üst alanı ve görevlerin exact10 alanı doğrulanır. Task ID/digest/tuple tekilliği, original task sırası, awaiting_external_response/unsubmitted ve false candidate_present/observation_verified/task_completed korunur. Unknown alanlar, full reference packet/projection veya candidate payload eklemek için alan bırakmaz. Response contract exact yedi alanın isim/tür tanımıdır; doldurulmuş response kabul edilmez. Yeni timestamp grammar/timezone, freshness veya locator semantics türetilmez.

Standalone strict parser UTF-8/BOM, duplicate JSON key, unknown schema/field, float/NaN/Infinity, bool-as-int, invalid digest/enum ve bounded string/depth/node kurallarını uygular. JSON string512/depth12/nodes20000 ve daha dar model limitleri korunur. Bu retlerin kaynak kodunda bulunması hostile JSON/ZIP, negatif veya limit senaryolarının çalıştırıldığı anlamına gelmez; bu fazda bunlar NOT_RUN'dır.

## Kanıtlanan ve kanıtlanmayan kapsam

Yapısal kontrol, sunulan capsule byte'ının canonical üyeler/model/manifest/hash ilişkisine uyduğunu gösterir. Alıcının gerçek kimliği, yetkisi, task'ın gerçekten gönderildiği veya yetkili bir response alındığı sonucu üretilmez. Birlikte değiştirilip yeniden hash'lenen tutarlı bir capsule yapısal kontrolden geçebilir. İmza, attestation, anti-replay veya producer authentication mekanizması yoktur.

Phase42'den alınan binding_digest current register6465, manifestfbe9 veya parent slots291 hash'iyle yeniden türetilmez. Orijinal Phase40 preimage'ı yoktur. Eşit kopya ve iç tuple ilişkisi original binding kriptografisi, task membership/necessity, component ownership veya fiziksel source dosyası kimliği değildir. Source truth, missing'in güncel fiziksel doğruluğu, observation freshness ve source locator doğrulanmaz.

Dış inspector yalnız yeni capsule/index/receipt/summary/manifest beşlisini okur; kaynak Phase42 beşlisini açmaz. `five_new_task_exchange_outputs_and_capsule_internal_correspondence_only` kapsamındaki content_consistent yalnız bu dosya ilişkileridir. Dokuz yerel işlem sınırı false kalır: original_Phase42_files_read, task_dispatched, analyst_assigned, candidate_response_processed, source_observation_verified, source_producer_verified, recipient_authorized, human_acceptance_verified, second_host_acceptance_performed. Bunlar kaynakta olmayan17 workflow alanının mirası değildir.

## Arşiv ve teslim ayrımı

İç capsule recipient yapısal doğrulaması içindir ve kendi içinde nested ZIP içermez. Dış kaynak ZIP yeni15 kaynak/belge + gerçek6 operational output'u taşır; bu nedenle iç capsule da dış ZIP'in operasyonel üyelerinden biridir. Dış ZIP portable capsule'ın imzası veya recipient kabulü değildir. Dört source/asset/delivery/closure metadata dosyası dış ZIP'in dışında tutulur; self-hash döngüsü kurulmaz. Fiziksel worktree prefix'i dış ZIP'e taşınmaz; logical security-platform/... kullanılır.

Gerçek ikinci host ve analist alımı; recipient authentication/authorization; filled candidate/decoder/submission; source observation/evidence; producer identity/signing/anti-replay/trusted timestamp; assignment/acceptance/completion; hostile/modified ZIP/JSON/limit/permission/crash/partialwrite/repeatdeterminism; Phase31 guard/compiler/module closure/ownership/native/human/legal/customer/production/release/Phase19 UI **NOT_RUN**'dır. Gerçek iki CLI ve dar manuel inceleme sonuçları yalnız [DEMO_DELIVERY](DEMO_DELIVERY.tr.md) içinde sonradan ölçülerek kaydedilir.
