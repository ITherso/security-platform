# Phase31 gerçek teslim kaydı

**DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED**

2026-11-12 tarihinde iki izinli ürün çağrısı gerçekten çalıştı; exit kodları **0, 0**, kalan çağrı **0**. Assembly sonrası dört gerçek dosyanın metadata/metin incelemesi tamamlandıktan sonra inspector çalıştırıldı. Sonuç `content_consistent`; bu, çıktıların kendi aralarındaki tutarlılığıdır. Compiler, fiziksel kimlik, devam eden dosya tazeliği veya canlı kabul kanıtı değildir.

Üretim kaynak commit'i `f211a108d094c59c43c556c0677bdfeffd936532`, tree `37b7f7a76c1431e3d7f1d361b1ecab76a63b01f7`. Bu commit'ten sonraki README ve bu teslim belgesi güncellemesi dokümantasyondur; ürün kodu ve eski kaynak/runtime güncellenmez. `source_reference` içindeki platform pin'i `e3b11d3101eafb3178868f391db713639c921c01` eski Phase24 metadata beyanıdır; dondurulmuş runtime pin'i `aa643d40797998d5f615cb5ba5b71b972596abc9` ayrı bir kayıttır. İkisi de attestation değildir.

## Girdi ve historical sınırı

Phase30'un beş artefact'ı ve mevcut kaynak ZIP'inin byte/hash kimliği assembly girdisidir. Eski evidence ve dört historical observation yeni ledger içinde değişmeden korunur. Historical gözlem, current gözlemin yerine geçirilmez.

| Eski girdi rolü | Bayt | SHA256 |
|---|---:|---|
| Evidence | 220041 | `81be491582f1163b7fbf7bc0520825df156db7abf0f543a23c99e6ae0058ab1e` |
| Triage | 211829 | `46590bff728d62c2e5c1989d673a5b46c3de3741fd0458f016e8328b269e7cf8` |
| Coverage | 11625 | `da0d5c62605c7a3c89162d2886275741505d8e967721fc13270f0e42caeca7d6` |
| Summary | 37221 | `91a9813a12e5f81937d355d753604afcd00d0bc0d13daab1ebaa6c3503cf3d0e` |
| Manifest | 7480 | `af4202db09ac16c5cde57392d29207fd862980d952659d4a0ff035ba1772bd3e` |
| Kaynak ZIP | 129296 | `aab4d89f3fbf95992675ce08b095468680ba29fb07e2b85dea7ed1dbd3742485` |

ZIP yalnız sınırlandırılmış binary byte/hash girdisi olarak okundu; açılmadı, çıkarılmadı ve üye içeriği doğrulanmadı. Baseline okuyucunun zorunlu hash koşulu korunur. Yeni current okuyucusunun nullable `current_expected_sha256` alanı ayrı bir beklentidir; eski okuyucuya `None` geçirerek bypass yapılmaz. Bu demo dört current expectation alanını da `null` bırakır; bu durum stale historical başarıya dönüş sağlamaz.

## Gerçek current gözlemler

Dört eski izinli path seçildi. Üç present dosyada toplam **45969 bayt** okundu ve historical/current byte hash'leri eşit gözlendi. Bir izinli alternatifin yokluğu yeniden gözlendi. Doğal değişim, ortaya çıkma veya kaybolma gözlenmedi; kaynaklar bu dalları üretmek için değiştirilmedi.

| Candidate | Göreli path | Current bayt | Historical ve current SHA256 / sonuç |
|---|---|---:|---|
| CAND0001 | `crates/termivar-core/src/outcome.rs` | 16180 | `4f792bc297a614f700dadb65b66ff1087b4efc90df44383ed26e960aa055a942` — `bytes_reobserved_equal` |
| CAND0002 | `crates/termivar-core/src/outcome/mod.rs` | `null` | Her iki hash `null`; `absence_reobserved`, `safe_absence_observed` |
| CAND0003 | `crates/termivar-scanner/src/authorization_review.rs` | 10749 | `c460167b1ce25c7b0dc71feabf23d6af10256e2af14981dedd7e5fe2597894ef` — `bytes_reobserved_equal` |
| CAND0005 | `crates/termivar-cli/src/report_compare.rs` | 19040 | `af383732f8bdec2309b1e8d061e2cf347ea1226646a54cd131361fb0edc1945e` — `bytes_reobserved_equal` |

Historical observation ID ve current observation ID ayrı alanlardır; comparison her iki ID'ye bağlanır. Üç present okuma `stable_bounded_read`, current physical identity `not_exported`; historical physical identity `not_recorded`, iki gözlem arasındaki fiziksel kimlik karşılaştırması `not_comparable`. Eşit byte, aynı fiziksel dosyayı veya reference bağlamının güncelliğini kanıtlamaz.

Guard dört file projection'ına yalnız anlık current metadata tüketimi izni verdi: **3 `fresh_candidate_byte_metadata_only` + 1 `fresh_absence_metadata_only`**; file düzeyinde blocked **0**. Historical hash'ten current projection üretilmez. Bu guard yalnız bu tool'a aittir; fallback, TTL, polling veya genel tazelik garantisi yoktur.

Beş candidate'ın dördünde current-only projection, birinde blocked sonucu vardır. **CAND0004** eski not-allowlisted adaydır; file/history/current ID ve projection `null`, sorgu yapılmadı. `authorization_review` reference'ında CAND0003 eşit byte gözlemi, CAND0004 engelini maskelemez: reference `candidate_reuse_blocked` kalır. Diğer iki reference `candidate_observations_reobserved` fakat context doğrulanmamıştır. 95 external reference'ın **92'si `outside_scope`**; sağlıklı, etkilenmemiş veya değişmemiş sayılmaz. Reference düzeyinde değişim **0**, blocked reuse **1**, context doğrulanmadan yeniden gözlenen **2**.

`reference_context_revalidated=false` dahil **15 güven alanının tamamı false** kalır. Eski kaynak/allowlist, Phase24 inventory/F kapsamı, Phase28 uygulanmamış delta ve component ownership güncellenmez. Conditional scanner bağlamı yeniden değerlendirilmez; compiler resolution, module closure, build/runtime, üretici, hukukî veya release kabulü çıkarılmaz.

## Çalışmış iki tarihsel komut

Bu komutlar tamamlanmış çağrıların kaydıdır; tekrar çalıştırma izni değildir. Sayaç **2/2 tüketildi ve kapandı**; assembly retry, otomatik tekrar veya üçüncü ürün çağrısı yoktur. Eski Phase20–30 bütçeleri ve Phase24/29 insan istisnaları da kapalıdır.

```text
python -I -B security-platform/tools/commercial_candidate_revalidation/assemble_revalidation.py --scope security-platform/tools/commercial_candidate_revalidation/examples/demo_revalidation_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --output-dir outputs/phase31-candidate-revalidation
```

Assembly: exit **0**. Dört dosyanın gerçek metadata/metin incelemesi ve manifest'in üç payload byte/hash bağının kontrolü tamamlandı.

```text
python -I -B security-platform/tools/commercial_candidate_revalidation/inspect_revalidation.py --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json --summary outputs/phase31-candidate-revalidation/revalidation-summary.md --manifest outputs/phase31-candidate-revalidation/manifest.json --output outputs/phase31-candidate-revalidation/inspection-summary.json
```

Inspector: exit **0**, `content_consistent`. Yalnız dört yeni ledger/reuse/summary/manifest girdisini okur; manifest üç payload'ı bağlar, kendisini ve inspection çıktısını kapsamaz. Eski Phase30 artefact'ları/ZIP, candidate kaynakları, eski entry-point/Phase24 dosyaları okunmaz; lexer yeniden çalışmaz. Bağımsız current kaynak gözlemi veya devam eden fiziksel tazelik doğrulaması yapılmaz.

## Gerçek çıktı kimlikleri

Konum: `outputs/phase31-candidate-revalidation/`. Aşağıdaki boyut ve SHA256 değerleri gerçek dosyalardan ölçüldü.

| Dosya | Bayt | SHA256 |
|---|---:|---|
| `revalidation-ledger.json` | 250674 | `d2076a23f56ba19181cd792ce762b65aaae54e4dc83ac412a7e0cec5e382db76` |
| `evidence-reuse.json` | 194223 | `6cd38b27d8734897a236f92986d382da0e37746a9b321a4534d56f768fc5350d` |
| `revalidation-summary.md` | 35690 | `7082ac96cdceeb046a767dcd4831a95324bff86448681279755b6ada382e5f76` |
| `manifest.json` | 5623 | `4515bbfbe603f05bf09e48dcf4ed95ccc8d872ab7c11535a0429b92e6d79f57a` |
| `inspection-summary.json` | 6141 | `72861c99fd46296a1f3bc5c48aec5d28f68d163cbd15af609ed68b947ac7fd90` |

## İnceleme ve yapılmayan kabul

Manuel inceleme gerçek JSON/Markdown/manifest içeriği, historical kayıtların korunması, current-only projection, candidate/reference ayrımı ve ölçülen byte/hash bağları ile sınırlıdır. Otomatik test, hostile-case kabulü veya native ürün kabulü değildir. CAND0004'ün gerçek kapsam engeli, stale historical başarıya fallback'in bütün negatif dallarda reddedildiğini kanıtlamaz.

**NOT_RUN:** `bytes_changed`, `previously_present_now_missing`, `previously_missing_now_present`; file düzeyinde `not_revalidated` ve `revalidation_inconclusive`; expectation/hash mismatch ve yanlış ID/root; hostile JSON/UTF-8; symlink/reparse/hardlink/alias/permission/TOCTOU/race; limit/crash/kısmi yazma; shared-file ve determinism; AST, compiler/module resolution/closure, build/runtime, ağ veya canlı sistem; producer/Git/ownership, insan/hukukî/release kabulü. Önceki açık kabul kapıları korunur.

Yeni kaynak paketinin boyut/SHA256 ve koruma kaydı, paketleme tamamlandığında ayrı [Phase31 teslim manifestinde](../../../../../outputs/phase31-candidate-revalidation-delivery-manifest.json) bulunur. ZIP'in kendi kimliği bu belgeye gömülmez; böylece öz hash döngüsü oluşturulmaz. Bu belge henüz ölçülmemiş ZIP kimliği iddia etmez. Yeni kaynak ZIP'i eski Phase30 girdilerinin veya native runtime'ın yerine geçmez.
