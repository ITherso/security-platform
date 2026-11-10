# Termivar Offline Analyst Review Desk

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Phase19, mevcut Phase18 packet'ından tek başına açılan bir HTML çalışma alanı üretir. Kaynak gözlemleri, eksik inceleme bilgileri ve kullanıcı karar taslağı ayrı gösterilir. Yeni platform ekranı, sunucu veya scanner yoktur. Bu fazda insan kararları doldurulmaz.

## Hazırlama ve yerel açma

Python standart kütüphanesi ve tarayıcının yerleşik özellikleri kullanılır; paket kurulumu veya build gerekmez. Komutların çalışma dizini `security-platform/` ve `outputs/` bulunan workspace köküdür.

```text
python -I -B security-platform/tools/commercial_review_desk/prepare_desk.py --review-packet outputs/phase18-review-packet/review-packet.json --packet-manifest outputs/phase18-review-packet/review-packet-manifest.json --overlay-template outputs/phase18-review-packet/decision-overlay.template.json --output-dir outputs/phase19-review-desk
```

Yeni dizinde `review-desk.html` ve `desk-manifest.json` oluşur. HTML doğrudan yerel tarayıcıda açılır; localhost server, dış CSS/font/script veya ağ çağrısı gerektirmez. Veri, script ve stil aynı dosyanın içindedir. [Gerçek üretim ve tarayıcı gözlem durumu](../../docs/commercial/operations/phase19/DEMO_WORKFLOW.tr.md).

Arama/filtre ile gözlemi seçin. Kaynak disposition, fingerprint/pointer ve mevcut insan durumları salt okunurdur. Category veya gerçek kanıt ayrıntısı packet'ta bulunmuyorsa arayüz bu bilgiyi tahmin etmez. Karar alanlarını değiştirmek, müşteri dahil etme kararını kendiliğinden değiştirmez.

## Taslak ve sonlandırma

Tarayıcı yalnız `termivar-analyst-decision-draft/v1` dosyası indirir. Bu dosya Phase18 overlay'i veya uzman onayı değildir. İlk açılışta karar listesi boştur; demo incelemesinde bu boş durum korunur. İndirme isteğinin oluşturulması dosyanın gerçekten diske kaydedildiğinin kanıtı değildir.

Gerçekten dışarı alınmış taslak dosyası mevcutsa, dosyayı açık bir cwd-relative argümanla seçin. Aşağıdaki taslak yolu gelecekteki gerçek indirme içindir; araç bu dosyayı kendiliğinden oluşturmaz:

```text
python -I -B security-platform/tools/commercial_review_desk/finalize_desk.py --review-packet outputs/phase18-review-packet/review-packet.json --packet-manifest outputs/phase18-review-packet/review-packet-manifest.json --handoff-input outputs/phase17-intake/handoff-input.json --decision-draft outputs/phase19-exported/termivar-decision-draft.json --output-dir outputs/phase19-finalized-overlay
```

`--handoff-input` açık ve zorunlu bir uyarlamadır: mevcut Phase18 `bind_decisions` gerçek orijinal handoff girdisini ister. Dosya JSON içindeki bir yoldan keşfedilmez; sahte `LoadedInput` oluşturulmaz. Python, tam karar context digest'ini mevcut Phase18 yardımcılarıyla hesaplar. JavaScript bu digest'i yeniden uygulamaz.

Başarılı sonlandırma `decision-overlay.json` ve `overlay-manifest.json` üretir. Yeni araç reconciliation veya builder'ı otomatik başlatmaz. Overlay gerçekten oluşmuşsa mevcut Phase18 aracı ayrıca kullanılabilir:

```text
python -I -B security-platform/tools/commercial_review/reconcile_review.py --review-packet outputs/phase18-review-packet/review-packet.json --packet-manifest outputs/phase18-review-packet/review-packet-manifest.json --handoff-input outputs/phase17-intake/handoff-input.json --overlay outputs/phase19-finalized-overlay/decision-overlay.json --output-dir outputs/phase19-reconciled
```

Bütün çıktı dizinleri yeni olmalı; mevcut boş dizin bile sahiplenilmez. Tekrar üretimde başka yeni adlar seçilir. Bu fazda en fazla üç sentetik ürün komutu vardır; gerçek browser export elde edilmeden ikinci/üçüncü komut çalıştırılmaz.

## Bağımlılıklar ve sınır

Korunmuş kardeş `commercial_handoff`, `commercial_intake` ve `commercial_review` kaynakları gerekir. Yeni ZIP eski çalışma kopyalarını veya eski packet/girdi dosyalarını içermez; mevcut checkout üzerine eklenir. Production wheel veya operator-console entegrasyonu yoktur.

Kararlar yalnız sayfa belleğindedir; storage/cookie/telemetri yoktur. Taslak indirilirse ayrı bir yerel dosya olarak kalır; otomatik redaksiyon, şifreleme veya güvenli silme garantisi yoktur. `human_review_verified=false`, `producer_verified=false`, `release_authorized=false` korunur. [Kullanım](../../docs/commercial/operations/phase19/REVIEW_DESK.tr.md), [taslak sözleşmesi](../../docs/commercial/operations/phase19/DECISION_DRAFT_CONTRACT.tr.md), [kaynak ve güven sınırı](../../docs/commercial/operations/phase19/SOURCE_AND_TRUST_BOUNDARY.tr.md).
