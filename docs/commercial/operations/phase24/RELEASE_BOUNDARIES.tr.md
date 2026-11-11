# Kaynak bileşimi ve dağıtım sınırları

**DEMONSTRATION ONLY — PRODUCT COMPOSITION REVIEW — NOT AUTHORIZED FOR DISTRIBUTION**

Aday: Termivar Web & API Security Assessment — Offline Pilot Candidate.
Bu inceleme etiketi ticari SKU, yayın adı veya pilot GO değildir. Phase14'teki
talep, ödeme isteği ve müşteri kabulü `not_validated` kalır.

İki native kaynak rolü assessment çekirdeği ve raporlama/karşılaştırmadır.
Sekiz ayrı offline destek rolü handoff/intake/review/review desk/scope/
traceability/case/portfolio'dur. Kaynak listesi dar, açık ve incelenebilirdir;
Termivar'ın bütün crate/feature'larını veya bu araçların hepsini zorunlu müşteri
dağıtımı olarak ilan etmez. Destek araçları production wheel/startup'a eklenmez.

HBF, Altay, platform backend, operator console, kurumsal IdP, merkezî yönetim,
policy execution, imzalı Windows installer ve gerçek zamanlı antivirüs bu adayın
otomatik parçaları değildir. Native API crate adı canlı API hizmeti veya gerçek
dinleyici kanıtı değildir. CLI'da işlev bulunması yeni runtime kabulü değildir.

Şu olgular ayrıdır: kaynak mevcut; dependency deklarasyonu; lock sürümü;
yerel dosya varlığı; lisans beyanı; lisans dosyası varlığı; yetkili redistribution
incelemesi; build kabulü; runtime kabulü; gerçek release yetkisi. Bir olgu diğerini
otomatik sağlamaz. Source hash'i imza, attestation veya kaynak–binary bağı değildir.

Bu faz `actual_distributable_artifacts=[]` üretir; executable/installer/wheel
oluşturmaz veya eski binary'leri yeniden paketlemez. Önceden var olan production
wheel yalnız koruma metadata'sında izlenir; adayın kabul edilmiş artefact'ı
olarak sunulmaz. Termivar'ın alpha.2 yayın bytes'ı, alpha.3 kaynak pin'i ve
henüz seçilmemiş pilot executable'ı ayrı kalır.

Açık blocker kodları: `license_review_required`, `dependency_license_unknown`,
`third_party_provenance_incomplete`, `binary_source_binding_missing`,
`build_acceptance_not_performed`, `runtime_acceptance_not_performed`,
`data_handling_pending`, `release_authority_missing`. Her kayıt etkilenen
subject, kaynak dayanağı, neden, gereken karar ve open durumunu taşır.
Blocker otomatik görev, hukuki hüküm, müşteri kararı veya onay oluşturmaz.

Bu turdaki source/çıktı okuması ve manifest byte kontrolü otomatik test değildir.
Inspector yalnız beş açık yeni dosyanın iç ilişkilerini inceler; native kaynak,
paket cache'i, license text veya git pin'ini yeniden açmaz. Ürün üretimi ile
manuel kaynak incelemesi ve inspector sonucu ayrı kaydedilir.

NOT_RUN: hostile/malformed/duplicate input, yanlış lock sürümü, lisans çatışması,
eksik dependency, büyük kaynak/sınır aşımı, symlink/reparse/hardlink/race,
değişen kaynak, izin/crash/kısmi yazma, tekrar determinism, dependency çözümleme,
gerçek derleme/runtime, ticari lisans incelemesi, imzalı release/production.
Önceki Phase19 UI gözlemleri kapanmaz. Tarayıcı/HTML özelliği bu faza eklenmez;
file:// yasağını aşan sunucu/hosting/başka browser yolu oluşturulmaz.

Test/runner/coverage/typecheck/build, native scanner, canlı hedef/DNS/ağ,
API/IdP/PG, Windows/VM/driver/servis/admin, credential, müşteri/pilot iletişimi,
hukuki finalizasyon, PDF ve push/release/deploy yapılmaz. İki izinli sentetik
ürün komutu ve inceleme sonrasında durulur; Phase25 başlatılmaz.
