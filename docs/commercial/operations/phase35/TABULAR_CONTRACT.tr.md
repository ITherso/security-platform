# Phase35 tabular veri sözleşmesi

**OFFLINE DEMONSTRATION — TABULAR DISCLOSURE ONLY — NO CURRENT SOURCE VERIFICATION**

Yeni ürün yalnız doğrulanmış kaynak kapsülde bulunan seçilmiş disclosure metadata'sını JSON dataset ve iki CSV görünümüne taşır. `exported_projection ⊆ validated_capsule_projection`. Yeni guard/evaluator, candidate/file observation, risk skoru veya kullanıcı yetkisi üretmez.

## Scope

`termivar-offline-capsule-tabular-scope/v1` tam beş alan taşır: `schema_version`, `mode`, `source_capsule_sha256`, `export_reference_ids`, `export_constraints`. Yalnız `mode=demo`; kaynak kapsülde bulunan 1–8 farklı açık reference ID. Kaynak SHA256 gerçek ZIP byte'larına bağlanır. Boş/duplicate/unknown seçim, yanlış digest ve unknown alan/version kapalı hatadır. Scope path, yeni candidate/observation, override, force-provided, kurum/kullanıcı yetkisi veya keyfî metadata taşımaz.

`export_constraints` tam dokuz sabit alan taşır; caller bu değerleri genişletemez:

| Alan | Sabit değer |
| --- | ---: |
| `max_source_zip_bytes` | 262144 |
| `max_dataset_bytes` | 131072 |
| `max_csv_bytes` | 131072 |
| `max_summary_bytes` | 131072 |
| `max_reference_records` | 8 |
| `max_projection_records` | 64 |
| `max_cell_bytes` | 4096 |
| `max_row_bytes` | 65536 |
| `max_total_input_bytes` | 1048576 |

## Dataset ve kapalı kayıtlar

`termivar-offline-capsule-tabular-dataset/v1` demo etiketini, 18 false güven bayrağını, strict scope'u, kaynak ZIP'in `bytes`/`sha256`/`capsule_reference` kimliğini, ayrı reference/projection kayıtlarını, gerçek sayımları, sabit CSV encoding politikasını ve sınırlamaları taşır. Tam kaynak nesne serialize edilmez; yalnız kapalı allowlist alanları oluşturulur.

Reference kaydının sabit sütun sırası:

| Sıra | Alan |
| ---: | --- |
| 1 | `reference_id` |
| 2 | `disclosure_status` |
| 3 | `projection_count` |
| 4 | `interpretation_limitations` |

Her seçilmiş referans için tam bir reference satırı vardır. `withheld_by_existing_guard` veya kapsam dışı kayıt projection count sıfır taşır; reference kaydı olumlu file metadata yetkisi değildir. Disclosure status kaynaktan korunur, yeniden değerlendirilmez. Reference kaydının `interpretation_limitations` alanı kaynak result'ın kapalı `limitation_codes` listesidir; projection'ın mevcut dört interpretation kodu ayrı alan olarak korunur.

Projection kaydının sabit sütun sırası:

| Sıra | Alan |
| ---: | --- |
| 1 | `reference_id` |
| 2 | `candidate_id` |
| 3 | `file_id` |
| 4 | `upstream_projection_kind` |
| 5 | `source_file_presence` |
| 6 | `observed_byte_size` |
| 7 | `observed_sha256` |
| 8 | `phase31_current_observation_id` |
| 9 | `phase31_comparison_id` |
| 10 | `upstream_comparison_status` |
| 11 | `interpretation_limitations` |

Yalnız `provided_limited_metadata` referansların mevcut izinli projection'ları taşınır. Tip, değer, null ve limitation sırası korunur. Bloke referans için projection satırı yoktur. Yeni hash, timestamp veya source observation üretilmez.

## Sayımlar ve CSV görünümü

Dokuz sayım ayrı requested/provided/withheld/unavailable reference; projection ilişkisi; unique candidate; unique file; present ve absence projection paydalarını taşır. Header satırı veri satırı değildir. Aynı file birden fazla ilişkide görünürse unique file ayrı sayılır. Count alanları güvenlik başarı skoru değildir.

Dataset JSON tipli kaynak değerlerin otoriter kapalı modelidir. `reference-register.csv` dört, `projection-register.csv` 11 sabit sütunla bu modelden türetilir. CSV DATA hücreleri `j:` + compact ASCII JSON; header'lar sabit normal sütun isimleridir. Comma/QUOTE_ALL/LF/UTF-8/no-BOM politikası sabittir. [Encoding belgesi](DISCLOSURE_AND_ENCODING.tr.md) null/empty/zero, koleksiyon ve kontrol karakteri ayrımını açıklar. CSV escape değeri kaynak değerle karıştırılmaz.

`csv_encoding` sözleşmedeki kapalı politikayla birebir eşleşmelidir: `cell_prefix=j:`, `payload_format=canonical_compact_ASCII_JSON`, hücre tipleri string/integer/null/string-array, null/empty/zero için `j:null`/`j:""`/`j:0`, koleksiyon JSON string-array, değer kaynağı tipli dataset JSON, header plain fixed column names, delimiter comma, quoting all, line ending LF ve UTF-8 BOM false. Hücre/satır üst sınırları aynı policy içinde de 4096/65536 B'dır. Policy alanı veri veya limit override kanalı değildir.

Dış manifest `termivar-offline-capsule-tabular-manifest/v1`, inspector çıktısı `termivar-offline-capsule-tabular-inspection/v1` sözleşmesidir; mevcut Phase33/34 kapsül şeması değişmez.

## Limitler ve yetki sınırı

Scope 32 KiB; kaynak ZIP 256 KiB; ZIP üye 128 KiB/expanded toplam 256 KiB/tam dört üye/ratio 20; reference 8/projection 64. Dataset/her CSV/Markdown 128 KiB; manifest 64 KiB; toplam açık girdi 1 MiB; depth 12/node 20.000/text 512. Kodlanmış hücre 4096 B, satır 65536 B. Daha sıkı owner limitleri korunur, truncation yoktur. Strict UTF-8/JSON; duplicate/unknown alan/version, float/NaN/Infinity, bool-as-int ve duplicate record reddi. Yeni/boş output ve overwrite yasağı korunur.

`demo_only=true` ve 18 false güven alanı korunur. Source freshness, producer, Phase31 guard, compiler/module closure, ownership, insan/hukukî/müşteri/release kabulü kazanılmaz. Scope/dataset doğrulaması saldırgan girdi kabulü veya gerçek spreadsheet import kabulü değildir. Actual komut ve dosya kimlikleri yalnız teslim kaydındadır.
