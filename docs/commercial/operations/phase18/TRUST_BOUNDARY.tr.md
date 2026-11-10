# Analyst review güven sınırı

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Bu fazdaki çalışan örnek boş karar aktarımıdır. Kaynak ve çıktı dosyalarının incelenmesi gerçek güvenlik uzmanının kanıt incelemesi veya bağımsız güvenlik kabulü değildir.

| Kontrol | Sağladığı sınırlı bilgi | Sağlamadığı kanıt |
| --- | --- | --- |
| Phase17 dosya hash/byte bağları | Seçilmiş üç dosyanın beyan edilen içerik ilişkisi | Native assessment'ın yeniden okunması, producer kimliği, yetki |
| Packet manifesti | Açıkça seçilen packet'ın byte kaydına eşitliği | Worksheet/template veya tam bundle'ın yeniden doğrulanması |
| Packet/source/observation bağı | Aynı metadata kaydına açık karar referansı | İmza, attestation, kararın doğruluğu |
| Reviewer/zaman beyanı | Sınırlı metin ve UTC biçimi | Gerçek kişi, uzmanlık veya inceleme yapıldığı |
| Phase16 strict çıktı | Eski handoff şemasına uyumluluk | Müşteri teslim yetkisi, teknik bulgu doğrulaması |

## Veri minimizasyonu

Packet yalnız kapalı metadata taşır; ham assessment, HTTP mesajı, payload, credential, hedef URL/IP/domain veya iç dosya yolu kopyalanmaz. Kaynak mapping'deki keyfî serbest metin modelin tamamı olarak taşınmaz. Bu, genel sır tarama veya anonimleştirme garantisi değildir.

Overlay'in izinli serbest metinleri hassas bilgi içerebilir. Gerçek müşteri verisi girilmez; otomatik redaksiyon yoktur. `safe_summary` yalnız açıkça yazılmış müşteri metnidir. Karar gerekçesi iç modelde kalır; eksik kanıt/takip metni eski Phase16'da ayrı alan bulmadığından zorla müşteri alanına birleştirilmez. Özgün overlay ayrı dosya olarak korunmalıdır.

JSON kod olarak çalıştırılmaz; worksheet/uzlaştırma raporu keyfî HTML veya Markdown metnini render etmez. Phase16'nın var olan renderer ve client allowlist'i aynen kullanılır. JSON içindeki URL/path/artefact adları otomatik açılmaz. Console'a ham dosya içeriği yazılmaz.

## Dosya ve çalışma sınırı

Yalnız açık cwd-relative girdiler, yeni çıktı dizinleri ve sabit dosya adları vardır. Symlink/reparse/kimlik kontrolleri, kontrollü staging, overwrite etmeyen hardlink yayını ve manifest-last tasarımı eski yardımcılarla korunur. Başarısız işlem yeni kısmi dizin veya staging kalıntısı bırakabilir; başarı ya da güvenli silme garantisi verilmez. Hostile filesystem race, tüm işletim sistemi/ACL ve crash dayanımı kabul edilmemiştir.

Bellekte doğrulanan kapalı DTO'lar kullanılır; çıktı dosyaları yerel diskte kalır. Şifreleme, güvenli silme, süreli saklama, merkezi audit veya access-control ürünü yoktur. Üçüncü taraf paket, ağ, subprocess, servis veya production startup entegrasyonu bulunmaz.

## Açık kapılar

Malformed UTF-8/JSON, duplicate key, sayı/boyut/derinlik sınırı, yanlış schema/manifest/bağlama, dolu overlay, pozitif inclusion, hostile encoding, symlink/reparse/race/permission/crash davranışları **NOT_RUN**. Bunlar için kod kontrolü bulunması yürütülmüş test değildir. Otomatik test/runner/coverage ve native Termivar CLI/scanner çalıştırılmaz.

Gerçek uzman incelemesi, müşteri/kurum yetkisi, veri işleme ve saklama kararları, güvenlik testleri ve gerçek müşteri teslim onayı açık kalır. Dolu overlay'deki `reviewed_for_delivery` beyanı bile global demo ve teslim blokajlarını kaldırmaz. [Mevcut Phase15 politikası](../OBSERVATION_REVIEW_POLICY.tr.md), [manuel teslim kapısı](../DELIVERY_GATE.tr.md).
