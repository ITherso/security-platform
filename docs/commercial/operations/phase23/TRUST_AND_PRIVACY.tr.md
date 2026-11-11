# Portföy güven ve veri sınırı

**DEMONSTRATION ONLY — OFFLINE CASE PORTFOLIO — NO CLIENT OR EXECUTION VERIFIED**

Portföy operasyonel bir durum indeksidir. Her case'in `content_consistent`
sonucu kendi ZIP iç yapısıyla sınırlıdır; portföye alınması güven seviyesini
yükseltmez. Orijinal 20 kaynak artefact yeniden açılmaz. Producer, uzman,
kurum, hedef sahipliği, gerçek çalışma yetkisi ve müşteri teslimi doğrulanmaz.

Mevcut Phase22 public `inspect_case_bundle(path)` doğrulaması yeniden kullanılır.
ZIP parser veya vaka şeması ikinci kez yazılmaz; eski CLI subprocess ile
çalıştırılmaz. Bozuk/uyumsuz ZIP kabul edilmez. İlk sürümde tek bir kaynak hatası,
duplicate raw SHA veya aynı case reference için farklı raw SHA bütün üretimi
durdurur. Kısmi başarı veya otomatik merge yoktur.

Her case'te kaynakta bulunan demo/execution ve sekiz false doğrulama alanı
korunur. `execution_binding=not_established`; producer/human/authorization/
release/plan execution/scope fulfillment/execution/production bayrakları false.
Portföy sözleşmesinin sabit demo sınırları ayrıca tanımlıdır. Hash/manifest
imza, attestation, kurumsal onay veya gerçek kaynak bütünlüğü garantisi değildir.

Yalnız izinli yeni DTO alanları aktarılır. Raw assessment/HTTP/evidence,
credential/cookie/token, gerçek hedef URL/IP/domain, yerel path, kişi/müşteri
kimliği, serbest uzman notu, ham handoff veya policy payload taşınmaz. Görüntüleme
etiketi demo etiketidir; müşteri adı veya yeni case ID değildir. Bu minimizasyon
otomatik secret detection, redaksiyon veya anonimlik garantisi değildir.

HTML statiktir: JavaScript, harici CSS/font/CDN/görsel, dış bağlantı, raw JSON
gömme veya storage/telemetri yoktur. Dinamik model metni escape edilir. Kaynak
ZIP yolunu açan link veya script üretilmez. Üretilmiş HTML dosyasını text olarak
incelemek, tarayıcıda görsel ürün kabulü değildir.

Yalnız map'teki açık göreli yollar okunur. Rekürsif tarama ve gömülü JSON
path/URL'den dosya keşfi yoktur. Inspector JSON/manifest/Markdown/HTML için
dört açık CLI seçimi alır; map veya case ZIP'lerini açmaz. Output dizini ve
inspection JSON'u yeni olmalıdır; overwrite, mevcut klasör sahiplenme veya
otomatik silme yoktur. Hata yeni kısmi çıktılar bırakabilir; tam atomiklik,
hostile filesystem race, ACL, şifreleme veya güvenli silme kabulü verilmez.

Bu tur yalnız demo veri kullanır. Yeni assessment/comparison, native scanner,
ağ/DNS, canlı API/IdP/PG/Windows/VM/driver/servis/admin, customer contact, PDF veya
deploy yoktur. Test/runner/coverage/otomatik kabul başlatılmaz. Dosya/source
incelemesi bunların yerine geçmez.

İki bağımsız case, duplicate/conflict, hostile JSON/ZIP/manifest, boyut aşımı,
path/symlink/reparse/race/permission/crash ve repeat determinism; gerçek
producer/uzman/kurum/müşteri ve HTML tarayıcı görsel kabulü **NOT_RUN** kalır.
Phase19 UI gözlemleri tamamlanmış sayılmaz. `file://` yasağı local server,
hosting, başka browser surface veya dolaylı yürütmeyle aşılmaz.

Bu özellik gerçek müşterilerle doğrulanmış ihtiyaç veya production-ready vaka
yönetimi olarak sunulmaz. Gerçek kabul kapıları açık kalır; Phase23 tesliminden
sonra yeni faz veya üçüncü ürün komutu kendiliğinden başlatılmaz.
