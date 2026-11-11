# Termivar Offline Case Portfolio & Triage — Phase23

**DEMONSTRATION ONLY — OFFLINE CASE PORTFOLIO — NO CLIENT OR EXECUTION VERIFIED**

Bağımsız standart kütüphane aracı, açıkça seçilmiş mevcut Phase22 vaka ZIP'lerinin
sınırlı durumunu tek portföyde gösterir. JSON/Markdown ve JavaScript içermeyen
offline HTML üretir. Yeni assessment, karşılaştırma, uzman kararı veya görev
ataması oluşturmaz. Kaynak dosyaları yeniden doğrulamaz.

[Sözleşme](../../docs/commercial/operations/phase23/PORTFOLIO_CONTRACT.tr.md),
[triage](../../docs/commercial/operations/phase23/TRIAGE_MODEL.tr.md),
[güven/veri](../../docs/commercial/operations/phase23/TRUST_AND_PRIVACY.tr.md),
[gerçek teslim](../../docs/commercial/operations/phase23/DEMO_DELIVERY.tr.md).

Workspace kökünden örnek kullanım:

```text
python -I -B security-platform/tools/commercial_portfolio/assemble_portfolio.py --portfolio-map security-platform/tools/commercial_portfolio/examples/demo_portfolio_map.json --output-dir outputs/phase23-portfolio
python -I -B security-platform/tools/commercial_portfolio/inspect_portfolio.py --portfolio outputs/phase23-portfolio/portfolio-index.json --manifest outputs/phase23-portfolio/portfolio-manifest.json --summary outputs/phase23-portfolio/portfolio-summary.md --overview outputs/phase23-portfolio/portfolio-overview.html --output outputs/phase23-portfolio/portfolio-inspection.json
```

İkinci komut yalnız ilk komut başarılıysa çalıştırılır. Özet ve HTML actual
byte/hash doğrulaması için ayrıca açık CLI argümanıyla seçilir; manifestteki
isimlerden dosya keşfi yapılmaz. Inspector case ZIP'lerini veya map'i yeniden
açmaz; yalnız dört açık portföy dosyasını inceler.

Bu fazın sınırı iki sentetik ürün çağrısıdır. Gerçek çağrı ve sonuçlar teslim
belgesindedir; tekrar çalışma veya test bu turda yapılmaz. Mevcut demo haritası
yalnız bir Phase22 ZIP'i içerir. Çoklu-vaka kodunun varlığı, çoklu-vaka kabulü
veya farklı müşteri sayısı değildir.

Harita 64 KiB, en fazla 25 ZIP; toplam sıkıştırılmış giriş 16 MiB. ZIP başına
Phase22 sınırları korunur. Invalid kaynak, duplicate raw SHA veya aynı vaka
referansına sahip farklı ZIP hash'i bütün üretimi kapalı hatayla durdurur.
Kaynak atlayarak kısmi portföy başarılı gösterilmez; otomatik merge yoktur.

Yeni ve mevcut olmayan output dizini, sabit payload adları, overwrite etmeyen
yayım ve son manifest kullanılır. Inspector ayrıca seçilmiş yeni JSON dosyası
yazar. Hata kısmi yeni çıktı bırakabilir; crash/yarış kabulü yapılmamıştır.

Korunmuş Phase22 public `inspect_case_bundle` fonksiyonu doğrudan yeniden
kullanılır; eski CLI subprocess ile çalıştırılmaz. Assembly için önceki helper
kaynakları ve mevcut vaka ZIP'i gerekir. Bu kaynak ZIP teslimi eski kaynakları
ve vaka paketini yeniden kopyalamaz. Wheel/startup/backend/frontend entegrasyonu,
servis, network, native scanner veya deploy yoktur.
