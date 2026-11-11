# Dosya, lisans ve veri güven sınırı

**DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED**

[Sözleşme](EVIDENCE_CONTRACT.tr.md), [kayıt bağı](COMPONENT_BINDING.tr.md),
[inceleme akışı](LICENSE_REVIEW_WORKFLOW.tr.md).

Hash yalnız seçilmiş dosyanın byte kimliğidir. Kaynak içi dosya/record ilişkisi;
üretici doğrulaması, imza, attestation, hukukî lisans yorumu veya ticari dağıtım
izni değildir. Lisans metni bulunması inceleme tamamlandı anlamına gelmez.
Birinci taraf MIT etiketi üçüncü taraf veya destek araçlarına yayılmaz.

Yalnız açık Phase24 dosyaları ve scope'ta seçilmiş evidence okunur. Repository
kökleri CLI ile açıkça verilir; belge içindeki URL/path başka okuma, indirme,
resolver veya komut başlatmaz. Kaynak metin kod olarak çalıştırılmaz. Mevcut
Phase24 güvenli okuyucusu değiştirilmeden yeniden kullanılır; Windows path/open
identity denetimlerinde farklı API ailelerinin ctime değerleri eşit sayılmaz.
Okuma ve son kararlılık kontrolleri tam atomiklik veya saldırgan filesystem
kabulü değildir.

Symlink/junction/reparse/path traversal ve hardlink kontrolleri uygulanır.
Yalnız bulunmayan dosya eksik kanıt sayılır; güvensiz yol, izin/okuma hatası
veya limit aşımı başarılı eksik-evidence akışı gibi yutulmaz. Beklenen hash
uyuşmazlığı bağlanmayan evidence/olay olarak görünür. Output dizini yeni
olmalıdır; overwrite veya eski dizini temizleme yapılmaz. Hata kısmi yeni çıktı
bırakabilir; manifest yokluğu veya başarısız süreç tamamlanmış teslim değildir.

Çıktı kapalı metadata alanlarıyla sınırlıdır. Tam lisans metni, kaynak kodu,
ham JSON/kaynak belge, credential/API anahtarı, özel kişi/müşteri bilgisi,
mutlak yerel yol, serbest uzman notu veya ham exception/stack trace taşınmaz.
Dosya kimliği, source key ve yerel referanslar da dikkat gerektiren metadata'dır.
Bu çalışma otomatik secret detection, redaksiyon, şifreleme veya anonimlik
garantisi vermez. Markdown dinamik metni HTML/Markdown kontrolü ve link
oluşturamayacak biçimde escape edilir; HTML/web arayüzü oluşturulmaz.

Inspector yalnız beş açık yeni çıktıyı okur. Şema, referans, sayımlar, saf
conflict/queue/summary projeksiyonları ve dört payload'ın manifest byte/hash
ilişkisi iç tutarlılık incelemesidir. Eski Phase24 kaynağı, kanıt dosyası,
repository kökü, git kimliği veya üretici bağımsız yeniden doğrulanmaz.

`demo_only=true`; lisans incelemesi, redistribution, release, production,
build, runtime, producer ve human-review doğrulama alanlarının sekizi false
kalır. Source presence, hash eşitliği veya başarılı inspector bu alanları
yükseltmez. Phase7–24 dosyaları, ledger'lar, lisanslar ve teslimatlar korunur.

NOT_RUN: malformed/duplicate JSON, hostile Unicode/kontrol karakteri,
yanlış/eksik kimlik, sahte/çelişen haricî kanıt, değiştirilmiş ledger, yanlış
manifest/hash, boyut/kayıt limitleri, symlink/reparse/hardlink, değişen kaynak,
permission/race/crash/kısmi yazma/power loss, tekrar determinism, gerçek dependency
çözümleme, hukukî/uyumluluk/lisans incelemesi, imzalı binary ve release kabulü.
Kaynak incelemesi ve iki sentetik ürün komutu otomatik test değildir.

Test/runner/coverage/typecheck/build, package manager, dependency veya lisans
indirme, native runtime/scanner, ağ/DNS/API/IdP/PG, Windows/VM/driver/servis/admin,
müşteri/pilot iletişimi, PDF, push/release/deploy yapılmaz. Phase24'ün kapalı
istisnası tekrar komut hakkı değildir. Phase25'in en fazla iki yeni ürün komutu
ve manuel inceleme/tesliminden sonra durulur; yeni faz başlatılmaz.
