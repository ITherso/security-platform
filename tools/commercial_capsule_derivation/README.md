# Offline capsule derivation ve monotonic disclosure

**OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION**

Bu bağımsız offline araç eldeki Phase33 kapsülünden yalnız açıkça seçilmiş referansları taşıyan strict subset kapsülü türetir. Kaynak Phase31/32 çalışma alanına dönmez, guard'ı yeniden çalıştırmaz ve kaynak dosya gözlemi yapmaz. `derived_disclosure ⊆ source_disclosure`: seçilen referansın status ve projection içeriği birebir korunur, seçilmeyen referans yeni kapsülde bulunmaz. Daha küçük kapsül daha yüksek güven değildir.

2026-11-13 tarihinde iki izinli Phase34 ürün çağrısı tamamlandı: derivation **exit 0**, ilişki inspector'ı **exit 0**. Bütçe **2/2 tüketildi ve kapandı; kalan 0**. Gerçek source→derived sayımları reference **3→2**, provided **2→1**, withheld **1→1**, projection **3→2**, present **2→1**, absence **1→1**. Seçilmiş iki referansın status/projection içerikleri kaynakla birebir korundu; bloke referansın projection listesi boş kaldı. Seçilmeyen referansın metadata'sı yeni kapsüle veya dış disclosure kayıtlarına taşınmadı. Bu gözlem hostile sızıntı kabulü değildir.

Gerçek derived ürün kapsülü `outputs/phase34-capsule-derivation/derived-reference-capsule.zip`, **20253 B / 4 üye**, SHA256 `d3eea4c7946d45290c4876ac8b6d8ca5172297933b7681812863158bf845c01d`. Kaynak kapsül **23439 B / 4 üye** kimliğiyle korundu. Beş dış dosya, dört derived iç üye ve tam kimlikleri için [teslim kaydına](../../docs/commercial/operations/phase34/DEMO_DELIVERY.tr.md) bak. Üretim source commit'i `d253dda8d1d57dbf933e8b6e6dfc7d5db2da7324`, tree `3b03bae8baf47570004d71a205ff2abb91b83562`; üretim sonrası yalnız README ve teslim kaydı actual sonuçlara göre güncellendi. On kod/örnek dosyası üretim snapshot'ıyla aynı kalır.

## Sahip biçimi ve saf subset API

Tek kaynak girdi `outputs/phase33-reference-capsule/guarded-reference-capsule.zip`; gerçek kayıtlı kimliği **23439 B / 4 üye**, SHA256 `19e61b261d63863f10b4147daf6dc5b2199faedcda41b03acb20322d30cb3388`. Yeni request bu ZIP'in gerçek hash'ine bağlanır. Native/Phase31/32 dosyası, başka arşiv veya ham baseline okunmaz.

Mevcut `commercial_reference_capsule` public `inspect_bundle(raw_path, requested_ids)` dönüşü `(inspection, lookup)` çiftidir; ham capsule modeli sayılmaz. Dar adapter mevcut ZIP okuma/model/manifest/summary/README doğrulamasını yeniden kullanarak immutable doğrulanmış metadata sağlar. İkinci ZIP güvenlik okuyucusu veya evaluator yazılmaz. `derive_reference_subset(validated_source_capsule, request)` kaynakta bulunan seçilmiş referansları alır, kapalı sonuç/projection içeriklerini korur, sayımları yeniden türetir ve yeni modeli gerçek Phase33 `validate_capsule` ile doğrular. Kaynak model değişmez; caller'ın allow/validated etiketi otorite değildir.

Request `termivar-offline-capsule-derivation-request/v1`, tam altı alan: `schema_version`, `mode`, `derivation_reference`, `source_capsule_sha256`, `selected_reference_ids`, `derivation_constraints`. Yalnız `mode=demo`; 1–8 farklı mevcut ID ve kaynak referans kümesinin strict subset'i. Boş/duplicate/unknown seçim veya yanlış hash kapalı hata. Candidate/projection/guard override/kurum yetkisi/keyfî ZIP üyesi veya dosya yolu yoktur. Validator veya kaynak sözleşmesi uyumluluk uğruna gevşetilmez. Yeni capsule_reference yerel derivation kimliğidir; seçilmiş referans/projection içeriği ve mevcut kaynak bağları bu kimlik değişimiyle güncellenmez.

Derived ZIP mevcut Phase33 sözleşmesiyle tam dört üye taşır: `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt`. Mevcut renderer/manifest/README byte politikası yeniden kullanılır. Bloke referansta `projections=[]`; olumlu alt dosya bilgisi hiçbir üye/ledger/summary'ye taşınmaz. Seçilmeyen referansın ID, adı veya projection metadata'sı disclosure log'una kopyalanmaz. Dış ledger yalnız strict request, iki ZIP'in kimliği ve toplu sayımları taşır; projection payload'ı taşımaz.

## Tamamlanan exact iki ürün çağrısı

Aşağıdakiler gerçekten tamamlanmış root komutlarının tarihsel kaydıdır; tekrar çalıştırma izni değildir. İkinci çağrı ilk exit 0, eksiksiz dört gerçek çıktı ve derived ZIP'in dört üyesinin manuel incelemesinden sonra çalıştı. Actual exit kodları **[0,0]**, **2/2 bütçe kapalı, kalan 0**. Retry/üçüncü çağrı veya eski CLI tekrar çalıştırması yoktur. Phase20–33 ve eski Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_capsule_derivation/derive_capsule.py --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --request security-platform/tools/commercial_capsule_derivation/examples/demo_derivation_request.json --output-dir outputs/phase34-capsule-derivation
```

```text
python -I -B security-platform/tools/commercial_capsule_derivation/inspect_derivation.py --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --derived-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --ledger outputs/phase34-capsule-derivation/derivation-ledger.json --summary outputs/phase34-capsule-derivation/derivation-summary.md --manifest outputs/phase34-capsule-derivation/manifest.json --output outputs/phase34-capsule-derivation/derivation-inspection.json
```

İlk çağrı `derived-reference-capsule.zip`, `derivation-ledger.json`, `derivation-summary.md`, `manifest.json` üretti. Manifest gerçek ilk üç payload'ı bağlar, kendisini/inspection çıktısını kapsamaz. Başarılı üretim ve manuel inceleme sonrası ikinci çağrı `derivation-inspection.json` üretti; `internal_content_status=content_consistent`, kapsam `two_explicit_capsules_and_derivation_ledger_summary_manifest_only`. Yeni/boş output dizini, overwrite yasağı ve kısmi yazmada başarı iddiası üretmeme koşulu korunur.

## Sınırlar, portatif kullanım ve güven

Mevcut Phase33 sınırları korunur: ZIP 256 KiB; üye 128 KiB; expanded toplam 256 KiB; ratio 20; tam dört üye; reference 8; projection 64; depth 12; node 20.000; text 512. Ek request 32 KiB, ledger 64 KiB, summary 128 KiB, toplam açık girdi 1 MiB. Strict UTF-8/JSON; duplicate/unknown key/version, float/NaN/Infinity ve bool-as-int reddi. Duplicate ZIP/traversal/symlink/encryption/unsupported compression reddi. Daha sıkı owner sınırları gevşetilmez; truncation yoktur.

Bu araç kendi başına standalone binary veya production wheel değildir. Aynı korunmuş `security-platform/tools` ağacındaki Phase33 kapsül validator, güvenli reader, renderer ve manifest modüllerine bağlıdır. Derived kapsül Phase33 biçiminde olduğundan mevcut portatif Phase33 reader/lookup ile yalnız içindeki seçilmiş kayıtlar bakımından okunabilir. Bu turda ayrı eski lookup CLI'sı çalıştırılmaz. Kaynak kod paketi eski Phase33 kaynaklarını veya kaynak kapsülü otomatik kopyalamaz.

İlişki inspector'ı kaynak ve derived ZIP'i ayrı ayrı mevcut Phase33 owner yoluyla doğruladı; status/projection birebir eşliği, strict subset, ledger, summary ve manifest ilişkilerini inceledi. ZIP extraction yapılmadı. `content_consistent` yalnız bu iki kapsülün iç bütünlüğü ve aralarındaki subset ilişkisidir. İki ZIP hash'inin varlığı veya farklılığı tek başına köken/üretici yetkisi kanıtı değildir; derived tek başına kaynak kapsülden geldiğini bağımsız kanıtlamaz. Gerçek çalışma mevcut çalışma alanındadır; ikinci offline host'a taşınmış kodla kaynak yokluğu runtime kabulü NOT_RUN.

`demo_only=true`; Phase33'ün 18 false güven alanı korunur. `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`. Gerçek source freshness, producer/signature, compiler/module closure, ownership, insan/hukukî/müşteri veya production/release otoritesi kazanılmaz. Kayıtlı upstream `fresh_*` kodları şimdi yeni gözlem veya TTL garantisi değildir. Minimizasyon şifreleme veya anonimlik değildir.

NOT_RUN: hostile/duplicate JSON, invalid UTF-8, yanlış digest/ID, çelişkili capsule, blocked projection enjeksiyonu, omitted metadata sızıntısı saldırıları, duplicate ZIP/ZIP bomb/traversal/symlink/compression/limit, permission/partial write/crash/power loss/repeat determinism, ikinci offline host/source-absence kabulü, producer/signature/upstream guard/source freshness/compiler/module closure/ownership/native/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Kodda koruma olması saldırgan girdi kabulü değildir.

Belgeler: [sözleşme](../../docs/commercial/operations/phase34/DERIVATION_CONTRACT.tr.md), [monotonic disclosure](../../docs/commercial/operations/phase34/MONOTONIC_DISCLOSURE.tr.md), [portatif bütünlük](../../docs/commercial/operations/phase34/PORTABLE_INTEGRITY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase34/DEMO_DELIVERY.tr.md).

Kaynak teslim ZIP'i `Termivar-Offline-Capsule-Derivation-phase34-2026-11-13.zip`, kaynak ve derived ürün kapsüllerinden farklı artefact'tır. Son kaynak teslim boyutu/üye sayısı/SHA256 root paketlemesinde ayrıca ölçülüp dış delivery manifestinde tutulur; burada ölçülmemiş kimlik uydurulmaz ve öz hash döngüsü oluşturulmaz. Phase7–33, backend/operator-console/HBF/Altay/native/auth/DB/roller/wheel/lock/lisans korunur. İzinli iki çağrı tamamlandı; ölçülmüş teslim kapanınca Phase35/yeni mikro özellik veya otomatik paylaşım başlatılmaz.
