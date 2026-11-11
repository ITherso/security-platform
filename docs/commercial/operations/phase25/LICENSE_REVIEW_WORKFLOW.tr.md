# Kanıt bağlama ve insan incelemesine hazırlık

**DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED**

[Sözleşme](EVIDENCE_CONTRACT.tr.md), [kayıt bağı](COMPONENT_BINDING.tr.md),
[güven/veri](TRUST_AND_PRIVACY.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).

1. Mevcut Phase24'ün beş açık dosyasını ve beklenen byte kimliklerini seç.
2. Gerçek kaynak lisans kaydını L referansı, subject ve primary row digest'iyle
   belirt. Aynı isimli farklı satırları birleştirme.
3. Yalnız mevcut, açık seçilmiş yerel belgeyi evidence olarak ekle. Belge yoksa
   `missing_evidence` ve null dosya alanları kullan; örnek lisans metni üretme.
4. Üretimde okunan dosya boyut/hash'i, biçim gözlemi ve kaynak dosya ref'i ayrı
   kaydedilir. Belge içindeki path/URL takip edilmez.
5. Kaynak bağı, eksiklikler ve çakışma bildirimlerini incele. İnsan kararı
   gerektiren belirsizlikler açık kalır; bu araç onay kararı almaz.

Desteklenen türler: `first_party_license_file`, `dependency_license_file`,
`package_metadata`, `source_manifest_declaration`, `unverified_external_evidence`,
`missing_evidence`. Bunlar lisans veya hukukî güven sınıfı değildir. Metadata
etiketi tam lisans metni değildir. Bu demo yeni haricî belge indirmez.
Dependency'yi bildiren manifestin lisans beyanı o dependency'nin lisansı olarak
bağlanmaz; exact dosya kimliği bile bu uygulanabilirlik bağını tek başına kurmaz.

Salt okunur queue her kaynak kaydını bir kez temsil eder. Gruplar:
`conflicting_evidence`, `ambiguous_binding`, `missing_evidence`,
`evidence_present_review_pending`, `unsupported_evidence`. Bir satır birden
fazla neden/grup taşıyabilir; group membership toplamı benzersiz kaynak kaydı
sayısından ayrı raporlanır. Sıra deterministiktir; risk, hukukî öncelik, SLA,
görev ataması veya ticari önem değildir.

Kaynak kanıtı mevcut ama inceleme bekleyen kayıt, eksik kanıtlı kayıt ve
belirsiz kaynak bağı ayrı tutulur. Kapsam `proposed_source_component`,
`selected_source_metadata` veya `excluded_backend_context` olarak korunur.
Backend context, offline destek araçlarının runtime bağımlılığı veya zorunlu
dağıtım bileşeni sayılmaz. Declaration/lock satırı sayısı benzersiz paket
sayısıyla eşit kabul edilmez.

Conflict dosyası tekrarlanan içerik, farklı içerik, farklı lisans beyanları,
belirsiz bağ, doğrulanmamış kaynak, açık istekte eksik dosya, hash uyuşmazlığı,
desteklenmeyen evidence ve kaynak seçicisi uyuşmazlığını ayırır. Eksik dosya
bildirimi bir lisans çelişkisi değildir. Hiç olay bulunmaması da hukukî
uyumluluk kanıtı değildir. İstenmeyen her kayıt için sahte conflict üretilmez.

Başlangıçtaki 461 kayıt ve 459 bilinmeyen lisans korunur. Demo scope bir mevcut
native LICENSE bağını ve bir açık eksik dependency kanıtını göstermek içindir.
Diğer kayıtlara yeni evidence seçilmez. Başarılı tek yeni bağ ve 460 yeni-kanıt
eksikliği görülmesi, 460 lisansın bilinmediği anlamına gelmez: ikinci eski MIT
beyanı ayrıca korunur. Bu örnek değerler gerçek teslim sonucuyla doğrulanır.

Her kayıtta `human_review_required=true` ve
`phase24_license_review_required=true` kalır. Gerçek reviewer, hukukçu,
kurum temsilcisi, tarih, imza veya onay oluşturulmaz. Lisans koşulu, copyleft,
patent/marka, ticari kullanım veya yeniden dağıtım kararı kesinleştirilmez.
Phase24 blocker'ları değiştirilmez; `license_review_completed=false`,
`redistribution_authorized=false`, `release_authorized=false` ve
`production_ready=false` korunur.
