# Phase44 demo teslim kaydı

**OFFLINE DEMONSTRATION — UNTRUSTED CAPSULE RECONCILIATION ONLY — NO TASK DISPATCH, ASSIGNMENT, APPROVAL, EXECUTION OR SUBMISSION**

Tarih: **2026-11-19**. Bu kayıt Phase44 kodunun gerçekten çalıştırılmasının ölçülmüş sonucudur.

- Çalışma kaynağı: `feat/offline-portable-task-exchange` worktree'si (`security-platform-phase43-source`).
- Base HEAD: `2f20571062ea19088271f7ee3401fbbce8afebb8`.
- Phase44 dosyaları çalışma anında commit'lenmemişti (untracked).

## Doğrulanmış Phase43 girdileri

Phase43 teslimi salt okunur doğrulandı. Dış ZIP şu değerlere sahip:

- `outputs/Termivar-Offline-Task-Exchange-phase43-2026-11-15.zip`
- 21 üye, 63322 byte
- SHA256 `ddf418306c33d107aa39d5eae734aca488d0405bd4b7a9de51747b507a9018c1`

Bu değerler closure kaydıyla eşleşti. Aşağıdaki altı Phase43 çıktısının diskteki hash'leri kayıtlarla aynıdır:

| Girdi rolü | Dosya | Byte | SHA256 |
| --- | --- | ---: | --- |
| İçe alınan (güvenilmeyen) capsule | outputs/phase43-task-exchange/task-exchange-capsule.zip | 6742 | 49a10169defbaa4f5f2c59e8488f8a345e8c8a51926dc4534893f9c93619c70a |
| Phase43 açıklama kaydı: index | outputs/phase43-task-exchange/task-exchange-index.json | 2014 | d3c1328549513342084493bf5390e11b871e04dfa501b869daa9822b8b346d41 |
| Phase43 açıklama kaydı: manifest | outputs/phase43-task-exchange/manifest.json | 6701 | 43d4bfca39ccf39c05c7d8a3a18ba78045a3504aad168b761628f0a31bd55ea7 |
| Phase42 görev kaydı: register | outputs/phase42-deferred-intake/deferred-intake-register.json | 6294 | 6465bab021f525b47d4fafd5a0ddc68020989b60e82bce3ec70f6bfaa4f8ff16 |
| Phase42 görev kaydı: manifest | outputs/phase42-deferred-intake/manifest.json | 5796 | fbe94605564f06a11165cc9fb71229100b609e2c7d0248e4772af53ddb81b6cc |

Tam girdi listesi `outputs/phase44-task-reconciliation/manifest.json` dosyasının `inputs` alanındadır: 12 rol, her biri byte ve SHA256 ile. Demo isteği `tools/commercial_task_reconciliation/examples/demo_reconciliation_request.json` yalnız bu doğrulanmış iki kimliği pinler. Ek candidate, sahte capsule veya uydurulmuş başarılı senaryo kullanılmadı. Demo, doğrulanmış tek Phase43 capsule'ını (F0001 / CAND0002) her iki yerel kayıt grubuyla yeniden içe almaktır. İçe alınan capsule ile Phase43 açıklama kaydındaki capsule aynı dosyadır.

## Gerçek komutlar ve çıkış kodları

Komutlar çalışma alanı kökünden çalıştırıldı. Aşağıdakiler tarihsel çağrı kaydıdır.

| Sıra | Komut | UTC başlatma | Çıkış kodu |
| ---: | --- | --- | ---: |
| 1 | import_task_capsule.py | 2026-11-19T08:29:34.162916+00:00 | 0 |
| 2 | inspect_task_reconciliation.py | 2026-11-19T08:29:42.233111+00:00 | 0 |

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_reconciliation/import_task_capsule.py --capsule outputs/phase43-task-exchange/task-exchange-capsule.zip --request security-platform-phase43-source/tools/commercial_task_reconciliation/examples/demo_reconciliation_request.json --local-register outputs/phase42-deferred-intake/deferred-intake-register.json --local-classification outputs/phase42-deferred-intake/intake-classification.json --local-intake-receipt outputs/phase42-deferred-intake/intake-source-receipt.json --local-intake-summary outputs/phase42-deferred-intake/intake-summary.md --local-intake-manifest outputs/phase42-deferred-intake/manifest.json --disclosed-capsule outputs/phase43-task-exchange/task-exchange-capsule.zip --disclosed-index outputs/phase43-task-exchange/task-exchange-index.json --disclosed-receipt outputs/phase43-task-exchange/task-exchange-source-receipt.json --disclosed-summary outputs/phase43-task-exchange/task-exchange-summary.md --disclosed-manifest outputs/phase43-task-exchange/manifest.json --output-dir outputs/phase44-task-reconciliation
```

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_reconciliation/inspect_task_reconciliation.py <yukarıdaki aynı girdiler> --inbox outputs/phase44-task-reconciliation/task-inbox-record.json --report outputs/phase44-task-reconciliation/capsule-reconciliation-report.json --summary outputs/phase44-task-reconciliation/capsule-reconciliation-summary.md --manifest outputs/phase44-task-reconciliation/manifest.json --output outputs/phase44-task-reconciliation/inspection-summary.json
```

## Ölçülmüş çıktılar

| Dosya | Byte | SHA256 |
| --- | ---: | --- |
| task-inbox-record.json | 2373 | 2203622b9e4e37888fddb519518c99969cc63727168331ce05f24316fc05b13a |
| capsule-reconciliation-report.json | 33548 | 9235ad645005e9c6bc65dd5f3bcbed9a90cb75915555ec283a1c9899f9eb9313 |
| capsule-reconciliation-summary.md | 11716 | 4f97db0c215b814590e9c31ad1168d1be7a892c55eb6c6fa5288fae260f7b415 |
| manifest.json | 4058 | 4a45a7237e2fbb8753471465788a91e2ea29ed2ad1f97d8ae17ee6f5d70114e0 |
| inspection-summary.json | 5353 | b59a0403bfcdcf6e00f7e65784d0009d24e2df1d40c25e17c73c2c77cd788668 |

## Sonuç

- **Arşiv:** `READABLE`, 4 üye, sıra `CANONICAL`, container `ACCEPTABLE`, bildirilen açılmış boyut 6276 byte.
- **Inner manifest:** üç payload eşleşmesi `MATCH`, owner manifest eşliği `MATCH`.
- **Phase43 owner reader:** `COMPATIBLE`. Temsil durumu `ESTABLISHED_BY_PHASE43_OWNER_READER`; beyan edilen ve temsil edilen kimlik eşliği `MATCH`.
- **Alan sınıflandırması:** 20 alanın tamamı (10 envelope, 10 görev) `VALID`. Eksik, null, boş, geçersiz veya beklenmeyen alan yok.
- **Yerel mutabakat:** `PHASE42_TASK_RECORDS_AND_PHASE43_DISCLOSURE_RECORDS` modunda 35 karşılaştırma satırının hepsi `MATCH`. Satırların kapsamı:
  - Phase42 tarafı: 2 kaynak digest'i, F0001'in 10 alanı, binding tuple ve iki ters binding sahipliği.
  - Phase43 tarafı: capsule SHA256, 4 iç üye SHA256'sı, 2 kaynak digest'i, request reference, görev listesi, 10 alan ve binding tuple.
  - Görev araması: Phase42 `FOUND`, Phase43 `FOUND`.
- **Bulgular:** yalnız `P44-MANUAL_REVIEW_REQUIRED:capsule` (bilgilendirme).
- **Uygunluk:** **`STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW`**, `manual_review=ELIGIBLE_FOR_MANUAL_REVIEW`, `manual_review_requirement=REQUIRED`.
- **Inbox:** `QUARANTINED_AWAITING_MANUAL_REVIEW`, 1 görev (F0001, `fact_origin=CAPSULE_DECLARED_STRUCTURALLY_VALID_NOT_AUTHENTICATED`, `local_reconciliation=MATCH`). 14 `non_claims` alanının tamamı `false`.
- **Inspector:** 10 kontrolün hepsi `PASSED`. Bağımsız türetilen uygunluk aynı, `eligibility_agreement=AGREES`, owner reader yeniden çalıştırıldı (`COMPATIBLE`), `regenerated_outputs=BYTE_IDENTICAL`.

Bu sonuç yalnız şunu söyler: aynı capsule'ın yerel kayıtlarla yapısal ve kayıt düzeyinde tutarlı olduğu. Capsule ve açıklama kaydı aynı dosya olduğu için `MATCH` sonucu beklenendir; bağımsız bir kaynaktan gelen capsule kanıtı değildir. Üretici kimlik doğrulaması, güvenli aktarım, kaynak provenance'ı, gerçek dünya gözlemi, görev atama, onay, yürütme veya gönderim değildir. Bir sonraki adım ancak yetkili bir insanın manuel incelemesi olabilir; Phase44 bunu başlatmaz.

## Testler (ilk teslim)

Komut, worktree kökünden ve mevcut `security-platform/.venv` ortamıyla (Python 3.14.7, pytest 9.2.0) çalıştırıldı; yeni paket kurulmadı:

```powershell
..\security-platform\.venv\Scripts\python.exe -m pytest tests/commercial_task_reconciliation -v -p no:cacheprovider
```

Sonuç: **62 passed**, 0 failed, 0 skipped. Testler sentetik fixture kullanır. Tek entegrasyon testi (`test_real_phase43_capsule_copies_reconcile`) mevcut Phase42 ve Phase43 çıktılarının geçici dizine alınmış kopyalarını okur.

Testlerin kapsamı:

- geçerli import;
- eksik ve duplicate üye, traversal/mutlak/ters bölü/iç içe/dizin adları, büyük-küçük harf çakışması;
- STORED olmayan, symlink ve şifreli girdiler;
- boyut, açılmış boyut ve üye sayısı sınırları, okunamayan arşiv ve CRC hatası;
- bozuk JSON, duplicate JSON anahtarı, şema uyuşmazlığı, canonical olmayan JSON, inner manifest hash uyuşmazlığı;
- tanılama ile owner reader çelişkisi;
- eksik, null ve boş kimlik; boş string/liste/nesne, false ve 0 ayrımı; bozuk tanımlayıcı;
- tutarsız görev beyanı, beklenmeyen alanlar;
- tam eşleşme, kimlik uyuşmazlığı (gizlenen ve yazılan yerel değer), belirsiz binding, yerel görev bulunamaması, yerel kayıt olmaması, istek ile yerel kayıt uyuşmazlığı, tutarsız yerel gruplar;
- byte-identical determinizm, açıklama minimizasyonu;
- CLI çıkış kodları; inspector'ın altı kurcalama türünü yakalaması; adversarial review regresyonları.

Mevcut proje testlerinin regresyon koşusu da yapıldı:

```powershell
..\security-platform\.venv\Scripts\python.exe -m pytest tests/unit tests/policy_contracts tests/policy_revision_lab -q -p no:cacheprovider -m "not integration and not e2e"
```

Sonuç: **413 passed, 2 skipped** (platform nedenli), 55 deselected. PostgreSQL gerektiren integration ve e2e testleri bu koşuda seçilmedi; **NOT_RUN**.

## Bağımsız adversarial inceleme

Kod iki turda, çok ajanlı bir iş akışıyla incelendi. Her bulgu ayrı bir şüpheci ajan tarafından yeniden üretilmeye çalışıldı.

**İlk tur** (4 bakış açısı + 4 doğrulayıcı) şunları doğruladı:

1. Bulgu taşması: duplicate adlarla 400 bulgu sınırı aşılıyor, rapor üretilmiyordu.
2. ZIP64 ve çok büyük boyut yüzünden rapor üretilmiyordu.
3. 2^31 ile 2^53 arasındaki integer'lar rapor doğrulamasını düşürüyordu.
4. `READ_ERROR` içerik durumu hiç kullanılmıyordu.
5. Inspector'ın byte taramasında yanlış pozitifler vardı.
6. Yerel register digest'inin açıklanmasında tutarsızlık vardı.

**İkinci tur** (fuzz/mutasyon, inspector kurcalama, belge–kod denetimi + 3 doğrulayıcı) şunları buldu:

- byte taramasında kalan JSON kaçışı ve hash kaynaklı yanlış pozitifler;
- beş belge ifadesi yanlış veya abartılıydı.

Hepsi düzeltildi ve regresyon testleri eklendi. Fail-open, yani güvenilmeyen capsule'ı kabul eden bir bulgu iki turda da çıkmadı.

## Koruma

Değişiklik öncesinde `outputs/` altındaki 651 dosyanın baseline'ı alındı. Demo sonrası yeniden ölçüldüğünde 651 dosyanın hepsi byte ve SHA256 olarak aynıydı; yalnız beş yeni Phase44 çıktısı eklendi.

Orijinal `security-platform` deposu (`feat/offline-deferred-intake`, HEAD `3dc85d1…`) değişmedi; önceden var olan üç untracked dizini korundu. Worktree'nin izlenen dosyalarında fark yoktur. Phase7–43 kaynakları, çıktıları, arşivleri ve manifestleri değiştirilmedi. Dış teslim ZIP'inin ve teslim metadata'sının ölçümü bu belgenin dışındaki kayıtlardadır; bu belge kendi arşivinin hash'ini içermez.

## Denetim düzeltmeleri sonrası yeniden çalıştırma (r2)

Aynı gün `2f2fbe0` commit'i üzerinde salt-okunur bir denetim yapıldı. Denetim kritik veya yüksek önemde bulgu çıkarmadı, dört orta önemde bulgu çıkardı. Dördü de düzeltildi:

1. **Inspector, çok görevli Phase43 açıklama kaydına karşı dürüst bir `IDENTITY_MISMATCH` çıktısını reddediyordu.** Builder virgülle birleştirilmiş `task_id_list` değerini doğru biçimde yazıyordu, ama inspector'ın izinli değer kümesinde bu birleşik değer yoktu. Açıklama denetimi artık satır bazlıdır: yazılan her yerel değer, yerel kayıttan ayrıca hesaplanan değerle karşılaştırılır.
2. **Özet, karantinadaki görevleri "Kabul edilen" diye adlandırıyordu.** Satır artık şöyledir: "Karantinadaki inbox kaydına alınan görev sayısı (kabul, onay veya atama değildir)".
3. **Yalnız Phase43 owner'ın uyguladığı kapılar test edilmemişti.** Sondaki/öndeki byte, birleştirilmiş arşiv, flag bitleri, üye yorumu, tarih, `create_system`, `external_attr`, `internal_attr`, sürüm alanı ve yalnız local header'daki extra alanı için testler eklendi. Owner'ın sıkı JSON parser'ı için de testler eklendi: BOM, NaN, float, negatif, 2^53, 17 basamak, tekil surrogate, derinlik ve duplicate anahtar.
4. **Phase44'ün kendi yollarında boşluklar vardı.** Şunlar için testler eklendi:
   - `PHASE43_DISCLOSURE_RECORDS_ONLY` modu;
   - 2 ve 8 görevli capsule'lar;
   - üçlü ile binding sahipliği;
   - owner ile beyan arasındaki farkın tek başına tetiklediği `DIAGNOSTIC_OWNER_DISAGREEMENT`;
   - IDENTITY_MISMATCH çıktısında inspector;
   - her kurcalamanın hangi inspector kontrolüne takıldığı;
   - pin, yeniden okuma ve kimlik kontrolleriyle dosya yükleyicileri (owner inceleme fonksiyonları yerine sentetik vekiller kullanıldı);
   - izole Python ile CLI çağrısı;
   - daha önce hiçbir testte doğrulanmayan 27 bulgu kuralı. Katalogda doğrulanmayan tek kural, mevcut sınırlarla ulaşılamayan `FINDINGS_TRUNCATED` kaldı.

Çalışma durumu `2f2fbe0` artı commit'lenmemiş düzeltmelerdir. Çalıştırma anında `tools/commercial_task_reconciliation/` altındaki Python dosyalarından yalnız ikisi değişmişti:

| Dosya | SHA256 |
| --- | --- |
| `inspect_task_reconciliation.py` | `36a251f5630a508a924ba10b06065ab891c804db7f3be705260002b1f9f352d7` |
| `reconciliation_renderer.py` | `df208fcbe0f3ac26514b27c8563841ab69adacefa16f90013fa21732f9180d33` |

Diğer `tools/commercial_task_reconciliation/*.py` dosyaları `2f2fbe0` ile aynıdır. Diğer değişikliklerin durumu:

- Çalıştırma anında iki test dosyası değişmiş, üç test dosyası yeni eklenmişti.
- README ve üç belge çalıştırmadan sonra güncellendi.
- Bağımsız incelemeden sonra yalnız test dosyaları ve bu kayıt değişti. Yukarıdaki iki hash, çalıştırılabilir kodun son hâlidir.

Komutlar, yukarıdaki demo komutlarının aynısıdır. Tek fark çıktı yollarının `outputs/phase44-task-reconciliation-r2/` olmasıdır.

| Sıra | Komut | UTC başlatma | Çıkış kodu |
| ---: | --- | --- | ---: |
| 1 | import_task_capsule.py | 2026-11-19T16:27:04.561309Z | 0 |
| 2 | inspect_task_reconciliation.py | 2026-11-19T16:27:04.967645Z | 0 |

| Dosya | Byte | SHA256 |
| --- | ---: | --- |
| task-inbox-record.json | 2373 | 2203622b9e4e37888fddb519518c99969cc63727168331ce05f24316fc05b13a |
| capsule-reconciliation-report.json | 33548 | 9235ad645005e9c6bc65dd5f3bcbed9a90cb75915555ec283a1c9899f9eb9313 |
| capsule-reconciliation-summary.md | 11759 | 5e4d08d02d5096a408d1cb81404a2776a7e2a5cd5b626cfdf9dbcb5701192697 |
| manifest.json | 4058 | 68d7bf62647fdcbab406db79180c1728179d05d4182affc014238b288400c88d |
| inspection-summary.json | 5353 | d54041061935cceedaab47b913c1a232550191d47ca5bb54bb7987d496e70d1b |

İlk çalıştırmayla karşılaştırma:

- Inbox ve rapor byte byte aynıdır.
- Özette yalnız görev sayısı satırı değişti.
- `manifest.json` ve `inspection-summary.json` yalnız özetin yeni byte kimliği nedeniyle farklıdır.
- Uygunluk yine `STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW`'dur; inspector yine `AGREES` / `BYTE_IDENTICAL` verdi.

İlk çalıştırmanın `outputs/phase44-task-reconciliation/` dizini ve `outputs/Termivar-Offline-Task-Capsule-Reconciliation-phase44-2026-11-19.zip` teslim arşivi değiştirilmedi. Bu arşiv düzeltme öncesi kodu ve eski özet ifadesini içerir; tarihsel kayıt olarak durur.

**Testler (r2):** `..\security-platform\.venv\Scripts\python.exe -m pytest tests/commercial_task_reconciliation -q -p no:cacheprovider -rs` komutu, bağımsız incelemeden sonra eklenen testlerle birlikte **157 passed**, 0 failed, 0 skipped verdi. Proje regresyon koşusu, yukarıdakiyle aynı komutla, **413 passed, 2 skipped** (platform nedenli), 55 deselected verdi.

Yeni O1 ve O2 testleri ayrıca kontrol edildi. Değiştirilmiş iki dosyanın `2f2fbe0` sürümleri geçici bir kopyaya kondu ve testler orada koşuldu. O1 testleri iki modda da ve özet ifadesi testi dört senaryonun hepsinde başarısız oldu. Yani testler düzeltilen hataları gerçekten yakalıyor.

**Bağımsız inceleme (r2):** Düzeltmeler üç ayrı açıdan incelendi: inspector doğruluğu, test kalitesi, belge–kod uyumu. Her bulguyu ayrı bir ajan çürütmeye çalıştı; toplam 9 ajan kullanıldı. Kritik, yüksek veya orta önemde bulgu çıkmadı.

Düşük önemdeki test boşlukları kapatıldı. Bunun için yeni açıklama kurallarının her biri, geçici bir kopyada kasten bozuldu. Yedi mutasyondan altısını hedeflenen test yakaladı.

Yakalanmayan tek mutasyon inspector'ın `match_local_value_differs` kontrolünü kaldırıyor. Bu kontrole sözleşmeye uygun hiçbir rapor ulaşamaz, çünkü kapalı rapor sözleşmesi `MATCH` satırında iki tarafın aynı tipte aynı değeri taşımasını zaten zorunlu kılar (`comparison_match_semantics`). Kontrol ikinci bir koruma olarak bırakıldı ve bu davranışı bir test sabitler.

**Koruma (r2):** Çalıştırmadan önce `outputs/` altındaki 661 dosya ölçüldü. Sonrasında hiçbiri değişmemiş veya kaybolmamıştı; yalnız beş r2 çıktısı eklendi.

**Açık kalanlar:**

- Denetimin düşük ve bilgi düzeyindeki bulguları bu turda ele alınmadı. Örnekler: container kararının owner reddinde `ACCEPTABLE` kalması, ulaşılamayan `FINDINGS_TRUNCATED` yolu, yayının atomik olmaması.
- Dosya yükleyicileri gerçek Phase42/Phase43 owner incelemesiyle yalnız çalışma alanı çıktılarının kopyalarını kullanan entegrasyon testinde çalışır. Bu test, çıktılar yoksa atlanır.
- Bağımsız incelemenin önceden var olan iki sertleştirme bulgusu açık kaldı:
  - Inspector, `capsule_value` alanlarını ve `MATCH`/`MISMATCH` etiketini owner reader çıktısından ayrıca yeniden hesaplamaz. Builder'da bir kusur olsaydı, sahte bir `MATCH` satırı açıklanmamış bir yerel değeri taşıyabilirdi. Bunu yalnız aynı motoru kullanan yeniden üretim adımı görür.
  - Binding sahibi yankısı, sahibin görev kimliğinin Phase43 kaydında bulunmasına bakar, binding'in kendisine bakmaz. Bu, builder ile inspector'ın ortak kuralıdır. Ancak birbiriyle tutarsız yerel kayıtlarla ortaya çıkar.
- Özetteki açıklama notu, yerel değerin yazıldığı üçüncü durumu (açık girdi dosyasının byte kimliği) hâlâ anmaz. Bu not değişirse özet byte'ları da değişir; bu yüzden ayrı bir turda ele alınmalıdır.

## NOT_RUN

- Üretici kimliği, imza, anti-replay, güvenilir zaman damgası, güvenli aktarım.
- Gerçek ikinci host veya bağımsız kaynaktan gelen capsule ile çalışma.
- Görev gönderimi, ataması, onayı, yürütmesi, tamamlanması; response gönderimi veya ingestion.
- Kaynak yeniden gözlemi; Phase31 guard; Rust ve native runtime.
- PostgreSQL integration ve e2e testleri.
- İnsan, hukuk, müşteri, production veya release kabulü.
- Push, release veya deploy.
