# Demo manuel teslim kapısı

**Demonstration only — No real system assessed.**

| Alan | Demo kaydı |
| --- | --- |
| `case_id` | `DEMO-TERMIVAR-015` — dahili demo dosya kimliği |
| `demo_only` | `true` |
| Genel kapı durumu | `blocked` — gerçek müşteri teslimi, pilot, satış veya production için GO yok |
| Mevcut handoff | [Paylaşılmamış demo taslağı](DEMO_CLIENT_HANDOFF.md) |
| Teslim sahibi / karar veren / karar zamanı | `not_provided` / `not_provided` / `not_provided` |

Matris durumları yalnız `ready_for_manual_review`, `blocked`, `pending_decision`, `not_applicable` değerleridir. `ready_for_manual_review`, belgedeki bilginin insan tarafından ele alınmaya hazır olduğunu belirtir; kontrolün geçtiği, uzman incelemesi veya teslim onayı değildir. `demo_only=true` genel blokajı kaldırmaz. Bu dosya [manuel kapı politikasının](../DELIVERY_GATE.tr.md) demo uygulamasıdır; otomatik karar motoru değildir.

## On iki kontrol alanı

| No | Kontrol | Durum | Mevcut kayıt ve açık kalan koşul |
| ---: | --- | --- | --- |
| 1 | Değerlendirme kapsamı ve yetkisi | `blocked` | Müşteri, gerçek hedef, yetki kaydı, faaliyet/pencere ve hariçler `not_provided`; dört A1 öğesinin scope_status değeri `unknown`. Kaynak profil, subject veya fingerprint yetki değildir |
| 2 | Kaynak artefact provenance | `ready_for_manual_review` | [Case index](DEMO_CASE_INDEX.md) altı mevcut dosyanın byte/SHA256 ve A/C/D provenance ayrımını kaydeder. Üretici kimliği veya özgünlük `not_verified`; yeni çalıştırma yok |
| 3 | Assessment completion / eksiklik | `ready_for_manual_review` | A1 kaynak `complete`, 1 subject/4 informational item; C2/C3 ayrı complete girdiler; D1 authored `incomplete` ve item projection unavailable. Complete güvenlik/kapsam garantisi, D1 sıfır bulgu değildir |
| 4 | Uzman inceleme kayıtları | `blocked` | [Ledger](DEMO_OBSERVATION_LEDGER.md) dört gerçek source referansını içerir; dört kayıt `unreviewed`. İnceleyen/zaman/karar yok; metadata kontrolü uzman incelemesi değildir |
| 5 | Müşteriye sunulacak iddiaların kaynak desteği | `blocked` | [Karar kayıtlarında](DEMO_REVIEW_DECISIONS.md) dört client_inclusion değeri `pending_decision`; dahil/hariç kararı verilmedi. Handoff'ta onaylanmış bulgu yok; kaynak gözlem doğrulanmış zafiyet yapılmadı |
| 6 | Hassas veri minimizasyonu | `pending_decision` | Handoff iç not, rol ataması, opaque evidence listesi, target/HTTP/credential içeriği aktarmaz. Gerçek veri sınıflandırma, paylaşılabilir alan/redaksiyon ve alıcı kararı henüz yok; alan adının “redacted” olması güvenli paylaşım kanıtı değildir |
| 7 | Manifest / bütünlüğün doğru anlatımı | `ready_for_manual_review` | A2'nin yalnız A1 JSON-entry uzunluk/hash/özet eşleşmesi kaydedildi. HTML yok; native verifier çalıştırılmadı. Tam bundle doğrulaması veya üretici kimliği doğrulaması iddiası yapılamaz |
| 8 | Karşılaştırma sınırları | `ready_for_manual_review` | C1, C2/C3 digestlerine bağlı ayrı sentetik karşılaştırmadır; A1 retest'i değildir. Dört grup kaynakta 1'er kayıt; only_in_before düzeltme, changed risk kararı, unchanged eşit güvenlik değildir |
| 9 | Veri saklama / erişim kararları | `pending_decision` | Karar sahibi, ortam/alıcı, erişim, aktarım, süre, yedek/silme ve olay kararları belirlenmedi. Süre veya hukuki dayanak uydurulmadı |
| 10 | Teslim sahibinin belirlenmesi | `blocked` | Gerçek teslim sahibi, inceleme/kalite kontrol ve kabul rolleri `not_provided`; demo belgeyi hazırlama gerçek rol ataması değildir |
| 11 | Gerçek müşteri kabul süreci | `pending_decision` | Alıcı, teslim kanalı, kabul ölçütü, teslim/kabul zamanı ve onay kanıtı `not_provided`. Demo paylaşılmadı; teslim/kabul/memnuniyet varsayılmadı |
| 12 | Gerekli teknik / kurumsal onaylar | `blocked` | Seçilen build/özellik/yolun kabulü, uzman kapasitesi, yetki, veri ve kurumsal/hukuki kararlar açık. [Phase14 pilot hazırlığı](../../PILOT_READINESS.tr.md) değişmedi; bekletilen test/Windows/IdP/revision faaliyetleri başlatılmaz |

## Somut durdurma kaydı

Bu örnek müşteri dosyasına çevrilmez veya gerçek hedefe uygulanmaz. En az kapsam/yetki ve uzman incelemesi eksikliği gerçek teslimi durdurur. Manifestin eksik HTML'iyle tam bundle başarısı iddiası ayrıca kullanılamaz. C kümesinden A1 için düzeltme veya retest sonucu türetilemez; D1 için temiz sonuç türetilemez. Bekleyen veri/rol/kurumsal kararlar belge doldurarak kapanmaz.

HBF Windows, platform IdP ve gerçek policy revision otoritesi ayrı ürün/entegrasyon kapılarıdır. Bunlar bağımsız Termivar hizmetinin otomatik önkoşulu yapılmaz veya yeniden karara açılmaz; bu örneği durduran Termivar kapsamı, insan incelemesi ve işletim kararlarının kendi eksikleridir.

İleride uygun karar sahipleri gerçek kayıt ve mevcut kanıtı değerlendirirse durum değişikliği gerekçesi, dayanağı, gerçek sorumlusu ve zamanı ayrıca kaydedilmelidir; mevcut demo kaydı yapılmamış incelemeye geriye dönük kanıt yapılamaz. Bu bir yeni test, yeniden assessment, müşteri teması veya yeni faz başlatma talimatı değildir.

## İç kayıt ve müşteri taslağı ayrımı

İç kayıtlar [case index](DEMO_CASE_INDEX.md), [ledger](DEMO_OBSERVATION_LEDGER.md) ve [bekleyen kararlar](DEMO_REVIEW_DECISIONS.md) üzerinden izlenir. [Client Handoff](DEMO_CLIENT_HANDOFF.md) yalnız kaynak türleri, tamamlanma/eksiklik ve yorum sınırlarını örnekler; review gerekçelerini, kişisel rol atamalarını veya ham kanıtı kopyalamaz. Paylaşım onayı, güvenli aktarım, erişim kontrolü veya saklama politikasının uygulanmış olduğu söylenmez. Bu matrisin okunması yazılım testi, native kabul veya gerçek pilot kabulü değildir.
