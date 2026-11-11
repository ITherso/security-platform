# Phase28 güven ve mahremiyet sınırı

**DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED**

Manifest target bildirimi → explicit path → izinli dosya → gözlenen byte/SHA256 → F membership → uygulanmamış delta → varyant projection zincirinin her adımı kendi kanıtını taşır. Dosya varlığı, içerik kimliği, component ownership, gerçek build ve release ayrı güven seviyeleridir.

## Veri sınırı

Yalnız scope'ta açık eski artefact, Cargo manifesti ve target-source allowlist'i okunur. Metadata içindeki URL, git/path dependency, başka target dosyası veya Rust module yolu otomatik takip edilmez. Recursive keşif, arka plan tarama, native execution, ağ veya resolver yoktur.

Target kaynak dosyaları en fazla 64 KiB parçalarda hash'lenir. Gövdeleri JSON/Markdown/log/ZIP'e taşınmaz; yalnız sınırlı referans, varlık, boyut/hash ve ilişki metadata'sı raporlanır. Ürün özeti ham JSON, script, dış link veya mutlak yerel root yayımlamaz. Metadata allowlist'i secret detection, şifreleme veya anonimlik garantisi değildir; relative path, target veya package adı da hassas olabilir.

Symlink/junction/reparse/path traversal, regular-file, kaynak root ve okuma stabilitesi korumaları uygulanır. Hardlink, TOCTOU ve permission/crash/race sınırları açık kalır. Windows ctime için aynı API ailesi kimlik yaklaşımı korunur. Kodda koruma bulunması saldırgan girdilerle kabulün çalıştırıldığı anlamına gelmez.

## Güven bayrakları

`demo_only=true` kalır. `source_inventory_updated`, `scope_delta_applied`, `component_ownership_verified`, `dependency_closure_verified`, `build_verified`, `runtime_verified`, `producer_verified`, `human_review_verified`, `license_review_completed`, `redistribution_authorized`, `release_authorized` ve `production_ready` false kalır. Dosya hash'lenmesi bunları yükseltmez.

Phase27 ownership belirsizliği ve 95 tekil/6 belirsiz legacy declaration binding korunur. Eski 451 dependency kaydı, 459 unknown lisans, 2 eski scoped MIT beyanı, 1 önceki fresh evidence/460 missing, 461 insan incelemesi ve 1377 açık blocker değişmez. Yeni target/file veya delta ilişkisi lisans kanıtı, producer yetkisi veya ticari onay oluşturmaz.

Inspector yalnız beş yeni çıktıdaki kapalı model, ilişki, sayım, Markdown ve gerçek byte/hash bağının iç tutarlılığını inceler. Eski artefact, native dosya gövdesi veya gerçek Git kaynak otoritesini yeniden doğrulamaz. `content_consistent` test, source completeness, başarılı build veya hukukî kabul değildir.

## Açık kabul kapıları

NOT_RUN: malformed/duplicate/hostile JSON; bozuk/desteklenmeyen TOML; yanlış target path; allowlist dışı dosya; kaynak/hash manipülasyonu; symlink/junction/reparse/hardlink; path traversal/TOCTOU; değişim/permission/filesystem race; limit aşımı; crash/partial write/power-loss; tekrar determinism; Cargo auto target keşfi; Rust module graph; gerçek source completeness; native build/runtime; dependency closure; üretici/Git attestation; insan/uzman/hukukî onay; production/release. Önceki kabul kapıları da kapanmaz.

Otomatik test/runner/coverage/typecheck/build/install, Cargo metadata/check/test/resolver, scanner/native runtime, canlı hedef/ağ/DNS/API/IdP/PG/VM/driver/servis/admin, müşteri/pilot/satış, hukukî finalizasyon, PDF, push/release/deploy yapılmaz. file:// yasağı sunucu/hosting/alternatif tarayıcıyla aşılmaz. İzinli iki ürün çağrısı ve ölçülmüş teslimattan sonra durulur; üçüncü çağrı veya yeni faz başlatılmaz.
