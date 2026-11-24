# Termivar Web Güvenlik Değerlendirme Merkezi

**Termivar Web Değerlendirmeleri**, önceden hazırlanmış desteklenen Termivar Web JSON artefaktlarını yerel tarayıcıda okur. Yeni scanner, evaluator veya rapor üretici değildir. Değerlendirme sonucu, **doğrulanmış güvenlik durumu değildir**. Cihazın Termivar Web kurulu/çalışır olduğunu veya bir hedefe müdahale yetkisini kanıtlamaz. [English guide](TERMIVAR_REVIEW.en.md).

## Kullanım

1. Gezinmeden **Termivar Web Değerlendirmeleri** alanını açın. Tek bir yerel assessment JSON dosyasını açıkça seçin; dosya en fazla **1 MiB** olabilir. Örnek düğmeleri sentetik örneği ayrı etiketle açar; geçersiz dosyanın yerine otomatik örnek konmaz.
2. Sürüm, tamamlanma, kapsam ve eksik bilgi açıklamalarını okuyun. Yalnız yüklenmiş sonuçlarda arayın, sonuç türünü filtreleyin ve bir kaydı seçin. Eksik tanı belgesinde assessment item'ları bulunmuyorsa tamamlanmış boş liste gösterilmez.
3. Serbest başlık/açıklama ve metadata başlangıçta gizlidir. Ayrıntıları açıkça göstermek yalnız bu import için geçerlidir; alanlar düz metindir. “Redacted” alan adı, güvenilir olmayan dosyada sır bulunmadığı garantisi değildir.
4. İsterseniz en fazla **64 KiB** manifest'i **ayrı ve açık seçimle** okuyun. Bu native manifest sınırı, assessment'ın 1 MiB UI sınırından ayrıdır. Seçim yalnız mevcut JSON'un byte uzunluğu, SHA256 ve özetinin manifest'teki JSON girdisiyle ilişkisini kontrol eder. HTML veya başka dosya aranmaz/okunmaz.
5. Yeni assessment seçimi önceki modeli ve görünürlük tercihini temizler. Geçersiz yeni dosya eski başarıyı yeni sonuç gibi bırakmaz. Temizleme türetilmiş modeli kaldırır; reload geri yüklemez. Normal sayfa/TR–EN geçişi importu korur; tenant/kaynak/örnek senaryosu/oturum değişimi ve mevcut erişim temizliği konservatif temizler.

Bu alan envanterden bağımsız yerel dosya incelemesidir. Hostname/IP'den `device_id` çıkarmaz; bir cihazla otomatik ilişkilendirme, durum raporuna/cihaz karşılaştırmasına/politika önizlemesine kopyalama veya backend yazımı yapmaz. Mevcut HBF importer'ının yerine geçmez.

## Desteklenen kapalı alt küme

| Artefakt | Kabul ve sınır |
|---|---|
| `venom-rendered-assessment/v1` | Tamamlanmış temel `web-review` belgesi. Dokuz zorunlu kök alanı ve kayıt başına yirmi gerçek item alanı doğrulanır. Ek capability audit bölümleri bu sürümde desteklenmez; silinip başarılı temel rapor gibi sunulmaz. |
| `web-assessment/v2` | Ayrı, `schema_version` ile tanımlanan exact-origin tanı belgesi; yalnız `disposition=incomplete|failed`. Kapsam/profile limits/usage/incomplete reasons ve unavailable item projection incelenir. Tamamlanmış assessment yerine kullanılmaz. Gelişmiş audit uzantıları ve single-resource tanı alt türü desteklenmez. |
| `termivar-report-bundle/v1` manifest | İsteğe bağlı, ayrı seçilen manifest. Gerçek iki sabit girdili yapı doğrulanır; yalnız seçilen JSON byte/özet ilişkisi incelenir. HTML girdisi okunmaz ve tam bundle doğrulanmış sayılmaz. |
| `termivar-report-comparison/v1` ve diğer türler | Assessment import'u değildir; açıkça desteklenmeyen tür olarak reddedilir. Compare belgesi yeni tarama, zafiyetin giderilmesi veya eşit kapsam kanıtına dönüştürülmez. |

UTF-8, duplicate key, geçersiz/sonlu olmayan sayı, safe-integer, alan ve sürüm denetimleri korunur. Assessment, kapalı `termivar-assessment-v1` `strictJson` profiliyle ayrıştırılır: **12 derinlik**, **300.000 düğüm**, metin başına **1.024 UTF-16 kod birimi**, dizi başına **4.096 eleman**, nesne başına **32 anahtar**, **600.000 token**. Alanların daha dar sınırları da geçerlidir (en fazla 4.096 item, 1.024 subject/form, item başına 256 kanıt referansı). Profil bu adapter sınırlarından ve 1 MiB dosya sınırından boyutlandırılmıştır; adapter'ın kabul ettiği 1 MiB altındaki belge ayrıştırma bütçeleri yüzünden reddedilmez. İsteğe bağlı manifest, 64 KiB sınırı içinde ortak varsayılan profili (12 derinlik, 12.000 düğüm, dizi başına 100 eleman, nesne başına 32 anahtar, 60.000 token) kullanmaya devam eder. Yerel kaynağın 16 MiB renderer sınırı UI kotası değildir: 1 MiB üstündeki yerel çıktılar dosya çok büyük hatasıyla reddedilir. İlk N kayıt sessizce alınmaz; açık hata gösterilir. Ret, kötü amaçlı dosya teşhisi değildir.

## Gerçek JSON → görünüm eşlemesi

| Kaynak alan | UI anlamı / çıkarılamayan bilgi |
|---|---|
| Complete `schema`, `source_schema`, `run_schema`, `profile_schema`, `profile`, `status` | Desteklenen belge ailesi ve `complete` beyanı; üretici kimliği veya güvenli hedef sonucu değildir. |
| Complete `subject_count`, `item_count`, `items` | Bildirilen kapsam/item toplamı ve yüklenen item'ların disposition/severity sayımları. Zafiyet sayısı veya kapsama yüzdesi değildir. |
| Item `disposition`, `claim_basis`, `severity`, `confidence_ppm` | Kaynağın sınıflandırması ve dayanak/metadata'sı; bağımsız güven/etki/risk skoru değildir. `severity=null` atanmamış kalır. |
| Item `evidence_count` ve üç `*_evidence_references` dizisi | Opaque kanıt referansı/sayısı ve mevcut bağ tutarlılığı. Haricî kanıtın varlığı, doğruluğu veya açılma yetkisi doğrulanmaz. |
| Item `subject_reference`, `fingerprint`, `capability_id` | Doküman içi/kaynak kimlikleri; hedef konumu, cihaz eşlemesi, üretici imzası veya yetki değildir. |
| Item `title`, `redacted_summary`, `category`, `cwe`, `remediation` | Varsa kaynağın sabit metni/önerisi; gizli sunum tercihiyle düz metin olarak gösterilebilir. Öneri uygulanmış veya doğrulanmış düzeltme değildir. |
| Item `case_reference`, `outcome_reference`, `verification_stage` | Kaynağın opaque verifier bağlantısı. `confirmed` beyanını merkezin bağımsız doğrulamasına yükseltmez. |
| Diagnostic `disposition`, `incomplete_reasons`, `assessment.report.assessment_items` | Tamamlanamama/başladıktan sonra failure ve item projection'ın unavailable oluşu. Eksik item sayısı sıfır bulguya dönmez. |
| Diagnostic `profile_contract.limits`, `assessment.report.usage` | Yalnız belgede bulunan açık limitler ve kullanımlar. `max_total_requests` istek limiti, `max_wall_time_ms` coverage `wallTimeLimitMs` süre limiti olarak kullanım değerlerinden ayrı korunur. İstek sayısı başarılı yanıt/bulgu sayısı değildir; budget içinde görünmek bütün kontrollerin tamamlandığını kanıtlamaz. |
| Diagnostic `semantics`, `defense`, `transport`, varsa `failure_inventory` | Desteklenen kapalı sayısal/tutarlılık alanları doğrulanır. Varsa `failure_inventory.consistent` ve `unrepresented_ledger_subjects`, coverage modelinde `inventoryConsistent` / `unrepresentedLedgerSubjects` olarak korunur; tutarsızlık temiz sonuç sayılmaz. Ham subject/form internalleri, query/control adları ve `target_origin` doğrulandıktan sonra UI modeline alınmaz. |
| Manifest `producer`, `assessment`, sabit `files` girdileri | Üretici **beyanı**, özet ve byte metadata'sı. Manifest yoksa üretici tahmin edilmez. HTML için declared değerler seçilip kontrol edilmiş byte'lar değildir. |

Complete temel JSON'da başlangıç/bitiş zamanı, producer nesnesi ve request budget/usage yoktur. Bunlar **Mevcut artefaktta bulunmuyor** kalır; dosya okuma zamanı scan zamanı sayılmaz. Diagnostic `elapsed_ms`, sağlanmış süre alanıdır, başlangıç/bitiş timestamp'i değildir. Gerçek sıfır ile bulunmayan değer ayrıdır. “Hangi tüm kontroller geçti?” sorusu için artefaktın vermediği sonuç hesaplanmaz.

## Observation, evidence, NeedsReview ve KnowledgeOnly

Gerçek `claim_basis` değerleri **`observation`**, **`differential`**, **`verifier_transition`** değerleridir. `evidence` ayrı bir claim_basis veya bulgu kategorisi değildir; kanıt referansları/sayısı kavramıdır.

- `informational` + `observation`, sınırlı gözlem beyanıdır; zafiyet/etki veya doğrulanmış düzeltme değildir.
- `needs_review` + `differential`, inceleme adayıdır. Tek doğrudan referanslı veya control/candidate referanslı desteklenen bağ biçimleri vardır; kesin zafiyet hükmü değildir.
- `confirmed` + `verifier_transition`, kaynağın tam opaque case/outcome/stage bağını taşımalıdır. İçe aktaran UI bu beyanın üreticisini veya gerçek dünyadaki doğruluğunu bağımsız doğrulamaz.
- **KnowledgeOnly**, runtime yetki/authority kavramıdır; bu assessment wire sözleşmesinde bağımsız alan, disposition veya sayaç değildir. Yeni KnowledgeOnly/“temiz”/“kritik” kategorisi türetilmez.

Tamamlanmış ve boş item listesi, eksik assessment ve desteklenmeyen/eksik sonuç biçimi ayrı durumlardır. Hiçbiri **Güvenli**, **Korunuyor**, **Düzeltildi**, **Verified** veya risk puanı üretmez. Bir observation'ın kaybolması ya da ayrı bir comparison'ın only-in-before sonucu remediation kanıtı değildir.

## Manifest kontrolünün kapsamı

Manifest yalnız kullanıcı ayrıca seçerse ele alınır. `selected_json_matches`, yakalanmış mevcut JSON'un tam byte uzunluğu/SHA256 ve tamamlanmış özetinin manifest JSON girdisiyle eşleştiğini söyler. `mismatch` bu ilişki kurulamadığında gösterilir; nedenin kötü amaçlı değişiklik olduğu varsayılmaz. Canonical yeniden serialize edilmiş JSON değil, seçilen byte'lar bağlanır.

HTML seçilmez, okunmaz, açılmaz veya hash'lenmez. Manifest'teki sabit adlar yol olarak izlenmez. Bu yüzden **tam bundle verification**, HTML–JSON semantik eşdeğerliği, producer authentication, scope authority, finding accuracy veya remediation sonucu oluşmaz. Manifest ve payload birlikte tutarlı biçimde değiştirilebilir; eşleşme imza değildir. Üretici doğrulaması **not_verified** olarak kalır. HBF'nin mevcut sayısal özeti ve merkezi `latest_report` DTO'su ayrı sözleşmelerdir.

## Bellek ve hassas sunum

Dosyalar yalnız File API ile açıkça seçilir. Ağ/upload, scanner/runtime, dış kaynak/URL/kanıt açma, script/HTML/komut üretimi, ham HTTP/kanıt alanları için ayrı açma eylemi, kopyalama/export/print/PDF veya kalıcı tarayıcı deposu yoktur. Bununla birlikte güvenilir olmayan title/summary/metadata metni HTTP içeriği veya sır içerebilir; opt-in bunları sırdan arındırmaz. Ham belge global store'a taşınmaz; yalnız doğrulanmış kapalı ve immutable model tutulur. Gizli metin DOM/attribute içinde CSS ile saklanmaz; render edilmez. Gizli alanlar üzerinden arama eşleşme oracle'ı kurulmaz.

Dosya adı ve özel hedef bilgisi başlığa, URL'ye, log veya analytics'e aktarılmaz. Ayrıntı opt-in'i şifreleme veya anonimleştirme değildir; kullanıcı dosyasındaki “redacted” metin ayrıca incelenmelidir. Temizleme OS/tarayıcı belleğinin adli olarak silinmesi garantisi değildir.

## Kaynaklar, örnekler ve yapılmayan işler

Yerel `ITherso/termivar` kaynağı `6a2639348c2366d0bf71b9a34e5484d40aa393a3` commit'inde salt okunur incelendi. Esas referanslar: [reporting.md](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md), [assessment_scan.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/assessment_scan.rs), [report_bundle.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/report_bundle.rs), [import.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs), [scan_profile.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/web_runtime/scan_profile.rs). Yerel yol ve tam örnek byte/SHA256 kaydı [provenance belgesindedir](../src/features/termivarReview/examples/README.md).

Yerleşik complete/incomplete örnekler elle yazılmış sentetiktir: **Örnek Termivar Web değerlendirmesi — gerçek hedef üzerinde tarama yapılmadı.** Ayrı `bundle-assessment.json` + `bundle-manifest.json`, daha önceki benign numeric-loopback fixture'ının değişmeden kopyalanmış iki dosyasıdır; bu fazın scanner çıktısı değildir ve HTML içermez. Örnekler geçersiz kullanıcı dosyasına otomatik fallback değildir.

Gerçek build/typecheck ve sınırlı manuel ürün gözlemleri [Phase11 teslim kaydında](DELIVERY.tr.md) ayrı tutulur. Bu tur test/runner/coverage, scanner/runtime veya fixture sunucusu, canlı API/IdP/PG, Windows/VM/driver/yönetici işlemi, uzaktan müdahale, print/PDF/export veya deploy/push/release çalıştırılmadı. Tarihsel test sayıları yeni ürün kabulü değildir. Backend, HBF, wheel, auth, policy ve dependency kilitleri korunur.
