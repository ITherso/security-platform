# Statik Cargo bildirimlerinin anlamı

**DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Sözleşme](DIRECT_DEPENDENCY_CONTRACT.tr.md), [ownership](COMPONENT_OWNERSHIP.tr.md),
[güven sınırı](TRUST_BOUNDARY.tr.md).

Yalnız açık seçilmiş root/core/scanner/cli Cargo.toml byte'ları stdlib tomllib
ile incelenir. Cargo/metadata/compiler/resolver çalışmaz; Cargo.lock yeniden
ayrıştırılmaz. Korunmuş Phase24 declaration projection yardımcıları uygun
yerlerde yeniden kullanılır; ikinci bir paket yöneticisi oluşturulmaz.

Workspace dependency pool ile crate bildirimi ayrıdır. Root template her
crate'e yayılmaz. Çocuk bildirimin açık workspace=true kullanımı, gerçek root
template id'si ve kaynak kimliğiyle eşleşirse inheritance kaydedilir. Çocuk ve
root feature/default-feature metadata'sı ayrı tutulur; etkin bir union veya
resolution sonucu üretilmez. Eksik/uyumsuz inheritance kesin edge değildir.
Bu statik bağ için çocuk crate dizininin açık literal workspace member olması,
exclude listesinde bulunmaması ve package.workspace override bildirilmemesi
ayrıca aranır. Üyelik glob'u genişletilmez, override path'i takip edilmez;
kurulamayan üyelik/override bağı insufficient_source_evidence kalır. Üyelik ve
exclude metadata'sı gerçek Cargo resolution sonucu değildir.

Normal, dev, build ve target-specific bölümler ayrı kind/target/TOML field path
taşır. Dependency anahtarı, varsa renamed package adı, requirement, source kind
ve locator hash'i ayrıdır. Ham git/path/URL çıktı veya yeni okuma kaynağı olmaz.
Requirement kesin lock sürümü değildir. Optional alanının verilmemiş olması
false yazılarak kaynak beyanına dönüştürülmez; local metadata korunur.

Optional, dev/build veya target koşulu bildirimi saklanır. Feature tanımları ve
istenen feature adları kaynak metadata'sıdır; Cargo feature graph çözülmez.
`activation_unknown` ve `target_evaluation=not_performed` korunur. Cfg string'i
aktif/pasif değerlendirilmez. Dev/build kind gerçek runtime inclusion veya
runtime yokluğu kanıtı değildir.

Source declaration yerel id'si source file hash'i ve gerçek TOML alan konumuna
bağlıdır. Aynı isim başka manifest veya bölümde geçince kayıt birleştirilmez.
Fingerprint metadata içerik kimliğidir; üretici imzası veya registry id değildir.

Phase24 binding yalnız mevcut declaration satırlarının bütün bilinen legacy
projection alanları ve manifest/scope ile yapılır. Eski modelin taşımadığı
kind/target/feature/git-selector ayrımları eksik alanlar olarak açıklanır.
Birden fazla aynı eski projection varsa bütün aday D id'ler korunur; yeni
ordinal/field bilgisiyle bir eski satır keyfî seçilmez. Definite binding sadece
bu metadata sınırındadır, component ownership veya resolved dependency değildir.

Gerçek korunacak çiftler serde_json D0039/D0041, termivar-oast D0044/D0076 ve
tokio-rustls D0070/D0077'dir. Bu üç aday kümesi altı eski D kaydı içerir; kaynak
kanıtı yokken tek eşleme yapılmaz. Lock340 ve Python declaration10, source
declaration grafiğine isim/semver eşlemesiyle bağlanmaz; global D düğümleri kalır.

Desteklenmeyen semantik kapalı hata veya açık insufficient_source_evidence
olarak kalır. Kaynakta bulunmayan renamed/build fixture, target evaluator veya
feature activation sonucu üretilmez. Kodda destek dalı bulunması bu dalların
gerçek çalışma zamanı kabulü değildir; NOT_RUN listesi teslimde açık tutulur.
