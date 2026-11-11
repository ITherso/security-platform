# Phase25 gerçek lisans kanıtı teslimi

**DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED**

11 Kasım 2026. Mevcut Phase24 kayıtlarına ayrı ve salt okunur evidence overlay’i, yerel kaynak anahtarları, bağlama sonuçları, olay analizi ve inceleme kuyruğu eklendi. Eski ledger/constraints değiştirilmedi. Bu teslim lisans incelemesi, ticari izin, release veya güvenlik kabulü değildir.

[Araç/CLI](../../../../tools/commercial_license_review/README.md), [sözleşme](EVIDENCE_CONTRACT.tr.md), [kimlik bağı](COMPONENT_BINDING.tr.md), [iş akışı](LICENSE_REVIEW_WORKFLOW.tr.md), [güven/veri](TRUST_AND_PRIVACY.tr.md).

## Gerçek üretim

Aşağıdaki iki yeni ürün komutu workspace kökünden birer kez çalıştırıldı; ikisi de **exit 0**. Phase25 hakkı **2/2 tüketildi**. Phase20 1/1, Phase21 1/1, Phase22 2/2, Phase23 2/2 ve Phase24’ün kapalı özel istisnalı3çağrısı değişmedi. Eski CLI tekrar çalıştırılmadı.

```text
python -I -B security-platform/tools/commercial_license_review/assemble_evidence.py --scope security-platform/tools/commercial_license_review/examples/demo_evidence_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --platform-root security-platform --output-dir outputs/phase25-license-evidence
python -I -B security-platform/tools/commercial_license_review/inspect_evidence.py --ledger outputs/phase25-license-evidence/license-evidence-ledger.json --queue outputs/phase25-license-evidence/review-queue.json --conflicts outputs/phase25-license-evidence/binding-conflicts.json --summary outputs/phase25-license-evidence/evidence-summary.md --manifest outputs/phase25-license-evidence/manifest.json --output outputs/phase25-license-evidence/inspection-summary.json
```

Assembly beş dosyayı; inspector altıncı inspection-summary.json dosyasını gerçekten oluşturdu. --summary, gerçek MD byte/hash ilişkisi için ek açık argümandır. Inspector yalnız beş yeni dosyayı okur; Phase24 girdilerini, evidence dosyasını veya native repository köklerini yeniden açmaz. Tam stdout/süreler `outputs/phase25-generation-record.json` içindedir.

## Oluşan gerçek dosyalar

Konum `outputs/phase25-license-evidence/`. Boyut ve SHA256 oluşturulan byte’lardan ölçüldü.

| Dosya | Bayt | SHA256 |
| --- | ---: | --- |
| binding-conflicts.json | 1852 | 7a60b3f594d97415f0af647823848e55d61d53d1d2151396b0fa4251fd5eceb6 |
| evidence-summary.md | 189988 | 629dd5458b727e492afe6c604581ae646f323fef621efe76f73fdc26905fb434 |
| inspection-summary.json | 3413 | b4b172e923177dc5aacfd5c106f70d65c1e95991ab1db9041898474f75cad6ab |
| license-evidence-ledger.json | 726760 | fa48a94625201dc2f15c0ebd380592ada10d9891bf7de82cb63dab84dea52a95 |
| manifest.json | 2386 | 60fb9e95188d4148ec5a3bc0cc8b631c979a6ee5a16eaf54a993cebdc602b27b |
| review-queue.json | 247097 | de4f82b7e990c276daeb66aeb943589a37b5dcc843f1b772c3c51c7f1bc22a45 |

## Kullanılan kaynaklar ve gerçek sonuç

Beş Phase24 girdisi inventory/dependencies/constraints/summary/manifest, açık scope yolları ve beklenen byte kimlikleriyle seçildi. Phase24’ün dört payload manifest bağı ve mevcut strict modelleri yeniden kullanıldı. Bu yeni dependency çözümlemesi veya native kaynak taraması değildir. Kaynak hash’leri evidence-summary.md ve yeni composition_reference içinde tam görünür.

Eski inventory’deki source pin beyanları Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3` ve platform `e3b11d3101eafb3178868f391db713639c921c01` olarak korunur; araç git veya producer attestation üretmez. Phase25 üretim kaynak commit’i `254955988a1e472316df965d91ea50ac71a9cff4`. Son doküman commit/tree kaynak ve teslim manifestlerinde bulunur.

- 461 kaynak lisans kaydı; 461 ayrı source key ve461 queue satırı. Her Lref bir kez temsil edilir.
- Kaynak kapsamı10önerilenbileşen/407seçilikaynakmetadata/44excluded_backend_context. Aynı isimli declaration/lock veya sürüm kayıtları birleşmedi.
- Eski lisans beyanları: iki scoped MIT,459unknown. Tamamı değişmeden kaldı.
- Bu turda gerçek yerel dosyası seçilip yeniden bağlanan kayıt: **1**.
- Bu scope’ta yeni kanıt seçilmemiş veya açık eksik kanıtlı kayıt: **460**. Bu sayı459unknownileaynı kavram değildir; ikinci eski MIT beyanı korunur.
- Queue unique461/row461/group membership461; missing_evidence460 ve evidence_present_review_pending1.
- Bildirilen olay1: yalnız açık istekte evidence_missing. Gerçek conflicting_license_declarations olayı0; ambiguity/unsupported/source-not-verified aggregate kayıt0. Bu, hostile/conflict senaryosu kabulü değildir.

### Gerçek yerel kanıt

L0001 / termivar-assessment-core0.10.0-alpha.3 için mevcut Termivar LICENSE seçildi:1085bayt, SHA256 `d308383be39c28054876444bc46a410a5e753c7df982afce644fab1e7e9f754d`. Beklenen hash eşleşti; Phase24F0088 ve L0001’in eski evidence kapsamıyla sınırlı ilişki kuruldu. Binding durumu `binding_confirmed_within_source`, review durumu `review_required`. Bu üretici, hukuki izin veya redistribution doğrulaması değildir. Aynı belge diğer native bileşene, dependency’ye veya helper’a otomatik yayılmadı.

### Gerçek kanıt eksikliği

L0112 / D0102 / aho-corasick1.1.4, registry lock kaydı ve `/dependencies/101` gerçek eski satırıdır. Lisansı unknown; gerçek belge olmadığı için missing_evidence seçildi. Dosya alanları null, matched ref null, neden explicit_evidence_missing. Yeni lisans metni, üretici veya insan kararı oluşturulmadı.

Bu sürüm MIT License başlık gözlemini ve seçilmiş TOML içindeki sınırlı beyanları metadata olarak işleyebilir; genel lisans metni/SPDX yorum motoru değildir. Yorumlanamayan form, doğrulanmamış harici kanıt veya dependency’yi bildiren manifestin kendi lisansı kesin package applicability bağı oluşturmaz. Tam source row seçimi ile lisansın o pakete uygulanabilirliği ayrı kalır.

## Gerçek inceleme ve sınırı

Root gerçek JSON/MD metadata’sını, iki binding sonucunu, counts/reference/queue ayrımını ve dört payload’ın actual manifest byte/hash bağlarını inceledi; beş eski girdi ile yerel LICENSE kimliği eşleşti. Bağımsız metadata incelemesinde461primary row/pointer/digest ve461eski Lrowpointer/digest/sourcekey gerçek Phase24 kayıtlarıyla eşleşti. İkinci bağımsız incelemede altı dosya ve MD’deki461tam key/row tutarlı bulundu. Product rerun, test veya hukuk incelemesi yapılmadı.

Inspector internal_content_status=content_consistent sonucu yalnız yeni dosyaların kapalı şema, referans, sayım, saf queue/conflict/MD ve manifest byte ilişkisidir. Orijinal kaynak veya evidence dosyasını yeniden doğrulamadı. Metadata/hash iç tutarlılığı imza, source authenticity, dependency closure veya dağıtım yetkisi değildir.

demo_only=true; sekiz bayrak false: license_review_completed, redistribution_authorized, release_authorized, production_ready, build_verified, runtime_verified, producer_verified, human_review_verified. Her461kayıtta human_review_required=true ve phase24_license_review_required=true; evidence kaynaklarında source_verified=false. Gerçek reviewer, tarih, owner, deadline, imza veya onay oluşturulmadı.

Ham lisans/kaynak gövdesi, mutlak kullanıcı kökü, credential veya gerçek kişi/müşteri verisi gözlenmedi. Kayıtlar sınırlı allowlist metadata’sıdır; secret detection, anonimlik veya redaksiyon garantisi değildir. Ayrıntılı kayıt `outputs/phase25-manual-output-review.json`.

## Değişiklikler ve koruma

Yeni19kaynak/belge dosyası:

- `docs/commercial/operations/phase25/COMPONENT_BINDING.tr.md`
- `docs/commercial/operations/phase25/DEMO_DELIVERY.tr.md`
- `docs/commercial/operations/phase25/EVIDENCE_CONTRACT.tr.md`
- `docs/commercial/operations/phase25/LICENSE_REVIEW_WORKFLOW.tr.md`
- `docs/commercial/operations/phase25/TRUST_AND_PRIVACY.tr.md`
- `tools/commercial_license_review/README.md`
- `tools/commercial_license_review/__init__.py`
- `tools/commercial_license_review/assemble_evidence.py`
- `tools/commercial_license_review/component_identity.py`
- `tools/commercial_license_review/composition_adapter.py`
- `tools/commercial_license_review/conflict_analysis.py`
- `tools/commercial_license_review/evidence_binding.py`
- `tools/commercial_license_review/evidence_contracts.py`
- `tools/commercial_license_review/evidence_manifest.py`
- `tools/commercial_license_review/evidence_reader.py`
- `tools/commercial_license_review/examples/demo_evidence_scope.json`
- `tools/commercial_license_review/inspect_evidence.py`
- `tools/commercial_license_review/output_renderer.py`
- `tools/commercial_license_review/review_queue.py`

Önceki201artefact/170kaynak/21frontendasset ve production wheel başlangıç byte/hash envanteriyle karşılaştırılır; son kayıt `outputs/phase25-preservation-review.json`. Git farkı yalnız yeni iki Phase25 kaynak/belge dizinidir. Phase7–24, backend/operator-console, nativeTermivar,HBF,Altay,auth/DB/roller,wheel,lockfile ve lisans değişikliği yoktur.

Yeni `Termivar-Offline-License-Evidence-Review-phase25-2026-11-11.zip` yalnız yeni kod/belge, altı sentetik metadata çıktısı ve Phase25 kayıtlarını içerir. Eski ZIPler, dependencycache, eski kaynak dosyaları veya tam LICENSE metni kopyalanmaz. Çalıştırmak için korunmuş Phase24/geçişli helper checkout’u ve açık kaynak dosyaları gerekir; bu bir bağımsız runtime veya müşteri release paketi değildir. Gerçek kaynak/teslim envanteri ve ZIP boyut/hash’i `outputs/phase25-license-evidence-source-manifest.json` ve `outputs/phase25-license-evidence-delivery-manifest.json` içindedir.

## NOT_RUN ve durma

Malformed/duplicate JSON; hostile Unicode/kontrol karakterleri; yanlış/eksik kimlik; sahte/çelişen harici evidence; değiştirilmiş ledger; yanlış manifest/hash; boyut/kayıt limitleri; symlink/reparse/hardlink; okuma sırasında değişen kaynak; permission/race/crash/kısmi yazma/power loss; tekrar determinism; gerçek dependency çözümleme; hukuki/lisans/kurumsal inceleme; imzalı binary/release. Otomatik test/runner/coverage/typecheck/build, native runtime ve öncekiPhase19eksikUI kabulü yapılmadı.

Ağ/DNS/hedef/API/IdP/PG, Windows/VM/driver/servis/admin, package manager/indirme, müşteri/pilot/satış iletişimi, hukuki finalizasyon, PDF ve push/release/deploy yoktur. İki yeni ürün komutu ve inceleme sonrası yalnız offline demo teknik teslimi kapanır. Phase26 veya mikroözellik başlatılmaz.
