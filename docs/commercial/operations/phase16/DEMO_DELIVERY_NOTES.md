# Phase16 demo üretim ve inceleme kaydı

**Demonstration only — No real system assessed.**

Durum: **yalnız mevcut dört incelenmemiş kayıtla gerçek offline demo üretimi yapıldı**. Workspace kökünde Python **3.14.7** ile aşağıdaki yeni builder komutu çalıştırıldı; exit code **0**. Üç taslak ve manifest gerçekten oluştu. Dosyalar kaynak/metin olarak manuel okundu; boyut/SHA256 değerleri mevcut byte'lardan salt okunur ölçüldü. Bu, native Termivar çalıştırması, otomatik test veya gerçek müşteri/güvenlik kabulü değildir.

## Kullanılan mevcut kaynaklar

Yeni [demo_input.json](../../../../tools/commercial_handoff/examples/demo_input.json), Phase15 `DEMO-TERMIVAR-015` dahili demo dosyasının dört kaynak bağlantısı ve ayrı insan durumlarından elle hazırlanmış yapıdır. Bu kimlik gerçek run/müşteri kimliği değildir. Native JSON kopyası veya kaynak şeması migration'ı değildir.

Tek source artifact **ART-A1**: korunmuş [assessment.json](../../examples/assessment.json), `venom-rendered-assessment/v1`, 3907 byte, SHA256 `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9`. Kaynak `web-review`, `complete`, 1 subject/4 item bildirir; dört native disposition `informational` ve claim basis `observation`dır. Complete kapsamın eksiksizliği veya güvenlik kararı değildir.

| Dahili observation ID | Gerçek native fingerprint | JSON pointer |
| --- | --- | --- |
| `OBS-01` | `sha256:32adc97266dff2c8c11116f202bc894adcab02b7a9f1c315f988f1878bd10004` | `/items/0` |
| `OBS-02` | `sha256:423a41c26f6479fa1d15e672819aea23926e3dee76902559fe92cbc564ddf53a` | `/items/1` |
| `OBS-03` | `sha256:e0e9548ae2581d2522aac9b1cdce9ade61e4010d02308c716f252a15cbb7addb` | `/items/2` |
| `OBS-04` | `sha256:fa8c2374a132316b67a492e8ab213f26b389c9fecefcdf39685026c75fde46f2` | `/items/3` |

Native fingerprint ile tam dosya SHA256'sı farklı kimliklerdir. Bu eşleme dosya/ledger okunarak hazırlanmıştır; builder kaynak dosyayı takip ederek yeniden doğrulamaz. [Phase14 provenance](../../examples/README.tr.md), [Phase15 case index](../examples/DEMO_CASE_INDEX.md), [ledger](../examples/DEMO_OBSERVATION_LEDGER.md) ve [bekleyen kararlar](../examples/DEMO_REVIEW_DECISIONS.md) korunur. Phase15 belge baseline'ı `bcf8a94f60129aacaa21e90c56e74747a8ea2222`; Termivar pin'i `6a2639348c2366d0bf71b9a34e5484d40aa393a3`. Tarihsel alpha.2 örneği yeni alpha.3 source kabulü olarak anlatılmaz.

## Modele dahil edilmeyen kaynaklar

| Kaynak | Neden dahil edilmedi? |
| --- | --- |
| ART-A2 manifest | A1 için kısmi JSON-entry ilişkisidir; HTML sağlanmadığından tam bundle doğrulaması değildir. Bu builder native verifier değildir ve A2'yi okumaz |
| ART-C1/C2/C3 comparison/before/after | Bağımsız sentetik document-processing kümesi; A1'in retest'i değildir. Yeni comparison üretilmez, değişim veya remediation sonucu türetilmez |
| ART-D1 incomplete diagnostic | Phase11 hand-authored fixture; CLI çıktısı veya A1'in devamı değildir. Bu modele birleştirilmez; unavailable item projection sıfır bulgu yapılmaz |
| Ham HTTP/target/credential/evidence payload | Demo girdisine alınmadı; opaque evidence bağlantısı ham kanıt veya erişim izni değildir |

## Dört observation neden müşteri bulgusu olmadı?

Her kayıtta `review_status=unreviewed`, `scope_status=unknown`, `client_inclusion=pending_decision`, `safe_summary=null`, `decision_ref=null`; `review_decisions=[]`. Gerçek uzman/karar zamanı uydurulmadı. Kaynak informational değeri, insan `informational_only` kararı değildir. Internal çıktı dört observation'ı bu durumlarla korudu; dördü için de seçim `false` oldu.

Her observation'ın beş seçim engeli görünür: `decision_reference_missing`, `scope_not_in_scope`, `client_inclusion_not_selected`, `review_status_not_eligible`, `safe_summary_missing`. Markdown dinamik metinlerindeki noktalama, referans ve kodlar numeric entity olarak yazılır; okunur sunumda kaynak değer korunur. Bu encoding ham içeriği redakte etmez veya insan incelemesi oluşturmaz.

İki müşteri biçiminde de gerçek açıklama: **“Bu taslakta müşteri raporuna dahil edilmesi kararlaştırılmış bir bulgu bulunmamaktadır. Bu durum değerlendirmede güvenlik açığı olmadığı anlamına gelmez.”** Bu, “0 vulnerability”, “No security findings”, “Clean assessment” veya “Assessment passed” sonucu değildir. Seçilmiş öğe ayrıntısı ve seçilmiş source referansı yoktur; kaynakta gözlem bulunmadığı anlamına gelmez. İç fingerprint/pointer/capability listeleri, provenance notu, kanıt sınırlamaları ve karar gerekçeleri müşteri çıktısına kopyalanmadı.

## Gerçek tek üretim komutu ve dosyalar

Workspace kökünden, yeni ve henüz bulunmayan `outputs/phase16-demo` yolu için:

```text
python -I -B security-platform/tools/commercial_handoff/assemble.py --input security-platform/tools/commercial_handoff/examples/demo_input.json --output-dir outputs/phase16-demo
```

Bu yalnız yeni offline builder komutudur; native Termivar CLI/test/scanner değildir. Exit code `0`; stdout sabit dosya adlarıyla `Created demo-only drafts: ...` ve `release_authorized=false; human_review_verified=false; client delivery is not authorized` bildirdi. Önceden var olan çıktı dizini üzerine yeniden üretim yapılmadı veya dizin silinmedi. Aynı yol ile yeniden çalıştırma yapılmadı; tekrarlı determinizm kabulü yoktur.

Gerçek girdi: `security-platform/tools/commercial_handoff/examples/demo_input.json`, **5286 byte**, SHA256 **`aae034bdc56edb10bd358d19578978462f5ce56a844d1bce4562ac5eed9d7247`**. Girdi üretimden sonra değiştirilmedi.

| Gerçek dosya | Byte | SHA256 |
| --- | ---: | --- |
| `outputs/phase16-demo/internal-review-summary.md` | 11728 | `8a3017136c94713147bf65aa659c2119d447474dd081363989c3495ec45d2f22` |
| `outputs/phase16-demo/client-handoff-draft.md` | 3506 | `4e82aaecee1b8efe4273e79f0ef570bbf8b93fc02497dfa362afd9851480f95e` |
| `outputs/phase16-demo/client-handoff-draft.html` | 4905 | `19bb1a0a3870507448696298e1e7805276ac32165265e5e4c6a77b7a6a78dd77` |
| `outputs/phase16-demo/manifest.json` | 1575 | `a88bc455fad514e0058c7dfc8fe7db7413ac5d4dc04f089f0ae261c3cb5c44cd` |

Manifest `termivar-handoff-output-manifest/v1` sözleşmesini, gerçek giriş hash/uzunluğunu ve üç çıktı hash/uzunluğunu taşır; kendi dosyasını hash listesine dahil etmez. Yukarıdaki manifest hash'i ayrıca gerçek dosya byte'larından ölçülmüştür. `demo_only=true`, `release_authorized=false`, `human_review_verified=false`; altı açık teslim blocker'ı `demo_only_not_for_delivery`, `human_review_not_verified`, `release_not_authorized`, `authorization_not_verified`, `delivery_constraints_unresolved`, `observation_selection_blocked`. Bunlar yetki veya onay sonucu değildir.

## İnceleme ile çalıştırılmayan kabulün ayrımı

| Konu | Gerçekten yapılan / açık kalan |
| --- | --- |
| A1 kaynak kimliği / dört pointer-fingerprint / Phase15 durumlarının okunması | Salt okunur belge/kaynak incelemesi yapıldı; uzman güvenlik incelemesi değil |
| Yeni girişin exact alanlarının `schema.py` ile eşlemesi | Manuel kaynak incelemesi; mevcut demo girdisi başarılı gerçek üretimde loader/schema yolundan geçti. Geçersiz girdilerin reddi yürütülmüş sayılmaz |
| Internal'da dört observation ve açık engellerin görünmesi | Gerçek çıktı metni okundu: dört kayıt, kaynak bağları, `unreviewed` / `unknown` / `pending_decision`, her biri seçim `false` ve beş engel |
| Client MD/HTML'de aynı model ve görünür sabit demo etiketi | Kaynak/metin olarak okundu: **DEMONSTRATION ONLY — NOT APPROVED FOR CLIENT DELIVERY**, no-selected-but-not-clean açıklaması; iç öğe/provenance/kanıt notları aktarılmadı |
| Statik HTML sınırı | Üretilmiş kaynak okundu: script veya dış CSS/font/CDN/görsel kaynağı yok; browser'da render kabulü `not_run` |
| Gerçek giriş/çıktı byte SHA256 manifesti | Dosya boyut/hash'leri salt okunur ölçüldü; manifestin giriş ve üç çıktı kayıtlarıyla eşleşti. İmza veya üretici kimliği kanıtı değil |
| Pozitif inclusion dalı ve hostile metin encoding davranışı | `not_run`; mevcut demo `safe_summary=null` ve karar listesi boş olduğu için bu dalları yürütmedi |
| Aynı girişten tekrarlı çıktı/determinizm | `not_run`; yalnız tek yeni çıktı dizinine üretim yapıldı |
| Geçersiz şema/tür/UTF-8/duplicate/limit hataları | `not_run`; kodda kontrol bulunması yürütülmüş hata kabulü değildir |
| Symlink/reparse, filesystem yarışı, permission/disk/staging hata yolları | `not_run`; OS güvenlik kabulü yapılmadı |
| Otomatik test/runner/coverage/native CLI/scanner | `not_run`; bu fazda yasak ve başlatılmadı |

Gerçek müşteri yetkisi/kapsamı, uzman incelemesi, veri erişimi–paylaşımı–saklama kararları, güvenlik testleri ve teslim onayı açık kalır. Çıktı üretilse dahi `demo_only=true`, `release_authorized=false`, `human_review_verified=false` kalmalıdır. Kaynak/doküman/hash incelemesi pilot GO veya müşteri kabulü değildir. Bu faz bitince başka ürün, test laboratuvarı veya canlı faaliyet kendiliğinden açılmaz.
