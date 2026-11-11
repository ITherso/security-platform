# Phase28 entry-point sözleşmesi

**DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED**

Bağımsız araç, açık Cargo target bildirimlerini izinli yerel dosya kimlikleriyle ve korunmuş Phase24 F kataloğuyla karşılaştırır. Phase27 dependency grafiğini yeniden üretmez; eski envantere yazmaz. Çalışma modu yalnız `demo`dur.

## Sürümlü belgeler

| Belge | Sözleşme | Sorumluluk |
| --- | --- | --- |
| Scope | `termivar-offline-entrypoint-coverage-scope/v1` | Açık eski artefact, manifest ve target dosyası izinlerini bağlar. |
| Coverage | `termivar-offline-entrypoint-coverage/v1` | Manifest → explicit target → allowlist → gözlenen dosya kimliği → F kapsamı zincirini gösterir. |
| Delta | `termivar-offline-source-scope-delta/v1` | Kaynak destekli, uygulanmamış repository-level inclusion önerilerini tutar. |
| Varyant | `termivar-offline-variant-entrypoint-projection/v1` | Mevcut Phase26 seçimlerini kesin ve belirsiz target ilişkileriyle açıklar. |

Yerel target/dosya/öneri referansları global package, executable veya release kimliği değildir. Kaynak root, pin, manifest, normalize relative path ve gözlenen byte/hash bağları ayrı korunur. Aynı path farklı root veya kaynak kimliğinde otomatik aynı dosya sayılmaz. Bildirilen pin, Git commit veya üretici attestation sağlamaz.

## Girdi ve çıktı sınırları

| Okunan veya üretilen veri | Tavan |
| --- | ---: |
| Scope JSON | 128 KiB |
| Her Phase24/26/27 JSON girdisi | 2 MiB |
| Her kaynak/çıktı manifesti | 128 KiB |
| Her Cargo manifesti | 256 KiB |
| Her target kaynak dosyası | 512 KiB |
| Toplam target-source okuması | 1 MiB |
| Toplam açık girdi okuması | 12 MiB |
| Her yeni JSON | 2 MiB |
| Markdown | 256 KiB |

Target hash okuma parçaları en fazla 64 KiB'dir; tam kaynak gövdesi çıktı veya bellekteki sonuç modeline alınmaz. Manifest ve target-source bütçeleri ayrıdır. CLI main.rs için bildirilen 279.631 bayt, manifest 256 KiB tavanıyla değerlendirilmez; gerçek okuma kendi 512 KiB sınırına tabidir.

En fazla 16 Cargo manifesti, 32 açık target dosyası/64 allowlist binding, 64 target declaration, 512 F referansı, 64 component, 4 varyant ve 64 öneri kabul edilir. Aynı kaynak dosyası yalnız aynı root/pin/path, beklenen hash, limit ve okuma türüyle farklı target'lara bağlanabilir. Bir EPF referansı yerel dosya gözlemidir; yeni Phase24 F satırı değildir. Aşımda ilk N kaydı döndürerek tam başarı üretilmez. Strict JSON graph sınırları derinlik 16, node 120.000, toplam metin 2 MiB ve tek dize 2048 karakterdir; array boyutları ayrıca alan bazında sınırlıdır.

Strict UTF-8, duplicate key, NaN/Infinity, boolean-as-integer, yanlış tür, bilinmeyen sürüm, duplicate kimlik ve geçersiz referans reddedilir. Kaynak/root/pin veya manifest hash uyuşmazlığı ve okuma sırasında kimlik değişimi doğrulanmış dosya sonucu oluşturamaz. Yeni çıktı dizinine exclusive yazılır; eski dosyalar silinmez veya üzerine yazılmaz.

## Sonuçların sınırı

Target bildirimi, explicit path, dosya varlığı, SHA256, F membership, component ownership, proposal, build ve release birbirini otomatik doğrulamaz. `read_not_performed`, dosya yokluğu değildir. Eksik bilgi sağlıklı/başarılı varsayılmaz.

`demo_only=true`; inventory update, delta application, component ownership, dependency closure, build/runtime, producer/human review, lisans incelemesi, redistribution, release ve production güven bayrakları false kalır. Her önerinin uygulama yetkisi ve uygulandı bilgisi de false'tur.

Inspector yalnız üç yeni JSON, Markdown ve manifestin iç tutarlılığına bakar. Eski artefact veya gerçek native dosyaları bağımsız yeniden okuduğunu iddia etmez. `content_consistent`, kaynak otoritesi, successful build veya release kabulü değildir. Gerçek komut sonuçları ve açık kapılar [teslim kaydında](DEMO_DELIVERY.tr.md) tutulur.
