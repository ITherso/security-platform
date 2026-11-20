# Termivar Offline Review Attribution

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Phase19 `finalize_desk.py` her kararda `reviewer_ref=null` ve `reviewed_at=null` yazar. Phase16 builder bu durumda her gözleme `reviewer_reference_missing` ve `review_timestamp_missing` engellerini ekler. Bu yüzden masada "dahil et" olarak işaretlenen hiçbir gözlem müşteri taslağına ulaşmaz.

Bu araç eksik adımı ayrı ve eklemeli olarak sağlar. Sonlandırılmış desk overlay'ine açıkça beyan edilen bir reviewer referansı ve inceleme zamanı yazar. Karar context digest'ini mevcut Phase18 fonksiyonuyla (`decision_context_digest`) yeniden hesaplar. Sonuç, mevcut Phase18 `reconcile_review.py` aracının kabul ettiği biçimde yeni bir overlay'dir. Phase16/18/19 kaynak dosyaları değişmez; araç onların doğrulayıcılarını import eder.

Attribution, kararı **kimin beyan ettiğini** kaydeder. Kişinin kimliğini doğrulamaz, gerçek bir insan incelemesinin yapıldığını kanıtlamaz, dahil etmeyi onaylamaz, teslim veya yayın yetkisi vermez.

## Çalıştırma

Python standart kütüphanesi kullanılır; paket kurulumu yoktur. Komutlar, `security-platform/` (deponun gerçek bir kopyası; junction kabul edilmez) ve `outputs/` bulunan workspace kökünden çalıştırılır. Girdi olarak Phase17, Phase18 ve Phase19 `finalize_desk` çıktıları gerekir (bkz. [Phase19 README](../commercial_review_desk/README.md)).

```text
python -I -B security-platform/tools/commercial_review_attribution/attribute_review.py --review-packet outputs/phase18-review-packet/review-packet.json --packet-manifest outputs/phase18-review-packet/review-packet-manifest.json --handoff-input outputs/phase17-intake/handoff-input.json --overlay outputs/phase19-finalized-overlay/decision-overlay.json --overlay-manifest outputs/phase19-finalized-overlay/overlay-manifest.json --reviewer-ref analyst-07 --reviewed-at 2026-11-20T10:00:00Z --output-dir outputs/phase19-attributed-overlay
```

Ardından mevcut araçlar değiştirilmeden, attribution yapılmış overlay ile çalıştırılır:

```text
python -I -B security-platform/tools/commercial_review/reconcile_review.py --review-packet outputs/phase18-review-packet/review-packet.json --packet-manifest outputs/phase18-review-packet/review-packet-manifest.json --handoff-input outputs/phase17-intake/handoff-input.json --overlay outputs/phase19-attributed-overlay/decision-overlay.json --output-dir outputs/phase19-attributed-reconciled
python -I -B security-platform/tools/commercial_handoff/assemble.py --input outputs/phase19-attributed-reconciled/handoff-input.json --output-dir outputs/phase19-attributed-handoff
```

Araç reconciliation veya builder'ı kendiliğinden başlatmaz. Bütün yollar cwd-relative olmalıdır; mutlak yol, `..`, link ve junction reddedilir. Çıktı dizini yeni olmalıdır; mevcut boş dizin bile kullanılmaz.

## Beyan kuralları

- `--reviewer-ref`: 1–128 karakter, tek satır, yalnız yazdırılabilir karakterler (sekme, satır/paragraf ayırıcı, kontrol ve biçim karakterleri yok). Baş/son boşluk kabul edilmez. Phase16'nın eksik reviewer sayıp engellediği yer tutucular (`not_provided`, `not_verified`, `pending_decision`, `not_assigned`; büyük/küçük harf duyarsız) kabul edilmez. Temel kural Phase18 overlay doğrulayıcısıyla aynıdır.
- `--reviewed-at`: `YYYY-MM-DDTHH:MM:SSZ` biçiminde geçerli bir takvim zamanı; Phase18 overlay kuralıyla aynıdır. Saatten varsayılan değer alınmaz. Gelecek tarih reddedilmez, çünkü bu alan bir beyandır, ölçüm değildir.
- Aynı referans ve zaman, overlay'deki **her** karara yazılır. Daha önce reviewer veya zaman taşıyan bir overlay'in üzerine yazılmaz (`attribution_already_present`).

## Kontroller

1–3 ve 6. adımlar import edilen sahip fonksiyonlarıyla yapılır; 4. ve 5. adımlar bu aracın kendi kapalı kontrolleridir:

1. Packet `validate_packet` ile, packet manifest'i `validate_packet_manifest` ile, handoff girdisi `load_input` ile kontrol edilir.
2. Overlay `validate_overlay` ile doğrulanır. Bu adım her kararın 17 alanlık context digest'ini de kontrol eder. Overlay byte'ları `finalize_desk` çıktısının birebir aynısı olmalıdır (`render_overlay`).
3. `bind_decisions` ile packet ve orijinal Phase17 girdisine bağlanır.
4. Kararlar Phase19 desk kararları olmalıdır (`DESK-<observation_id>`). Reviewer ve zaman boş olmalıdır. En az bir karar bulunmalıdır.
5. `overlay-manifest.json` kapalı alan kümesiyle kontrol edilir. `finalize_desk` işlemi, overlay byte kimliği, packet/packet manifest/handoff girdi kimlikleri, gözlem ve karar sayıları ile `false` güven bayrakları eşleşmelidir. Manifest'te adı geçen karar taslağı açılmaz; yalnız biçimi kontrol edilir.
6. Yeni satırlar yeniden `validate_overlay` ve `bind_decisions` kontrolünden geçer. `review_context` içindeki `human_review_verified`, `producer_verified` ve `release_authorized` değerleri `false` kalır.

## Çıktılar

- `decision-overlay.json`: `termivar-analyst-decision-overlay/v1`, `finalize_desk` ile aynı serileştirme. Yalnız `reviewer_ref`, `reviewed_at` ve `decision_context_digest` değişir.
- `attribution-manifest.json`: `termivar-review-attribution-manifest/v1`, en son yazılır. Beş girdinin ve overlay'in byte kimliklerini, sayıları ve şu bayrakları içerir: `human_review_verified=false`, `reviewer_identity_verified=false`, `producer_verified=false`, `release_authorized=false`, `native_assessment_verified=false`, `full_bundle_verified=false`. Reviewer metni, zaman ve dosya yolları manifest'e ve konsola yazılmaz.

## Hatalar

Hata çıktısı sabit bir koddur; yol, reviewer metni veya dosya içeriği içermez.

- exit 2: `review_attribution: <kod>`. Kodlar:
  - `invalid_arguments`
  - `attribution_invalid_reviewer_ref`
  - `attribution_reviewer_ref_placeholder`
  - `attribution_invalid_review_time`
  - `attribution_overlay_not_canonical`
  - `attribution_requires_decisions`
  - `attribution_not_desk_overlay`
  - `attribution_already_present`
  - `attribution_overlay_manifest_fields`
  - `attribution_overlay_manifest_inputs`
  - `attribution_overlay_manifest_input_mismatch`
  - `attribution_overlay_manifest_mismatch`
  - `output_directory_must_be_new`
  - sahip doğrulayıcılarının kodları (ör. `decision_context_digest_mismatch`, `relative_path_required`)
- exit 1: `review_attribution: local_attribution_failed; no successful attribution is claimed`.

Başarısız bir çalışma, kendi yeni kısmi çıktısını veya staging dizinini bırakabilir. Güvenli silme veya düşmanca yarış durumlarına dayanıklılık iddia edilmez.

## Sınır

Müşteri taslağı yalnız Phase16'nın kendi seçim kurallarını geçen gözlemi gösterir: `in_scope`, `include_with_limits`, uygun `review_status`, `safe_summary`, reviewer referansı ve zaman. Reviewer referansı müşteri taslağına yazılmaz; yalnız iç özette "kimliği doğrulanmadı" etiketiyle görünür. Global teslim engelleri sürer: `demo_only_not_for_delivery`, `human_review_not_verified`, `release_not_authorized`, `authorization_not_verified`. Karar verilmemiş diğer gözlemler varsa `observation_selection_blocked` da sürer. Taslak "inceleme eksik" olarak işaretli kalır.

## Test

```text
python -B -m pytest -p no:cacheprovider tests/commercial_review_attribution
```

Test geçici bir workspace kurar: `git ls-files` ile listelenen dosyalar ve bu araç `security-platform/` altına kopyalanır. Phase17 → 18 → 19 commit edilmiş örnek girdilerden README komutlarıyla çalıştırılır. Bir gözlemi dahil eden sentetik bir desk taslağı sonlandırılır. Sonra attribution, `reconcile_review` ve builder çalıştırılır. Kopyalama başarısız olursa test atlanır.
