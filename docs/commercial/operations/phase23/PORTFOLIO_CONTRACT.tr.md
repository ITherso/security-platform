# Offline portföy sözleşmesi

**DEMONSTRATION ONLY — OFFLINE CASE PORTFOLIO — NO CLIENT OR EXECUTION VERIFIED**

[Araç ve CLI](../../../../tools/commercial_portfolio/README.md),
[triage](TRIAGE_MODEL.tr.md), [güven/veri](TRUST_AND_PRIVACY.tr.md),
[gerçek teslim](DEMO_DELIVERY.tr.md).

Girdi `termivar-offline-portfolio-map/v1`: exact `schema_version`, `mode`,
`portfolio_reference`, `case_bundles`, `display_preferences` alanları.
`mode=demo`; referans ve isteğe bağlı display label sentetik etiketlerdir.
Müşteri, assessment run veya çalışma yetkisi kimliği oluşturmaz.

Her seçimin açık göreli ZIP yolu, beklenen `termivar-offline-case-bundle/v1`,
nullable sentetik `display_label` ve nullable `expected_sha256` alanı vardır.
Beklenen hash verilirse gerçek raw ZIP hash'iyle eşleşmelidir; üretici veya
signature kanıtı sayılmaz. Display tercihleri hash görünürlüğü ve sınırlı case
ayrıntısının açık/kapalı sunumunu belirler; güven statüsünü değiştirmez.

Çıktı `termivar-offline-portfolio/v1` kapalı immutable modeldir. Her kaynak için
yalnız raw ZIP kimliği/boyutu, mevcut case reference/contract, iç tutarlılık,
altı aşama, mevcut blocker'lar, sınırlı workflow facts ve demo/güven sınırları
taşınır. Path, raw ZIP üyeleri, kaynak indeksinin tamamı, observation fingerprint
ve ham notlar portföy modeline taşınmaz. Kaynak nesnesi doğrudan serialize edilmez.

Duplicate raw ZIP SHA reddedilir. Aynı case reference farklı ZIP SHA ile gelirse
conflict oluşur ve üretim durur. Vaka referansı küresel tekil case/run kimliği
olarak kullanılmaz. Farklı dosya adı, mtime veya dizin üzerinden yeni vaka,
güncellik veya müşteri sonucu çıkarılmaz. Kaynak hatasında geri kalanlar sessizce
tamamlanmış portföy sayılmaz. Bu ilk sürüm fail-closed'dur.

Portföy toplamları seçili geçerli paketleri sayar; müşteri, gerçek değerlendirme,
zafiyet veya güvenlik başarısı sayısı değildir. Blocker üyelikleri ve aşama
sayımları gerçek case metadata'sından yeniden türetilir. Kaynaklar farklı
müşteri veya farklı run olarak kabul edilmez.

JSON indeks, Markdown özet, statik HTML ve manifest oluşturulur. Manifest üç
payload'ın gerçek boyut/SHA değerlerini taşır; kendisini hash listesine eklemez.
Inspector şema/özet sayaçları ve dört açık dosyanın byte ilişkisini inceler.
Markdown/HTML için `--summary` ve `--overview` açıkça eklenmiştir; JSON içindeki
entry/path üzerinden yeni dosya açılmaz. Inspector orijinal map/case ZIP'lerini
yeniden okumaz.

Limitler: map 64 KiB, 1–25 seçim, toplam sıkıştırılmış ZIP girişi 16 MiB;
Phase22 raw ZIP 2 MiB/expanded 1 MiB/ratio100 ve beş üye guard'ları korunur.
Portföy JSON ve HTML 512 KiB, Markdown 128 KiB, manifest 64 KiB ile sınırlıdır.
Strict UTF-8, duplicate/sayı/schema/unknown-field ve aggregate
depth12/node10000/text128KiB sınırları uygulanır. Bunların negatif/hostile
güvenlik kabulü yapılmadıysa **NOT_RUN** kalır.
