# Phase37 gerçek source grubu ve güven sınırı

**OFFLINE DEMONSTRATION — DISCLOSED METADATA ONLY — NO CURRENT SOURCE VERIFICATION**

Yeni input grubu beş gerçek Phase36 dosyasıdır: typed inbox, reference query, import receipt, inbox summary, manifest. Yeni source kimlikleri bu dosyaların gerçek byte/SHA256/schema bağlarıdır. Inbox içindeki eski Phase35 provenance descriptor'ları bu inputların yerine geçirilmez; eski CSV veya kapsül açılmaz.

## Kaynak owner doğrulaması

Önce beş dosya bounded güvenli okuma ile alınır ve manifestin gerçek dört payload bağı incelenir. Phase36 mevcut üç model/cross-relation validator'ları kullanılır. Mevcut `ValidatedInbox(raw_bytes)` ve `read_typed_inbox` exact immutable typed modeli doğrular; `build_reference_query` ve `build_import_receipt` kayıtları inbox'tan yeniden türetir. Mevcut `render_inbox_summary` ve owner manifest fonksiyonuyla gerçek byte/model eşliği aranır. Yalnız bundan sonra immutable `ValidatedPhase36Source` kullanılabilir.

`ValidatedInbox` tek başına beş eski dosyanın doğrulandığı anlamına gelmez; yeni adapter bu group bağını ayrıca kurar. Immutable source snapshot beş gerçek byte dizisini tutar, constructor ve public `read_source` bunları owning model/renderer/manifest ile yeniden doğrular. Return değeri tam eski validated inbox modeli ve beş gerçek artefact descriptor'ıdır; eski query sonucu tam inbox sayılmaz. Caller'ın `validated=true`/`trusted=true`/`allow=true` işareti otorite değildir.

Yeni pure index builder tam source grubundan yalnız provided reference paketlerini alır; mevcut Phase36 `query_reference_metadata` her referansın bütün izinli projection'larını sağlar. File kayıtları bu modelden türetilir. Disk erişimi adapter/CLI/publisher sınırındadır; index ve lookup kaynak CSV/kapsül/guard/native dosyası keşfetmez. JSON URL/path yeni input yetkisi değildir.

## Receipt ve yeni inspector

Source receipt dosya adı, byte/SHA256/schema, gerçek source inbox/manifest digest'leri ve aggregate source/index counts taşır. `five_Phase36_artifact_internal_correspondence_only` scope'u producer veya source freshness kanıtı değildir. Receipt'e olumlu bloke metadata veya full source model ikinci kopya olarak eklenmez.

Yeni inspector yalnız beş yeni index/lookup/receipt/summary/manifest dosyasını okur. Üç kapalı model, file/reference/candidate bağları, whole-reference paketleri, request/source digest'leri, null/absence/count ayrımı, sayımlar, receipt, yeniden türetilen Markdown ve dört gerçek payload manifest byte eşliği incelenir. Phase36 input dosyaları yeniden açılmaz ve source import davranışı bağımsız doğrulanmaz. `content_consistent` yalnız bu yeni çıktıların iç tutarlılığıdır.

Saldırgan bütün tutarlı girdileri değiştirip hash'leri yeniden oluşturabilir; byte/hash/model eşliği imza, producer authentication veya yetkili kaynak kanıtı değildir. Source file metadata indekslenmesi yeni gözlem, module resolution, ownership veya release kabulü oluşturmaz. File ID fiziksel inode/Windows file identity/path değildir.

## Kod bağımlılığı ve açık kabuller

Yeni kaynak delta paketi standalone binary veya production wheel değildir. Korunmuş Phase36 snapshot/query/receipt/renderer/manifest ve daha eski kapalı wire/güvenli okuma yardımcılarının kodu gerekir. Kod bağımlılığı eski runtime, data, CSV veya kapsüle erişim değildir. Yeni ZIP eski dependency kaynaklarını veya önceki veri/arşivlerini kopyalamaz. İkinci offline host'a gerçek aktarım/çalıştırma yapılmadıkça NOT_RUN'dır; import grafiği kaynak incelemesi runtime kabulü değildir.

Yeni common dört alanlıdır; nested kapalı `trust_flags` içinde Phase36'nın 18 false alanı korunur ve `demo_only=true` kalır. Source/context/independent observation/upstream guard, producer/ownership/release/production false değerleri yükselmez. Compiler/module closure, native, insan/hukukî/müşteri ve release otoritesi kazanılmaz. Kayıtlı upstream fresh kodu source freshness/TTL garantisi değildir.

Request 32 KiB; source inbox/query/receipt 256/128/64 KiB, MD 128 KiB/manifest 64 KiB; toplam 1 MiB. Index 256 KiB, lookup/MD 128 KiB, receipt/manifest 64 KiB; reference 8/projection/visible file 64/requested File ID 8/depth 12/node 20.000/text 512. Owner daha sıkı sınırı, strict UTF-8/JSON, duplicate/unknown type/field/schema ve invalid integer/float/bool-as-int reddi korunur. Yeni/boş output; truncation/overwrite/otomatik silme ve partial-write başarısı yoktur.

Hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible File ID, duplicate/çelişkili projection, yanlış relation, single-file ve shared-file multiple-reference, modified inbox, limit/permission/crash/partial write/repeat determinism/ikinci host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release kabulleri gerçekten çalıştırılmadıkça NOT_RUN kalır. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir; file:// yasağı korunur. Actual komut/kimlik/gözlemler teslim kaydındadır.
