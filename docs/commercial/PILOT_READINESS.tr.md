# Ücretli pilot öncesi hazırlık ve açık kararlar

**Belge paketi hazırlanabilir; gerçek ücretli pilot için GO kararı yoktur.** Bu faz yeni müşteri, değerlendirme, sözleşme, tahsilat veya production faaliyeti başlatmaz. Teknik kaynak, sentetik format örneği ve hizmet süreci taslağı vardır; gerçek müşteri talebi, memnuniyet, ödeme isteği ve işletim kapasitesi `not_validated` kalır.

## 1. Teknik kapılar

| Kapı | Bugünkü kanıt/durum | Gerçek pilot öncesi kapanış kaydı |
|---|---|---|
| Build ve özellik kimliği | Pinli Termivar source `6a263934...`, `0.10.0-alpha.3`; source mevcut, pilot executable'ı `not_selected`. Yayımlanmış alpha.2 ve tarihsel örnek binary'leri farklıdır. | Tam source/build/version/hash, compile features ve seçili runtime yolunun kaydı; kabul edilmiş dağıtım kaynağı ve sahibi. Hash imza/source attestation sayılmaz. |
| Kaynak olgunluğu ve dar kullanım kabulü | Source experimental/not production-ready, bağımsız güvenlik audit'i yok. | Seçilen build, işletim ortamı, kapsam ve sınırların teknik/uzman incelemesi; açık risk ve destek kararı. Burada bağımsız audit yapılmış veya ürün production-ready olmuş sayılmaz. |
| Seçilen yolun kontrollü kabulü | Bu faz CLI, scanner, test, build veya native report verifier çalıştırmadı. Önceki benign fixture kayıtları tarihsel. | İleride kullanıcı tarafından ayrıca yetkilendirilen yerel/benign kabul: seçili komut, kapsam, bütçe/eksiklik/durdurma, çıktı ve teslim ilişkileri. Testler hâlen bekletiliyor; burada başlatılmaz. |
| API/ek feature sınırı | GraphQL/OpenAPI/REST ve diğer review yolları derleme/opt-in/policy sınırlarına bağlı. | İlk pilotta kullanılacak dar yol ve yöntem açık seçilir. Seçilmemiş/uygun olmayan uzantı dahil edilmez; bütün API, rol veya zafiyet kapsamı iddiası yoktur. |
| Kanıt ve tamamlanma yorumu | Native Informational/NeedsReview; temel web-review Confirmed üretmez. Incomplete/failed, clean sonuç değildir. | Uzmanın evidence/source erişimi, inceleme yöntemi ve unavailable/skipped alanların raporda gösterimi; etiketlerin doğrulama kararından ayrılması. |
| Rapor/manifest/karşılaştırma | Native sözleşmeler mevcut; örnek JSON+manifest kısmi, HTML yok. Ayrı comparison ana raporun retest'i değil. | Gerçek çalışmada teslim edilen byte kimlikleri; hangi doğrulamanın yapıldığı ve yapılmadığı. Uygun iki complete kaynak yoksa comparison üretilmemesinin gerekçesi. |

Kaynak dayanakları: [README16–20](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/README.md#L16-L20), [native item sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/FEATURES.md#L29-L31), [build feature listesi](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/Cargo.toml#L57-L101), [ayrıntılı iddia matrisi](CAPABILITY_CLAIMS.tr.md).

## 2. İşletim kapıları

| Kapı | Açık karar / ölçüm | Mevcut durum |
|---|---|---|
| Kapsam/yetki sahibi | Hedefin yetki kaydı, hariçler, izinli faaliyet ve penceresi, müşteri teknik irtibatı | `not_established` |
| Operatör ve uzman kapasitesi | İşi yürüten, kanıt inceleyen, raporu kontrol eden, durdurma/kapanış kararını veren roller ve müsaitlik | `not_assigned`; hazır kadro/kapasite varsayılmaz |
| Durdurma/olay yönetimi | Hedefi izleme, durdurma kanalı, beklenmeyen etki/veri durumunda temas ve yeniden başlatma kararı | `not_accepted`; uygulanmış olay müdahale servisi değil |
| Veri işleme | Erişim, asgari veri/redaksiyon, aktarım ortamı, saklama süresi/yeri, silme/yedek ve olay sorumluları | `open`; şifreleme/anonimlik veya otomatik silme garantisi yok |
| Rapor ve takip | İnceleme alanları, müşteri açıklaması, takip işi ve ayrı yetkili yeniden değerlendirme sınırı | Standardı taslakta mevcut; gerçek müşteriyle `not_validated` |
| Efor/destek kapasitesi | Hazırlık, yürütme, inceleme, rapor, destek ve revizyonların gerçek zaman/iş yükü kaydı | `not_measured`; otomatik analytics sistemi eklenmedi |
| Talep ve değer | Teknik ekibin raporu kullanabilmesi, destek ihtiyacı, memnuniyet ve ödeme isteği | `not_validated`; görüşme veya satış yapılmadı |

İlk bağımsız Termivar Web hizmeti için bunlar somut hazırlık gereksinimleridir. [Kapsam taslağı](PILOT_SCOPE.tr.md) doldurulmadan gerçek hedef seçilmiş sayılmaz. İnsan incelemesi native JSON'u değiştirerek source disposition'ını yükseltmez; ayrı not ve gerekçeyle tutulur.

## 3. Hukuki ve kurumsal kararlar

Bu bölüm bir hukuk yorumu, düzenleyici uygunluk kararı veya bağlayıcı sözleşme değildir. Aşağıdaki konuların uygun taraflarca kararlaştırılmış olduğu varsayılmaz:

- Hedef sahibinin yetkisi, üçüncü taraf/provider kullanım sınırları ve faaliyetleri kapsayan yazılı iş/kapsam kararı.
- Müşteri/sağlayıcı rollerinin, veri erişimi ve işleme amacının, aktarım/saklama/silme kararlarının ve gerekiyorsa kurumsal/hukuki incelemesinin belirlenmesi.
- Dağıtılacak binary/rapor/fixture ve bağımlılıkların hak/lisans/atıf koşullarının seçilen dağıtım modeli için incelenmesi. Termivar [MIT metadata ve LICENSE](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/LICENSE) mevcut; bu faz dependency lisans clearance, SBOM veya hukuk incelemesi tamamlamadı. Kopyalanan notice hakları yeniden tanımlamaz.
- Hizmet kapsamı, destek sınırı, sorumluluk, gizlilik ve kabul/kapanış metinlerinin uygun karar sahiplerince incelenmesi. Kesin müşteri sözleşmesi, SLA, sertifika veya yeni garanti hazırlanmadı.
- İleride ücret alınacaksa ticari taraf/teklif/onay ve ödeme/faturalama süreçlerinin kurumsal kararı. Bu çalışma şirket, ödeme altyapısı, lisans anahtarı veya faturalama kodu oluşturmaz; fiyat/ciro tahmini içermez.

Bu açık kararlar yeni yasal zorunluluk listesi değildir. Kimin hangi kararı vereceği atanmadıysa açık kalır; taslak hazırlanması kabul anlamına gelmez.

## 4. Pilot başarısı nasıl ölçülecek?

Aşağıdaki ölçütler önerilen pilot kayıt yöntemidir; bu fazın ölçülmüş sonuçları değildir. Kriterleri kabul edecek taraflar ve hedef değerleri pilot öncesi belirler. Gözlem sayısı güvenlik/başarı puanına dönüştürülmez.

| Soru | Kaydedilecek somut çıktı / payda | Bu fazın sonucu |
|---|---|---|
| Kapsam anlaşılır mı? | Kabul edilmiş tüm hedef/hariç/faaliyet maddelerine raporda karşılık; açıklığa kavuşmayan maddelerin açık listesi | Gerçek kapsam/kullanıcı kabulü `not_validated` |
| Sonuç hangi kanıta dayanıyor? | Teslim edilen her öğede kaynak dosya/hash ve evidence referansı; ham kanıta erişilmiş/erişilmemiş durumu. Referansı açıklanamayan öğelerin ayrı listesi | Sentetik format örneği var; gerçek kanıt incelemesi `not_performed` |
| İnceleme ihtiyacı ayrılıyor mu? | Tüm kaynak disposition'ları ile ayrı insan review_status/gerekçe; bekleyen uzman kararlarının sayısı ve listesi | Gerçek uzman kabulü `not_validated` |
| Eksikler görünür mü? | Her incomplete/skipped/unsupported/unavailable veya kapsam dışı iş için sebep, etkisi ve takip kaydı; “0 bulgu”ya çevrilmemesi | Örnek incomplete açıklaması var; gerçek çalışma `not_performed` |
| Rapor teknik ekipçe kullanılabilir mi? | Teknik okuyucunun kaynak/kanıt/sınırlama/takip maddesini bulup anlamasına ilişkin kabul notu ve açıklama soruları | Müşteri kullanılabilirliği `not_validated` |
| Değişim izlenebilir mi? | Uygun iki complete kaynak varsa exact byte hash bağları, kapsam beyanı ve dört grup; yoksa neden karşılaştırılamadığı | Bağımsız sentetik comparison var; gerçek retest `not_performed` |
| Uzman ve destek emeği ölçülebiliyor mu? | Çalışma bazında gerçek dakika/saat kayıtları, destek soru/adet/konuları, yeniden işleme ve rapor revizyonları; eksik kaydın da belirtilmesi | Hizmet eforu ve kapasite `not_measured` |
| Müşteri değeri ve ödeme isteği var mı? | İleride açıkça yetkilendirilen görüşme/geri bildirim ve ticari karar kaydı | Memnuniyet, talep ve ödeme isteği `not_validated` |

Hiçbir süre, doğruluk, maliyet veya verim artışı yüzdesi ölçülmeden yazılmaz. Teknik request bütçesinin içinde bitmek bütün kontrollerin tamamlandığını; fazla kayıt daha iyi güvenliği göstermez. Teknik ekibin raporu kabul etmesi de bütün bulguların doğrulandığı veya hedefin güvenli olduğu anlamına gelmez.

Önerilen pilot kapanışı: kabul edilen kapsam ve teslim standardına göre gerçek dosya/inceleme/eksiklik/efor kayıtları tamamlanır; açık takip işleri ve sorumluları gösterilir; müşterinin teslim/kapanış kararı ayrı kaydedilir. Kapanışta açık bir madde kalıyorsa o madde “düzeltildi/verified” yapılmaz. Yeniden değerlendirme ayrı kapsam ve yetki ister.

## 5. İlk pilotu bekletmeyen ayrı ekosistem kapıları

| Alan | Korunan durum | Bu bağımsız Termivar Web pilotuna etkisi |
|---|---|---|
| Termivar Platform production API/IdP/PG | Gerçek kurumsal kabul bekliyor | Yerel CLI + dosya + insan incelemesi hizmetinin otomatik önkoşulu değil. Entegrasyon istenirse Enterprise Future için ayrı kapı. |
| HostBasedFirewall Windows/native yaşam döngüsü | 12 gerçek vaka NOT_RUN; ayrı endpoint ürünü | Temel Termivar Web assessment'ın önkoşulu değil; kabulü tamamlanmış gibi tanıtılmaz. |
| HBF policy revision/lineage ve sorumlusu | Kararlaştırılmadı / not_established | Burada yeniden sorulmaz veya seçilmez. Offline Policy Impact Workbench uygulama yetkisi kazanmaz. |
| Antivirus | Planned/unavailable, motor yok | İlk teklife çalışan ürün olarak dahil edilmez. |

Bu ayrım platform `aa643d40797998d5f615cb5ba5b71b972596abc9` [yetenek/açık kapılar matrisine](../../operator-console/docs/CAPABILITY_MATRIX.tr.md) ve [statik ürün kataloğuna](../../operator-console/src/features/productHub/productCatalog.ts) dayanır. Bütün ekosistemin hazır olması ilk ürünün şartı yapılmaz. Termivar Web ve hizmet sürecinin yukarıdaki kendi kapıları ise açık kalır.

## 6. Bu fazın gerçek teslim durumu

Ürün tanımı, müşteri hipotezi, kapsam/teslim standardı, kaynak iddia matrisi, üç seviye ve mevcut artefact'lardan sentetik örnek hazırlandı. Kaynak ve byte/SHA256 koruma kayıtları yeni manifestte verilir. Bunlar doküman/artefact incelemesidir; otomatik test, CLI, canlı assessment, production kabulü veya ticari doğrulama değildir.

**GO/NO-GO sahibi ve pilot başlangıcı bu fazda belirlenmedi; GO yok.** Satış, müşteri iletişimi, test/runner/coverage, gerçek domain değerlendirme, Windows/VM/IdP/PG, yönetici işlemi, public deploy, GitHub push/release veya ödeme faaliyeti başlatılmadı. Bu belge paketi teslim edildikten sonra burada durulur.
