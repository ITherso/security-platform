# Phase29 güven ve mahremiyet sınırı

**DEMONSTRATION ONLY — RUST SOURCE REFERENCES — NO MODULE CLOSURE OR BUILD AUTHORIZED**

Dosya varlığı → byte/SHA256 → lexical observation → explicit literal path → allowlist → gözlenen file-binding ayrı kanıtlardır. Bunlar etkin build koşulunu, component ownership'yi veya gerçek build/runtime/release kabulünü otomatik doğrulamaz. Hash ve yerel deterministik ID imza veya Git/producer attestation değildir.

Yalnız açık eski artefact ve Rust source allowlist okunur. Kaynak içindeki path/URL, external mod adı, macro veya import yeni dosya açma yetkisi değildir. Recursive keşif, Cargo/compiler resolver, macro/env/build-script çalıştırma veya canlı ağ yoktur. Rust kaynak metni yalnız bounded geçici bellekte incelenebilir; gövde/snippet/raw condition/macro argümanı JSON/Markdown/log/ZIP'e taşınmaz. İzinli kısa identifier/path ve konum metadata'sı hassas olabilir; allowlist secret detection, anonimleştirme veya şifreleme garantisi değildir.

Root/relative path, regular-file, symlink/junction/reparse, hardlink/alias ve okuma öncesi/sonrası kimlik korumaları uygulanır. Windows ctime yalnız aynı API ailesi içinde karşılaştırılır. Taşınabilir kontroller saldırgan dosya sisteminin atomik snapshot'ı değildir; TOCTOU/permission/race/crash kapıları açık kalır.

demo_only=true kalır. source_inventory_updated, scope_delta_applied, component_ownership_verified, dependency_closure_verified, module_closure_verified, build_verified, runtime_verified, producer_verified, human_review_verified, license_review_completed, redistribution_authorized, release_authorized ve production_ready false kalır. Eski 451 dependency, 6 belirsiz D, 461 lisans subject'i/459 unknown, 1 önceki fresh evidence/460 missing ve insan/release engelleri değişmez. İki scoped MIT beyanı yeni dosya ilişkilerine yayılmaz.

Inspector yalnız beş yeni dosyanın model/ref/count/Markdown ve byte/hash tutarlılığını inceler. Rust gövdelerini okumaz, lexer/classifier'ı yeniden çalıştırmaz, eski Phase24/27/28 kaynaklarını yeniden doğrulamaz. content_consistent, Rust lexical yorumunun dil açısından doğruluğu veya gerçek module closure kabulü değildir.

NOT_RUN: hostile/duplicate/malformed JSON; UTF-8/BOM kenarları; kapanmamış string/nested comment; karmaşık raw delimiter; char/lifetime; macro token tree/procedural macro; cfg_attr path alternatifleri; desteklenmeyen lexical yapılar; Rust AST/module resolution; generated source; feature/target evaluation; traversal/symlink/junction/reparse/hardlink; TOCTOU/filesystem race; source/hash manipülasyonu; token/node/byte limitleri; crash/partial write/power-loss; repeat determinism; gerçek build/scanner/runtime; module closure/source completeness; producer/Git attestation; component ownership; uzman/hukukî/release/production kabulü. Koruma kodu bu kabullerin geçtiği anlamına gelmez; önceki açık kapılar kapanmaz.

Test/runner/coverage/typecheck/build/install/package manager, native runtime, ağ/DNS/hedef/API/IdP/PG/VM/driver/servis/admin, müşteri/pilot/satış, hukukî finalizasyon, PDF, push/release/deploy yapılmaz. file:// yasağı dolaylı yüzeyle aşılmaz. En fazla iki root ürün çağrısı ve ölçülmüş teslimden sonra durulur; üçüncü çağrı veya Phase30 başlatılmaz.
