# Seçili cihazlar — ürün bildirim özeti

Durum raporu, kullanıcının açıp incelediği cihaz ayrıntılarından oluşan küçük bir bellek taslağıdır. Yalnız seçili cihazları kapsar; tüm kurum envanteri veya aynı anda alınmış merkezî snapshot değildir. En fazla **20 cihaz** ve toplam **256 KiB UTF-8 taslak verisi** kabul edilir. Sınır aşımında açıklama gösterilir; kayıt sessizce kesilmez veya ilk 20'ye indirilmez.

## Ekleme, güncelleme ve kaldırma

1. Cihazlar ekranından bir ayrıntıyı açın. Yalnız başarıyla yüklenmiş, runtime DTO denetiminden geçmiş ve görüntülenen ayrıntıda **Durum raporuna ekle** kullanılabilir. Yükleniyor/hata ekranı kayıt kaynağı değildir.
2. Gezinmedeki **Durum raporu (N)** girişinden seçilmiş kayıtları ve kapsamı görün. Aynı cihaz tekrar eklenince çoğaltılmaz. Daha sonra açılan ayrıntı eski rapor kopyasını kendiliğinden yenilemez; değiştirmek için **Rapordaki kaydı bu görüntülenen bilgilerle güncelle** eylemini kullanın.
3. Tek kaydı kaldırabilir veya taslağı temizleyebilirsiniz. Boş taslak açıklama gösterir; boş rapor yazdırma eylemi açılmaz.
4. Alan tercihini seçip önizleme oluşturun. **Düzenlemeye dön** taslağa döner. Taslak veya alan tercihi değişince eski önizleme geçersizleşir; yeniden önizleme oluşturmak gerekir.

Liste DTO'su ürün state'i taşımaz. Bu nedenle listeden toplu seçim, gizli N+1, bütün sayfaları çekme veya rapor için yeni ayrıntı isteği yoktur. Mevcut cihaz ayrıntısı gezinmesi kendi normal GET'ini kullanabilir; rapora ekleme/güncelleme, taslağı açma, önizleme ve yazdırma yeni fetch/refresh/polling başlatmaz.

## Ad ve kimlik seçimi

**Kurum ve cihaz adlarını/kimliklerini rapora dahil et** seçeneği varsayılan olarak kapalıdır. Kapalıyken rapor önizlemesi ve baskı **Seçili kurum**, **Cihaz 01** gibi rapora özgü etiketler kullanır. Dahili bağlama için tutulan tenant/device kimlikleri görünür veya gizli HTML alanına, başlığa ya da baskı attribute'una çevrilmez. Açık seçim, yalnız izin verilen mevcut ad/kimlikleri gösterir.

Bu seçenek **ad ve kimlikleri gösterme/gizleme** tercihidir; anonimleştirme garantisi değildir. Durumlar ve zamanlar yine seçilmiş cihazlara ait bilgidir. Yazdırılmış veya kaydedilmiş kopyanın bağlantı kesilince geri alınabileceği iddia edilmez.

## Taslak ne zaman temizlenir?

Taslak tek tenant, veri kipi ve bağlantı oturumu bağlamına aittir. Aynı bağlamdaki normal sayfa gezintisi seçimi korur; her ekran geçişi taslağı silmez. Tenant, örnek/API kipi, örnek senaryosu, API hedefi veya token/bağlantı oturumu değişince taslak ve önizleme temizlenir. Disconnect/401 veya erişimi etkileyen 403 de eski rapor kopyasının kalmasını engeller. Geciken eski yanıt yeni bağlamda taslak oluşturamaz.

Sayfa yenilenince taslak geri gelmez. localStorage/sessionStorage/IndexedDB/cookie/service worker veya backend rapor deposu yoktur. Bağlantı bağlamı token'ın kendisiyle değil, sayfa içindeki oturum kimliğiyle ilişkilendirilir; bu kimlik gerçek principal veya policy revision otoritesi değildir.

## İçerik ve zamanlar

Rapor yalnız açık alan listesinden oluşturulan, iç içe değişebilir referans taşımayan bir sunum kopyasıdır. Mevcut ad/kimlik tercihi, veri kipi, cihaz kayıt durumu, HBF/Termivar Web/AV'nin ve Altay EDR ajanının ürün bildirimleri, sağlanan sürümler, sınırlı sayısal özetler, zamanlar ve eksik/bilinmiyor/güven açıklamaları kullanılır. Sonraki API veya görünüm değişimi seçilmiş kaydı sessizce değiştirmez.

**Altay EDR ajanı** (GitHub #15): rapor, cihaz ayrıntısındaki ajan kartının alanlarını aynı etiketlerle kopyalar. Snapshot V2 ajanında durum, sürüm, başlangıç zamanı, motor kimliği, kural dosyasının varlığı (**Var / Yok / Bilinmiyor**), sensör durumu ve hata kodu ile sekiz sayaç yer alır. Snapshot V3 ajanında kural dosyası yerine kural seti durumu ve kimliği gelir; ayrıca davranış kuralları sürümü, hizmet yapılandırması, önceki çalışmanın bitişi, heartbeat aralığı, dört yetenek durumu, yanıt kanalı, son eylem sırası, yalıtım durumu ve zamanları ile karantina öğe sayısı yer alır ve sayaçlar on altıdır. V3'ün iki listesi, etkin yanıt eylemleri ve yanıt anahtarları, rapora alınmaz. Durum, sürüm, kaynak gözlem zamanı ve her ajan değeri **“Ajanın beyanı · bağımsız doğrulanmadı”** işaretini taşır. Ajan bildirildiğinde bölümün notu ajanın prototip olduğunu, sanal makinede kabulünün henüz yapılmadığını, işaretli değerlerin ajanın kendi beyanı olduğunu, bağımsız doğrulanmadığını ve koruma veya kural yükleme iddiası olmadığını, kural dosyası/kural seti bilgisinin de kuralların uygulandığını göstermediğini söyler; sayaç kapsamı notu da gelir. Snapshot V3 ajanında kartın tarama notu ve yanıt kapsamı notu da yer alır: konsol bu aşamada ajana aksiyon göndermez ve bir aksiyonun yapıldığını göstermez. Ajanı bildirmeyen cihazda ajan **Ürün bildirimi yok** olarak görünür; kendi değeri, ajan notu ve işareti yoktur. 20 cihaz/256 KiB sınırı değişmedi; en büyük V3 ajanlı 20 kayıt sınırın içinde kalır ([teslim kaydı](DELIVERY.tr.md)).

| Zaman | Anlamı |
|---|---|
| Kaynak bildirim/gözlem zamanı | Cihazın bildirdiği zaman; sağlanmayabilir. |
| Sunucu `received_at` / cihaz son alımı | Merkezin ilgili bildirimi kabul ettiği zaman. |
| Konsol okuma zamanı | Kullanıcının ayrıntıyı okuduğu zaman. Farklı cihazlar farklı okuma zamanlarından gelebilir. |
| Rapor oluşturulma zamanı | Önizleme hazırlanırken alınan sabit tarayıcı metadata'sı; cihaz verisini tazelemez. |

Eksik zaman **Bilinmiyor / sağlanmıyor** kalır. Aynı önizlemede rapor oluşturulma zamanı sabittir; varsa yaş gösterimi bu referansa bağlıdır. Yazdırma sırasında değişen sayaç veya yeni stale/SLA eşiği oluşturulmaz. Termivar Web'in sağlanan içe aktarma zamanı varsa tarama/rapor üretim zamanı gibi adlandırılmaz.

Token/Authorization, API adresi ve bağlantı ayarı, JWT claim'leri, credential/enrollment bilgileri, audit/aktör verisi, hata body'si, tarama hedefi, ham rapor/kanıt veya policy içeriği rapora girmez. Session/token nesnesi rapor oluşturucuya verilmez. HTML/JSON/CSV indirme, import/arşiv, otomatik dosya kaydı, e-posta, zamanlama veya paylaşım sunucusu yoktur.

Ürün anlamları değişmez: **Cihazın bildirdiği / Bağımsız doğrulanmadı**; veri yok/unknown/stale ayrıdır; eksik sayı sıfır değildir. İptal edilmiş cihaz kaydı HBF'nin kaldırıldığı/durduğu anlamına gelmez. Termivar Web özeti çalışır scanner/merkezî tarama kanıtı değildir. AV **Planlanan ürün — kullanıma hazır değil** kalır. Politika uygulandı/verified, korunuyor, güvenlik skoru, uyumluluk sertifikası veya hazırlanmış/onaylanmış imza sonucu üretilmez. Ayrıntılar [PRODUCT_STATES](PRODUCT_STATES.tr.md) içindedir.

## Yazdırma ve PDF

Önizlemede **Yazdır / PDF olarak kaydet** düğmesi tarayıcının yerleşik yazdırma akışını açar. PDF hedefini, dosya konumunu veya iptali kullanıcı tarayıcıda seçer. Uygulama otomatik dosya kaydetmez; `window.print()`/`afterprint` sonucundan **PDF başarıyla kaydedildi** veya baskı tamamlandı sonucu çıkarmaz. Bu ayrım [HTML yazdırma standardının](https://html.spec.whatwg.org/multipage/timers-and-user-prompts.html#printing) kullanıcıya bırakılan akışına dayanır.

Yalnız ayrı rapor kökü basılır; gezinme, bağlantı/token paneli ve düzenleme kontrolleri baskı kapsamı dışındadır. A4 dikey ve baskı stilleri `@media print`/`@page` ile düzenlenir; yaklaşım [MDN yazdırma rehberinde](https://developer.mozilla.org/en-US/docs/Web/CSS/Guides/Media_queries/Printing) açıklanır. Tarayıcının üstbilgi/altbilgi ve yazıcı seçenekleri uygulama garantisi değildir.

Örnek kipte başlık ve cihaz bölümlerindeki **ÖRNEK VERİ — GERÇEK CİHAZ RAPORU DEĞİLDİR** etiketi baskıda korunur. Ekran görüntüsü PDF dosyası veya baskı kabulü değildir. Bu tur yalnız yerel örnek rapor/önizleme incelenebilir; fiziksel yazıcıya iş gönderilmez. Gerçek build/elle gözlem ve varsa fiilen kaydedilmiş örnek PDF, [DELIVERY](DELIVERY.tr.md) kaydında ayrı belirtilir; kaydedilmemiş dosya üretilmiş gibi sunulmaz.

Üyelik geri çekildiğinde mevcut API 404 de döndürebilir. Bu nedenle kapsamlı cihaz/liste okumasında 404 geldiğinde taslak ve önizleme ihtiyatla temizlenir; bu yanıt tek başına nesnenin silindiği veya yetkinin kaldırıldığı sonucuna dönüştürülmez.

Bu teslimde HTML rapor önizlemesi ve dar ekranı gerçekten incelendi. Uygulama içi tarayıcının yerleşik yazdırma iletişim kutusuna erişilemedi; örnek PDF kaydedilmedi ve kağıt sayfaları doğrulanmadı. Standart tarayıcıda Yazdır düğmesiyle hedef seçimi kullanıcıya aittir.

## Türkçe/İngilizce sunum

Dil değişimi taslağın cihazlarını ve ad/kimlik tercihini korur; yalnız hazır önizlemeyi geçersizleştirir. Kullanıcı aynı taslaktan yeni dilde açıkça yeni önizleme oluşturur. Her önizlemenin locale'i ve oluşturma zamanı sabittir; kaynak/alım/okuma zamanları değişmez. Gizli adlar İngilizce görünümde **Selected organization / Device 01**, örnek etiketi **SAMPLE DATA — NOT A REPORT FROM REAL DEVICES** olur. Bu sunum değişikliği modele ID/context/token/generation geri eklemez. [Yerelleştirme ayrıntıları](LOCALIZATION.tr.md).

Önceki native printpreview erişim eksikliği ve PDF kaydedilmemesi geçerlidir. Bu dil turunda yazdırma düğmesi/native iletişim kutusu veya PDF üretimi denenmez; HTML önizleme gözlemi bu kabulün yerine geçmez.
