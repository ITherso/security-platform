# Phase24 gerçek ürün bileşimi teslimi

**DEMONSTRATION ONLY — PRODUCT COMPOSITION REVIEW — NOT AUTHORIZED FOR DISTRIBUTION**

11 Kasım 2026. Termivar Web & API Security Assessment — Offline Pilot Candidate için gerçek yerel kaynak metadata envanteri oluşturuldu. Bu bir ticari SKU, release, SBOM sertifikası, hukuki görüş veya dağıtım izni değildir.

[Araç ve CLI](../../../../tools/commercial_composition/README.md), [sözleşme](COMPOSITION_CONTRACT.tr.md), [dependency/lisans](DEPENDENCY_AND_LICENSE.tr.md), [dağıtım sınırı](RELEASE_BOUNDARIES.tr.md).

## Gerçek komut geçmişi ve açık kullanıcı istisnası

İlk assembly, kaynak commit `a7fca264439a6e89d55c38edb0bb27b3cedd6b4f` ile **exit 1** verdi: `composition_source_identity_changed`. Output dizini oluşmadı; inspector o aşamada çalıştırılmadı. Bu başarısız çağrı silinmedi veya başarılı sayılmadı.

111 seçili dosyanın salt okunur metadata incelemesinde 79 dosyada yalnız lstat/fstat ctime değerlerinin farklı olduğu, path-lstat önce/sonra değerlerinin sabit kaldığı görüldü. Düzeltme commit `3a21342202a29dcfc208e17b48305e3629f7ff58`: dev/inode/size/mtime/nlink yöntemler arasında; ctime bunlarla birlikte her yöntemin kendi önce/sonra kayıtları arasında karşılaştırılır. Hardlink/reparse, byte sınırı ve path stability kontrolleri korunur. Bu gözlem saldırgan filesystem kabulü değildir.

Görevin ilk sınırı iki yeni ürün komutuydu; ikinci komut ilk assembly başarısına bağlıydı. Bu nedenle duruldu ve kullanıcıdan bir assembly tekrarı ile başarılıysa inspector olmak üzere iki ek komut için açık onay istendi. Kullanıcının **“Onaylıyorum”** yanıtı üzerine bu iki ek komut çalıştırıldı. Toplam gerçek Phase24 ürün çağrısı **3**, exit code geçmişi **[1, 0, 0]**. Eski Phase20 1/1, Phase21 1/1, Phase22 2/2, Phase23 2/2 sayaçları değişmedi. Test/build yetkisi alınmadı veya kullanılmadı.

Başarılı iki komut workspace kökünden:

```text
python -I -B security-platform/tools/commercial_composition/assemble_composition.py --scope security-platform/tools/commercial_composition/examples/demo_composition_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --platform-root security-platform --output-dir outputs/phase24-composition
python -I -B security-platform/tools/commercial_composition/inspect_composition.py --inventory outputs/phase24-composition/composition-inventory.json --dependencies outputs/phase24-composition/dependency-license-ledger.json --constraints outputs/phase24-composition/release-constraints.json --summary outputs/phase24-composition/composition-summary.md --manifest outputs/phase24-composition/manifest.json --output outputs/phase24-composition/inspection-summary.json
```

Assembly **exit 0** ile beş dosya; inspector **exit 0** ile altıncı dosyayı oluşturdu. `--summary`, gerçek Markdown boyut/hash bağını incelemek için ek açık argümandır. Inspector manifestten dosya seçmez; beş açık yeni dosyayı okur. Kaynak map/root/dosya, package cache veya git pin doğrulaması yapmaz.

Tam çağrı/çıktı kayıtları: `outputs/phase24-first-generation-attempt.json`, `outputs/phase24-user-retry-authorization.json`, `outputs/phase24-generation-record.json`. İlk ve düzeltilmiş kaynak snapshotları ayrı korunur. Yeni ürün çağrısı yapılmayacak.

## Gerçek dosyalar

Konum `outputs/phase24-composition/`; değerler oluşturulan dosyalardan hesaplandı.

| Dosya | Bayt | SHA256 |
| --- | ---: | --- |
| composition-inventory.json | 41016 | 57858a6de13a3f0994f3d21cc4564ccb430ae15eb2e6e9c2f885365492ce1a4e |
| composition-summary.md | 15004 | 64862044de910a9c183ee1d89faff1b8625ab77477501159053e37e5e46edfcd |
| dependency-license-ledger.json | 481295 | e5cb40e42c46bf66b8721bf0f386b9be8112518e3cd5b4342e6b16682715cfe6 |
| inspection-summary.json | 3072 | e75b44ac8285196614264e22ba79b19596c5df0719e1cdb5efaca85822de2c01 |
| manifest.json | 1814 | 95c04d5c14f2b6d017154817aec968e453d4a2772ba750baaf0b0ad47796cc32 |
| release-constraints.json | 472825 | 8997a93eb051ed2c0e72f59b92e17c129a3082135ba7044e6b33369202bbdd9d |

## Kaynak bileşimi ve lisans belirsizlikleri

- 10 birinci taraf kaynak bileşeni: iki Termivar native kaynak rolü, sekiz ayrı offline destek aracı.
- 111 açık seçilmiş dosya, toplam 2.454.416 kaynak baytı; 27 Termivar ve 84 platform dosyası.
- Sekiz gerçek manifest/lock seçimi. Root/core/scanner/cli Cargo manifestleri; Cargo.lock v4; pyproject ve iki requirements pin dosyası.
- 451 dependency metadata kaydı: 111 deklarasyon + 340 lock kaydı. Bunlar tekil paket veya eksiksiz build/runtime dependency sayısı değildir.
- 407 kayıt seçili kaynak metadata kapsamındadır. 44 Python backend/test/build kaydı yalnız excluded_backend_context olarak ayrılır; offline yardımcıların runtime bağımlılığı sayılmaz.
- Kaynak türü: registry388, declared_index44, unknown19. Path veya eksik lock source workspace sahipliği olarak yükseltilmez.
- 461 lisans subject kaydı: iki scoped native MIT kanıtı, sekiz helper unknown ve 451 dependency unknown. Toplam459 unknown; tüm461 insan incelemesi gerektirir.
- Gerçek dağıtılabilir artefact listesi boştur. Binary, installer veya wheel üretilmedi.

Native kaynak pin `6a2639348c2366d0bf71b9a34e5484d40aa393a3`; workspace sürümü `0.10.0-alpha.3`. İki native bileşendeki MIT, açık Cargo/yerel LICENSE kaynağına bağlıdır. LICENSE1085 bayt, SHA256 `d308383be39c28054876444bc46a410a5e753c7df982afce644fab1e7e9f754d`. Bu lisans diğer bağımlılıklara veya yardımcı araçlara yayılmaz. Helper source pin `e3b11d3101eafb3178868f391db713639c921c01`; platform project0.1.0 beyanı helper release sürümü değildir. Pinler scope beyanıdır; araç git/source attestation üretmez.

Cargo.lock306 kaydı, seçilen binary/feature kapanışı veya lisans bilgisi değildir. Yerel dependency paketleri indirilmedi veya doğrulanmadı. Manifest deklarasyonları, optional/dev/build/target girdileri ve lock satırları resolver olmadan ayrı tutulur. Lisans veya sürüm ezberden doldurulmadı.

## Açık engeller ve bayraklar

1377 açık blocker kaydı; üyelikler örtüşür ve risk puanı değildir:

| Kod | Etkilenen subject |
| --- | ---: |
| license_review_required | 461 |
| dependency_license_unknown | 451 |
| third_party_provenance_incomplete | 451 |
| binary_source_binding_missing | 10 |
| build_acceptance_not_performed | 1 |
| runtime_acceptance_not_performed | 1 |
| data_handling_pending | 1 |
| release_authority_missing | 1 |

`demo_only=true`, `source_inventory_generated=true`; altı bayrak **false**: `license_review_completed`, `redistribution_authorized`, `build_verified`, `runtime_verified`, `release_authorized`, `production_ready`. Kaynak/byte tutarlılığı bu bayrakları yükseltmez.

Dokuz hariç: HBF, Altay, platform backend, operator console, kurumsal IdP, merkezî yönetim, policy execution, imzalı Windows installer ve gerçek zamanlı antivirüs. Bunlar adayın otomatik parçaları değildir. Phase14 talep/ödeme isteği `not_validated`; pilot GO yoktur.

## Yapılan incelemelerin ayrımı

1. Manuel kaynak incelemesi: gerçek scope, Cargo/pyproject/pin/lisans metadata ve yazılım kaynak sınırları okundu. Root, assembly sonrası111 açık kaynağın gerçek boyut/hash kaydını inventory ile karşılaştırdı; tümü eşleşti. Bu imza, provenance veya eksiksiz dependency kabulü değildir.
2. Manifest byte incelemesi: dört payload boyut/hash kaydı gerçek dosyalarla eşleşti. Manifest kendisini hash listesine eklemez.
3. Inspector: beş açık çıktıdan kapalı şemalar, referanslar, sayımlar ve saf blocker/Markdown ilişkilerini yeniden türetti; internal_content_status=content_consistent. Kaynakları/lisansları ikinci kez doğrulamadı.
4. Bağımsız salt okunur çıktı incelemesi: altı gerçek dosyada sayı/metadata/lisans/güven sınırlarında engelleyici tutarsızlık bulunmadı. Product import/CLI/test/build/browser/native/ağ veya dosya mutasyonu yapılmadı.

JSON/Markdown metadata alanlarında source body, ham assessment, hedef/credential veya mutlak kullanıcı kökü gözlenmedi. Repository-relative source yolları dosya kimliğinin parçasıdır. Bu allowlist/known-field incelemesi otomatik secret detection, anonimlik veya redaksiyon garantisi değildir.

`outputs/phase24-manual-output-review.json` gerçek inceleme ve byte kayıtlarını; `outputs/phase24-preservation-review-final.json` son koruma karşılaştırmasını taşır. Windows metadata tanısı ham dosya içeriği okumadı; ayrıntılı yerel zaman kayıtları kaynak teslim ZIP’ine konmaz.

## Değişen dosyalar ve koruma

Yalnız yeni16kaynak/belge dosyası:

- `docs/commercial/operations/phase24/COMPOSITION_CONTRACT.tr.md`
- `docs/commercial/operations/phase24/DEMO_DELIVERY.tr.md`
- `docs/commercial/operations/phase24/DEPENDENCY_AND_LICENSE.tr.md`
- `docs/commercial/operations/phase24/RELEASE_BOUNDARIES.tr.md`
- `tools/commercial_composition/README.md`
- `tools/commercial_composition/__init__.py`
- `tools/commercial_composition/artifact_manifest.py`
- `tools/commercial_composition/assemble_composition.py`
- `tools/commercial_composition/composition_contracts.py`
- `tools/commercial_composition/composition_renderer.py`
- `tools/commercial_composition/dependency_reader.py`
- `tools/commercial_composition/examples/demo_composition_scope.json`
- `tools/commercial_composition/inspect_composition.py`
- `tools/commercial_composition/license_evidence.py`
- `tools/commercial_composition/release_constraints.py`
- `tools/commercial_composition/source_inventory.py`

Önceki179 artefact,154korunan kaynak,21frontendasset ve production wheel başlangıç boyut/hash envanteriyle eşleşir. Backend/operator-console, nativeTermivar,HBF,Phase14–23araçları,auth/DB/roller,lockfile ve lisanslar değiştirilmez. Kaynakları düzeltme amacıyla eski fazlar yeniden çalıştırılmadı.

Yeni `Termivar-Offline-Product-Composition-phase24-2026-11-11.zip` yalnız yeni kaynak/belge, altı sentetik metadata çıktısı ve Phase24 kayıtlarını içerir. Eski kaynaklar/ZIPler, runtimebinary, wheel, müşteri verisi veya credential kopyalanmaz. Korunmuş commercial_handoff/commercial_case ve geçişli helper kaynakları çalıştırma için gereklidir. Bu arşiv bağımsız runtime veya müşteri dağıtım paketi değildir. Gerçek ZIP boyut/hash ve envanteri `outputs/phase24-composition-delivery-manifest.json` ve `outputs/phase24-composition-source-manifest.json` içindedir.

## NOT_RUN ve durma noktası

Malformed/duplicate/hostile input; yanlış lock sürümü; çelişkili lisans metadata; eksik dependency; büyük kaynak sınırı; hostile symlink/reparse/hardlink; dosya yarışı/değişen kaynak; izin/kısmi yazma/crash; tekrar determinism; gerçek dependency çözümleme/cache; gerçek build/native runtime; yetkili ticari lisans incelemesi; imzalı release/production. Otomatik test/runner/coverage/typecheck/build ve öncekiPhase19eksikUIkabulü yapılmadı. Metadata uyumluluk sorununun normal dosyalarda görülmesi hostile race kabulü sayılmaz.

Native scanner/CLI, yeni assessment/comparison, hedef/ağ/DNS/API/IdP/PG, Windows/VM/driver/servis/admin, müşteri/pilot iletişimi, hukuki finalizasyon, PDF ve push/release/deploy yoktur. Kullanıcının onayladığı iki ek komut ve inceleme sonrasında yalnız offline demo teknik teslimi kapanır. Phase25 veya yeni mikroözellik başlatılmaz.
