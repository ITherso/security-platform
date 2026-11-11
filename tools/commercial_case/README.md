# Termivar Offline Case Bundle & Workflow Integrity — Phase22

**DEMONSTRATION ONLY — NO REAL SYSTEM ASSESSED OR CLIENT DELIVERY AUTHORIZED**

Bağımsız offline araç mevcut sentetik plan, assessment, intake, review ve handoff
artefact'larının sınırlı durumunu tek taşınabilir vaka ZIP'inde toplar. Orijinal
kaynakların tam kopyası paketlenmez. İkinci CLI paketi çıkarmadan okur; kaynakları
yeniden açmaz, producer/uzman/yetki doğrulamaz.

[Sözleşme](../../docs/commercial/operations/phase22/CASE_BUNDLE_CONTRACT.tr.md),
[ilişkiler](../../docs/commercial/operations/phase22/RELATIONSHIP_MODEL.tr.md),
[iş akışı](../../docs/commercial/operations/phase22/WORKFLOW_STATES.tr.md),
[güven ve veri](../../docs/commercial/operations/phase22/TRUST_AND_PRIVACY.tr.md),
[gerçek teslim](../../docs/commercial/operations/phase22/DEMO_DELIVERY.tr.md).

Workspace kökünde örnek kullanım:

```text
python -I -B security-platform/tools/commercial_case/assemble_case.py --workspace-root . --case-map security-platform/tools/commercial_case/examples/demo_case_map.json --output-dir outputs/phase22-case
python -I -B security-platform/tools/commercial_case/inspect_case.py --bundle outputs/phase22-case/termivar-demo-case.zip --output outputs/phase22-case/inspection-summary.json
```

İkinci komut yalnız ilk komut başarılıysa çalıştırılır. Bu fazın sınırı bu iki
sentetik ürün çağrısıdır; tekrar çalışma veya negatif senaryolar yapılmaz.
Gerçekte kullanılan komutlar ve sonuçlar teslim belgesinde kayıtlıdır.

`--workspace-root .` mevcut çalışma dizinini seçer. Başka root'a geçilmez;
harita yolları bu workspace'e göre güvenli göreli yollardır. Rekürsif keşif,
JSON içindeki başka path/URL'den dosya seçme veya ağ bağlantısı yoktur.
Harita dosyası ile 20 seçili kaynak ayrı kimliklerdir; rol, run kimliği değildir.

Assembly yeni ve mevcut olmayan çıktı dizini ister. Inspector çıktısı ayrıca
açıkça seçilen yeni JSON dosyasıdır; aynı assembly klasöründe mevcut dosyaların
üzerine yazmaz. Hata kısmi yeni dosyalar bırakabilir; güvenli silme/crash/yarış
kabulü yapılmamıştır. Kaynaklar kullanıcı adına onaylanmaz.

ZIP yalnız beş sabit üyeden oluşur. Kaynaklar olmadan dış ilişkiler sonradan
bağımsız doğrulanamaz. Hash iç tutarlılıktır; imza/attestation veya izin değildir.
Inspector, kendi içinde tutarlı biçimde değiştirilmiş paketin gerçek üreticisini
tespit ettiğini iddia etmez.

Python standart kütüphanesi kullanılır. Korunmuş Phase16–21 helper kaynakları ve
mevcut örnek girdiler assembly için gereklidir; kaynak teslim ZIP'i bunları
tekrar kopyalamaz. Native CLI/scanner, wheel/startup, frontend, servis, test,
gerçek hedef veya müşteri teslimi başlatılmaz.
