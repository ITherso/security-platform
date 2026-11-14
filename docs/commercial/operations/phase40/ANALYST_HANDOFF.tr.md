# Phase40 — Analist handoff kullanımı

**OFFLINE DEMONSTRATION — RECORDED MISSING EVIDENCE FOLLOW-UP ONLY — NO OBSERVATION OR ASSIGNMENT AUTHORIZED**

Handoff, kayıtlı missing source metadata'sını daha sonra insanın değerlendirebileceği açık bir talep bağlamına taşır. Gerçek analist kimliği, assignee, iletişim adresi, onay veya veri toplama yetkisi içermez. Araç talebi göndermez; atamaz, kabul etmez, tamamlamaz veya yeni observation kaydetmez.

## Okuma sırası

1. Demo banner'ını ve current Phase39 WITNESSES/manifest kimliklerini kontrol et. Bunlar eski Phase38 pinleri veya Phase39 QUERY kimliği değildir.
2. Yerel request_reference ve canonical queue_sha256 bağını oku. Hash, queue JSON byte kimliğidir; üretici imzası veya güvenilir kaynak attestation'ı değildir.
3. Her task'ın reference/candidate/file üçlüsünü supporting_projection_bindings ve ilgili missing projection ile karşılaştır. Task ID F0001 gibi yerel sıra etiketidir.
4. `prepared_unassigned` ve `not_observed` durumlarının açık talep anlamını koru. Kaynakta missing olması bugünkü fiziksel yokluk değildir.
5. Referansın bütün izinli paketini oku. Present projection da aynı bağlamın parçasıdır; yalnız missing satırları ayırarak reference proof oluşturma.
6. Kaynak sayımı, queue sayımı ve handoff sayımının farklı kapsamlarını ayır. İnsan kabulü veya yeniden observation için bu araç dışında açık ve gerçek sorumluluk gerekir; ürün bunu sağladığını iddia etmez.

## Tam paket ve görev ilişkisi

`build_analyst_handoff(validated_queue)` exact immutable queue'dan kapalı model üretir. Handoff_tasks queue'nun bütün işlerini aynı ID/reference/candidate/file/presence/kind/status/fulfillment ile taşır. Reference_packets yalnız bu işlerin referanslarını içerir; her biri source witness'ın tam beş alanını ve bütün 11-alan projection listesini özgün sıra ve türlerle korur.

İşi olmayan selected referans queue'da bulunabilir; handoff'a kopyalanmaz. Bu nedenle handoff yedi sayımı queue sayımlarından kör kopyalanmaz; kendi full packet/task listelerinden yeniden türetilir. Pending task benzersiz task bağıdır; distinct file/candidate bütün handoff projection paketlerinden sayılır. Task yoksa handoff listeleri ve sayımları sıfırdır. Sıfır task yeni fiziksel gözlem veya bütün kaynakların eksiksizliği değildir.

Missing projection'ın gerçek supporting triple'ı yoksa bütün request reddedilir. Sonradan candidate, path veya observation türetilmez; ambiguous/duplicate/çelişkili bağ sessiz seçilmez. Aynı File ID ayrı gerçek reference bağlarında bağlamını korur. Null observed_byte_size/observed_sha256 sıfır-byte dosya veya boş digest değildir.

## Ürün eyleminin sınırı

| Kayıt | Anlamı |
| --- | --- |
| request_fresh_source_observation | İleride değerlendirilecek source gözlem talebi |
| prepared_unassigned | Yerel talep hazırlanmış; gerçek atama yapılmamış |
| not_observed | Yeni gözlem ve fulfilment yok |
| recorded_source_file_presence=missing | Önceden kaynakta kayıtlı metadata durumu |
| queue_sha256 | Canonical queue JSON byte ilişkisi |

Talebin varlığı collection authorization, insan görev kabulü, source freshness, ownership, compiler/module closure, güvenlik veya release kararı üretmez. Human/legal/customer/production/release alanları ve diğer exact 18 nested trust flag false kalır; demo_only true'dur. Gerçek analist kabulü, kaynak yeniden gözlemi, dosya toplama, ikinci host ve hostile/adversarial akışlar NOT_RUN'dır.

Handoff/Markdown yerel okunabilir sentetik çıktı artefact'larıdır. Kimlik/hash hassas olabilir; dosyayı başka kişiye göndermek bu araç tarafından yapılmaz. Minimizasyon anonimlik/şifreleme garantisi değildir. [Sözleşme](FOLLOWUP_QUEUE_CONTRACT.tr.md), [disclosure/trust](DISCLOSURE_AND_TRUST.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).
