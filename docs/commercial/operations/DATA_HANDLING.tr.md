# Veri işleme, minimizasyon ve paylaşım kararları

Bu rehber elle doldurulacak karar alanlarını tanımlar. **Gerçek veriyi silmez, şifrelemez, erişim yetkisi/ACL, güvenli kasa veya aktarım sistemi oluşturmaz.** Gerçek müşteri verisi toplanmadı/işlenmedi. Varsayılan saklama günü, hukukî dayanak, kurum politikası, seçilmiş aktarım kanalı veya koruma seviyesi atanmaz. Bu kararların mevcut durumu `pending_decision` olup gerçek pilotun açık kapısıdır. [PILOT_SCOPE §5](../PILOT_SCOPE.tr.md#5-veri-işleme-kararları), [PILOT_READINESS §2–3](../PILOT_READINESS.tr.md#2-işletim-kapıları).

## Sekiz veri sınıfı

Aşağıdaki kaynaklar **varsa** kaydedilir; rendered JSON'un bütün veri sınıflarını içerdiği iddia edilmez. Kaynak ref'i, içeriğin sağlandığı veya ona erişim izni bulunduğu anlamına gelmez. Her satır için ayrıca alttaki karar kaydı tutulur.

| ID / veri sınıfı | Neden gerekebilir / mevcutsa kaynak | Gereksiz paylaşım riski | Önerilen elle minimizasyon ve redaksiyon |
|---|---|---|---|
| D01 — Assessment metadata | Sözleşme, durum ve çalışma bağını anlamak; mevcut assessment/diagnostic ve ayrı vaka kaydı. | Müşteri, proje, zaman/ortam veya iç süreç bilgisi açığa çıkabilir. | Yalnız gerekli kimlik/sürüm/durum referansını aktar; kaynakta olmayan hedef/zaman/kullanımı uydurma. |
| D02 — Hedef/domain/IP bilgileri | Onaylı kapsamı ve gözlemin bağlamını belirtmek; ayrı yetki/kapsam kaydı, sağlanmış diagnostic/context. | Altyapı/tenant, iç adres, URL yolu/query veya üçüncü taraf ilişkisi açığa çıkabilir. | Gerekli kapsamı anlatmaya yetecek referansı seç; URL'deki sır ve gereksiz host/IP ayrıntısını çıkar. Kapsam/redaksiyon anlatımı çelişirse paylaşımı beklet. |
| D03 — HTTP request/response ve header | Uzman yorumunun dayanağını incelemek; yalnız ayrıca mevcut ve yetkili kanıt kaynağı. | Body/header içinde kişisel veri, sır veya iç sistem ayrıntısı olabilir. | Önce mevcut opaque referans ve sınırlı açıklamayı kullan; ham veri gereksinimini ayrıca gerekçelendir. Gereksiz body/header değerlerini müşteri dosyasına kopyalama. |
| D04 — Cookie, token, credential | Yalnız ayrıca kabul edilmiş desteklenen kimlikli yolun işletimi için gerekebilir; temel credentialsız pilotta varsayılmaz. | Hesaba erişim, oturumun kötüye kullanımı ve yetki sızıntısı. | Ham değeri vaka/ledger/rapor/manifest/URL içine koyma; sır yerine non-secret referans ve eksiklik notu kullan. Sır giriş/erişim/iptal yolu seçilmediyse bu veriyle faaliyet başlatma. |
| D05 — Kanıt ve örnek payload | Gözlem/yorum bağını açıklamak; mevcut evidence/control/candidate referansları veya ayrıca sağlanan örnek. | Hassas içerik, çalıştırılabilir/aktif metin veya hedefe özgü bilgi taşınabilir. | Önce referans ve gerekli redakte parça; içerik gerekiyorsa amaç ve izin kaydı. Payload'ı çalıştırma veya referansı otomatik açma izni oluşturma. |
| D06 — Uzman inceleme notları | Gerekçe, çelişki, eksik işlem ve karar geçmişi; ledger ve review decision dosyaları. | Kişi bilgisi, iç tartışma veya incelenmemiş varsayım müşteriye kesin sonuç gibi gidebilir. | İç kayıtta gerekli gerekçeyi tut; müşteriye yalnız ayrıca seçilmiş anlatım/sınırları çıkar. İnceleyenin kimliği/tarihi yoksa üretme. |
| D07 — Müşteriye sunulan özet | Kapsam/yöntem, seçilmiş yorum ve belirsizliği anlatmak; onaylanacak handoff taslağı. | İç not/sır taşınması, bağlam kaybı veya desteklenmeyen güvenlik iddiası. | İlgili karar referansıyla seçilmiş metin; kapsam, eksik işler ve kanıt sınırını koru. Ham iç ledger'ı otomatik ek olarak verme. |
| D08 — Manifest ve fingerprint bilgileri | Dosya/gözlem ilişkisini izlemek; mevcut manifest, dosya hash kaydı, source/item fingerprint. | Dosya adı, producer metadata ve ilişkiler özel bağlamı açığa çıkarabilir; hash'e aşırı güven üretilebilir. | Yalnız gerekli mevcut kimliği ve gerçekten kontrol edilmiş bütünlük kapsamını paylaş. Gereksiz yerel path ve metadata'yı çıkar; yeniden paketlenmiş/redakte byte'ı özgün hash ile tanımlama. |

Rendered item'ın evidence referansları, ham request/response'un dosyada bulunduğu anlamına gelmez. Kaynağın belirli assessment gözlemcisi text sampling ve ek hassas header yakalamayı daraltır; bu dar kod yolu bütün feature'lar, belgeler veya ayrıca sağlanan kanıtlar için sır temizliği garantisi değildir. [Pinli assessment observer, policy.rs95–114](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/http_evidence/policy.rs#L95-L114), [DELIVERABLE_SPEC §3](../DELIVERABLE_SPEC.tr.md#3-her-öğe-için-kayıt).

`redacted_summary` gibi alan adları veya düz metin/HTML encoding, sırların kaldırıldığını kanıtlamaz. Kaynak metin paylaşılmadan ayrıca gözden geçirilmelidir. [Pinli paylaşım uyarısı, reporting.md590–597](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L590-L597).

## Her sınıf için açık karar kaydı

Bu tablo bir onay kaydı değil, doldurulmamış başlangıçtır. `decision_owner` gerçek karar verecek kişi/kurumsal rol ve yetki bağıyla ileride doldurulur; rol adı önerisi atanmış kişi sayılmaz. Saklama süresi, tetikleyici tarih, kopya/yedek istisnası ve silme kanıtı henüz seçilmedi.

| Sınıf | `decision_owner` | `retention_decision` | `deletion_decision` | Müşteri çıktısı: `client_inclusion` |
|---|---|---|---|---|
| D01 Assessment metadata | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision` |
| D02 Hedef/domain/IP | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision` |
| D03 HTTP/header | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision` |
| D04 Cookie/token/credential | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision`; ham değer handoff'a taşınmaz |
| D05 Kanıt/payload | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision` |
| D06 İç uzman notu | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision`; iç kayıt otomatik paylaşılmaz |
| D07 Müşteri özeti | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision` |
| D08 Manifest/fingerprint | `pending_decision` | `pending_decision` | `pending_decision` | `pending_decision` |

Her sınıfın karar kaydına şu alanlar eklenir: `case_id`, sınıf ID'si, ilgili `source_artifact_ref` / gözlem ref'i, `decision_id`, gerekli amaç, asgari içerik, erişebilecek roller, saklama yeri/kopyalar/yedekler, aktarım alıcısı/kanalı, seçilen korumaların gerçek kanıtı, paylaşım gerekçesi, saklama/silme kararları ve açık takip. Bulunmayan karar `pending_decision`, bulunmayan gerçek kanıt `not_provided` kalır. Bu dosyada belirlenmiş saklama günü veya otomatik silme işi yoktur.

Erişim, yer, aktarım, yedek/silme, olay inceleme/temas ve gerekiyorsa hukuki/kurumsal kararlar da `pending_decision` durumundadır. Bu kit şifreleme, güvenli paylaşım, ACL, tüm kopyaların silinmesi veya olay bildirim süresi vaat etmez. Beklenmeyen sır/kişisel veri veya erişim belirsizliği ortaya çıkarsa paylaşım hazırlanmaz; sorumlu karar ve [DELIVERY_GATE](DELIVERY_GATE.tr.md) kaydı bekletilir. Mevcut sentetik dosyalar için de bu metin bir silme talimatı değildir.

## İç kayıt ve müşteri çıktısının ayrılması

**Internal Review Record**, kaynak/gözlem bağı, karar gerekçesi, kanıt eksikliği, redaksiyon nedeni ve bitmemiş işleri tutar. **Client Handoff**, yalnız ayrı kararla paylaşılması uygun görülen metin ve gerekli sınırlamalardan oluşur. İç kayıtta ham sır tutmanın gerekli veya izinli olduğu varsayılmaz. Bir iç ref'in müşteri metninde bulunması, ham kanıtın eklenmesi veya müşterinin o depoya erişebilmesi demek değildir.

`client_inclusion` yalnız `pending_decision`, `include_with_limits`, `exclude_with_reason` kullanır. Dahil etme/hariç tutma için [inceleme politikasındaki](OBSERVATION_REVIEW_POLICY.tr.md#karar-kuralları) gerekçe, dayanak/sınırlama ve `decision_id` zinciri gerekir. Belge hazırlayanın metni ayıklaması gerçek uzmanın kararı veya gerçek paylaşım onayı olarak kaydedilmez. Ham credential'ın müşteri çıktısına alınmaması kuralı, diğer veri sınıflarını otomatik paylaşılabilir yapmaz.

Kaynak artefact byte'ı korunur; müşteri için redaksiyon yapılırsa türetilmiş dosya ayrı referans/sürümle anlatılır. Hash gerçekten ölçülmediyse yazılmaz. Özgün manifest redakte dosyanın bütünlüğünü kanıtlamaz. Manifest/hash eşleşmesi de producer/target kimliği, yetki, finding doğruluğu, HTML güvenliği veya remediation değildir. [Pinli bütünlük sınırı, reporting.md411–419](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419).

## Bu fazın veri durumu

**Demonstration only — No real system assessed.** Yalnız [Phase14'ün mevcut sentetik/benign artefact kayıtları](../examples/README.tr.md) kullanılır. Incomplete dosyanın elle hazırlanmış fixture olduğu ve comparison'ın ayrı örnek olduğu korunur. Gerçek müşteri verisi, paylaşım, erişim/saklama kararı, silme, uzman incelemesi veya teslim yapılmış sayılmaz. Bu rehber, [PILOT_READINESS](../PILOT_READINESS.tr.md) açık kapılarını kapatmaz.
