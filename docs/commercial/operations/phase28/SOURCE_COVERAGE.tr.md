# Phase28 kaynak giriş noktası kapsamı

**DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED**

Araç yalnız seçilmiş gerçek Cargo manifestlerindeki `[lib]` ve `[[bin]]` alanlarını inceler. Target adı bir component veya executable kimliği değildir. Kesin target-to-file ilişkisi için manifestte explicit `path` gerekir; path yoksa `entrypoint_not_established` korunur.

Cargo'nun otomatik src/main.rs veya src/lib.rs keşfi, workspace üyelerinden target üretme, examples/tests/benches tarama, build.rs çalıştırma ve Rust module/import graph çözümü yapılmaz. Manifestte yeni bir yol görülmesi dosyayı okumaya yetki vermez.

## Allowlist ve dosya gözlemi

Önce kaynak manifest/root/pin kimliği, güvenli normalize relative path, scope'taki manifest/target ilişkisi ve exact allowlist eşleşmesi aranır. Yalnız izinli regular file'ın varlığı, byte boyutu, SHA256 ve okuma öncesi/sonrası kimlik stabilitesi incelenir. Kaynak gövdesi model, JSON, Markdown, log veya ZIP'e kopyalanmaz.

Dosya okuyucu yalnız `present_and_hashed` veya `declared_file_missing` gözlemi üretir. Eksik dosyada boyut/hash ve regular-file kanıtı null kalır. Allowlist dışı target için dosya gözlemi uydurulmaz; `read_not_performed`, fiziksel dosya yokluğu değildir. Güvensiz dosya türü, kaynak kimlik/hash uyuşmazlığı veya okuma sırasında değişim başarılı gözlem yerine kapalı hata oluşturur. Hash gözlemi üretici, Git commit, derlemeye giriş veya güvenlik kanıtı değildir.

## Phase24 F semantiği

Korunmuş gerçek envanterin global `inventory.files` kataloğunda 111 F satırı vardır. Component `source_file_refs` birleşimi 107 farklı F referansıdır. Birleşimin dışındaki 4 kayıt:

| F | Mevcut kaynak bağlamı |
| --- | --- |
| F0005 | Excluded backend requirements |
| F0006 | Excluded backend lock |
| F0086 | Cargo.lock; explicit selected-source metadata |
| F0088 | LICENSE; local license file |

F satırlarında genel `selected`, `metadata_only` veya `excluded` alanı yoktur. Yeni araç bütün F satırlarına böyle bir sınıf atamaz. Component referansında olmamak otomatik excluded değildir; bulunmak runtime inclusion değildir. F0004 ortak pyproject, sekiz helper için ayrı runtime dependency/distribution kanıtı değildir. F0086 ve F0088'in kendi kaynak bağlamı korunur.

Katalog ilişkileri `listed_in_global_f_catalog` / `not_listed_in_global_f_catalog`, component bağı `referenced_by_component` / `not_referenced_by_component`, desteklenmeyen kapsam niteliği `scope_classification_unknown` olarak ayrılır. Eski isimde selected-source ifadesi bulunması, eski F satırlarında yeni bir selected bayrağı bulunduğu anlamına gelmez.

## Coverage kararı

Eşleme yalnız path benzerliğine dayanmaz: repository/root, pin, relative path, dosya türü, eski byte/hash ve F/component bağları kullanılır. Yeni SHA256, eski artefact'ta eksik kimliği geriye dönük doldurmaz. Katalog üyeliği ile eski byte/hash eşitliği ayrı gösterilir.

`source_present_inventory_gap`, izinli dosyanın gerçekten hash'lendiği fakat global F kataloğunda bulunmadığı dar durumdur. Envanter eksiği, dosyanın fiziksel yokluğu değildir. Mevcut F satırına güvenilir bağ kurulamazsa kesin coverage üretilmez. Component ownership durumu ayrıca taşınır; aynı dosya için kapsam boşluğu ve çözülmemiş ownership birlikte bulunabilir.

Görevde bildirilen core/scanner lib veCLI bin kaynakları yalnız demo allowlist adaylarıdır. Üç gerçek coverage gap sonucu ve ölçülen byte/hash değerleri ancak yeni assembly sonrasında [teslim kaydına](DEMO_DELIVERY.tr.md) yazılır. Bu gözlem tüm kaynak ağacının completeness kabulü değildir.
