# Phase30 path ve module sınırları

**DEMONSTRATION ONLY — RUST MODULE CANDIDATE EVIDENCE — NO COMPILER RESOLUTION VERIFIED**

External module gözlemi, candidate path declaration, desteklenen path context, allowlist izni, dosya varlığı/hash'i ve compiler resolution farklı kanıtlardır. candidate_file_present gerçek rust_module_resolved anlamına gelmez.

Phase29 mod adından foo.rs veya foo/mod.rs dosyası üretmez. Phase30 da bu yolları otomatik açmaz. İncelenecek yol yalnız yeni scope'un explicit candidate kaydından gelir. Dosya adı benzerliği supported_static_path_context değildir. Kaynak literal path taşımıyorsa böyle bir kanıt uydurulmaz.

| Path context | Anlam |
| --- | --- |
| explicit_operator_candidate | Operatör bir adayı seçmiştir; Rust bu dosyayı seçmiş sayılmaz. |
| supported_static_path_context | Dar statik bağ için gerekli gerçek kaynak kanıtı vardır; compiler resolution değildir. |
| context_ambiguous | Lexical/nested/relative-base ilişkisi kesin kurulmamıştır. |
| unsupported_path_context | İstenen yol ilişkisi desteklenen subset'in kanıt sınırını aşar. |

Scope'ta supported context iddiası bulunması doğrulama yerine geçmez. Parent lexical context, inline nesting ve güvenilir relative base eksikse olumlu statik ilişki üretilmez. cfg/feature/target koşulları değerlendirilmez; condition metadata korunur.

İki candidate ayrı kayıttır. İkisi mevcutsa otomatik seçim yapılmaz; yalnız biri mevcutsa da alternatif kümesi exhaustive sayılmaz. Bir aday okunmadıysa diğerinin present sonucu belirsizliği kapatmaz. Candidate missing, modülün bütün repository'de bulunmadığını söylemez.

Aynı canonical root/pin/path birden fazla reference tarafından kullanılabilir: tek dosya gözlemi, ayrı candidate/reference ilişkileri korunur. Farklı root/path veya hardlink aynı dosya diye sessizce birleştirilmez. Conflicting expected hash/limit/read kind kapalı hata oluşturur. Bir reference'ın allowlist izni başka binding'e otomatik yetki vermez.

Okuma yalnız hash/varlık/tür/byte/stabilite içindir; Rust body decode/parse edilmez. Aday dosyanın içindeki modüller takip edilmez. resolved_file ve compiler_resolution_verified false kalır; source completeness, module closure ve component ownership ayrıca açık kalır.
