# Doğrudan dependency kaynak kanıtı sözleşmesi

**DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Araç/CLI](../../../../tools/commercial_dependency_evidence/README.md),
[Rust semantiği](RUST_MANIFEST_SEMANTICS.tr.md), [ownership](COMPONENT_OWNERSHIP.tr.md),
[güven sınırı](TRUST_BOUNDARY.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).

`termivar-offline-direct-dependency-scope/v1` kapalı sekiz alan taşır:
`schema_version`, `mode`, `source_reference`, `composition_sources`,
`variant_sources`, `manifest_sources`, `component_ownership_sources`,
`inspection_constraints`. Mode yalnız demo; build/resolve/activate/approve yolu
yoktur. Ownership kaynak seçicisi gerçek eski component row digest'ini belirtir;
kullanıcının sahiplik beyanı veya override yetkisi değildir.

Phase24 ve Phase26 için beşer açık CLI girdi rolü seçilir. Eski summary'ler,
dört payload'lı manifestlerin byte bağını tamamlamak içindir. Descriptor; gerçek
şema (Markdown'da null), boyut ve SHA256 taşır. Phase26'nın Phase24 kimlikleri,
source pinleri, katalogları ve D/L row/pointer/digest bağları eski modellerle
uyuşmalıdır. Benzer dosya seçme, isim eşleştirmesi veya sessiz fallback yoktur.
Ürün orijinal Phase25 girdilerini yeniden açmaz; lisans sınırı Phase26'nın
korunmuş projeksiyonundan gelir.

Source reference; yerel Phase27 candidate, eski composition candidate ve iki
deklaratif kaynak pinine, çıktı aşamasında iki eski beşli source descriptor
grubunu ekler. Pin, üretici/git/build attestation değildir. Açık dört Cargo
seçimi eski manifest id, F ref, root/path, boyut/hash ve pin kimliğiyle bağlanır.
Scope'taki manifest yolu yalnız belirtilen root altında okunur; dependency
path/git/URL veya bin/lib entry yolu takip edilmez.

Üç çıktı modeli:

- `termivar-offline-direct-dependency-evidence/v1`: sınırlı eski component/
  manifest katalogları, tüm eski D kayıtları, iki eski variant seçimi, lisans
  sınırı ve normalized manifest/declaration/ownership/binding metadata'sı.
- `termivar-offline-direct-dependency-graph/v1`: beş node/edge türü, içerik
  fingerprint'i, açık definite/possible ayrımı ve yeniden türetilebilir sayımlar.
- `termivar-offline-variant-dependency-evidence/v1`: tüm D ref'ler üzerinde ayrı
  source-evidence overlay; eski Phase26 enum veya dosyalarının yerine geçmez.

101 Rust declaration sayısı fixture değildir; gerçek seçilmiş TOML alanlarından
türetilir. Eski 451 D satırı bir kez korunur: 111 declaration, 340 lock;
407 selected-source, 44 excluded backend-context. D ref sayısı unique package
sayısı değildir. Aynı ada sahip farklı satırlar birleştirilmez.

Scope 128 KiB; eski JSON başına 2 MiB, summary 512 KiB, manifest 64 KiB;
scope ve açık artefact okumaları toplam 12 MiB. Cargo başına 256 KiB, en fazla
16 açık Cargo; 64 component, 1024 eski D, 512 source declaration, dört variant,
4096 node ve 8192 edge. Yeni JSON 4 MiB, Markdown 512 KiB; ayrıca korunmuş
JSON depth16/node120000/text2 MiB/string2048 sınırları uygulanır. Limit aşımında
ilk N kayda başarı yoktur. UTF-8/BOM/duplicate/float/nonfinite, yanlış tür,
bilinmeyen alan/sürüm ve geçersiz referans kapalı hatadır.

Manifest dört payload'ın gerçek byte/hash'ini bağlar, kendisini hariç tutar.
Inspector yalnız beş yeni açık dosyada kapalı model, normalized semantik,
referans/count, graph/overlay/Markdown ve byte bağını inceler. Orijinal Cargo,
eski Phase24/26, git veya üretici bağımsız yeniden doğrulanmaz. Tüm sonuçlar
demo'dur; çözümleme, closure/runtime, lisans/redistribution, release/production,
producer/human/build doğrulama bayrakları false kalır.
