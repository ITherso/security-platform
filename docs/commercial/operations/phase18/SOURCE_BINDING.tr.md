# Kaynak, packet ve karar bağı

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Kaynak kimliği `sha256:<assessment-byte-SHA256>#/items/i` biçimindeki `observation_key` ile temsil edilir. Fingerprint ayrı, kaynaktan alınan bir etikettir; eşit olması gözlemlerin birleştirilmesini veya eşit kanıtı gerektirmez. Aynı fingerprint farklı pointer'larda ayrı kalır. [Packet hazırlama kaynağı](../../../../tools/commercial_review/packet_builder.py).

## Hazırlama sırasında

Üç açık Phase17 dosyası strict ayrıştırılır. Intake manifestinin handoff/mapping byte kayıtları gerçekten okunan dosyalara eşleşmelidir. Manifestteki assessment kimliği, mapping assessment metadata'sı ve handoff source kaydı eşleşir. Her gerçek observation için ID, array konumu/pointer, fingerprint, capability ve disposition birebir karşılaştırılır. Count, sıra veya içerik farkı en yakın fingerprint tahminiyle çözülmez; kapalı hata olur.

Packet bu üç dosyanın gerçek byte SHA256 ve boyutlarını tutar. Orijinal native assessment bu aşamada **açılmaz**; onun digest'i Phase17 metadata'sından alınır. Yeni araç, önceki kaynak üretimini veya tam native import doğrulamasını bağımsız olarak tekrarladığını iddia etmez. Optional manifestin mevcut JSON-entry/summary beyanı korunur; producer/full bundle/HTML doğrulaması oluşmaz.

## Uzlaştırma sırasında

1. Packet'ın kapalı sürümü ve sabit güven sınırı doğrulanır.
2. Ayrı manifestteki packet entry, seçilen packet'ın gerçek SHA256 ve boyutuyla karşılaştırılır. Worksheet/template dosya adları açılmaz; bunlar bu kontrolde doğrulanmış sayılmaz.
3. Overlay'in `review_packet_digest` alanı tam packet byte hash'ine; `source_assessment_digest` alanı packet assessment digest'ine eşleşir.
4. Ayrı seçilen orijinal handoff'un byte kimliği packet'taki Phase17 kaydıyla ve kapalı gözlem metadata'sıyla eşleşir. Önceden review/summary/karar eklenmiş girdi fresh başlangıç değildir; conflict olur.
5. Her karar, observation ID ve tam source SHA/pointer/fingerprint/capability/disposition bağıyla eşleşir. Bilinmeyen gözlem, yinelenen karar/gözlem veya değişmiş kaynak kapalı hata olur. FP-only eşleştirme yoktur.
6. Geçerli karar yalnız yeni Phase16-compatible modelde ilgili review alanlarına uygulanır. Kararı olmayan kayıt değişmeden kalır. Kaynak gözlemler ve disposition silinmez/değişmez. Phase16 strict sınırları tekrar uygulanır.

## Karar içeriği digest'i

`decision_context_digest` için karar satırının yalnız bu alanı çıkarılır; diğer bütün zorunlu alanlar, null'lar ve tam metinler dahil kalır. Önce [kapalı overlay kuralları](REVIEW_CONTRACT.tr.md) doğrulanır. Ardından `json.dumps(..., ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)` sonucunun **sonunda newline olmadan UTF-8 byte'ları** SHA256 ile özetlenir. Sonuç 64 küçük hex karakteridir. [Saf yardımcı](../../../../tools/commercial_review/decision_overlay.py): `decision_context_digest`.

Trim, Unicode normalizasyonu, metin miras alma veya anlam tahmini yapılmaz. `safe_summary`, gerekçe, takip, reviewer/zaman beyanı, istenen durumlar ve kaynak bağı bu digest'e dahildir. Özet değiştiğinde eski karar digest'i otomatik taşınmaz. Phase15'in [yeni müşteri anlatımı için yeniden inceleme kuralı](../OBSERVATION_REVIEW_POLICY.tr.md) kurumsal sorumluluk olarak ayrıca kalır.

Herkes digest'i yeniden hesaplayabilir. Bu bağ bir hash ile değiştirilmiş kararın dışarıdan tespit garantisi, imza, kimlik doğrulama veya insanın metni gerçekten okuduğunun kanıtı değildir. Paket+manifest+overlay birlikte değiştirilip yeniden hash'lenirse güvenilir dış referans sağlamaz. `human_review_verified=false`, `producer_verified=false`, `release_authorized=false` kalır.

## Revision sınırı

İlk profil yalnız taze Phase17 girdisini kabul eder. Mevcut kararları revize eden/supersede eden, farklı paketleri birleştiren veya karar geçmişini doğrulayan mekanizma yoktur. Eski Phase15 defter ve karar belgeleri korunur; desteklenmeyen alanlar Phase16 JSON'una zorla eklenmez. Dolu overlay, duplicate ve değişmiş kaynak hata yolları bu fazda **NOT_RUN** durumundadır.
