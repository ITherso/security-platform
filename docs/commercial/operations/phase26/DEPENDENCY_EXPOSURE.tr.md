# Dependency exposure ve belirsiz closure

**DEMONSTRATION ONLY — PILOT VARIANT ANALYSIS — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Sözleşme](VARIANT_CONTRACT.tr.md), [lisans/readiness](LICENSE_AND_READINESS.tr.md),
[güven sınırı](TRUST_BOUNDARY.tr.md).

Exposure mevcut kaynak metadata'sının varyantla ilişkisini açıklar. Gerçek build
inclusion, feature aktivasyonu, transitive graph, runtime gereksinimi veya paket
içeriği değildir. Her özgün D kaydı bir kez korunur; declaration ve lock ayrı
kalır. Global 451 kaynak satırı benzersiz yayınlanmış paket sayısı değildir.

Altı sınıf birbirinden ayrıdır:

| Sınıf | Sınırlı anlamı |
| --- | --- |
| `explicit_component_link` | Kaynak sözleşmesinde gerçek dependency–component bağı |
| `declared_source_scope` | Seçilen tek potansiyel component'in kaynak kapsamındaki deklarasyon |
| `shared_or_ambiguous_scope` | Birden fazla component'e potansiyel kaynak ilişkisi; ayrım kesin değil |
| `unattributed_record` | Seçili component'e ilişki kurmaya yetecek metadata bulunmuyor |
| `excluded_context_record` | Eski kaynak gerçekten excluded backend-context bildiriyor |
| `insufficient_dependency_evidence` | Mevcut model kapsam/ilişki belirlemeye yetmiyor |

Phase24 v1 explicit dependency–component owner bağı taşımadığından ilk sınıf
kendiliğinden doldurulmaz. Aynı repository, paket adı, manifestin varlığı veya
F referansı explicit owner bağı değildir.

Sınırlı potansiyel ilişki şöyle türetilir: dependency'nin gerçek manifest id'si,
manifest root/path metadata'sı üzerinden mevcut inventory F referansına
bağlanır. Bu F'nin hangi component `source_file_refs` listelerinde bulunduğu
korunur. İlişki yalnız seçilmiş kaynak dosya kapsamıdır; manifest veya dependency
kaynağındaki path/URL takip edilmez.

Excluded backend-context sınıfı, F'nin helper kayıtlarında görünmesinden önce
uygulanır. Diğer kayıtlarda bir seçilmiş potansiyel component ve toplam tek
potansiyel component varsa declared source scope; toplam birden fazlaysa shared/
ambiguous scope kullanılır. Seçilmiş potansiyel ilişki yoksa kayıt unattributed
kalır. Eksik manifest/F referansı başarılı boş ilişki sayılmaz, kapalı hatadır.
Mevcut tam eski sözleşmeler için insufficient sınıfının boş olması mümkündür.

Cargo.lock'ın bütün workspace satırları belirli executable'ın dependency
closure'ı değildir. Source türü `unknown`, eksik sürüm ve belirlenemeyen
directness korunur. Yerel/path veya source alanının yokluğu workspace üyeliği,
üretici veya first-party sahiplik kanıtına yükseltilmez.

Her varyant için altı sınıfın ayrık üyelik toplamı global dependency kayıt
sayısına eşit olmalıdır. Bir kaynak satırı birden fazla varyantta görünse de
global envanterde çoğaltılmaz. Varyant toplamı, global benzersiz D ref sayısı,
declaration/lock satır sayısı ve unique package kavramları ayrı tutulur.

İki varyantın exposure sayımları aynı kalabilir. B'ye sekiz helper eklenmesi,
belirli transitive dependency'lerin kesin eklendiğini kanıtlamaz. A'da helper
seçilmemesi de belirli yükümlülüklerin veya gerçek runtime dependency'lerinin
ortadan kalktığını göstermez. Excluded context, hiçbir gerçek dağıtımda
gerekmeyecek anlamına gelmez. Belirsiz ilişki kesin yokluğa çevrilmez.
