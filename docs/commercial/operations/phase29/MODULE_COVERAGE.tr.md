# Phase29 module coverage sınırları

**DEMONSTRATION ONLY — RUST SOURCE REFERENCES — NO MODULE CLOSURE OR BUILD AUTHORIZED**

Coverage projection, gözlenen source reference ile gerçek allowlisted dosyayı ayırır. External mod declaration kesin dosya bağı değildir. Aynı isimli referanslar source SHA256, konum ve lexical scope kaybedilerek birleştirilmez.

## Graph semantiği

Source contains reference ve güvenilir explicit file naming, yalnız kendi sınırlı kaynak ilişkisini belirtir. Reference bound to observed file için desteklenen literal path, güvenli relative base, izinli root, exact allowlist, regular-file ve gerçek byte/SHA256 gözlemi gerekir. Olası dosya ilişkisi, unresolved ilişki ve conditional unresolved ilişki ayrı edge türü/certainty olarak sayılır.

External mod adından path veya candidate file üretilmez. not_allowlisted, file_missing, unsupported_reference ve unresolved birbirinin yerine kullanılmaz. Çözülemeyen referans graph'tan sessizce çıkarılmaz. Sıfır kesin file-binding, kaynak böyle destekliyorsa dürüst bir sonuçtur; sahte pozitif kenarla yükseltilmez.

## Phase24 F membership

Mevcut global F kataloğu 111; component source_file_refs birleşimi 107 F'dir. Genel selected/excluded/metadata_only bayrağı yoktur. Yalnız listed_in_global_f_catalog/not_listed_in_global_f_catalog, referenced_by_component/not_referenced_by_component ve scope_classification_unknown ilişkileri gösterilir. Katalog üyeliği, eski byte/hash eşitliği ve component ownership ayrıca değerlendirilir.

Component referansında bulunmamak otomatik excluded veya unused değildir; bulunmak gerçek runtime inclusion değildir. F0005/F0006 backend-context, F0086 Cargo.lock metadata ve F0088 yerel LICENSE bağlamları component birleşimi dışında kaldığı için değiştirilmez. Ortak pyproject helper runtime sahipliği oluşturmaz.

## Phase28 katmanı

EPF0001 core lib, EPF0002 scanner lib ve EPF0003 CLI bin kimlikleri korunur. Bunların explicit target ilişkisi, yeni lexical gözlemden ayrı kanıttır. Önceki üç repository-level source inclusion önerisi uygulanmamış kalır. Yeni F numarası veya Phase28 delta kaydı yazılmaz. Yeni modül kaynak boşluğu yalnız Phase29 coverage gözlemidir.

Phase27/28 kesin owner sayısı 0'dır. Yeni modül referansı, core primary bağı veya scanner/CLI ortak scope belirsizliğini çözmez. component_ownership_verified her zaman false kalır.

observed_static_reference, observed_allowlisted_file, unresolved_reference, source_inventory_gap ve module_closure_not_verified ayrı tutulur. Bir referansın çözülememesi dosyanın fiziksel yokluğunu kanıtlamaz. Bütün gözlenen referanslar bağlansa dahi macro/conditional/generated source ve desteklenmeyen Rust semantiği nedeniyle tam module closure ve source completeness doğrulanmış olmaz.
