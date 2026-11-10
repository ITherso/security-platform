# Gözlem inceleme ve teslim kararı politikası

Bu belge elle yürütülecek kayıt disiplinini tanımlar; uzman incelemesi yapmaz, karar motoru veya çalışma izni oluşturmaz. Hizmetin tanımı [PRODUCT_OFFERING](../PRODUCT_OFFERING.tr.md), yetki/kapsam sınırı [PILOT_SCOPE](../PILOT_SCOPE.tr.md), müşteri çıktısının yapısı [DELIVERABLE_SPEC](../DELIVERABLE_SPEC.tr.md) içindedir. Phase14 belge başlangıcı `1517364dabe779b19c84f02c5f62beea19c164db` olarak korunur.

## Kaynak kaydı ile insan kararı

Kaynak `disposition`, `claim_basis`, varsa severity/confidence ve kanıt bağlantıları değiştirilmeden kaydedilir. İnsan incelemesi ayrı belge alanıdır. `informational`, `needs_review` ve `confirmed` kaynak disposition'larıdır; aşağıdaki `review_status` değerleri bunların yerine geçmez. Mevcut native assessment yetenekleri `Confirmed` üretmez; ithal bir etiket de bağımsız doğrulama değildir. [Pinli renderer sözleşmesi, reporting.md150–163](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L150-L163).

`KnowledgeOnly` runtime doğrulama yetkisi/hedefi sınırıdır; wire disposition, bulgu sınıfı, güvenli sonucu veya ayrı gözlem sayacı değildir. Kaynakta bulunmayan severity/confidence tahmin edilmez; `null` veya bulunmayan değer düşük risk/sıfır yapılmaz. Kaynak confidence alanı varsa ürün doğruluk yüzdesi veya CVSS diye yorumlanmaz. [DELIVERABLE_SPEC §2–3](../DELIVERABLE_SPEC.tr.md#2-durumlar-ve-iddia-sınırı), [pinli runtime bağlamı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/decision_loop/policy.rs#L685-L701).

Dosya yolu, JSON alanı, mevcut hash/fingerprint veya manifest metadata'sının belge üzerinden kontrol edilmesi **güvenlik uzmanının kanıt incelemesi değildir**. Bu kontrol, `reviewer` / `reviewed_at` alanlarını doldurma veya gözlemi onaylama gerekçesi olamaz. Kaynak/provenance kaydı, teknik inceleme ve müşteri paylaşım kararı ayrı tutulur.

## Phase15 sözlüğü

`review_status` yalnız şu altı belge değerini kullanır:

| Değer | Kaydedilecek anlam | Tek başına sağlamadığı sonuç |
|---|---|---|
| `unreviewed` | Gerçek uzman incelemesi yapılmamış. Başlangıç ve bu fazın dört demo gözleminin durumu. | Kaynak informational olsa da teslim için onay değildir. |
| `needs_manual_review` | Gerçek kayıt sahibi gerekli insan incelemesini ve eksik işlemi belirlemiş; sonuç açık. | Zafiyet doğrulaması veya rapora dahil etme kararı değildir. |
| `informational_only` | Gerçek inceleyen, belirtilen kanıt/sınırlar içinde yalnız gözlem olarak anlatılabileceğini gerekçelendirmiş. | Kaynak `informational` değerinin otomatik kopyası veya hedefin güvenli olduğu kararı değildir. |
| `inconclusive` | İncelenen mevcut kanıt kararı desteklemiyor veya çelişkili; belirsizlik ve takip kayıtlı. | Temiz, risksiz veya hatalı pozitif sonucu değildir. |
| `excluded_with_reason` | Gerçek inceleyen, müşteri sunumundan çıkarma gerekçesini ve kalan etkisini kaydetmiş. | İç kaydın silinmesi veya gözlemin yanlış olduğunun kanıtı değildir. |
| `reviewed_for_delivery` | Gerçek inceleyen, belirtilen anlatımı/kanıt sınırını müşteri çıktısı bakımından incelemiş. | İstismar, bağımsız doğrulanmış zafiyet, düzeltme, müşteri kabulü veya teslim izni değildir. |

**Phase14 ile açık fark:** [DELIVERABLE_SPEC §2](../DELIVERABLE_SPEC.tr.md#2-durumlar-ve-iddia-sınırı) insan belgesi için `not_performed`, `needs_additional_evidence`, `reviewed` öneriyordu; [PILOT_SCOPE §6](../PILOT_SCOPE.tr.md#6-uzman-incelemesi-kabul-ve-kapanış) `not_performed` kullanıyordu. Phase15 yeni operasyon kayıtlarında yukarıdaki zorunlu altılı sözlük kullanılır. Eski belgeler değiştirilmez; otomatik eşleme, native şema migration'ı veya geçmiş inceleme yapılmış varsayımı yoktur. Eski bir kayıt taşınacaksa özgün durum ve referansı korunur, yeni durumun gerekçesi ayrıca yazılır. Bu fazda gerçek uzman incelemesi yokluğu `unreviewed` olarak kaydedilir.

Diğer iki eksen bağımsızdır:

| Alan | İzin verilen belge değerleri | Başlangıç |
|---|---|---|
| `scope_status` | `in_scope`, `out_of_scope`, `unknown` | Yetki/kapsam kaydı yoksa `unknown` |
| `client_inclusion` | `pending_decision`, `include_with_limits`, `exclude_with_reason` | `pending_decision` |

Bir hedefin kaynak dosyada bulunması kapsam izni değildir. Kaynak disposition veya dolu şablon `client_inclusion` değerini kendiliğinden değiştirmez. `reviewed_for_delivery` ile `include_with_limits` aynı alan değildir; ikisinin de ayrı anlamı ve gerekçesi bulunur.

## Zorunlu kayıt ve izlenebilirlik

[Observation ledger şablonu](templates/OBSERVATION_LEDGER.template.md) her gözlem için `case_id`, `observation_ref`, `source_artifact`, `source_disposition`, `scope_status`, `evidence_reference`, `evidence_limitations`, `review_status`, `review_reason`, `client_inclusion`, `follow_up`, `reviewer`, `reviewed_at` alanlarını taşır. Ek `source_artifact_ref`, vaka dizinindeki artefact kaydına; `source_artifact` mevcut dosya referansına bağlanır.

İz şu sırayla kurulmalıdır:

1. **Kaynak:** Vaka → kayıtlı artefact referansı → mevcut byte/SHA256 kaydı → mevcut gözlem fingerprint'i/kimliği ve JSON pointer. Eksik hash/kimlik `not_provided` kalır; dosya adı hash, yeni yerel sıra da native fingerprint sayılmaz.
2. **Kanıt:** Mevcut doğrudan/control/candidate referansları, erişilmiş ve erişilmemiş kanıtlar, sınırlamalar. Opaque referans ham HTTP'ye erişildiği veya onun paylaşılacağı anlamına gelmez; aynı referans birden çok öğede bulunabilir. [DELIVERABLE_SPEC §3](../DELIVERABLE_SPEC.tr.md#3-her-öğe-için-kayıt).
3. **Karar:** [Review decision kaydı](templates/REVIEW_DECISION.template.md) içindeki `decision_id` → ilgili gözlem/artefact referansları → `review_reason` → dayanak ve sınırlama → `client_inclusion` → takip. `decision_id` yerel belge kimliğidir; native doğrulama kimliği değildir. Henüz karar verilmeyen demo kaydının kimliği bulunması kararın verilmiş olduğunu göstermez.
4. **Çıktı:** Dahil edilen anlatımın handoff bölüm/öğe referansı veya hariç tutulan kaydın karar referansı. Müşteri metninin sonradan değiştirilmesi, yeni anlatımın eski kararla kendiliğinden kapsandığı anlamına gelmez; yeniden belge incelemesi ve gerekçe gerekir.

Gerçek kişi veya inceleme zamanı yoksa `reviewer=not_provided`, `reviewed_at=not_provided` yazılır. Kaynak dosyanın zamanı, belge hazırlama zamanı veya sentetik kişi gerçek uzman incelemesi yerine kullanılamaz. Eksik kanıta ilişkin görev `follow_up` alanına yazılabilir; görev yazılması görevin yapıldığı anlamına gelmez.

## Karar kuralları

**Dahil etme:** `include_with_limits`, müşterinin hangi sınırlı bilgiyi görmesinin uygun bulunduğunu söyler. Gerekçe, karar kimliği, kaynak/kanıt referansı, kapsam durumu, belirsizlikler ve [veri paylaşım kararı](DATA_HANDLING.tr.md) birlikte bulunmalıdır. Gerçek uzman incelemesi, paylaşım veya kapsam kararı eksikse `pending_decision` korunur ve [teslim kapısı](DELIVERY_GATE.tr.md) açık kalır. Dahil etmek kaynak disposition'ını yükseltmez.

**Hariç tutma:** `exclude_with_reason` için hangi kaydın neden çıkarıldığı, dayanak/kanıt eksikliği, karar kimliği, kapsam/rapor üzerindeki etkisi ve takip yazılır. `excluded_with_reason` inceleme durumu ile müşteri dahil etme alanı ayrı ayrı gerekçelendirilir. İç ledger satırı ve önceki karar referansı korunur; gerekçe için gereksiz ham sır kopyalanmaz. Bu, uygulanmış değişmez audit deposu veya otomatik sürümleme garantisi değildir.

**Kanıt yetersizliği:** İnceleme hiç yapılmadıysa `unreviewed` kalır. Gerçek inceleyen kanıt eksiğini değerlendirdiyse `needs_manual_review` veya `inconclusive` seçimini gerekçelendirir. Source `NeedsReview` otomatik zafiyet, `Informational` otomatik teslim onayı olmaz. Bir notu yalnız kaynaktan doğrulamak, henüz yapılmamış teknik incelemeyi tamamlamaz.

**Kapsam/çalışma eksikliği:** `scope_status=unknown` yetki ispatı sayılmaz; `out_of_scope` kayıt yeni faaliyet izni üretmez. Incomplete/failed assessment'ın item projection'ı unavailable olabilir; eksik hedef/kontrol “0 bulgu” veya temiz sonuç yapılmaz. Ayrı diagnostic artefact, complete assessment ile tek koşu gibi birleştirilmez. [Pinli incomplete sözleşmesi](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L599-L603).

**Karşılaştırma:** Ayrı artefact, seçili before/after referansları ve gerçek kapsam beyanı korunur. `only_in_before` düzeltilmiş, `only_in_after` yeni zafiyet, `changed` risk artışı/azalışı, `unchanged` bütün güvenlik durumunun eşitliği değildir. `--same-scope` operatör beyanıdır; byte hash'i hedef/üretici doğrulamaz. [Pinli karşılaştırma sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L471-L487), [DELIVERABLE_SPEC §6](../DELIVERABLE_SPEC.tr.md#6-önceki-değerlendirmeyle-karşılaştırma).

Canlı test, uygulama, düzeltme veya yeniden tarama gerektiren takip yalnız gelecekte ayrıca yetkilendirilecek iş olarak yazılır. Bu kit onu başlatmaz.

## Bu fazın demo sınırı

**Demonstration only — No real system assessed.** Mevcut dört informational gözlem kaynak referanslarıyla listelenir; her biri `review_status=unreviewed`, `client_inclusion=pending_decision`, `scope_status=unknown` kalır. Gerçek reviewer/tarih, çalışma yetkisi, seçilmiş pilot binary'si, müşteri kabulü veya GO yoktur. Kısmi JSON/manifest kaydı ve ayrı comparison, uzman incelemesi yapılmış veya tek gerçek retest gerçekleşmiş gibi birleştirilmez. [Korunan Phase14 örnek provenance kaydı](../examples/README.tr.md).
