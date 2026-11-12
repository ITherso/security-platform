# Phase32 güven ve mahremiyet sınırı

**DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION**

Bu araç yalnız açık request kapsamındaki reference metadata'sını küçültür. Response/selection/Markdown tam historical baseline, kaynak path/root/pin, physical identity, ham Rust/JSON, credential, yorum/exception veya keyfî metadata içermez. Upstream bağ yalnız dört dosyanın sürüm/byte/SHA256 descriptor'ları ve bunlardan türetilmiş snapshot kimliğidir; descriptor'da path yoktur.

İzinli record kimlikleri ve raporlanmış hash/size hassas olabilir. Minimizasyon anonimleştirme, şifreleme, secret detection, imza veya producer attestation değildir. Byte kimliği yalnız belirli artefact içeriğine bağ kurar.

Bloke reference için `projections=[]`; olumlu alt candidate'ın hash/size bilgisi selection'a, Markdown'a veya başka alana taşınmaz. Yalnız istenen reference ID'leri yeni modele girer; diğer bağlam reference'larının ID listesi, iç isimleri veya incelendikleri iddiası yoktur. Request kimliği yerel korelasyondur; credential/rol/yetki değildir.

## Tekrar okunmayan kaynaklar

Assembly yalnız request ve dört açık Phase31 metadata dosyasını okur. Kaynak ZIP'i, candidate/Rust/entry-point/Phase24 dosyaları açılmaz, eski CLI veya lexer çalışmaz. Snapshot'ın kendi immutable bytes'ını tekrar doğrulaması yeni filesystem/source gözlemi değildir. Önceki gözlemden bugüne dosyanın değişmeden kaldığı çıkarılamaz.

Inspector yalnız yeni response, selection, summary ve manifest'i okur. Model correspondence, üç payload'ın gerçek byte/hash bağı ve inert Markdown türetimini denetler. Eski upstream guard ve dosya gözlemlerini bağımsız yeniden doğrulamaz. `content_consistent` yalnız yeni artefact iç tutarlılığıdır.

## Korunan false alanları

`source_inventory_updated`, `scope_delta_applied`, `component_ownership_verified`, `dependency_closure_verified`, `module_closure_verified`, `compiler_resolution_verified`, `build_verified`, `runtime_verified`, `producer_verified`, `human_review_verified`, `license_review_completed`, `redistribution_authorized`, `release_authorized`, `production_ready`, `reference_context_revalidated`, `independent_observation_verified`, `source_files_reobserved` alanlarının tamamı **false** kalır; `demo_only=true`.

Metadata verilmesi ALLOW, güvenli, uygulanmış, doğrulanmış, module resolved veya release-ready anlamı taşımaz. Absence projection'ında byte/hash null'dır; sıfır byte'lık present dosyayla karıştırılmaz. Upstream `fresh_*` kodları geçmiş karar isimleridir; bu çağrıda yeni okuma, TTL veya canlı tazelik garantisi yoktur.

## Açık kabul kapıları

Çalıştırılmadıkça NOT_RUN: hostile JSON/UTF-8; duplicate/bilinmeyen ID; request digest uyuşmazlığı; bozuk upstream; bilinmeyen guard kararı veya projection tutarsızlığı; limit/path/link/race/crash; farklı shared-file düzenleri, tekrarlı determinism ve gerçek source değişimi. Native/compiler/module closure/ownership/producer/uzman/hukukî/release kabulü açık kalır.

Kaynak kod incelemesi negatif dalların çalıştığına kanıt değildir. İki komut bütçesi test/runner/coverage/typecheck/build, tarayıcı workaround'u, ağ, canlı endpoint veya müşteri işlemi izni vermez. Önceki açık kabul sınırları korunur.
