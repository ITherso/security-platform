# Termivar Offline Handoff Builder

Bu bağımsız, Python standart kütüphanesiyle yazılan araç `termivar-handoff-draft/v1` demo girdisinden iç inceleme özeti ile sınırlı Markdown/statik HTML müşteri **taslakları** hazırlar. Native Termivar CLI/scanner çalıştırmaz; yeni assessment, comparison veya güvenlik kararı üretmez. Platform backend/frontend başlangıcına, production wheel'e veya operator-console'a eklenmez.

`mode` yalnız `demo` olabilir. Gerçek müşteri modu, ortam değişkeniyle açılan production yolu veya `--force` yoktur. Şema biçimini doğrulamak gerçek inceleyiciyi, kararın doğruluğunu veya teknik bulguyu doğrulamaz.

## Kullanım

Çalışma dizini, `security-platform/` ve `outputs/` dizinlerini içeren **workspace kökü** olmalıdır. Kod Python 3.10+ sözdizimi kullanır; bu teslimatta yalnız Python **3.14.7** ile çalıştırılmıştır, diğer sürümlerin kabulü yapılmamıştır. Yalnız yeni offline builder için örnek komut:

```text
python -I -B security-platform/tools/commercial_handoff/assemble.py --input security-platform/tools/commercial_handoff/examples/demo_input.json --output-dir outputs/phase16-demo
```

Girdi/çıktı yolları açıkça verilir, çalışma dizinine göredir; mutlak/drive/UNC yol, `..` ve ADS reddedilir. Çıktı üst dizini mevcut olmalı, çıktı dizininin kendisi önceden bulunmamalıdır; mevcut boş dizin de yeniden kullanılmaz. Aynı komutu aynı çıktı yolunda tekrar çalıştırmak overwrite veya temizleme izni değildir. Yeniden üretim için ayrı, yeni bir çıktı yolu seçilmelidir. Girişteki metinler, path/URL benzeri değerler ve provenance referansları başka dosya açma veya ağ erişimi için kullanılmaz.

Bu komut native Termivar CLI, tarama veya test komutu değildir. Örneğin gerçekten çalıştırılıp çalıştırılmadığı ve dosya kimlikleri [demo teslim notlarında](../../docs/commercial/operations/phase16/DEMO_DELIVERY_NOTES.md) ayrı kaydedilir; burada bir çalıştırma sonucu varsayılmaz.

## Girdi ve çıktı

Girdi en fazla 256 KiB, BOM'suz strict UTF-8 JSON'dur. Sürüm, bilinmeyen/eksik alanlar, duplicate key, tür ve sınırlar kapalıdır. Detaylar [INPUT_CONTRACT](../../docs/commercial/operations/phase16/INPUT_CONTRACT.tr.md) ve yetkili [schema.py](schema.py) içindedir. Araç Phase15 Markdown defterlerini parse etmez veya değiştirmez; kaynak JSON'ları otomatik içe almaz. [Demo girdisi](examples/demo_input.json), dört kaynak kimliği ve insan durumlarının ayrı, elle hazırlanmış aktarımıdır.

Sabit çıktı adları:

| Dosya | İçerik ve sınır |
| --- | --- |
| `internal-review-summary.md` | Bütün geçerli observation'lar, kaynak/insan durumları, eksik kanıt, engeller ve müşteri çıktısına alınmama nedenleri. Müşteriye yönelik değildir |
| `client-handoff-draft.md` | Yalnız müşteri modelinin izinli alanları; uygun review ve ayrı inclusion kararının ikisi birden gereklidir |
| `client-handoff-draft.html` | Aynı sınırlı müşteri modelinin statik, dinamik metinleri escape edilmiş sunumu; script veya dış kaynak yok |
| `manifest.json` | Giriş byte SHA256'sı, üç çıktı dosyasının gerçek boyut/hash'leri, sabit demo/yetki sınırları ve açık engeller; imza veya sertifika değildir |

Müşteri taslaklarında görünür sabit etiket: **DEMONSTRATION ONLY — NOT APPROVED FOR CLIENT DELIVERY**. `release_authorized=false`, `human_review_verified=false` ve `demo_only=true` taslak niteliğini korur. Manifest kendi hash'ini kendi içine ekleyen bir güven zinciri değildir.

Mevcut demo dört `unreviewed` / `unknown` / `pending_decision` kayıt içerir. `safe_summary=null`, `decision_ref=null`, `review_decisions=[]`; bu nedenle müşteri bulgusu seçilmesi beklenmez. Bunun anlamı güvenlik açığı bulunmadığı veya temiz assessment değildir.

## Güven ve hata sınırı

Metin escape edilmesi otomatik redaksiyon, secret taraması veya paylaşım onayı değildir. İnsan tarafından sağlanan kapsam ve güvenli özet alanları dahi ayrı veri/iddia incelemesi gerektirir. Kimlik, hash ve tarih biçimi denetimi insanı veya incelemeyi kanıtlamaz.

Yazım yalnız exclusive oluşturulan yeni dizin ve sabit dosya adları içindir. Aynı üst dizinde araca ait geçici staging, no-overwrite hardlink yayımı ve en son yazılan manifest kısmi çıktıyı başarı saymamak için kullanılır. Hata halinde başarı iddiası yapılmaz; kısmi dosyalar kalabilir, kullanıcı dosyaları üzerine yazılmaz veya silinmez. Bu yöntem bütün dizinin tek atomik işlemle yayımlandığı anlamına gelmez. Yol/symlink/reparse kontrolleri, filesystem yarışlarının, hardlink desteğinin veya bütün OS erişim haklarının kabul edildiği anlamına gelmez. Çalıştırılmayan hata/yarış senaryoları `not_run` kalır.

[Araç işleyişi](../../docs/commercial/operations/phase16/HANDOFF_BUILDER.tr.md), [güvenlik sınırı](../../docs/commercial/operations/phase16/SECURITY_BOUNDARY.tr.md) ve [Phase15 operasyon kiti](../../docs/commercial/operations/README.tr.md) birlikte okunmalıdır. Bu araç gerçek değerlendirme, müşteri teması, teslim, pilot veya yeni faz başlatmaz.
