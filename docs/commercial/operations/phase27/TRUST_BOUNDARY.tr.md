# Kaynak kanıtı, resolver ve kabul sınırı

**DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Sözleşme](DIRECT_DEPENDENCY_CONTRACT.tr.md), [Rust semantiği](RUST_MANIFEST_SEMANTICS.tr.md),
[ownership](COMPONENT_OWNERSHIP.tr.md).

Source existence, byte/hash identity, manifest declaration, component attribution,
legacy record binding, dependency resolution, build closure, binary/runtime
inclusion, lisans izni ve release onayı ayrı güven seviyeleridir. Bir kaynak
kenarı diğer seviyelerin doğrulandığını göstermez. Pin ve fingerprint imza,
attestation, registry/vendor veya global kalıcı package kimliği değildir.

Yalnız on açık eski artefact, scope ve açık dört Cargo manifesti okunur. Eski
summary'ler manifest byte bağını tamamlar. CLI yolları ve scope manifest seçimi
dışında keşif/tarama yoktur. TOML path/git/URL, workspace member veya native
bin/lib entry metadata'sı başka dosya açtırmaz. F kapsamı dışındaki entry
dosyaları var/doğrulandı sayılmaz. Kaynak kod veya bildirim çalıştırılmaz.

Korunmuş ctime-düzeltilmiş okuyucu; symlink/junction/reparse/traversal ve
hardlink, boyut, okuma boyunca kimlik/değişim kontrolleriyle kullanılır.
Windows lstat/fstat ctime farklı API aileleri arasında eşitlenmez. Kaynak
kararlılığı kontrolü tam atomiklik, TOCTOU veya saldırgan filesystem kabulü
değildir. Yeni output zorunludur; overwrite/eski dosya silme yoktur. Kısmi yeni
dosya veya manifest varlığı tek başına başarılı üretim/onay değildir.

Kapalı metadata allowlist'i; kontrollü relative manifest referansı, SHA256,
TOML field/declaration, id/pointer ve belirsizlik taşır. Ham Cargo/lock/source
gövdesi, tam lisans metni, credential/token, müşteri/özel kişi bilgisi, mutlak
Windows kullanıcı yolu, kontrolsüz serbest metadata ve exception/stack trace
taşınmaz. Metadata minimizasyonu secret detection/redaksiyon/şifreleme veya
anonimlik garantisi değildir. Markdown dinamik metni link/HTML oluşturmayacak
biçimde escape edilir; web arayüzü yoktur.

Inspector yalnız beş yeni açık çıktıdaki kapalı modelleri, referans/count,
normalized inheritance/ownership/binding, source graph/variant overlay/Markdown
ve dört payload byte/hash bağını yeniden türetir. Orijinal Cargo veya eski
artefact'lara, git, package cache veya producer doğrulamasına dönmez. Projected
source identity ve normalized metadata'nın iç tutarlılığı, ham TOML doğruluğunun
veya kaynağın bağımsız yeniden doğrulanması olarak sunulmaz.

Demo true kalır. Resolution, build closure, runtime inclusion, lisans incelemesi,
redistribution, release/production ve ek producer/human/build/runtime doğrulama
alanları false kalır. Kaynak bildirimi lisans kanıtı oluşturmaz; unknown459 veya
önceki review/production engelleri kendiliğinden çözülmez.

NOT_RUN: hostile/malformed/duplicate JSON, bozuk/desteklenmeyen TOML, yanlış
inheritance, renamed/build dependency kenar senaryoları, feature resolution,
target cfg evaluation, Cargo metadata/resolution, çoklu lock version eşleme,
digest manipülasyonu, geçersiz node/edge, graph/file limitleri,
symlink/reparse/hardlink/TOCTOU/race/permission/crash/partial write/power loss,
repeat determinism, native build closure, binary/runtime inclusion,
lisans/producer/hukukî inceleme, production/release. Önceki NOT_RUN kapıları da
kapanmış sayılmaz. Kodda kontrol bulunması saldırgan girdi kabulü değildir.

Test/runner/coverage/typecheck/build, package manager/resolver, dependency
indirme, native scanner/runtime, ağ/DNS/API/IdP/PG/VM/driver/servis/admin,
gerçek müşteri/pilot/satış, hukukî finalizasyon, PDF ve push/release/deploy
yapılmaz. İki izinli ürün komutu ve manuel inceleme/tesliminden sonra durulur;
üçüncü çağrı veya yeni faz başlatılmaz. Browser file:// yasağı başka surface,
sunucu veya hosting üzerinden aşılmaz.
