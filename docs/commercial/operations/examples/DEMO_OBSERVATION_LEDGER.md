# Demo gözlem defteri — Internal Review Record

**Demonstration only — No real system assessed.**

`case_id=DEMO-TERMIVAR-015`; `demo_only=true`. Bu defter yalnız [ART-A1 assessment.json](../../examples/assessment.json) içindeki dört informational öğeyi izler. A1'in tam byte SHA256'sı `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9`; uzunluğu 3907 byte. Kaynak ve insan kararları ayrı alanlardır. Aşağıdaki sayfa, yapılmış uzman incelemesi veya paylaşım izni değildir.

`OBS-01..04` bu defterin dahili sıra etiketleridir; native run/finding kimliği veya yeni Termivar observation ID'si değildir. Her `observation_ref`, **ART-A1 + yukarıdaki tam dosya hash'i + native fingerprint + JSON pointer** bileşimidir. Aynı fingerprint'in başka dosyada görünmesi bu belge zincirini kendiliğinden kurmaz. Kaynak byte kimlikleri [case index](DEMO_CASE_INDEX.md) içindedir.

## OBS-01 — Referrer-Policy kaynak gözlemi

| Alan | Kayıt |
| --- | --- |
| `case_id` | `DEMO-TERMIVAR-015` |
| `source_artifact_ref` | `ART-A1` |
| `source_artifact` | [assessment.json](../../examples/assessment.json) |
| `source_artifact_sha256` | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `observation_ref` | `sha256:32adc97266dff2c8c11116f202bc894adcab02b7a9f1c315f988f1878bd10004` |
| `source_json_pointer` | `/items/0` |
| `capability_id` / `subject_reference` | `web.passive.referrer-policy.missing@1` / `subject-0000` |
| Kaynak başlık | `Referrer-Policy was not observed` |
| Kaynak redakte özet | `The eligible HTML response did not include a Referrer-Policy.` |
| `source_disposition` / claim basis | `informational` / `observation` |
| Kaynak category / CWE | `browser-defense` / `null` |
| Kaynak severity / confidence | `null` / `confidence_ppm=1000000`; atanmamış severity ve kaynağın confidence alanı |
| `scope_status` | `unknown` |
| `evidence_reference` | `evidence-0000`, `evidence-0001`, `evidence-0002`, `evidence-0005`, `evidence-0006`, `evidence-0007` |
| Kaynak evidence bağlantıları | `evidence_count=6`; control/candidate listeleri boş; case/outcome/verification stage `null` |
| `evidence_limitations` | Opaque referansların ham HTTP içeriği verilmedi ve uzman tarafından incelenmedi. Eligible response anlatımı, gerçek müşteri kapsamı, exploitable durum veya etkilenmiş kullanıcı kanıtı değildir |
| `review_status` | `unreviewed` |
| `review_reason` | Uzman incelemesi yapılmadı; yalnız mevcut metadata ve kaynak bağlantısı belgeye aktarıldı |
| `client_inclusion` | `pending_decision` |
| `follow_up` | İleride yetkili uzman kapsamı ve mevcut kanıta erişim kararını belirlemeli; uygulamanın disclosure ihtiyacını ve source önerisinin uygunluğunu incelemeli. Yeni canlı istek veya düzeltme burada başlatılmaz |
| Kaynak önerisi | `web.remediation.referrer-policy@1`: uygulamanın cross-origin disclosure ihtiyacına uygun Referrer-Policy tanımlama önerisi; bağımsız uzman önerisi veya uygulanmış düzeltme değildir |
| `reviewer` / `reviewed_at` | `not_provided` / `not_provided` |
| İnsan karar bağlantısı | [OBS-01 bekleyen karar kaydı](DEMO_REVIEW_DECISIONS.md#obs-01); `decision_id=not_provided` |

## OBS-02 — X-Content-Type-Options kaynak gözlemi

| Alan | Kayıt |
| --- | --- |
| `case_id` | `DEMO-TERMIVAR-015` |
| `source_artifact_ref` | `ART-A1` |
| `source_artifact` | [assessment.json](../../examples/assessment.json) |
| `source_artifact_sha256` | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `observation_ref` | `sha256:423a41c26f6479fa1d15e672819aea23926e3dee76902559fe92cbc564ddf53a` |
| `source_json_pointer` | `/items/1` |
| `capability_id` / `subject_reference` | `web.passive.x-content-type-options.missing@1` / `subject-0000` |
| Kaynak başlık | `X-Content-Type-Options was not observed` |
| Kaynak redakte özet | `The eligible document response did not include X-Content-Type-Options.` |
| `source_disposition` / claim basis | `informational` / `observation` |
| Kaynak category / CWE | `browser-defense` / `null` |
| Kaynak severity / confidence | `null` / `confidence_ppm=1000000` |
| `scope_status` | `unknown` |
| `evidence_reference` | `evidence-0001`, `evidence-0002`, `evidence-0003`, `evidence-0005`, `evidence-0006`, `evidence-0007` |
| Kaynak evidence bağlantıları | `evidence_count=6`; control/candidate listeleri boş; case/outcome/verification stage `null` |
| `evidence_limitations` | Ham response, sunulan content bağlamı ve tarayıcı etkisi incelenmedi; header gözlemi MIME etkisi, istismar veya müşteri kapsamı kanıtı değildir |
| `review_status` | `unreviewed` |
| `review_reason` | Uzman incelemesi yapılmadı; metadata belge kontrolü teknik doğrulama sayılmadı |
| `client_inclusion` | `pending_decision` |
| `follow_up` | İleride yetkili uzman kapsamı, gerekli mevcut kanıtı ve `nosniff` önerisinin content uyumluluğunu incelemeli; işlem/erişim için ayrıca karar gerekir |
| Kaynak önerisi | `web.remediation.nosniff@1`: içerikle uyumlu olduğunda `X-Content-Type-Options: nosniff` önerisi; uygulanmadı veya doğrulanmadı |
| `reviewer` / `reviewed_at` | `not_provided` / `not_provided` |
| İnsan karar bağlantısı | [OBS-02 bekleyen karar kaydı](DEMO_REVIEW_DECISIONS.md#obs-02); `decision_id=not_provided` |

## OBS-03 — Permissions-Policy kaynak gözlemi

| Alan | Kayıt |
| --- | --- |
| `case_id` | `DEMO-TERMIVAR-015` |
| `source_artifact_ref` | `ART-A1` |
| `source_artifact` | [assessment.json](../../examples/assessment.json) |
| `source_artifact_sha256` | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `observation_ref` | `sha256:e0e9548ae2581d2522aac9b1cdce9ade61e4010d02308c716f252a15cbb7addb` |
| `source_json_pointer` | `/items/2` |
| `capability_id` / `subject_reference` | `web.passive.permissions-policy.missing@1` / `subject-0000` |
| Kaynak başlık | `Permissions-Policy was not observed` |
| Kaynak redakte özet | `The eligible HTML response did not include a Permissions-Policy.` |
| `source_disposition` / claim basis | `informational` / `observation` |
| Kaynak category / CWE | `browser-defense` / `null` |
| Kaynak severity / confidence | `null` / `confidence_ppm=1000000` |
| `scope_status` | `unknown` |
| `evidence_reference` | `evidence-0001`, `evidence-0002`, `evidence-0005`, `evidence-0006`, `evidence-0007`, `evidence-0008` |
| Kaynak evidence bağlantıları | `evidence_count=6`; control/candidate listeleri boş; case/outcome/verification stage `null` |
| `evidence_limitations` | Ham HTML/header ve uygulamanın gerekli browser feature'ları incelenmedi. Header gözleminden izinlerin fiilen kötüye kullanıldığı veya risk seviyesi çıkarılmaz |
| `review_status` | `unreviewed` |
| `review_reason` | Gerçek uzman ve kanıt incelemesi yok; kaynak öğe insan kararı olarak yükseltilmedi |
| `client_inclusion` | `pending_decision` |
| `follow_up` | İleride yetkili uzman kapsamı ve uygulamanın kullandığı browser feature ihtiyacını mevcut uygun kanıt üzerinden değerlendirmeli; paylaşım ve ek işlem ayrı karara bağlıdır |
| Kaynak önerisi | `web.remediation.permissions-policy@1`: gerekli browser feature'ları incelendikten sonra Permissions-Policy tanımlama önerisi; yapılmış değişiklik değildir |
| `reviewer` / `reviewed_at` | `not_provided` / `not_provided` |
| İnsan karar bağlantısı | [OBS-03 bekleyen karar kaydı](DEMO_REVIEW_DECISIONS.md#obs-03); `decision_id=not_provided` |

## OBS-04 — Content-Security-Policy kaynak gözlemi

| Alan | Kayıt |
| --- | --- |
| `case_id` | `DEMO-TERMIVAR-015` |
| `source_artifact_ref` | `ART-A1` |
| `source_artifact` | [assessment.json](../../examples/assessment.json) |
| `source_artifact_sha256` | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `observation_ref` | `sha256:fa8c2374a132316b67a492e8ab213f26b389c9fecefcdf39685026c75fde46f2` |
| `source_json_pointer` | `/items/3` |
| `capability_id` / `subject_reference` | `web.passive.csp.missing@1` / `subject-0000` |
| Kaynak başlık | `Content-Security-Policy was not observed` |
| Kaynak redakte özet | `The eligible HTML response did not include a Content-Security-Policy.` |
| `source_disposition` / claim basis | `informational` / `observation` |
| Kaynak category / CWE | `content-policy` / `null` |
| Kaynak severity / confidence | `null` / `confidence_ppm=1000000` |
| `scope_status` | `unknown` |
| `evidence_reference` | `evidence-0001`, `evidence-0002`, `evidence-0004`, `evidence-0005`, `evidence-0006`, `evidence-0007` |
| Kaynak evidence bağlantıları | `evidence_count=6`; control/candidate listeleri boş; case/outcome/verification stage `null` |
| `evidence_limitations` | Opaque bağlantılar ham response veya exploit kanıtı değildir. CSP gözlemi XSS'nin varlığını, sömürülebilirliği veya müşteri etkisini bağımsız doğrulamaz |
| `review_status` | `unreviewed` |
| `review_reason` | Yapılmış uzman incelemesi yok; kaynak disposition ve atanmamış severity korunuyor |
| `client_inclusion` | `pending_decision` |
| `follow_up` | İleride yetkili uzman kapsam/kanıt ilişkisini ve uygulamaya uygun CSP yaklaşımını incelemeli. Ek canlı doğrulama veya policy değişikliği ayrıca yetki gerektirir; burada yapılmaz |
| Kaynak önerisi | `web.remediation.csp@1`: uygulama belgesi için CSP tanımlama ve geçerliliğini değerlendirme önerisi; düzeltme veya doğrulama sonucu değildir |
| `reviewer` / `reviewed_at` | `not_provided` / `not_provided` |
| İnsan karar bağlantısı | [OBS-04 bekleyen karar kaydı](DEMO_REVIEW_DECISIONS.md#obs-04); `decision_id=not_provided` |

## Defterin ortak sınırları

Dört öğede 6'şar evidence referansı bulunur; toplam 24 referans bağlantısı **24 bağımsız kanıt değildir**. Birleşimde `evidence-0000..0008` olmak üzere 9 ayrı opaque etiket vardır; ham kanıt bu belgeye sağlanmış veya müşteriye teslim edilmiş sayılmaz. Kaynakta `null` olan severity low/sıfır risk yapılmadı; confidence ürün doğruluğu, istismar olasılığı veya CVSS'ye dönüştürülmedi. Dört öğe `needs_review`, `confirmed` veya `KnowledgeOnly` diye yeniden etiketlenmedi.

Phase15 insan sözlüğü `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery` değerlerinden oluşur. Bunlar native sonuç sınıfları değildir. Bu defterin dört değeri de `unreviewed` kalır. Phase14'ün ayrı önerilen sözlüğüne migration veya otomatik eşleme yapılmaz. Gelecekte `reviewed_for_delivery` kararı verilse bile bu tek başına zafiyet doğrulaması olmaz.

Bu iç defterin kayıtları [paylaşılmamış handoff taslağına](DEMO_CLIENT_HANDOFF.md) bulgu veya ham kanıt olarak otomatik aktarılmaz. Kaynak/alan anlamları [Phase14 teslim standardı](../../DELIVERABLE_SPEC.tr.md#3-her-öğe-için-kayıt), [örnek provenance](../../examples/README.tr.md) ve [pinli native DTO](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting.rs#L18308-L18330) ile sınırlıdır.
