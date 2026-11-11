# Phase30 güven ve mahremiyet sınırı

**DEMONSTRATION ONLY — RUST MODULE CANDIDATE EVIDENCE — NO COMPILER RESOLUTION VERIFIED**

Candidate fiziksel varlığı yalnız dosya gözlemidir. SHA256 içerik kimliğidir; producer authentication, pinlenmiş Git tree, compiler resolution, module closure, binary inclusion veya lisans/dağıtım yetkisi değildir. Açık operator candidate, insan/uzman onayına yükseltilmez.

Yalnız exact allowlist binding'leri filesystem gözlemine izin verir. Diğer path için exists/stat/open yapılmaz. Root/relative path, parent chain, regular-file, symlink/junction/reparse, hardlink/alias ve okuma öncesi/sonrası kimlik kontrolleri korunur. Windows ctime yalnız aynı API ailesi içinde karşılaştırılır; Path.resolve sonucu tek başına güvenlik kanıtı değildir. Kontroller atomik hostile-filesystem snapshot veya TOCTOU kabulü sağlamaz.

Reader en fazla 64 KiB parçalarda hash'ler; body decode/parse edilmez, yeni modül takip edilmez. Raw Rust, serbest snippet, absolute Termivar root, ham nested JSON veya dinamik URL JSON/Markdown/log/ZIP'e taşınmaz. Gösterilen relative path, module name ve identifier da hassas olabilir; metadata allowlist secret detection, şifreleme veya anonimlik garantisi değildir. Metin inert olarak escape edilir; dosya yolları çalıştırılabilir link sayılmaz.

Eski düzeltilmiş Phase29 gerçek referanslar, 0 exact file-binding, Phase24 F kataloğu, 3 uygulanmamış Phase28 delta, 0 kesin owner, 451 dependency/6 belirsiz D ve 459 unknown lisans korunur. Yerel dosya gözlemi eski insan/lisans/release engellerini kapatmaz; scoped MIT beyanları candidate ilişkilerine yayılmaz.

demo_only=true; compiler_resolution_verified, module_closure_verified, source_inventory_updated, scope_delta_applied, component_ownership_verified, dependency_closure_verified, build_verified, runtime_verified, producer_verified, human_review_verified, license_review_completed, redistribution_authorized, release_authorized ve production_ready false kalır.

Inspector yalnız beş yeni metadata dosyasının kapalı model, ID/ref/count/Markdown ve gerçek byte/hash bağını inceler. Candidate dosyalarını, Phase29 lexer'ını veya Phase24 kaynaklarını yeniden açmaz. content_consistent lexical doğruluk, compiler/AST/module resolution, source completeness, producer veya release kabulü değildir.

NOT_RUN: hostile/duplicate/malformed JSON; UTF-8/Unicode uç durumları; reference/parent/path/hash manipülasyonu; traversal/symlink/junction/reparse/hardlink; TOCTOU/permission/filesystem/değişim yarışı; byte/kayıt limit saldırıları; crash/partial write/power-loss; repeat determinism; Rust compiler/AST/module resolution; cfg/feature/target/macro expansion; module closure/build/runtime; producer/Git attestation; ownership; hukukî/uzman/kurumsal/release/production kabulü. Önceki açık kapılar korunur.

Test/runner/coverage/typecheck/build/install/package manager, native runtime, ağ/DNS/hedef/API/IdP/PG/VM/driver/servis/admin, müşteri/pilot/satış, hukukî finalizasyon, PDF, push/release/deploy yapılmaz. file:// yasağı dolaylı yüzeyle aşılmaz. En fazla iki Phase30 ürün çağrısı ve ölçülmüş teslim sonrası durulur; eski sayaç/istisna açılmaz, üçüncü çağrı veya Phase31 başlatılmaz.
