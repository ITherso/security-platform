# Phase29 Rust statik referans sınırları

**DEMONSTRATION ONLY — RUST SOURCE REFERENCES — NO MODULE CLOSURE OR BUILD AUTHORIZED**

Araç bir Rust compiler, tam parser, AST doğrulayıcı veya Cargo module resolver değildir. Kaynak hash gözlemi ve lexical inceleme ayrı aşamalardır. JSON/TOML quote tarayıcısı Rust lexer yerine kullanılmaz.

## Lexical subset

Dar lexer, normal satır yorumlarını, en fazla 64 derinlikli nested block comment'leri, desteklenen normal/byte string escape'lerini, en fazla 64 # delimiter içeren raw string/raw byte string biçimlerini, identifier/punctuation token'larını ve sınırlı delimiter/attribute sınırlarını ayırır. Yorum veya string içindeki mod/include/path metni gerçek kaynak bildirimi sayılmaz.

Kapanmamış string/comment, desteklenmeyen delimiter veya escape, belirsiz char/lifetime ayrımı, dengesiz delimiter ve güvenle kurulamayan lexical bağlamda tahminî referans üretilmez. Kapalı hata veya açık partial_unverified/lexical_boundary_unresolved sınırı korunur; belirsiz bölge normal Rust kodu gibi taranmaz.

## Birbirine dönüştürülmeyen referanslar

| Gözlem | Anlamı ve sınırı |
| --- | --- |
| External module declaration | Modül adı gözlendi; foo.rs veya foo/mod.rs adayı üretilmez, dosya çözülmüş sayılmaz. |
| Explicit path module declaration | Desteklenen literal path ve ilgili mod attribute bağı vardır; relative base ve exact allowlist ayrıca gerekir. |
| Literal include reference | Sade include! literal'ı gözlendi; mod declaration veya etkin build inclusion değildir. |
| Dynamic reference unresolved | Include bağlamındaki dinamik ifade çözülemedi; macro/env/build script çalıştırılmaz. Fiziksel missing_file iddiası değildir. |
| Inline module declaration | Aynı kaynak içinde lexical scope'tur; external dosya oluşturmaz. Nested declaration ayrıca ve kendi konumuyla korunur. |
| Unsupported reference | Güvenilir yorum yapılamadı; başarılı file-binding'e yükseltilmez. |

include_str! ve include_bytes! source-module edge sayılmaz. Sıradan println!, json!, env! veya concat! macro kullanımı include! bağlamı bulunmadan dinamik kaynak referansı değildir. Macro token tree'leri opaque kalır; içindeki mod metni etkin bildirim sayılmaz. Macro genişletme ve procedural macro çözümü yapılmaz.

cfg/cfg_attr attribute varlığı sınırlı metadata olarak tutulur; raw koşul kodu veya serbest snippet taşınmaz. Condition evaluation yapılmaz. cfg_attr içindeki alternatif path kesin dosya seçtirmez. Nested explicit path'te güvenli relative base kurulamazsa path_resolution_context_unresolved korunur.

Desteklenen subset ile gerçek kaynakta gözlenen subset ayrı sayılır. İlk incelemede bildirilen 95 textual external mod ve bir inline tests modülü ürün sonucu olarak sabitlenmez. Kaynakta gözlenmeyen path/include/nested-comment/macro pozitif olayı fixture veya kabul başarısı gibi üretilmez. Gerçek sayımlar yalnız yeni assembly sonrası [teslim kaydına](DEMO_DELIVERY.tr.md) yazılır.
