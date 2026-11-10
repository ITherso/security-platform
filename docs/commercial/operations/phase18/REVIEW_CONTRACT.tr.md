# Phase18 kapalı inceleme sözleşmeleri

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Yeni iki sözleşme yalnız analyst metadata'sıdır; native Termivar assessment ve değişmemiş `termivar-handoff-draft/v1` ile karıştırılmaz. Uygulayan kaynaklar: [review_contracts.py](../../../../tools/commercial_review/review_contracts.py), [packet_builder.py](../../../../tools/commercial_review/packet_builder.py), [decision_overlay.py](../../../../tools/commercial_review/decision_overlay.py), [reconciler](../../../../tools/commercial_review/handoff_reconciler.py).

## Packet: `termivar-analyst-review-packet/v1`

| Kök alan | İçerik |
| --- | --- |
| `schema_version`, `mode`, `demo_label` | Sabit yeni sürüm, `demo`, görünür demo etiketi |
| `phase17_inputs` | `handoff_input`, `source_mapping`, `intake_manifest`; her biri `sha256`, `byte_length` |
| `source_assessment` | `sha256`, `byte_length`, `schema`, `source_schema`, `run_schema`, `profile_schema`, `profile`, `status`, `subject_count`, `item_count`; mevcut Phase17 dar profilinin metadata'sı |
| `manifest_limitation` | Mevcut optional manifestin `provided`, digest/boyut, status, JSON-entry/summary ilişkisi; HTML/full bundle/producer false |
| `observations` | En fazla 256 kapalı kaynak ve başlangıç durum kaydı |
| `review_requirements`, `delivery_blockers` | Sabit eksik inceleme/kapsam/kanıt/paylaşım/metin ve teslim engeli kodları |
| `source_verification` | `phase17_file_binding_only` |
| `demo_only` | `true` |
| `human_review_verified`, `producer_verified`, `release_authorized`, `native_assessment_verified` | Hepsi `false` |

Her observation: `observation_id`, `observation_key`, `source_assessment_sha256`, `source_json_pointer`, `fingerprint`, `capability_id`, `source_disposition`, `review_status`, `scope_status`, `client_inclusion`. Kimlik ve pointer sırası gerçek Phase17 kayıtlarına bağlıdır. Başlangıç durumları yalnız `unreviewed / unknown / pending_decision` kabul edilir. Kaynak serbest metni veya tüm handoff nesnesi packet'a eklenmez.

## Overlay: `termivar-analyst-decision-overlay/v1`

Kök alanlar tam olarak `schema_version`, `review_packet_digest`, `source_assessment_digest`, `decisions`, `review_context` olur. Digest'ler 64 küçük hex karakterli SHA256'dır; observation fingerprint'i ayrıca `sha256:` öneklidir.

`review_context`: `mode=demo`, `demo_only=true`, sabit `demo_label` ve false kalan `human_review_verified`, `producer_verified`, `release_authorized`. Şablonda `decisions=[]`; kişi veya tarih yoktur.

Bir insanın ileride dolduracağı karar satırındaki **bütün alanlar zorunlu anahtardır**, belirtilmeyen metinler `null` olur:

| Alanlar | Anlam / eşleme |
| --- | --- |
| `decision_id`, `observation_id` | Sınırlı yerel karar/gözlem kimliği |
| `observation_key`, `source_assessment_sha256`, `source_json_pointer`, `fingerprint`, `capability_id`, `source_disposition` | Packet ile değişmeden eşleşecek kaynak bağı |
| `scope_status`, `review_status`, `client_inclusion` | Ayrı ve açıkça istenen üç durum; Phase16 observation alanları |
| `safe_summary` | Nullable, yalnız açık müşteri anlatımı; karar içeriği digest'ine dahildir |
| `reason` | Nullable iç karar gerekçesi; Phase16 `ReviewDecision.reason`; null için açık `not_provided` işareti |
| `missing_evidence`, `follow_up` | Nullable iç notlar; Phase16'da ayrı alan bulunmadığından aktarılmaz, özgün overlay ve hash bağı korunur |
| `reviewer_ref`, `reviewed_at` | Nullable, doğrulanmamış kişi/zaman beyanı; Phase16 karar alanları |
| `decision_context_digest` | Satırın tüm diğer alanlarının tam içeriğine bağlı SHA256; [tarif](SOURCE_BINDING.tr.md) |

`safe_summary/reason` en fazla 2048, `missing_evidence/follow_up` 1024 karakter ve 16 satır; `reviewer_ref` 128 karakter ve tek satır; zaman `YYYY-MM-DDTHH:MM:SSZ` biçiminde geçerli UTC takvim değeri veya null. Boş/yalnız whitespace metin yerine null gerekir. Satır limiti CRLF/CR/LF ayrımları üzerinden sayılır; verilen metin kırpılmaz veya Unicode normalize edilmez. Geçersiz UTF-8/surrogate, C0 kontrol karakterleri (LF/CR/TAB hariç) ve C1/DEL reddedilir.

Review değerleri [Phase15 politikasındaki](../OBSERVATION_REVIEW_POLICY.tr.md) altı değerdir: `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery`. Inclusion: `pending_decision`, `include_with_limits`, `exclude_with_reason`. Scope: `in_scope`, `out_of_scope`, `unknown`. Yeni enum yoktur; Termivar disposition ayrı kalır.

`include_with_limits` yalnız açık `in_scope`, uygun insan durumu (`informational_only` veya `reviewed_for_delivery`) ve dolu `safe_summary` ile biçimsel olarak kabul edilir. Null reviewer/zaman araç tarafından doldurulmaz; Phase16 seçim engelleri kalır. Hariç bırakmada gerekçe gerekir, kaynak gözlem silinmez. Dolu karar yolu bu fazda yürütülmemiştir.

## Dosya ve çıktı sınırları

Seçilen JSON girdileri en fazla 256 KiB; packet manifesti en fazla 64 KiB. Phase16'nın 12 derinlik, 10.000 düğüm (anahtarlar dahil), toplam 128 KiB UTF-8 metin ve tek JSON string için 8192 karakter sınırları da uygulanır. Daha önceki geniş generic loader bu bütçeleri genişletmez. En fazla 256 observation ve 256 decision; 20 karakteri aşan sayı sözcüğü, float/NaN/Infinity, duplicate key, bilinmeyen alan/sürüm ve yanlış tür reddedilir. Limit aşımında ilk N kayıt sessizce alınmaz.

Packet ve handoff JSON üretimi aynı 256 KiB bütçeye uyar. Worksheet renderer 256 KiB, reconciliation raporu renderer 1 MiB sınırındadır; ortak publisher'ın payload tavanı 4 MiB'dir ve bu daha dar renderer sınırlarını yükseltmez. Yeni manifestler 64 KiB sınırındadır. Manifestler kendi hash'ini kendi içine koymaz. `termivar-analyst-review-packet-manifest/v1` ve `termivar-analyst-reconciliation-manifest/v1` yalnız yeni araç metadata'sıdır; üretici/onay kanıtı değildir.

Reconciliation yalnız mevcut Phase16 alanlarını üretir: gözlemin review/scope/inclusion/summary/decision referansı ve yedi alanlı `ReviewDecision`. Kaynak kayıtları, case/scope açıklaması, yetki durumu ve delivery constraints değiştirilmez. Yeni doğrulama bayrakları eski strict JSON'a eklenmez; `mode=demo` korunur, false bayraklar yeni manifest/raporda görünür. Phase16 client allowlist'i değişmez.
