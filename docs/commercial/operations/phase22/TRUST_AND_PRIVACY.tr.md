# Vaka paketi güven ve veri sınırı

**DEMONSTRATION ONLY — NO REAL SYSTEM ASSESSED OR CLIENT DELIVERY AUTHORIZED**

Vaka ZIP'i kaynak dosyalarının tam delil arşivi değildir. Yalnız sabit rol/
sözleşme/byte/hash bilgisi, sınırlı observation metadata'sı, aşama ve blocker
projeksiyonu taşır. Kaynaklar olmadan dış ilişkiler sonradan yeniden
doğrulanamaz; inspector'ın sonucu iç tutarlılıkla sınırlıdır.

Ham assessment, HTTP request/response, credential/cookie/token, hedef URL/IP/
domain, yerel kaynak path'i, raw evidence, kontrolsüz HTML, serbest uzman notu
ve kişi/müşteri bilgisi yeni projeksiyona alınmaz. Kaynak JSON spread/serialize
edilmez; izinli alanlardan frozen model oluşturulur. Case map yalnız `demo`
kabul eder. Otomatik redaksiyon, secret detector veya anonimleştirme garantisi
yoktur. Özel müşteri verisi bu turda kullanılmaz.

Observation pointer'ı mantıksal JSON konumudur; dosya yolu değildir. Kaynak
fingerprint ve raw file SHA farklı kimliklerdir. İkisi de üretici, yetki,
imza/attestation, bağımsız bulgu doğruluğu veya uzman onayı sayılmaz. Dört
observation ayrı konumlarıyla kalır; duplicate etiketler birleştirilmez.

Haritadaki 20 açık göreli yol dışında keşif yoktur. Gömülü manifest/path/URL
yeni dosya açtırmaz. Workspace mevcut CWD'dir; root değiştirilmez. Link/reparse,
regular-file ve identity kontrolleri source helper'larıyla uygulanır. Kaynak
eksikliği veya tutarsızlık başarılı paket gibi sunulmaz.

ZIP yalnız beş düz isimden oluşur; executable/HTML yoktur. Inspector üye
adı/sayı/tür/boyut/oran ve closed schema kontrollerini uygular. Üyeleri diske
çıkarmaz. Şifreli veya desteklenmeyen compression, duplicate/unsafe entry ve
symlink girişleri reddedilecek şekilde uygulanmıştır. Bu senaryolar hostile
girdiyle çalıştırılmadıysa güvenlik kabulü olarak sunulmaz.

Çıktı dizini yeni; inspector çıktı dosyası ayrıca açıkça seçilmiş yeni bir
dosyadır. Overwrite veya mevcut klasör sahiplenme yoktur. Hata kısmi yeni çıktı
bırakabilir; atomik bütün dizin, crash recovery, ACL, şifreleme veya güvenli
silme garantisi yoktur. Kaynak/çıktı dosyaları yerel diskte kalır.

Tutarlı biçimde değiştirilmiş bir ZIP, kendi manifestiyle tutarlı olabilir.
Harici signature/producer trust kurulmadığından bu araç böyle bir paketin
gerçek kaynağını tespit ettiğini iddia etmez. İnceleyici orijinal 20 kaynağı
okumaz veya bildirilmiş kaynak ilişkilerini yeniden doğrulanmış saymaz.

Boş overlay gerçek insan incelemesi değildir. Plan ile bağımsız assessment
arasında execution bağı yoktur. Önceki Phase18 dönemi handoff taslakları,
Phase19'da yeni builder veya müşteri teslimi olarak etiketlenmez. Bütün
execution/human/producer/authorization/release kapıları kapalı kalır.

Native CLI/scanner/runtime, ağ/DNS/gerçek hedef, backend/frontend/auth/DB,
Windows/VM/driver/servis/admin, müşteri/pilot iletişimi, PDF/deploy veya
otomatik test/runner/coverage yoktur. İki sentetik ürün çağrısı ve manuel
dosya incelemesi güvenlik kabulü değildir. Hostile JSON/ZIP/path/race/permission/
crash ve repeat determinism; gerçek producer/uzman/kurum/yürütme/müşteri kabulü
**NOT_RUN** kalır. Yeni faz veya ek komut kendiliğinden başlatılmaz.
