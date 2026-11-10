# Review Desk kaynak ve güven sınırı

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Desk yeni observation doğrulayıcısı değildir. Python mevcut [Phase18 sözleşmelerini](../phase18/REVIEW_CONTRACT.tr.md), packet manifest kontrolünü ve karar bağlama fonksiyonlarını kullanır. HTML'ye yalnız dar kapalı metadata projeksiyonu alınır.

## Kimlikler ve serbest metin

Packet digest seçilen dosyanın gerçek byte SHA256'sıdır. Assessment digest, Phase18 packet metadata'sında beyan edilen önceki kaynak kimliğidir; native assessment yeniden açılmaz. Observation anahtarı assessment SHA256 + JSON pointer'dır. Fingerprint ayrı etikettir; tekrar eden fingerprint'ler farklı pointer kayıtlarını birleştirmez.

Packet manifest karşılaştırması yalnız açık packet entry'sini ve metadata ilişkilerini kontrol eder. Ayrı verilen overlay template ayrıca okunur ve boşluğu/digest bağları kontrol edilir. Bunlar producer, tam bundle, insan kimliği veya bağımsız kanıt doğrulaması değildir. Hash'ler imza/attestation yerine geçmez.

Kaynakta bulunmayan category veya ayrıntılı kanıt durumu için “Mevcut sonuçta bulunmuyor” gösterilir. Yokluk sıfır risk/kanıt yok/güvenli sonuç diye yorumlanmaz. UI review ve inclusion seçenekleri insan karar taslağıdır; native disposition değişmez.

Tarayıcıda yazılan gerekçe, özet, eksik kanıt veya takip hassas veri içerebilir. Gerçek müşteri bilgisi girilmez; otomatik sır tarama/redaksiyon yoktur. UI metinleri `textContent`/form değerleriyle sunulur; kullanıcı metni HTML/script olarak yorumlanmaz. Nihai strict doğrulama Python'da tekrarlanır.

## Tek dosya ve tarayıcı sınırı

Projeksiyon UTF-8 JSON olarak base64 kodlanır; HTML/script bağlamını kıramaz. Sabit JS/CSS aynı belgeye gömülür ve gerçek inline byte'larından üretilen hash CSP kullanılır. Dış kaynak, network API, storage/cookie, service worker, telemetri veya otomatik kaydetme kodu yoktur. JSON'daki yol/URL başka dosya açtırmaz.

Kararlar sayfa belleğindedir. Yalnız açık kullanıcı eylemi Blob JSON indirme isteği oluşturur; uygulama dosyanın diskte kaydedildiğini doğrulayamaz. Yeniden açılış önceki kararları yüklemez. Tarayıcı indirme geçmişi, yerel dosyalar, bellek artıkları ve platform ayarları için eksiksiz izolasyon/güvenli silme garantisi verilmez. CSP dosyanın değiştirilmediğini veya producer kimliğini kanıtlamaz.

Kaynak/çıktı dosyaları açık cwd-relative CLI argümanlarıyla seçilir; yeni dizin şarttır. Eski path/reparse kontrolleri, kendi staging dizini, overwrite etmeyen hardlink ve manifest-last tasarımı kullanılır. Başarısız işlem yeni kısmi çıktı/staging bırakabilir; bütün dosya sistemi/ACL/race/crash davranışları kabul edilmiş sayılmaz.

## Açık kabul kapıları

Otomatik test/runner/coverage yoktur. Malformed/duplicate/hostile encoding/path/symlink/permission/crash ve dolu/pozitif karar senaryoları **NOT_RUN** kalır. Kodda bir kontrolün bulunması yürütülmüş güvenlik testi değildir.

Gerçek uzman incelemesi, kullanıcı kimliği, kurumsal/veri işleme yetkisi, güvenlik testleri ve müşteri teslim onayı açıktır. Tarayıcıya erişilemiyorsa gözlem/indirme; gerçek draft elde edilmediyse finalize/reconciliation tamamlanmış gösterilmez. Gerçek durum [demo notlarında](DEMO_WORKFLOW.tr.md) belirtilir.

Bu yeni araç eski Phase16/17/18 kaynaklarına bağımlıdır; bunları, operator-console'u, backend/HBF/Termivar runtime'ı veya production wheel'i değiştirmez. Yeni faz veya canlı işlem başlatmaz.
