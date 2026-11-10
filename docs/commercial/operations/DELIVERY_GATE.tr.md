# Manuel teslim kararı matrisi

Bu matris [iş akışındaki](ASSESSMENT_WORKFLOW.tr.md) müşteri paketi hazırlığını kayıt altına alır. **Otomatik kontrol, gerçek değerlendirme/teslim izni veya satış/pilot/üretim için GO değildir.** Phase14 [PILOT_SCOPE](../PILOT_SCOPE.tr.md), [DELIVERABLE_SPEC](../DELIVERABLE_SPEC.tr.md) ve [PILOT_READINESS](../PILOT_READINESS.tr.md) açık kapıları korunur; ürün tanımı yeniden yapılmaz.

## Durum sözlüğü ve kayıt biçimi

Her kapının `status` alanı yalnız şu dört değerden biridir:

| Değer | Anlam |
|---|---|
| `ready_for_manual_review` | Belirtilen belge/kanıt, belirtilen dar konu için yetkili insanın incelemesine hazırlanmış. İnceleme tamamlandı, onaylandı, teslim edilebilir veya GO anlamına gelmez. |
| `blocked` | Eksik/çelişkili kanıt veya ihlal nedeniyle bu konu ilerletilemez. Neden, gerekli dış kanıt ve takip yazılır. |
| `pending_decision` | Gerekli gerçek sahip/kurumsal karar veya kabul henüz verilmemiş. Doldurulmuş dosya bunu kapatmaz. |
| `not_applicable` | Vakanın kabul edilmiş dar kapsamına uygulanmadığı kanıt/gerekçeyle gösterilmiş. Zorunlu ama eksik bir yetki/karar bu değere çevrilemez. |

`demo_only` ayrı bir marker'dır; `status` değeri değildir. Bir vaka kaydı `case_id`, `demo_only`, kapı ID'si, `status`, kaynak/karar referansları, gerçek yapılan kontrolün kapsamı, doğrulanmamış alanlar, gerekçe, gerekli takip, sorumlu rol ve varsa gerçek karar sahibi/zamanını taşır. Atanmamış kişi/zaman `not_provided`, verilmemiş karar `pending_decision` kalır. Kanıt olmayan bir rol adı veya dosya hazırlama tarihi onay sahibinin imzası yerine kullanılamaz.

## On iki kapı

Aşağıdaki başlangıç durumları gerçek vaka doldurulmadan değiştirilmez. Bunlar bu fazda verilmiş müşteri kararları değildir. İstenen kanıt sağlansa bile sonuç en fazla o dar inceleme için `ready_for_manual_review` olur; yetkilendirme ve teslim kararı ayrı dış süreçtir.

| ID / kontrol alanı | Manuel incelemeye hazırlanacak kayıt | Bekletme/durdurma nedeni | Başlangıç `status` / karar rolü |
|---|---|---|---|
| G01 — Kapsam ve yetki | Tam hedef/faaliyet/hariç/pencere, yetkilendirenin yetki bağı ve mevcut yetki ref'i; bütçe. | Yetki/target sınırı yok veya çelişkiliyse gerçek faaliyet/teslim için ilerlenmez. Origin adı yetki değildir. [PILOT_SCOPE §1–4](../PILOT_SCOPE.tr.md#1-kapsam-nasıl-bağlanır) | `blocked`; yetki/kapsam sahibi `not_provided` |
| G02 — Kaynak artefact provenance | Kayıtlı dosya/contract/source commit veya mevcut provenance, mevcut byte/hash kimliği, eksik/sağlanmayan dosyalar. | Dosyalar yanlış bağlanmış, kaynak belirsiz veya mevcut olmayan verification sonucu yazılmışsa `blocked`. Hash/parse producer doğrulamaz. [DELIVERABLE_SPEC §5](../DELIVERABLE_SPEC.tr.md#5-dosyalar-ve-bütünlük) | `pending_decision`; artefact kayıt sorumlusu `not_provided` |
| G03 — Tamamlanma ve eksiklik | Complete assessment ile ayrı incomplete/failed diagnostic, unavailable/skipped/unsupported işler ve etkileri. | Eksik çalışma temiz/0 bulgu yapılmış veya ayrı fixture tek koşu gibi anlatılmışsa `blocked`. Eksik çalışma varsa yalnız sınırları açık eksiklik tesliminin uygunluğu incelenebilir. [DELIVERABLE_SPEC §4](../DELIVERABLE_SPEC.tr.md#4-tamamlanma-ve-kapsam-eksikleri) | `pending_decision`; teknik inceleme rolü `not_provided` |
| G04 — Uzman inceleme kayıtları | Her kaynak gözlemi için ledger, altılı review durumu, mevcut kanıt/sınırlama, gerçek reviewer/tarih varsa kaydı; decision ref'leri. | Kaynak informational diye otomatik onay veya yapılmamış uzman incelemesi varsa `blocked`. Dört demo kayıt `unreviewed` kalır. [İnceleme politikası](OBSERVATION_REVIEW_POLICY.tr.md) | `blocked`; uzman inceleyen `not_provided` |
| G05 — Müşteri iddialarının desteği | Handoff'taki her sınırlı anlatım → gözlem/artefact → kanıt/sınırlama → gerekçeli karar kimliği. | Zafiyet/güvenlik/remediation veya doğruluk iddiası dayanağı aşarsa `blocked`. `reviewed_for_delivery` doğrulama değildir. [DELIVERABLE_SPEC §2–3](../DELIVERABLE_SPEC.tr.md#2-durumlar-ve-iddia-sınırı) | `blocked`; rapor inceleme rolü `not_provided` |
| G06 — Hassas veri minimizasyonu | Sekiz sınıfın paylaşım kararı, asgari içerik/redaksiyon gerekçesi, türetilmiş çıktı ref'i; iç/dış kayıt ayrımı. | Ham credential/token/cookie, gereksiz ham HTTP/iç not veya incelenmemiş hassas içerik kalmışsa `blocked`. Redacted alan adı yeterli değildir. [DATA_HANDLING](DATA_HANDLING.tr.md) | `pending_decision`; veri paylaşım karar sahibi `not_provided` |
| G07 — Manifest/bütünlük anlatımı | Manifest varlığı, sağlanan dosyalar ve gerçekten yapılmış kontrolün türü/sonucu; yapılmayanlar. | JSON+manifest kısmi ilişki tam bundle/CLI verify, hash imza/producer doğrulaması diye sunulursa `blocked`. [Pinli reporting.md411–419](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419) | `pending_decision`; artefact inceleme rolü `not_provided` |
| G08 — Karşılaştırma sınırları | Ayrı comparison ref'i, seçili before/after byte kimlikleri ve mevcut kapsam beyanı; dört grup ve yorum sınırları. | İlgisiz demo gerçek retest'e bağlanmış veya `only_in_before=fixed` yapılmışsa `blocked`. Karşılaştırma yoksa yokluğu/gerekçesi belirtilir; `not_applicable` için açık kapsam gerekçesi gerekir. [DELIVERABLE_SPEC §6](../DELIVERABLE_SPEC.tr.md#6-önceki-değerlendirmeyle-karşılaştırma) | `pending_decision`; karşılaştırma inceleme rolü `not_provided` |
| G09 — Saklama ve erişim kararları | Sekiz sınıfın karar sahibi, erişim/yer/aktarım, retention/silme/yedek ve olay karar ref'leri; gerçek uygulama kanıtı varsa ayrı. | Bu gerçek kararlar/uygun veri işleme yolu yoksa müşteri verisiyle ilerlenmez; şablon doldurma, şifreleme/ACL/silme uygulaması değildir. [DATA_HANDLING karar tablosu](DATA_HANDLING.tr.md#her-sınıf-için-açık-karar-kaydı) | `pending_decision`; veri/kurum karar sahibi `not_provided` |
| G10 — Teslim sahibi | Paketin sürümü/dosya ref'leri, teslimi yapacak gerçek rol/kişi ve yetki bağı, gereken inceleyenler. | Gerçek sahip yoksa belge hazırlayan otomatik teslim yetkilisi sayılmaz. Atama veya karar belgesi olmadan ilerlenmez. [PILOT_READINESS §2](../PILOT_READINESS.tr.md#2-işletim-kapıları) | `blocked`; teslim sahibi `not_provided` |
| G11 — Gerçek müşteri kabul süreci | Yetkili alıcı, kabul/kapanış yöntemi, açık işlerin gösterimi; gerçekleşirse gerçek teslim/alındı/kabul kaydı. | Alıcı/süreç yoksa karar bekler; belge varlığı `delivered`, müşteri kabulü veya memnuniyet sayılmaz. [PILOT_READINESS §4](../PILOT_READINESS.tr.md#4-pilot-başarısı-nasıl-ölçülecek) | `pending_decision`; müşteri kabul rolü `not_provided` |
| G12 — Gerekli teknik/kurumsal onaylar | Bu dar vaka için seçili binary/feature, experimental kaynak riski, uzman işletimi, yetki/veri ve gerekli kurumsal karar ref'leri. | Gerekli gerçek onay/işletim kanıtı yoksa açık kalır; bütün ekosistem kapıları bağımsız Termivar pilotuna eklenmez. [PILOT_READINESS §1–3 ve §5](../PILOT_READINESS.tr.md) | `blocked`; ilgili karar sahipleri `not_provided` |

## Matris nasıl kullanılır?

1. Vaka, artefact ve ledger/decision kayıtlarının gerçek referansları eklenir; kanıt olmayan kontrol sonucu yazılmaz. Kaynak metadata'sını okumak uzman incelemesi değildir.
2. Her kapı kendi gerekçesiyle değerlendirilir. Bir kapının hazırlanmış olması ötekini kapatmaz; boş alan ve dış kanıt eksikliği `pending_decision` veya somut engelde `blocked` kalır.
3. Include/exclude kararı için `decision_id`, gerekçe, kanıt/sınırlama ve handoff bağı bulunur. [Delivery checklist](templates/DELIVERY_CHECKLIST.template.md) matrise referans verir; yeni onay üretmez.
4. Herhangi bir `blocked` veya gerekli `pending_decision`, gerçek müşteri handoff'unu ilerletmeme nedenidir. Tüm satırların `ready_for_manual_review` olması da GO değildir. Gerçek dış yetkilendirme, uzman kararı ve teslim sahibi yerine bu kit geçmez.
5. Gerçek teslim kanıtı yoksa `delivered`, gerçek kabul yoksa kabul edildi yazılmaz. Açık takip, ayrı yeniden değerlendirme veya müşteri geri bildirimi gerçekleşmiş sayılmaz.

## Demo vakaya uygulanışı

Vaka `demo_only=true` taşır: **Demonstration only — No real system assessed.** Bu marker yetki, lisans, uzman incelemesi veya müşteri kabulü sağlamaz. Mevcut benign assessment'ın dört informational gözlemi kaynak inceleme statüsü değil native sonuçtur; operasyon ledger'ında `unreviewed`, `scope_status=unknown`, `client_inclusion=pending_decision` kalır. [Phase14 örnek provenance](../examples/README.tr.md).

Demo belge/metadata'sı yalnız kendi dar kapsamı için `ready_for_manual_review` olarak hazırlanabilir. Bu etiket dört gözlemi incelenmiş yapmaz. Gerçek scope/yetki, pilot binary seçimi, yeni çalışma, reviewer/teslim sahibi, retention/erişim kararları veya müşteri kabulü yoktur; ilgili gerçek kapılar `pending_decision` ya da engel varsa `blocked` kalır. Onaysız bir gerçek faaliyet `not_applicable` denilerek atlanmaz. Demo gate [ayrı örnek kayıtta](examples/DEMO_DELIVERY_GATE.md) tutulur.

Kısmi assessment JSON/manifest ilişkisi tam bundle doğrulaması değildir; mevcut comparison ayrı örnektir, ana assessment'ın retest'i değildir. Elle hazırlanmış incomplete fixture native CLI çıktısı diye anlatılmaz. Incomplete, temiz sonuç; `KnowledgeOnly`, wire disposition veya yeni doğrulama yetkisi yapılmaz. [İnceleme politikası](OBSERVATION_REVIEW_POLICY.tr.md), [DELIVERABLE_SPEC §4–6](../DELIVERABLE_SPEC.tr.md#4-tamamlanma-ve-kapsam-eksikleri).

Bu faz yalnız offline belge/örnek hazırlığı ve manuel belge tutarlılığı incelemesidir. Yazılım testi, CLI/scanner çalıştırması, gerçek uzman güvenlik incelemesi, canlı kabul, müşteri teslimi, satış/pilot/üretim GO'su veya yeni faz başlangıcı değildir.
