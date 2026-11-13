# Phase36 canonical CSV reconciliation

**OFFLINE DEMONSTRATION — TYPED CSV IMPORT ONLY — NO CURRENT SOURCE VERIFICATION**

Yeni typed reader iki gerçek CSV'nin hücrelerini standart `csv` modülüyle parse eder. Dataset JSON kayıtlarını typed import yerine kopyalamaz; JSON yalnız mevcut owner sözleşmesi ve içerik eşliği için karşılaştırmadır. Kaynak Phase35 encoder/decoder/renderer salt okunur yeniden kullanılır, genel CSV framework veya gevşek alternatif encoding yazılmaz.

## Fiziksel CSV ve hücre biçimi

Kaynak biçim UTF-8/no-BOM, comma, `QUOTE_ALL`, LF ve sabit header sırasıdır. Reference dört, projection 11 sütundur. Header'lar normal sabit sütun adlarıdır; her DATA hücresi `j:` + canonical compact ASCII JSON'dur. Hücre 4096 B/satır 65536 B/CSV 128 KiB limitleri korunur.

Reader header tekilliğini ve exact sırasını; sütun/satır sayılarını; her DATA prefix'ini; strict JSON tipini; mevcut encoder ile canonical hücre eşliğini; duplicate record yokluğunu kontrol eder. Yeni parsed reference/projection kayıtları owner dataset ve alan bazlı tip/değerlerle eşlenir. Tam dosya mevcut CSV renderer ile yeniden üretilerek byte eşliği aranır. `csv.reader(strict=True)` başarısı tek başına QUOTE_ALL/LF/row order veya canonical payload kabulü değildir.

BOM, eksik/fazla/duplicate header, eksik/fazla hücre, ek satır, missing `j:`, noncanonical JSON/escape, bozuk quoting, CRLF uyumsuzluğu, duplicate reference/projection, unknown status/field veya manifest/hash uyuşmazlığı kapalı hatadır. Sessiz whitespace/CRLF temizleme, satır atlama, default değer veya kısmi kayıt kabulü yoktur.

## Gerçek JSON türleri

Aşağıdaki hücre metinleri CSV parser'ın çıkardığı logical değerlerdir; dış CSV quoting katmanı değildir:

| Hücre metni | Typed anlam |
| --- | --- |
| `j:null` | Null; unknown/yokluk metadata'sı integer sıfır değildir |
| `j:""` | Boş string; alan sözleşmesi ayrıca izin vermelidir |
| `j:0` | Integer sıfır; string değildir |
| `j:"0"` | String sıfır; integer değildir |
| `j:[]` | Boş liste; alan sözleşmesi ayrıca izin vermelidir |
| `j:false` | Boolean; mevcut Phase35 DATA hücresi kabul etmez, sıfıra dönüştürülmez |

Literal string `j:null` hücrede `j:"j:null"` olur; null ile çakışmaz. `interpretation_limitations` mevcut JSON string-array encoding ve sırasını korur. Float/NaN/Infinity, boolean-as-integer ve beklenmeyen nesne türleri reddedilir. Ortak model güven bayraklarının false boolean'ları DATA hücre kuralından ayrı zorunlu metadata'dır.

Bu protokol örnekleri null/empty/zero/string/boolean adversarial acceptance fixture'ı değildir. Demo yalnız gerçekten içerdiği değerleri gözlemleyebilir. Absence byte/hash null kalmalı; bir reference count sıfırı sıfır-byte source dosyası sayılmamalıdır.

## Formula ve kaynak güveni

Importer `j:` kaldırıp ham metni CSV/formül/shell olarak çalıştırmaz. `eval`, expression engine veya shell yoktur. JSON control/newline/tab kaçışları gevşetilmez; ham formule dönüşüm yapılmaz. Gerçek Excel/LibreOffice import kabulü yapılmaz. Typed decoding daha önceki güvenli görünümü kaynak değerle karıştırmaz.

Beş Phase35 artefact hash'i ve manifestteki dört payload ilişkisi iç byte bağlarıdır. Saldırgan CSV/dataset/manifesti birlikte değiştirebilir ve yeniden hash'leyebilir; iç eşlik producer kimliği, gerçek guard veya source freshness kanıtı değildir. Receipt'teki canonical/equal durumları import anını kaydeder; yeni inspector kaynak CSV'yi yeniden parse etmediğinden bu davranışı bağımsız doğrulamaz.

Hostile/duplicate JSON/UTF-8/BOM, formula/quoting/header/sütun/canonical `j:` ve null-empty-zero adversarial durumlar, duplicate records/wrong hash/değiştirilmiş input, limit/permission/crash/partial write/repeat determinism çalıştırılmadıkça NOT_RUN kalır. Kod koruması runtime güvenlik kabulü değildir; ikinci offline host, spreadsheet import, Phase19 UI ve native/human/legal/release kapıları açıktır.
