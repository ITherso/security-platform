# Phase35 disclosure ve CSV encoding

**OFFLINE DEMONSTRATION — TABULAR DISCLOSURE ONLY — NO CURRENT SOURCE VERIFICATION**

Dataset yalnız kaynak kapsüldeki seçilmiş reference durumları ile `provided_limited_metadata` kayıtlarının mevcut 11 projection alanını taşır. Bloke referans yalnız dört alanlı reference register'da görünür; projection satırı, olumlu candidate/file/hash/byte veya audit kopyası kazanmaz. Önceki fazda çıkarılmış referans geri getirilmez.

## Tipli değer ve kodlanmış görünüm

Dataset JSON gerçek kaynak tip/değerlerini tutar. CSV her DATA hücresini `j:` öneki ardından compact ASCII JSON olarak kodlar. Aşağıdakiler CSV parser'ın çıkardığı mantıksal hücre metinleridir; dosyanın dış CSV quoting katmanı değildir:

| Tipli değer | Mantıksal hücre metni |
| --- | --- |
| `null` | `j:null` |
| Boş string | `j:""` |
| Bilinen integer sıfır | `j:0` |
| String `j:null` | `j:"j:null"` |
| String listesi | `j:["a","b"]` |
| Boş liste | `j:[]` |

Bu gösterimler çakışmaz. Koleksiyon sırası kapalı modelden korunur; JSON listesi liste olarak geri yorumlanır. Prefix çıkarılıp JSON olarak decode edilmesi, tablo formülü evaluate etme veya veri sahibinin yetkisini kabul etme izni değildir. Örnek gösterimler encoding tanımıdır; adversarial null/empty/zero testlerinin çalıştırıldığı iddiası değildir.

Kaynak absence byte/hash `null` kalır; sıfır-byte dosya veya boş stringe çevrilmez. Kaynak `fresh_*` veya observation kimliği eski kayıt kodudur; CSV üretimi yeni source gözlemi değildir. Yeni timestamp/hash/size eklenmez.

## Formula ve kontrol karakteri sınırı

Python standart `csv` writer comma delimiter, `QUOTE_ALL`, LF ve UTF-8/no-BOM kullanır. Her DATA hücresi `j:` ile başlar. Kaynak string `=`, `+`, `-`, `@` veya kontrol karakteriyle başlasa bile ham kaynak değeri hücre başı olmaz; JSON string literal içindedir. Header sabit ve formula-free normal sütun adıdır. Dış CSV quoting'i JSON string quoting'inden ayrı katmandır.

Compact ASCII JSON newline/tab/control karakterlerini kaçış dizileri halinde yazar; gerçek tab veya multiline veri hücresi üretilmez. Unicode kaçışları kaynağın anonimleştirildiği anlamına gelmez; tersine yorumlandığında aynı tipli değer geri gelir. Kaynak değer güvenli gösterim için sessizce değiştirilmez.

Hücre 4096 B, satır 65536 B ve her CSV 128 KiB sınırındadır; limitte truncation veya kısmi başarılı export yoktur. Sütun sırası sabit, reference satırı her seçilmiş referans için bir, projection satırı yalnız izinli kayıt için birdir. Header veri sayısına dahil değildir. CSV yeniden üretimi dataset'le byte eşliği bakımından incelenir.

## Açıklanmayan veri ve açık kabuller

Tam baseline, raw Rust, root/path/physical identity, credential, raw exception, gerçek kullanıcı/kurum kimliği veya kapsülde bulunmayan metadata taşınmaz. Bloke olumlu hash/byte başka bölümde tutulmaz. ID/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.

Encoding tasarımının kaynakta bulunması gerçek spreadsheet import veya adversarial formula/control/multiline/null-empty-zero kabulü değildir. Bu dallar çalıştırılmadıkça NOT_RUN kalır. Değiştirilmiş kapsül, wrong digest/ID, blocked projection enjeksiyonu, hostile JSON/UTF-8 ve ZIP/link/limit/crash kabulü de ayrı kapılardır.

`demo_only=true`; source/context/independent observation, upstream guard ve diğer mevcut 18 güven alanı false kalır. CSV dönüştürmek producer attestation, gerçek kullanıcı yetkisi, kaynak güncelliği, compiler/ownership, hukukî veya release otoritesi oluşturmaz.
