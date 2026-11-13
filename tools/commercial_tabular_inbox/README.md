# Offline tabular inbox ve typed reference query

**OFFLINE DEMONSTRATION — TYPED CSV IMPORT ONLY — NO CURRENT SOURCE VERIFICATION**

Bu bağımsız offline araç beş Phase35 aktarım dosyasından iki CSV'yi gerçekten parse ederek typed reference/projection kayıtları oluşturur. Kaynak dataset JSON yalnız sahip sözleşmesi ve alan/tür/değer karşılaştırmasıdır; JSON kayıtlarını kopyalamak CSV import değildir. Kapsül ZIP'i, native kaynak veya Phase31/32 guard açılmaz. Query yalnız içe alınmış immutable inbox üzerinde açık reference ID'lerini kullanır.

Kaynak hazırlığında Phase36 ürün çağrısı **0**. Henüz typed inbox/query/receipt/inspector başarısı veya yeni dosya/ZIP boyutu/SHA256 iddia edilmez. Actual çalışma kayıtlarında istemci tarihi **2026-11-14** kullanılır; görevde istenen kaynak ZIP'in `2026-11-13` dosya adı etiketi aynen korunur.

## Gerçek kaynak ve doğrulama sırası

Yalnız beş açık Phase35 girdisi: `tabular-dataset.json`, `reference-register.csv`, `projection-register.csv`, `tabular-summary.md`, `manifest.json`. Manifest gerçek ilk dört payload'ın boyut/SHA256 bağını taşır; kendi hash'ini içermez. Request kaynak manifestin gerçek hash'ine bağlanır.

Sıra: bounded güvenli okuma ve gerçek manifest bağı; mevcut `commercial_capsule_tabular.tabular_contracts.validate_dataset`; mevcut `output_renderer.render_summary` byte eşliği; yeni typed CSV parsing; gerçek parsed record'larla dataset alan/tür/değer eşliği; mevcut CSV renderer ile tam byte reconciliation; ancak sonra immutable typed import/inbox. Owning modeller ve daha sıkı sınırlar gevşetilmez. Eski CLI veya kapsül reader çalıştırılmaz; ikinci CSV/JSON framework veya guard oluşturulmaz.

Reader standart `csv` modülünü kullanır; header/sütun/satır/QUOTE_ALL/LF/no-BOM ve her DATA hücresinin `j:` + canonical compact ASCII JSON biçimi kontrol edilir. Mevcut `decode_cell` / `encode_cell` typed/canonical kuralları korunur. Başarılı `csv.reader(strict=True)` tek başına canonical kabulü değildir. Tam yeniden üretilen CSV byte eşliği zorunludur. Bozuk/ek satır veya CRLF sessizce temizlenmez; kısmi kabul yoktur.

## Sözleşmeler ve sorgu

Request `termivar-offline-tabular-inbox-request/v1` tam beş alan taşır: `schema_version`, `mode`, `request_reference`, `source_manifest_sha256`, `requested_reference_ids`. Mode yalnız `demo`, 1–8 farklı mevcut ID. Boş/duplicate/unknown ID veya yanlış manifest hash'i kapalı hatadır. Query ifadesi, yeni candidate/path/override veya gerçek kullanıcı yetkisi yoktur.

Inbox `termivar-offline-tabular-inbox/v1`; query yalnız bu inbox'ın kayıtlarından üretilir. Reference kayıtları mevcut dört, projection kayıtları mevcut 11 kapalı alanı korur. Reference-to-projection candidate ilişkileri ve sayımları gerçek parsed kayıtlardan türetilir. Caller'ın `validated=true`/`trusted=true`/`guard_passed=true` etiketi otorite değildir. Bloke referansın projection sayısı sıfır, sorgu listesi `projections=[]`; olumlu child metadata başka audit alanına taşınmaz. Projection'sız referans otomatik source missing sayılmaz.

Receipt `termivar-offline-tabular-import-receipt/v1` gerçek beş artefact kimliği, kaynak schema, header/kayıt sayısı ve import sırasında kaydedilen canonical CSV/dataset eşliğini taşır; projection payload kopyası değildir. Receipt dijital imza, üretici doğrulaması, eski guard kabulü, source freshness veya ikinci host aktarım kanıtı değildir. Bir saldırgan CSV/dataset/manifesti birlikte değiştirip yeniden hash'leyebilir; yalnız iç hash eşliği özgün kaynağın güvenilirliği değildir.

## Tür ve formula sınırı

`j:null`, `j:""`, `j:0`, `j:"0"`, `j:[]` farklı typed değerlerdir; alan sözleşmesi ayrıca izin vermelidir. Mevcut Phase35 DATA hücre sözleşmesi boolean kabul etmez: `false` integer sıfır yapılmaz, reddedilir. Modelin ortak güven bayraklarındaki false ise zorunlu boolean metadata'dır. Koleksiyonlar mevcut canonical JSON string-array sırasıyla korunur. Absence byte/hash null kalır; bilinen sıfır-byte dosya veya boş stringe çevrilmez.

Importer formül, expression, `eval` veya shell çalıştırmaz; `j:` kaldırılıp ham değer CSV'ye yeniden yazılmaz. Source control/newline/tab kaçışları ve canonical encoding gevşetilmez. Gerçek Excel/LibreOffice import veya adversarial formula/control/null/zero kabulü bu fazda yapılmaz.

## Planlanan exact iki ürün çağrısı

Aşağıdakiler henüz başarı kaydı değildir. Phase36 bütçesi en fazla iki çağrı. İkinci yalnız ilk exit 0, eksiksiz beş gerçek output ve manuel inbox/query/receipt/null incelemesinden sonra. Başarısız çağrı tüketilir; retry/üçüncü çağrı, test runner veya eski CLI tekrarı yoktur. Phase20–35 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_tabular_inbox/assemble_inbox.py --dataset outputs/phase35-capsule-tabular/tabular-dataset.json --references outputs/phase35-capsule-tabular/reference-register.csv --projections outputs/phase35-capsule-tabular/projection-register.csv --source-summary outputs/phase35-capsule-tabular/tabular-summary.md --source-manifest outputs/phase35-capsule-tabular/manifest.json --request security-platform/tools/commercial_tabular_inbox/examples/demo_import_request.json --output-dir outputs/phase36-tabular-inbox
```

```text
python -I -B security-platform/tools/commercial_tabular_inbox/inspect_inbox.py --inbox outputs/phase36-tabular-inbox/typed-inbox.json --query outputs/phase36-tabular-inbox/reference-query.json --receipt outputs/phase36-tabular-inbox/import-receipt.json --summary outputs/phase36-tabular-inbox/inbox-summary.md --manifest outputs/phase36-tabular-inbox/manifest.json --output outputs/phase36-tabular-inbox/inspection-summary.json
```

Assembly ilk beş output'u üretir: typed inbox, query, receipt, Markdown, manifest. Manifest gerçek ilk dört payload'ı bağlar, kendisini kapsamaz. Inspector yalnız beş yeni açık output'u okuyup üç model/ref/count/query/receipt/MD/manifest ilişkisini değerlendirir; Phase35 kaynak CSV'lerini tekrar parse etmez ve import davranışını bağımsız doğrulamaz. `content_consistent` yalnız yeni çıktıların iç tutarlılığıdır; kapsül, source freshness, producer veya guard doğruluğu değildir.

## Limitler, kod bağımlılığı ve açık kabuller

Request 32 KiB; kaynak dataset/her CSV/MD 128 KiB, kaynak manifest 64 KiB, toplam açık girdi 1 MiB. Inbox 256 KiB, query/MD 128 KiB, receipt 64 KiB; reference 8/projection 64; depth 12/node 20.000/text 512. Mevcut DATA hücresi 4096 B/satır 65536 B sınırı korunur. Strict UTF-8/JSON; duplicate/unknown schema/field/record ve invalid integer/bool/float reddi. Yeni/boş output, overwrite/otomatik silme yasağı, limitte truncation ve partial-write başarısı yoktur. JSON path/URL başka dosya açtırmaz.

Bu kaynak delta paketi standalone binary veya production wheel değildir. Korunmuş Phase35 owner validator/encoder/renderer/manifest, Phase33 kapalı JSON/alan primitive'leri ve mevcut güvenli okuma bütçesi/dosya yardımcılarının kodu gereklidir; bu kod bağımlılığı eski kapsül veya özgün çalışma alanı verisini açmak değildir. Yeni ZIP eski dependency kaynaklarını veya önceki veri/ZIP'lerini kopyalamaz. Gerçek ikinci offline host'ta kurulum/aktarım kabulü NOT_RUN kalır. Backend/operator-console, API/GUI/DB/scheduler/watcher veya yeni servis yoktur.

`demo_only=true`; mevcut 18 false güven alanı korunur. Source/context/independent observation, upstream guard, producer/ownership/production/release false. Compiler/native/insan/hukukî/müşteri kabulü kazanılmaz. Kayıtlı `fresh_*` kodu yeni gözlem/TTL garantisi değildir. Kimlik/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.

NOT_RUN: hostile/duplicate JSON/UTF-8/BOM, adversarial formula/quoting/header/sütun/canonical `j:`/null-empty-zero-string-boolean, duplicate reference/projection, yanlış manifest/hash veya değiştirilmiş CSV/dataset, limit/permission/crash/partial write/repeat determinism, ikinci offline host, spreadsheet import, Phase31 guard/source freshness/Rust compiler/module closure/ownership/native/producer/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Kaynakta koruma olması bu kabullerin geçtiği anlamına gelmez.

Belgeler: [typed import](../../docs/commercial/operations/phase36/TYPED_IMPORT_CONTRACT.tr.md), [CSV reconciliation](../../docs/commercial/operations/phase36/CSV_RECONCILIATION.tr.md), [reference query](../../docs/commercial/operations/phase36/REFERENCE_QUERY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase36/DEMO_DELIVERY.tr.md).

Kaynak ZIP adı görev etiketine göre `Termivar-Offline-Tabular-Inbox-phase36-2026-11-13.zip`; gerçek kayıt tarihi 2026-11-14'tür. Ölçülmemiş ZIP kimliği uydurulmaz; final boyut/üye/SHA256 dış delivery manifestinde tutulur. Phase7–35 ve backend/operator-console/native/HBF/Altay/auth/DB/roller/wheel/lock/lisans korunur. İzinli iki çağrı, dar inceleme ve ölçülmüş teslim bitince durulur; Phase37/yeni mikro özellik/otomatik test/native/release başlatılmaz.
