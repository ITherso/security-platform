# Lisans kanıtı sözleşmesi

**DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED**

[Araç/CLI](../../../../tools/commercial_license_review/README.md),
[kayıt bağı](COMPONENT_BINDING.tr.md), [inceleme akışı](LICENSE_REVIEW_WORKFLOW.tr.md),
[güven/veri](TRUST_AND_PRIVACY.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).

Girdi `termivar-license-evidence-scope/v1` yalnız demo modundadır. Kapalı yedi
alan: `schema_version`, `mode`, `composition_reference`, `composition_inputs`,
`evidence_sources`, `binding_requests`, `review_constraints`. Gizli approval,
release veya lisans değiştirme modu yoktur.

Composition reference, Phase24 aday referansını ve gerçek inventory,
dependency ledger, constraints, summary, manifest dosyalarının ayrı boyut/SHA256
kimliklerini taşır. Beş dosya açık yolla seçilir. Summary'nin ayrıca seçilmesi,
Phase24 manifestinin dört payload'ını gerçek byte'larıyla bağlamak içindir;
manifestten dosya keşfi yapılmaz. Phase24 dosyaları salt okunur kalır.
`source_commits`, eski inventory'deki Termivar ve platform pin beyanlarını ayrı
korur. Araç git çalıştırmaz; bu beyanlar kaynak/üretici, çalışma ağacı veya build
attestation değildir. Binding key formülü bu pinleri global kimliğe dönüştürmez.

Sonuçlar `termivar-license-evidence-ledger/v1`,
`termivar-license-review-queue/v1`, `termivar-license-binding-conflicts/v1`.
Ledger eski kayıtların sınırlı subject projeksiyonunu, gerçek evidence dosya
metadata'sını, açık binding isteklerinin sonuçlarını ve her subject'in durumunu
ayrı taşır. Eski lisans beyanı `base_declared_license` olarak korunur; gözlenen
yeni etiket veya bağlama durumu onun yerine geçirilmez.

Scope'taki dosya yolları bir okuma seçimi, evidence id ve request id ise yerel
referanstır. Çıktıya mutlak kök veya belge gövdesi taşınmaz. Beklenen hash, gerçek
dosya hash'i, içerik biçimi gözlemi, Phase24 dosya ref'i ve `source_verified=false`
ayrı alanlardır. Bağlama durumu kaynak düzeyindedir; hukukî karar değildir.

Bir Phase24 lisans kaydına bir subject, bir ledger durum kaydı ve bir queue
satırı karşılık gelir. Aynı adı taşıyan declaration/lock kayıtları birleştirilmez.
Mevcut başlangıç 461 kayıttır: iki scoped MIT etiketi, 459 bilinmeyen lisans.
Yeni kanıt seçilmemiş kayıt sayısı bu 459 sayısıyla aynı kavram değildir.

Scope 128 KiB; eski üç JSON'un her biri 1 MiB, eski summary 512 KiB, eski
manifest 64 KiB; tek evidence 256 KiB/toplam 2 MiB; en fazla 64 evidence,
256 binding isteği, 1024 kaynak lisans kaydı. Yeni JSON 4 MiB, Markdown 512 KiB;
JSON derinlik16/node120000/metin2 MiB/dize2048 sınırları korunur. Sınır aşımında
ilk N kayıtla başarı üretilmez. UTF-8/BOM/duplicate/float/nonfinite, bilinmeyen
alan/sürüm ve yanlış türler kapalı hatadır.

Manifest `termivar-license-evidence-manifest/v1` dört yeni payload'ın gerçek
byte/hash kimliğini bağlar; kendisini hash listesine eklemez. Inspector
`termivar-license-evidence-inspection/v1` yalnız beş açık yeni çıktı dosyasının
kapalı sözleşme, referans, sayı, saf queue/conflict/Markdown ve manifest
ilişkilerini inceler. Eski Phase24 veya evidence dosyalarını yeniden doğrulamaz.

Her sonuçta `demo_only=true`; lisans incelemesi, redistribution, release,
production, build, runtime, producer ve human-review doğrulama bayrakları false
kalır. Inspector iç tutarlılığı bu bayrakları yükseltmez.
