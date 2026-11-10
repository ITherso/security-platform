# Demo vaka dizini — DEMO-TERMIVAR-015

**Demonstration only — No real system assessed.**

Bu dosya bir **Internal Review Record** örneğidir. `DEMO-TERMIVAR-015`, bu belge takımı için verilen dahili demo dosya kimliğidir; Termivar run, müşteri, assessment veya yetkilendirme kimliği değildir. `demo_only=true`. Yeni assessment, comparison veya kanıt üretilmedi. Mevcut altı JSON yalnız okundu; byte'ları değiştirilmedi veya bu dizine kopyalanmadı.

## Vaka ve kapsam kaydı

| Alan | Doldurulmuş demo kaydı |
| --- | --- |
| `case_id` | `DEMO-TERMIVAR-015` |
| Müşteri / kurum referansı | `not_provided` |
| Amaç | Üç ayrı sentetik kaynak kümesinin kaynak → gözlem → bekleyen insan kararı → paylaşılmamış handoff bağlantısını göstermek |
| Gerçek değerlendirme / yetki kaydı | `not_provided`; bu belge çalışma izni oluşturmaz |
| İzin verilmiş gerçek hedef / faaliyet / pencere | `not_provided` |
| Gözlemlerin `scope_status` değeri | `unknown`; kaynak profil veya subject referansından müşteri kapsamı türetilmez |
| Bu belge çalışmasının sınırı | Önceden mevcut benign JSON ve Phase14 belgeleri üzerinden offline kayıt hazırlığı |
| Hariçler | Yeni tarama/CLI, test/build, hedef erişimi, canlı doğrulama, müşteri iletişimi, gerçek teslim, otomatik düzeltme |
| Kabul edilmiş istek ve zaman bütçesi | `not_provided`; yeni yürütme yok. A kümesinin rendered JSON'unda bütçe/kullanım ve başlangıç/bitiş zamanı bulunmuyor |
| Beklenen demo çıktıları | Bu dizindeki beş Markdown kayıt; native JSON, tam bundle veya müşteri teslim paketi üretimi değil |
| Veri işleme / erişim / paylaşım / saklama / silme kararları | `pending_decision`; süre ve aktarım kanalı seçilmedi |
| Operatör / uzman / kalite kontrol / teslim sahibi | Her biri `not_provided`; rol ihtiyacı, atanmış kişi değildir |
| Uzman inceleme zamanı / gerçek teslim / müşteri kabul kanıtı | Her biri `not_provided` |
| Gerçek pilot / satış / production GO | Verilmedi; [demo kapısı](DEMO_DELIVERY_GATE.md) `blocked` |

## Kaynak artefact dizini

A, C ve D **ayrı kaynak kümeleridir**. Birbirini tamamlayan aynı koşu veya gerçek zaman çizgisi olarak birleştirilmez. A1/A2 kısmi JSON–manifest çifti; C1/C2/C3 ayrı belge karşılaştırması; D1 ayrı elle yazılmış diagnostic örneğidir. Aşağıdaki boyut/SHA256 değerleri mevcut dosya byte'larından salt okunur ölçülmüştür; JSON parse edilip yeniden kaydedilmemiştir.

| `source_artifact_ref` | Mevcut kaynak bağlantısı | Byte | Tam dosya SHA256 |
| --- | --- | ---: | --- |
| `ART-A1` | [assessment.json](../../examples/assessment.json) | 3907 | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `ART-A2` | [manifest.json](../../examples/manifest.json) | 711 | `c77ce74508e8efaff7ebf1b0203331b4295d468c726e4acd7bad709eb85813df` |
| `ART-C1` | [comparison.json](../../examples/comparison.json) | 5674 | `291f5e7b407a247cb786119a249fe6f3cb9f5526e6700605c4a0008bee91a1d0` |
| `ART-C2` | [comparison-before.json](../../examples/comparison-before.json) | 3795 | `33f709237ffea142d892891d818815251c1cb35d888abe155f7175e15d7d481f` |
| `ART-C3` | [comparison-after.json](../../examples/comparison-after.json) | 3812 | `5ea44cfd6dbab132aa96e62813c32c12e35f0bf32c09b43a102a16e9ff7bbe64` |
| `ART-D1` | [incomplete-diagnostic.json](../../examples/incomplete-diagnostic.json) | 3465 | `85881c1d3883bb719cd05e7fbd63f564188371ddab58be94eb7e56c9e84d4f0a` |

Tam dosya SHA256'sı byte kimliğidir; native öğenin `sha256:` fingerprint'i ayrı alan ve farklı amaçtır. İkisi de üretici imzası, kimliği, yetki veya bulgu doğrulaması değildir.

### A — Ana complete örnek ve kısmi manifest

`ART-A1`: `venom-rendered-assessment/v1`; source `venom-assessment-run/v1`; run `venom-run/v1`; profile schema `venom.scan-profile/v1`; profile `web-review`; status `complete`; 1 subject, 4 item. Dördü de `informational` / `observation`; severity ve verification stage `null`. Bu, dört doğrulanmış zafiyet veya bütün kapsamın değerlendirildiği anlamına gelmez.

`ART-A2`: `termivar-report-bundle/v1`; producer alanı `Termivar` / `0.10.0-alpha.2`. JSON-entry uzunluğu, SHA256'sı ve assessment özetindeki profile/status/subject/item sayıları A1 ile eşleşir. Bu **yalnız seçili JSON-entry ve özetinin belge kontrolüdür**. Manifestin bildirdiği `assessment.html` (8000 byte, SHA256 `a43070ee91860782a1eb47cd081b5fe628423a847bcc172e1a039cb6055cf1c1`) burada bulunmaz; okunmadı, render edilmedi veya doğrulanmadı. Native verifier çalıştırılmadı; tam bundle doğrulaması ve üretici kimliği `not_verified`.

Provenance: Phase14 [örnek kaynak kaydı](../../examples/README.tr.md), pinli Termivar checkout `6a2639348c2366d0bf71b9a34e5484d40aa393a3` altındaki `docs/examples/report-bundle/assessment-001/` dosyalarını belirtir. Aynı kayıt tarihsel generation revision'ını `e747db4153eb52e06664bcec9dcb3411daef6fe6`, development binary'yi alpha.2 olarak açıklar. Bu geçmiş yeni çalıştırma veya mevcut alpha.3 source için runtime kabulü değildir.

### C — Ana assessment'tan bağımsız karşılaştırma

`ART-C1`: `termivar-report-comparison/v1`. Kaynak beyanları `scope_assurance=operator-declared`, `coverage_equivalence=not-established`, `source_authenticity=not-established-by-parsing`. Dört grubun her birinde 1 kayıt vardır: `only_in_after`, `only_in_before`, `changed`, `unchanged`. `changed_fields` yalnız `redacted_summary` içerir.

Before digest'i C2'ye, after digest'i C3'e eşleşir; iki girdi de `venom-rendered-assessment/v1`, `web-review`, `complete`, 1 subject / 3 item bildirir. Bu digestlerin hiçbiri A1 değildir. **C1, A1'in retest'i değildir.** Yeni fark hesaplanmadı; mevcut gruplar ve bağlar okundu. Ayrı manifest bu C kümesinde sağlanmamıştır.

[Phase14 provenance kaydı](../../examples/README.tr.md), C kümesini aynı pinli checkout'un `docs/examples/report-compare/` dizinine ve tarihsel generation revision `664d385bd455a4fc5002b98a2103078cfba1be29` / development alpha.2 kaydına bağlar. Düzenlenmiş sentetik document-processing girdileridir; müşteri değişim sonucu değildir. `only_in_before` düzeltme, `only_in_after` yeni oluşma, `changed` risk artışı/azalışı, `unchanged` eşit güvenlik/kapsam kanıtı değildir.

### D — Ayrı incomplete diagnostic

`ART-D1`: `schema_version=web-assessment/v2`, `disposition=incomplete`; `subject_execution_incomplete` ve `wall_time_limit`; item projection `unavailable` / `incomplete_assessment_items_withheld`. `items` listesi veya tamamlanmış raporun `item_count` alanı yoktur; “0 bulgu” sonucu yazılamaz.

Kaynak, platformun Phase11'de **elle hazırlanmış** fixture'ıdır; Phase14 [kaynak kaydı](../../examples/README.tr.md), platform baseline `aa643d40797998d5f615cb5ba5b71b972596abc9` içindeki `operator-console/src/features/termivarReview/examples/incomplete-example.json` byte'larını belirtir. CLI çıktısı veya ölçülmüş çalışma değildir. Mevcut exact-origin, sıfır wall-time bütçesi ve sıfır kullanım alanları authored demo değerleridir; müşteri için kabul edilmiş bütçe veya ölçülen çalışma değildir. Ayrı manifest sağlanmamıştır. A/C ile kapsam ya da zaman ilişkisi kurulmaz; fixture'ın placeholder hedefi açılmaz veya handoff'a taşınmaz.

## Kayıt zinciri ve paylaşım sınırı

1. [Observation ledger](DEMO_OBSERVATION_LEDGER.md): yalnız A1'in dört öğesi; `OBS-01..04` dahili sıra etiketleri, gerçek kaynak kimliği yerine geçmez. Her biri tam A1 hash'i + native fingerprint + `/items/0..3` ile bağlanır.
2. [İnceleme karar kayıtları](DEMO_REVIEW_DECISIONS.md): dört kayıt `unreviewed`, `scope_status=unknown`, `client_inclusion=pending_decision`; gerçek karar/inceleyen/zaman yoktur.
3. [Demo teslim kapısı](DEMO_DELIVERY_GATE.md): belge hazırlanması ile gerçek teslim izni ayrılır; tüm açık kararlar korunur.
4. [Client Handoff](DEMO_CLIENT_HANDOFF.md): paylaşılmamış demo taslağı. Ledger'in iç notları, rol atamaları, opaque evidence listeleri ve ham kaynak içerikleri otomatik aktarılmaz; müşteri için onaylanmış bulgu listesi yoktur.

Phase15'in altılı insan `review_status` sözlüğü yeni **belge alanlarıdır**. Phase14'ün `not_performed / needs_additional_evidence / reviewed` önerisi değiştirilmedi; native JSON migration'ı veya otomatik eşleme yapılmadı. Bu örneğin `unreviewed` değeri, uzman incelemesinin yapılmadığını açıklar; dosya/hash kontrolü uzman incelemesi sayılmaz.

## Phase14 ve native sözleşme bağlantıları

[Ürün teklifi](../../PRODUCT_OFFERING.tr.md) hizmet amacını, [pilot kapsamı](../../PILOT_SCOPE.tr.md) gerçek izin sınırını, [teslim standardı](../../DELIVERABLE_SPEC.tr.md) müşteri çıktısını, [iddia matrisi](../../CAPABILITY_CLAIMS.tr.md) teknik sınırları, [pilot hazırlığı](../../PILOT_READINESS.tr.md) açık kapıları tanımlar. Bu kayıtlar onları uygulamak için hazırlanmış demo dosyalarıdır; ürün teklifini veya kabul durumunu değiştirmez.

Pinli native dayanaklar: [öğe DTO'su, reporting.rs18308–18330](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting.rs#L18308-L18330), [native disposition sınırı150–163](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L150-L163), [bütünlük sınırı411–419](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419), [comparison ve diagnostic sınırı567–603](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L567-L603). Pinli teknik kaynaklar yerel checkout üzerinden okundu; bu kaynak bağlantıları açılmadı ve değerlendirme hedefiyle iletişim kurulmadı.
