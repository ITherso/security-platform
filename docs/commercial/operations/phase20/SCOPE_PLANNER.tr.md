# Çevrimdışı kapsam planlayıcısı

**DEMONSTRATION ONLY — NO TARGET ASSESSED — NO EXECUTION AUTHORIZED**

Phase20, kapsam belirleme → Termivar değerlendirmesi → Phase17 Intake →
Phase18/19 Analyst Review → Phase16 Handoff zincirinin yalnız kapsam önerisi
adımını ele alır. Diğer adımlar otomatik başlatılmaz veya değiştirilmez.

[Araç ve örnek](../../../../tools/commercial_scope/README.md),
[kaynak eşlemesi](CAPABILITY_MAPPING.tr.md),
[güven ve yetki](TRUST_AND_AUTHORIZATION.tr.md),
[gerçek teslim kaydı](DEMO_DELIVERY.tr.md).

Girdi `termivar-assessment-scope-proposal/v1` sürümlü, exact-field JSON'dur:
`schema_version`, `mode`, `proposal_id`, `assessment_profile`, `scope`,
`requested_capabilities`, `budgets`, `authorization_status`,
`data_handling_status`, `review_requirements`. `mode=demo`, yetki
`not_provided`, veri işleme `pending_decision` sabittir. Gerçek domain,
credential, token, cookie veya yetki sahibi bilgisi için alan bulunmaz.

`scope` yalnız `origin`, `root_url`, `requested_methods`,
`authenticated_context`, `context_markers` içerir. URL'ler ASCII HTTP(S)
`.invalid` metinleridir; kullanıcı bilgisi kabul edilmez. Kök URL'sindeki farklı
origin, query veya fragment sessizce onarılmaz, preflight'ta uyumsuz gösterilir.
Metot listesi önerilen izinli üst sınırdır; ilk alt küme GET/HEAD'dir ve native
kök subject GET gerektirir. Placeholder bağlam işareti gerçek kimlik değildir.

Öneri en fazla 128 KiB; strict UTF-8, BOM/duplicate key/float/NaN/unknown field
reddi, derinlik 12, düğüm 10000 ve toplam metin 128 KiB sınırları vardır.
URL en fazla 2048 karakter, capability en fazla 32, context marker en fazla
16; sayılar boolean olamaz ve 0..2^53−1 aralığındadır. Bu sayısal parser aralığı
native bütçe izni değildir. Native yedi aralık ayrıca preflight'ta incelenir.
Desteklenmeyen sürüm reddedilir. JSON içeriği dosya seçemez veya bağlantı açamaz.

Çıktıların anlamı:

| Dosya | İçerik |
| --- | --- |
| `capability-catalog.json` | Sınırlı 11 kaynak tanımı, kanıt sınıfı, önkoşullar, bütçe aralıkları ve 17 dosya kimliği |
| `scope-preflight.json` | Her koşul için açıklama, kaynak referansı ve ayrı sonuç |
| `assessment-plan-proposal.json` | Yeni yürütülemeyen plan sözleşmesi, öneri/katalog/kaynak bağlantısı ve engeller |
| `assessment-plan-summary.md` | İnsan tarafından okunabilen aynı kapsam ve sınırlamalar |
| `manifest.json` | Gerçek payload boyutları ve SHA256; kendisi hash listesine dahil değildir |

Sonuçlar `supported_by_source`, `unsupported`, `insufficient_source_evidence`,
`missing_required_context`, `budget_conflict`, `pending_authorization` olarak
ayrılır. Teknik kaynak eşleşmesi olumlu olabilir; genel sonuç yetki beklemeye
devam eder. Bilinmeyen capability katalog dışında olarak açıkça listelenir.
Hiçbir seçim sessizce atılmaz. `baseline` native profili vardır, fakat ilk
planlayıcının web-review alt kümesinde desteklenmez; web-review limitleri ona
uygulanmaz. Native bir işlevin varlığı çalışma başarısı veya güvenlik bulgusu
olarak gösterilmez.

Yeni plan `termivar-assessment-plan-proposal/v1` sözleşmesidir. Native
`venom.scan-profile/v1`, AttackPlan, evaluator sonucu, YAML config veya scheduler
işi değildir. Tarama başlatacak CLI satırı veya yürütme öğesi içermez.

Tam kaynak ve demo komutu teslim belgesindedir. Çıktı dizini yeni olmalıdır;
mevcut klasör üzerine yazılmaz. Yarım yazma, symlink/reparse ve path korumaları
koda eklenmiştir; saldırgan girdi/yarış/crash kabulü bu fazda yapılmamıştır.

Yeni test, build, frontend, sunucu, servis veya native çalışma yoktur. Bu tur
bir sentetik üretimle biter; gerçek pilot ve başka faz kendiliğinden başlamaz.
