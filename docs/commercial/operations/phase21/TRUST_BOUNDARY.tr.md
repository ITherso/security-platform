# İzlenebilirlik güven sınırı

**DEMONSTRATION ONLY — PLAN AND ASSESSMENT EXECUTION LINK NOT ESTABLISHED**

Plan intent, assessment beyanı ve execution linkage ayrı bilgi katmanlarıdır.
Phase20 planıyla Phase14 örneğinin aynı çalışmaya ait olduğunu gösteren güvenilir
run bağı yoktur. `execution_binding=not_established` bütün çıktı boyunca sabit
kalır. Şema adı, profil, capability, fingerprint, origin veya aynı dosya seçimi
run kimliği yerine kullanılamaz.

`plan_execution_verified`, `scope_fulfillment_verified`,
`authorization_verified`, `human_review_verified`, `producer_verified`,
`release_authorized`, `execution_authorized` ve `production_ready` false;
`demo_only` true kalır. Bir dosya eşleşmesi bu bayrakları yükseltmez. Gerçek
scope owner, yetki, veri işleme, uzman, kurum ve müşteri kararı ayrı açık
gerekliliklerdir. Araç bu kararları üretmez veya hukukî görüş sunmaz.

Üç farklı dosya bağı vardır:

| Bağ | İncelenen kısım | Doğrulanmayan kısım |
| --- | --- | --- |
| Phase20 dosyaları | Plan/preflight/catalog byte/hash, kapalı sözleşme ve plan içerik ID'si | Original proposal dosyası, plan-summary payload, producer, gerçek native runtime |
| Phase14 partial manifest | Seçili assessment JSON-entry boyut/SHA ve özet ilişkisi | HTML payload ve bütün report bundle, signature/attestation |
| Assessment → Phase17 | Gerçek assessment/map/handoff byte kimlikleri ve observation pointer metadata'sı | Native importer tam kabulü, kanıt doğruluğu, plan → assessment execution |

Plan manifestindeki özet entry'si yalnız metadata olarak doğrulanır; dosyası
açılmaz. Assessment manifestindeki HTML de açılmaz. Gömülü proposal/source path,
URL, manifest entry adı veya evidence referansı başka dosya/ağ okuma talimatı
olamaz. Gerçek dosya kaynağı yalnız dokuz açık CLI argümanıdır.

Kaynak SHA256 içerik bağını gösterir; üretici veya değerlendirme yetkisi değildir.
Phase20'nin 17 native dosya kimliği plan/katalogda bildirilen pinler olarak
korunur; Phase21 güncel native checkout'u veya binary'yi doğruladığını iddia
etmez. Preflight `pending_authorization` engelleri anlamını korur. Planın ve
assessment'ın profil veya capability eşleşmesi kapsam tamamlanması değildir.

Ham assessment başlık/açıklama/remediation/HTTP içeriği ledger'a gömülmez.
Doğrulanan kapalı metadata, fingerprint ve pointer'lar kullanılır. Markdown'da
dinamik metin HTML veya bağlantı talimatı olarak çalıştırılmaz. Yerel dosyalar
şifrelenmez; bu bir anonimleştirme, secret detector, güvenli silme veya ACL
garantisi değildir. Gerçek müşteri/credential bu fazda kullanılmaz.

Yalnız yeni local output dizini, sabit adlar, kontrollü staging, overwrite
etmeyen yayım ve manifest-last yaklaşımı vardır. Mevcut klasör sahiplenilmez.
Hata yeni kısmi dizin bırakabilir; bütün dizinin atomikliği veya hostile
filesystem yarışlarına dayanıklılık kabulü yapılmamıştır.

Native Termivar CLI/scanner/runtime, DNS/HTTP, gerçek target, frontend/server,
servis, canlı API/IdP/PG/Windows/VM/driver/admin, customer contact ve deploy yoktur.
Yeni assessment/comparison, test/runner/coverage/otomatik kabul veya PDF üretilmez.
Manuel kaynak/çıktı incelemesi güvenlik kabulü değildir. Malformed/duplicate/
hostile encoding/namespace/mapping/manifest/path/race/permission/crash ve tekrarlı
determinism davranışları çalıştırılmadıysa **NOT_RUN** kalır.

[Phase20 güven sınırı](../phase20/TRUST_AND_AUTHORIZATION.tr.md) ve önceki
[Phase17 kaynak sınırı](../phase17/TRUST_BOUNDARY.tr.md) değiştirilmez. Gerçek
execution binding, producer/uzman/kurum ve müşteri kabulü açık kalır. Bu fazın
sentetik tesliminden sonra yeni test, gerçek değerlendirme veya sonraki faz
kendiliğinden başlamaz.
