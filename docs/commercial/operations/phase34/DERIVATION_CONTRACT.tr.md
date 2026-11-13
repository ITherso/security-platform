# Phase34 derivation sözleşmesi

**OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION**

Yeni offline araç yalnız mevcut Phase33 kapsülünün seçilmiş referanslarından strict subset kapsülü türetir. İş mantığı doğrulanmış immutable metadata ile saftır; disk erişimi adapter/CLI ve güvenli paketleme sınırındadır. Yeni guard, evaluator, authorization veya resolver oluşturulmaz.

## Kapalı request

`termivar-offline-capsule-derivation-request/v1` tam altı alan kabul eder:

| Alan | Anlam |
| --- | --- |
| `schema_version` | Yalnız desteklenen derivation request v1 |
| `mode` | Yalnız `demo` |
| `derivation_reference` | Sınırlı yerel demo kimliği; yetki veya credential değildir |
| `source_capsule_sha256` | Gerçek açık kaynak ZIP byte'larının SHA256 beklentisi |
| `selected_reference_ids` | Kaynakta mevcut 1–8 farklı ID; kaynak referans kümesinin strict subset'i |
| `derivation_constraints` | Caller tarafından genişletilemeyen kapalı sabit limitler |

Boş/duplicate/unknown seçim, yanlış hash, unknown alan/schema/version veya demo dışı mode kapalı hatadır. Request yeni candidate/projection, `override_guard`, `allow_blocked_projection`, gerçek kurum/kullanıcı yetkisi veya keyfî dosya/ZIP üyesi seçimi taşımaz.

`derivation_constraints` tam dokuz sabit alanı taşır:

| Alan | Sabit değer |
| --- | ---: |
| `max_request_bytes` | 32768 |
| `max_source_zip_bytes` | 262144 |
| `max_derived_zip_bytes` | 262144 |
| `max_ledger_bytes` | 65536 |
| `max_summary_bytes` | 131072 |
| `max_total_input_bytes` | 1048576 |
| `max_selected_references` | 8 |
| `preserve_selected_results_exactly` | `true` |
| `require_proper_reference_subset` | `true` |

Bu alanlar caller tarafından genişletilemez. Integer ve boolean türleri birbirinin yerine kabul edilmez. Yeni derived `capsule_reference`, request'in `derivation_reference` kimliğidir; seçilmiş referans/projection içerikleri ve mevcut kaynak artefact bağları korunur. Yeni yerel kapsül kimliği producer veya gözlem kimliği değildir.

## Saf subset ve mevcut kapsül sözleşmesi

`derive_reference_subset(validated_source_capsule, request)` yalnız gerçek mevcut owner validator'ından geçmiş exact modeli tüketir. Caller'ın `validated=true` veya allow işareti otorite değildir. Seçilen her referansın status, upstream karar, limitation kodları ve projection listesindeki bütün alan/değerler aynı kalır; kaynak model değiştirilmez. Sayımlar yeniden türetilir. Kaynakta olmayan alan null/default ile doldurulmaz.

Yeni model gerçek Phase33 `validate_capsule` ile doğrulanır. Uyumlu model üretilemiyorsa validator gevşetilmez ve tamamlanmış kapsül iddia edilmez. Mevcut `inspect_bundle(raw_path, requested_ids)` dönüşü `(inspection, lookup)` çiftidir; ham capsule modeli değildir. Dar adapter doğrulanmış immutable model almak için mevcut güvenli ZIP parser/model/manifest/summary/README yolunu yeniden kullanır; ikinci ZIP güvenlik reader'ı kurmaz.

Derived ZIP aynı Phase33 v1 kapsül şemasını ve tam dört üyeyi korur: `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt`. Summary yeni JSON'dan owner renderer ile türetilir; inner manifest gerçek üç payload'ı bağlar, kendisini kapsamaz. Mevcut README byte açıklaması olumlu onay iddiasıyla yeniden yazılmaz. Derived ZIP içine yeni derivation/köken alanı veya seçilmeyen referans disclosure log'u eklenmez.

## Dış ledger ve sayımlar

Dış `termivar-offline-capsule-derivation-ledger/v1` tam request'i, kaynak ve derived ZIP'in `bytes`, `sha256`, `capsule_reference` kimliklerini, ayrı `source_counts`/`derived_counts`, `strict_reference_subset_with_exact_selected_results` ilişki kodunu ve sınırlamaları taşır. Projection payload'ı veya çıkarılan referansların ID/ad/hash/byte/file kimlikleri ledger'a kopyalanmaz. Yalnız seçilmiş ID'ler ve toplu sayımlar açıklanır. Ledger common alanları yalnız yeni schema/derivation kimliği/demo etiketi/true demo ve 18 false bayraktır; tam source_bindings nesnesi ledger'a taşınmaz.

Her sayım kümesi ayrı reference/provided/withheld/unavailable reference; projection ilişkisi; unique candidate; unique file; present ve absence projection paydalarını kullanır. Toplam sayımlar çıkarılan referansların kimliğini açıklamaz. Gerçek ilişkiyi incelemek için iki kapsül gerekir; ledger'ın varlığı tek başına köken veya içerik eşitliği kanıtı değildir.

Dış manifest `termivar-offline-capsule-derivation-manifest/v1`, inspection `termivar-offline-capsule-derivation-inspection/v1` sözleşmesidir. Bu yeni dış kayıtlar mevcut Phase33 iç kapsül şemasını değiştirmez.

## Sınırlar ve kabul

Phase33 ZIP 256 KiB, üye 128 KiB, expanded toplam 256 KiB, ratio 20, tam dört üye, reference 8, projection 64, JSON depth 12/node 20.000/text 512 sınırları korunur. Request 32 KiB, ledger 64 KiB, summary 128 KiB, toplam açık girdi 1 MiB. Strict UTF-8/JSON; duplicate/unknown key/version, float/NaN/Infinity ve bool-as-int reddi. Yeni/boş output, overwrite yasağı, limitte truncation ve kısmi yazmada başarı iddiası yoktur. Daha sıkı owner sınırı korunur.

`demo_only=true` ve mevcut 18 false güven alanı korunur. Daha küçük kapsül source freshness, producer/signature, kullanıcı yetkisi, guard doğruluğu, compiler/module closure, ownership veya hukukî/release güveni kazandırmaz. Bu sözleşme belgesi saldırgan runtime kabulünün geçtiği anlamına gelmez; actual komutlar ve byte kimlikleri yalnız teslim kaydındadır.
