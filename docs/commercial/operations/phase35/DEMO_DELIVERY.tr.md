# Phase35 gerçek tabular teslim kaydı

**OFFLINE DEMONSTRATION — TABULAR DISCLOSURE ONLY — NO CURRENT SOURCE VERIFICATION**

2026-11-13 tarihinde iki izinli Phase35 ürün çağrısı tamamlandı: assembly **exit 0**, bağımsız içerik inspector'ı **exit 0**. İkinci çağrı başarılı assembly'nin eksiksiz beş gerçek output'u, CSV satırları/encoding/null ayrımı manuel incelendikten sonra çalıştı. Bütçe **2/2 tüketildi ve kapandı; kalan çağrı 0**. Retry/üçüncü çağrı, gizli test veya eski CLI tekrarı yoktur. Phase20–34 ve Phase24/29 insan istisnaları kapalıdır.

Başlangıç Phase34 HEAD `78e62ba2e6169d1cd5b7d5d60043cc5d900a1d94`, tree `0f9c63fc7be047c90e236638c58b7425712fbdf8`. Üretim source commit'i `e188ef96a02f2996ea78ea029e72d10a77557fa4`, tree `6adf08f408acd1bc71e155ff360bf9d00d4d2661`. Üretim sonrası yalnız README ve bu belge actual sonuçlara göre güncellendi; kod ve diğer üç belge donduruldu. Phase7–34 kaynak/çıktı/arşiv/manifestleri, backend/operator-console/HBF/Altay/native/auth/DB/roller/wheel/lock/lisans korunur. Yeni kaynak ZIP'i önceki kapsül/arşivleri, raw Rust, binary/wheel/cache/DB veya özel dosyaları kopyalamaz.

## Gerçek kaynak ve seçilen referanslar

Kaynak `outputs/phase34-capsule-derivation/derived-reference-capsule.zip`, **20253 B / 4 üye**, SHA256 `d3eea4c7946d45290c4876ac8b6d8ca5172297933b7681812863158bf845c01d`. Scope bu gerçek byte kimliğine bağlanır; ZIP hash'i producer imzası veya güncel filesystem kanıtı değildir.

| Seçilen bağlam | Gerçek reference ID | Dataset'te korunan durum | Gerçek projection |
| --- | --- | --- | ---: |
| outcome | `rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81` | `provided_limited_metadata` | 2 |
| authorization_review | `rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a` | `withheld_by_existing_guard` | 0 |

Gerçek dataset **2 reference = 1 provided + 1 withheld + 0 unavailable**, **2 projection ilişkisi, 2 benzersiz candidate, 2 benzersiz file**, **1 kayıtlı present + 1 absence** taşıdı. Reference CSV'de iki, projection CSV'de iki veri satırı oluştu; header'lar bu sayıya dahil değildir. Sayımlar kaynak kapsülden yeniden türetildi, başarı sabiti olarak kodlanmadı. Bloke referansın projection count değeri sıfır; olumlu candidate/file/hash/byte projection kaydı yoktur. Önceki fazda çıkarılan bağlamın ID/candidate/file/hash/byte değerleri bu kayda veya yeni output'a geri getirilmedi.

## Gerçek tamamlanan exact iki ürün komutu

Aşağıdakiler gerçek generation kaydındaki tamamlanmış iki çağrıdır; yeniden çalıştırma izni değildir. İlk çağrı exit **0**, eksiksiz beş gerçek output; sonra manuel CSV incelemesi; ikinci çağrı exit **0**. Actual exit kodları **[0,0]**, **2/2 bütçe kapalı, kalan çağrı 0**. Başarısız çağrı tüketilir; otomatik retry/üçüncü çağrı veya eski CLI çalıştırması yoktur.

```text
python -I -B security-platform/tools/commercial_capsule_tabular/assemble_tabular.py --source-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --scope security-platform/tools/commercial_capsule_tabular/examples/demo_tabular_scope.json --output-dir outputs/phase35-capsule-tabular
```

```text
python -I -B security-platform/tools/commercial_capsule_tabular/inspect_tabular.py --source-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --dataset outputs/phase35-capsule-tabular/tabular-dataset.json --references outputs/phase35-capsule-tabular/reference-register.csv --projections outputs/phase35-capsule-tabular/projection-register.csv --summary outputs/phase35-capsule-tabular/tabular-summary.md --manifest outputs/phase35-capsule-tabular/manifest.json --output outputs/phase35-capsule-tabular/inspection-summary.json
```

Inspector `internal_content_status=content_consistent`, kapsam `explicit_capsule_and_dataset_two_CSVs_summary_manifest_correspondence_only` raporladı. Kaynak kapsül kimliği, dataset/iki CSV/summary/manifest iç ilişkisidir; gerçek Phase31 guard, producer, source freshness veya native davranışın bağımsız kabulü değildir.

## Altı gerçek dış çıktı

Konum `outputs/phase35-capsule-tabular/`. Boyut/SHA256 değerleri gerçek disk byte'larından ölçüldü.

| Dosya | Bayt | SHA256 |
| --- | ---: | --- |
| `tabular-dataset.json` | 5817 | `e66548f773b74cb670503c645b1ca3cfe49aac1521b76855ed4da423ced39d5e` |
| `reference-register.csv` | 522 | `aa57d6576470a12c40900c365a1a46bf35734cd214c5c6ef9d5b00f165656390` |
| `projection-register.csv` | 1660 | `0fd3c41f41458704b684086318f8d823faf5edcfc23893620c5888154868a405` |
| `tabular-summary.md` | 10617 | `310e82ef1c5137f4ec1c763b06940653af7561a79e76983b001b432fe87d3a27` |
| `manifest.json` | 2714 | `22c5600604ce604a041fe976593fb99b6db2c111364f9268f29936277e0f389a` |
| `inspection-summary.json` | 3518 | `08a984dffebae65eaa6982f125c503712d0a12b58a857fb21906c0f0db7be467` |

Gerçek kaynak ZIP bağı **20253 B / SHA256 `d3eea4c7946d45290c4876ac8b6d8ca5172297933b7681812863158bf845c01d`**, kapsüldeki demo kimliği `DEMO-TERMIVAR-DERIVATION-034`. Bu kimlik yeni source observation veya producer attestation değildir. Scope aynı SHA256 beklentisini korur. Manifest gerçek ilk dört payload'ı bağlar; kendisini ve inspection output'unu kapsamaz.

## Gerçek CSV satırları ve tipli görünüm

| CSV | Header sütunu | Veri satırı | Header dahil toplam kayıt |
| --- | ---: | ---: | ---: |
| `reference-register.csv` | 4 | 2 | 3 |
| `projection-register.csv` | 11 | 2 | 3 |

Header sırası kapalı sözleşmedeki dört/11 alandır. Gerçek dosyalar UTF-8/no-BOM, comma delimiter, `QUOTE_ALL` ve LF kullandı; CR veya gerçek multiline hücre gözlenmedi. Header'lar normal sabit adlar, tüm DATA hücreleri `j:` + compact ASCII JSON görünümüdür. Collection hücreleri kaynak limitation string listelerinin kanonik JSON array metnini taşıdı.

Bloke referans yalnız reference register'da `withheld_by_existing_guard` ve projection count mantıksal hücresi **`j:0`** ile yer aldı; projection register'da satırı yoktur. Kayıtlı absence projection'ının byte ve hash mantıksal hücreleri **`j:null`** kaldı. Bu `j:0` referansın projection sayısıdır; sıfır-byte dosya gözlemi değildir. Kaynak null bilinmeyeni integer sıfır veya boş stringe çevrilmedi.

Empty string, literal-prefix çakışması, sıfır-byte dosya ve adversarial formula/control/multiline/null-empty-zero runtime senaryoları bu demo ile çalıştırılmadı. Gerçek spreadsheet uygulamasında import veya ikinci offline host kabulü yapılmadı. Kaynakta kodlanmış korumalar bu ayrı kabullerin yerine geçmez.

## Encoding ve inceleme sınırı

Dataset JSON tipli kaynak metadata'dır; CSV DATA hücresi `j:` + compact ASCII JSON görünümüdür. Mantıksal hücrelerde `j:null`, `j:""`, `j:0`, `j:["a"]` ve literal string için `j:"j:null"` çakışmaz. Header'lar normal sabit sütun isimleri; comma/QUOTE_ALL/LF/UTF-8/no-BOM. Newline/tab/control JSON kaçışı ve formula-leading kaynak metni `j:` sonrası string literal olur. Bu protokol açıklaması adversarial CSV/null/empty/zero veya gerçek spreadsheet import kabulü değildir.

Inspector mevcut sahip source reader yoluyla yalnız kaynak kapsül/dataset/iki CSV/summary/manifest arasındaki iç ilişkiyi değerlendirdi. `original_phase31_files_read=false`, `original_phase32_files_read=false`, `old_guard_reexecuted=false`, `native_source_files_read=false`, `original_source_artifact_bytes_independently_verified=false`, `source_producer_verified=false`, `legal_review_performed=false`, `spreadsheet_import_acceptance_performed=false` raporladı. `content_consistent` yalnız bu ilişkiyle sınırlıdır; producer, source freshness veya native doğruluk kazanılmaz.

Manuel incelemede iki reference/iki projection ayrımı, bloke olumlu alt metadata'nın taşınmaması, iki null hücresi, count zero, fixed header/sütun/satır sayıları ve dört payload manifest bağı gözlendi. Bu metadata/metin ve byte/hash incelemesidir; otomatik test veya hostile runtime kabulü değildir. Kapsülde bulunmayan metadata audit kaydına kopyalanmadı.

`demo_only=true`; mevcut 18 false güven alanı, source/context/independent observation ve upstream guard false kalır. Kayıtlı upstream `fresh_*` kodu yeni gözlem veya TTL garantisi değildir. CSV aktarımı kullanıcı/kurum yetkisi, hukukî onay, compiler/ownership veya release otoritesi sağlamaz.

NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest/ID, blocked projection enjeksiyonu, adversarial CSV formula/control/multiline/null-empty-zero, değiştirilmiş kapsül/ZIP bomb/traversal/symlink/limit, permission/crash/partial write/repeat determinism, gerçek ikinci offline host, gerçek spreadsheet import, Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Kaynakta koruma bulunması runtime güvenlik kabulü değildir.

Kaynak teslim ZIP'i `Termivar-Offline-Capsule-Tabular-phase35-2026-11-13.zip`; 20253 B kaynak ürün kapsülünden farklı artefact'tır. Son kaynak ZIP boyutu/üye sayısı/SHA256 root paketlemesinde ayrıca ölçülüp dış delivery manifestinde tutulur; burada ölçülmemiş kimlik uydurulmaz. Source manifest kendi digest'ini kapsamaz ve öz hash döngüsü oluşturulmaz.

İzinli iki ürün çağrısı ve dar gerçek çıktı incelemesi tamamlandı. Önceki kaynak koruması ve ölçülmüş teslim kapanınca durulur. Phase36/yeni mikro özellik, otomatik test/native çalışma, müşteri işlemi/otomatik paylaşım veya public release başlatılmaz.
