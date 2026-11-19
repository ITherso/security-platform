# Offline Task Capsule Lifecycle & Reconciliation (Phase44)

**OFFLINE DEMONSTRATION — UNTRUSTED CAPSULE RECONCILIATION ONLY — NO TASK DISPATCH, ASSIGNMENT, APPROVAL, EXECUTION OR SUBMISSION**

Phase44, Phase43'ün dışa aktardığı bir portable task capsule'ı açıkça verilen yoldan alır. Capsule'ı yerel ve **güvenilmeyen** bir inbox kaydına koyar, sonra deterministik bir mutabakat raporu üretir. Rapor şu soruları yanıtlar:

- Capsule hangi görev kimliğini beyan ediyor?
- İçeriği gerçekte hangi kimliği temsil ediyor?
- Phase43 reader'ıyla uyumlu mu?
- Hangi alanlar var, eksik, null, boş ya da geçersiz?
- Yerel Phase42 görev kayıtları ve Phase43 açıklama kayıtlarıyla hangi kimlikler ve binding'ler eşleşiyor, hangileri eşleşmiyor, hangileri karşılaştırılamıyor?
- Capsule manuel incelemeye uygun mu?

Araç hiçbir görevi göndermez, almaz, yürütmez, atamaz, onaylamaz, tamamlamaz ve gönderime sunmaz.

**2026-11-19 demo sonucu:** Doğrulanmış Phase43 capsule'ı (6742 byte, `49a10169…3619c70a`) her iki yerel kayıt grubuyla yeniden içe alındı.

- import exit **0**, inspector exit **0**
- Phase43 owner reader `COMPATIBLE`
- 35 karşılaştırma satırının hepsi `MATCH`
- Durum `STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW`, inbox `QUARANTINED_AWAITING_MANUAL_REVIEW`
- Inspector: `AGREES` / `BYTE_IDENTICAL`

Aynı gün, salt-okunur denetimin orta önemdeki bulguları düzeltildikten sonra demo `outputs/phase44-task-reconciliation-r2/` dizinine yeniden çalıştırıldı. Sonuç aynıdır; yalnız özetteki görev sayısı satırı nötr ifadeye geçti.

Bu sonuç güven, atama veya onay değildir; manuel inceleme zorunludur. Gerçek byte ve hash değerleri [demo teslim kaydındadır](../../docs/commercial/operations/phase44/DEMO_DELIVERY.tr.md).

## Modüller

| Modül | Sorumluluk |
| --- | --- |
| `reconciliation_contracts.py` | Sürümlü kapalı modeller (istek, rapor, inbox, manifest, inceleme), açık enum'lar, sınırlar |
| `reconciliation_findings.py` | Kararlı kimlikli bulgu kataloğu ve iyileştirme önerileri |
| `capsule_zip_inventory.py` | ZIP ayrıştırma: bellekte, sınırlı, container güvenlik kapıları |
| `capsule_claims.py` | Şema doğrulama ve capsule yorumu: alan durumları, owner validator'lar, manifest eşliği |
| `local_task_records.py` | Açık yerel referans anlık görüntüsü (Phase42 ve Phase43 owner'ları üzerinden) |
| `identity_reconciliation.py` | Yerel kimlik ve açıklama karşılaştırması, açıklama kuralı |
| `reconciliation_engine.py` | Envanter → yorum → Phase43 owner reader → mutabakat → uygunluk |
| `reconciliation_renderer.py` | Raporun inert Markdown görünümü |
| `reconciliation_manifest.py` | Çıktı byte kimlikleri, manifest ve yeni dizine owner yayıncısıyla yazma |
| `reconciliation_inputs.py`, `reconciliation_paths.py` | Açık CLI girdileri ve sabit owner import kökleri |
| `import_task_capsule.py` | İçe alma CLI'ı |
| `inspect_task_reconciliation.py` | Bağımsız inceleme CLI'ı |

Phase43 sözleşmesi yeniden yazılmadı. Kullanılan Phase43 owner kodu:

- `exchange_contracts`: parser, validator'lar, sayaçlar
- `portable_capsule`: üye adları, sınırlar, README, manifest builder
- `recipient_reader`: uyumluluk otoritesi
- `inspect_task_exchange`: Phase43 çıktı doğrulaması
- `phase42_adapter`: bütçeli okuma ve Phase42 kaynak doğrulaması
- `commercial_reference_capsule.capsule_manifest`: yeni dizine yayın

## Kullanım

Ayrıntılı akış, CLI, çıkış kodları ve çıktı yapısı [içe alma ve doğrulama](../../docs/commercial/operations/phase44/IMPORT_AND_VALIDATION.tr.md) belgesindedir. Veri modeli ve uygunluk anlamları [mutabakat sözleşmesi](../../docs/commercial/operations/phase44/RECONCILIATION_CONTRACT.tr.md) belgesinde, güven ve açıklama sınırı ile bilinen sınırlamalar [güven ve açıklama](../../docs/commercial/operations/phase44/TRUST_AND_DISCLOSURE.tr.md) belgesindedir. Gerçek demo kaydı [demo teslim](../../docs/commercial/operations/phase44/DEMO_DELIVERY.tr.md) belgesindedir.

Demo isteği `examples/demo_reconciliation_request.json` dosyasıdır. Doğrulanmış Phase42 register SHA256 değerini (`6465bab0…8ff16`) ve Phase43 index SHA256 değerini (`d3c13285…346d41`) pinler. Doğrulanmış tek Phase43 capsule'ını (F0001 / CAND0002) her iki yerel kayıt grubuyla birlikte yeniden içe alır.

## Testler

`tests/commercial_task_reconciliation/` altındaki testler sentetik fixture'lar kullanır: `SYNTH*` candidate'leri ve `synthetic-*` etiketlerinin digest'leri. Bunlar gerçek güvenlik gözlemi değildir. İsteğe bağlı bir entegrasyon testi mevcut Phase42/43 çıktılarının **kopyalarını** okur; orijinal dosyalar değiştirilmez. Testlerin çalıştırılma kaydı teslim belgesindedir.
