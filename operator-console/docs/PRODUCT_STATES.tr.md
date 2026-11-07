# Ürün ve veri durumlarının anlamı

Bu ekran güvenlik skoru veya enforcement denetimi değildir. Kayda erişim, bağlantı tazeliği, ürünün çalışma beyanı ve bağımsız doğrulama ayrı gösterilir. Aynı yeşil/kırmızı “sağlık” sonucuna birleştirilmez.

## Üç zaman

| Bilgi | Kaynak | Ne kanıtlamaz? |
|---|---|---|
| Konsolun son yükleme saati | Kullanıcının son GET/görünüm okuması | Cihazdan yeni rapor geldiğini kanıtlamaz. |
| `last_received_at` / ürün `received_at` | Merkezin son snapshot kabulü | Ürünün o anda sağlıklı veya enforcement'ın etkin olduğunu kanıtlamaz. |
| `source_observed_at` / `observation` | Cihazın bildirdiği kaynak zaman ve API yaş zarfı | Bağımsız saat doğrulaması değildir. |
| Termivar `imported_at` / `report_import_age` | Cihazdaki yerel rapor içe aktarması | Rapor üretim, tarama veya scanner çalışma zamanı değildir. |

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

## Termivar

`experimental/unknown` ürün durumu; `scanner_installed`, `execution_available` ve `report_presence` birbirinden ayrıdır. `present` yalnız son rapor özetinin varlığını, `none` bu snapshot'ta rapor olmadığını, `unknown` bilinmediğini söyler. Rapor olması scanner'ın kurulu/çalışır olduğu veya merkezden tarama yapıldığı kanıtı değildir. Bu ürün arayüzünde scan/import/target/ham kanıt görünümü yoktur.

İçe aktarma zamanı, SHA256 digest, subject/item sayıları ve disposition/severity toplamları kaynak özetidir. `confirmed`, raporun kendi disposition alanıdır; merkezin veya bağımsız inceleyenin doğruladığı güvenlik bulgusu gibi etiketlenmez. `not_verified` her zaman korunur. HTML rapor/link önizlemesi, hedef URL veya kanıt yolu bu DTO'dan üretilmez.

## Planlanan antivirüs

`planned` + `unavailable`, **“Planlanan ürün — kullanıma hazır değil”** anlamındadır. `unknown` değerleri bilinmiyor kalır. Kurulu/etkin/koruyor rozeti, AV testi, tarama sonucu veya “yakında tara” eylemi eklenmez. Bu konsol AV motoru veya uzaktan yürütücü değildir.

## Sözleşme uyuşmazlığı

Runtime doğrulama gerekli alanları/türleri ve ilişkileri kontrol eder. Bilinmeyen güven/koruma enum'u olumluya çevrilmez; eksik/uygunsuz yanıt açık hatadır. JavaScript'in kesin temsil sınırını aşan BIGINT/sayaç değerleri yuvarlanmaz: fail closed sözleşme hatası gösterilir. 401 bağlantıyı temizler, 403 erişimi reddeder; ikisi “kayıt yok” değildir. Canlı API hatasında sentetik kayda geçilmez.

Örnek veri kipinde bu senaryolar yalnız ürün görünümünü anlatır. Gerçek Windows kabulü, IdP, üretim API, policy revision otoritesi veya enforcement kanıtı oluşturmaz.

## Seçili cihaz raporu

[Durum raporu](REPORTS.tr.md), açılıp görüntülenmiş ayrıntıların açık alan listeli kopyasıdır; yeni tarama, ölçüm veya merkezî snapshot değildir. Her kaydın kaynak/alım/okuma zamanı korunur; sabit rapor oluşturma zamanı veriyi tazelemez. Eksik sayılar sıfıra, self_reported/not_verified olumlu güven sonucuna çevrilmez. Örnek veri etiketi baskıda da kalır. Ad/kimlik gizleme anonimleştirme, tarayıcı yazdırma/PDF akışı da policy/enforcement veya dosyanın kaydedildiğine ilişkin kabul kanıtı değildir.

## İki dilde aynı anlam

[TR/EN yerelleştirme](LOCALIZATION.tr.md) yalnız sunumdur. **Cihazın bildirdiği / Reported by the device**, **Bağımsız doğrulanmadı / Not independently verified**, **Bilinmiyor / Unknown**, **Veri yok / No data**, **Güncel değil / Stale** ayrımları korunur. **Device registration revoked**, firewall disabled değildir; **Planned product — unavailable** etkin AV değildir. Dil, 404 nedenini kesinleştirmez veya doğrulama/güncellik düzeyini yükseltmez. Timestamp ve sayısal veriler değişmez; tr-TR/en-GB sunumu aynı UTC anını gösterir.
