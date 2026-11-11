# İzlenebilirlik sözleşmesi

**DEMONSTRATION ONLY — PLAN AND ASSESSMENT EXECUTION LINK NOT ESTABLISHED**

`termivar-assessment-traceability/v1` kapalı çıktı modeli üç bilgi katmanını
ayırır: **plan intent**, **assessment reported**, **execution linkage**.
[Araç](../../../../tools/commercial_traceability/README.md),
[eşleme](CAPABILITY_MAPPING.tr.md), [güven sınırı](TRUST_BOUNDARY.tr.md),
[gerçek demo](DEMO_DELIVERY.tr.md).

Plan katmanı gerçek Phase20 plan kimliğini, profilini, seçili capability'leri,
sentetik `.invalid` kapsamını, yedi bütçe limitini ve mevcut precondition
engellerini taşır. Plan ID, raw dosya SHA256'sından ayrıdır: `plan_id`
çıkarılmış gövdenin sıralı JSON + son LF temsilinin digest'idir. Planın
gömülü proposal SHA'sı yalnız beyan edilen kimliktir; proposal dosyası açılmaz.

Assessment katmanı mevcut base `venom-rendered-assessment/v1` içindeki
profil/status/count ve dört desteklenen informational passive observation'ın
kapalı metadata'sını taşır. `venom-run/v1` bir şema etiketidir; run ID değildir.
Başlık, ham HTTP, remediation, credential veya serbest kaynak metni taşınmaz.
`subject-0000` gibi opaque referanslar gerçek target/origin yerine kullanılamaz.

Execution linkage sabit `not_established` kalır. Aynı capability, profil,
fingerprint, kaynak sürümü veya dosya seçimi bunu değiştirmez. Dosya düzeyindeki
assessment → Phase17 bağlantısı ayrı raporlanır; plan → assessment bağı değildir.

Capability eşleme kategorileri:

| Kategori | Sınırlı anlam |
| --- | --- |
| `declared_in_both` | Aynı desteklenen assessment-item kimliği iki tarafta tanımlı |
| `plan_only` | Planda mevcut, assessment'ta aynı kimlikle raporlanmış değil |
| `assessment_only` | Assessment'ta raporlanmış, planda seçili değil |
| `unmappable` | Namespace/yapı farklılığı güvenilir eşlemeye izin vermiyor |
| `insufficient_evidence` | Kimlik eşlemesi için kaynak bilgisi yetersiz |

Bu kategoriler başarılı/başarısız çalışma veya tamamlanmış kontrol anlamına
gelmez. Birden fazla observation aynı capability/fingerprint'i bildirirse
ayrı pointer'larıyla korunur; fingerprint üzerinden tek kayda indirilmez.

Profil iki tarafta da bildirildiğinde yalnız beyan karşılaştırılabilir.
Assessment origin, root URL, yöntem, yedi bütçe ve gerçekleşmiş tüketimi
bildirmediği için bu alanlar `not_reported` kalır. Semantik karşılığı bulunmayan
plan/assessment durumları `not_comparable` olarak açıklanır. Assessment'ın
`complete` beyanı planın tamamlandığını doğrulamaz. Coverage/tüketim yüzdesi,
güvenlik puanı veya risk tahmini yoktur.

Dokuz açık girdi rolü gerçek SHA256/byte kimliğiyle bağlanır. Kapalı immutable
DTO'lar kullanılır; ham artefact bütünü ledger'a veya global store'a taşınmaz.
Desteklenen mevcut Phase20 sözleşmesi ve sabit katalog alt kümesiyle uyumsuz
alan/sürüm/namespace kapalı hata veya açık eşlenemezlik üretir. Kaynak uyuşmazlığı
başarılı ilişkilendirmeye dönüştürülmez.

Byte sınırları: plan 512 KiB, assessment 1 MiB, mapping/handoff/preflight/catalog
256 KiB, manifest başına 64 KiB. Mapping için korunmuş Phase18 okuyucusunun
256 KiB alt kümesi kullanılır; önerilen 512 KiB üst sınırına genişletilmez.
Planın ham okuma tavanı 512 KiB olsa da gerçek Phase20 manifest sözleşmesinin
payload başına 256 KiB sınırı ayrıca korunur; daha büyük bir dosya bu yolla
geçerli Phase20 payload'ı ilan edilemez.
Strict UTF-8, duplicate key/float/NaN/Infinity reddi ve aggregate
depth12/node10000/text128KiB sınırları uygulanır. Bunlar çalıştırılmış
hostile-input kabulü değildir.

Çıktı JSON ledger, Markdown özet ve kendi hash'ini içermeyen son manifesttir.
Manifest girdi kimliklerini ve iki payload'ın gerçek boyut/hash'lerini içerir.
Her çıktıda demo etiketi ve doğrulama engelleri görünür kalır. Şema dosya
kimliğini üretici/uzman/yetki doğrulaması yerine kullanmaz.
