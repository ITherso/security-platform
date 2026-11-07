# Türkçe ve İngilizce arayüz

Üst çubuktaki **Dil / Language** seçimi Türkçe ve English arasında geçiş yapar. İlk açılış Türkçedir. Tarayıcı dili otomatik okunmaz; dış çeviri servisi, dinamik sözlük indirme veya analitik çağrısı yoktur. Seçim yalnız sayfa belleğindedir; cookie/localStorage/sessionStorage/IndexedDB veya URL'ye kaydedilmez. Sayfa yenilenince Türkçe başlangıç davranışı devam eder.

Dil değişimi yalnız sunumdur. Tenant, veri kipi, örnek senaryosu, mevcut ekran/cihaz, arama, filtre, sıralama, sayfalama ve rapor taslağı korunur. Token/bağlantı ömrü veya devam eden isteğin bağlamı değişmez. Fetch/reconnect/refresh/disconnect tetiklenmez; uygulama/veri sağlayıcısı locale anahtarıyla yeniden kurulmaz. Dil, tenant/token/source generation veya yetki değildir. Mevcut bağlam değişimi, 401/403/404 temizliği ve geç yanıt koruması aynen geçerlidir.

## Sözlüğe metin ekleme

Kaynaklar `src/i18n/` altındadır: `messages.tr.ts`, `messages.en.ts`, ortak `types.ts`, çeviri erişimi ve `formatters.ts`. Sözlük yapısı aynı anahtarları ve string/fonksiyon parametre şekillerini bağlar; İngilizce değerleri Türkçe literal metinlere eşit olmaya zorlamaz.

`catalogs/app.ts`, `catalogs/products.ts` ve `catalogs/reports.ts` ekran alanlarının TR/EN metinlerini tutar; iki `messages.*` dosyası bunları birleştirir. React bileşeni `useLocale()` üzerinden `locale`, `setLocale` ve tipli `t` alır. React dışı sunumda `translate(locale, key, ...args)` kullanılır; saklanan istemci mesajı `message(key, ...args)` ile kod/parametre olarak tutulup `renderMessage` ile seçilen dilde çizilir. Örneğin mevcut `t('app.inspect', deviceName)` çağrısında isim string parametredir; yanlış parametre türü sözlük sözleşmesine uymaz.

1. Kullanıcıya gösterilecek yeni metin için ortak sözlük yapısında bir anahtar belirleyin. Bir durum/route/filtre kimliği gerekiyorsa sabit iç kodu görünen etiketten ayrı tutun.
2. Aynı anahtarı iki sözlüğe ekleyin. Sayı veya isim içeren cümleyi kelime parçalarıyla birleştirmek yerine tipli parametre alan bir mesaj fonksiyonu kullanın; her dil cümleyi doğal kurabilsin.
3. Ortak `CatalogShape`/mesaj sözleşmesiyle `satisfies` uyumunu koruyun. Anahtar eksik/fazlalığı ve yanlış parametre çağrıları mevcut strict TypeScript denetiminde görünür olmalıdır. TR string literal türlerini EN değerlerine taşımayın. Dayanak: TypeScript'in [mapped types](https://www.typescriptlang.org/docs/handbook/2/mapped-types.html) ve [satisfies](https://www.typescriptlang.org/docs/handbook/release-notes/typescript-4-9.html#the-satisfies-operator) belgeleri.
4. Görünür metin, aria-label, tooltip/title, dialog ve istemci hata mesajını aynı dilden alın. Hata çevirisini kod/kategoriye bağlayın; Türkçe cümleyi parse etmeyin. Ham response/body/token çeviri parametresi değildir.

Yeni anahtar kontrol script'i veya test runner eklenmez. Bu tur testler bekletilir; `pnpm typecheck` ve production build sonucu [DELIVERY](DELIVERY.tr.md) içinde ayrı kaydedilir. Typecheck, bütün doğal dil çevirisinin veya erişilebilirliğin kabulü değildir.

## Çevrilmeyen veri

Tenant/device adı, hostname, kullanıcı/API içeriği ve örnek fixture adları veri olarak kalır. Audit olayının ham içeriği, kimlik, product ID, enum/hata kodu, API path/JSON alanı, sürüm/hash, timestamp ve sayısal değer değiştirilmez. Ürün markaları yeniden adlandırılmaz. Dil değişimi fixture/senaryo veya kullanıcı aramasını sıfırlamaz. Yetki/rol kararı, DTO/safe-integer doğrulaması ve token/generation/sequence davranışı çeviri katmanının dışındadır.

| Türkçe sunum | English presentation |
|---|---|
| Örnek veri — gerçek cihazlara bağlı değil | Sample data — not connected to real devices |
| Cihazın bildirdiği | Reported by the device |
| Bağımsız doğrulanmadı | Not independently verified |
| Bilinmiyor | Unknown |
| Veri yok | No data |
| Güncel değil | Stale |
| Cihaz kaydı iptal edildi | Device registration revoked |
| Planlanan ürün — kullanıma hazır değil | Planned product — unavailable |

`not_verified`, invalid/trusted/verified anlamına gelmez. Cihaz kaydının iptali firewall'ın kapatıldığı anlamına çevrilmez; credential iptalinden söz ediliyorsa özne credential olarak kalır. 404 bir dilde “bulunamadı/kapsam dışında”, diğerinde kesin “membership revoked” olamaz. Null/eksik, veri yok, hata ve gerçek sıfır ayrı kalır. Termivar özeti çalışır scanner/merkezî tarama kanıtı değildir; AV planned/unavailable etkin koruma olmaz.

## Tarih ve sayı politikası

Sayı/tarih sunumu TR'de **tr-TR**, EN'de **en-GB** kullanır. Her iki dilde zaman dilimi açıkça **UTC**'dir ve etiketlenir; tarayıcı veya dilden zaman dilimi çıkarılmaz. `Intl.DateTimeFormat` locale ve timeZone seçeneklerini ayrı ele alır; burada sunum değişir, temel an değişmez. [MDN DateTimeFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/DateTimeFormat), [NumberFormat](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/Intl/NumberFormat).

Formatlanmış metin domain modeline geri yazılmaz. Tarih sıralaması gerçek timestamp anahtarında kalır; yalnız dil değişti diye liste yeniden sıralanmaz. Teknik kimlik/sürüm/hash/sıra değerlerine grup ayıracı eklenmez. Eksik veya bozuk tarih şimdi/epoch'a çevrilmez. Kaynak/alım/okuma/oluşturma zamanları ayrı kalır; yeni göreli yaş sayacı veya SLA üretilmez. `document.documentElement.lang`, seçime göre `tr`/`en` olur.

## Rapor önizlemesi

Dil değişimi seçilmiş cihazları ve ad/kimlik gösterme tercihini korur; **yalnız hazır rapor önizlemesini geçersizleştirir**. Yeni dilde açıkça yeni önizleme oluşturulur. Önceki sabit önizleme sessizce çevrilmez ve eski guard üzerinden yazdırılabilir kalmaz.

Yeni `ReportModel` kendi sunum locale'ini sabitler. Kaynak veriler ve kaynak/alım/okuma zamanları değiştirilmez; yeni oluşturma zamanı yalnız açık önizleme eyleminde oluşur. Gizli kimliklerde **Seçili kurum / Cihaz 01** ve **Selected organization / Device 01** gibi etiketler kullanılır. Locale eklemek modele ID/context/token/generation geri sokmaz. 20 cihaz/256 KiB guard, açık alan listesi, deep copy/freeze ve bağlam temizliği korunur.

Örnek etiketinin İngilizcesi **SAMPLE DATA — NOT A REPORT FROM REAL DEVICES**'tır. İki dilde de kapsam, cihaz beyanı ve bağımsız doğrulanmadı açıklamaları korunur. Bu yerelleştirme turu native printpreview/PDF denemesi içermez: önceki yerleşik baskı önizlemesine erişilememe ve PDF kaydedilmeme bilgisi değişmez. Yeni build/örnek HTML gözlemi bu boşluğu kapatmaz.
