# Phase43 minimum veri açıklama sınırı

**OFFLINE DEMONSTRATION — PORTABLE TASK REQUEST ONLY — NO TASK DISPATCH OR RESPONSE AUTHORIZED**

Portable talep, alıcının hangi bekleyen görevin hangi mevcut bağla tanımlandığını ve gelecekteki yanıt alanlarının adlarını okuyabilmesi için tasarlanır. Phase42'nin bütün kaynak metadata'sını başka ortama taşımaz. Bu bir minimizasyon sınırıdır; anonimleştirme veya şifreleme garantisi değildir. Task/reference/candidate/file kimlikleri ve digest değerleri de hassas olabilir.

## Taşınan veri

Yalnız açıkça seçilmiş ve gerçek kaynakta hâlâ yanıtsız görevlerin şu on alanı aktarılır:

| Alan | Aktarım amacı |
| --- | --- |
| task_id | Original takip işini tanımak |
| reference_id | Bu görevin mevcut reference bağı |
| candidate_id | Bu görevin mevcut candidate bağı |
| file_id | Bu görevin mevcut metadata File ID bağı |
| binding_digest | Kaynakta kayıtlı inherited binding'i eşit korumak |
| slot_status | awaiting_external_response durumunu korumak |
| response_status | unsubmitted durumunu korumak |
| candidate_present | false durumunu korumak |
| observation_verified | false durumunu korumak |
| task_completed | false durumunu korumak |

Envelope, güncel Phase42 register/manifest kimliklerini, bounded yerel request reference'ı, ortak demo/trust/sınırlama alanlarını ve altı sayacı ayrıca taşır. Kapalı şema unknown alanı reddeder. Request1–8 unique task seçer; kaynakta olmayan veya uygun olmayan tek seçim bütün request'i reddeder. Yeniden numaralama ya da seçilmemiş görevi ekleme yoktur.

Future response contract yalnız yedi alanın tür tanımıdır; `source_locator_description:string` alan adının bulunması source locator değeri taşındığı anlamına gelmez. Doldurulmuş response, örnek gözlem, analist kimliği veya sahte yanıt üretilmez. Gerekli source locator ayrıca yetkili insan tarafından sağlanmalıdır; Phase43 dosya toplamayı, gözlem yapmayı veya yanıt göndermeyi başlatmaz.

## Taşınmayan veri ve full packet gerekçesi

Phase42 aynı reference packet içinde present ve missing projection'ları birlikte tutabilir. Yalnız task için bir projection'ı kesip full packet gibi sunmak bağlamı yanlış gösterebilir; bütün packet'ı kopyalamak ise seçilmemiş present metadata'yı gereksiz açıklar. Phase43 packet/projection yerine görevdeki minimum bağı taşır; kaynak grubu üretici tarafında salt okunur korunur.

Portable capsule içinde şu veriler bulunmaz:

- Full reference_packets koleksiyonu veya projection listesi; exported packet/projection sayısı0.
- Seçilmemiş görevler ve present CAND0001 kaydının olumlu metadata'sı.
- observed_byte_size/observed_sha256 gibi hedef source gözlem detayları; Phase31 observation/comparison metadata'sı.
- Ham kaynak dosyası, Rust kodu, candidate payload veya doldurulmuş response.
- Source locator değeri, yerel mutlak path, kullanıcı adı/SID veya gerçek müşteri bilgisi.
- Credential/token/API key, raw exception/stack trace veya analist kimliği/atama/onay kaydı.

Kapalı envelope/response sözleşmesi ve exact dört ZIP üyesi ek dosya/alanla genişletilemez. Reader extraction veya başka path açma yapmaz; JSON içindeki bir değeri URL/path olarak izlemez. Bu sınır, kaynak artefact'ın kriptografik kaynağını veya task kimliklerinin fiziksel dosya kimliği olduğunu kanıtlamaz.

## Dış receipt ile iç talebin farkı

Portable ZIP yalnız task-request.json, response-contract.json, README.txt, capsule-manifest.json taşır. Dış source receipt, üretici incelemesi için gerçek beş Phase42 dosyasının byte/SHA256/şema kimliklerini ve altı sayım kapsamını taşır; kaynak gövdelerini veya gözlenen hedef dosya içeriğini taşımaz. Dış receipt/index/summary/manifest portable capsule'a eklenmez.

Kaynak paydalarının register_counts/classification_counts/slots_counts/template_counts/queue_counts/handoff_counts olması farklı kapsamları korur. Parent file/candidate2 sayıları burada source provenance'dır; portable request'e present candidate metadata'sı eklemek için gerekçe değildir. Bir yanıt tanımı bütün paket için ortak7'dir; task sayısıyla çarpılmaz. Submitted response, verified observation ve completed task sayıları integer0 kalır.

## Korunan anlamlar

`candidate_present=false` bir response sağlanmadığını korur; kaynakta candidate_response=null'dır, portable task'ta candidate_response alanı yoktur. False, null, integer0 ve missing/unknown farklı anlamlardır. Kaynakta missing olarak kayıtlı bir gözlem, dosyanın güncel fiziksel yokluğunu kanıtlamaz.

Inherited binding_digest kaynaktan eşit kopyalanır; current Phase42 veya parent Phase41 hash'iyle yeniden üretilmez. Orijinal Phase40 preimage'ı portable wire'da yoktur. Task binding eşliği producer authentication, gerçek görev sahipliği, source observation veya authorization değildir. Hash'ler imza/attestation yerine geçmez; tutarlı değişiklikler yeniden hash'lenebilir. Exact18 nested trust flag false ve demo_only=true korunur;17 workflow flag mirası uydurulmaz.

Gerçek ikinci host aktarımı, dispatch, analist alımı/atama, recipient auth, source reobservation/evidence collection, future response/decoder/ingestion ve task acceptance/completion **NOT_RUN** kalır. Kullanımın runtime kaydı [DEMO_DELIVERY](DEMO_DELIVERY.tr.md), kapalı alanlar [TASK_EXCHANGE_CONTRACT](TASK_EXCHANGE_CONTRACT.tr.md) belgesindedir.
