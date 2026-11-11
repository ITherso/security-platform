# Güven, kaynak kimliği ve çalışma yetkisi

**DEMONSTRATION ONLY — NO TARGET ASSESSED — NO EXECUTION AUTHORIZED**

Kapsam önerisinin kaynakla eşleşmesi tarama yetkisi vermez. Her JSON çıktısı ve
Markdown özeti `demo_only=true`, `execution_authorized=false`,
`authorization_verified=false`, `production_ready=false` sınırını korur.
Girdideki `authorization_status=not_provided` ve
`data_handling_status=pending_decision` değiştirilemez. `authorized`,
`approved_by`, credential, force veya production override alanları yoktur;
unknown field reddedilir.

İnsan kararı gereken başlıklar scope owner, authorization, data handling,
human review ve runtime qualification'dır. Proposal bu başlıkları listeden
çıkarsa da engeller kaldırılmaz. Gerçek hukuki onay, sahiplik, kurum/müşteri
ilişkisi, veri işleme izni ve zaman penceresi doğrulanmaz. Scope ve authority
modelleri teknik kısıttır, hukuki görüş değildir.

Bu çalışma [Phase14 kapsam sınırını](../../PILOT_SCOPE.tr.md) ve
[Phase15 case kaydını](../templates/CASE_RECORD.template.md) genişletmez.
[Phase17 güven sınırı](../phase17/TRUST_BOUNDARY.tr.md),
[Phase18 güven sınırı](../phase18/TRUST_BOUNDARY.tr.md) ve
[Phase19 kaynak sınırı](../phase19/SOURCE_AND_TRUST_BOUNDARY.tr.md) korunur.
Review kararları, customer handoff, gerçek pilot veya release üretilmez.

Plan kimliği, ID alanı hariç sürümlü ve sıralı JSON temsilinin SHA256 değeridir.
Bu temsil gerçek proposal dosyası SHA256'sını, gerçek katalog byte SHA256'sını,
pinlenmiş native commit'i ve incelenen kaynakların gerçek SHA256 değerlerini
içerir. Sistem saati, random değer ve makinenin özel kaynak yolu plan kimliğine
girmez. Proposal whitespace değişikliği raw digest'i değiştirebilir.
Tekrarlı çalışma determinism kabulü bu turda **NOT_RUN**'dır.

Kaynak koruması bütün repository'nin veya binary'nin attestation'ı değildir.
Aracın sabit 17 dosya allowlist'i actual byte length/hash ve Git HEAD ile
eşleştirilir. Native kaynak değişirse sessizce başka katalog kullanılmaz.
Git yalnız metadata için sabit `rev-parse HEAD` çağrısıyla çalışır; native
Termivar komutu çağrılmaz. Hashler kaynağın üreticisini, commit tarihçesini,
yetkilendirmeyi veya tarama sonucunu doğrulamaz.

Proposal URL'si, context marker'ı ve kaynak referansı dosya/ağ okuma talimatı
değildir. Açık CLI kaynak kökü dışındaki hedefler takip edilmez; yalnız sabit
source dosyaları okunur. DNS, HTTP, gerçek target, kimlik girişi, API, IdP veya
PG bağlantısı yoktur. Output yeni klasöre yerel yazılır; telemetri/harici upload
ve kalıcı servis yoktur. Bu bir şifreleme veya anonimleştirme garantisi değildir.

Preflight olumlu olsa dahi demo, yetki, veri işleme, scope owner, insan incelemesi
ve runtime kabulü yürütmeyi engeller. Plan native evaluator sonucu değildir;
güvenlik puanı, risk tahmini, Confirmed bulgu veya otomatik düzeltme üretmez.
Kaynakta informational/NeedsReview görülen tanımlar bu sınırda kalır.

Manuel kaynak/çıktı incelemesi bir güvenlik testi değildir. Malformed JSON,
hostile encoding, duplicate key, permission, symlink/reparse, yarış, crash ve
tekrarlı determinism davranışları çalıştırılmamıştır. Gerçek uzman, kurum,
veri işleme, hedef ve müşteri kabulü ayrıca gerekir. Sonraki faz veya gerçek
değerlendirme kendiliğinden başlatılmaz.
