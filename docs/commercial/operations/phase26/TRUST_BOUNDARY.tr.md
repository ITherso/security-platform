# Kaynak, exposure ve gerçek kabul sınırı

**DEMONSTRATION ONLY — PILOT VARIANT ANALYSIS — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Sözleşme](VARIANT_CONTRACT.tr.md), [exposure](DEPENDENCY_EXPOSURE.tr.md),
[lisans/readiness](LICENSE_AND_READINESS.tr.md).

Kaynak dosyasının varlığı, içerik hash'i, manifest tutarlılığı, potansiyel
dependency kaynak ilişkisi, gerçek build closure, lisansın uygulanabilirliği,
hukukî redistribution izni ve production kabulü ayrı olgulardır. Birinin
varlığı diğerlerini otomatik kanıtlamaz. Candidate scope gerçek paket içeriği
değildir; exposure dependency resolution değildir; evidence present dağıtım
yetkisi değildir; source inventory başarılı build değildir.

Kaynak pinleri eski inventory'de bulunan deklaratif commit metadata'sıdır;
git, producer veya build attestation oluşturulmaz. Phase24/25 dosyaları gerçek
byte/hash ilişkileriyle seçilir. İki fazın composition identity/source pin ve
subject ilişkisi uyuşmazsa sessiz fallback yoktur. Önceki dosyalar korunur.

Yalnız açık CLI yolları okunur. Dosya gövdesindeki path/URL yeni okuma, indirme,
resolver veya komut başlatmaz. Eski güvenli okuyucu değiştirilmeden yeniden
kullanılır: symlink/junction/reparse/path traversal ve hardlink kontrolleri,
okuma boyunca kimlik/boyut/değişim incelemesi korunur. Windows lstat/fstat ctime
farklı API aileleri arasında doğrudan eşitlenmez. Kaynak kararlılığı denetimi
filesystem race veya saldırgan girdi kabulü değildir.

Yeni output dizini ve overwrite etmeyen yayım kullanılır. Dört payload ve son
manifest yayımlanır. Kısmi yeni dosyalar başarılı süreç sayılmaz; hata eski
dosyaları silmez. Tam atomiklik, crash/power-loss veya güvenli silme kabulü
verilmez.

Çıktılar kapalı ve sınırlı metadata projeksiyonudur. Ham lock/manifest, kaynak
kodu veya lisans metni, credential/token/API anahtarı, müşteri/özel kullanıcı
bilgisi, mutlak kullanıcı yolu, kontrolsüz serbest metadata ve exception/stack
trace taşınmaz. Repo-relative manifest metadata'sı, paket adı ve digest bile
dikkat gerektiren bilgi olabilir. Otomatik secret detection, redaksiyon,
şifreleme veya anonimlik garantisi yoktur. Markdown metni link veya HTML
oluşturamayacak biçimde escape edilir; web arayüzü eklenmez.

Inspector yalnız beş açık yeni çıktı dosyasını okur. Kapalı modeller, referans,
sayım, component seçimi, F-association/exposure, karşılaştırma/readiness/Markdown
ve dört payload'ın manifest hash bağını iç tutarlılık düzeyinde inceler.
Eski Phase24/25 dosyaları, source root, evidence, git veya package cache tekrar
açılmaz. Projeksiyondan ham primary source row/üretici doğruluğu yeniden
doğrulanamaz; iç tutarlılık bağımsız kaynak doğrulaması olarak sunulmaz.

NOT_RUN: malformed/duplicate JSON, hostile encoding, yanlış source/binding
digest, değiştirilmiş ledger, sahte/çelişkili kanıt, geçersiz kimlik, limit
aşımı, symlink/reparse/hardlink, permission/race/crash/kısmi yazma/power loss,
tekrar determinism, dependency resolution, native build closure, binary
analizi, hukukî lisans incelemesi, runtime/production kabulü, müşteri pilotu ve
ödeme isteği doğrulaması. Korumanın kodda bulunması bu kontrollerin geçtiği
anlamına gelmez.

Test/runner/coverage/typecheck/build, package manager, dependency indirme veya
çözümleme, native scanner/runtime, ağ/DNS/API/IdP/PG/VM/driver/servis/admin,
gerçek müşteri/satış/pilot iletişimi, hukukî finalizasyon, PDF, push/release/
deploy yoktur. Phase26 en fazla iki yeni ürün komutu ve manuel inceleme/teslim
ile biter; eski sayaçlar ve kapalı Phase24 istisnası yeniden kullanılmaz.
