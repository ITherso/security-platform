# Termivar Offline Analyst Review Workspace

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Bu bağımsız Python aracı, mevcut Phase17 metadata'sından kaynakla bağlı bir inceleme paketi, boş karar şablonu ve çalışma sayfası hazırlar. İkinci komut açıkça seçilmiş karar overlay'ini mevcut Phase16 girdisiyle uzlaştırır. Tarama, otomatik uzman kararı, gerçek insan doğrulaması veya müşteri teslim yetkisi üretmez.

## Çalıştırma

Python standart kütüphanesi kullanılır; paket kurulumu yoktur. Komutların çalışma dizini `security-platform/` ve `outputs/` bulunan workspace köküdür. Çıktı üst dizini mevcut olmalı; komutta verilen çıktı dizini henüz bulunmamalıdır. Mevcut boş dizin bile kullanılmaz.

```text
python -I -B security-platform/tools/commercial_review/prepare_review.py --handoff-input outputs/phase17-intake/handoff-input.json --source-mapping outputs/phase17-intake/source-mapping.json --intake-manifest outputs/phase17-intake/intake-manifest.json --output-dir outputs/phase18-review-packet
python -I -B security-platform/tools/commercial_review/reconcile_review.py --review-packet outputs/phase18-review-packet/review-packet.json --packet-manifest outputs/phase18-review-packet/review-packet-manifest.json --handoff-input outputs/phase17-intake/handoff-input.json --overlay outputs/phase18-review-packet/decision-overlay.template.json --output-dir outputs/phase18-reconciled
```

Hazırlama dört dosya üretir: `review-packet.json`, `decision-overlay.template.json`, `review-worksheet.md`, `review-packet-manifest.json`. Uzlaştırma üç dosya üretir: `handoff-input.json`, `review-reconciliation.md`, `reconciliation-manifest.json`.

Phase16 builder ayrı bir komuttur; yeni araç onu subprocess ile başlatmaz:

```text
python -I -B security-platform/tools/commercial_handoff/assemble.py --input outputs/phase18-reconciled/handoff-input.json --output-dir outputs/phase18-handoff
```

Bu fazdaki gösterim yalnız mevcut dört sentetik gözlem ve **boş `decisions=[]`** kullanır. Hiçbir reviewer, inceleme zamanı veya pozitif dahil etme örneği oluşturulmaz. Gerçek komut sonuçları ve hash'ler [demo notlarındadır](../../docs/commercial/operations/phase18/DEMO_REVIEW_NOTES.md). Tekrar üretim için başka yeni dizin adları gerekir; bu belgedeki komutları mevcut çıktıların üzerine çalıştırmayın.

## Kaynak ve karar sınırı

İlk profil yalnız Phase17'nin desteklenen taze çıktısını kabul eder: `unreviewed / unknown / pending_decision`, boş kararlar ve null müşteri özeti/karar referansı. Önceden inceleme kararı eklenmiş girdi conflict olarak durur. Revision, geçmiş karar üzerine yazma veya karar birleştirme mekanizması yoktur.

Kaynak kimliği assessment SHA256 + gerçek JSON pointer'dır; fingerprint ayrı kalır. Aynı fingerprint farklı pointer'ları birleştirmez. Packet ve overlay hash bağları byte tutarlılığıdır; imza, producer veya reviewer doğrulaması değildir. Native assessment dosyası bu komutlara verilmez ve yeniden açılmaz.

İleride açıkça doldurulan overlay yalnız gerçek Phase16 alanlarına aktarılır; teknik kararın doğruluğu değerlendirilmez. `safe_summary` karar içeriğinin digest bağına dahildir. İç gerekçe ile müşteri modeli ayrı tutulur; mevcut Phase16 allowlist ve global teslim engelleri korunur. Bu sürümde dolu overlay davranışı çalıştırılarak kabul edilmemiştir.

## Yerel dosyalar ve bağımlılıklar

Yalnız açık cwd-relative dosya argümanları okunur. JSON içindeki yol/URL takip edilmez. Strict UTF-8, duplicate key/tür/sayı/sürüm/alan/adet/metin sınırları, eski yardımcıların path/reparse kontrolleri ve manifest-last yayınlama tasarımı kullanılır. Kaynakta kontrol bulunması saldırı dayanımı kabulü değildir. Ayrıntılar [sözleşmede](../../docs/commercial/operations/phase18/REVIEW_CONTRACT.tr.md).

Araç korunmuş kardeş [Phase16](../commercial_handoff/README.md) ve [Phase17](../commercial_intake/README.md) modüllerini import eder. Yeni Phase18 ZIP'i bu eski çalışma kopyalarını veya eski girdi dosyalarını içermez; mevcut korunmuş checkout üzerine eklenir. Production wheel, platform frontend/backend veya native Termivar runtime entegrasyonu yoktur.

[İş akışı](../../docs/commercial/operations/phase18/ANALYST_WORKFLOW.tr.md), [kaynak bağı](../../docs/commercial/operations/phase18/SOURCE_BINDING.tr.md), [güven sınırı](../../docs/commercial/operations/phase18/TRUST_BOUNDARY.tr.md), [örnek kaynaklar](examples/README.md).
