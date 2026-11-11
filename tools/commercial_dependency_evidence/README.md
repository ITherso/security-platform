# Offline Direct Dependency Attribution & Source Evidence Graph

**DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED**

Bağımsız Python standart kütüphanesi aracı, Phase24/26 dosyalarıyla kimliği bağlı
dört gerçek Cargo manifestinin kaynak bildirimlerini inceler. Source declaration,
component attribution ve resolved/build dependency ayrı güven seviyeleridir.
Cargo, compiler, resolver, native scanner/runtime veya canlı sistem çalıştırmaz.

[Sözleşme](../../docs/commercial/operations/phase27/DIRECT_DEPENDENCY_CONTRACT.tr.md),
[Rust metadata](../../docs/commercial/operations/phase27/RUST_MANIFEST_SEMANTICS.tr.md),
[sahiplik](../../docs/commercial/operations/phase27/COMPONENT_OWNERSHIP.tr.md),
[güven sınırı](../../docs/commercial/operations/phase27/TRUST_BOUNDARY.tr.md),
[gerçek teslim/NOT_RUN](../../docs/commercial/operations/phase27/DEMO_DELIVERY.tr.md).

İlk demo root/core/scanner/CLI manifestlerinden toplam101 Rust declaration
bildirimi bekler; sayı kaynak verisinden hesaplanır. Workspace havuzu32 tanımı
bütün crate'lere yayılmaz. Child `workspace=true` kullanımının açık kaynağı
bağlanır. Optional, feature/default-feature, dev/build ve target ifadeleri
metadata olarak korunur; activation/target/feature resolution yapılmaz.
Version requirement bir çözülmüş sürüm değildir. Git/path/target giriş dosyaları
ve URL'ler takip edilmez. Kaynakta gözlenmeyen renamed/build örneği üretilmez.

Scanner ve CLI manifestleri iki native component'in kaynak listesinde de var;
primary manifest alanı bu belirsizliği tek başına çözmez. Core manifesti yalnız
assessment kaynak kapsamındadır ancak primary manifest değildir. Bunlar kesin
component ownership'e yükseltilmez. Python helper'ların ortak pyproject kaydı,
44 backend-context dependency'nin helper runtime sahipliğini kanıtlamaz.

Phase24'ün451 özgün D kaydı global grafikte korunur.111 declaration ve340 lock
kaydı unique package listesi değildir. Üç çiftte6 D kaydı eski non-ID metadata'da
aynı görünür: D0039/D0041, D0044/D0076, D0070/D0077. Hepsi olası bağ olarak
görünür; ordinal sıra veya isimle seçim yapılmaz. Tekil eski metadata projeksiyonu
eşleşmesi yalnız o alanlar için bağdır; eski kayıtta bulunmayan kind/feature/
target bilgisi uydurulmaz. Lock version veya checksum runtime proof değildir.

Phase26 Variant A/B seçimi ayrı bir overlay'de gösterilir. Eski exposure enum'ları,
451 kayıt,461 lisans subject'i,459 unknown lisans, tek L0001 evidence ve tüm açık
insan inceleme/release engelleri değişmez. Yeni edge lisans kanıtı veya dağıtım
yetkisi vermez. Bildirim bulunmaması sıfır runtime dependency anlamına gelmez.

Scope JSON yalnız demo modundadır. On eski artifact yolu açık CLI argümanlarıdır.
İki Markdown summary mevcut dört payload manifestlerini byte düzeyinde bağlamak
için seçilir. Dört Cargo manifesti scope'ta açık root-relative yol, eski F ref,
boyut/SHA256 ve deklaratif pin ile seçilir; `--termivar-root` yerel kökü açıkça
verir. Yalnız eski katalogla birebir eşleşen seçimler okunur. Kaynak commit pin'i
producer/git/build attestation değildir. Product Phase25 dosyalarını veya eski
LICENSE/Cargo.lock gövdesini yeniden açmaz; korunan Phase26 modelini doğrular.

Workspace kökünden iki komut aşağıdadır. Teslimde bütçe2/2 tüketilmişse yeniden
çalıştırma. Inspector yalnız başarılı assembly sonrasında izinlidir.

```powershell
python -I -B security-platform/tools/commercial_dependency_evidence/assemble_evidence_graph.py `
  --scope security-platform/tools/commercial_dependency_evidence/examples/demo_dependency_scope.json `
  --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar `
  --composition-inventory outputs/phase24-composition/composition-inventory.json `
  --composition-dependencies outputs/phase24-composition/dependency-license-ledger.json `
  --composition-constraints outputs/phase24-composition/release-constraints.json `
  --composition-summary outputs/phase24-composition/composition-summary.md `
  --composition-manifest outputs/phase24-composition/manifest.json `
  --variant-analysis outputs/phase26-pilot-variants/variant-analysis.json `
  --variant-dependencies outputs/phase26-pilot-variants/dependency-exposure.json `
  --variant-licenses outputs/phase26-pilot-variants/license-readiness.json `
  --variant-summary outputs/phase26-pilot-variants/variant-comparison.md `
  --variant-manifest outputs/phase26-pilot-variants/manifest.json `
  --output-dir outputs/phase27-dependency-evidence

python -I -B security-platform/tools/commercial_dependency_evidence/inspect_evidence_graph.py `
  --evidence outputs/phase27-dependency-evidence/direct-dependency-evidence.json `
  --graph outputs/phase27-dependency-evidence/source-evidence-graph.json `
  --variants outputs/phase27-dependency-evidence/variant-dependency-evidence.json `
  --summary outputs/phase27-dependency-evidence/dependency-evidence-summary.md `
  --manifest outputs/phase27-dependency-evidence/manifest.json `
  --output outputs/phase27-dependency-evidence/inspection-summary.json
```

İlk komut üç JSON, Markdown ve manifest üretir. Inspector beş yeni açık dosyada
kapalı sözleşme, projection/ref/sayım, sahiplik/binding/inheritance, graph/overlay,
Markdown ve manifest iç tutarlılığını inceler. Orijinal kaynak/TOML/üreticiyi
bağımsız yeniden doğrulamaz. `content_consistent` test, build veya hukukî kabul
değildir. Hatalar sabit mesaj ve nonzero exit verir; eski çıktı yeni başarı gibi
gösterilmez. Çıktı dizini yeni olmalı; kısmi yeni dosyalar başarılı teslim sayılmaz.

Scope128KiB, JSON başına2MiB; scope/JSON/MD toplam12MiB. Eski summary512KiB,
manifest64KiB. Cargo başına256KiB/en fazla16/toplam4MiB ayrı bütçe.64component,
1024D kaydı,512declaration,4variant,4096node,8192edge. Yeni JSON4MiB/MD512KiB;
strict JSON depth16/node120000/text2MiB/string2048 korunur; sessiz kesme yoktur.
UTF-8/BOM/duplicate/float/nonfinite/unknown-field/version ve bozuk ref reddi;
symlink/reparse/traversal/hardlink/kimlik/değişim kontrolleri vardır. Windows
lstat/fstat ctime aileleri karıştırılmaz. Kodda guard bulunması hostile input
veya filesystem race kabulü yapıldığı anlamına gelmez.

Ham source, manifest/lock/LICENSE gövdeleri, credential veya mutlak kullanıcı
kökleri çıktıya taşınmaz. Sınırlı metadata bile hassas olabilir; allowlist secret
detection, redaksiyon veya anonimlik garantisi değildir. Production wheel,
startup, backend/console/auth/DB/roller, native kaynaklar ve Phase7–26 değişmez.
Test/build/install/native-runtime/network/admin/customer/legal-final/push/release/
deploy yolu yoktur. Phase27 iki komut ve ölçülmüş teslim sonrasında kapanır.
