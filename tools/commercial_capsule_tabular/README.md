# Offline capsule tabular export

**OFFLINE DEMONSTRATION — TABULAR DISCLOSURE ONLY — NO CURRENT SOURCE VERIFICATION**

Bu bağımsız offline araç Phase34 kapsülündeki seçilmiş reference durumları ve yalnız izinli projection metadata'sı için kapalı JSON dataset, iki CSV ve okunabilir özet üretir. `exported_projection ⊆ validated_capsule_projection`. Bloke referans reference register'da durumuyla görünür, projection register'da olumlu candidate/file satırı kazanmaz. CSV üretmek metadata güncelliğini veya güveni yükseltmez.

Kaynak hazırlığında Phase35 ürün çağrısı **0**. Henüz dataset/CSV/inspector başarısı, yeni dosya veya teslim ZIP'i boyutu/SHA256 iddia edilmez. Kaynak Phase34 metadata'sı yeni ürün başarısı yerine geçirilmez.

## Kaynak ve kapalı veri modeli

Tek kaynak kapsül `outputs/phase34-capsule-derivation/derived-reference-capsule.zip`, kayıtlı **20253 B / 4 üye**, SHA256 `d3eea4c7946d45290c4876ac8b6d8ca5172297933b7681812863158bf845c01d`. Scope gerçek açık ZIP byte'larına bağlanır. Korunmuş Phase34 `load_validated_source` / `read_validated_source` ve Phase33 güvenli owner yolu yeniden kullanılır; ikinci ZIP parser veya eski CLI çalıştırması yoktur.

`read_validated_source(snapshot)` tam capsule modeli ile ZIP kimliğini ayrı `(capsule, identity)` değerleri olarak döndürür. Snapshot immutable actual byte taşır, exact-type okunur ve yeniden owning doğrulanır. Phase33 `inspect_bundle(path, ids)` ise `(inspection, lookup)` döndürür; lookup tam model sayılmaz. Caller'ın allow/validated etiketi otorite değildir.

Scope `termivar-offline-capsule-tabular-scope/v1`, tam beş alan: `schema_version`, `mode`, `source_capsule_sha256`, `export_reference_ids`, `export_constraints`. Yalnız `mode=demo`, kaynakta bulunan 1–8 farklı ID. Boş/duplicate/unknown seçim, digest uyuşmazlığı veya unknown alan/version kapalı hata. Scope candidate/observation/override/path/gerçek kullanıcı yetkisi/keyfî metadata taşımaz.

Dataset `termivar-offline-capsule-tabular-dataset/v1` yalnız doğrulanmış kapalı alanlardan oluşturulur. `reference_records` tam dört alan taşır: reference ID, disclosure status, projection count, interpretation limitations. `projection_records` yalnız provided referanslardan gelen mevcut 11 alanı aynen korur. Kaynak nesne kontrolsüz serialize edilmez; null/zero ayrımı ve kaynak status değişmez. Reference/projection/unique candidate/unique file sayımları ayrı türetilir. Bir reference kaydı olumlu file metadata açıklama yetkisi değildir.

## CSV encoding

`reference-register.csv` dört sabit sütun, `projection-register.csv` mevcut 11 sabit sütun kullanır. Header normal sabit ASCII sütun adlarıdır; bütün DATA hücreleri `j:` + compact ASCII JSON olarak kodlanır. CSV parser'ın çıkardığı mantıksal hücre metni `j:null`, `j:""`, `j:0`, `j:["a"]` için farklıdır. Kaynak string `j:null` ise hücre `j:"j:null"` olur. Koleksiyon sırası kapalı modelden korunur; decoding tipli değeri geri verir. Bu encoding kaynak değeri değildir ve formül evaluate etme izni vermez.

Standart `csv` writer, comma delimiter, `QUOTE_ALL`, LF, UTF-8/no-BOM kullanılır. CSV quoting'i JSON cell encoding'den ayrı katmandır. DATA hücresi `j:` ile başladığından source `=`, `+`, `-`, `@`, newline/tab/control başlangıcı ham hücre başı olarak yazılmaz. JSON control kaçışları gerçek multiline/tab değildir. Encoding genel spreadsheet uygulamalarında import kabulünün yapıldığı anlamına gelmez. Hücre 4096 B, satır 65536 B, CSV başına 128 KiB limitinde truncation yoktur.

## Planlanan exact iki ürün çağrısı

Henüz çalıştırılmış başarı kaydı değildir. Phase35 bütçesi en fazla iki yeni çağrı; ikinci yalnız ilk exit 0, eksiksiz beş output ve gerçek CSV'lerin manuel incelemesinden sonra. Başarısız çağrı tüketilir; retry/üçüncü çağrı, gizli test veya eski CLI tekrarı yoktur. Phase20–34 ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_capsule_tabular/assemble_tabular.py --source-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --scope security-platform/tools/commercial_capsule_tabular/examples/demo_tabular_scope.json --output-dir outputs/phase35-capsule-tabular
```

```text
python -I -B security-platform/tools/commercial_capsule_tabular/inspect_tabular.py --source-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --dataset outputs/phase35-capsule-tabular/tabular-dataset.json --references outputs/phase35-capsule-tabular/reference-register.csv --projections outputs/phase35-capsule-tabular/projection-register.csv --summary outputs/phase35-capsule-tabular/tabular-summary.md --manifest outputs/phase35-capsule-tabular/manifest.json --output outputs/phase35-capsule-tabular/inspection-summary.json
```

Assembly `tabular-dataset.json`, `reference-register.csv`, `projection-register.csv`, `tabular-summary.md`, `manifest.json` üretir. Manifest gerçek ilk dört payload'ı bağlar, kendisini kapsamaz. İkinci çağrı `inspection-summary.json` üretir; yalnız kaynak kapsül ile kapalı dataset/iki CSV/MD/manifest ilişkisini değerlendirir. Source dosyası/guard, producer veya native doğrulaması değildir.

## Sınırlar, bağımlılıklar ve açık kabuller

Scope 32 KiB, kaynak ZIP 256 KiB, üye 128 KiB, expanded toplam 256 KiB, tam dört üye/ratio 20/reference 8/projection 64; dataset, her CSV ve MD 128 KiB; manifest 64 KiB/toplam açık girdi 1 MiB; JSON depth 12/node 20.000/text 512. Daha sıkı Phase33 owner ZIP limitleri korunur. Strict UTF-8/JSON, duplicate/unknown key/schema, float/NaN/Infinity/bool-as-int ve duplicate record reddi; traversal/symlink/encryption/unsupported compression reddi. Yeni/boş output, overwrite yasağı ve partial-write başarısı üretmeme koşulu vardır; keyfî URL/path izlenmez.

Yeni araç standalone binary veya production wheel değildir; korunmuş Phase34 adapter/budget ve Phase33 owner reader/validator/renderer/manifest modüllerine bağlıdır. Kaynak paket eski modül ağaçlarını veya önceki kapsülleri kopyalamaz. Kapsül doğrulaması ve CSV üretimi aynı yerel offline bağlamdadır; ikinci offline host ve gerçek spreadsheet uygulamasında import kabulü NOT_RUN.

`demo_only=true`; mevcut 18 false güven alanı korunur. Source/context/independent observation ve upstream guard doğrulaması false; producer/signature, compiler/module closure, ownership, insan/hukukî/müşteri/production/release otoritesi kazanılmaz. Eski upstream `fresh_*` kodu yeni gözlem veya TTL garantisi değildir. Minimizasyon şifreleme/anonimlik değildir; ID/hash hassas olabilir. Otomatik sender, risk skoru, API veya GUI yoktur.

NOT_RUN: hostile/duplicate JSON/UTF-8, yanlış digest/ID, bloke projection enjeksiyonu, adversarial CSV formula/control/multiline/null-empty-zero, değiştirilmiş kapsül/ZIP bomb/traversal/symlink/limit, permission/crash/partial write/repeat determinism, ikinci offline host, gerçek spreadsheet import, Phase31 guard/source freshness/compiler/module closure/ownership/native/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemede kalır. Koruma kodu saldırgan girdi kabulü değildir.

Belgeler: [sözleşme](../../docs/commercial/operations/phase35/TABULAR_CONTRACT.tr.md), [disclosure ve encoding](../../docs/commercial/operations/phase35/DISCLOSURE_AND_ENCODING.tr.md), [kaynak sınırı](../../docs/commercial/operations/phase35/PORTABLE_SOURCE_BOUNDARY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase35/DEMO_DELIVERY.tr.md).

Kaynak teslim ZIP'i `Termivar-Offline-Capsule-Tabular-phase35-2026-11-13.zip`; kaynak ürün kapsülünden farklıdır. Ölçülmemiş kimlik uydurulmaz; final ZIP kimliği ayrı dış delivery manifestinde tutulur. Phase7–34, backend/operator-console/HBF/Altay/native/auth/DB/roller/wheel/lock/lisans korunur. İzinli iki çağrı, dar inceleme ve ölçülmüş teslim bitince durulur; Phase36/yeni mikro özellik/otomatik paylaşım başlatılmaz.
