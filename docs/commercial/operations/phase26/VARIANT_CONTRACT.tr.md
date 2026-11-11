# Pilot kapsamı sözleşmesi

**DEMONSTRATION ONLY — PILOT VARIANT ANALYSIS — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Araç/CLI](../../../../tools/commercial_pilot_variants/README.md),
[dependency exposure](DEPENDENCY_EXPOSURE.tr.md),
[lisans/readiness](LICENSE_AND_READINESS.tr.md), [güven sınırı](TRUST_BOUNDARY.tr.md),
[gerçek teslim](DEMO_DELIVERY.tr.md).

`termivar-offline-pilot-variant-scope/v1` kapalı sekiz alan taşır:
`schema_version`, `mode`, `candidate_reference`, `composition_sources`,
`evidence_sources`, `variants`, `comparison_pairs`, `inspection_constraints`.
Mode yalnız demo; varyant kimlikleri yerel karşılaştırma etiketleridir.
SKU, müşteri paketi, gerçek release veya pilot GO kimliği değildir.

Phase24 ve Phase25 için beşer girdi rolü seçilir. Her source metadata kaydı
gerçek şema (Markdown için null), boyut ve SHA256 taşır. Dosya yolları yalnız
açık CLI argümanlarıdır. İki eski summary'nin ayrıca seçilmesi mevcut dört
payload'lı manifestleri gerçek byte'larıyla bağlamak içindir; JSON path/URL
değerlerinden yeni dosya keşfi yapılmaz.

Phase25'in bildirdiği beş Phase24 içerik kimliği ve deklaratif kaynak pinleri,
yüklenen Phase24 ile eşleşmelidir. Kaynak uyuşmazlığında benzer/eski dosya
seçilmez. Phase25'in subject, pointer, row digest ve yerel source key ilişkisi
gerçek eski modellerin saf projeksiyonuyla karşılaştırılır. Eski dosyalar
yeniden üretilmez veya güncellenmez.

Her variant; id, etiket, açıklama ve gerçek component id'lerinin seçilmiş/
seçilmemiş tam ayrımını taşır. Duplicate, bilinmeyen veya iki tarafta bulunan
component reddedilir. İlk demo A'da iki native kaynak bileşeni, B'de aynı iki
native ve sekiz bağımsız offline destek aracı seçer. Seçilmeyen kaynak bileşeni
gerçek binary'den çıkarılmış sayılmaz. Karşılaştırma çifti farklı iki id seçer;
ters sırayla tekrarlanan aynı çift de reddedilir.

Üç JSON sonucu:

- `termivar-offline-pilot-variant-analysis/v1`: sınırlı component/manifest
  katalogları, varyantlar ve yeniden türetilebilir karşılaştırmalar.
- `termivar-offline-dependency-exposure/v1`: her özgün Phase24 dependency
  kaydına tek satır, varyant exposure üyelikleri ve ayrı sayımlar.
- `termivar-offline-pilot-license-readiness/v1`: her Phase25 lisans kaydına tek
  satır, kanıt/binding ilişkileri, varyant ilişkileri ve açık blocker özetleri.

451 dependency ve 461 lisans kaydı farklı kayıtlardır. İsim eşitliğiyle
birleştirme veya 451'i 461'e birebir çevirmek yoktur. Kataloglar ham kaynak
gövdesi yerine doğrulanmış alan projeksiyonlarıdır.

Scope 128 KiB; eski JSON başına 1 MiB, summary başına 512 KiB, manifest başına
64 KiB; scope dahil açık okuma toplamı 6 MiB. En fazla dört variant, altı farklı
çift, 64 component referansı, 2000 dependency/lisans referansı. Yeni JSON 4 MiB,
Markdown 512 KiB; korunmuş JSON derinlik16/node120000/metin2 MiB/dize2048
sınırları ayrıca uygulanır. Limit aşımında sessiz kesme yoktur.

`demo_only=true`; dependency closure, lisans incelemesi, redistribution, build,
runtime, producer, release ve production bayrakları false kalır. Ek
`human_review_verified=false` insan incelemesi yapılmadığını korur.
Manifest ilk dört yeni payload'ın gerçek byte/hash'ini bağlar ve kendisini
hariç tutar. Inspector yalnız beş açık yeni dosyanın iç tutarlılığını inceler;
kaynaklara, git'e, lisans belgesine veya package cache'ine dönmez.
