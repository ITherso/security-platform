# Lisans kanıtı ve açık hazırlık engelleri

**DEMONSTRATION ONLY — PILOT VARIANT ANALYSIS — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Sözleşme](VARIANT_CONTRACT.tr.md), [exposure](DEPENDENCY_EXPOSURE.tr.md),
[güven sınırı](TRUST_BOUNDARY.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).

Phase25'in 461 lisans subject'i, gerçek L referansı ve artefact'a özgü source
key/pointer/digest bağıyla korunur. Bu kayıtlar 451 dependency satırıyla aynı
envanter değildir: on first-party component lisans kaydı da vardır. Aynı isimli
declaration/lock satırları birleştirilmez. Yerel binding key paket yayını veya
vendor kimliği değildir.

Eski lisans beyanı, yeni evidence durumu ve insan incelemesi ayrı alanlardır.
Başlangıçta iki scoped MIT beyanı ve 459 bilinmeyen lisans; bir yeni kaynak içi
evidence bağı ve 460 yeni kanıt eksikliği vardır. Bilinen ikinci MIT kaydına bu
scope'ta yeni kanıt seçilmemesi eski MIT beyanını silmez. 460 yeni evidence
eksikliği, 460 bilinmeyen lisans demek değildir.

Yeni yerel LICENSE bağı yalnız L0001/termivar-assessment-core kaydına aittir.
L0002'ye, diğer helper'lara veya Rust dependency'lerine yayılmaz. Belgenin
byte/hash kimliği, lisansın dependency'ye uygulanabilirliği, üretici ve hukukî
dağıtım izni ayrı sınırlardır. Phase26 yeni kanıt okumaz veya bağlamaz; eski
evidence metadata'sını varyant ilişkisiyle gösterir.

Varyant lisans özetleri ayrı paydalar taşır: seçilmiş component, seçilmemiş
component, kaynak ilişkisi bulunan dependency, unattributed dependency ve
excluded backend-context. Sadece seçilmiş component sayısı gösterilerek diğer
lisans kayıtları kaybolmuş veya artık gerekli değilmiş gibi sunulmaz. Her 461
kaydın insan inceleme gereksinimi korunur; `unknown`, varyant seçimi nedeniyle
approved/resolved/not_required yapılmaz.

Phase24'ün kaynak blocker'ları kendi kodu, subject ve varyant ilişki kategorisi
ile sayılır. Seçilmemiş, belirsiz ve excluded kayıtların engelleri görünür
kalır; otomatik kapatılmaz. Candidate düzeyindeki build/runtime, veri işleme
ve release yetkisi eksiklikleri her varyant için açıktır. Kaynak lisans metninin
varlığı build, binary–source bağı veya gerçek dağıtım onayı değildir.

Eksik evidence olayı lisans çelişkisi değildir. Farklı içerik veya literal
etiketler hukukî uyumluluk kararı değildir. Evidence binding confirmed durumu
kaynak içi eşleşmedir; `producer_verified` ve `human_review_verified` false
kalır. Gerçek reviewer, hukukçu, owner, tarih, imza, onay veya risk puanı
üretilmez.

Her varyant demo'dur. Dependency closure, license review, redistribution,
build/runtime, producer, release ve production doğrulaması false kalır.
Daha az component seçimi daha güvenli, hukukî olarak uygun veya production-ready
olma sonucu üretmez. Phase14 müşteri talebi/ödeme isteği `not_validated` ve
pilot GO eksikliği bu karşılaştırmayla kapanmaz.
