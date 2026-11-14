# Offline disclosed co-reference join

**OFFLINE DEMONSTRATION — DISCLOSED CO-REFERENCE ONLY — NO PHYSICAL FILE OR SOURCE RELATIONSHIP VERIFIED**

Bu yeni offline araç açık 2–8 metadata File ID'nin görünür referans kümelerinden her benzersiz çift için kesişim ve gerçek supporting projection binding'leri üretir. Ortak provided referansların bütün izinli projection'ları tekilleştirilmiş lookup'ta birlikte döner. Mevcut ters indeksi yeniden üretmez, yeni graph/guard/evaluator/resolver veya risk skoru oluşturmaz.

**2026-11-14** tarihinde iki izinli Phase38 çağrısı tamamlandı: co-reference assembly **exit 0**, içerik inspector'ı **exit 0**. Bütçe **2/2 tüketildi ve kapandı; kalan 0**. Gerçek iki visible File ID **1 shared pair / 1 shared provided referans / 2 supporting binding (2 unique)** üretti. Lookup aynı referansı bir kez ve bütün **2 projection (1 kayıtlı present/1 absence)** ile döndürdü. Bu yalnız mevcut görünür metadata co-reference ilişkisidir; fiziksel/content/security/causal/source/compiler ilişkisi kanıtı değildir.

Altı gerçek çıktı `outputs/phase38-co-reference/` altında üretildi; tam byte/SHA256 kimlikleri, gerçek supporting üçlüler ve gözlemler [teslim kaydındadır](../../docs/commercial/operations/phase38/DEMO_DELIVERY.tr.md). Üretim source commit'i `1f6b6f57ee9151769dac5cc7181a6a8fa887de6a`, tree `51e2427ba2b4093d17e54d25940809f723fda86d`. Üretim sonrası yalnız README ve teslim belgesi actual sonuçlarla güncellendi; dokuz kod/örnek dosyası ve diğer üç belge değişmedi.

## Gerçek source bağı ve saf API

Yalnız beş açık Phase37 input'u: `file-reference-index.json`, `file-reference-lookup.json`, `index-source-receipt.json`, `file-index-summary.md`, `manifest.json`. Yeni source index/manifest SHA256 bu dosyaların gerçek byte kimlikleridir; eski embedded Phase36/35 hash'leri değildir. Owner strict model/cross-relation, yeniden türetilen Markdown ve gerçek dört payload manifest byte eşliği sağlanmadan join çalışmaz. Builder/manifest tek başına validator değildir.

Adapter exact frozen `ValidatedPhase37Source` içinde beş gerçek byte dizisini tutar; constructor/read owning doğrulamayı tekrar yapar, public `read_source` tam eski validated index modeli ve beş gerçek schema/byte/SHA256 descriptor'ı döndürür. İş mantığı fiziksel I/O yapmaz. Caller'ın trusted/validated/allow alanı otorite değildir. Eski Phase36 dosyası, CSV, kapsül, guard/native source veya eski CLI açılmaz.

`build_co_reference_join(validated_index, requested_file_ids)` içindeki validated_index gerçek beş-dosya source grubudur; caller dict'i veya yalnız canonical model hash'i değildir. Mevcut Phase37 `ValidatedFileIndex` ve `lookup_disclosed_files` kullanılarak yalnız gerçek visible file kümeleri ve bütün provided paketler alınır. Her benzersiz çift lexicographic sıralanır, kesişim gerçek left/right projection üçlüleriyle desteklenir. Kaynakta olmayan projection ID veya benzer isim/hash üzerinden ilişki üretilmez.

`build_co_reference_lookup(validated_index, validated_join)` aynı gerçek source grubuna bağlı immutable join'i yeniden doğrular; yalnız shared reference union'ının bütün izinli paketlerini döndürür. Referans birden fazla çiftte bulunsa da bir kez döner. İstenen dosyalara göre projection filtrelenmez. Yeni join constructor'ının internal wire doğrulaması tek başına özgün source/producer kanıtı değildir.

## Kapalı sözleşmeler ve disclosure

Request `termivar-offline-co-reference-request/v1` tam altı alan: `schema_version`, `mode`, `request_reference`, gerçek `source_index_sha256`, gerçek `source_manifest_sha256`, `requested_file_ids`. Yalnız demo; 2–8 farklı biçimsel File ID. Duplicate, yanlış digest, unknown schema/field reddedilir. Override/include-blocked/force-match/yeni candidate/reference/path/risk bilgisi yoktur. Yerel request_reference yalnız dış manifestin tam request kaydındadır; üç ürün modeline sahte/default kimlik eklenmez.

Join `termivar-offline-disclosed-co-reference/v1`; lookup `termivar-offline-co-reference-lookup/v1`; receipt `termivar-offline-co-reference-source-receipt/v1`. Common schema/demo label/demo_only true ve nested exact 18 false trust_flags'tır. Join'in açık `reference_packets` eki yalnız ortak referansların bütün mevcut beş-alan provided paketlerini taşır; yeni beş-dosya inspector'ının whole-packet kontrolü için kullanılır. Unshared full catalog, bloke ID/metadata veya eski global bloke sayımları kopyalanmaz. Source counts yalnız Phase37 visible index'in altı paydasıdır.

File sonucu matched veya ortak `not_in_disclosed_index`. Pair sonucu `shared_disclosed_reference`, `no_shared_disclosed_reference`, `not_in_disclosed_index`. Son iki durum fiziksel yokluk, blokeli kayıtta varlık, başka source'ta ilişkisizlik veya farklı fiziksel dosya kanıtı değildir. Shared sonuç yalnız iki görünür file'ın gerçek provided referans kesişimidir. `files_share_disclosed_reference ≠ same_physical_file`.

Supporting binding gerçek `(reference_id,candidate_id,file_id)` üçlüsüdür. Bir çift içinde duplicate reddedilir. Aynı üçlü farklı gerçek çiftleri destekleyebilir; occurrence sayımı ile unique binding sayımı ayrıdır. Lookup result tam dört alan taşır: reference ID/disclosure status/matched file ID'ler/bütün 11-alan projection listesi. Null/absence ve kaynak tür/değerler korunur; sayısal count sıfırı sıfır-byte dosya veya null değildir.

## Tamamlanan exact iki ürün çağrısı

Aşağıdakiler gerçek generation kaydındaki tamamlanmış iki çağrıdır; yeniden çalıştırma izni değildir. İkinci, ilk exit 0 ve eksiksiz beş output'un gerçek join/lookup/receipt/MD manuel incelemesinden sonra çalıştı. Actual exit kodları **[0,0]**, kapalı **2/2 bütçe**, kalan çağrı **0**. Retry/üçüncü/preflight helper/test runner/eski CLI tekrarı yoktur. Phase20–37 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_co_reference/assemble_co_reference.py --index outputs/phase37-file-reference-index/file-reference-index.json --source-lookup outputs/phase37-file-reference-index/file-reference-lookup.json --receipt outputs/phase37-file-reference-index/index-source-receipt.json --source-summary outputs/phase37-file-reference-index/file-index-summary.md --source-manifest outputs/phase37-file-reference-index/manifest.json --request security-platform/tools/commercial_co_reference/examples/demo_co_reference_request.json --output-dir outputs/phase38-co-reference
```

```text
python -I -B security-platform/tools/commercial_co_reference/inspect_co_reference.py --join outputs/phase38-co-reference/co-reference-join.json --lookup outputs/phase38-co-reference/co-reference-lookup.json --receipt outputs/phase38-co-reference/co-reference-source-receipt.json --summary outputs/phase38-co-reference/co-reference-summary.md --manifest outputs/phase38-co-reference/manifest.json --output outputs/phase38-co-reference/inspection-summary.json
```

Assembly ilk beş output'u üretti. Manifest gerçek ilk dört payload'ı ve tam request'i bağlar; kendisini/inspection çıktısını kapsamaz. Inspector `internal_content_status=content_consistent`, kapsam `five_new_co_reference_outputs_internal_correspondence_only` raporladı. `original_Phase37_files_read=false`, `source_co_reference_independently_verified=false`, `source_import_independently_verified=false`, `source_capsule_read=false`; yalnız beş yeni dosyanın internal model/pair/binding/full-packet/MD/manifest ilişkisidir. Source co-reference, import, producer veya fiziksel/source/compiler ilişkisinin bağımsız doğruluğu değildir.

Gerçek source sayımları yalnız görünür altı paydaydı: 2 file / 1 reference / 2 candidate / 2 projection / 1 present / 1 absence. Bloke ID/metadata veya eski global bloke sayımları yeni ürün kayıtlarına taşınmadı. Lookup'un bütün projection listesi join'deki shared source paketiyle eşleşti; absence byte/hash JSON null kaldı. Nested 18 false flag ve demo-only true korundu. No-shared, unknown/nonvisible, multi-reference veya adversarial runtime varyantı çalıştırılmadı.

## Limitler, bağımlılıklar ve NOT_RUN

Request 32 KiB; source index/lookup/receipt 256/128/64 KiB, MD 128 KiB, manifest 64 KiB; toplam açık input 1 MiB. Yeni join 256 KiB, lookup/MD 128 KiB, receipt/manifest 64 KiB. Requested file 2–8, pair 28, reference 8, projection/visible file 64, depth 12/node 20.000/text 512. Daha sıkı owner limitleri korunur. Strict UTF-8/JSON, duplicate/unknown schema/field/type, float/NaN/Infinity/bool-as-int, wrong digest/binding reddi. Yeni/boş output; truncate/overwrite/otomatik silme ve partial-write başarısı yoktur. JSON path/URL yeni input yetkisi değildir.

Yeni delta paket standalone binary veya production wheel değildir; korunmuş Phase37 index/lookup/renderer/manifest ve eski kapalı wire/güvenli okuma koduna bağlıdır. Kod bağımlılığı eski runtime/veri/CSV/kapsül erişimi değildir. Yeni kaynak ZIP'i eski dependency kodunu veya önceki input/ZIP'lerini kopyalamaz. İkinci offline host kabulü NOT_RUN'dır. Backend/operator-console/DB/GUI/API/servis/scheduler entegrasyonu yapılmaz.

18 nested false trust flag ve demo_only true korunur. Co-reference, physical/content/security/causal/source/compiler/ownership ilişki kanıtı değildir. Producer/source freshness/guard/native/human/legal/customer/production/release yetkisi kazanılmaz. Eski fresh kodu yeni observation/TTL garantisi değildir. ID/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.

NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible File ID, no-shared çifti, shared-file multiple-reference, duplicate/çelişkili binding/sahte shared-reference, modified index, limit/permission/crash/partial write/repeat determinism/ikinci host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Kodda koruma runtime kabulü değildir. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir; file:// kısıtı aşılmaz.

Belgeler: [sözleşmeler](../../docs/commercial/operations/phase38/CO_REFERENCE_CONTRACT.tr.md), [join ve disclosure](../../docs/commercial/operations/phase38/JOIN_AND_DISCLOSURE.tr.md), [güven sınırı](../../docs/commercial/operations/phase38/TRUST_BOUNDARY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase38/DEMO_DELIVERY.tr.md).

Kaynak teslim adı `Termivar-Offline-Co-Reference-phase38-2026-11-14.zip`. Ölçülen ZIP boyut/üye/SHA256 kimliği [delivery manifestinde](../../../outputs/phase38-co-reference-delivery-manifest.json); kaynak kimlikleri [source manifestte](../../../outputs/phase38-co-reference-source-manifest.json), nihai durum [closure kaydında](../../../outputs/phase38-delivery-closure.json) tutulur. Bu dış kayıtlar öz hash döngüsünü önler. Phase7–37, backend/operator-console/native/HBF/Altay/auth/DB/roller/wheel/lock/lisans korunur. İzinli iki çağrı tamamlandı; Phase39/yeni mikro özellik/native/otomatik test/release başlatılmaz.
