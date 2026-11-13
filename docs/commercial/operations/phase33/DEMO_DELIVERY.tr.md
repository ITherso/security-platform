# Phase33 gerçek kapsül ve lookup teslim kaydı

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

2026-11-13 tarihinde iki izinli Phase33 ürün çağrısı tamamlandı: assembly **exit 0**, bağımsız kapsül inspector ve açık lookup **exit 0**. İkinci çağrı, başarılı assembly'nin eksiksiz dört gerçek çıktısı ve kapsülün dört iç üyesi manuel incelendikten sonra çalıştı. Bütçe **2/2 tüketildi ve kapandı; kalan çağrı 0**. Otomatik retry veya üçüncü ürün çağrısı yoktur. Phase20–32 bütçeleri ve Phase24/29 insan istisnaları kapalıdır.

Başlangıç Phase32 HEAD `19c0c13b2537f7f0bb1396e7cf7fac399d572c42`, tree `69b424b823d193f2ca08b17b51811eab8c884df6`; Phase33 baseline 341 artefact, 313 kaynak, 21 runtime asset ve mevcut 60030 B wheel'i korur. Üretim source commit'i `95d4762635dc0464701e93b79940bd9518ed00d2`, tree `482dfabe5f55c5187ad81ab0dcc0fd21510d0061`. Üretim sonrası yalnız README ve bu belge actual sonuçlara göre güncellendi; ürün kodu değişmedi. Yeni kaynak teslim ZIP'i önceki arşivleri/native/wheel/cache/DB veya özel çalışma dosyalarını kopyalamaz.

## Gerçek eski girdi kimlikleri

Assembly kaynağı `outputs/phase32-reference-metadata/` altında dört açık artefact'tır. Kimlikler gerçek byte'lardan doğrulandı. Bu dört kaynak ve request dışında eski baseline/Rust/entry-point veya Phase31 kaynak gözlemi yeniden okunmadı.

| Rol | Dosya | Bayt | SHA256 |
| --- | --- | ---: | --- |
| Response | `reference-metadata-response.json` | 7069 | `98d1a5409ccc12a4f504d209844b9f95b89b4452e278ba953add2aff508e89c5` |
| Selection | `metadata-selection-ledger.json` | 4382 | `2bef037c617ab120cb925eaffa1ef5bde8100b69204b98603a528ee77c4cf5e4` |
| Summary | `metadata-summary.md` | 10989 | `7782401c5ea1e298a27893394fdb0f9e52cb475d054838d7a469fc426702339b` |
| Manifest | `manifest.json` | 3290 | `7309d00d1c4ba5ad5866f73c66118c1e86060ec96da6d6ae2d526b616f185204` |

Assembly sırası strict parse → Phase32 `validate_documents` → gerçek kaynak summary byte eşliği → gerçek üç payload manifest byte/SHA256 eşliğidir. Eski builder, Phase31 guard, native kaynak veya başka ZIP çalıştırılmaz/açılmaz.

## İstenen demo referansları

| Kaynak etiketi | Gerçek reference ID | Kapsülde ve lookup'ta korunan durum | Gerçek projection |
| --- | --- | --- | ---: |
| outcome | `rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81` | `provided_limited_metadata` | 2 |
| authorization_review | `rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a` | `withheld_by_existing_guard` | 0 |
| report_compare | `rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a` | `provided_limited_metadata` | 1 |

Gerçek capsule ve lookup sayımları **3 reference = 2 provided + 1 whole-reference withheld + 0 unavailable**; **3 projection ilişkisi, 3 benzersiz candidate ve 3 benzersiz file**, **2 kayıtlı present + 1 absence**. Sayımlar gerçek doğrulanmış kaynak modellerinden türetildi; koda başarılı fixture olarak sabitlenmedi. `authorization_review` için kapsülde ve lookup'ta `projections=[]`; mevcut referans engeli olumlu CAND0003 alt metadata'sını da dışarı vermedi. Bloke hash/size/path başka bölüme taşınmadı. Diğer 92 referans kapsüle eklenmedi veya taranmış gibi sunulmadı. Absence byte/hash alanları `null`; bilinen sıfır-byte dosya değildir.

## Gerçek tamamlanan exact iki çağrı

Aşağıdakiler gerçek generation kaydındaki tamamlanmış iki komuttur; tekrar çalıştırma izni değildir. Birinci çağrı başarılı ve eksiksiz dört çıktı üretti; gerçek kapsül üyeleri manuel incelendi; sonra ikinci çağrı çalıştı. Actual exit kodları **[0,0]**, kalan çağrı **0**. Başarısız çağrı tüketilir; otomatik retry veya üçüncü çağrı yoktur.

```text
python -I -B security-platform/tools/commercial_reference_capsule/assemble_capsule.py --response outputs/phase32-reference-metadata/reference-metadata-response.json --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json --source-summary outputs/phase32-reference-metadata/metadata-summary.md --source-manifest outputs/phase32-reference-metadata/manifest.json --request security-platform/tools/commercial_reference_capsule/examples/demo_capsule_request.json --output-dir outputs/phase33-reference-capsule
```

```text
python -I -B security-platform/tools/commercial_reference_capsule/inspect_capsule.py --bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --lookup-reference rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81 --lookup-reference rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a --lookup-reference rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a --inspection-output outputs/phase33-reference-capsule/capsule-inspection.json --lookup-output outputs/phase33-reference-capsule/lookup-results.json
```

Assembly exit **0**, dört gerçek dış çıktı üretti. Inspector/lookup exit **0**, `internal_content_status=content_consistent`, `lookup_scope=explicit_capsule_records_only`. Inspection yalnız `four_capsule_members_and_internal_model_byte_correspondence_only` kapsamındadır. Bu sonuç özgün Phase31/32 artefact byte'ları, gerçek guard veya bugünkü kaynak dosyalarının bağımsız doğruluğu değildir.

## Altı gerçek dış çıktı

Konum `outputs/phase33-reference-capsule/`. Boyut ve SHA256 değerleri gerçek disk byte'larından ölçüldü.

| Dosya | Bayt | SHA256 |
| --- | ---: | --- |
| `guarded-reference-capsule.zip` | 23439 | `19e61b261d63863f10b4147daf6dc5b2199faedcda41b03acb20322d30cb3388` |
| `capsule-source-bindings.json` | 1908 | `98545bd77122731c54716940bb15e35579cf2b5f7fbccca8ccd80f88c3501e04` |
| `capsule-assembly-summary.md` | 11461 | `f976a1c1dde28110a0ecce22d958c5e56105550878440eb16faf0891888f5333` |
| `assembly-manifest.json` | 2840 | `d8fb9678e3a36688a1b2e0c02491299b330699aea417814707860fbe5c2a4b16` |
| `capsule-inspection.json` | 3922 | `ed21257290eff3c33bea23a9f78baa90ac6e85b0fdda438316aad55534d109e4` |
| `lookup-results.json` | 7470 | `9c3d1a4c6c79d2103e6b51f48a93f1b2e0ac66146af32043e32efb2eb690bf34` |

Source bindings snapshot kimliği `phase32-artifact-snapshot-de84cc349bbc3760371ee9d4a48497a67d708c0996eff5457abfc1d8a256ef78`; yalnız dört kayıtlı Phase32 artefact'ın sözleşme/byte/SHA256 bağını taşır. Ham Phase32 metadata tekrarlanmaz. Dış assembly manifesti ilk üç gerçek payload'ın byte/hash bağını taşır; kendisini, inspection ve lookup dosyalarını kapsamaz.

## Kapsülün dört gerçek iç üyesi

Ürün kapsülü **23439 B / tam 4 üye**. ZIP extraction yapılmadan okunmuştur. Üye sırası aşağıdaki gibidir; gerçek ZIP metadata'sı her üyede `ZIP_STORED`, zaman `1980-01-01 00:00:00`, Unix regular-file metadata politikasıdır. Expanded toplam **22969 B**. Bu bir kez gözlenen çıktıdır; tekrar-determinism kabulü NOT_RUN kalır.

| İç üye | Bayt | SHA256 |
| --- | ---: | --- |
| `reference-capsule.json` | 7720 | `2fab02d00f1c7f61b4769c70aaf8525641530f5f2d385e65e7bf5963dc94c20d` |
| `reference-summary.md` | 11105 | `f045ff2450bb6f476edd60c0e972b72947525269c3bddc20e854d0c53382bf12` |
| `bundle-manifest.json` | 2798 | `8d03ef70ce9d0f8b898a1c0d9edb2b6bd0b64b3eaa2cdfb835e46515aa45565c` |
| `README.txt` | 1346 | `289fee84ca443fd6510d6d3ae405dc2623d21fb8af981a430cd9983d7025ced3` |

Inner manifest kapsül JSON, summary ve sabit README'nin gerçek byte/SHA256 bağını taşır; kendi hash'ini içermez. Summary yalnız kapalı capsule modelinden türetildi. README exact sabit güven banner'ını içerir. Bloke referansın olumlu projection'ı dört iç üyeye veya lookup'a kopyalanmadı; source path/baseline/raw source alanları taşınmadı.

## Gerçek lookup ve manuel gözlemler

Üç açık `--lookup-reference` sonucu kapsüldeki üç referans sonucuyla eşleşti. `outcome` CAND0001 kayıtlı present ve CAND0002 kayıtlı absence için iki projection; `report_compare` CAND0005 için bir kayıtlı present projection aldı. `authorization_review` mevcut `withheld_by_existing_guard` durumuyla sıfır projection döndürdü. Lookup yalnız kapsül kayıtlarını kullandı; source path, internet veya başka ZIP açmadı.

Manuel incelemede dört iç üye, whole-reference withholding, null absence, 18 false bayrak ve iki manifestin farklı kapsamları gözlendi. Bunlar actual metadata/metin ve byte/hash gözlemleridir; saldırgan girdi kabulü veya genel güvenlik testi değildir.

## İnceleme sınırı ve kapanış

Kapsül ZIP'i `guarded-reference-capsule.zip`; kaynak teslim ZIP'i `Termivar-Offline-Guarded-Reference-Capsule-phase33-2026-11-13.zip`. Bunlar farklı artefact'lardır. Yukarıdaki 23439 B / dört üye / SHA256 yalnız ürün kapsülüne aittir. Son kaynak teslim ZIP'i root paketlemesinde ayrıca ölçülür; boyut/üye sayısı/SHA256, source/delivery manifest ve closure kaydında tutulur. Bu belgede henüz ölçülmemiş kaynak ZIP kimliği uydurulmaz. Source manifest kendi digest'ini kapsamaz; son kaynak ZIP kimliği dış delivery manifestinde tutularak öz hash döngüsü oluşturulmaz.

Gerçek inspector yalnız kapsül ZIP'ini extraction olmadan okudu. `original_phase31_files_read=false`, `original_phase32_files_read=false`, `old_guard_reexecuted=false`, `old_source_archive_read=false`, `native_candidate_files_read=false`, `source_artifact_bytes_independently_verified=false`, `source_producer_verified=false` raporladı. İç byte/model eşliği özgün guard veya üretici doğrulaması değildir. `demo_only=true`; 18 güven alanı false, `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`. Kayıtlı upstream `fresh_*` kodları yeni observation veya TTL garantisi değildir.

İkinci çağrı mevcut çalışma alanında çalıştı. Inspector'ın yalnız dört yeni yerel modül ve standart kütüphane kullanan import grafiği kaynak üzerinden incelendi; dört modülün ikinci bir offline host'a kopyalanıp özgün kaynaklar yokken çalıştırılması kabulü **NOT_RUN**. Mevcut çalışmada özgün Phase31/32 dosyalarını okumaması, bu ayrı taşınmış-host runtime kabulü yerine geçmez.

NOT_RUN: hostile/duplicate JSON, invalid UTF-8, değiştirilmiş kaynak dosyaları, sahte guard/unknown status/injected projection/yanlış ID, duplicate ZIP/ZIP bomb/ratio/symlink/traversal/bozuk manifest/limit, crash/partial write/power loss/repeat determinism, ikinci offline host'a dört modülle taşınmış kaynak-yokluğu runtime kabulü, gerçek source freshness, Phase31 guard'ın bağımsız doğruluğu, compiler/module closure, component ownership, producer/Git attestation, native runtime, insan/hukukî/müşteri/release kabulü. Test/runner/coverage/typecheck/build/install ve Phase19 manuel UI kabulü beklemede kalır. Koruma kodu saldırgan girdi kabulü değildir.

İzinli iki ürün çağrısı ve dar gerçek çıktı incelemesi tamamlandı. Önceki kaynak koruması ve ölçülmüş kaynak teslimi kapandığında durulur. Yeni mikro özellik, Phase34, test/build/native çalışma, otomatik gönderim veya public release başlatılmaz.
