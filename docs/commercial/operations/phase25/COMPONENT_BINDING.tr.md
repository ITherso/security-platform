# Kaynak kayıt kimliği ve kanıt bağı

**DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED**

[Sözleşme](EVIDENCE_CONTRACT.tr.md), [inceleme akışı](LICENSE_REVIEW_WORKFLOW.tr.md),
[güven/veri](TRUST_AND_PRIVACY.tr.md).

Paket adı tek başına eşleşme değildir. Phase24'ün gerçek L kayıt referansı,
subject türü/id'si, ekosistem, bildirilen sürüm, source türü, manifest/lock
kaynağı, ürün kapsamı ve gerçek JSON konumu korunur. Aynı paket adı farklı
declaration veya lock satırlarında ayrı kalır. Eksik sürüm veya `unknown`
kaynak türü isim eşitliğiyle kesinleştirilmez.

Primary row, component için inventory `components` satırı; dependency için eski
ledger `dependencies` satırıdır. SHA256 girdisi tam gerçek satırın UTF-8,
`ensure_ascii=False`, sıralı key, kompakt ayırıcı ve nonfinite içermeyen canonical
JSON gösterimidir. Eski `license_evidence` satırının konumu ve digest'i ayrıca
korunur. Primary row digest'i lisans kaydı digest'inin yerine geçmez.

Yerel source key, `termivar-license-source-binding/v1` kimlik girdisinin
canonical digest'ini `termivar-license-binding/v1:` önekiyle taşır. Kimlik girdisi
source artefact hash'i, primary JSON pointer/digest'i, eski dependency ledger
hash'i ve eski lisans satırı pointer/digest'ini birlikte bağlar. Key yalnız bu
seçilmiş artefact'lar içindeki kaydı belirtir; yayınlanmış paket/vendor kimliği,
üretici doğrulaması veya bütün sürümlerde kalıcı küresel ID değildir.

Binding isteği source L referansı, subject türü/id'si ve primary row digest'ini
tam seçer. Seçici uyuşmazlığı bilinen kayda bağlı bir çatışma olarak görünür;
isimden yedek eşleştirme yapılmaz. Bilinmeyen L referansı kapalı hatadır.

`binding_confirmed_within_source` için gerçek yerel dosya, uyumlu dosya/metadata
biçimi, hash ilişkisi ve subject'in eski `base_source_file_refs` kapsamına giren
bir eşleşme gerekir. First-party license yalnız component'e, dependency license
yalnız dependency'ye bağlanabilir. Yerel MIT dosyası başka dependency'lerin
bilinmeyen lisanslarını çözmez. Haricî kanıt dosyası mevcut olsa bile üreticisi
doğrulanmış kabul edilmez.

Dependency'yi bildiren Cargo.toml veya lock dosyasının tam F/hash eşleşmesi,
belgenin lisans beyanının dependency'ye ait olduğunu kanıtlamaz. Dependency
package metadata/source manifest seçimi ve declaring-manifest/lock dosyasının
dependency license dosyası diye seçilmesi belirsiz bağ olarak kalır. Workspace
MIT beyanı third-party dependency MIT bilgisine çevrilmez. Dosya kimliği,
lisansın o subject'e uygulanabilirliği, üretici ve hukukî karar ayrı sınırlardır.

Beklenen hash farklıysa başarılı bağ kurulmaz. Yalnız metadata, dosya yolu veya
aynı lisans etiketi de yeterli değildir. Farklı içerikler ve farklı literal
lisans beyanları ayrı gözlemlerdir; hukuki uyumluluk veya SPDX eşdeğerliği
otomatik yorumlanmaz. Kaynak kaydı silinmez, bir kanıt sessizce seçilmez.

Demo için mevcut Termivar LICENSE yalnız seçilmiş bir native subject'e yeniden
bağlanır. Phase24'teki ikinci MIT beyanı korunur; ona bu scope'ta yeni dosya
seçilmemesi yeni kanıt durumunda eksikliktir, eski MIT bilgisini silmez. Tüm
451 dependency ve sekiz destek aracının önceki bilinmeyen lisans bilgisi
otomatik değişmez. Gerçek bağlama sonuçları teslim belgesinde kaydedilir.
