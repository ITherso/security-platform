# Phase34 gerçek derivation teslim kaydı

**OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION**

2026-11-13 tarihinde iki izinli Phase34 ürün çağrısı tamamlandı: derivation **exit 0**, bağımsız ilişki inspector'ı **exit 0**. İkinci çağrı, ilk başarılı üretimin eksiksiz dört dış çıktısı ve derived ZIP'in dört iç üyesi manuel incelendikten sonra çalıştı. Bütçe **2/2 tüketildi ve kapandı; kalan çağrı 0**. Otomatik retry, üçüncü çağrı veya eski CLI tekrar çalıştırması yoktur. Phase20–33 ve Phase24/29 insan istisnaları kapalıdır.

Başlangıç Phase33 HEAD `018ff78ac37c03c1b5042c83346156b8be339713`, tree `ff063f8cc2fc1f9b131e2643a916a18f94f31aa7`. Üretim source commit'i `d253dda8d1d57dbf933e8b6e6dfc7d5db2da7324`, tree `3b03bae8baf47570004d71a205ff2abb91b83562`. Üretim sonrası yalnız README ve bu teslim belgesi actual sonuçlara göre güncellendi; on kod/örnek dosyası üretim snapshot'ıyla aynı kalır. Phase34 baseline 358 artefact, 327 kaynak, mevcut 21 runtime asset ve production wheel kimliğini korur. Yeni kaynak teslim ZIP'i yalnız yeni Phase34 kod/belge/gerçek output ve teslim kayıtlarını kapsar; eski arşiv/native/wheel/cache/DB veya özel dosya kopyalanmaz.

## Gerçek kaynak kapsül ve seçim

Kaynak `outputs/phase33-reference-capsule/guarded-reference-capsule.zip`, **23439 B / 4 üye**, SHA256 `19e61b261d63863f10b4147daf6dc5b2199faedcda41b03acb20322d30cb3388`. Request gerçek kaynak ZIP byte'larına bağlanır. Kaynak hash'i üretici imzası veya güncel filesystem kanıtı değildir.

| Seçilen bağlam | Kaynak ve derived kapsülde korunan reference ID | Kaynak ve derived durum | Gerçek projection |
| --- | --- | --- | ---: |
| outcome | `rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81` | `provided_limited_metadata` | 2 |
| authorization_review | `rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a` | `withheld_by_existing_guard` | 0 |

Demo yalnız bu iki referansı seçti. Seçilmeyen mevcut bağlamın ID, native hash/byte/file/candidate veya projection bilgisi bu kayda kopyalanmadı. Seçilmiş iki referansın sonuçları ve `outcome` içindeki iki projection'ın bütün alan/değerleri kaynakla birebir korundu. `authorization_review` için `withheld_by_existing_guard` ve `projections=[]` korundu; olumlu alt metadata eklenmedi. Absence byte/hash null kalır, bilinen sıfıra çevrilmez.

| Gerçek toplam | Kaynak | Derived |
| --- | ---: | ---: |
| Referans | 3 | 2 |
| Provided referans | 2 | 1 |
| Withheld referans | 1 | 1 |
| Unavailable referans | 0 | 0 |
| Projection ilişkisi | 3 | 2 |
| Benzersiz candidate | 3 | 2 |
| Benzersiz file | 3 | 2 |
| Kayıtlı present projection | 2 | 1 |
| Kayıtlı absence projection | 1 | 1 |

Sayımlar gerçek doğrulanmış kapsüllerden türetildi; başarılı fixture olarak kodlanmadı. Çıkarılan bir referansın yalnız toplam adedi raporlandı; kimliği ve olumlu metadata'sı disclosure kayıtlarında listelenmedi.

## Gerçek tamamlanan exact iki çağrı

Aşağıdakiler gerçek generation kaydındaki tamamlanmış iki çağrıdır; yeniden çalıştırma izni değildir. Birinci başarılı ve eksiksiz dört output üretti; gerçek derived ZIP'in dört üyesi manuel incelendi; sonra ikinci çalıştı. Actual exit kodları **[0,0]**, kapalı **2/2 bütçe**, kalan çağrı **0**. Başarısız çağrı tüketilir; otomatik retry, üçüncü çağrı veya eski CLI tekrar çalıştırması yoktur.

```text
python -I -B security-platform/tools/commercial_capsule_derivation/derive_capsule.py --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --request security-platform/tools/commercial_capsule_derivation/examples/demo_derivation_request.json --output-dir outputs/phase34-capsule-derivation
```

```text
python -I -B security-platform/tools/commercial_capsule_derivation/inspect_derivation.py --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --derived-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --ledger outputs/phase34-capsule-derivation/derivation-ledger.json --summary outputs/phase34-capsule-derivation/derivation-summary.md --manifest outputs/phase34-capsule-derivation/manifest.json --output outputs/phase34-capsule-derivation/derivation-inspection.json
```

Derivation exit **0** dört gerçek dış output üretti. İlişki inspector'ı exit **0**, `internal_content_status=content_consistent`, kapsam `two_explicit_capsules_and_derivation_ledger_summary_manifest_only`. İki kapsül, seçilmiş sonuç/projection birebir eşliği, strict subset, ledger, summary ve manifest byte/model bağları incelendi. Bu gerçek Phase31/32 artefact, guard, güncel kaynak dosyası veya producer doğrulaması değildir.

## Beş gerçek dış çıktı kimliği

Konum `outputs/phase34-capsule-derivation/`. Boyutlar ve SHA256 değerleri gerçek disk byte'larından ölçüldü.

| Dosya | Bayt | SHA256 |
| --- | ---: | --- |
| `derived-reference-capsule.zip` | 20253 | `d3eea4c7946d45290c4876ac8b6d8ca5172297933b7681812863158bf845c01d` |
| `derivation-ledger.json` | 3339 | `fc1b20a0b480968333273b91074474e6bbd01af7022ea906ea5aff4aa4e9d7ee` |
| `derivation-summary.md` | 7671 | `637138e3581a6bc59137844489785d095bfeb8d0c33e52c04906d4e2765fe292` |
| `manifest.json` | 2630 | `1c79d7240c75f58f841cfb72de803ca011176dfd82b5309b7eb7df76942ab9b3` |
| `derivation-inspection.json` | 3219 | `e1d808080c8f3b5043b8ada96152ec14815767dd08d992ef687d5c9ab76e6557` |

Ledger yalnız altı alanlı strict request'i, kaynak ve derived ZIP byte/SHA256/demo kimliklerini, toplu sayımları ve sınırlamaları taşır. Projection payload'ı, source_bindings veya omitted ID listesi taşımaz. Dış manifest ilk üç gerçek output'u bağlar; kendisini ve inspection output'unu kapsamaz.

## Kaynak ve derived ürün kapsülleri

Kaynak kimliği **23439 B / 4 üye / SHA256 `19e61b261d63863f10b4147daf6dc5b2199faedcda41b03acb20322d30cb3388`** olarak korundu. Derived kimliği **20253 B / 4 üye / SHA256 `d3eea4c7946d45290c4876ac8b6d8ca5172297933b7681812863158bf845c01d`**. Derived kapsül kimliği `DEMO-TERMIVAR-DERIVATION-034`; yerel kimlik değişimi seçilmiş reference/projection değerlerini veya mevcut kaynak bağlarını değiştirmez.

| Derived ZIP iç üyesi | Bayt | SHA256 |
| --- | ---: | --- |
| `reference-capsule.json` | 6107 | `f905753f7f052b62e3aa405f7ae458f0d26433946fefbeb694beab94af9ac183` |
| `reference-summary.md` | 9530 | `a195e8bff8181d0004fef214c59fcdd1b6cc6da4a86779f6dcec430c042c7004` |
| `bundle-manifest.json` | 2800 | `cfd68ca112ba29e0a0687a05317345955b978b6cedf1e13e54f657d6b6e67b2e` |
| `README.txt` | 1346 | `289fee84ca443fd6510d6d3ae405dc2623d21fb8af981a430cd9983d7025ced3` |

Gerçek üye sırası tablodaki gibidir; `ZIP_STORED`, sabit `1980-01-01 00:00:00` metadata politikası, expanded toplam **19783 B** gözlendi. Mevcut Phase33 writer/renderer/manifest/README açıklamaları yeniden kullanıldı; README byte kimliği kaynaktakiyle aynıdır. Inner manifest diğer üç üyenin byte/SHA256 bağını taşır, kendi digest'ini taşımaz. Tek gerçek üretim tekrar-determinism kabulü değildir.

## Manuel gözlem

İki seçilmiş referans ve bütün projection alan/değerleri kaynakla aynıydı; bloke sonuç boş kaldı. Derived JSON, Markdown, README ve dış disclosure kayıtlarında seçilmeyen referansın ID veya olumlu metadata'sının taşınmadığı gözlendi. Bu gözlemde omitted ID/native hash/byte/file/candidate değerleri ayrıca rapora kopyalanmadı. Sızıntı saldırgan senaryolarının geneli NOT_RUN kalır.

Özgün Phase31/32 artefact veya native kaynak yeniden okunmadı, guard yeniden çalıştırılmadı. Inspector `original_phase31_files_read=false`, `original_phase32_files_read=false`, `native_source_files_read=false`, `old_guard_reexecuted=false`, `original_source_artifact_bytes_independently_verified=false`, `source_producer_verified=false`, `legal_review_performed=false` raporladı. İnceleme iki açık ZIP ve üç dış ledger/summary/manifest girdisinin iç ilişkisiyle sınırlıdır.

## Güven sınırı ve NOT_RUN

İlişki inspector'ı iki ZIP'i mevcut Phase33 sahip yolu ile extraction olmadan okuyup strict subset ve seçilmiş status/projection birebir eşliğini değerlendirdi. Dış ledger yalnız request, iki ZIP kimliği ve toplu sayımlar taşır; projection payload'ı veya omitted ID listesi taşımaz. `content_consistent` yalnız iki kapsülün iç ilişkisidir; producer/signature, gerçek guard veya bugünkü source doğruluğu değildir. Mevcut çalışma alanındaki bu iki çağrı ikinci offline host'a taşınmış kodla source-absence runtime kabulü değildir.

`demo_only=true`; mevcut 18 false güven alanı, `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false` korunur. Türetme yeni source gözlemi veya TTL garantisi değildir. Daha küçük disclosure daha yüksek güven değildir.

NOT_RUN: hostile/duplicate JSON/invalid UTF-8, yanlış source digest/reference ID, sahte/çelişkili capsule, bloke projection enjeksiyonu, omitted metadata sızıntısı saldırıları, duplicate ZIP/ZIP bomb/path traversal/symlink/compression/limit, kısmi yazma/permission/crash/power loss/repeat determinism, ikinci offline host/source-absence runtime kabulü, kaynak producer/signature, Phase31 guard'ın bağımsız doğruluğu, gerçek source freshness, compiler/module closure, component ownership, native runtime, insan/hukukî/müşteri/release kabulü. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Kodda koruma olması saldırgan girdi kabulü değildir.

Kaynak ürün kapsülü, derived ürün kapsülü ve `Termivar-Offline-Capsule-Derivation-phase34-2026-11-13.zip` kaynak teslimi farklı artefact'lardır. Yukarıdaki 20253 B / dört üye / SHA256 yalnız derived ürün kapsülüne aittir. Son kaynak teslim ZIP boyutu/üye sayısı/SHA256 root paketlemesinde ayrıca ölçülüp dış delivery manifestinde tutulur; burada ölçülmemiş teslim kimliği uydurulmaz. Source manifest kendi digest'ini kapsamaz ve öz hash döngüsü oluşturulmaz.

İzinli iki ürün çağrısı ve dar gerçek çıktı incelemesi tamamlandı. Önceki kaynak koruması ve ölçülmüş teslim kapanınca durulur. Phase35/yeni mikro özellik, test/build/native runtime, otomatik paylaşım veya public release başlatılmaz.
