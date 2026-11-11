# Offline Product Composition & License Readiness — Phase24

**DEMONSTRATION ONLY — PRODUCT COMPOSITION REVIEW — NOT AUTHORIZED FOR DISTRIBUTION**

Bağımsız standart kütüphane aracı, açık seçilmiş mevcut kaynak dosyalarının
metadata envanterini üretir. Termivar değerlendirme çekirdeği ve raporlama
kaynakları ile sekiz offline destek aracını ayrı rollerde gösterir. Dağıtılabilir
ürün, binary, wheel, installer veya SBOM standardı sertifikası üretmez.

[Sözleşme](../../docs/commercial/operations/phase24/COMPOSITION_CONTRACT.tr.md),
[dependency/lisans](../../docs/commercial/operations/phase24/DEPENDENCY_AND_LICENSE.tr.md),
[dağıtım sınırı](../../docs/commercial/operations/phase24/RELEASE_BOUNDARIES.tr.md),
[gerçek teslim](../../docs/commercial/operations/phase24/DEMO_DELIVERY.tr.md).

Workspace kökünden, açık yerel repository kökleriyle:

```text
python -I -B security-platform/tools/commercial_composition/assemble_composition.py --scope security-platform/tools/commercial_composition/examples/demo_composition_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --platform-root security-platform --output-dir outputs/phase24-composition
python -I -B security-platform/tools/commercial_composition/inspect_composition.py --inventory outputs/phase24-composition/composition-inventory.json --dependencies outputs/phase24-composition/dependency-license-ledger.json --constraints outputs/phase24-composition/release-constraints.json --summary outputs/phase24-composition/composition-summary.md --manifest outputs/phase24-composition/manifest.json --output outputs/phase24-composition/inspection-summary.json
```

İkinci komut yalnız ilk komut başarılıysa çalıştırılır. Phase24 sınırı iki yeni
ürün çağrısıdır; gerçek çağrı kayıtları teslim belgesindedir. Eski CLI'lar, native
Termivar, package manager, resolver, test, typecheck/build veya ağ çalıştırılmaz.

Scope yalnız açık dosya listeleri taşır. Kaynak kod import edilmez; hash için
byte okunur. `Cargo.toml`/`Cargo.lock`/`pyproject.toml` stdlib `tomllib`, açık
requirements pin dosyaları sınırlı destekle okunur. Manifest içindeki path/URL,
Cargo feature, build script veya dependency kaynağı takip edilmez. Kökler yalnız
CLI'dan seçilir; çıktıya mutlak kök yolları yazılmaz. Pin commit'ler gözden
geçirilmiş scope beyanıdır; araç git veya build attestation üretmez.

Kaynak dosya başına 4 MiB, toplam 32 MiB, en fazla 5000 metadata kaydı ve
64 bileşen. Scope 512 KiB; JSON 4 MiB, Markdown 512 KiB; derinlik16,
120000 node, toplam 2 MiB JSON metni ve dize başına2048 karakter.
UTF-8/BOM/duplicate/float/nonfinite/unknown schema/alan, link/reparse/traversal,
hardlink ve okuma öncesi/açık/sonrası kimlik değişimi reddedilir. Bunların
saldırgan girdi veya yarış kabulü bu turda yapılmaz.

Yeni output dizini ve dosya zorunludur; overwrite yoktur. Dört payload staging
üzerinden yayımlanır, manifest son yazılır. Hata yeni kısmi çıktı bırakabilir;
crash veya tam atomiklik kabulü verilmez. Inspector beş açık dosyayı okur;
`--summary` gerçek Markdown byte/hash ilişkisini denetlemek için ek açık
argümandır. Manifestten dosya keşfi yapmaz, orijinal kaynaklara dönmez.

Cargo workspace lock kayıtları seçilen feature/binary kapanışı değildir.
Path veya lock source yokluğu workspace sahipliği kanıtlamaz; source type
unknown kalır. Manifest deklarasyonları, lock kayıtları ve backend context bağımlılıkları ayrı
kalır. Cargo.lock lisans kanıtı değildir. Bilinmeyen lisanslar doldurulmaz;
yerel MIT beyanı üçüncü taraflara veya platform yardımcılarına yayılmaz.
İnsan incelemesi ve redistribution/release yetkisi açık kalır.

Arşiv yalnız yeni araç, belgeler ve sentetik metadata çıktılarıdır. Korunmuş
`commercial_handoff` ve inspection publisher için `commercial_case` helper
kaynakları gerekir; eski kaynaklar veya binary'ler yeni ZIP'e kopyalanmaz.
Üretim wheel/startup/backend/frontend entegrasyonu yoktur.
