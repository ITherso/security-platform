# Kaynak destekli capability ve bütçe eşlemesi

**DEMONSTRATION ONLY — NO TARGET ASSESSED — NO EXECUTION AUTHORIZED**

Native kaynak pini `6a2639348c2366d0bf71b9a34e5484d40aa393a3`.
Katalog bütün Termivar özelliklerinin envanteri değildir. Kaynakta kullanılan
isim/namespace korunur; CLI capability, GraphQL metadata tanımı ve assessment
item kimliği birbirinin yerine kullanılmaz. Gerçek göreli dosyalar ve SHA256
değerleri üretilen katalog ile manifesttedir. Kaynak kökü CLI'de açıkça seçilir;
proposal bir path/modül seçemez.

`source_declared` kaynak/sözleşme beyanı, `implementation_inspected` ilgili kodun
statik incelenmesi, `insufficient_source_evidence` yetersiz kaynak kanıtıdır.
Bu sınıflar binary feature kabulü, runtime başarısı veya tarama sonucu değildir.

| Gerçek isim | Kaynak türü ve sınırlama |
| --- | --- |
| `web.passive.referrer-policy.missing@1` | Gözlem; informational passive header koşulu |
| `web.passive.x-content-type-options.missing@1` | Gözlem; informational passive header koşulu |
| `web.passive.permissions-policy.missing@1` | Gözlem; informational passive header koşulu |
| `web.passive.csp.missing@1` | Gözlem; informational passive header koşulu |
| `graphql.anonymous-root-introspection@1` | Opsiyonel GraphQL child bağlamı gerekir; POST bileşimi ilk GET/HEAD planner alt kümesinde kabul edilmez |
| `api.openapi-contract-observed@1` | Opsiyonel OpenAPI feature/opt-in bağlamı; yalnız gözlem |
| `api.rest-readonly-surface-observed@1` | Opsiyonel REST feature/opt-in ve aynı çalışmada OpenAPI bağlamı; yalnız gözlem |
| `authorization.resource-cross-principal-equivalence@1` | Resource authorization bağlamı ve placeholder principal'lar; differential NeedsReview sınırı |
| `api.review.authorization-context.visibility-difference@1` | Ayrı root auth-context karşılaştırması; HTTPS exact origin root; NeedsReview sınırı |
| `graphql.get-query` | GraphQL catalog metadata-only; executable assessment item değildir |
| `command.api` | Mevcut CLI UnsupportedStub; assessment capability değildir |

İlk dört tanım `web_runtime/assessment_passive.rs:131–327`; item kimlik ve
disposition sınırları `assessment_item.rs:1811–1869`. Diğer item'lar sırasıyla
`graphql_runtime.rs:113–133`, `openapi_runtime.rs:49–53`,
`rest_runtime.rs:39–42`, `resource_authorization_runtime.rs:49–60`,
`assessment_api_visibility.rs:34–45`. Metadata-only ayrımı
`graphql_review.rs:592–637`, API stub `termivar-cli/src/capabilities.rs:870–880`.
Bu yollar katalogdaki `crates/termivar-scanner/src/` veya `crates/` köküne göredir.

Yerel context marker'lar yalnız gerekli feature/opt-in/same-run/kimlik
placeholder beyanını temsil eder; native CLI flag veya doğrulanmış feature
listesi değildir. Gerçek credential istenmez. Root ve resource authorization
yolları native CLI'de birbirini dışlar (`main.rs:424–434`). Kaynakta `GET` adı
yan etkisizlik garantisi değildir. Kullanıcı izni ve asset sahipliği bu
eşlemenin dışında kalır.

`WebAssessmentLimits` için incelenen yedi Rust API aralığı:

| Proposal alanı | Minimum | Default | Maksimum |
| --- | ---: | ---: | ---: |
| `max_total_requests` | 0 | 256 | 10000 |
| `max_wall_time_ms` | 0 | 300000 | 3600000 |
| `max_subjects` | 1 | 64 | 1024 |
| `max_discovery_depth` | 0 | 2 | 16 |
| `max_active_verifications` | 0 | 10 | 64 |
| `max_response_body_bytes` | 1 | 262144 | 16777216 |
| `max_total_response_bytes` | 1 | 16777216 | 268435456 |

Kaynak: `web_runtime/web_assessment.rs:309–375,466–629`, body hard cap ayrıca
`http_evidence/policy.rs:13`. Parser bu değerleri clamp etmez. Zero request veya
zero time API şekline uyabilse de dispatch'i engellediği için `budget_conflict`
üretir. Diğer alanların native kapsamı sınırlı katalogda kaynak referanslarıyla
ayrı açıklanır; probe maliyetleri toplanıp coverage hesabı uydurulmaz.

Genel request/time budget override CLI bayrakları bulunmadı: `ScanArgs`
`termivar-cli/src/main.rs:677–735`. Limit eşlemesi Rust API envelope'udur;
kullanılabilir CLI seçenekleri veya binary'de ölçülmüş limit kabulü değildir.
Custom library limit yolu `scan_profile.rs:646–653` ile ayrıdır.

Opsiyonel child'ların active allowance bileşimi `web_assessment.rs:2929–3030`
nedeniyle basit toplam maliyet/kapsama garantisine indirgenmez. Response byte
muhasebesinde bir chunk'ın tamamı limit geçişinden önce sayılabilir; retained
body ve aggregate limitler tam wire-byte tavanı olarak sunulmaz. Planner bu
bileşimlerin çalışma zamanı kabulünü yapmaz.

Exact-origin scheme/host/etkin port sınırıdır (`http_evidence/policy.rs:42–92`).
Native discovery query/fragment'i kaldırır (`web_assessment/discovery.rs:45–68`);
planner bu girdiyi değiştirmeden uyumsuz bildirir. Root GET ve subject GET/HEAD
`web_assessment.rs:757–795,3152` kaynaklıdır. OPTIONS genel HTTP probe modelinde
vardır; bu ilk assessment alt kümesine taşınmaz.

Okunamayan bir pinlenmiş dosya veya hash/commit farkı `source_version_mismatch`
ile üretimi durdurur. İncelenmeyen diğer yetenekler için destek varsayılmaz.
Runtime/binary qualification ve hostile-input kabulü açık kalır.
