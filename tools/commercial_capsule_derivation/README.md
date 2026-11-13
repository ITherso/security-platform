# Offline capsule derivation ve monotonic disclosure

**OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION**

Bu bağımsız offline araç eldeki Phase33 kapsülünden yalnız açıkça seçilmiş referansları taşıyan strict subset kapsülü türetir. Kaynak Phase31/32 çalışma alanına dönmez, guard'ı yeniden çalıştırmaz ve kaynak dosya gözlemi yapmaz. `derived_disclosure ⊆ source_disclosure`: seçilen referansın status ve projection içeriği birebir korunur, seçilmeyen referans yeni kapsülde bulunmaz. Daha küçük kapsül daha yüksek güven değildir.

Kaynak hazırlığında Phase34 ürün çağrısı **0**. Henüz yeni derived ZIP, ilişki inspector'ı veya çıktı başarısı, boyut/SHA256 iddia edilmez. Mevcut Phase33 sonuçları yeni ürün sonucu yerine geçirilmez.

## Sahip biçimi ve saf subset API

Tek kaynak girdi `outputs/phase33-reference-capsule/guarded-reference-capsule.zip`; gerçek kayıtlı kimliği **23439 B / 4 üye**, SHA256 `19e61b261d63863f10b4147daf6dc5b2199faedcda41b03acb20322d30cb3388`. Yeni request bu ZIP'in gerçek hash'ine bağlanır. Native/Phase31/32 dosyası, başka arşiv veya ham baseline okunmaz.

Mevcut `commercial_reference_capsule` public `inspect_bundle(raw_path, requested_ids)` dönüşü `(inspection, lookup)` çiftidir; ham capsule modeli sayılmaz. Dar adapter mevcut ZIP okuma/model/manifest/summary/README doğrulamasını yeniden kullanarak immutable doğrulanmış metadata sağlar. İkinci ZIP güvenlik okuyucusu veya evaluator yazılmaz. `derive_reference_subset(validated_source_capsule, request)` kaynakta bulunan seçilmiş referansları alır, kapalı sonuç/projection içeriklerini korur, sayımları yeniden türetir ve yeni modeli gerçek Phase33 `validate_capsule` ile doğrular. Kaynak model değişmez; caller'ın allow/validated etiketi otorite değildir.

Request `termivar-offline-capsule-derivation-request/v1`, tam altı alan: `schema_version`, `mode`, `derivation_reference`, `source_capsule_sha256`, `selected_reference_ids`, `derivation_constraints`. Yalnız `mode=demo`; 1–8 farklı mevcut ID ve kaynak referans kümesinin strict subset'i. Boş/duplicate/unknown seçim veya yanlış hash kapalı hata. Candidate/projection/guard override/kurum yetkisi/keyfî ZIP üyesi veya dosya yolu yoktur. Validator veya kaynak sözleşmesi uyumluluk uğruna gevşetilmez. Yeni capsule_reference yerel derivation kimliğidir; seçilmiş referans/projection içeriği ve mevcut kaynak bağları bu kimlik değişimiyle güncellenmez.

Derived ZIP mevcut Phase33 sözleşmesiyle tam dört üye taşır: `reference-capsule.json`, `reference-summary.md`, `bundle-manifest.json`, `README.txt`. Mevcut renderer/manifest/README byte politikası yeniden kullanılır. Bloke referansta `projections=[]`; olumlu alt dosya bilgisi hiçbir üye/ledger/summary'ye taşınmaz. Seçilmeyen referansın ID, adı veya projection metadata'sı disclosure log'una kopyalanmaz. Dış ledger yalnız strict request, iki ZIP'in kimliği ve toplu sayımları taşır; projection payload'ı taşımaz.

## İzinli exact iki ürün çağrısı

Aşağıdakiler planlanan root komutlarıdır; henüz başarı kaydı değildir. Phase34 bütçesi en fazla iki çağrı. İkinci yalnız ilk exit 0, eksiksiz dört gerçek çıktı ve manuel derived-üye incelemesi sonrası çalışır. Başarısız çağrı tüketilir; retry/üçüncü çağrı veya eski CLI tekrar çalıştırması yoktur. Phase20–33 ve eski Phase24/29 insan istisnaları kapalıdır.

```text
python -I -B security-platform/tools/commercial_capsule_derivation/derive_capsule.py --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --request security-platform/tools/commercial_capsule_derivation/examples/demo_derivation_request.json --output-dir outputs/phase34-capsule-derivation
```

```text
python -I -B security-platform/tools/commercial_capsule_derivation/inspect_derivation.py --source-bundle outputs/phase33-reference-capsule/guarded-reference-capsule.zip --derived-bundle outputs/phase34-capsule-derivation/derived-reference-capsule.zip --ledger outputs/phase34-capsule-derivation/derivation-ledger.json --summary outputs/phase34-capsule-derivation/derivation-summary.md --manifest outputs/phase34-capsule-derivation/manifest.json --output outputs/phase34-capsule-derivation/derivation-inspection.json
```

İlk çağrı `derived-reference-capsule.zip`, `derivation-ledger.json`, `derivation-summary.md`, `manifest.json` üretir. Manifest gerçek ilk üç payload'ı bağlar, kendisini kapsamaz. Başarılı üretim sonrası ikinci çağrı `derivation-inspection.json` üretir. Yeni/boş output dizini, overwrite yasağı ve kısmi yazmada başarı iddiası üretmeme koşulu korunur.

## Sınırlar, portatif kullanım ve güven

Mevcut Phase33 sınırları korunur: ZIP 256 KiB; üye 128 KiB; expanded toplam 256 KiB; ratio 20; tam dört üye; reference 8; projection 64; depth 12; node 20.000; text 512. Ek request 32 KiB, ledger 64 KiB, summary 128 KiB, toplam açık girdi 1 MiB. Strict UTF-8/JSON; duplicate/unknown key/version, float/NaN/Infinity ve bool-as-int reddi. Duplicate ZIP/traversal/symlink/encryption/unsupported compression reddi. Daha sıkı owner sınırları gevşetilmez; truncation yoktur.

Bu araç kendi başına standalone binary veya production wheel değildir. Aynı korunmuş `security-platform/tools` ağacındaki Phase33 kapsül validator, güvenli reader, renderer ve manifest modüllerine bağlıdır. Derived kapsül Phase33 biçiminde olduğundan mevcut portatif Phase33 reader/lookup ile yalnız içindeki seçilmiş kayıtlar bakımından okunabilir. Bu turda ayrı eski lookup CLI'sı çalıştırılmaz. Kaynak kod paketi eski Phase33 kaynaklarını veya kaynak kapsülü otomatik kopyalamaz.

İlişki inspector'ı kaynak ve derived ZIP'i ayrı ayrı mevcut Phase33 owner yoluyla doğrular; status/projection birebir eşliği, strict subset, ledger, summary ve manifest ilişkilerini inceler. ZIP extraction yapmaz. `content_consistent` yalnız bu iki kapsülün iç bütünlüğü ve aralarındaki subset ilişkisidir. İki ZIP hash'inin varlığı veya farklılığı tek başına köken/üretici yetkisi kanıtı değildir; derived tek başına kaynak kapsülden geldiğini bağımsız kanıtlamaz.

`demo_only=true`; Phase33'ün 18 false güven alanı korunur. `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`. Gerçek source freshness, producer/signature, compiler/module closure, ownership, insan/hukukî/müşteri veya production/release otoritesi kazanılmaz. Kayıtlı upstream `fresh_*` kodları şimdi yeni gözlem veya TTL garantisi değildir. Minimizasyon şifreleme veya anonimlik değildir.

NOT_RUN: hostile/duplicate JSON, invalid UTF-8, yanlış digest/ID, çelişkili capsule, blocked projection enjeksiyonu, omitted metadata sızıntısı saldırıları, duplicate ZIP/ZIP bomb/traversal/symlink/compression/limit, permission/partial write/crash/power loss/repeat determinism, ikinci offline host/source-absence kabulü, producer/signature/upstream guard/source freshness/compiler/module closure/ownership/native/human/legal/customer/release. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Kodda koruma olması saldırgan girdi kabulü değildir.

Belgeler: [sözleşme](../../docs/commercial/operations/phase34/DERIVATION_CONTRACT.tr.md), [monotonic disclosure](../../docs/commercial/operations/phase34/MONOTONIC_DISCLOSURE.tr.md), [portatif bütünlük](../../docs/commercial/operations/phase34/PORTABLE_INTEGRITY.tr.md), [teslim kaydı](../../docs/commercial/operations/phase34/DEMO_DELIVERY.tr.md).

Kaynak teslim ZIP'i `Termivar-Offline-Capsule-Derivation-phase34-2026-11-13.zip`, kaynak ve derived ürün kapsüllerinden farklı artefact'tır. Ölçülmemiş kimlik uydurulmaz; final kaynak ZIP kimliği dış delivery manifestinde tutulur. Phase7–33, backend/operator-console/HBF/Altay/native/auth/DB/roller/wheel/lock/lisans korunur. İzinli geliştirme, iki çağrı, dar inceleme ve ölçülmüş teslim bitince durulur; Phase35/yeni mikro özellik veya otomatik paylaşım başlatılmaz.
