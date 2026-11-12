# Phase32 gerçek teslim kaydı

**DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION**

2026-11-12 tarihinde iki izinli ürün çağrısı tamamlandı: assembly **exit 0**, inspector **exit 0**. İkinci çağrı, ilk çağrının eksiksiz dört gerçek çıktısının manuel incelemesinden sonra çalıştı. Bütçe **2/2 tüketildi ve kapandı; kalan çağrı 0**. Otomatik retry, inspector hakkını assembly tekrarına dönüştürme veya üçüncü ürün çağrısı yoktur. Phase20–31 bütçeleri ve eski Phase24/29 insan istisnaları da kapalıdır.

Üretim source commit'i `66a644175a23df913b1303fbdec20c5303b6a52d`, tree `be5f2f9ea9af73470fc0e6650263066d4d547b0d`. Üretim snapshot'ından sonra yalnız README ve bu teslim belgesi actual sonuçlara göre güncellendi. Ürün kodu, eski artefact grupları ve native runtime bu belge değişikliğiyle güncellenmez.

## Gerçek istek ve referans sonuçları

Yerel request `DEMO-TERMIVAR-REFERENCE-METADATA-032`, yalnız mevcut üç external reference'ı ister. Kimlikler doğrulanmış Phase31 bağlamından alınmıştır; isimden üretilmemiştir. Request ledger/reuse beklentileri gerçek byte kimliklerine bağlanmıştır.

| Bağlam etiketi | Tam reference ID | Mevcut karar | Tüketici sonucu | Projection |
|---|---|---|---|---:|
| outcome | `rust-ref-dfd6b59f25de8346b72d86fedce91afe4e9ace4f55fac7986019ede3b1ecef81` | `candidate_observations_reobserved` | `provided_limited_metadata` | 2 |
| authorization_review | `rust-ref-555f207606bbd8a43d836efed36f64587866e090fa212c2cadefb898c8c4ce1a` | `candidate_reuse_blocked` | `withheld_by_existing_guard` | 0 |
| report_compare | `rust-ref-6bc3209001edb569d2477705369c3609f5befa7a0963dc53883935c1452d6c4a` | `candidate_observations_reobserved` | `provided_limited_metadata` | 1 |

Gerçek sayımlar: **3 istenen reference → 2 provided + 1 withheld + 0 unavailable**. **3 projection ilişkisi, 3 benzersiz candidate ve 3 file kimliği** sunuldu: **2 kayıtlı present + 1 kayıtlı absence**. `outcome` CAND0001 byte metadata'sı ve CAND0002 yokluk metadata'sı; `report_compare` CAND0005 byte metadata'sı aldı. Absence byte/hash alanları `null`; bilinen sıfır byte değildir.

`authorization_review` için `projections=[]`. CAND0004 nedeniyle mevcut referans engeli, olumlu CAND0003 alt dosya kaydını da dışarı vermedi. Bloke referansa ait olumlu hash/size veya kaynak path'i response, selection, Markdown veya başka bir tüketici alanına taşınmadı. Bu gerçek örnek filtreleme gözlemidir; bütün negatif dalların kabulü değildir. Request dışı reference ID'leri yeni çıktıya kopyalanmadı; bunlar taranmış veya güncel gözlenmiş gibi sunulmadı.

Kaynak metadata snapshot kimliği `phase31-metadata-snapshot-083e011b342f86f8007d92c8601394793fcb5d6893c9def579e280a8557b8d22`. Bu kimlik dört artefact byte bağıdır; producer attestation, credential veya yeni source gözlemi değildir.

## Açık upstream byte bağları

Assembly yalnız request ve dört açık Phase31 dosyasını okudu. İki JSON owning strict parser/validator'dan, Markdown owning renderer byte eşliğinden, manifest gerçek üç payload eşliğinden geçti. Tam baseline bu giriş doğrulamasında korunur; yalnız yeni tüketici çıktısına geçerken küçültülür. Immutable snapshot'ın tekrar doğrulanması yeni kaynak okuması değildir.

| Phase31 rolü | Bayt | SHA256 |
|---|---:|---|
| Ledger | 250674 | `d2076a23f56ba19181cd792ce762b65aaae54e4dc83ac412a7e0cec5e382db76` |
| Reuse | 194223 | `6cd38b27d8734897a236f92986d382da0e37746a9b321a4534d56f768fc5350d` |
| Summary | 35690 | `7082ac96cdceeb046a767dcd4831a95324bff86448681279755b6ada382e5f76` |
| Manifest | 5623 | `4515bbfbe603f05bf09e48dcf4ed95ccc8d872ab7c11535a0429b92e6d79f57a` |

Kaynak ZIP'i, native/candidate/Rust/entry-point/Phase24 dosyaları veya eski CLI açılmadı. Yeni native kaynak dosyası hash'i, path keşfi, fiziksel kimlik veya reference-context değerlendirmesi yapılmadı.

## Çalışmış iki tarihsel komut

Bu komutlar tamamlanmış çağrıların kaydıdır; tekrar çalıştırma izni değildir.

```text
python -I -B security-platform/tools/commercial_reference_metadata/assemble_metadata.py --ledger outputs/phase31-candidate-revalidation/revalidation-ledger.json --reuse outputs/phase31-candidate-revalidation/evidence-reuse.json --source-summary outputs/phase31-candidate-revalidation/revalidation-summary.md --source-manifest outputs/phase31-candidate-revalidation/manifest.json --request security-platform/tools/commercial_reference_metadata/examples/demo_metadata_request.json --output-dir outputs/phase32-reference-metadata
```

Assembly exit **0**; üç payload ve en son manifest üretildi. Dört gerçek dosyada minimizasyon ve byte/hash bağları manuel incelendi.

```text
python -I -B security-platform/tools/commercial_reference_metadata/inspect_metadata.py --response outputs/phase32-reference-metadata/reference-metadata-response.json --selection outputs/phase32-reference-metadata/metadata-selection-ledger.json --summary outputs/phase32-reference-metadata/metadata-summary.md --manifest outputs/phase32-reference-metadata/manifest.json --output outputs/phase32-reference-metadata/inspection-summary.json
```

Inspector exit **0**, `internal_content_status=content_consistent`. Yalnız dört yeni açık dosyada iki modelin/selection'ın karşılığını, sayımları, yeniden türetilen Markdown'ı ve üç payload byte/hash bağını inceledi. Manifest kendisini ve inspection çıktısını kapsamaz.

## Beş gerçek çıktı kimliği

Konum `outputs/phase32-reference-metadata/`. Boyut ve SHA256 değerleri disk üzerindeki gerçek dosyalardan ölçüldü.

| Dosya | Bayt | SHA256 |
|---|---:|---|
| `reference-metadata-response.json` | 7069 | `98d1a5409ccc12a4f504d209844b9f95b89b4452e278ba953add2aff508e89c5` |
| `metadata-selection-ledger.json` | 4382 | `2bef037c617ab120cb925eaffa1ef5bde8100b69204b98603a528ee77c4cf5e4` |
| `metadata-summary.md` | 10989 | `7782401c5ea1e298a27893394fdb0f9e52cb475d054838d7a469fc426702339b` |
| `manifest.json` | 3290 | `7309d00d1c4ba5ad5866f73c66118c1e86060ec96da6d6ae2d526b616f185204` |
| `inspection-summary.json` | 3682 | `846a34df129c1c05ee63b0a7b5de7686b917e5f863afa16d98a21740f22b207e` |

Selection metadata projection'larını yeniden kopyalamaz. Response/selection/Markdown tam historical baseline, root/pin, physical identity, ham source veya source path içermez; yalnız istenen referanslar ve yayımlanabilir dar metadata gösterilir. Minimizasyon anonimlik veya şifreleme değildir.

## Manuel gözlem ve açık kabul kapıları

Manuel incelemede üç reference sonucu, blocked referansın boş projection listesi, olumlu alt dosya hash'inin yeni çıktılarda bulunmaması, source path/baseline alanlarının taşınmaması, null absence ve üç payload manifest bağı gözlendi. Bu metadata/metin incelemesidir; otomatik test, genel güvenlik veya native kabulü değildir.

`reference_context_revalidated=false`, `independent_observation_verified=false`, `source_files_reobserved=false` dahil **17 güven alanı false**, `demo_only=true`. Upstream `fresh_*` kodları yalnız kayıtlı Phase31 kararıdır; şimdi yeni gözlem veya bugünkü dosya durumu değildir. Envanter/delta, ownership/module closure, producer/human, build/runtime, hukukî/release kabulü kazanılmaz; TTL veya canlı tazelik garantisi yoktur.

Inspector `original_phase31_files_read=false`, `old_baseline_read=false`, `candidate_files_read=false`, `source_archive_read=false`, `old_guard_reexecuted=false`, `upstream_guard_independently_verified=false` raporladı. `content_consistent` yalnız yeni artefact iç tutarlılığıdır; upstream guard doğruluğu, bağımsız source gözlemi veya devam eden tazelik kanıtı değildir.

**NOT_RUN:** hostile JSON/UTF-8; duplicate/yanlış reference veya request digest uyuşmazlığı; bozuk upstream, bilinmeyen guard durumu, projection eksikliği/çelişkisi; `candidate_change_observed`/kapsam dışı response dalları; limit/path/link/race/crash; farklı shared-file düzenleri, tekrarlı determinism ve gerçek source değişimi; native/compiler/Rust resolution/module closure/ownership/producer/uzman/hukukî/release kabulü. Test/runner/coverage/typecheck/build veya browser çalışması yoktur. Mevcut örneğin referans engeli bu negatif senaryoların kabulü olarak sunulmaz.

Paket adı `Termivar-Offline-Guarded-Reference-Metadata-phase32-2026-11-12.zip`. Son ZIP boyutu/üye sayısı/SHA256 ve source/delivery/closure kayıtları root paketlemesinde ayrıca ölçülür; bu belge henüz ölçülmemiş ZIP kimliği iddia etmez. ZIP'in kimliği ayrı dış teslim manifestinde tutulur; öz hash döngüsü için bu belgeye gömülmez. Yeni kaynak paketi korunmuş kardeş owning araçlara ve dört ayrı Phase31 girdisine bağlıdır; eski artefact grupları/native/wheel kopyalanmaz.

İzinli kaynak geliştirmesi ve iki çağrı tamamlandı. Yeni faz/feature, kaynak mutasyonu, eski CLI/native/ağ çalışması veya başka ürün çağrısı başlatılmaz.
