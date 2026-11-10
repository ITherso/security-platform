# Termivar değerlendirme teslim ve uzman inceleme kiti — Phase15

Bu kit, mevcut Termivar çıktısından elle tutulan inceleme kaydına ve müşteri teslim taslağına giden yolu tanımlar. Yeni değerlendirme çalıştırmaz. Gerçek kapsam/yetki, uzman incelemesi, veri kararı veya teslim kabulü bu dosyalar doldurularak oluşmaz.

## Kullanım sırası

1. [İş akışını](ASSESSMENT_WORKFLOW.tr.md) okuyup [vaka kaydını](templates/CASE_RECORD.template.md) ayrı çalışma kopyasında doldurun. Kaynak dosyaları ve byte kimliklerini birbirinden bağımsız kaydedin.
2. Her kaynak gözlemi [inceleme defterine](templates/OBSERVATION_LEDGER.template.md) bağlayın; kaynak fingerprint ve JSON pointer'ı koruyun. [İnceleme politikası](OBSERVATION_REVIEW_POLICY.tr.md) kaynak iddiası ile insan kararını ayırır.
3. Gerçekten yapılan inceleme için [karar kaydını](templates/REVIEW_DECISION.template.md) gerekçe/kanıt/sınırlama ile tutun. Yapılmayan incelemenin durumu `unreviewed` kalır.
4. [Veri rehberi](DATA_HANDLING.tr.md) ve [manuel teslim kapısını](DELIVERY_GATE.tr.md), [kontrol listesi](templates/DELIVERY_CHECKLIST.template.md) üzerinden değerlendirin. Dış kanıt gerektiren eksikler açık kalır.
5. Yalnız paylaşımına karar verilen içerikle [TR](templates/CLIENT_HANDOFF.template.tr.md) veya [EN](templates/CLIENT_HANDOFF.template.en.md) müşteri taslağını hazırlayın. Gerçek teslim/kabul için ayrı kanıt gerekir.

İç kayıt ve müşteri çıktısı ayrı dosyalardır. Birbirlerine kimlikle bağlanmaları, ham kanıtın veya iç karar notunun otomatik kopyalanması anlamına gelmez. Bu Markdown düzeni erişim kontrolü veya güvenli dosya kasası sağlamaz.

## Tamamlanmış sentetik dosya örneği

[Demo vaka indeksi](examples/DEMO_CASE_INDEX.md), dört gözlemi [defter](examples/DEMO_OBSERVATION_LEDGER.md) ve [karar kayıtlarına](examples/DEMO_REVIEW_DECISIONS.md) bağlar; [demo teslim kapısı](examples/DEMO_DELIVERY_GATE.md) gerçek teslimi açık bırakır. [Örnek müşteri taslağı](examples/DEMO_CLIENT_HANDOFF.md) iç defterin tamamını taşımaz.

**Demonstration only — No real system assessed.** Örnek dosyalar, belgeleri doldurma gösterimi olarak tamamlanmıştır. Uzman incelemesi, müşteri kabulü veya gerçek pilot tamamlanmış değildir. Kullanılan JSON'lar korunmuş [Phase14 örnek dizinindedir](../examples/README.tr.md); bu fazda yeniden üretilmez ve yeni belge ZIP'ine kopyalanmaz.

## Phase14 ile bağlantı ve açık sözlük farkı

| Korunan Phase14 belgesi | Bu kitteki somut kullanım |
| --- | --- |
| [PRODUCT_OFFERING](../PRODUCT_OFFERING.tr.md) | Vaka amacı ve beklenen teslimat, tanımlı hizmet sınırına bağlanır. Ürün teklifi yeniden yazılmaz. |
| [PILOT_SCOPE](../PILOT_SCOPE.tr.md) | İş akışı A: yetki, hedef/hariçler, bütçe, roller ve durdurma kaydı. |
| [DELIVERABLE_SPEC](../DELIVERABLE_SPEC.tr.md) | Müşteri handoff'unun kapsam, yöntem, sonuç, eksik iş, kanıt ve takip bölümleri. |
| [CAPABILITY_CLAIMS](../CAPABILITY_CLAIMS.tr.md) | Defter/karardaki teknik iddia için kaynak desteği ve native sınıf sınırı. |
| [PILOT_READINESS](../PILOT_READINESS.tr.md) | Gerçek pilot için teknik/işletim/veri/kurumsal açık kararlar teslim kapısında korunur. |

Phase14 teslim standardı insan incelemesi için `not_performed / needs_additional_evidence / reviewed` önerir. Phase15 talimatı bu kitte `unreviewed / needs_manual_review / informational_only / inconclusive / excluded_with_reason / reviewed_for_delivery` sözlüğünü ister. **Bu, yeni insan belgesi sözlüğüdür; Termivar şema değişikliği veya otomatik durum dönüşümü değildir.** Eski kayıt, sözlüğü ve gerçek inceleme kanıtı ile korunur; yeni karar gerekiyorsa eski kayda bağlanan ayrı gerekçeli kayıt açılır. Demo için inceleme yapılmadığından `unreviewed` kullanılır. `reviewed_for_delivery` bağımsız zafiyet doğrulaması veya teslim izni değildir.

## Kaynak ve koruma kaydı

Başlangıç belge commit'i `1517364dabe779b19c84f02c5f62beea19c164db`; teknik platform `aa643d40797998d5f615cb5ba5b71b972596abc9`, Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3`, HBF `74a88ed336cb8a0a2fab16e20389c9410590c292`. Kaynakta mevcut olmak gerçek pilot kabulü değildir. Teknik dayanaklar [inceleme politikası](OBSERVATION_REVIEW_POLICY.tr.md) ve korunmuş Phase14 kaynak kayıtlarına bağlıdır.

Yalnız bu operations dizini ve üst README bağlantısı eklenir. Yeni dokümanların değişen dosya/byte/SHA256 ve koruma listesi, dış `phase15-operations-source-manifest.json` kaydında verilir. Belge paketinin içindeki `source-manifest.json` aynı kaydı taşır; kendi hash'i dış teslim manifestinde bulunur. Paket yalnız yeni operations belgelerini içerir; Phase14 JSON'larına ve üst teknik kaynaklara giden bağlantılar önceki checkout/teslimatı gerektirir. Dosya hash'i imza veya üretici kimliği değildir.

Gerçek yetki, saklama politikası, müşteri kabulü ve bağımsız doğrulama kapıları açık kalır. Bu tur test/build/CLI/scanner, gerçek hedef, müşteri iletişimi veya yayın başlatılmaz; kit tamamlandığında yeni faz kendiliğinden açılmaz.
