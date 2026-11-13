# Offline disclosed file index ve reverse reference lookup

**OFFLINE DEMONSTRATION — DISCLOSED METADATA ONLY — NO CURRENT SOURCE VERIFICATION**

Bu yeni offline araç doğrulanmış Phase36 typed inbox'taki yalnız provided referansların mevcut File ID ilişkilerini indeksler. Yeni yetenek File ID → görünür referanslar → her eşleşen referansın bütün izinli projection paketidir. `lookup_disclosure ⊆ validated_inbox_disclosure`. Aynı referans birden fazla istenen File ID ile eşleşse bile bir kez döner; hangi File ID'lerle eşleştiği ayrı kaydedilir.

Kaynak hazırlığında Phase37 ürün çağrısı **0**. Henüz indeks/lookup/receipt/inspector başarısı, yeni output veya ZIP boyutu/SHA256 iddia edilmez. Source beklentisi yeni ürün sonucu değildir. Tarih ve kaynak ZIP etiketi **2026-11-14**.

## Gerçek source grubu ve saf API

Yalnız beş açık Phase36 dosyası okunur: `typed-inbox.json`, `reference-query.json`, `import-receipt.json`, `inbox-summary.md`, `manifest.json`. Gerçek inbox/manifest SHA256 değerleri yeni source kimlikleridir; inbox içine kaydedilmiş önceki Phase35 artefact hash'leri onların yerine geçirilmez. Beş descriptor dosya adı/byte/SHA256/schema taşır; summary schema null'dır.

Dar adapter mevcut Phase36 validator'larını, exact `ValidatedInbox`/`read_typed_inbox`, `build_reference_query`, `build_import_receipt`, owner summary ve manifest eşliğini kullanır. Gerçek dört payload manifest bağı önce incelenir; üç model/query/receipt/MD ilişkileri başarılıysa immutable `ValidatedPhase36Source` oluşturulur. Caller'ın validated/trusted işareti otorite değildir. Phase35 CSV, kapsül, guard, native kaynak veya eski CLI açılmaz.

`build_disclosed_file_index(ValidatedPhase36Source) -> ValidatedFileIndex` yalnız provided referansların bütün kapalı paketlerini ve gerçek `(reference_id,candidate_id,file_id)` bağlarını alır. Projection ID uydurmaz. File kayıtları deterministik sıralanır; duplicate veya çelişkili metadata reddedilir. `ValidatedFileIndex` exact immutable byte snapshot'ıdır; public okuma kapalı wire modeli tekrar doğrular. `lookup_disclosed_files(validated_index, requested_file_ids)` ve schema wrapper `build_file_lookup` yalnız bu model üzerinde saftır.

Request `termivar-offline-disclosed-file-lookup-request/v1` tam altı alan taşır: `schema_version`, `mode`, `request_reference`, gerçek `source_inbox_sha256`, gerçek `source_manifest_sha256`, `requested_file_ids`. Yalnız demo; 1–8 farklı biçimsel File ID; duplicate veya yanlış digest kapalı hata. Biçimsel geçerli fakat görünür indekste olmayan ID aynı `not_in_disclosed_index` ve boş reference listesi verir. Bu durum fiziksel yokluk veya bloke kayıtta varlık hakkında neden vermez.

## İndeks, bütün referans paketi ve trust model

Index v1 görünür reference paketleri, file records, gerçek beş source identity, source/visible sayımları ve sınırlamaları taşır. File kaydı File ID, sorted unique reference/candidate listesi ve gerçek üçlü bindings'tir. Bloke/kapsam dışı referans indekse girmez; yalnız aggregate source sayımı kalabilir. Olumlu child hash/byte başka audit alanına kopyalanmaz. File ID metadata kimliğidir; gerçek inode/Windows File ID/path veya evrensel dosya kimliği değildir.

Lookup eşleşen referansı bütün mevcut 11-alan projection'larıyla tekilleştirir. Tek File ID eşleşmesi referansın diğer izinli projection'ını gizlemez. Mevcut source status/değer/null/türler değişmez. Reference/candidate/file/projection sayımları ve source/index/lookup paydaları ayrıdır. Absence null count sıfırından farklıdır; görünür absence File ID eşleşmesi gerçek fiziksel dosya varlığı değildir.

Yeni common wire `schema_version`, `demo_label`, `demo_only=true`, kapalı `trust_flags` nesnesidir. **18 false alan nested trust_flags içinde korunur**; top-level ikinci kopya/pozitif yükseltme yoktur. Receipt beş Phase36 identity/schema ve aggregate scope taşır; projection audit kopyası veya producer authentication değildir. Hash imza, source freshness, ownership veya release yetkisi değildir.

## Planlanan exact iki ürün çağrısı

Aşağıdakiler henüz çalışmış başarı kaydı değildir. İlk çağrı exit 0, eksiksiz beş output ve gerçek index/lookup/receipt/MD manuel incelemesi sonrası ikinci çalışır. Phase37 en fazla iki yeni çağrı; başarısız çağrı tüketilir, retry/üçüncü/preflight helper/test runner/eski CLI yoktur. Phase20–36 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_file_reference_index/assemble_file_index.py --inbox outputs/phase36-tabular-inbox/typed-inbox.json --source-query outputs/phase36-tabular-inbox/reference-query.json --receipt outputs/phase36-tabular-inbox/import-receipt.json --source-summary outputs/phase36-tabular-inbox/inbox-summary.md --source-manifest outputs/phase36-tabular-inbox/manifest.json --request security-platform/tools/commercial_file_reference_index/examples/demo_file_lookup_request.json --output-dir outputs/phase37-file-reference-index
```

```text
python -I -B security-platform/tools/commercial_file_reference_index/inspect_file_index.py --index outputs/phase37-file-reference-index/file-reference-index.json --lookup outputs/phase37-file-reference-index/file-reference-lookup.json --receipt outputs/phase37-file-reference-index/index-source-receipt.json --summary outputs/phase37-file-reference-index/file-index-summary.md --manifest outputs/phase37-file-reference-index/manifest.json --output outputs/phase37-file-reference-index/inspection-summary.json
```

Assembly ilk beş output'u üretir: index, lookup, source receipt, summary, manifest. Manifest gerçek ilk dört payload'ı bağlar; kendisini kapsamaz. Inspector yalnız beş yeni açık dosyanın model/bağ/whole-reference/count/receipt/MD/manifest iç tutarlılığını değerlendirir. Phase36 dosyalarını tekrar açmaz, source import davranışını veya eski guard/kapsül doğruluğunu bağımsız kabul etmez. `content_consistent` yalnız bu yeni çıktılardır.

## Sınırlar, bağımlılık ve NOT_RUN

Request 32 KiB; gerçek Phase36 source inbox/query/receipt sırasıyla 256/128/64 KiB, MD 128 KiB, manifest 64 KiB; toplam açık girdi 1 MiB. Yeni index 256 KiB, lookup/MD 128 KiB, receipt/manifest 64 KiB; source reference 8, görünür projection/file 64, istenen File ID 8, depth 12/node 20.000/text 512. Owner daha sıkı limitleri korunur. Strict UTF-8/JSON, duplicate/unknown schema/field/type/ilişki, float/NaN/Infinity/bool-as-int/wrong digest reddi; yeni/boş output, overwrite/otomatik silme/truncation/partial-write başarısı yoktur. JSON URL/path yeni file-open yetkisi değildir.

Bu delta paket standalone binary/wheel değildir; korunmuş Phase36 owner snapshot/query/receipt/renderer/manifest ve eski kapalı wire/güvenli dosya yardımcı koduna bağlıdır. Bu kod bağımlılığı eski runtime/veri/CSV/kapsül erişimi değildir. Yeni source ZIP eski dependency kodu/veri/ZIP'lerini kopyalamaz. Gerçek ikinci offline host kabulü NOT_RUN'dır. Backend/operator-console/DB/GUI/API/server/watcher/scheduler entegrasyonu yoktur.

NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible File ID, duplicate/çelişkili projection veya yanlış reference/file/candidate bağı, tek File ID ile whole-reference runtime varyantı, shared-file multiple-reference, modified inbox, limit/permission/crash/partial write/repeat determinism/ikinci offline host; gerçek Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Demo iki gerçek File ID'yi birlikte sorgular; bu başka varyantların runtime kabulü değildir. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir; file:// tarayıcı kısıtı korunur.

Belgeler: [v1 sözleşmeleri](../../docs/commercial/operations/phase37/REVERSE_INDEX_CONTRACT.tr.md), [disclosure](../../docs/commercial/operations/phase37/DISCLOSURE_INTEGRITY.tr.md), [source/trust sınırı](../../docs/commercial/operations/phase37/SOURCE_AND_TRUST_BOUNDARY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase37/DEMO_DELIVERY.tr.md).

Kaynak teslim adı `Termivar-Offline-File-Reference-Index-phase37-2026-11-14.zip`. Ölçülmemiş boyut/üye/SHA256 uydurulmaz; final ZIP kimliği ayrı dış delivery manifestinde tutulur. Phase7–36, backend/operator-console/native/HBF/Altay/auth/DB/roller/wheel/lock/lisans korunur. İzinli iki çağrı, dar inceleme ve ölçülmüş teslim sonrası durulur; Phase38/yeni mikro özellik/native/otomatik test/release başlatılmaz.
