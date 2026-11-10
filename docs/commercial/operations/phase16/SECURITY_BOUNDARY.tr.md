# Offline Handoff Builder — veri ve güven sınırı

Bu araç **yalnız demo taslağı** üretir. Native Termivar scanner/CLI çağrısı, yeni assessment/comparison, müşteri gönderimi, production kabulü, kimlik/yetki doğrulaması veya güvenlik sertifikası değildir. Gerçek hassas müşteri verisiyle kullanım bu fazda kabul edilmiş sayılmaz.

## Offline girdi ve izinli alan listesi

Kullanıcı açıkça tek bounded JSON girişini seçer. [Tam sözleşme](INPUT_CONTRACT.tr.md) root ve nested object'lerde exact alan kümeleri, enum/tür, 256 KiB dosya, derinlik/node/metin ve kayıt sınırları tanımlar. UTF-8/BOM/duplicate key/sayısal biçim kontrolleri native kaynak içeriğine güven atamaz. JSON metnindeki path veya URL başka dosya açma, link oluşturma, network, shell ya da tarayıcı başlatma talimatı değildir.

Girişte native assessment'ın tamamı, hedef/credential/session alanı veya raw HTTP/payload alanı yoktur. `provenance_note`, `evidence_limitations`, `reason`, `scope_summary`, `safe_summary` ve constraint gibi izinli **serbest metinler yine hassas içerik taşıyabilir**. Şema unknown field reddeder; mevcut serbest metin içinde sır veya yanlış iddia bulunmadığını kanıtlamaz. Otomatik redaksiyon, secret detector, anonimleştirme veya semantik hedef/IP taraması yoktur. Gerçek veri seçimi ve paylaşımı insan incelemesi gerektirir.

## İç modelden müşteri modeline sınır

İç çıktı source/ref, insan review/inclusion beyanları, eksik kanıt ve engelleri tutar. Müşteri modeli izinli alanlardan ayrıca kurulur; iç DTO veya tam ledger serialize/spread edilip HTML'e gömülmez. Internal karar gerekçeleri, provenance notlarının tamamı, iç dosya yolları ve raw evidence otomatik taşınmaz.

Observation'ın biçimsel olarak geçerli olması müşteri seçimi değildir. Ayrı inclusion kararı ile uygun review/source/karar koşulları gerekir. `unreviewed`, `needs_manual_review`, `inconclusive`, `excluded_with_reason` kesin müşteri bulgusuna yükseltilmez. `informational_only` zafiyet, `reviewed_for_delivery` teknik doğrulama değildir. Girdi reviewer ve tarih taşısa bile araç kişinin kimliğini veya incelemenin gerçekliğini doğrulamaz.

Markdown ile statik HTML aynı sınırlı müşteri modelini kullanır. Dinamik içerik güvenli metin olarak escape edilir; giriş HTML'i render edilmez. HTML script, dış CSS/font/CDN/görsel URL veya JavaScript kullanmaz; gizli attribute/comment/metadata üzerinden iç model taşınmamalıdır. Escape ve düz metin sunumu, içeriğin doğru, sırdan arınmış veya paylaşılması onaylanmış olduğu anlamına gelmez.

Her müşteri taslağının görünür sabit etiketi **DEMONSTRATION ONLY — NOT APPROVED FOR CLIENT DELIVERY**. `demo_only=true`, `release_authorized=false`, `human_review_verified=false` sabit sınırları gerçek onay/production bayrağına çevrilemez. Gizli flag, env override veya `--force` yoktur.

## Dosya ve hata sınırı

Yalnız explicit göreli input/output yolları; mutlak/drive/UNC yol, `..`, ADS, symlink/reparse ancestry reddi ve yeni çıktı dizini kontrolleri uygulanır. Çıktı üst dizini mevcut olmalı; çıktı dizini exclusive oluşturulur ve mevcut boş dizin dahi kabul edilmez. Sabit adlar, aynı üst dizinde araca ait staging, exclusive/no-overwrite hardlink yayımı ve manifestin en son completion marker olarak yazılması mevcut müşteri dosyasını sahiplenmemek ve kısmi yazımı başarı göstermemek içindir. Bütün dizin için tek atomik yayın işlemi iddia edilmez. Araç overwrite, kullanıcı dizini silme veya eski teslimatı otomatik düzeltme yolu sunmaz. Başarısız işlem tamamlanmış teslim olarak gösterilmez; kısmi dosyalar kalabilir, başarı belgesi sayılamaz.

Bu korumaların kodda bulunması, bütün filesystem race/TOCTOU durumlarının, paralel süreç müdahalesinin, güç kaybının veya farklı OS ACL/owner davranışının yürütülüp kabul edildiği anlamına gelmez. Güvenli silme, şifreli disk, erişim kontrolü veya bütün platformlarda güvenli dosya kasası iddiası yoktur. Çalıştırılmayan malformed input, symlink/reparse, permission, disk/writer failure ve yarış yolları `not_run` kalır.

## Manifest neyi kanıtlar?

Manifest açıkça seçilen giriş byte'larının SHA256'sını ve üç oluşturulmuş dosyanın ad/boyut/SHA256'sını kaydeder. Oluşturulmuş byte kimliği ile girdinin bildirdiği ART-A1 kaynak hash'i farklı katmanlardır. Builder A1'i açıp yeniden doğrulamaz; elle aktarılan provenance, fingerprint veya pointer'ın kaynağa ait olduğunu bağımsız kanıtlamaz.

Hash imza, bağımsız trust attestation, üretici/source kimliği, native full-bundle verification, uzman incelemesi veya müşteri onayı değildir. Dosyaları ve manifesti birlikte değiştirebilen kişi tutarlı yeni hash'ler yazabilir. İçerik deterministik olabilir; bu, aynı dosyanın yetkili kişi tarafından hazırlandığını kanıtlamaz. Manifest kendi hash'ini veya ayrı bir imzalama/sertifikalandırma sistemi üretmez.

## Yapılan inceleme ve açık kabul

[Demo notları](DEMO_DELIVERY_NOTES.md), başarılı tek demo üretimini gerçek komut/dosya kimlikleriyle kaydeder. Manuel kod/çıktı okuması otomatik test, unit-test runner, coverage veya güvenlik kabulü değildir. Çalıştırılmamış hata senaryosu “kontrol mevcut” ifadesinden geçirilmiş sayılmaz.

Gerçek müşteri kullanımı öncesi şu konular açık kalır: yetki/kapsam; seçili executable ve çalışma yolu; gerçek uzman/kanıt incelemesi; metinlerin iddia/veri minimizasyonu; erişim/aktarımı ve saklama/silme/yedek sahipleri; kurumsal/hukuki kararlar; güvenlik testleri ve gerçek teslim/onay. Bu belge bunları kararlaştırmaz veya yeni test/canlı iş başlatmaz. HBF Windows, platform IdP ve gerçek revision otoritesi ayrı kapılardır; bağımsız Termivar hizmetinin otomatik önkoşulu yapılmaz ve yeniden seçilmez.

Korunan dayanaklar: [Phase15 inceleme politikası](../OBSERVATION_REVIEW_POLICY.tr.md), [veri rehberi](../DATA_HANDLING.tr.md), [manuel teslim kapısı](../DELIVERY_GATE.tr.md), [Phase14 iddia matrisi](../../CAPABILITY_CLAIMS.tr.md) ve [pilot hazırlığı](../../PILOT_READINESS.tr.md). Eski JSON, manifest, lisans, teknik kaynak, lockfile ve arşivleri bu araç değiştirmez.
