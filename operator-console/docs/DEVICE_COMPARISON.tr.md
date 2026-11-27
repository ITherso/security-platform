# Cihaz güvenlik durumu karşılaştırması

Bu alan, kullanıcının ayrıntısını gerçekten açtığı **iki cihazın bildirimlerini** yan yana gösterir. **Gerçek koruma eşdeğerliğini doğrulamaz.** Güvenlik skoru, risk sıralaması, konfigürasyon eşdeğerliği, uyumluluk ihlali veya politika/enforcement sonucu üretmez.

## İki cihazı seçme

1. Mevcut cihaz listesinden bir ayrıntıyı açın. Yükleme tamamlanıp geçerli DTO görüntülendikten sonra **Karşılaştırmaya ekle** eylemini kullanın. Yükleniyor/hata ekranı veya liste satırı karşılaştırma veri kaynağı değildir.
2. Başka cihazın ayrıntısını açıp onu da ekleyin. İlk seçimden sonra ikinci sütun, karşılaştırmak için başka bir cihaz seçilmesi gerektiğini açıklar. Gezinmedeki karşılaştırma sayacı en fazla **2/2** olur.
3. Aynı cihaz ikinci kez ayrı kayıt olarak eklenmez. Önceden seçilmiş cihazı yeniden açmak eski kopyayı yenilemez; **Karşılaştırmadaki kaydı bu görüntülenen bilgilerle güncelle** eylemi gerekir.
4. İki taraf doluyken üçüncü cihaz için değiştirilecek tarafı açıkça seçin. Bir taraf sessizce silinmez veya değiştirilmez. Tek seçimi kaldırabilir ya da bütün karşılaştırmayı temizleyebilirsiniz.

Eklemek, değiştirmek, güncellemek ve karşılaştırma alanını açmak yeni ayrıntı isteği yapmaz. Normal cihaz açma, mevcut detail GET'ini kullanabilir; komşu/diğer seçili cihazları topluca okuma, prefetch, polling veya otomatik retry yoktur. Genel cihaz önbelleği kurulmaz. Phase8 önceki/sonraki gezinmesi kendi yüklü sayfa sınırında kalır; karşılaştırmaya ise farklı liste sayfalarından elle açılmış cihazlar seçilebilir.

Karşılaştırma ve durum raporu ayrı seçimlerdir. Karşılaştırma eylemi rapora ekleme/çıkarma/güncelleme veya rapor önizlemesi oluşturmaz; raporun 20 cihaz/256 KiB sınırını ve kimlik tercihini değiştirmez. Bu alan PDF, yazdırma, export/import veya rapora otomatik aktarma sunmaz.

## Sabit kopya, boyut ve bağlam

Her seçim, doğrulanmış mevcut ayrıntıdan açık alan listesiyle oluşturulan immutable kopyadır. İç içe değişebilir DTO/session referansları taşınmaz. Sonraki API yanıtı, yeni okuma veya sıradan React render'ı seçilmiş kaydı sessizce değiştirmez.

Tek kayıt en fazla **32 KiB**, iki kayıtlık kapalı model toplamda en fazla **64 KiB UTF-8** olabilir. Sınır aşımında açıklama gösterilir; veri sessizce kesilmez. Bu küçük model yeni snapshot/revision/receipt veya doğrulama protokolü değildir.

İki kayıt aynı tenant, örnek/API kipi, örnek senaryosu ve bağlantı oturumu generation bağından gelmelidir. Tenant/kip/senaryo/API hedefi/token oturumu değişimi, disconnect ve mevcut 401/403/404 erişim temizliği karşılaştırmayı temizler. 404 tek başına üyelik iptali veya cihaz silinmesi diye açıklanmaz.

Normal ekran gezintisi, arama, filtre, sıralama ve sayfalama seçilmiş kopyaları korur. TR/EN değişimi de seçim/veri/okuma zamanlarını koruyup yalnız metni yeniden çizer; fetch/refresh/reconnect yapmaz. Tarayıcı sayfası yeniden yüklenince seçim geri gelmez. Kalıcı tarayıcı deposu, cookie, URL/query/hash veya backend saklaması yoktur. Güvenli context generation referansı dahili bağdır; ürün verisi, gerçek principal veya revision otoritesi değildir.

## Karşılaştırılan içerik

| Bölüm | Mevcut ayrıntıdan taşınan sınırlı bilgi |
|---|---|
| Cihaz ve kayıt | Görüntülenen ad/izin verilen kimlikler, cihaz kayıt durumu ve mevcut bildirim zamanları. DTO'nun vermediği ayrı agent sürümü uydurulmaz; Altay EDR ajanının kendi bildirdiği sürüm yalnız ajan bölümünde görünür. |
| HostBasedFirewall | Bildirilen ürün/çalışma/mod bilgileri, varsa mevcut ürün sürümü ve sınırlı durum alanları. Policy içeriği karşılaştırılmaz. |
| Termivar Web | Mevcut durum, rapor varlığı ve sınırlı sayısal özetler. Ham rapor, tarama hedefi ve kanıt taşınmaz. |
| Altay EDR ajanı | Ajanın kendi bildirdiği durum, sürüm ve cihaz ayrıntısındaki ajan kartının alanları, kartın etiketleriyle (GitHub #15): Snapshot V2 ve V3 alanları, sayaçlar, kaynak ve doğrulama. V3'ün iki listesi (etkin yanıt eylemleri, yanıt anahtarları) taşınmaz. Bölüm notu ve satır notları değerlerin ajanın kendi beyanı olduğunu ve bağımsız doğrulanmadığını söyler. |
| Antivirüs ve veri güvenilirliği | Planned/unavailable anlamı, kaynak, bağımsız doğrulanmadı ve eksik bilgi alanları. |

Token/Authorization, API base, principal/session nesnesi, enrollment/credential, JWT, audit payload/aktör, ham hata body’si, gizli yapılandırma, istek epoch/sequence/bağlantı sırrı veya serbest JSON metadata modele alınmaz. Ürün/agent sürümü veya başka bir alan kaynak DTO'da yoksa **Bilinmiyor / sağlanmıyor** kalır.

Kaynak gözlem zamanı, sunucu alım zamanı ve konsol okuma zamanı ayrı gösterilir. İki kayıt farklı anlara ait olabilir; eşzamanlı ölçüm garantisi yoktur. Tarihler mevcut tr-TR/en-GB biçimleyicisiyle açık **UTC** sunulur; eksik zaman şimdi/epoch'a dönmez. Karşılaştırmayı açmak verinin yaşını sıfırlamaz ve yeni SLA eşiği oluşturmaz.

## Alan sonuçlarının anlamı

| Sonuç | Anlamı |
|---|---|
| **Aynı** | Aynı tür/kapsamda karşılaştırılabilen iki geçerli değer eşittir. Yalnız o bildirilen alan için kullanılır. |
| **Farklı** | Aynı tür/kapsamda karşılaştırılabilen iki geçerli değer farklıdır. Daha iyi/kötü veya daha güvenli/riskli sonucu değildir. |
| **Eksik bilgi** | Bir veya iki tarafta gerekli değer yok/bilinmiyor. İki eksik/unknown değer “Aynı” değildir. Gerçek sıfır eksik değer değildir. |
| **Karşılaştırılamıyor** | Değerlerin anlamı veya gözlem kapsamı eşleştirilemiyor. Sayısal eşitlik tek başına yeterli değildir. |

İki tarafta HBF `enforce` olması yalnız aynı bildirilen mod olabilir; aynı koruma düzeyi değildir. Aynı `not_verified`, aynı **bağımsız doğrulanmamış beyan** düzeyidir; trusted/verified anlamı kazanmaz. Cihaz kaydının `revoked` olması firewall'ın durduğu/kaldırıldığı anlamına gelmez. İki planned/unavailable AV aktif koruma değildir. Termivar Web özeti scanner'ın kurulu/çalışır olduğunu veya merkezden tarama yapıldığını kanıtlamaz.

**Termivar Web sayıları:** Kaynak özetler iki cihazda aynı değerlendirme/hedef/zaman penceresini kanıtlamaz. Bu nedenle iki tarafta sayı bulunsa bile kapsamın aynı olduğu gösterilemiyorsa sonuç **Karşılaştırılamıyor** olur; artış/azalış, performans, güvenlik farkı veya risk puanı türetilmez. Bir tarafta sayı yoksa eksiklik ayrıca görünürdür. Sayıların aynı olması kapsam kanıtı değildir. Legacy policy hash eşitliği de eşit enforcement davranışı sayılmaz; gizli policy/config karşılaştırması eklenmez.

**Altay EDR ajanı:** Sunucu alım zamanı, veri kaynağı ve doğrulama düzeyi dışındaki değerler ajanın kendi beyanıdır (`self_reported`); bağımsız doğrulanmadı (`not_verified`) ve koruma veya kural yükleme iddiası değildir. Ajan prototiptir, sanal makinede kabulü henüz yapılmadı. Konsol bu aşamada ajana aksiyon göndermez ve bir aksiyonun yapıldığını göstermez. Sonucunun kendi notu olmayan her ajan satırı, sunucu alım zamanı ve veri kaynağı dışında, raporun işaretiyle aynı **“Ajanın beyanı · bağımsız doğrulanmadı”** notunu taşır; eksik bilgi, karşılaştırılamayan ve doğrulama satırları kendi notlarını gösterir. İki tarafta aynı sensör, kural seti veya yetenek durumu aynı davranışı kanıtlamaz. Ajan sayaçları her ajanın kendi süreç başlangıcından beri sayıldığı için **Karşılaştırılamıyor** olur. Son eylem sırası ve karantina öğe sayısı bu aşamada ajan tarafından gönderilmez (`null`), bu yüzden satırları **Eksik bilgi** olur; değer bildirildiğinde de kapsamları tanımlanmadığı için **Karşılaştırılamıyor** olurlar. Snapshot V2 ve V3 ajanlarının alanları farklıdır: yalnız bir sürümde bulunan alan, seçili cihazlardan biri o sürümü bildirdiğinde satır olur; o alanı taşımayan sürümdeki ajanın tarafında **Bu ajanın Snapshot sürümünde bu alan yok** yazar ve sonuç **Eksik bilgi**dir. Ajanı bildirmeyen cihazda ajan alanları **Bilgi yok** gösterir; ajanın kurulu olmadığı varsayılmaz.

**Yalnız farklı alanları göster** varsayılan kapalıdır. Açıldığında yalnız görünüm süzülür; yakalanmış kayıtlar değişmez. Eksik ve karşılaştırılamayan alanlar görünür kalır. Varsa fark/eksiklik sayacı yalnız görüntülenen alanların sayısıdır; bulgu sayısı, güvenlik skoru veya kurum toplamı değildir.

## Örnek veri ve sınırlar

Örnek kipte üst uyarı ve her cihaz bölümündeki örnek kimliği korunur. **Cihazın bildirdiği / Reported by the device** ve **Bağımsız doğrulanmadı / Not independently verified** iki dilde aynı anlamı taşır. Karşılaştırma yerel sunum işlemidir; kaynak beyanını bağımsız doğrulamaya yükseltmez.

390px görünüm için bölüm bazında dikey yerleşim ve okunabilir fark etiketleri hedeflenir; gerçekleştirilen dar ekran gözlemi [DELIVERY](DELIVERY.tr.md) içinde ayrıca kaydedilir. Bu belgedeki kullanım açıklaması test, güvenlik/canlı API kabulü veya yapılmış PDF/Windows işlemi iddiası değildir.
