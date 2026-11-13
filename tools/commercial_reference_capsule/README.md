# Offline guarded reference capsule ve portable lookup

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

Bu bağımsız offline araç, Phase32'nin doğrulanmış ve küçültülmüş wire metadata'sını tam dört üyeli bir kapsül ZIP'ine taşır. Açık reference ID lookup'u yalnız kapsüldeki kayıtları kullanır. Kapsül özgün çalışma alanı veya Phase31/32 araçları olmadan iç bütünlük bakımından incelenebilir; kaynak dosyalar yeniden gözlenmez.

2026-11-13 tarihinde iki izinli ürün çağrısı gerçekten tamamlandı: assembly **exit 0**, inspector ve açık lookup **exit 0**. Bütçe **2/2 tüketildi ve kapandı; kalan 0**. Üç referans için gerçek sonuç 2 provided/1 whole-reference withheld, 3 projection ilişkisi, 2 kayıtlı present/1 absence. `authorization_review` için kapsülde ve lookup'ta `projections=[]`; olumlu alt dosya metadata'sı referans engelini aşmadı.

Ürün kapsülü `outputs/phase33-reference-capsule/guarded-reference-capsule.zip`, **23439 B / 4 üye**, SHA256 `19e61b261d63863f10b4147daf6dc5b2199faedcda41b03acb20322d30cb3388`. Bu kimlik kaynak teslim ZIP'ine ait değildir. Altı gerçek dış çıktı, dört gerçek iç üye ve üç lookup sonucu için [teslim kaydına](../../docs/commercial/operations/phase33/DEMO_DELIVERY.tr.md) bak. Üretim source commit'i `95d4762635dc0464701e93b79940bd9518ed00d2`, tree `482dfabe5f55c5187ad81ab0dcc0fd21510d0061`; üretim sonrası yalnız README ve teslim kaydı actual sonuçlara göre güncellendi.

## Giriş ve kapalı disclosure sınırı

Assembly yalnız açık request ve dört Phase32 dosyası okur: response, selection, summary, manifest. Sıra: strict parse → gerçek `consumer_contracts.validate_documents(response, selection)` → gerçek `output_renderer.render_summary` byte eşliği → gerçek üç payload için `artifact_manifest.manifest_data` byte/SHA256 eşliği. Eski builder/CLI veya Phase31 guard yeniden çalıştırılmaz.

Request `termivar-offline-guarded-reference-capsule-request/v1` tam yedi alan taşır: `schema_version`, `mode`, `capsule_reference`, `source_response_sha256`, `source_selection_sha256`, `requested_reference_ids`, `inspection_constraints`. Mode yalnız `demo`; 1–8 farklı mevcut reference ID. Duplicate/bilinmeyen ID, kaynak digest uyuşmazlığı veya unknown alan reddedilir. Request dosya yolu, yeni candidate veya guard override taşımaz.

Kapsül `termivar-offline-guarded-reference-capsule/v1`, lookup `termivar-offline-reference-capsule-lookup/v1` sözleşmesidir. Mevcut `provided_limited_metadata`, `withheld_by_existing_guard` ve `unavailable_in_existing_scope` durumları korunur. Bloke/kapsam dışı referansta `projections=[]`; olumlu alt dosya hash/size başka bölüme kopyalanmaz. İzinli projection yalnız Phase32'nin mevcut 11 alanıdır. Null absence byte/hash bilinen sıfır değildir. Sayımlar reference/projection/candidate/unique-file paydalarıyla kapalı modelden yeniden türetilir.

## Sabit portatif biçim ve bağımlılıklar

Kapsül ZIP'inde tam `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt` bulunur. Ham Phase32 dosyaları kopyalanmaz. Inner manifest kendisini kapsamaz; diğer üç üyenin gerçek byte/SHA256 bağını taşır. Üye sırası ve ZIP metadata politikası kaynakta sabittir; gerçek tekrar-determinism kabulü yapılmadıkça başarılı sayılmaz.

Assembly korunmuş `security-platform/tools/commercial_reference_metadata` sahip validator/renderer ve mevcut yardımcılarına bağlıdır. Portatif inspector için yalnız yeni `inspect_capsule.py`, `capsule_contracts.py`, `capsule_manifest.py`, `capsule_renderer.py` modülleri ve Python standart kütüphanesi gerekir. Bu dört modül aynı yerel dizinde bulunmalıdır. Bu kaynaklar standalone binary/wheel değildir; production wheel'e veya startup'a eklenmez. Inspector Phase31/32 helper'larını, source bindings'teki eski dosyaları veya başka ZIP'i açmaz. Gerçek ikinci çağrı mevcut çalışma alanında çalıştı ve özgün Phase31/32 dosyalarını okumadığını raporladı; dört modülün ikinci bir offline host'a kopyalanarak kaynak yokluğunda çalıştırılması kabulü **NOT_RUN**. Bağımsız import grafiğinin kaynak incelemesi bu ek runtime kabulünün yerine geçmez.

ZIP diske çıkarılmaz. Yalnız açık bundle path okunur; lookup yalnız açık capsule reference kayıtlarını kullanır. Dört beklenen üyeden farklı/duplicate/path traversal/symlink/encrypted/unsupported compression ZIP reddedilir. Sabit sınırlar: ZIP 256 KiB, üye 128 KiB, expanded toplam 256 KiB, ratio 20, reference 8, projection 64, depth 12, node 20.000, text 512 karakter. Strict UTF-8/JSON; duplicate/unknown key/version, float/NaN/Infinity ve bool-as-int reddi; truncation yoktur.

## Tamamlanan exact iki ürün çağrısı

Aşağıdakiler gerçekten tamamlanmış root çağrılarının tarihsel kaydıdır; yeniden çalıştırma izni değildir. İkinci, ilk assembly exit 0, eksiksiz dört gerçek çıktı ve kapsülün dört iç üyesinin manuel incelemesinden sonra çalıştı. Actual exit kodları **[0,0]**, **2/2 bütçe kapalı, kalan 0**. Retry, inspector hakkını tekrar assembly'ye çevirme veya üçüncü çağrı yoktur. Phase20–32 ve eski Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_reference_capsule/assemble_capsule.py --response outputs/phase32-reference-metadata/reference-metadata-response.json --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json --source-summary outputs/phase32-reference-metadata/metadata-summary.md --source-manifest outputs/phase32-reference-metadata/manifest.json --request security-platform/tools/commercial_reference_capsule/examples/demo_capsule_request.json --output-dir outputs/phase33-reference-capsule
```

```text
python -I -B security-platform/tools/commercial_reference_capsule/inspect_capsule.py --bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --lookup-reference rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81 --lookup-reference rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a --lookup-reference rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a --inspection-output outputs/phase33-reference-capsule/capsule-inspection.json --lookup-output outputs/phase33-reference-capsule/lookup-results.json
```

Gerçek output dizini `outputs/phase33-reference-capsule/`. Assembly `guarded-reference-capsule.zip`, `capsule-source-bindings.json`, `capsule-assembly-summary.md`, `assembly-manifest.json` üretti. Başarılı assembly ve manuel inceleme sonrası inspector `capsule-inspection.json` ve `lookup-results.json` üretti. Kapsül içindeki dört üye ile dış output dizinindeki altı artefact farklı kapsamdır. Yeni/boş dizin koşulu korunur; overwrite veya otomatik silme yoktur.

Inspector `internal_content_status=content_consistent` bildirdi: yalnız dört iç üyenin kapalı model/byte/hash/summary/README bağları. Lookup `explicit_capsule_records_only` kapsamıyla üç capsule sonucunu aynen korudu. İç manifest kendi digest'ini kapsamaz; dış assembly manifesti ilk üç dış payload'ı bağlar ve kendisini/inspection/lookup'u kapsamaz. Bunlar Phase31 guard veya özgün kaynak byte'larının bağımsız doğrulanması değildir.

## Güven ve açık kabul kapıları

`demo_only=true`; Phase32'nin 17 false güven alanı ve yeni `upstream_guard_independently_verified=false` olmak üzere 18 false alan korunur. `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`. Upstream `fresh_*` kodları önceki kayıt kodlarıdır; açılış/lookup bugünkü filesystem durumu veya TTL garantisi üretmez.

İç byte/model bütünlüğü imza, producer/user authority, gerçek guard doğruluğu, compiler/module closure, ownership, insan/hukukî/müşteri/release kabulü değildir. Kapsül source path/root/physical identity/raw Rust/baseline/credential/exception/review notu içermez. ID/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir. Otomatik sender, ağ, kaynak lookup'u, tarama veya risk skoru yoktur.

NOT_RUN: hostile/duplicate JSON, invalid UTF-8, değiştirilmiş kaynak/sahte guard/unknown status/enjekte projection/yanlış ID, duplicate ZIP/ZIP bomb/ratio/symlink/traversal/bozuk manifest/limit, crash/partial write/power loss/repeat determinism, ikinci offline host'a taşınmış dört modülle kaynak yokluğu runtime kabulü, gerçek source freshness/upstream guard/compiler/module closure/ownership/producer attestation/native/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Koruma kodu bulunması bu saldırgan dalların kabul edildiği anlamına gelmez.

Belgeler: [sözleşme](../../docs/commercial/operations/phase33/CAPSULE_CONTRACT.tr.md), [disclosure sınırı](../../docs/commercial/operations/phase33/DISCLOSURE_BOUNDARY.tr.md), [portatif inceleme](../../docs/commercial/operations/phase33/PORTABLE_INSPECTION.tr.md), [teslim kaydı](../../docs/commercial/operations/phase33/DEMO_DELIVERY.tr.md).

Kaynak teslim ZIP'i `Termivar-Offline-Guarded-Reference-Capsule-phase33-2026-11-13.zip`, içte taşınan ürün kapsülü `guarded-reference-capsule.zip` ile farklı artefact'tır. Son kaynak ZIP boyutu/üye sayısı/SHA256 root paketlemesinde ayrıca ölçülüp dış delivery manifestine yazılır; öz hash döngüsü oluşturulmaz ve burada ölçülmemiş değer uydurulmaz. Önceki Phase7–32, backend/operator-console/HBF/Altay/native/auth/DB/roller/wheel/lock/lisans korunur. İzinli iki ürün çağrısı tamamlandı; ölçülmüş teslim kapanınca Phase34 veya yeni mikro özellik başlatılmaz.
