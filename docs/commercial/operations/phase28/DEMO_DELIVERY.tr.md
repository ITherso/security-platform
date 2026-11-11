# Phase28 gerçek teslim kaydı — 2026-11-11

**DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED**

Offline Target Entry-Point Coverage & Source-Scope Delta Workbench, dört gerçek Cargo manifestinden üç explicit target ilişkisini çıkardı; exact allowlist üzerinden üç mevcut dosyanın byte/SHA256 kimliğini gözledi ve üç uygulanmamış repository-level kapsam önerisi üretti. Kaynak varlığı, envanter üyeliği, component ownership ve gerçek build/runtime kabulü ayrı tutuldu. Phase24 envanterine yazılmadı.

Dal `feat/offline-entrypoint-coverage`; iki ürün çağrısında kullanılan kaynak commit `54d3671d7bf880907a13aa2567a03ae078b94e5c`; başlangıç Phase27 HEAD `6cdbe4548b3879a0f8ed79a2f3a79d2f79018741`. Gerçek sonuçlardan sonra yalnız bu teslim belgesi güncellenir. Son belge commit'i ve gerçek ZIP kimliği [dış teslim manifestinde](../../../../../outputs/phase28-entrypoint-coverage-delivery-manifest.json) tutulur. ZIP kendi hash'ini içermez.

## Gerçek Cargo ve target dosyaları

| Cargo manifesti | F bağı | Bayt | Explicit target | SHA256 |
| --- | --- | ---: | --- | --- |
| `Cargo.toml` | F0087 | 2141 | Yok; virtual workspace | `bd99cc4f708ccaf3368001fb1203d640b70e665cc515b6802624c0c4554fc299` |
| `crates/termivar-core/Cargo.toml` | F0095 | 1305 | lib / termivar_core / src/lib.rs | `5a230741de40010ab9597321ea3219ee1bcddcc9569320230aa4c1fa2ee2da43` |
| `crates/termivar-scanner/Cargo.toml` | F0099 | 11848 | lib / termivar_scanner / src/lib.rs | `a51309fca54b8a4585072ed1c022a363e30cf25ff8042a08430d66081de646ff` |
| `crates/termivar-cli/Cargo.toml` | F0090 | 4774 | bin index0 / termivar / src/main.rs | `7a6205bb33518ffc984a378a860fb22436b410b1e0e879c5f1bc1be90ffb59e4` |

Dört manifest toplam 20.068 bayttır. Root workspace otomatik target sayılmadı. `[lib]` ve `[[bin]]` alanlarındaki üç explicit path, scope'taki exact manifest/target/file allowlist bağıyla değerlendirildi.

| Yerel dosya | Root-relative dosya | Tür | Gerçek bayt | Gerçek SHA256 |
| --- | --- | --- | ---: | --- |
| EPF0001 | `crates/termivar-core/src/lib.rs` | lib | 3156 | `294513eeb3d23d1989fcfe8e9e0f74b23f05f090b4263da611a6b019e998efd1` |
| EPF0002 | `crates/termivar-scanner/src/lib.rs` | lib | 21450 | `61f68b72ecd83580ce42ae9fbf8fc55a835b231333717f4a32bcf97fab976e40` |
| EPF0003 | `crates/termivar-cli/src/main.rs` | bin | 279631 | `c96f2e3a27be6f1ecbbbcaae539c3b9ec87253c25d0043b2891f9a6621ec0bff` |

Üç dosya toplam 304.237 bayttır; her biri `present_and_hashed`, `source_file_presence=present`, `regular_file=true` sonucunu taşır. Scope'taki beklenen hash'ler başarılı gözlem yerine kullanılmadı; assembly gerçek bounded/chunked okumayla kimlikleri ölçtü. Parçalar en fazla 64 KiB'dir. CLI dosyası 256 KiB manifest tavanını aşar; ayrı 512 KiB target-file ve 1 MiB toplam target bütçesiyle okundu. Dosya gövdeleri decode/parse edilmedi, JSON/Markdown/log/ZIP'e kopyalanmadı.

Kaynakta olmayan target veya path üretilmedi. Cargo auto target keşfi, Rust module graph, Cargo metadata/build/check/test/resolver ve feature/target activation çalıştırılmadı. Yerel target/EPF referansları executable, imza, Git commit attestation veya global release kimliği değildir.

## F coverage ve korunmuş ownership

Global F kataloğu 111 satır; component source_file_refs birleşimi 107 farklı F'dir. Birleşim dışındaki dört kayıt:

| F | Kaynak | Mevcut bağlam |
| --- | --- | --- |
| F0005 | `requirements-build-lock.txt` | Excluded backend requirements |
| F0006 | `requirements-lock.txt` | Excluded backend lock |
| F0086 | `Cargo.lock` | Explicit selected-source metadata |
| F0088 | `LICENSE` | Local license file |

Eski F satırlarında genel selected/metadata_only/excluded alanı yoktur; böyle bir bayrak eklenmedi. Component birleşiminde olmamak otomatik excluded değildir. F0088 için dar dependency-manifest projection'ında bağlam bulunmaması, dosyanın önceki yerel lisans bağlamını değiştirmez. F0004 ortak pyproject, sekiz helper için runtime dependency veya distribution sahipliği kanıtı sayılmadı.

Üç native dosyanın her biri `not_listed_in_global_f_catalog`, `not_referenced_by_component`, `phase24_source_reference=null`, `phase24_identity_status=not_in_catalog` ve `source_present_inventory_gap` taşır. Fiziksel dosya eksikliği sıfırdır. Envanter boşluğu dosyanın mevcut olmadığı anlamına gelmez. Yeni F numarası atanmadı veya eski kimlik alanı yeni hash ile geriye dönük doldurulmadı.

Kesin component ownership 0 kaldı. Core manifesti `ownership_not_established`; scanner/CLI `ambiguous_ownership` durumundadır. Üç target da `component_ownership_unresolved` ve `established_component_id=null` taşır. Root workspace'in eski ownership eksikliği çözülmedi. Dosya varlığı, target veya Cargo package adı kesin component ataması oluşturmadı.

## Üç uygulanmamış repository-level öneri

Gerçek delta sayımları: 3 benzersiz proposal, 3 source-file ve 3 target referansı; uygulama yetkili 0, uygulanmış 0. Her öneri `proposal_level=repository_source_coverage`, `proposed_scope_action=propose_selected_source_inclusion`, `current_phase24_coverage=source_present_inventory_gap`, `proposed_component_id=null` taşır. `application_authorized=false`, `application_performed=false`, `phase24_inventory_modified=false`, `component_ownership_verified=false` korunur.

Her dosya için bir global öneri, gerçek explicit target → exact allowlist → present/hash → F boşluğu zincirinden üretildi. Native kaynaklar assessment/reporting component'ine kesin atanmadı. Inventory patch edilmedi; component source listesi değiştirilmedi. Öneri tam source completeness, dependency closure, binary/runtime inclusion veya lisans/dağıtım yetkisi değildir.

| Varyant | Seçilen component | Kesin component-owned target | Ownership çözülmemiş potansiyel target | Global öneri referansı |
| --- | ---: | ---: | ---: | ---: |
| `native-assessment` | 2 | 0 | 3 | 3 |
| `native-offline-support` | 10 | 0 | 3 | 3 |

İki varyantın üç target ilişkisi de `candidate_scope_relevant_ownership_unresolved` durumundadır. Ortak component 2; yalnız A 0; yalnız B 8'dir. Sekiz helper farkı native target veya ek dependency üretmedi. Global target 3 ve benzersiz proposal 3'tür. Varyant target referans toplamı 6'dır; bu 6 global proposal değildir. A/B aynı üç öneriye referans verir. Completeness oranı, risk/güvenlik puanı veya production readiness artışı üretilmedi.

## Kaynak ve lisans sınırları

15 eski artefact explicit scope descriptor'larıyla seçildi; byte kimliklerinin toplamı 4.753.447 bayttır. Phase24/26/27 sürümlü sözleşmeler ve gerçek dört payload manifest bağları korunur. Pin beyanları Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3` ve platform `e3b11d3101eafb3178868f391db713639c921c01` değerleridir; producer veya Git/build attestation değildir.

Eski 451 dependency kaydı, 6 belirsiz D kaydı, 0 kesin owner; ayrı 461 lisans subject'i, 459 unknown, 2 eski scoped MIT beyanı, 1 önceki fresh evidence/460 missing, 461 insan incelemesi ve 1377 açık blocker korunur. Yeni target/file veya delta ilişkisi lisans kanıtı oluşturmaz ve önceki kabul kapılarını kapatmaz.

Tüm yeni global sonuçlar ve varyantlar `demo_only=true`; `source_inventory_updated=false`, `scope_delta_applied=false`, `component_ownership_verified=false`, `dependency_closure_verified=false`, `build_verified=false`, `runtime_verified=false`, `producer_verified=false`, `human_review_verified=false`, `license_review_completed=false`, `redistribution_authorized=false`, `release_authorized=false`, `production_ready=false` olarak kalır.

## İki gerçek ürün komutu

[Üretim kaydı](../../../../../outputs/phase28-generation-record.json) tam komutları ve gerçek exit code'ları tutar. Komut 1:

```powershell
python -I -B security-platform/tools/commercial_entrypoint_coverage/assemble_coverage.py --scope security-platform/tools/commercial_entrypoint_coverage/examples/demo_coverage_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase28-entrypoint-coverage
```

Exit `0`: coverage, uygulanmamış source-scope delta, variant projection, Markdown ve manifest oluşturuldu. Inventory update, delta application, component ownership ve build bayrakları false kaldı.

Yalnız ilk başarılı çağrı ve beş gerçek dosyanın manuel incelemesinden sonra komut 2:

```powershell
python -I -B security-platform/tools/commercial_entrypoint_coverage/inspect_coverage.py --coverage outputs/phase28-entrypoint-coverage/entrypoint-coverage.json --delta outputs/phase28-entrypoint-coverage/source-scope-delta.json --variants outputs/phase28-entrypoint-coverage/variant-entrypoint-projection.json --summary outputs/phase28-entrypoint-coverage/entrypoint-summary.md --manifest outputs/phase28-entrypoint-coverage/manifest.json --output outputs/phase28-entrypoint-coverage/inspection-summary.json
```

Exit `0`: `internal_content_status=content_consistent`. Gerçek çağrı sayısı 2/2, kalan 0; üçüncü çağrı veya retry yoktur. Phase20/21 1/1; Phase22/23/25/26/27 2/2; Phase24 üç çağrı ve kapalı özel retry istisnası değişmedi. Bunlar yazılım testi veya gerçek source/build/runtime kabulü değildir.

## Gerçek çıktı boyutları ve SHA256

| Çıktı | Bayt | SHA256 |
| --- | ---: | --- |
| `entrypoint-coverage.json` | 63930 | `f75e0e61789d90da544a05a09eb6452bb293e575670f72c311241d8ec3ec832b` |
| `source-scope-delta.json` | 10288 | `24d56afe089636d34a9ffdae511b4fd807bafe6f854794f3b4cf85a577bdd2ac` |
| `variant-entrypoint-projection.json` | 15053 | `224fab9939be9c503b02c86a76ef90692829072a9afc70f739d5ea4f8ab0dba8` |
| `entrypoint-summary.md` | 31703 | `1e85b293ec46e8a9058d060aa337d057c6f33ac95d25ba61cba7a90b5a705912` |
| `manifest.json` | 6465 | `8e3ffcc2c408c58aa0ad9944c4b726902631e9c4207ccd3eb87e7f385f0eba51` |
| `inspection-summary.json` | 6820 | `1d5d12a7e77088f0dd69a269bfd109555a4273544907df898ea4a770bbe88e67` |

Altı dosya `outputs/phase28-entrypoint-coverage/` altındadır. Manifest ilk dört payload'ın gerçek byte/hash kimliklerini bağlar; kendi hash'i dışarıda ölçülür. Inspector beş yeni girdi dosyasının gerçek byte/hash kimliklerini raporlar.

Inspector kapalı model, target/source-file/coverage/delta/variant referansları, sayımlar, normalize metadata, ownership sınırı, Markdown ve manifest iç tutarlılığını kontrol etti. `original_phase24_phase26_phase27_files_read=false`, `original_source_manifests_read=false`, `original_target_files_read=false`. Gerçek native kaynak, pinlenmiş Git commit veya üretici bağımsız yeniden doğrulanmadı. `content_consistent` source completeness, successful build veya release kabulü değildir.

## Manuel inceleme, koruma ve paketleme

Reader, saf builder, renderer, sözleşme ve CLI entegrasyonları kaynak üzerinden incelendi. Gerçek JSON/Markdown'da dört manifest, üç explicit path/allowlist bağı, 304.237 gözlenen byte, üç F boşluğu, üç tekil repository proposal, sıfır owner ve iki varyantın çözülmemiş ilişkileri okundu. Manifestteki dört gerçek payload boyut/SHA256 bağı salt okunur metadata incelemesinde eşleşti. Markdown'da ham dış URL, HTML/script veya mutlak Windows root görülmedi. Bu gözlemler browser, hostile-input veya kaynak completeness kabulü değildir.

[Gerçek koruma kaydı](../../../../../outputs/phase28-preservation-review.json), önceki 249 artefact, 226 kaynak/belge, 21 frontend asset ve 60.030 bayt production wheel için byte/hash eşliğini true kaydeder. Wheel SHA256 `59ad0bfee4d5427e4dc197e0c535cc3d2ade4c3c621d4919fe9d2c3a995bbf06`. Üretim snapshot'ındaki 13 tool/example/README dosyası iki çağrıdan sonra değişmedi. HBF `74a88ed336cb8a0a2fab16e20389c9410590c292` ve Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3` kaynak ağaçları temiz kaldı. Bu metadata kaydı execution closure doğrulaması değildir.

Yeni git kapsamı yalnız 18 dosyadır: tool dizinindeki 13 dosya ve Phase28 altındaki 5 belge. Eski Phase7–27 source/artefact/manifest, backend/operator-console, HBF/Altay, native Termivar, auth/DB/credential, lock/lisans ve wheel değiştirilmedi. Tam yeni dosya listesi Phase28 kaynak manifestinde tutulur.

Ayrı ZIP yalnız yeni Phase28 kod/belge, gerçek sentetik çıktı ve Phase28 metadata kayıtlarını içerir. Eski tam arşiv, üç native entry dosyasının gövdesi, binary/installer/wheel, dependency cache, DB veya credential kopyalanmaz. Çalışmak için korunmuş checkout ve açık eski girdiler gerekir. Gerçek ZIP boyutu, üye sayısı, SHA256, son belge commit'i ve kaynak manifest kimliği [dış teslim manifestinde](../../../../../outputs/phase28-entrypoint-coverage-delivery-manifest.json) ölçülür. Bu belge henüz bilinmeyen ZIP kimliği uydurmaz.

## NOT_RUN ve kapanış

- Malformed/duplicate/hostile JSON.
- Geçersiz, bozuk veya desteklenmeyen Cargo TOML.
- Yanlış target path ve izin verilmeyen kaynak dosyası.
- Source identity/hash manipülasyonu.
- Symlink, junction, reparse ve hardlink saldırgan girdileri.
- Path traversal, TOCTOU ve dosya değişim yarışı.
- Permission/filesystem race.
- Boyut, kayıt, graph veya Markdown limit aşımı.
- Crash, partial write ve power-loss.
- Tekrarlı determinism.
- Cargo otomatik target keşfi.
- Rust module graph analizi.
- Gerçek source completeness kabulü.
- Cargo metadata, feature/target resolution ve gerçek dependency closure.
- Native Termivar build/scanner/runtime ve binary/runtime inclusion.
- Üretici ve pinlenmiş Git commit attestation.
- İnsan/uzman/hukukî lisans veya scope uygulama onayı.
- Ticari release, redistribution, production veya müşteri/pilot kabulü.
- Otomatik test/runner/coverage/typecheck/build/install.
- Önceki açık kapılar; Phase19 UI kabulü.

Kodda koruma bulunması bu kabul çalışmalarının tamamlandığı anlamına gelmez. Ağ/DNS/canlı hedef/API/IdP/PG/VM/driver/servis/admin, müşteri/pilot/satış, hukukî finalizasyon, PDF, GitHub push/release/public deploy yapılmadı. file:// kısıtı sunucu/hosting veya alternatif tarayıcıyla aşılmadı. Metadata allowlist'i secret detection veya anonimlik garantisi değildir.

Phase28 yalnız offline entry-point coverage ve uygulanmamış repository-level source-scope önerisinin teknik teslimi olarak kapanır. Gerçek source completeness, component ownership, producer/Git doğrulaması, build/runtime, dependency closure ve uzman/hukukî/production kararları açık kalır. İki ürün çağrısı ve ölçülmüş teslimattan sonra durulur; üçüncü ürün çağrısı, yeni mikro özellik veya Phase29 başlatılmaz.
