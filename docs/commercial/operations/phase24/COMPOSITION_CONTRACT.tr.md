# Ürün bileşimi sözleşmesi

**DEMONSTRATION ONLY — PRODUCT COMPOSITION REVIEW — NOT AUTHORIZED FOR DISTRIBUTION**

[Araç/CLI](../../../../tools/commercial_composition/README.md),
[dependency/lisans](DEPENDENCY_AND_LICENSE.tr.md), [dağıtım](RELEASE_BOUNDARIES.tr.md),
[gerçek teslim](DEMO_DELIVERY.tr.md).

Girdi `termivar-offline-composition-scope/v1`, exact dokuz alan:
`schema_version`, `mode`, `candidate_reference`, `source_roots`,
`included_components`, `excluded_components`, `dependency_manifests`,
`license_evidence_sources`, `inspection_constraints`. Mode yalnız demo;
referans sentetik aday etiketidir, müşteri/run/yayın/onay kimliği değildir.

İki kök `termivar` ve `platform`; repository label ve pinlenmiş commit scope'ta,
yerel kök yolları açık CLI argümanlarında bulunur. Araç git çalıştırmaz: commit
pin'i gözden geçirilmiş scope beyanıdır, çalışma ağacı/build attestation değildir.
Kaynak kimliği seçilen gerçek dosyaların byte/hash kaydıdır. Her bileşenin rolü,
manifesti, kaynak referansları ve sürüm beyanı ayrı tutulur. Python project
0.1.0 beyanı offline yardımcıların release sürümü olarak sunulmaz.

Sonuç `termivar-offline-composition/v1`: açık kaynak bileşimi, gerçek dosya
metadata'sı, hariçler, manifest referansları ve `actual_distributable_artifacts=[]`.
Bu boş liste bu fazın kabul edilmiş ürün paketi üretmediğini gösterir;
makinede hiçbir binary bulunmadığını iddia etmez.

`termivar-offline-dependency-license-ledger/v1` manifest deklarasyonlarını,
lock kayıtlarını ve subject bazlı LicenseEvidence metadata'sını taşır.
`termivar-offline-release-constraints/v1` yalnız açık karar/kanıt engellerini
üretir. Alanlar, türler, sürümler, referanslar, sayaçlar ve sabit bayraklar
kapalı doğrulanır. Manifest `termivar-offline-composition-manifest/v1` dört
payload'ın gerçek byte/hash değerlerini bağlar; kendi hash'ini içermez.

Inspector yalnız inventory/dependencies/constraints/summary/manifest olmak
üzere beş açık dosya okur. `--summary` gerçek Markdown ilişkisi için eklenmiştir.
Sözleşmeler, sayımlar, referanslar, yeniden türetilen saf blocker/Markdown ve
manifest ilişkileri incelenir. `termivar-offline-composition-inspection/v1`
sonucu kaynakları, lisansları, git kimliğini veya dependency kapanışını yeniden
doğruladığını iddia etmez.

Scope512 KiB; dosya4 MiB/toplam32 MiB; 64 bileşen/5000 dosya;
JSON4 MiB/Markdown512 KiB; derinlik16/node120000/metin2 MiB/dize2048 sınırları.
Strict UTF-8, duplicate/float/nonfinite/BOM ve bilinmeyen alan/sürüm reddi.
Yalnız açık dosyalar okunur; recursive discovery veya metadata URL/path takibi
yoktur. Kaynak metni çıktıya taşınmaz. Bounded metadata bile hassas olabilir;
bu bir secret detection, redaksiyon veya anonimlik garantisi değildir.

Her yol bileşeni link/reparse için incelenir; traversal ve hardlink reddedilir.
Okuma öncesi/açık/sonrası identity/size/time karşılaştırılır; yayım öncesi
stability stat kontrolü vardır. Kontroller race/ACL/saldırgan filesystem
kabulü değildir. Yeni output zorunludur; hata kısmi yeni çıktı bırakabilir.

`demo_only=true`, gerçek envanter üretildiğinde `source_inventory_generated=true`;
`license_review_completed`, `redistribution_authorized`, `build_verified`,
`runtime_verified`, `release_authorized`, `production_ready` daima false.
Kaynak varlığı ve hash tutarlılığı bu altı bayrağı yükseltmez.
