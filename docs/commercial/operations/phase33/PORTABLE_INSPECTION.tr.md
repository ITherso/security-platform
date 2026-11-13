# Phase33 bağımsız kapsül inceleme ve lookup

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

Portatif inspector yalnız açıkça verilen kapsül ZIP'ini okur ve diske çıkarmaz. Kaynak repository, Phase31/32 araçları, özgün kaynak dosyalar veya eski artefact'lar iç inceleme/lookup için gerekmez. Gerekli dört yeni yerel modül `inspect_capsule.py`, `capsule_contracts.py`, `capsule_manifest.py`, `capsule_renderer.py` ve Python standart kütüphanesidir; bunlar aynı dizinde bulunmalıdır. Bu bir standalone binary veya production wheel değildir.

## Kontrol edilen kapalı kapsam

ZIP'in tam dört beklenen üyesi olmalıdır: `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt`. Duplicate/bilinmeyen üye, traversal, symlink, encrypted ZIP veya desteklenmeyen compression kapalı hatadır. ZIP 256 KiB; üye 128 KiB; expanded toplam 256 KiB; ratio 20; reference 8; projection 64; depth 12; node 20.000; text 512 sınırları uygulanır. Limit aşımında truncation yoktur.

Inspector inner manifestteki üç gerçek payload byte/SHA256 bağını; capsule strict modelini, unique ID ve projection-reference bağlarını; bloke referansın boş projection listesini; yeniden türetilen Markdown byte eşliğini; sabit README byte eşliğini ve 18 false güven alanını inceler. Manifest kendi hash'ini içermez. JSON ve metin strict UTF-8'dir; duplicate/unknown key/version ve geçersiz sayılar reddedilir.

Kaynak bindings içindeki SHA256 ve sözleşme kimlikleri yalnız kapsülün eski metadata bağlarıdır. Inspector bu dosyalara erişmez; modelin bir üretici veya insan tarafından yetkili biçimde hazırlandığını kanıtlamaz. Yalnız kapsülün kendi iç byte/model bütünlüğünü değerlendirebilir. Kaynak hash'i bir imza veya attestation değildir.

## Açık reference lookup

Kullanıcı `--lookup-reference` ile 1–8 farklı ID verir. Lookup yalnız kapsülde bulunan kayıtları kullanır. Unknown veya duplicate ID reddedilir. `termivar-offline-reference-capsule-lookup/v1` sonucu kapsüldeki disclosure durumunu ve yalnız izinli projection'ları korur; başka ZIP veya source path açmaz.

`withheld_by_existing_guard` sonucu lookup'ta görünür ancak `projections=[]` kalır. Olumlu alt candidate hash/size bilgisi geri getirilmez. Kayıtlı yokluk byte/hash `null`; otomatik sıfır veya başarılı source observation değildir. Lookup yeni guard veya kaynak freshness kararı üretmez.

İkinci ürün çağrısı yalnız ilk assembly exit 0, eksiksiz dört gerçek çıktı ve manuel inceleme sonrası izinlidir. Inspector yalnız ürün kapsülünü okumalı; dış assembly summary/source-bindings/manifest, Phase32 dosyaları veya eski CLI'lar yeniden açılmamalıdır. İki açık output path inspection ve lookup dosyalarının yazılacağı yerlerdir; okunacak başka input değildir.

## Sonuçların pratik sınırı

`source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`; diğer Phase32 güven bayrakları da false kalır. Kayıtlı `fresh_*` kodu şimdi dosyanın aynı kaldığını söylemez. İç bütünlük; producer kimliği, gerçek kullanıcı yetkisi, özgün guard doğruluğu, güncel source durumu, compiler/module closure, ownership, native/runtime veya insan/hukukî/müşteri/release kabulü değildir.

Bu kullanım belgesi portatif inspector'ın gerçekten çalıştığının kanıtı değildir; actual çağrı ve çıktı kimlikleri yalnız teslim kaydında tutulur. Gerçek demo sonrasında yalnız gözlenen üç lookup sonucu ve iç bütünlük raporlanabilir. Hostile/duplicate JSON, invalid UTF-8, değiştirilmiş kaynak/sahte guard/unknown status/enjekte projection/yanlış ID, duplicate ZIP/ZIP bomb/ratio/symlink/traversal/bozuk manifest/limit, crash/partial write/power loss ve repeat determinism NOT_RUN kalır. Test/runner/coverage/typecheck/build/install yapılmaz. Phase19 UI kabulü için tarayıcı kısıtına workaround uygulanmaz.
