# Ürün ve veri durumlarının anlamı

Bu ekran güvenlik skoru veya enforcement denetimi değildir. Kayda erişim, bağlantı tazeliği, ürünün çalışma beyanı ve bağımsız doğrulama ayrı gösterilir. Aynı yeşil/kırmızı “sağlık” sonucuna birleştirilmez.

## Üç zaman

| Bilgi | Kaynak | Ne kanıtlamaz? |
|---|---|---|
| Konsolun son yükleme saati | Kullanıcının son GET/görünüm okuması | Cihazdan yeni rapor geldiğini kanıtlamaz. |
| `last_received_at` / ürün `received_at` | Merkezin son snapshot kabulü | Ürünün o anda sağlıklı veya enforcement'ın etkin olduğunu kanıtlamaz. |
| `source_observed_at` / `observation` | Cihazın bildirdiği kaynak zaman ve API yaş zarfı | Bağımsız saat doğrulaması değildir. |
| Termivar Web `imported_at` / `report_import_age` | Cihazdaki yerel rapor içe aktarması | Rapor üretim, tarama veya scanner çalışma zamanı değildir. |

Ekranı yenilemek yalnız konsolun okuma bilgisini değiştirir. API'nin `connection_status` değeri aynen korunur; UI yeni stale eşiği veya SLA icat etmez. Tarayıcı saatinden ek yaş gösterilirse yalnız görüntüleme bilgisidir. `clock_state=future` pozitif bir tazelik/sağlık işareti değildir; yaş bilinmiyor kalır.

## Veri, kimlik ve güven

| DTO durumu | Ürün dili |
|---|---|
| Rapor/alım yok, `never_seen` | Henüz merkezde rapor yok; ürünün gerçekte kapalı/kurulu olmadığı sonucu çıkarılmaz. |
| `unknown` veya nullable alan | Bilinmiyor; sıfır/çalışıyor/güvenli değildir. |
| `recent` | Yakın zamanda bildirim alındı; “çevrimiçi/korunuyor” değildir. |
| `stale` | API'ye göre bildirim eski; veri silinmez veya yeniymiş gibi sunulmaz. |
| Cihaz `identity_status=revoked` | Cihaz kaydı iptal edilmiş. Bu API'nin credential erişimine etkisi vardır; HBF'nin durduğu, kaldırıldığı veya paket engellemesinin kapandığı iddiası değildir. |
| `source=self_reported` | Cihazın bildirdiği. |
| `producer_verification=not_verified` | Bağımsız doğrulanmadı. TLS/başarılı GET/credential kimliği bu düzeyi yükseltmez. |
| `missing_products` içinde ürün | Bu geçerli snapshot'ta ürün bildirimi yok. Önceki snapshot'tan kart/state taşınmaz. |

`last_sequence` ve `snapshot_sequence`, snapshot sıralamasıdır; policy revision/lineage, CAS, applied veya verified kanıtı değildir. Mevcut envanter DTO'su legacy policy hash taşımadığı için konsol böyle bir alan uydurmaz. Başka kaynaktan bildirilen legacy hash de tam davranış/uygulanma/doğrulama kanıtına dönüştürülemez.

## HostBasedFirewall

`installed`, `reported_running`, `reported_stale`, `firewall_mode`, `error_codes` ve `status` ayrı cihaz beyanlarıdır. `running` çalışma bildirimi, `observing` gözlem bildirimi, `degraded` sorun bildirimi, `stopped` durmuş bildirimi, `unavailable/unknown` kullanılamaz/bilinmiyor bilgisi verir. Bunlar bağımsız servis/driver/native firewall kabulü değildir.

`firewall_mode=enforce` bildirilen uygulama modu, `sniff` gözlem modu, `unknown` bilinmeyen moddur. Tek başına “trafik korunuyor” rozeti oluşturmaz. Hata kodunun yokluğu veya boş hata listesi olumlu güvenlik kabulü değildir. Kaynak/alım eskiliği ayrıca görünür kalır.

## Termivar Web

`experimental/unknown` ürün durumu; `scanner_installed`, `execution_available` ve `report_presence` birbirinden ayrıdır. `present` yalnız son rapor özetinin varlığını, `none` bu snapshot'ta rapor olmadığını, `unknown` bilinmediğini söyler. Rapor olması scanner'ın kurulu/çalışır olduğu veya merkezden tarama yapıldığı kanıtı değildir. Bu ürün arayüzünde scan/import/target/ham kanıt görünümü yoktur.

İçe aktarma zamanı, SHA256 digest, subject/item sayıları ve disposition/severity toplamları kaynak özetidir. `confirmed`, raporun kendi disposition alanıdır; merkezin veya bağımsız inceleyenin doğruladığı güvenlik bulgusu gibi etiketlenmez. `not_verified` her zaman korunur. HTML rapor/link önizlemesi, hedef URL veya kanıt yolu bu DTO'dan üretilmez.

## Planlanan antivirüs

`planned` + `unavailable`, **“Planlanan ürün — kullanıma hazır değil”** anlamındadır. `unknown` değerleri bilinmiyor kalır. Kurulu/etkin/koruyor rozeti, AV testi, tarama sonucu veya “yakında tara” eylemi eklenmez. Bu konsol AV motoru veya uzaktan yürütücü değildir.

## Altay EDR ajanı

Snapshot V2 (Aşama 2 adım 3) ile cihaz ayrıntısı **Altay EDR ajanı / Altay EDR agent** kartını gösterir. Kart ajanın kendisi hakkında söylediğidir; tamamı `self_reported` / `not_verified` kalır ve kart **“Ajan kendi durumunu bildirir; koruma veya kural yükleme iddiası değildir”** notunu taşır. Ajan bir prototiptir; gerçek sensörün sanal makinede kabulü henüz yapılmadı.

| Görünen bilgi | Anlamı | Ne kanıtlamaz? |
|---|---|---|
| “Hizmet döngüsü çalıştığını bildirdi” (`status=running`) | Ajanın servis döngüsü durumu oluştururken bunu bildirdi. `unknown` bilinmiyordur (ör. tek seferlik `edr-agent heartbeat` komutu). | Korumanın çalıştığını veya sensörün olay topladığını. |
| Ajan sürümü, başlangıç zamanı, motor kimliği | Ajanın bildirdiği sürüm, süreç başlangıcı (cihaz saati) ve motor kimliği. | Yayıncı, imza veya ikili dosya doğrulamasını. |
| Kural dosyası: **Var / Yok / Bilinmiyor** | Yalnız kural dosyasının var olup olmadığı. | Kuralların yüklendiğini veya uygulandığını; servis Aşama 2'de kural yüklemez. “Yüklü” denmez. |
| Sensör durumu | Başladı, Kayboldu, Başarısız, Durdu, Devre dışı (sensörsüz çalışma, `--no-sensor`) veya Bilinmiyor. | Sensörün gerçekten olay topladığını. |
| Sensör hata kodu | Yalnız Kayboldu/Başarısız ile gelen kod; kod yoksa “Kod bildirilmedi”, diğer durumlarda “Bu durumda kod yok”. | Hatanın nedenini. |
| Sayaçlar ve giden kutusu birikimi | Ajan sürecinin başlangıcından beri düşen, yazılamayan, eşlenemeyen, atlanan, sınırda silinen, başka kayda ait diye atılan ve indirgenmiş kabul edilen olaylar; gönderilmeyi bekleyen kayıtlar. **Bilinmiyor** değerin bildirilmediğidir, sıfır değildir. | Kaybın tamamını veya sıfırın gerçek olduğunu; sayaçlar süreç yeniden başlayınca sıfırlanır. |

Ajanı bildirmeyen cihazda kart **“Bildirim yok”** olarak kalır; ajanın kurulu olmadığı varsayılmaz. Kartta koruma, gerçek zamanlı koruma veya “kurallar yüklü” rozeti yoktur. Durum raporu ve cihaz karşılaştırması Snapshot V2 adımında ajan kartını kopyalamıyordu; GitHub #15'ten beri ikisi de ajanın kendi durumunu kartın etiketleriyle gösterir. Rapordaki her ajan değeri **“Ajanın beyanı · bağımsız doğrulanmadı”** işaretini taşır; karşılaştırmada ajanın bildirdiği değerlerin satırları da, sonuçlarının kendi notu yoksa, aynı notu, ajan bölümü de değerlerin ajanın kendi beyanı olduğunu söyleyen notu taşır. Raporun ajan notu ve karşılaştırmanın bölüm notu kartın “koruma veya kural yükleme iddiası değildir” ifadesini de içerir. Ajanı bildirmeyen cihazda ajan eksik ürün olarak görünür ([teslim kaydı](DELIVERY.tr.md)).

## Sözleşme uyuşmazlığı

Runtime doğrulama gerekli alanları/türleri ve ilişkileri kontrol eder. Bilinmeyen güven/koruma enum'u olumluya çevrilmez; eksik/uygunsuz yanıt açık hatadır. JavaScript'in kesin temsil sınırını aşan BIGINT/sayaç değerleri yuvarlanmaz: fail closed sözleşme hatası gösterilir. 401 bağlantıyı temizler, 403 erişimi reddeder; ikisi “kayıt yok” değildir. Canlı API hatasında sentetik kayda geçilmez.

Örnek veri kipinde bu senaryolar yalnız ürün görünümünü anlatır. Gerçek Windows kabulü, IdP, üretim API, policy revision otoritesi veya enforcement kanıtı oluşturmaz.

## Olaylar ve uyarılar

| Görünen bilgi | Anlamı | Ne kanıtlamaz? |
|---|---|---|
| Olay satırı | Cihazın bildirdiği süreç veya sensör olayı (`self_reported`, `not_verified`). | Olayın gerçekten olduğunu veya cihazın tam kayıt tuttuğunu. |
| Gözlem / alım zamanı | Cihaz saati / sunucunun batch'i aldığı an. | Cihaz saatinin doğruluğunu. |
| “n olay kayıp” satırı | Yüklenen iki olay arasında platformun tutmadığı sıra numaraları. | Kaybın nedenini (cihaz kaybı, sınır veya saklama silmesi). |
| Sınırın sildiği olaylar, bastırılan uyarılar | Platformun cihaz başına sayaçları. | Cihazın davranışının zararsız veya zararlı olduğunu. |
| Uyarı | Cihaz olaylarının basit bir sunucu kuralına uyması; tekrarlar bir uyarıda sayılır. | Teşhis, kötü amaçlı yazılım, saldırı veya ihlal. Kötü niyetli bir cihaz kendi uyarılarını tetikleyebilir veya bastırabilir. |
| Açık / onaylandı / kapatıldı | API'de yapılan operatör geçişi; konsol bunu değiştirmez. | Olayın incelendiğini veya çözüldüğünü. |

Uyarı yokluğu “temiz cihaz” değildir: kurallar dar ve basittir, olaylar eksik olabilir ve kapalı uyarılar saklama süresi dolunca (`alerts prune`) silinir.

## Seçili cihaz raporu

[Durum raporu](REPORTS.tr.md), açılıp görüntülenmiş ayrıntıların açık alan listeli kopyasıdır; yeni tarama, ölçüm veya merkezî snapshot değildir. Her kaydın kaynak/alım/okuma zamanı korunur; sabit rapor oluşturma zamanı veriyi tazelemez. Eksik sayılar sıfıra, self_reported/not_verified olumlu güven sonucuna çevrilmez. Örnek veri etiketi baskıda da kalır. Ad/kimlik gizleme anonimleştirme, tarayıcı yazdırma/PDF akışı da policy/enforcement veya dosyanın kaydedildiğine ilişkin kabul kanıtı değildir.

## İki dilde aynı anlam

[TR/EN yerelleştirme](LOCALIZATION.tr.md) yalnız sunumdur. **Cihazın bildirdiği / Reported by the device**, **Bağımsız doğrulanmadı / Not independently verified**, **Bilinmiyor / Unknown**, **Veri yok / No data**, **Güncel değil / Stale** ayrımları korunur. **Device registration revoked**, firewall disabled değildir; **Planned product — unavailable** etkin AV değildir. Dil, 404 nedenini kesinleştirmez veya doğrulama/güncellik düzeyini yükseltmez. Timestamp ve sayısal veriler değişmez; tr-TR/en-GB sunumu aynı UTC anını gösterir.

## Aynı sayfada cihaz ayrıntıları arasında geçiş

Önceki/sonraki kapsamı tüm kurum değildir: mevcut yüklü sayfada, ekrandaki arama/filtre/sıralama sonucunda bulunan cihazlardır. Sınırda geçiş durur; sarmalama, gizli prefetch veya sayfa okuma yoktur. Her açık geçiş yalnız seçilen hedefin mevcut ayrıntı okumasıdır; yükleniyor/hata durumu o hedefe aittir ve ürünün güvenlik durumuna çevrilmez.

Pencereyi kapatma liste seçimini ve sayfayı, dil değiştirme hedef cihazı korur. Tenant/kip/erişim bağlamı ve gecikmiş yanıt kuralları genişletilmez. Cihaz gezintisi rapordaki seçilmiş kopyaları kendiliğinden eklemez veya yenilemez; ekleme/güncelleme yine başarıyla görüntülenen ayrıntıda açık eylemdir.
