# Phase37 teslim kaydı — gerçek file index bekliyor

**OFFLINE DEMONSTRATION — DISCLOSED METADATA ONLY — NO CURRENT SOURCE VERIFICATION**

Bu belge kaynak hazırlığı kaydıdır. Phase37 ürün çağrısı henüz **0**. Yeni index/lookup/receipt/inspector başarısı, output veya kaynak ZIP boyutu/SHA256 iddia edilmez. Phase36 kaynak beklentisi yeni ürün sonucu değildir. Actual tarih ve kaynak ZIP etiketi **2026-11-14**.

Başlangıç Phase36 HEAD `230b4f7d761401b775832b65766fd4b4906df93c`, tree `54c452f2923f30c898caced84cf0b7926bee0354`; baseline 408 artefact, 373 korunacak kaynak, 21 asset ve 60030 B wheel'i korur. Yeni kaynak ZIP'i eski arşiv/CSV/kapsül/Rust/binary/wheel/cache/DB/dependency kodu veya gizli veri kopyalamaz.

## Gerçek beş Phase36 source kimliği

Kaynak `outputs/phase36-tabular-inbox/` altındaki beş açık dosyadır. Bunlar eski embedded Phase35 provenance kimlikleri değildir; yeni request gerçek Phase36 inbox/manifest SHA256 değerlerine bağlanır.

| Kaynak dosya | Bayt | SHA256 |
| --- | ---: | --- |
| `typed-inbox.json` | 5676 | `8f42ae940dfe34b73065a365be753c7f424850268f0d7981ead20365107aaea2` |
| `reference-query.json` | 5208 | `899e5657b8695cb43a9e83de85adfe36e1d913017a5fb910a520cc27a2cea4ce` |
| `import-receipt.json` | 3311 | `09bda63816bbd137efc648a40469c7125ce5e8844c833889e9af9f3c3d22b3f8` |
| `inbox-summary.md` | 13728 | `1058437236dac56a90f57536a7e65250604f0e6748ed4629ece5e44ee2ff55bf` |
| `manifest.json` | 3485 | `671a192258c0a52eab3bf5fc0de3f0aa2a53346e782c18eb81d3459708c9d0ad` |

Kaynak manifest gerçek dört payload'ı bağlar. Owner üç model ilişkisi, inbox'tan yeniden türetilen query/receipt, MD ve manifest eşliği başarılıysa yeni immutable source snapshot kullanılabilir. CSV/kapsül/guard/native kaynak veya eski CLI açılmaz.

## Gerçek görünür File ID seçimi

| Kaynak typed projection | Gerçek metadata File ID |
| --- | --- |
| outcome kayıtlı present projection | `candidate-file-9230e44e0642dff1b64663ebd9e20da0c589d22ca1cd224f09b8c954b4328370` |
| outcome kayıtlı absence projection | `candidate-file-9a67f54741d040e044cb2e94b227515bd0c9b595e8f6eae0d896e70ea664ec9a` |

Demo bu iki gerçek File ID'yi birlikte ister. Beklenen kaynak sayımı iki reference/bir provided/bir withheld/iki typed projection; görünür sonuç iki File ID, tek outcome referansı, bütün iki projection, bir present/bir absence. Bu sayımlar gerçek inbox'tan türetilmeli, başarı fixture'ı olmamalıdır. Bloke referans file index'e alınmamalı; olumlu alt candidate/file/hash/byte kopyalanmamalı. File ID fiziksel inode/Windows identity/path değildir; absence File ID eşleşmesi dosyanın şimdi var olduğunu söylemez.

## Planlanan exact iki ürün çağrısı

Aşağıdakiler henüz çalıştırılmış başarı kaydı değildir. İlk çağrı exit 0 ve eksiksiz beş output üretirse index/lookup/receipt/MD manuel incelenir; ancak sonra ikinci çalışır. Phase37 en fazla iki çağrı; başarısız çağrı tüketilir, retry/üçüncü/preflight helper/test runner/eski CLI yoktur. Phase20–36 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_file_reference_index/assemble_file_index.py --inbox outputs/phase36-tabular-inbox/typed-inbox.json --source-query outputs/phase36-tabular-inbox/reference-query.json --receipt outputs/phase36-tabular-inbox/import-receipt.json --source-summary outputs/phase36-tabular-inbox/inbox-summary.md --source-manifest outputs/phase36-tabular-inbox/manifest.json --request security-platform/tools/commercial_file_reference_index/examples/demo_file_lookup_request.json --output-dir outputs/phase37-file-reference-index
```

```text
python -I -B security-platform/tools/commercial_file_reference_index/inspect_file_index.py --index outputs/phase37-file-reference-index/file-reference-index.json --lookup outputs/phase37-file-reference-index/file-reference-lookup.json --receipt outputs/phase37-file-reference-index/index-source-receipt.json --summary outputs/phase37-file-reference-index/file-index-summary.md --manifest outputs/phase37-file-reference-index/manifest.json --output outputs/phase37-file-reference-index/inspection-summary.json
```

Gerçek üretim sonrası altı output'un tam byte/SHA256 değerleri, source/index/lookup ayrı sayımları, whole-reference tekilliği/null gözlemleri, iki actual exit code ve yalnız beş yeni dosyayı okuyan inspector kapsamı eklenecektir. Üretim source snapshot'ı ile son README/DEMO actual güncellemesi ayrılır.

## İnceleme sınırı ve açık kabuller

Yeni source receipt beş gerçek Phase36 artefact kimliği/schema ve aggregate source/index sayımlarını taşır; projection audit kopyası değildir. Yeni inspector yalnız index/lookup/receipt/summary/manifest model/ref/file/candidate/whole-packet/count/MD ve dört payload byte bağını inceler. Phase36 dosyalarını yeniden açmaz ve source import davranışını bağımsız doğrulamaz. `content_consistent` yalnız yeni çıktıların iç tutarlılığıdır; source freshness/producer/guard/kapsül doğruluğu değildir.

Nested `trust_flags` içindeki aynı 18 false alan ve top-level `demo_only=true` korunur. Kaynakta görünmeyen ilişkiler oluşturulmaz. Null absence byte/hash, integer count sıfırı ve sıfır-byte source dosyası birbirine çevrilmez. Hash imza veya producer attestation değildir; File ID fiziksel file identity değildir.

NOT_RUN: hostile/duplicate JSON/UTF-8, wrong digest, unknown/nonvisible File ID, duplicate/çelişkili projection, yanlış reference/file/candidate bağı, tek File ID ile whole-reference runtime varyantı, shared-file multiple-reference, modified inbox, limit/permission/crash/partial write/repeat determinism, ikinci offline host; Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Demo iki ID'yi birlikte sorar; ayrı single-file/shared/unknown/adversarial fixture oluşturulmaz. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemede; file:// yasağı korunur. Kodda kural bulunması bu kabullerin geçtiği anlamına gelmez.

Kaynak teslim adı `Termivar-Offline-File-Reference-Index-phase37-2026-11-14.zip`. Ölçülmemiş ZIP boyut/üye/SHA256 uydurulmaz; final kimlik ayrı dış delivery manifestinde tutulur. Source manifest kendi digest'ini kapsamaz ve öz hash döngüsü oluşturulmaz. Phase7–36 ve backend/operator-console/native/HBF/Altay/auth/DB/roller/wheel/lock/lisans korunur.

İzinli iki çağrı, dar inceleme ve ölçülmüş teslim bitince durulur. Phase38/yeni mikro özellik/native/otomatik test/release başlatılmaz.
