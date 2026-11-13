# Phase34 iki kapsülün portatif bütünlük ilişkisi

**OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION**

Kaynak ve derived kapsül ayrı açık ZIP dosyalarıdır. İlişki inspector'ı ikisini mevcut Phase33 güvenli inspect yolu ile ayrı ayrı inceler; ZIP'leri diske çıkarmaz. Phase31/32 artefact veya native kaynak dosyalarını açmaz, guard'ı yeniden çalıştırmaz. Aynı kapalı Phase33 formatı yeniden kullanılır; ikinci ZIP reader'ı kurulmaz.

## Sahip API ve karşılaştırma

Mevcut `inspect_bundle(raw_path, requested_ids)` `(inspection, lookup)` döndürür; bu çift capsule JSON'u sayılmaz. Dar adapter mevcut reader/validator/manifest/renderer/README doğrulamasından geçen immutable modelin alınmasını sağlar. Yeni iş mantığı yalnız doğrulanmış metadata üzerinde subset ve birebir eşitlik değerlendirir.

Her iki ZIP tam dört beklenen üye, byte/hash inner manifest, capsule v1 model, yeniden türetilen summary, sabit README ve mevcut false bayraklar bakımından kontrol edilir. Strict ZIP boyut/expanded/ratio/member kuralları korunur. Duplicate/unknown/path traversal/symlink/encrypted/unsupported compression kayıtları reddedilir. Kaynak parser'ın daha sıkı koşulları gevşetilmez.

İlişki kontrolü derived ID'lerin kaynak strict subset'i olmasını; her seçilmiş referansın status/karar/limitation/projection içeriklerinin aynı kalmasını; bloke referansların boş projection taşımasını; seçilmeyen metadata'nın yeni kapsülde olmamasını; ayrı toplam sayımları ve dış ledger/summary/manifest byte bağlarını değerlendirir. Sadece ZIP hash'lerini karşılaştırmak bu içerik ilişkisini kanıtlayamaz.

`internal_content_status=content_consistent` yalnız bu iki kapsülün iç byte/model bütünlüğü ve subset ilişkisidir. Kaynak üreticisi, imza, gerçek insan yetkisi, Phase31 guard doğruluğu, güncel source veya Rust module çözümü doğrulanmış sayılmaz.

## Kaynak ve derived kimlikler

Dış ledger kaynak ve derived ZIP'in gerçek byte/SHA256 kimlikleriyle ilişkilidir. Inner manifest kendi hash'ini içermez; dış manifest gerçek derived ZIP, ledger ve summary payload'larını bağlar. Ledger/summary projection payload'ı veya çıkarılan referansların olumlu alanlarını kopyalamaz. Source capsule hash'i producer attestation değildir.

Derived kapsül mevcut Phase33 portable reader ve `build_lookup(capsule, ids)` ile yalnız içinde bulunan seçilmiş referanslar için kullanılabilir. Bloke sonuç lookup'ta da sıfır projection taşır. Bu fazda ayrı eski CLI tekrar çağrısı için hak verilmez; yalnız iki yeni ürün komutu vardır. Türetilmiş kapsül tek başına özgün kaynağın köken kanıtı değildir; kaynakla ilişki incelemesi için iki kapsül birlikte gerekir.

Yeni araç kendi başına standalone binary veya production wheel değildir; korunmuş Phase33 owner modüllerine bağımlıdır. Kaynak teslim ZIP'i bu eski kodları, eski kaynak kapsülü veya native arşivleri otomatik kopyalamaz. İkinci offline host'a kopyalanmış modüllerle özgün source workspace yokken runtime kabulü yapılmadıkça NOT_RUN'dır. Import grafiğinin kaynak incelemesi bu ek kabulün yerine geçmez.

## Sınırlar ve açık kabuller

ZIP 256 KiB/üye 128 KiB/expanded toplam 256 KiB/ratio 20/tam dört üye/reference 8/projection 64/depth 12/node 20.000/text 512 owner limitleri; request 32 KiB/ledger 64 KiB/summary 128 KiB/toplam açık girdi 1 MiB ek limitleri korunur. Strict UTF-8, duplicate/unknown key/version, geçersiz sayılar ve bool-as-int reddi; truncation/overwrite yoktur. Yeni/boş output dizininde kısmi yazma başarı kabul edilmez.

`demo_only=true`, mevcut 18 false güven alanı; source/context/independent observation ve upstream guard doğrulaması false kalır. Compiler/module closure, ownership, producer/signature, native, insan/hukukî/müşteri/release kabulü kazanılmaz. Güncellik veya TTL garantisi yoktur.

Hostile/duplicate JSON/UTF-8, yanlış digest/ID, sahte veya çelişkili kapsül, blocked projection ve omitted metadata sızıntı saldırıları, duplicate ZIP/ZIP bomb/traversal/symlink/ratio/limit, permission/partial write/crash/power loss/repeat determinism, ikinci host/source-absence ve gerçek source freshness kabulü çalıştırılmadıkça NOT_RUN kalır. Test/runner/coverage/typecheck/build/install yapılmaz; Phase19 UI kabulü için tarayıcı kısıtı aşılmaz. Actual komutlar/sonuçlar ve byte kimlikleri yalnız teslim kaydındadır.
