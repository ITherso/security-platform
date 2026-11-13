# Phase33 teslim kaydı — gerçek üretim bekliyor

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

Bu belge kaynak hazırlığı kaydıdır. Phase33 ürün çağrısı henüz **0**. Gerçek kapsül, inspection veya lookup başarısı; yeni dosya/ZIP boyutu ya da SHA256 burada iddia edilmez. Mevcut Phase32 kaynak sonuçları yeni ürün çıktısının yerine geçirilmez.

Başlangıç Phase32 HEAD `19c0c13b2537f7f0bb1396e7cf7fac399d572c42`, tree `69b424b823d193f2ca08b17b51811eab8c884df6`; Phase33 baseline 341 artefact, 313 kaynak, 21 runtime asset ve mevcut 60030 B wheel'i korur. Yeni kaynak teslim ZIP'i önceki arşivleri/native/wheel/cache/DB veya özel çalışma dosyalarını kopyalamaz.

## Gerçek eski girdi kimlikleri

Kaynak `outputs/phase32-reference-metadata/` altında dört açık artefact'tır. Kimlikler mevcut disk metadata'sıdır; bu tabloda yeni Phase33 üretim iddiası yoktur.

| Rol | Dosya | Bayt | SHA256 |
| --- | --- | ---: | --- |
| Response | `reference-metadata-response.json` | 7069 | `98d1a5409ccc12a4f504d209844b9f95b89b4452e278ba953add2aff508e89c5` |
| Selection | `metadata-selection-ledger.json` | 4382 | `2bef037c617ab120cb925eaffa1ef5bde8100b69204b98603a528ee77c4cf5e4` |
| Summary | `metadata-summary.md` | 10989 | `7782401c5ea1e298a27893394fdb0f9e52cb475d054838d7a469fc426702339b` |
| Manifest | `manifest.json` | 3290 | `7309d00d1c4ba5ad5866f73c66118c1e86060ec96da6d6ae2d526b616f185204` |

Assembly sırası strict parse → Phase32 `validate_documents` → gerçek kaynak summary byte eşliği → gerçek üç payload manifest byte/SHA256 eşliğidir. Eski builder, Phase31 guard, native kaynak veya başka ZIP çalıştırılmaz/açılmaz.

## İstenen demo referansları

| Kaynak etiketi | Gerçek reference ID | Kaynakta kayıtlı durum | Kaynak projection |
| --- | --- | --- | ---: |
| outcome | `rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81` | `provided_limited_metadata` | 2 |
| authorization_review | `rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a` | `withheld_by_existing_guard` | 0 |
| report_compare | `rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a` | `provided_limited_metadata` | 1 |

Yeni demo bu gerçek kaynaklardan yeniden türetilmelidir: beklenen 3 reference, 2 provided/1 withheld, 3 projection ilişkisi, 2 kayıtlı present/1 absence. Sayımlar koda başarılı fixture olarak sabitlenmez. `authorization_review` referans engeli, olumlu CAND0003 alt metadata'sını da kapsülün dört üyesinden ve lookup'tan çıkarır. Diğer 92 referans kapsüle eklenmez veya taranmış gibi sunulmaz.

## İzinli exact iki çağrı

Aşağıdakiler henüz çalıştırılmamış planlanan komutlardır. Birinci çağrı başarılı ve eksiksiz dört çıktı üretirse gerçek kapsül üyeleri manuel incelenir; ancak sonra ikinci çağrı çalışır. Başarısız çağrı tüketilir. En fazla iki yeni ürün çağrısı; otomatik retry veya üçüncü çağrı yoktur. Phase20–32 bütçeleri ve Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_reference_capsule/assemble_capsule.py --response outputs/phase32-reference-metadata/reference-metadata-response.json --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json --source-summary outputs/phase32-reference-metadata/metadata-summary.md --source-manifest outputs/phase32-reference-metadata/manifest.json --request security-platform/tools/commercial_reference_capsule/examples/demo_capsule_request.json --output-dir outputs/phase33-reference-capsule
```

```text
python -I -B security-platform/tools/commercial_reference_capsule/inspect_capsule.py --bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --lookup-reference rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81 --lookup-reference rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a --lookup-reference rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a --inspection-output outputs/phase33-reference-capsule/capsule-inspection.json --lookup-output outputs/phase33-reference-capsule/lookup-results.json
```

Gerçek üretim sonrası altı yeni dosya, kapsülün tam dört iç üyesi, byte/SHA256 bağları, üç gerçek lookup sonucu ve iki actual exit code kaydedilecektir. Üretim kaynak snapshot'ı ile yalnız README ve bu teslim belgesindeki actual-result güncellemesi ayrılır.

## İnceleme sınırı ve kapanış

Kapsül ZIP'i `guarded-reference-capsule.zip`; kaynak teslim ZIP'i `Termivar-Offline-Guarded-Reference-Capsule-phase33-2026-11-13.zip`. Bunlar farklı artefact'lardır. Henüz ölçülmemiş kimlikleri yazılmaz. Kapsül kendi üç payload'ını iç manifestle bağlar; son kaynak ZIP kimliği ayrı dış delivery manifestinde tutulur. Source manifest kendi digest'ini kapsamaz; öz hash döngüsü oluşturulmaz.

Portatif inspector yalnız kapsül ZIP'ini extraction olmadan okuyacak; Phase31/32, eski baseline, kaynak workspace veya native source açmayacak. İç byte/model eşliği özgün guard veya üretici doğrulaması değildir. `demo_only=true`; 18 güven alanı false, `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`. Kayıtlı upstream `fresh_*` kodları yeni observation veya TTL garantisi değildir.

NOT_RUN: hostile/duplicate JSON, invalid UTF-8, değiştirilmiş kaynak dosyaları, sahte guard/unknown status/injected projection/yanlış ID, duplicate ZIP/ZIP bomb/ratio/symlink/traversal/bozuk manifest/limit, crash/partial write/power loss/repeat determinism, gerçek source freshness, Phase31 guard'ın bağımsız doğruluğu, compiler/module closure, component ownership, producer/Git attestation, native runtime, insan/hukukî/müşteri/release kabulü. Test/runner/coverage/typecheck/build/install ve Phase19 manuel UI kabulü beklemede kalır. Koruma kodu saldırgan girdi kabulü değildir.

İzinli iki ürün çağrısı, dar gerçek çıktı incelemesi, önceki kaynak koruması ve ölçülmüş teslim tamamlandığında durulur. Yeni mikro özellik, Phase34, test/build/native çalışma, otomatik gönderim veya public release başlatılmaz.
