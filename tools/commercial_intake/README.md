# Termivar Assessment-to-Handoff Bridge

Bu bağımsız çevrimdışı araç, açıkça seçilen mevcut native assessment JSON'unun desteklenen dar profilini okur; eski Phase16'nın `termivar-handoff-draft/v1` girdisini **kendisi üretir**. Elle observation JSON'u yazmak gerekmez. Kaynakta bulunmayan hedef, yetki, kişi, inceleme kararı veya güvenli müşteri özeti oluşturmaz.

Yalnız demo dönüşümü vardır. Dört kaynak gözlem `unreviewed / unknown / pending_decision` olur; `safe_summary=null`, `decision_ref=null`, `review_decisions=[]` kalır. Otomatik uzman incelemesi, native scanner, assessment/comparison üretimi veya müşteri teslimi yapılmaz.

## Kullanım

Python standart kütüphanesi kullanılır. Bu teslimin gerçek çalışma sürümü ve komut sonuçları [demo entegrasyon notunda](../../docs/commercial/operations/phase17/DEMO_INTEGRATION.tr.md) kayıtlıdır. Kod Python 3.10+ sözdizimi kullanır; başka Python/OS sürümlerinin kabulü yapılmış sayılmaz.

Komutlar, `security-platform/` ile `outputs/` bulunan workspace kökünden verilir. Aşağıdaki kaynaklar **önceden mevcut sentetik örneklerdir**:

```text
python -I -B security-platform/tools/commercial_intake/assemble_intake.py --assessment security-platform/docs/commercial/examples/assessment.json --manifest security-platform/docs/commercial/examples/manifest.json --output-dir outputs/phase17-intake
python -I -B security-platform/tools/commercial_handoff/assemble.py --input outputs/phase17-intake/handoff-input.json --output-dir outputs/phase17-handoff
```

`--manifest` isteğe bağlı ve ayrı dosya seçimidir. Manifestte adı geçen HTML veya JSON içindeki bir path/URL açılmaz. Yollar cwd-relative olmalı; mutlak/drive/UNC/`..`/ADS ve symlink/reparse yönlendirmesi kabul edilmez. Çıktı üst dizinleri mevcut, çıktı dizinlerinin kendisi henüz bulunmayan yeni yollar olmalıdır. Mevcut boş dizin bile sahiplenilmez; tekrar üretimde farklı yeni adlar seçilir. Gizli real/production modu, `--force`, otomatik klasör keşfi veya arka plan işlem yoktur.

## Destek profili ve dosyalar

İlk adapter, Phase14'ün base-only `venom-rendered-assessment/v1`, `web-review`, `complete` örneğine bağlıdır. En fazla 1 MiB / 256 item; gerçek native CLI'nin genel kapasitesi değildir. Yalnız mevcut dört pasif capability kimliği ve bu örneğin iki category değeri desteklenir. Bilinen optional audit bölümleri de bu sürümün kapsamı dışındadır; varlıkları açık ret sebebidir. Yinelenen fingerprint etiketleri birleştirilmez: her kayıt kaynak byte SHA256'sı ve kendi pointer'ıyla korunur, tekrar bayrağı gösterilir. Bu davranış native tam importer'ın fingerprint benzersizliği kabulü değildir. [Tam sınırlar ve eşleme](../../docs/commercial/operations/phase17/SOURCE_MAPPING.tr.md).

Yeni intake dizinindeki sabit dosyalar:

- `handoff-input.json`: Phase16'nın değişmemiş strict sözleşmesine göre, sürekli demo ve inceleme bekleyen girdi.
- `source-mapping.json`: Gerçek kaynak byte SHA256'sı, pointer/fingerprint/disposition ve izinli kapalı metadata; taşınmayan alanların yalnız sınıf adları.
- `intake-manifest.json`: Gerçek giriş/çıktı byte kimlikleri, sayılar, kısmi manifest sınırı ve açık blokajlar. Kendi hash'i kendi içine eklenmez; dış teslim manifestinde ölçülür.

Phase16 ikinci, ayrı komuttur; bridge onu subprocess ile başlatmaz. Phase16'nın tüm gözlemleri gösteren iç özeti ile yalnız ayrı karar/koşullarla seçilmiş alanlardan oluşan müşteri modeli korunur. Dört incelenmemiş örnek müşteri bulgusu olarak taşınmaz; bu, güvenlik açığı bulunmadığı sonucu değildir.

## Bağımlılık ve güven sınırı

Yeni araç eski [Phase16](../commercial_handoff/README.md) Python yardımcılarını import eder; eski dosyaları değiştirmez, kopyalamaz veya wheel'e bağlamaz. Çalışma için korunmuş `tools/commercial_handoff/` dizini kardeş konumunda bulunmalıdır. Üçüncü taraf paket kurulumu gerekmez. Yeni Phase17 ZIP'i önceki çalışma kopyalarını içermez; mevcut Phase16 checkout/teslimatı üzerine yeni dosyalar olarak kullanılır.

Free-text native başlık/özet/remediation, hedef, iç yol, kişi, ham HTTP/credential/payload aktarılmaz. Sabit adapter açıklamaları kullanılır. Bu, genel redaksiyon veya sır taraması değildir. Hash/kısmi manifest eşleşmesi üretici imzası, uzman incelemesi veya tam bundle doğrulaması değildir. `demo_only=true`, `human_review_verified=false`, `producer_verified=false`, `release_authorized=false` kalır.

[Araç açıklaması](../../docs/commercial/operations/phase17/ASSESSMENT_INTAKE.tr.md), [güven sınırı](../../docs/commercial/operations/phase17/TRUST_BOUNDARY.tr.md) ve [örnek kaynak konumu](examples/README.md) birlikte okunmalıdır. Gerçek müşteri yetkisi, veri/kurum kararları ve güvenlik kabulü açıktır; bu faz bitince yeni faz veya canlı iş açılmaz.
