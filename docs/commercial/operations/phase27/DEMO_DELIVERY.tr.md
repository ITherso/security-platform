# Phase27 gerçek teslim kaydı — 2026-11-11

**DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED**

Offline Direct Dependency Attribution & Source Evidence Graph çalışan bağımsız araç ve gerçek sentetik çıktı teslimidir. Source declaration, component attribution ve resolved/build dependency ayrı tutulur. Gerçek binary, feature/target resolution, hukukî dağıtım kararı veya pilot GO oluşturulmadı.

Dal `feat/offline-direct-dependency-evidence`; üretimde kullanılan kaynak commit `4c1a1d24611520a0aa063a8227c7a20b7cd87f74`; başlangıç Phase26 HEAD `cc337415955737755a91084e48480374c211776f`. Son belge commit ve ZIP kimliği ayrı teslim manifestinde ölçülür. ZIP kendi hash’ini içermez.

## Gerçek kaynak ve bildirim sonucu

| Cargo manifesti | Bayt | Declaration | SHA256 |
| --- | ---: | ---: | --- |
| `Cargo.toml` | 2141 | 32 | `bd99cc4f708ccaf3368001fb1203d640b70e665cc515b6802624c0c4554fc299` |
| `crates/termivar-core/Cargo.toml` | 1305 | 10 | `5a230741de40010ab9597321ea3219ee1bcddcc9569320230aa4c1fa2ee2da43` |
| `crates/termivar-scanner/Cargo.toml` | 11848 | 35 | `a51309fca54b8a4585072ed1c022a363e30cf25ff8042a08430d66081de646ff` |
| `crates/termivar-cli/Cargo.toml` | 4774 | 24 | `7a6205bb33518ffc984a378a860fb22436b410b1e0e879c5f1bc1be90ffb59e4` |

Dört manifest toplam20.068 bayt; gerçek file hash/F referansları eski katalogla eşleşti. Toplam101 declaration kaynakta sayıldı:32 workspace template ve69 crate bildirimi.48 açık workspace inheritance,45 optional/dev/target koşullu declaration korundu. Kind sayıları normal54/dev15/build0/workspace_template32; optional=true29, target cfg(unix)1. Renamed dependency veya build-dependency fixture kaynakta bulunmadı, oluşturulmadı.

Çocuk workspace=true bildirimi, aynı pin/root identity, açık root template ve literal workspace üyeliği birlikte aranır. Root’ta10 literal üye var; seçili üç crate üyedir. Exclude/override/glob ve desteklenmeyen yol semantiği tahmin edilmez; üyelik kurulamazsa inheritance yetersiz kalır. Feature/default-feature metadata ayrı tutulur; activation_unknown ve target_evaluation=not_performed. Cargo/semver/feature/target çözümlemesi yapılmadı. Native bin/lib target path’leri metadata’dır; envanterde bulunmayan giriş dosyaları takip edilmedi.

## Ownership ve eski kayıt bağı

Kesin component ownership0; ambiguous2(scanner/CLI), ownership_not_established2(root/core). Scanner veCLI F refs iki native component listesinde; primary manifest metadata’sı bu ortaklığı çözmez. Core yalnız assessment scope’undadır ama primary manifest değildir. Sıfır component_owns_manifest edge’i kaynak sınırına uygundur. Ortak Python pyproject/helper scope’undan ownership veya sıfır runtime dependency çıkarılmaz.

95 declaration için bütün bilinen eski metadata projection alanlarıyla tekil eşleşme bulundu;95 farklı eski D ref.6 declaration,3 aday kümesinde6 eski D kaydına belirsiz bağlanır:
- `D0039` / `D0041`
- `D0044` / `D0076`
- `D0070` / `D0077`

Her belirsiz declaration’ın iki possible D kenarı vardır: toplam12 possible edge. Eski kind/optional/feature/target/git-selector ayrımları mevcut olmadığından yeni ordinal bilgisiyle keyfî seçim yapılmadı. Tekil binding de yalnız sınırlı eski metadata aynılığıdır; component ownership veya runtime inclusion değildir. Lock version/checksum adı üzerinden resolution yapılmadı.

## Grafik ve varyant overlay’i

Grafik566 düğüm içerir:10 component,4 source_manifest,32 workspace template,69 crate declaration ve451 özgün Phase24 D kaydı.256 edge:101 manifest declaration,48 workspace inheritance,95 tekil metadata eşleşmesi,12 possible bağ; component_owns_manifest0. Farklı kayıtlar isimle birleştirilmedi.

Eski451 dependency,111 declaration/340 lock,407 selected-source/44 excluded backend-context aynen korundu. Her eski D, yeni grafikte bir defa temsil edilir. Bunlar unique package sayıları değildir. Phase26 A iki native component, B aynı iki ve sekiz helper seçimini korur; ortak2/yalnız A0/yalnız B8. Yeni overlay dağılımı her iki varyantta:

| Yeni overlay sınıfı | A | B |
| --- | ---: | ---: |
| `evidenced_direct_declaration` | 0 | 0 |
| `conditional_declaration` | 0 | 0 |
| `ambiguous_declaration_binding` | 6 | 6 |
| `source_scope_only` | 95 | 95 |
| `unattributed` | 306 | 306 |
| `excluded_context` | 44 | 44 |
| `insufficient_evidence` | 0 | 0 |

Overlay’de conditional sınıfının0 olması,45 kaynak koşulunun kaybolması değildir: kesin component owner kurulamadığından deklarasyonlar source_scope_only/ambiguous sınırında kalır; koşullu declaration id’leri ayrıca taşınır. Kaynak kanıtı farkı runtime dependency farkı değildir. Eski Phase26 enum ve dosyaları değişmedi.

Ayrı461 lisans subject’i,459 unknown, iki eski scoped MIT, tek L0001 evidence/460 yeni evidence eksikliği, tüm461 insan incelemesi ve1377 açık blocker korunur. Yeni edge lisans incelemesi veya redistribution/release yetkisi sağlamaz. Her global sonuç ve varyant demo_only=true; `dependency_resolution_performed=false`, `build_closure_verified=false`, `runtime_inclusion_verified=false`, `license_review_completed=false`, `redistribution_authorized=false`, `release_authorized=false`, `production_ready=false`, `producer_verified=false`, `human_review_verified=false`, `build_verified=false`, `runtime_verified=false`.

## Gerçek artefact girdileri ve iki komut

On eski dosya açık CLI argümanlarıyla seçildi; iki summary mevcut dört payload manifestlerini gerçek byte’larıyla bağlar. Eski dosyalar toplam2.969.532 bayt, scope 5762 bayt (SHA256 `8d511d047c148e438bc9d3b4e9b7aada1905d29546efe4b21360d586110efdd1`);12MiB sınırının altında. Dört Cargo ayrı4MiB toplam/256KiB tek dosya bütçesindedir. Product Phase25 dosyalarını veya Cargo.lock/ham source/LICENSE gövdesini yeniden okumaz. Mevcut Cargo.lock yalnız başlangıç manuel metadata incelemesinde77.260 bayt/306 kayıt olarak görülmüş, resolver çalıştırılmamıştır.

| Eski kaynak / rol | Bayt | SHA256 |
| --- | ---: | --- |
| `outputs/phase24-composition/composition-inventory.json` (inventory) | 41016 | `57858a6de13a3f0994f3d21cc4564ccb430ae15eb2e6e9c2f885365492ce1a4e` |
| `outputs/phase24-composition/dependency-license-ledger.json` (dependencies) | 481295 | `e5cb40e42c46bf66b8721bf0f386b9be8112518e3cd5b4342e6b16682715cfe6` |
| `outputs/phase24-composition/release-constraints.json` (constraints) | 472825 | `8997a93eb051ed2c0e72f59b92e17c129a3082135ba7044e6b33369202bbdd9d` |
| `outputs/phase24-composition/composition-summary.md` (summary) | 15004 | `64862044de910a9c183ee1d89faff1b8625ab77477501159053e37e5e46edfcd` |
| `outputs/phase24-composition/manifest.json` (manifest) | 1814 | `95c04d5c14f2b6d017154817aec968e453d4a2772ba750baaf0b0ad47796cc32` |
| `outputs/phase26-pilot-variants/variant-analysis.json` (analysis) | 48267 | `16ec8d8d509e3bfc6dc689a00262e0e0d6bb9d3e71d3dee859a8f9fb06aa44ce` |
| `outputs/phase26-pilot-variants/dependency-exposure.json` (dependencies) | 718170 | `f873a031237111fd63047eb4ecea8dff83c28e2afdf51802560e89bf81ee502e` |
| `outputs/phase26-pilot-variants/license-readiness.json` (licenses) | 942012 | `94dbe23914c43a735bd9374aa3d389c985a68c97caccd1da16f3fac52caa89d2` |
| `outputs/phase26-pilot-variants/variant-comparison.md` (summary) | 244998 | `cb8a2c9ae08cd4da02ac3dd1f94f64f5566c89e88ad15dab49485efe3e6f4a4b` |
| `outputs/phase26-pilot-variants/manifest.json` (manifest) | 4131 | `9db501cf6fb091a3b1aebc21a22726c839760b37c9ff1b3b212feb98c7c4883f` |

Pinler eski kaynak kapsamı beyanıdır: Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3`, platform `e3b11d3101eafb3178868f391db713639c921c01`. Git/build/producer attestation değildir. Tüm CLI argümanları [README](../../../../tools/commercial_dependency_evidence/README.md) ve workspace `outputs/phase27-generation-record.json` kaydındadır.

| Çağrı | Exit | Gerçek sonuç |
| --- | ---: | --- |
|1 assemble_evidence_graph.py|0|Üç JSON, Markdown ve manifest oluşturuldu|
|2 inspect_evidence_graph.py|0|`internal_content_status=content_consistent`|

İkinci çağrı yalnız ilk başarılı üretim ve beş gerçek dosyanın manuel okunmasından sonra çalıştı. Bütçe2/2 tüketildi; tekrar/üçüncü çağrı yoktur. Phase20/21 1/1; Phase22/23/25/26 2/2; Phase24 üç çağrı ve kapalı insan retry istisnası değişmedi. Bu iki çağrı yazılım testi veya gerçek kabul değildir.

| Gerçek çıktı | Bayt | SHA256 |
| --- | ---: | --- |
| `outputs/phase27-dependency-evidence/dependency-evidence-summary.md` | 119620 | `eeea3e40006eda7c2b6fda6afe4453ecc98b51ca048be45484618395fa3fb946` |
| `outputs/phase27-dependency-evidence/direct-dependency-evidence.json` | 781353 | `112c459a33d7b4181411ea527fef1373a9bc8360a5f44d01ce7559bf2e916813` |
| `outputs/phase27-dependency-evidence/inspection-summary.json` | 6506 | `be24f8a7f6216257cc5e76c32d2bbba448685aa008f601e909a988d5c87e8f47` |
| `outputs/phase27-dependency-evidence/manifest.json` | 4165 | `6d23970109da92c2b6ec88fb42ea77bba46ecccbb1dece2c5e6069e500147948` |
| `outputs/phase27-dependency-evidence/source-evidence-graph.json` | 414825 | `13693e7b5c5423a47846d7c5f3598883232a6bca2234b74ebe525d6828dbd042` |
| `outputs/phase27-dependency-evidence/variant-dependency-evidence.json` | 463952 | `5b2528b9b2bdfbabba93ec1d710900f31e26352fd1bca34f21c352f680767a1d` |

Manifest dört payload’ın gerçek byte/hash bağını taşır; own hash dışarıda kalır. Inspector yalnız beş yeni dosyada kapalı model/identity/ref/count, normalized inheritance/ownership/binding, graph/overlay, Markdown ve manifest iç tutarlılığını inceledi. `original_phase24_phase26_files_read=false`, `original_source_manifests_read=false`. Raw TOML doğruluğu, kaynak üreticisi, activation veya binary bilgisi bağımsız yeniden doğrulanmadı.

## Manuel inceleme, değişiklikler ve koruma

Kaynak sözleşmeleri ve code/API kaynak üzerinden incelendi. Gerçek JSON sayımları,45 koşullu metadata, dört ownership sonucu, üç belirsiz D çifti, global451 D düğümü, definite/possible kenarlar ve UTF-8 Markdown okundu. Bağımsız salt okunur stdlib metadata incelemesi tüm101 kaynak TOML konumu/alanı,48 açık üye/template ilişkisi ve451 eski D alanı/pointer/hash/key ile uyum bildirdi. Bu browser, hostile-input veya production kabulü değildir.

Önceki233 artefact,207 kaynak/belge,21 frontend asset ve60030 bayt production wheel gerçek byte/SHA256 karşılaştırmasıyla korundu. Wheel SHA256 `59ad0bfee4d5427e4dc197e0c535cc3d2ade4c3c621d4919fe9d2c3a995bbf06`. HBF HEAD `74a88ed336cb8a0a2fab16e20389c9410590c292`; Termivar HEAD `6a2639348c2366d0bf71b9a34e5484d40aa393a3`; ağaçlar temiz. Platform runtime `aa643d40797998d5f615cb5ba5b71b972596abc9` değişmedi. Üretim snapshot’ındaki14 tool/example/README dosyası çıktı üretiminden sonra değişmedi.

Değişen19 dosya yalnız yeni tool dizinindeki14 dosya ve phase27 altındaki5 belgedir; tam dosya listesi kaynak manifestindedir. Eski source/artefact/lock/lisanslar yeniden biçimlendirilmedi, silinmedi veya üzerine yazılmadı. Ayrı ZIP yeni19 dosya+6 gerçek çıktı+5 yeni metadata kaydı+kaynak manifestini içerir. Eski kaynak/Cargo/lock/LICENSE gövdeleri, archive, binary, wheel, DB veya credential kopyaları yoktur. Çalışmak için korunmuş checkout ve açık eski girdiler gerekir.100 eski tool kaynağının byte metadata referansı execution closure doğrulaması değildir.

## NOT_RUN ve kapanış

- `malformed_duplicate_hostile_JSON`
- `broken_or_unsupported_TOML`
- `wrong_workspace_inheritance_membership_exclusion_override`
- `renamed_build_dependency_edge_cases`
- `feature_resolution`
- `target_cfg_evaluation`
- `Cargo_metadata_dependency_resolution`
- `multiple_lock_version_resolution`
- `source_manifest_digest_manipulation`
- `hostile_invalid_node_edge_references`
- `graph_file_record_limits`
- `symlink_reparse_hardlink`
- `TOCTOU_filesystem_race`
- `permission_crash_partial_write_power_loss`
- `repeat_run_determinism`
- `real_native_build_closure`
- `binary_runtime_inclusion`
- `legal_license_producer_review`
- `production_release_acceptance`
- `customer_pilot_willingness_to_pay`
- `automatic_tests_runner_coverage_typecheck_build`
- `Phase19_outstanding_UI_acceptance`

Test/runner/coverage/typecheck/build/install/Cargo/package manager/resolver/native runtime, canlı ağ/DNS/hedef/API/IdP/PG/VM/driver/servis/admin, gerçek müşteri-pilot-satış, hukukî finalizasyon, PDF, push/release/deploy yapılmadı. Kaynak/hash tutarlılığı producer veya hukukî yetki değildir. Metadata allowlist’i secret detection/anonimlik garantisi değildir. Önceki NOT_RUN kapıları kapanmadı.

Phase27 yalnız offline kaynak kanıtı grafiğinin teknik teslimi olarak kapanır. Gerçek dependency closure, binary/runtime inclusion, uzman/hukukî/üretici doğrulaması ve production/release kabulü açık kalır. Yeni mikro özellik, üçüncü ürün komutu veya Phase28 başlatılmaz.
