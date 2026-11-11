# Dört ayrı kaynak ilişkisi

**DEMONSTRATION ONLY — NO REAL SYSTEM ASSESSED OR CLIENT DELIVERY AUTHORIZED**

Dosya bütünlüğü, observation kaynağı, review hazırlığı ve gerçek yürütme bağı
aynı güven bilgisi değildir. Case map'in 11 beklenen ilişki kaydı bu dört
türü açıkça ayırır. Biri tutarlı olsa da başka türün sonucu yükseltilmez.

| Tür | Gerçekte incelenebilen ilişki | Sağlamadığı kanıt |
| --- | --- | --- |
| File content binding | Seçili manifest entry'si ↔ gerçek byte boyutu/SHA | Producer, signature, bulgu doğruluğu |
| Assessment observation binding | Actual assessment SHA ↔ Phase17 pointer/fingerprint/disposition metadata'sı | Gerçek uzman incelemesi, plan execution |
| Review packet binding | Actual packet, original handoff, boş overlay ve reconciliation metadata'sı | Reviewer kimliği, inceleme tarihi, müşteri dahil etme onayı |
| Plan-to-assessment execution | Mevcut kaynaklarda `not_established` | Aynı run, kapsamın karşılanması veya planın uygulanması |

Korunmuş Phase21 `load_plan_bundle`, `load_assessment_bundle`,
`bind_source_mapping` ve saf ledger modeli yeniden kullanılır. Mevcut Phase18
packet/manifest/overlay/binding/reconciliation doğrulayıcıları da gerçek seçilmiş
dosyalarla kullanılır. Önceki fazların CLI'ları yeniden çalıştırılmaz.

Yeni Phase22 reader, sağlanan Phase21 JSON ledger/manifest ve reconciliation /
handoff output manifestlerini açık alan listesiyle bağlar. Generic JSON parse
başarısı bir kaynak ilişkisi sayılmaz. Input digest'i okunmamış handoff için
tahmin edilmez. İçerik uyumsuzluğu veya eksik zorunlu kaynak kapalı hata olur;
başka observation, en yakın fingerprint veya farklı dosya aranmaz.

Plan-summary, assessment HTML, review worksheet, reconciliation Markdown ve
handoff HTML bu 20 kaynak listesinde değildir. Bu manifest entry'leri sadece
metadata olarak kalır; otomatik açılmaz veya tam bundle doğrulaması sayılmaz.
Seçili packet/template, handoff Markdown veya JSON payload'ları kendi actual
byte/hash ilişkileriyle sınırlı biçimde incelenir.

Dört observation kaynak pointer'ları ve ayrı OBS kimlikleriyle korunur. Aynı
fingerprint başka pointer'ı birleştirmez. Fingerprint kaynak beyan etiketidir;
üretici veya sistem güvenliği kanıtı değildir.

`outputs/phase18-handoff/` dosyaları önceki Phase18 dönemindeki Phase16 builder
çıktılarıdır. Phase19 reconciliation input'u aynı byte'lara sahip olsa da bu,
yeni Phase19 builder çalıştığını veya müşteriye teslim edildiğini kanıtlamaz.
Case status bu tarihsel kaynak ayrımını korur; yeni çalışma olayı/tarih üretilmez.

Taşınabilir ZIP kaynak dosyaları içermez. Inspector yalnız paketin iç ilişkisini
yeniden inceler; assembly zamanında dış kaynaklar için bildirilen bağları
orijinalleri olmadan bağımsız doğrulayamaz. Hash manifesti imza/attestation veya
kurumsal onay yerine geçmez.
