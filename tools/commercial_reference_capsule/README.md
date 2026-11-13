# Offline guarded reference capsule ve portable lookup

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

Bu bağımsız offline araç, Phase32'nin doğrulanmış ve küçültülmüş wire metadata'sını tam dört üyeli bir kapsül ZIP'ine taşır. Açık reference ID lookup'u yalnız kapsüldeki kayıtları kullanır. Kapsül özgün çalışma alanı veya Phase31/32 araçları olmadan iç bütünlük bakımından incelenebilir; kaynak dosyalar yeniden gözlenmez.

Kaynak hazırlığı aşamasında Phase33 ürün çağrısı **0**. Henüz gerçek assembly/inspection/lookup başarısı, kapsül veya teslim ZIP'i boyutu/SHA256 iddia edilmez. Önceki Phase32 sayımları yeni ürün sonucu yerine geçirilmez.

## Giriş ve kapalı disclosure sınırı

Assembly yalnız açık request ve dört Phase32 dosyası okur: response, selection, summary, manifest. Sıra: strict parse → gerçek `consumer_contracts.validate_documents(response, selection)` → gerçek `output_renderer.render_summary` byte eşliği → gerçek üç payload için `artifact_manifest.manifest_data` byte/SHA256 eşliği. Eski builder/CLI veya Phase31 guard yeniden çalıştırılmaz.

Request `termivar-offline-guarded-reference-capsule-request/v1` tam yedi alan taşır: `schema_version`, `mode`, `capsule_reference`, `source_response_sha256`, `source_selection_sha256`, `requested_reference_ids`, `inspection_constraints`. Mode yalnız `demo`; 1–8 farklı mevcut reference ID. Duplicate/bilinmeyen ID, kaynak digest uyuşmazlığı veya unknown alan reddedilir. Request dosya yolu, yeni candidate veya guard override taşımaz.

Kapsül `termivar-offline-guarded-reference-capsule/v1`, lookup `termivar-offline-reference-capsule-lookup/v1` sözleşmesidir. Mevcut `provided_limited_metadata`, `withheld_by_existing_guard` ve `unavailable_in_existing_scope` durumları korunur. Bloke/kapsam dışı referansta `projections=[]`; olumlu alt dosya hash/size başka bölüme kopyalanmaz. İzinli projection yalnız Phase32'nin mevcut 11 alanıdır. Null absence byte/hash bilinen sıfır değildir. Sayımlar reference/projection/candidate/unique-file paydalarıyla kapalı modelden yeniden türetilir.

## Sabit portatif biçim ve bağımlılıklar

Kapsül ZIP'inde tam `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt` bulunur. Ham Phase32 dosyaları kopyalanmaz. Inner manifest kendisini kapsamaz; diğer üç üyenin gerçek byte/SHA256 bağını taşır. Üye sırası ve ZIP metadata politikası kaynakta sabittir; gerçek tekrar-determinism kabulü yapılmadıkça başarılı sayılmaz.

Assembly korunmuş `security-platform/tools/commercial_reference_metadata` sahip validator/renderer ve mevcut yardımcılarına bağlıdır. Portatif inspector için yalnız yeni `inspect_capsule.py`, `capsule_contracts.py`, `capsule_manifest.py`, `capsule_renderer.py` modülleri ve Python standart kütüphanesi gerekir. Bu dört modül aynı yerel dizinde bulunmalıdır. Bu kaynaklar standalone binary/wheel değildir; production wheel'e veya startup'a eklenmez. Inspector Phase31/32 helper'larını, kaynak repo'yu, source bindings'teki eski dosyaları veya başka ZIP'i açmaz.

ZIP diske çıkarılmaz. Yalnız açık bundle path okunur; lookup yalnız açık capsule reference kayıtlarını kullanır. Dört beklenen üyeden farklı/duplicate/path traversal/symlink/encrypted/unsupported compression ZIP reddedilir. Sabit sınırlar: ZIP 256 KiB, üye 128 KiB, expanded toplam 256 KiB, ratio 20, reference 8, projection 64, depth 12, node 20.000, text 512 karakter. Strict UTF-8/JSON; duplicate/unknown key/version, float/NaN/Infinity ve bool-as-int reddi; truncation yoktur.

## Yalnız iki izinli ürün çağrısı

Aşağıdakiler planlanan exact root komutlarıdır; henüz çalışmış sonuç değildir. Phase33 bütçesi en fazla iki çağrı. İkinci yalnız ilk assembly exit 0, eksiksiz dört gerçek çıktı ve manuel incelemeden sonra çalışır. Başarısız çağrı tüketilir; retry, inspector hakkını tekrar assembly'ye çevirme veya üçüncü çağrı yoktur. Phase20–32 ve eski Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_reference_capsule/assemble_capsule.py --response outputs/phase32-reference-metadata/reference-metadata-response.json --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json --source-summary outputs/phase32-reference-metadata/metadata-summary.md --source-manifest outputs/phase32-reference-metadata/manifest.json --request security-platform/tools/commercial_reference_capsule/examples/demo_capsule_request.json --output-dir outputs/phase33-reference-capsule
```

```text
python -I -B security-platform/tools/commercial_reference_capsule/inspect_capsule.py --bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --lookup-reference rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81 --lookup-reference rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a --lookup-reference rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a --inspection-output outputs/phase33-reference-capsule/capsule-inspection.json --lookup-output outputs/phase33-reference-capsule/lookup-results.json
```

Output yeni ve boş dizin olmalı; overwrite veya otomatik silme yoktur. Assembly dört çıktı üretir: `guarded-reference-capsule.zip`, `capsule-source-bindings.json`, `capsule-assembly-summary.md`, `assembly-manifest.json`. Başarılı assembly sonrası inspector `capsule-inspection.json` ve `lookup-results.json` üretir. Kapsül içindeki dört üye ile dış output dizinindeki altı artefact farklı kapsamdır.

## Güven ve açık kabul kapıları

`demo_only=true`; Phase32'nin 17 false güven alanı ve yeni `upstream_guard_independently_verified=false` olmak üzere 18 false alan korunur. `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`. Upstream `fresh_*` kodları önceki kayıt kodlarıdır; açılış/lookup bugünkü filesystem durumu veya TTL garantisi üretmez.

İç byte/model bütünlüğü imza, producer/user authority, gerçek guard doğruluğu, compiler/module closure, ownership, insan/hukukî/müşteri/release kabulü değildir. Kapsül source path/root/physical identity/raw Rust/baseline/credential/exception/review notu içermez. ID/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir. Otomatik sender, ağ, kaynak lookup'u, tarama veya risk skoru yoktur.

NOT_RUN: hostile/duplicate JSON, invalid UTF-8, değiştirilmiş kaynak/sahte guard/unknown status/enjekte projection/yanlış ID, duplicate ZIP/ZIP bomb/ratio/symlink/traversal/bozuk manifest/limit, crash/partial write/power loss/repeat determinism, gerçek source freshness/upstream guard/compiler/module closure/ownership/producer attestation/native/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Koruma kodu bulunması bu saldırgan dalların kabul edildiği anlamına gelmez.

Belgeler: [sözleşme](../../docs/commercial/operations/phase33/CAPSULE_CONTRACT.tr.md), [disclosure sınırı](../../docs/commercial/operations/phase33/DISCLOSURE_BOUNDARY.tr.md), [portatif inceleme](../../docs/commercial/operations/phase33/PORTABLE_INSPECTION.tr.md), [teslim kaydı](../../docs/commercial/operations/phase33/DEMO_DELIVERY.tr.md).

Kaynak teslim ZIP'i `Termivar-Offline-Guarded-Reference-Capsule-phase33-2026-11-13.zip`, içte taşınan ürün kapsülü `guarded-reference-capsule.zip` ile farklı artefact'tır. Henüz ölçülmemiş kimlikler yazılmaz. Önceki Phase7–32, backend/operator-console/HBF/Altay/native/auth/DB/roller/wheel/lock/lisans değişmez. İzinli geliştirme, iki çağrı, dar inceleme ve ölçülmüş teslim bitince durulur; Phase34 veya yeni mikro özellik başlatılmaz.
