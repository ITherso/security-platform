# Çevrimdışı vaka paketi sözleşmesi

**DEMONSTRATION ONLY — NO REAL SYSTEM ASSESSED OR CLIENT DELIVERY AUTHORIZED**

[Araç](../../../../tools/commercial_case/README.md),
[ilişki modeli](RELATIONSHIP_MODEL.tr.md), [iş durumları](WORKFLOW_STATES.tr.md),
[güven/veri sınırı](TRUST_AND_PRIVACY.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).

Yeni harita `termivar-offline-case-map/v1`: yalnız `schema_version`, `mode`,
`case_reference`, `artifact_roles`, `source_constraints`,
`expected_relationships`. `mode=demo`; referans `DEMO-` ile başlayan sentetik
organizasyon etiketidir. Müşteri, yetki veya run kimliği değildir.

Rol registry'si 20 sabit kaynakla sınırlıdır: dört Phase20 dosyası, iki Phase14
dosyası, üç Phase17 intake, üç Phase18 review packet/template, Phase19 overlay,
iki Phase19 reconciliation, iki Phase21 traceability ve üç mevcut handoff
Markdown/manifest kaynağı. Harita beklenen sözleşmeyi, rolü, açık göreli yolu,
varlık durumunu, ilgili manifest rolünü ve beklenen ilişkiyi bildirir.
Bilinmeyen alan/rol/sürüm reddedilir. Eksik zorunlu kaynak başarılı pakete
dönüştürülmez. Örnek harita gerçek mevcut yolları açıkça seçer.
Harita en fazla 64 KiB'dır. İlk sürüm mevcut boş-overlay demo alt kümesini
kabul eder; dolu karar veya gerçek müşteri modu eklenmez.

`termivar-offline-case-bundle/v1` kapalı vaka defteridir. Kaynak kimlikleri,
ayrı observation metadata'sı, kaynak ilişkileri, sınırlı workflow facts,
altı aşama ve blocker listesi frozen DTO'lardan oluşturulur. Ham kaynak JSON
veya metni serialize edilmez. Path, origin, target veya serbest reviewer notu
için output alanı bulunmaz. Pointer bir JSON konumudur; dosya yolu değildir.

İç vaka ZIP'i yalnız şu üyeleri taşır:

| Üye | Sınırlı içerik |
| --- | --- |
| `case-ledger.json` | Sürümlü vaka durumu ve açık engeller |
| `case-summary.md` | Yeni üretilmiş, sınırlı insan özeti |
| `source-index.json` | Kaynak rolü, sözleşme, byte/SHA ve ilişkiler; yerel path yok |
| `bundle-manifest.json` | Diğer dört üyenin gerçek boyut/hash'leri; kendisi hariç |
| `README.txt` | Demo, kaynak eksikliği ve doğrulama sınırı |

Bu bir tam delil arşivi değildir. Kaynak dosyalar pakette yokken dış ilişkiler
yeniden kurulmuş sayılamaz. Case map'in ham içeriği de vaka ZIP'ine kopyalanmaz.
Case-map dosyası organizasyon talimatıdır; kaynak artefact'ıyla aynı şey değildir.

Assembly çıktısı yeni klasörde vaka ZIP'i, dış `case-manifest.json` ve
`assembly-summary.md` olur. Dış manifest gerçek ZIP boyut/SHA'sını taşır;
kendi hash'ini içermez. Bağımsız inspector ayrı açık JSON çıktı dosyası yazar.
İç manifest ile dış ZIP kimliği arasında döngüsel self-hash kurulmaz.

Inspector beş üye, closed schema, manifest bağları, source-index/ledger ilişkisi,
Markdown ve README'nin tanımlı projeksiyonla tutarlılığını inceler. ZIP'i diske
çıkarmaz veya üyeyi kod/HTML olarak çalıştırmaz. Üretici kimliği, müşteri onayı
ve gerçek güvenlik sonucu bu incelemenin dışında kalır.

Kaynak başına limitler mevcut sözleşmelere göre seçilidir; toplam giriş okuma
bütçesi 16 MiB'ı aşmaz. Strict UTF-8, duplicate key/NaN/Infinity/yanlış tür,
derinlik/düğüm/metin sınırları ve güvenli göreli path kontrolleri vardır.
ZIP ham 2 MiB, açılmış toplam 1 MiB, beş üye ve 100 kat oran tavanıyla sınırlıdır;
JSON/Markdown/README/manifest için ayrıca düşük üye limitleri kullanılır.
Bu guard'ların hostile-input güvenlik kabulü **NOT_RUN**'dır.
