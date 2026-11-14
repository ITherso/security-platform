# Phase38 source doğrulaması ve co-reference güven sınırı

**OFFLINE DEMONSTRATION — DISCLOSED CO-REFERENCE ONLY — NO PHYSICAL FILE OR SOURCE RELATIONSHIP VERIFIED**

Source grubu beş gerçek Phase37 dosyasıdır. Yeni `source_index_sha256` ve `source_manifest_sha256`, bu dosyaların byte kimlikleridir; embedded eski Phase36/35 provenance hash'leri değildir. Beş descriptor sabit ad/byte/SHA256/schema taşır; Markdown schema null. Global eski inbox/bloke sayımları yeni receipt'e kopyalanmaz, source counts yalnız altı visible index sayımıdır.

## Owner ve immutable snapshot sınırı

Adapter gerçek dört payload'ın raw manifest byte/hash bağını kontrol eder; mevcut Phase37 üç model/cross-relation validator'larını uygular; immutable `ValidatedFileIndex` ve old pure lookup/receipt yeniden üretimi ile model eşliği; owner Markdown ve manifest byte eşliği sağlar. Ancak sonra exact frozen `ValidatedPhase37Source` kullanılabilir. Constructor ve public read aynı immutable gerçek byte'ları yeniden doğrular; mutable cache/trusted token otoritesi yoktur.

Old `ValidatedFileIndex` canonical in-memory modeli source-bound query için kullanılır; gerçek source identity bu serialize edilmiş byte'lardan uydurulmaz, açık dosyaların gerçek descriptor'larından gelir. Yeni `ValidatedCoReferenceJoin` direct constructor'ı yalnız kapalı wire iç bütünlüğünü doğrular; özgün source/prodüktör kanıtı değildir. Source-bound lookup aynı gerçek source grubundan join'i yeniden türetip karşılaştırır. Caller'ın validated/allow/trusted işareti yeterli değildir.

Yeni iş mantığı saf metadata üzerinde çalışır. Disk erişimi adapter/CLI/publisher sınırındadır; Phase36 dosyaları, Phase35 CSV, kapsül, guard, Rust veya eski CLI açılmaz. JSON içindeki path/URL başka input okuma yetkisi değildir. Yeni guard/evaluator/resolver veya graph framework kurulmaz.

## Yeni inspector'ın sınırı

Inspector yalnız beş yeni join/lookup/receipt/summary/manifest dosyasını okur. Pair tekilliği, visible set kesişimi, iki file için gerçek temsil edilen supporting binding, join shared packet ve lookup bütün projection eşliği, reference tekilliği, source digest/schema, source/join/lookup counts, nested flag/Markdown ve dört payload manifest byte bağı incelenir. Tam request'in request_reference kaydı manifesttedir; üç modelde sahte/default local ID eklenmez.

`reference_packets` yalnız shared union'ın full provided paketlerini taşıyan açık wire ekidir; yeni inspector'ın all-or-nothing iç kontrolü içindir. Phase37 inputları yeniden açılmadığından source co-reference ilişkilerinin özgün kaynaktan bağımsız yeniden doğrulanması değildir. `content_consistent` yalnız beş yeni dosyanın iç tutarlılığıdır. Source import/CSV/kapsül/guard/native/producer veya source freshness doğrulanmış sayılmaz.

Receipt `five_Phase37_artifact_internal_correspondence_only` kapsamındadır. Hash'ler imza veya Git/producer attestation değildir; saldırgan bütün tutarlı girdileri değiştirebilir ve hash'leri yeniden oluşturabilir. File ID fiziksel inode/Windows identity/path değildir. Ortak görünür referans fiziksel/content/security/causal/source/compiler/ownership bağı veya release yetkisi oluşturmaz.

## Portatif kod, limit ve açık kabuller

Yeni kaynak delta paketi standalone binary veya production wheel değildir. Korunmuş Phase37 owner index/lookup/renderer/manifest ve eski kapalı wire/güvenli okuma kodu gerekir; bu kod bağımlılığı eski runtime/veri/CSV/kapsül açmak değildir. Yeni ZIP eski dependency kaynaklarını veya önceki input/arşivleri kopyalamaz. Gerçek ikinci offline host aktarım/çalıştırma kabulü NOT_RUN'dır; import graph kaynak incelemesi bu kapıyı geçmez.

Request 32 KiB; source index/lookup/receipt 256/128/64 KiB, MD 128 KiB/manifest 64 KiB; toplam input 1 MiB. Join 256 KiB, lookup/MD 128 KiB, receipt/manifest 64 KiB; requested file 2–8/pair 28/reference 8/projection 64/depth 12/node 20.000/text 512. Owner daha sıkı sınırı korunur. Strict UTF-8/JSON, duplicate/unknown schema/field/enum/type, float/NaN/Infinity/bool-as-int ve invalid digest/binding reddi; truncate/overwrite/otomatik silme/partial-write başarısı yoktur.

Nested kapalı trust_flags içinde aynı 18 false alan ve demo_only true korunur. Source/context/independent observation, upstream guard, producer/ownership/release/production değerleri olumluya yükselmez. Eski fresh kodu yeni gözlem veya TTL garantisi değildir. Minimizasyon anonimlik/şifreleme değildir.

Hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible file, no-shared pair, shared-file multiple-reference, duplicate/çelişkili binding/sahte shared ref, modified index, limit/permission/crash/partial write/repeat determinism/ikinci host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release kabulü gerçekten çalıştırılmadıkça NOT_RUN kalır. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir; file:// kısıtı aşılmaz. Actual kapsam ve kimlikler teslim kaydındadır.
