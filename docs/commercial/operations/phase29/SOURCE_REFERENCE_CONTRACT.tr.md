# Phase29 kaynak referansı sözleşmesi

**DEMONSTRATION ONLY — RUST SOURCE REFERENCES — NO MODULE CLOSURE OR BUILD AUTHORIZED**

Bağımsız araç yalnız açık scope içindeki Rust dosyalarının sınırlı lexical referans metadata'sını üretir. Mode yalnız demo'dur. Kaynak metnindeki bir path yeni dosya okuma yetkisi vermez; başka dosyalar kendiliğinden keşfedilmez.

| Belge | Sözleşme | Sorumluluk |
| --- | --- | --- |
| Scope | `termivar-offline-rust-source-graph-scope/v1` | Eski artefact kimliklerini, EPF ve explicit source allowlist bağlarını seçer. |
| Ledger | `termivar-offline-rust-source-reference-ledger/v1` | Kaynak kimliği, lexical durum, gözlenen referans, koşul, tanı ve ayrı file-binding metadata'sını tutar. |
| Graph | `termivar-offline-rust-source-evidence-graph/v1` | Kesin, olası ve çözülemeyen kaynak ilişkilerini ayrı gösterir. |
| Coverage | `termivar-offline-module-coverage-projection/v1` | Global F membership ve korunmuş EPF/delta ilişkilerini module closure iddiası olmadan açıklar. |

Yeni modeller eski Phase24/27/28 modellerinin tam gövdesini kopyalamaz. Dar Phase28 source_context, EPF kimliği/target ilişkisi ve uygulanmamış delta referansları kullanılır. Kaynak gövdesi, serbest snippet veya macro argüman metni çıktı değildir. Referans kimliği source SHA256, sınırlı konum, tür ve lexical scope üzerinden yerel olarak bağlanır; derleyici sembol veya release kimliği değildir.

## Kesin tavanlar

| Veri | Tavan |
| --- | ---: |
| Scope JSON | 128 KiB |
| Her eski JSON / Markdown / manifest | 2 MiB / 512 KiB / 128 KiB |
| Bir Rust kaynak dosyası / toplam Rust okuması | 512 KiB / 1 MiB |
| Hash okuma parçası | 64 KiB |
| Toplam eski artefact okuması | 12 MiB |
| Her yeni JSON / yeni Markdown | 2 MiB / 256 KiB |
| Rust dosyası / kaynak referansı | 16 / 2048 |
| Lexical durum veya uyarı / graph node / graph edge | 4096 / 4096 / 8192 |
| Scope veya delimiter nesting / nested block comment | 128 / 64 |
| Raw string delimiter # / dosya token / toplam token | 64 / 400.000 / 750.000 |

Konumlar bounded line/column ve byte offset içerir. UTF-8 byte offset ile Unicode karakter konumu aynı değildir; CRLF tek newline sayılır. Lexer line_count, trailing newline sonrasındaki boş satırı da içerir. Ön incelemenin CRLF sayımı bu logical line sayısıyla aynı payda değildir. JSON string/array/object/toplam node sınırları ayrıca uygulanır. Limit aşımında ilk N kayıt tam başarı diye döndürülmez.

Strict UTF-8, duplicate JSON key, NaN/Infinity, boolean-as-integer, yanlış tür, desteklenmeyen sürüm veya referans kapalı doğrulanır. Hash uyuşmazlığı ve okuma sırasında kaynak kimliği değişimi başarılı lexical sonuç değildir. BOM veya belirsiz lexical sınır açıkça sınırlandırılır. Yeni output dizinine yazılır; mevcut dosyalar silinmez veya üzerine yazılmaz.

Saf graph/coverage builder'ları metadata'dan türetilir. Inspector yalnız beş yeni dosyanın model/ref/count ve gerçek byte/hash tutarlılığını inceler; Rust lexer'ını yeniden çalıştırmaz. `content_consistent`, lexical yorumun Rust diline göre doğruluğu veya gerçek module closure kabulü değildir. Gerçek komutlar ve açık kapılar [teslim kaydında](DEMO_DELIVERY.tr.md) tutulur.
