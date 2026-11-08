# Termivar pilot kapsamı — doldurulmamış çalışma taslağı

Durum: **not_authorized / not_started**. Bu belge gerçek müşteri sözleşmesi veya hukuki görüş değildir. Bir hedef sahibinin yetkisi, çalışma emri, değerlendirme izni veya başlamış pilot anlamına gelmez. Bu faz yalnız ticari hazırlıktır; hedef, tarih, müşteri, credential veya kabul sahibi uydurulmaz.

## 1. Kapsam nasıl bağlanır?

Pilot adayı önce aşağıdaki kapsam kaydını somut ve gözden geçirilebilir hale getirir. Değerlendirme ve yeniden değerlendirme ayrı çalışmalardır. Her çalışma için kaynak artefact kimliği ve insan inceleme notu ayrıca tutulur.

| Karar alanı | Pilot öncesi doldurulacak bilgi | Mevcut durum |
|---|---|---|
| Yetkilendiren ve varlık ilişkisi | Hedef sahibi/temsilci, yetkisinin temeli, yetki kaydı ve geçerli faaliyet sınırı | `not_established` |
| Tam hedef | Scheme, host, port; izinli kaynak/API endpoint kapsamı; ortamın üretim/staging niteliği | `not_selected` |
| Hariçler | Yol/işlem ve veri sınıfları; ödeme, hesap/oturum değişimi, yönetim, üçüncü taraf servisler gibi hassas alanların açık listesi | `not_selected` |
| Değerlendirme yolu | Seçilen executable/source/hash/compile features; profil, opt-in bayrakları ve gerekli non-secret policy revizyonları | `not_selected` |
| Pencere ve temas | Başlangıç/bitiş penceresi, hedefi izleyen teknik irtibat, operatör, durdurma ve yeniden başlatma kararı | `not_assigned` |
| Bütçe | Kullanılacak built-in yolun request/time/body/byte limitlerinin kabulü; provider/IdP varsa ayrı kapsamı | `not_accepted` |
| Veri | Erişim, aktarım, saklama yeri/süresi, yedek, silme ve olay kararı | `open` |
| Uzman/kapanış | Kanıt inceleyicisi, rapor kalite kontrolü, takip sorumlusu ve müşteri kabul rolü | `not_assigned` |

Origin/endpoint listesi kapsam kaydıdır; kendi başına yetki kanıtı değildir. CDN, IdP, OAST/provider veya ortak barındırma servisi müşteriye ait origin ile otomatik yetkilendirilmez. Redirect görülmesi yeni hedefe izin vermez. Source discovery **exact-origin** ile sınırlıdır ve redirect takip etmez; bu teknik sınır müşterinin bütün varlıklarına veya bütün endpoint'lere yetki oluşturmaz. [Profil constructors](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/scan_profile.rs#L487-L508), [runtime sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/FEATURES.md#L29-L31).

## 2. İzin verilebilecek faaliyetler

İlk pilot taslağının varsayımı, kabul edilmiş bir exact-origin üzerinde **temel, credentialsız `web-review`** ve ardından ayrı insan incelemesidir. Kaynağın mevcut bounded discovery, semantic extraction, pasif ve düşük riskli differential yolları kapsam formunda açıkça kabul edilmiş olmalıdır. Bunlar bütün uygulamanın pentest'i veya doğrulanmış zafiyet sonucu değildir; native web-review `Confirmed` üretmez. GET veya “düşük riskli” adı yan etkisizlik garantisi değildir. [Native davranış ve sınırlar](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/FEATURES.md#L29-L31).

API hedeflerinde OpenAPI/REST/GraphQL/authorization aynı faaliyet sayılmaz. Seçilen build'de derlenmiş özellik, desteklenen girdi, yöntem ve runtime opt-in ayrıca kabul edilmeden dahil değildir. Örneğin GraphQL sınırlı anonim POST içerir; REST review ise desteklenen OpenAPI catalogue'dan bir anonim bodyless GET ile sınırlıdır. [Gerçek API alt kümeleri](CAPABILITY_CLAIMS.tr.md). Dolayısıyla “tüm API yöntemleri/rolleri test edildi” ifadesi kullanılmaz.

Supplied-session, OAuth/OIDC, WordPress, OAST/XML, provider çağrısı, JWT, browser/interaktif login ve diğer ek yollar ilk temel kapsamın parçası değildir. Sonraki bir teklif için seçileceklerse ayrı kaynak/build/özellik, hedef ve veri kabulü gerekir. Burada bu seçimler yapılmaz. Keyfî payload/istek, credential denemesi, brute force, exploit/impact, hizmet engelleme, kapsam dışı discovery veya canlı sistem değişikliği dahil değildir.

Değerlendirme sonrasında desteklenen complete JSON'u inceleme, uygun native rapor dosyalarını gözden geçirme ve iki uygun complete kaynağın çevrimdışı karşılaştırılması kapsamlandırılabilir. Offline karşılaştırma yeni hedef değerlendirmesi değildir; `--same-scope` yalnız operatör beyanıdır. [Karşılaştırma args ve explicit scope](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/report_compare.rs#L20-L43).

## 3. İstek, zaman ve çıktı bütçesi

| Sınır | İlk temel web-review için kaynak varsayılanı | Kabulde korunacak anlam |
|---|---:|---|
| Subject / discovery depth | 64 / 2 | Sınırlı retained envanter; bütün site kapsanmış sayılmaz |
| Belge başına reference | 128 | Omitted/skipped veya erişilemeyen alanlar ayrıca açıklanır |
| Paylaşılan broker request | 256 | Başarılı cevap/bulgu sayısı veya bütün dış sistem çağrılarının evrensel sayacı değildir |
| Wall-time | 300 saniye | Motorun değerlendirme sınırı; rapor teslim/uzman emeği/SLA süresi değildir |
| Per-response body / toplam response | 256 KiB / 16 MiB | Retention ve muhasebe sınırı; dönen her veri sınırsız işlenmez |
| Temel active verification / concurrency | 10 / 1 | Opt-in child allowance'ları bütün kombinasyonlarda aynı değildir |

Kaynak [WebAssessmentLimits309–375](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/web_assessment.rs#L309-L375), [Default706–722](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/web_assessment.rs#L706-L722), [optional allowance2929–2984](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/web_assessment.rs#L2929-L2984). Baseline ayrı single-resource profildir: 16 request / 60 saniye / toplam1 MiB; aynı müşteri assessment çıktısı olarak sessizce ikame edilmez. Hard cap ve source default, kabul edilmiş ticari limit değildir.

Mevcut CLI custom profil/bütçe override dosyası sunmaz. Müşterinin kabul ettiği sınır desteklenen built-in yola uymuyorsa pilot başlamaz; olmayan bayrak veya yeni library host varmış gibi tarif edilmez. Manuel durdurmanın daha düşük bir sayısal sınırı anlık ve kesin uyguladığı iddia edilmez. Ek provider/IdP yolları seçilirse onların muhasebesi ve izinleri ayrıca kabul edilmelidir; temel broker tablosu buna onay vermez.

İnsan hazırlık, inceleme, raporlama ve destek süreleri ayrı tutulur. Kaynak report payload limiti16 MiB; CLI comparison ve console importer limitleri de farklıdır. Örneğin console assessment1 MiB/comparison8 MiB alt kümesi native CLI kapasitesi gibi pazarlanmaz. [Teslim standardı](DELIVERABLE_SPEC.tr.md), [console sınırları](../../operator-console/docs/TERMIVAR_REVIEW.tr.md).

## 4. Durdurma ve yeniden başlatma

Şu durumlardan biri oluştuğunda operatör yeni faaliyet başlatmayı bırakır ve kapsam/olay kaydını günceller:

- Hedef sahibinin veya tanımlı irtibatın durdurma talebi; yetkinin, sürenin veya hedef ilişkisinin belirsizleşmesi.
- Kapsam dışı origin/resource, beklenmeyen üçüncü taraf bağı, erişim/credential bağlamı veya onaylanmamış feature ihtiyacı.
- Hedefte beklenmeyen erişilebilirlik/latency/hata veya iş akışı etkisi; yan etki şüphesi ve izleme kanalının kaybı.
- Beklenmeyen sır/kişisel veri, kanıt aktarımına ilişkin ihlal şüphesi veya kabul edilmemiş saklama ihtiyacı.
- Motorun budget/deadline/cancellation sınırı, preflight hatası, incomplete/failed durumu, uygun olmayan build/artefact veya operatörün açıklayamadığı sonuç.

Bu liste operasyon taslağıdır; uygulanmış harici kill-switch veya gerçekleşmiş incident response kabulü değildir. Başlamış ağ isteğinin geri alınacağı, yapılmış yan etkinin rollback edileceği veya kesintisiz çalışma garantisi verilmez. Yeniden başlatma; neden, etkiler, kalan kapsam/bütçe ve gerekli yetkinin sorumlu kişilerce yeniden kabulüne bağlıdır. Otomatik retry/yeniden pilot başlatma taahhüdü yoktur.

## 5. Veri işleme kararları

| Karar | Pilot başlamadan yazılacak içerik | Durum |
|---|---|---|
| Asgari veri ve redaksiyon | Gerekli rapor/kanıt sınıfları, çıkarılacak secret/personal data ve paylaşım öncesi uzman kontrolü | `open` |
| Erişim | Müşteri/operatör/inceleyici ve üçüncü taraf erişimi, erişimin kaldırılması | `open` |
| Yer ve aktarım | Dosyaların bulunduğu ortam, alıcı ve kabul edilmiş korumalı aktarım kanalı | `open` |
| Saklama | Ham kaynak, türetilmiş rapor, credential ve yedek için ayrı süre ve karar sahibi | `open`; varsayılan gün uydurulmadı |
| Silme ve yedek | Silme yöntemi, doğrulama kaydı, kopya/yedek istisnaları ve kapanış sorumlusu | `open` |
| Olay ve açıklama | Veri/kanıt olayı temasları, durdurma, inceleme ve bildirim kararı | `open`; bağlayıcı süre tanımlanmadı |

Rendered alan adındaki “redacted” veya console'un varsayılan gizli sunumu, verinin sırdan arındırılmış/anonim olduğu garantisi değildir. CLI rapor/bundle yolu diske dosya yazabilir. Console'un seçilmiş yerel dosyayı yalnız tarayıcı belleğinde işlemesi bu hizmetin rapor dosyaları için otomatik saklama/silme/şifreleme politikası oluşturmaz. Credential değerleri teklif, rapor manifesti, URL veya normal log'a taşınmaz; gerekirse yalnız desteklenen secret giriş sınırı ayrıca kabul edilir. [Rapor I/O sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L1-L18), [console yerel veri sınırı](../../operator-console/docs/TERMIVAR_REVIEW.tr.md).

## 6. Uzman incelemesi, kabul ve kapanış

NeedsReview, KnowledgeOnly, eksik veya çelişkili kanıt, atanmamış severity, source/manifest uyuşmazlığı, eksik assessment ve karşılaştırılamayan kapsam uzman tarafından açıkça ele alınır. `Success`, complete, parse veya hash eşleşmesi tek başına güvenlik/kapanış kararı değildir. Öğenin listeden kaybolması düzeltme kanıtı yapılmaz. İnceleyen kişi ve gerekçe atanmamışsa `review_status=not_performed` kalır; yeni native JSON alanı üretilmez.

Pilot kapanış önerisi: kabul edilmiş kapsam ve hariçler raporda bulunur; her öğenin kaynak/kanıt ilişkisi ve insan inceleme durumu kaydedilir; incomplete/skipped/bilinmeyen alanlar açıklanır; teknik takip ve ayrı yeniden değerlendirme gereği görünürdür; teslim dosyalarının kimlikleri, emek/destek kayıtları ve kabul eden tarafın kararı vardır. Açık teknik işlerle kapanış yapılacaksa hangi işlerin açık kaldığı ayrıca kayıtlıdır; bunlar düzeltilmiş sayılmaz. Ölçülebilir ölçütler [PILOT_READINESS](PILOT_READINESS.tr.md) içindedir.

Bu taslak kapsam onayı, müşteri kabulü veya ücretli pilot başlatma kararı içermez. HBF Windows, platform IdP ve gerçek policy revision otoritesi kararları ayrı ürünlere aittir; burada yeniden istenmez.
