# Offline Pilot Variant & Dependency Exposure Workbench

**DEMONSTRATION ONLY — PILOT VARIANT ANALYSIS — NO BUILD OR DISTRIBUTION AUTHORIZED**

İki açık kaynak kapsamını karşılaştıran bağımsız, Python standart kütüphanesiyle
çalışan offline karar destek aracıdır. Native assessment adayı iki Termivar kaynak
bileşenini; geniş aday aynı iki bileşen ve sekiz offline destek aracını seçer.
Bu seçim bir binary, SKU, müşteri paketi veya gerçek pilot GO değildir.

[Sözleşme](../../docs/commercial/operations/phase26/VARIANT_CONTRACT.tr.md),
[dependency exposure](../../docs/commercial/operations/phase26/DEPENDENCY_EXPOSURE.tr.md),
[lisans/readiness](../../docs/commercial/operations/phase26/LICENSE_AND_READINESS.tr.md),
[güven sınırı](../../docs/commercial/operations/phase26/TRUST_BOUNDARY.tr.md),
[gerçek teslim ve NOT_RUN](../../docs/commercial/operations/phase26/DEMO_DELIVERY.tr.md).

Phase24'ün 451 dependency kaydı ile Phase25'in 461 lisans subject'i ayrı tutulur.
Declaration/lock kayıtları unique package sayısı değildir. Metadata'da gerçek
component→dependency kenarı yoktur: `explicit_component_link` bu sözleşmede
üretilemez. F referansı üyeliği yalnız olası kaynak ilişkisini destekler.
306 whole-workspace lock kaydı gerçek build closure değildir. Sekiz helper'ın
ortak pyproject metadata'sı 44 excluded backend kaydını helper runtime
bağımlılığına dönüştürmez. Bilinmeyen ilişki, dependency yokluğu anlamına gelmez.

Tek yerel MIT evidence yalnız mevcut L0001 bağına aittir. İki önceki scoped MIT
beyanı, 459 unknown lisans ve tüm insan inceleme gereksinimleri korunur.
Evidence bulunması redistribution, hukukî kabul veya producer verification değildir.
Seçilmeyen kaynak bileşeni, gerçek paket içinden çıkarılmış sayılmaz.

Girdi `examples/demo_variant_scope.json` yalnız demo modunu destekler. On açık
dosyanın beklenen sürüm/boyut/SHA256 metadata'sını taşır; yollar CLI'da seçilir.
İki Markdown summary'nin açık seçilmesi eski dört payload manifestlerinin gerçek
byte bağlarını doğrulamak içindir. Scope JSON içindeki hiçbir path/URL izlenmez.
Eski kaynak ağaçları, package cache, lisans dosyaları veya git yeniden okunmaz.
Hash/pointer/row digest ile kurulan kaynak bağı paket üreticisi attestation değildir.

Workspace kökünden iki ayrı komut aşağıdadır. Phase26 tesliminde bu bütçe en fazla
iki gerçek çağrıdır; teslim belgesindeki sayaç tüketildikten sonra yeniden çalıştırma.
İkinci komut yalnız birinci komut başarılıysa izinlidir. Üçüncü çağrı yoktur.

```powershell
python -I -B security-platform/tools/commercial_pilot_variants/assemble_variants.py `
  --scope security-platform/tools/commercial_pilot_variants/examples/demo_variant_scope.json `
  --composition-inventory outputs/phase24-composition/composition-inventory.json `
  --composition-dependencies outputs/phase24-composition/dependency-license-ledger.json `
  --composition-constraints outputs/phase24-composition/release-constraints.json `
  --composition-summary outputs/phase24-composition/composition-summary.md `
  --composition-manifest outputs/phase24-composition/manifest.json `
  --evidence-ledger outputs/phase25-license-evidence/license-evidence-ledger.json `
  --evidence-queue outputs/phase25-license-evidence/review-queue.json `
  --evidence-conflicts outputs/phase25-license-evidence/binding-conflicts.json `
  --evidence-summary outputs/phase25-license-evidence/evidence-summary.md `
  --evidence-manifest outputs/phase25-license-evidence/manifest.json `
  --output-dir outputs/phase26-pilot-variants

python -I -B security-platform/tools/commercial_pilot_variants/inspect_variants.py `
  --analysis outputs/phase26-pilot-variants/variant-analysis.json `
  --dependencies outputs/phase26-pilot-variants/dependency-exposure.json `
  --licenses outputs/phase26-pilot-variants/license-readiness.json `
  --summary outputs/phase26-pilot-variants/variant-comparison.md `
  --manifest outputs/phase26-pilot-variants/manifest.json `
  --output outputs/phase26-pilot-variants/inspection-summary.json
```

İlk komut üç sürümlü JSON, deterministik Markdown ve dört payload'ın manifestini
yeni dizine yazar. Inspector yalnız beş yeni açık dosyadan iç model/byte tutarlılığı
çıkarır; eski dosyaları, evidence'i veya source producer'ı yeniden doğrulamaz.
`content_consistent` test, build, runtime veya hukukî kabul değildir. Hatalar
sabit/sınırlı mesaj ve nonzero exit ile biter; eski çıktı başarı gibi gösterilmez.
Hata kısmi yeni dizin bırakabilir; manifest tek başına yetki vermez.

Scope128KiB; eski JSON başına1MiB, Markdown512KiB, manifest64KiB; scope dahil
açık okuma6MiB;4varyant/6çift/64bileşen/2000dependency+lisans kaydı. Yeni JSON4MiB,
Markdown512KiB; mevcut bounded JSON depth16/node120000/text2MiB/string2048
korunur. UTF-8/BOM/duplicate/noninteger/nonfinite ve bilinmeyen alan/sürüm reddi;
symlink/reparse/traversal/hardlink ve kaynak değişimi kontrolleri bulunur.
Bu kontroller saldırgan filesystem veya girdi kabulü yapıldığı anlamına gelmez.

Ürün ağ, resolver, native scanner/runtime, backend, console, wheel, installer,
test/build, onay veya gerçek ticari dağıtım yolu içermez. Metadata bile hassas
olabilir; alan allowlist'i secret detection/anonimlik garantisi değildir. Çıktıya
ham source/LICENSE/lock metni veya yerel mutlak kök taşınmaz. Phase7–25 değişmez.
