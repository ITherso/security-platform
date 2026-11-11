# Bağımlılık ve lisans kanıtı

**DEMONSTRATION ONLY — PRODUCT COMPOSITION REVIEW — NOT AUTHORIZED FOR DISTRIBUTION**

Kaynak incelemesi: native Termivar pin'i `6a2639348c2366d0bf71b9a34e5484d40aa393a3`,
workspace sürümü `0.10.0-alpha.3`, workspace lisans beyanı MIT. Gerçek yerel root
LICENSE 1085 bayt, SHA256
`d308383be39c28054876444bc46a410a5e753c7df982afce644fab1e7e9f754d`.
Bu beyan ve metin iki seçili native kaynak bileşeniyle ilişkilendirilir;
bağımlılıklara veya platform yardımcılarına aktarılmaz.

Seçili root/core/scanner/cli Cargo manifestleri ve root Cargo.lock okunur.
Cargo.lock format4, bütün workspace için 306 paket kaydı içerir; 296 registry
kaydı checksum bildirir, on kayıtta source/checksum yoktur. Yerel path veya
source alanının yokluğu tek başına workspace üyeliği ya da birinci taraf
sahipliği değildir; araç bu kayıtların kaynak türünü `unknown` bırakır.
Lock lisans alanı taşımaz. Bunlar kaynak incelemesi ölçümleridir; gerçek
ürün üretiminde oluşan deklarasyon/lock/kanıt sayımları teslim kaydındadır.

Manifest deklarasyonları ve lock kayıtları ayrı tutulur; sürüm aralığı lock
sürümüyle sessizce birleştirilmez. Workspace dependency havuzu her bileşenin
doğrudan bağımlılığı değildir. Normal/dev/build/target/optional deklarasyonlar
feature aktivasyonu veya seçilen executable'ın kapanışı sayılmaz. Lock satırı
için güvenle belirlenemeyen direct/transitive bağı `unknown` kalır. Araç semver
resolver, Cargo metadata, dependency indirme veya yerel cache taraması yapmaz.
Source URL'leri takip veya render edilmez; yalnız sınırlı kaynak türü ve
source metninin kimlik hash'i taşınabilir. Checksum yerel paketin doğrulanması
veya üretici imzası değildir.

Platform `pyproject.toml`, `requirements-lock.txt`, `requirements-build-lock.txt`
yalnız **excluded_backend_context** olarak kaydedilir. Backend/test/build
deklarasyonları stdlib offline araçların otomatik bağımlılığı değildir.
Pyproject static main/optional/build-system tanımları ve desteklenen açık pin
satırları okunur. Bilinmeyen YAML lock biçimi parsed sayılmaz; yeni parser veya
dependency eklenmez. Desteklenmeyen/eksik kapsam bütün dependency listesinin
eksiksiz doğrulandığı anlamına gelmez.

Platform/helper genel LICENSE/NOTICE ve pyproject lisans alanı bulunmadı.
Phase14 örneklerine ait Termivar MIT kopyası başka bileşenlere hak vermez.
Frontend React notice ayrı ve bu adayın otomatik parçası değildir. Sekiz offline
destek aracının görülen import sınırı stdlib ve kardeş helper'lardır; araçlar
native Termivar runtime veya platform wheel'inin otomatik parçaları değildir.

LicenseEvidence düzeyleri: `local_license_file`, `package_metadata_declaration`,
`source_manifest_declaration`, `not_available`, `conflicting_declarations`.
Her kanıt subject'i, mevcut lisans beyanı, gerçek kaynak dosya hash referansı,
belirsizlikleri ve gerekli insan incelemesini içerir. Kaynaklar çelişirse biri
sessizce seçilmez. Bilinmeyen lisans ezberden veya paket isminden doldurulmaz.
`license_review_required` korunur; `redistribution_authorized=false`.

Lisans metni bulunması ticari kullanım veya dağıtım kararı değildir. Bu çalışma
hukuki görüş, SBOM standardı sertifikası veya bütün üçüncü taraf içeriklerin
clearance'ı değildir. Yetkili inceleme ve gerçek dağıtım modeli kararı açık kalır.
