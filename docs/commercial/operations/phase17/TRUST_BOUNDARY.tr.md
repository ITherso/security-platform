# Assessment intake — kaynak, veri ve teslim güven sınırı

Bu araç yalnız seçilmiş mevcut dosyalardan **demo metadata aktarımı** yapar. Native Termivar, gerçek hedef, müşteri sistemi veya uzman kimliğiyle iletişim kurmaz; yeni assessment/comparison, review onayı, veri işleme yetkisi veya production modu açmaz. Eski Phase14/15/16 dosyaları, backend/frontend/HBF/auth/wheel/lockfile/lisanslar değiştirilmez.

## Kaynak ne kadar doğrulanır?

Assessment'ın gerçek seçilmiş byte'ları okunur ve SHA256 hesaplanır. Desteklenen dar alan profili, liste/sayı ve evidence ilişkileri kontrol edilir. Bu, producer/source authenticity, yetkili scan, bulgu doğruluğu veya native tam importer/constructor kabulü değildir. Fingerprint alanı kaynağın bildirdiği değerdir; araç tahmin edip yeni fingerprint üretmez. Pointer belirli byte kimliğindeki array konumudur, içeriğin güvenilirliğinin kanıtı değildir.

Yinelenen fingerprint etiketleri ayrı pointer'larıyla korunur ve tekrar bayrağı gösterilir. Native importer'ın benzersizlik kuralı burada sağlanmış kabul edilmez. Bu açık fark [eşleme belgesinde](SOURCE_MAPPING.tr.md#kimlik-yinelenen-etiket-ve-insan-durumları) belirtilir; kayıtları tek kayda indirmek veya doğrulanmış bulgu gibi sunmak için kullanılmaz.

## İsteğe bağlı kısmi manifest

Yalnız ayrıca verilmiş `--manifest` dosyası, en fazla 64 KiB, okunur. Base `termivar-report-bundle/v1` alanları; iki sabit entry adı/format/media type/pozitif byte uzunluğu/lowercase SHA256; bounded SemVer producer metadata ve assessment özetinin primitive alanları kontrol edilir. Producer version değeri doğrulama kimliği sayılmaz ve yeni modelde serbest metin olarak taşınmaz.

Manifestin `assessment.json` entry uzunluğu/hash'i gerçek seçilmiş assessment byte'larıyla; profile/status/subject/item özeti kaynakla karşılaştırılır. Uyuşmazlıkta başarılı dönüşüm yoktur. `assessment.html` entry'si **yalnız metadata'dır; dosya açılmaz**, kopyalanmaz, render edilmez ve hash'i mevcut HTML üzerinden doğrulanmaz. Başka entry/path/URL izlenmez.

Sonuç `partial_json_entry_match` olsa bile `producer_verified=false`, `full_bundle_verified=false`, `html_payload_read=false` kalır. Manifest yoksa `not_provided`; uygun varsayımı yapılmaz. Bu native `report verify`, dijital imza, attestation veya bütünlük sertifikası değildir. [Native bütünlük sınırı](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419).

## Minimizasyon ve insan incelemesi

Raw kaynak, parser'ın yerel belleğinde okunur; dönüştürücüye kapalı frozen metadata DTO'su verilir. Native başlık/description/özet/remediation/CWE gibi serbest değerler doğrulandıktan sonra atılır. Handoff açıklamaları yalnız sabit adapter metinleridir. Opaque evidence ref'leri yalnız biçimi sınırlı kaynak eşleme metadata'sıdır; ham HTTP, authorization header, cookie/token/credential, payload veya hedefe erişim içermez.

Bu allowlist genel redaksiyon veya secret detector değildir. Dosyaya keyfî biçimde gizlenmiş bir sırın bütün anlamsal biçimlerini tespit ettiği, metadata'nın anonim olduğu veya gerçek müşteri verisine uygun olduğu iddia edilmez. Gerçek müşteri verisi bu fazda kullanılmaz. Kodun/girdinin bilinçli değiştirilmesi yeni onaylı bir çalışma yolu oluşturmaz.

Kaynak etiketleri insan incelemesi değildir. Bütün aktarımlar `unreviewed / unknown / pending_decision`; güvenli müşteri özeti ve gerçek review kararı yoktur. Mevcut Phase16 da müşteri modele geçiş koşullarını ayrıca uygular ve yalnız izinli alanları kullanır. `human_review_verified=false`, `producer_verified=false`, `release_authorized=false`, `demo_only=true` değişmez. Boş müşteri listesi güvenli/temiz sonuç değildir.

## Dosya yayımı ve kabul sınırı

Eski Phase16 path/reparse/regular-file/kimlik yardımcıları uygun yerlerde yeniden kullanılır. Açık göreli CLI dosyaları dışında keşif yoktur; çıktı yeni dizin, sabit adlar, araca ait staging, overwrite etmeyen hardlink ve manifestin en son yayımıyla hazırlanır. Mevcut boş dizin dahi alınmaz. Hata başarı sayılmaz; yeni kısmi dizin/staging kalabilir. Bütün dizinin tek atomik yayınlandığı, güvenli silme/şifreleme/ACL veya bütün filesystem yarışlarının önlendiği iddia edilmez.

İntake manifesti iki payload'ın gerçek boyut/hash'ini; dış teslim kaydı intake manifestinin kendi byte hash'ini verir. Phase16 builder manifesti başka katmandır: onun giriş hash'i yeni `handoff-input.json` byte'larını tanımlar, eski native assessment'ın doğruluğunu kanıtlamaz. İki kaydı birbirine eşlemek üretici veya uzman onayı yaratmaz.

İzinli yürütme yalnız bir benign intake ve ardından bir Phase16 builder çağrısıdır. Kod/gerçek çıktı okuması ile malformed/hostile/duplicate/symlink/reparse/race/permission/crash/alternatif şema davranışlarını çalıştırmak ayrı şeylerdir; yapılmayanlar `not_run` olarak [entegrasyon notunda](DEMO_INTEGRATION.tr.md) kalır. Gerçek müşteri yetkisi, uzman/kanıt incelemesi, veri/saklama/kurum kararları, güvenlik kabulü ve teslim onayı açıktır. Bu kit onları veya bekletilen Windows/IdP/revision kararlarını yeniden açmaz.
