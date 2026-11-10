# termivar-handoff-draft/v1 — tam giriş sözleşmesi

Yetkili tanım [schema.py](../../../../tools/commercial_handoff/schema.py) içindeki `validate` ve frozen DTO'lardır. Bu belge yeni araç girişini açıklar; Termivar'ın native sözleşmesini veya Phase15 Markdown alanlarını değiştirmez. `schema_version` sayısal `1` değil, tam **`termivar-handoff-draft/v1` string'i**dir.

## JSON ve toplam sınırlar

Tek girdi dosyası **1–262144 byte (256 KiB)** ve uzantısı case-insensitive `.json`; strict UTF-8, BOM yok. Duplicate object key, geçersiz Unicode, ondalık/üstel sayısal literal ve NaN/Infinity kabul edilmez. Integer literal uzunluğu eksi işareti dahil en fazla 20 karakterdir; JSON sayısı gereken tek alan `byte_length` için gerçek `int` gerekir, boolean sayı sayılmaz. Maksimum yapı derinliği 12, key'ler dahil toplam node 10000, bütün key ve value string'lerinin toplam UTF-8 metin bütçesi 131072 byte (128 KiB). Loader tek parsed string için önce 8192 karakter sınırı uygular; şemanın alan limitleri daha dardır. Derinlik ön kontrolü string içindeki bracket karakterlerini yapı olarak saymaz. Yerel dizi/metin sınırları bunlara ek uygulanır; küçük dosya olmak tümünü sağlamak değildir.

Her object **tam** alan kümesini ister: bilinmeyen veya eksik key reddedilir. `null` kabul eden alanın key'i de zorunludur. Boş/yalnız whitespace string reddedilir; `null`, `""` veya `"not_provided"` birbirinin yerine otomatik çevrilmez. String değerler sessizce trim edilmez. Metinler UTF-8 encode edilebilir olmalı; C0 kontrolleri (`\n`, `\r`, `\t` hariç), DEL ve C1 kontrolleri reddedilir. Alan metin limitleri Python karakter sayısıdır; toplam metin bütçesi UTF-8 byte sayısıdır.

## Ortak değer türleri

| Tür | Kesin biçim |
| --- | --- |
| Kimlik | `[A-Za-z0-9][A-Za-z0-9_-]{0,63}`; en fazla 64 ASCII karakter |
| Dosya SHA256 | Tam 64 lowercase hex karakter; `sha256:` prefix'i yok |
| Kaynak observation fingerprint | `sha256:` + tam 64 lowercase hex karakter |
| Kaynak pointer | `/items/(0\|[1-9][0-9]{0,3})`; örneğin `/items/0`; leading zero, negatif indeks veya keyfî path yok |
| Genel metin | 1–2048 karakter; boş/yalnız whitespace olmaz |
| `review_status` | `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery` |
| `client_inclusion` | `pending_decision`, `include_with_limits`, `exclude_with_reason` |
| `scope_status` | `in_scope`, `out_of_scope`, `unknown` |
| `source_disposition` | `informational`, `needs_review`, `confirmed`; kaynak etiketi, bağımsız doğrulama değil |

## Kök object — dokuz zorunlu alan

| Alan | Tür / sınır | Anlam |
| --- | --- | --- |
| `schema_version` | Sabit string `termivar-handoff-draft/v1` | Bu araç sözleşmesi |
| `case_id` | Kimlik | Dahili dosya kimliği; native run veya müşteri yetkisi değil |
| `mode` | Yalnız `demo` | Gerçek müşteri/production modu yok |
| `scope_summary` | Metin, en fazla 1024 karakter | İnsan tarafından sağlanan kapsam açıklaması; yetki kanıtı veya otomatik redaksiyon sonucu değil |
| `authorization_status` | `not_provided`, `not_verified`, `pending_decision` | Hiçbiri çalışma/teslim izni vermez |
| `source_artifacts` | 0–32 source object | Önceden kayıtlı kaynak metadata'sı |
| `observations` | 0–256 observation object | Kaynak gözlem ile ayrı insan durumları |
| `review_decisions` | 0–256 decision object | Varsa insan kararı beyanları; kimlik/gerçeklik doğrulaması yok |
| `delivery_constraints` | 1–32 string; her biri en fazla 1024 karakter | Açık teslim sınırları; serbest metin insan kontrolü ister |

## Source object — altı zorunlu alan

| Alan | Tür / sınır |
| --- | --- |
| `artifact_id` | Kimlik; source listesi içinde benzersiz |
| `contract` | `venom-rendered-assessment/v1`, `termivar-report-bundle/v1`, `termivar-report-comparison/v1`, `web-assessment/v2` |
| `sha256` | Dosya SHA256 |
| `byte_length` | Strict `int`, 1–16777216 (16 MiB); `true`, float veya numeric string kabul edilmez |
| `completion_status` | `complete`, `incomplete`, `failed`, `not_provided` |
| `provenance_note` | Genel metin, en fazla 2048 karakter |

Bu kayıt native dosyanın içeriği değildir. Builder dosyayı açmaz, hash'i kaynakla yeniden karşılaştırmaz, contract/status veya provenance doğruluğunu bağımsız kanıtlamaz. Farklı contract adlarının metadata olarak kabul edilmesi, comparison veya diagnostic içeriğinin assessment'a çevrildiği anlamına gelmez.

## Observation object — on iki zorunlu alan

| Alan | Tür / sınır | Eksik bilgi gösterimi |
| --- | --- | --- |
| `observation_id` | Kimlik; observation listesinde benzersiz | Zorunlu; demo `OBS-01..04` dahili sıra etiketleri |
| `source_artifact` | Kimlik veya `null` | `null` bilinmeyen kaynak bağlantısı; sessiz müşteri sonucu oluşturmaz |
| `observation_ref` | Kaynak fingerprint veya `null` | `null` referans eksikliği; native fingerprint uydurulmaz |
| `source_json_pointer` | Kaynak pointer veya `null` | `null` konum eksikliği; dosya okumak için kullanılmaz |
| `capability_id` | 1–128 karakter, `[A-Za-z0-9._@-]+` | Native kaynaktan aktarılır; dosya/URL değildir |
| `source_disposition` | Yukarıdaki üç native etiket | Bilinmeyen değer için yeni kategori oluşturulmaz; girdi reddedilir |
| `review_status` | Altılı insan belge sözlüğü | Yapılmamış review için `unreviewed` |
| `scope_status` | Üçlü kapsam sözlüğü | Kapsam bilinmiyorsa `unknown` |
| `client_inclusion` | Üçlü inclusion sözlüğü | Karar yoksa `pending_decision` |
| `safe_summary` | Genel metin (en fazla 2048) veya `null` | Hazırlanmış/gözden geçirilmiş müşteri özeti yoksa `null`; native title/summary otomatik kopyalanmaz |
| `evidence_limitations` | Genel metin, en fazla 2048 | Sağlanmayan/incelenmeyen kanıtı açıklar; raw HTTP/payload alanı değildir |
| `decision_ref` | Kimlik veya `null` | Gerçek karar kaydı yoksa `null` |

Nullable kaynak/karar alanı, şemanın bilinmeyeni temsil etmesini sağlar; review kurallarından veya müşteri seçimi koşullarından muafiyet değildir. Formatı doğru referansın kaynakta gerçekten bulunması ayrı kanıt konusudur. Eksik/uyumsuz bağ internal engel olarak korunur, müşteri bulgusuna sessizce yükseltilmez.

## Decision object — yedi zorunlu alan

| Alan | Tür / sınır |
| --- | --- |
| `decision_id` | Kimlik; decision listesinde benzersiz |
| `observation_id` | Kimlik; hedef observation referansı |
| `review_status` | Altılı insan belge sözlüğü |
| `client_inclusion` | Üçlü inclusion sözlüğü |
| `reviewer_ref` | Metin, 1–128 karakter veya `null`; insan kimliği doğrulanmaz |
| `reviewed_at` | `null` veya geçerli takvim tarihi içeren tam UTC `YYYY-MM-DDTHH:MM:SSZ` (20 karakter); kesir veya offset biçimi yok |
| `reason` | Genel metin, en fazla 2048 karakter; internal gerekçe |

Observation ve decision beyanlarının tutarlılığı ayrıca review kurallarınca ele alınır. Doldurulmuş isim/tarih incelemenin gerçekten yapıldığını kanıtlamaz. `include_with_limits` tek başına yeterli değildir; source/ref, kapsam, review, karar ve güvenli özet koşulları birlikte değerlendirilir. Çıktı her durumda demo taslağıdır; araç release veya GO vermez.

## Müşteri seçimi — ayrı semantik katman

Bir kayıt yalnız bütün bu koşullar birlikte sağlanırsa taslağa seçilebilir: kayıtlı kaynak `venom-rendered-assessment/v1` ve `complete`; fingerprint/pointer mevcut; aynı beyan edilmiş source byte SHA256 + fingerprint + pointer başka observation ile tekrarlanmamış; `scope_status=in_scope`; `client_inclusion=include_with_limits`; insan durumu `informational_only` veya `reviewed_for_delivery`; `safe_summary` mevcut; `decision_ref` mevcut karara bağlı; karar aynı observation, review ve inclusion değerlerini bildiriyor; reviewer referansı ile UTC zaman sağlanmış.

`reviewer_ref` içindeki `null` veya trim/case-insensitive `not_provided`, `not_verified`, `pending_decision`, `not_assigned` değerleri eksik reviewer sayılır. Bunların dışındaki metni kabul etmek kimlik doğrulaması değildir. Bilinmeyen observation'a bağlı veya hiçbir observation'ın karar referansına bağlanmayan kararlar internal blocker olarak görünür. Kaynak alias'ları aynı byte hash/fingerprint/pointer'a bağlanıyorsa tekrar kimliğiyle ele alınır. Bunlar beyan tutarlılığı kontrolleridir; kaynak byte'ları yeniden açılmaz veya karşılaştırma motoru çalıştırılmaz.

Müşteri modelinin tam alan listesi: üst düzey `case_id`, `scope_summary`, `selected_items`, `source_references`, `incomplete_review`; sonuncusu gerçek review doğrulanamadığı için **daima true**. Her seçilmiş öğede yalnız `observation_id`, `safe_summary`, `source_disposition`, `review_status`, `source_artifact_id`, `observation_ref`, `source_json_pointer` bulunur. Yalnız seçilen öğelere bağlı source referanslarında `artifact_id`, `contract`, `sha256`, `byte_length`, `completion_status` bulunur. Internal `reason`, `evidence_limitations`, `provenance_note`, reviewer ve zaman bu client modeline kopyalanmaz. Kayıt seçilmezse ona bağlı source metadata'sı da client referans listesine alınmaz; bu kaynakta gözlem olmadığı anlamına gelmez.

Bu pozitif seçim dalı mevcut dört incelenmemiş demo ile yürütülmüş sayılmaz; kabulü `not_run`dur. Seçilmiş kayıt olsa bile sabit demo/yetki engelleri ve açık teslim kısıtları devam eder.

## Explicit dosya yolu sözleşmesi

`--input` ve `--output-dir` JSON alanı değildir. Her biri 1–512 karakter, çalışma dizinine göre açık göreli yoldur. Mutlak/drive/UNC kökü, NUL, boş path bileşeni, `.`/`..`, sonu boşluk/nokta olan bileşen, `< > : " \| ? *` karakterleri, C0 kontrolleri ve Windows reserved device adları (`CON`, `PRN`, `AUX`, `NUL`, `COM1..9`, `LPT1..9`, uzantı verilse de) reddedilir. Slash ve backslash bileşen ayrımı için ele alınır; `:` reddi ADS yolunu da kapsar.

Mevcut input regular dosya olmalı; çalışma dizini, input ancestry ve output üst dizini symlink/reparse kontrollerinden geçmelidir. Output üst dizini mevcut olmalı, output dizini **hiç bulunmamalıdır**; mevcut boş dizin de reddedilir. JSON içindeki hiçbir path/URL veya source referansı bu dosya yollarını değiştirmez. Bu kontrollerin kaynakta bulunması filesystem race veya OS izin kabulü değildir.

## Phase15 eşlemesi ve demo

| Phase15 kaydı | Yeni giriş alanı |
| --- | --- |
| Case kimliği | `case_id=DEMO-TERMIVAR-015`; gerçek run değil |
| ART-A1 dosya byte kimliği | `source_artifacts[0]`: `artifact_id`, gerçek `contract`, SHA256 ve 3907 byte |
| Dahili OBS sıra etiketi | `observation_id`; native kimlik yerine geçmez |
| Fingerprint + JSON pointer | Ayrı `observation_ref` ve `source_json_pointer`; ART-A1 tam dosya hash'iyle birlikte izlenir |
| Native disposition | `source_disposition=informational`; insan review değeri değildir |
| İnsan durumu / kapsam / dahil etme | Dört kayıtta `unreviewed` / `unknown` / `pending_decision` |
| Hazırlanmamış güvenli özet / karar | `safe_summary=null`, `decision_ref=null` |
| Gerçek karar / reviewer / zaman yok | `review_decisions=[]`; `not_provided` kişisi veya uydurma tarih eklenmez |
| Eksik kanıt | `evidence_limitations`; ham evidence içerikleri kopyalanmaz |

[Demo girdisi](../../../../tools/commercial_handoff/examples/demo_input.json) yalnız ART-A1 metadata'sını içerir. A2 manifesti, ayrı C karşılaştırması ve D hand-authored incomplete fixture bu modele birleştirilmez; [demo notları](DEMO_DELIVERY_NOTES.md) dışarıda bırakma nedenlerini açıklar. Phase15'in [ledger'i](../examples/DEMO_OBSERVATION_LEDGER.md), [karar kayıtları](../examples/DEMO_REVIEW_DECISIONS.md) ve eski native JSON değiştirilmez. Phase14'ün farklı insan sözlüğü için migration yapılmaz.
