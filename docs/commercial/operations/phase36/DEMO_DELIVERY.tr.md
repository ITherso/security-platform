# Phase36 teslim kaydı — gerçek typed import bekliyor

**OFFLINE DEMONSTRATION — TYPED CSV IMPORT ONLY — NO CURRENT SOURCE VERIFICATION**

Bu belge kaynak hazırlığı kaydıdır. Phase36 ürün çağrısı henüz **0**. Gerçek typed inbox/query/receipt/inspector başarısı, yeni dosya veya ZIP boyutu/SHA256 iddia edilmez. Kaynak Phase35 sonuçları yeni typed import başarısı yerine geçirilmez. Actual çalışma kayıtlarının istemci tarihi **2026-11-14**; görevdeki kaynak ZIP etiketi `2026-11-13` olarak aynen korunur.

Başlangıç Phase35 HEAD `2cdb2495ee82c88921a49a71ac677bee7394f745`, tree `7a272eb822ae9a31d58f9030ccb7017cab8db7b0`. Phase7–35 kaynak/belge/çıktı/arşivleri, backend/operator-console/native/HBF/Altay/auth/DB/roller/wheel/lock/lisans korunur. Yeni kaynak ZIP'i eski arşiv/kapsül/dependency kodu/native/binary/wheel/cache/DB veya özel verileri kopyalamaz.

## Gerçek beş Phase35 girdi

Kaynak `outputs/phase35-capsule-tabular/` altındaki beş açık dosyadır. Byte kimlikleri eski aktarımı tanımlar; yeni Phase36 başarı sonucu değildir.

| Kaynak dosya | Bayt | SHA256 |
| --- | ---: | --- |
| `tabular-dataset.json` | 5817 | `e66548f773b74cb670503c645b1ca3cfe49aac1521b76855ed4da423ced39d5e` |
| `reference-register.csv` | 522 | `aa57d6576470a12c40900c365a1a46bf35734cd214c5c6ef9d5b00f165656390` |
| `projection-register.csv` | 1660 | `0fd3c41f41458704b684086318f8d823faf5edcfc23893620c5888154868a405` |
| `tabular-summary.md` | 10617 | `310e82ef1c5137f4ec1c763b06940653af7561a79e76983b001b432fe87d3a27` |
| `manifest.json` | 2714 | `22c5600604ce604a041fe976593fb99b6db2c111364f9268f29936277e0f389a` |

İlk manifest gerçek dört payload'ı bağlar, kendisini kapsamaz. Request bu manifestin gerçek SHA256 değerine bağlanır. Owner dataset doğrulaması/MD byte eşliği sonrası iki CSV gerçekten parse edilmeli; parsed typed kayıtlar dataset'le eşlenmeli ve owning CSV renderer ile tam byte reconciliation sağlanmalıdır. Dataset kayıtları kopyalanarak import yapılmış sayılmaz.

## Açık demo query referansları

| Seçilen bağlam | Gerçek reference ID | Kaynak durum | Kaynak projection |
| --- | --- | --- | ---: |
| outcome | `rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81` | `provided_limited_metadata` | 2 |
| authorization_review | `rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a` | `withheld_by_existing_guard` | 0 |

Yeni demo sayımları gerçek CSV'den türetilmeli: iki reference, biri provided/biri withheld, iki typed projection, bir kayıtlı present/bir absence. Absence byte/hash null kalmalı; bloke query `projections=[]` ve count sıfır kalmalı. Önceden çıkarılmış veya bloke olumlu candidate/file/hash/byte değerleri bu kayda veya yeni output'a kopyalanmaz. Beklenti başarılı fixture olarak kodlanmaz; sahte null/zero veya adversarial CSV örneği üretilmez.

## Planlanan exact iki ürün çağrısı

Aşağıdakiler henüz çalışmış başarı kaydı değildir. İlk çağrı exit 0 ve eksiksiz beş output üretirse gerçek inbox/query/receipt/typed null/blocked empty manuel incelenir; ancak sonra ikinci çağrı çalışır. En fazla iki yeni Phase36 çağrısı; başarısız çağrı tüketilir, retry/üçüncü çağrı/test runner veya eski CLI tekrarı yoktur. Phase20–35 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_tabular_inbox/assemble_inbox.py --dataset outputs/phase35-capsule-tabular/tabular-dataset.json --references outputs/phase35-capsule-tabular/reference-register.csv --projections outputs/phase35-capsule-tabular/projection-register.csv --source-summary outputs/phase35-capsule-tabular/tabular-summary.md --source-manifest outputs/phase35-capsule-tabular/manifest.json --request security-platform/tools/commercial_tabular_inbox/examples/demo_import_request.json --output-dir outputs/phase36-tabular-inbox
```

```text
python -I -B security-platform/tools/commercial_tabular_inbox/inspect_inbox.py --inbox outputs/phase36-tabular-inbox/typed-inbox.json --query outputs/phase36-tabular-inbox/reference-query.json --receipt outputs/phase36-tabular-inbox/import-receipt.json --summary outputs/phase36-tabular-inbox/inbox-summary.md --manifest outputs/phase36-tabular-inbox/manifest.json --output outputs/phase36-tabular-inbox/inspection-summary.json
```

Gerçek üretim sonrası altı output'un tam boyut/SHA256 değerleri, parsed import ve query sayımları, receipt/canonical reconciliation, iki actual exit code ve yalnız yeni beş dosyayı okuyan inspector kapsamı eklenecektir. Üretim kod snapshot'ı ile son README/DEMO actual-result güncellemesi ayrılır.

## İnceleme sınırı ve açık kabuller

Assembly beş eski Phase35 dosyasını gerçekten okuyacak; kapsül veya Phase31/32 guard açmayacak. Typed kayıtların kaynağı gerçek CSV parsing'dir. Yeni inspector yalnız yeni inbox/query/receipt/summary/manifest modellerini/ref/count/MD/dört payload byte bağını inceler; kaynak CSV'yi yeniden parse etmez ve import davranışını bağımsız doğrulamaz. `content_consistent` yalnız yeni çıktıların iç tutarlılığı olur; source freshness, producer veya kapsül doğruluğu değildir.

Receipt beş gerçek artefact kimliğini ve import anındaki canonical CSV/dataset eşliğini kaydeder; imza/üretici/insan yetkisi veya ikinci host aktarım kanıtı değildir. Saldırgan CSV/dataset/manifesti beraber değiştirip yeniden hash'leyebilir. `demo_only=true`; source/context/independent observation/upstream guard dahil 18 güven alanı false kalır. Null, zero ve string ayrımı korunur; mevcut DATA boolean desteklemez ve false sıfıra çevrilmez.

NOT_RUN: hostile/duplicate JSON/UTF-8/BOM; adversarial formula/quoting/header/sütun/canonical `j:`/null-empty-zero-string-boolean; duplicate reference/projection, wrong manifest/hash veya değiştirilmiş CSV/dataset; limit/permission/crash/partial write/repeat determinism; gerçek ikinci offline host, spreadsheet import, Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Koruma kodu bu kabullerin geçtiğini göstermez.

Kaynak teslim adı görevdeki etiketle `Termivar-Offline-Tabular-Inbox-phase36-2026-11-13.zip`. Actual çalışma kayıt tarihi 2026-11-14'tür. Henüz ölçülmemiş ZIP kimliği uydurulmaz; son boyut/üye/SHA256 ayrı dış delivery manifestinde tutulur. Source manifest kendi digest'ini kapsamaz ve öz hash döngüsü oluşturulmaz.

İzinli iki çağrı, dar inceleme ve ölçülmüş teslim bitince durulur. Phase37/yeni mikro özellik, otomatik test/native çalışma veya release başlatılmaz.
