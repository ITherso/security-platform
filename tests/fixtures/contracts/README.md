# Cihaz sözleşmesi fikstürleri

Bu ağaç, ajanın Platform'a gönderdiği cihaz yüklerinin paylaşılan ve sürümlü örnekleridir (GitHub issue #10). Her yük, Platform'un ona verdiği kararla birlikte durur. Kabul edilen her yük için operatör API'sinin sonraki cevabı da burada saklanır. Platform testi, konsol testi ve ileride ajan testi aynı dosyaları okur.

## İçerik

| Yol | Ne |
|---|---|
| `events/v1/`, `events/v2/` | `POST /api/v1/device/events` gövdeleri, `altay-edr-event/v1` ve `v2`. |
| `snapshots/v1/`, `snapshots/v2/`, `snapshots/v3/` | `PUT /api/v1/device/snapshot` gövdeleri, Snapshot V1, V2 ve V3. |
| `.../valid/` | Kabul edilmesi gereken yükler. Gövdedeki `schema_version` dizinin sürümüdür. |
| `.../invalid/` | Reddedilmesi gereken yükler. Dizin, hangi sürümün kuralının denendiğini söyler; gövde başka bir `schema_version` taşıyabilir (ör. `events/v1/invalid/schema_version_unknown.json`). |
| `expectations.json` | Her yükün beklenen kararı. Elle yazılır; test onu hiçbir zaman yeniden yazmaz. |
| `goldens/<aile>/v<N>/<ad>.json` | Kabul edilen her yükün altın cevabı. |
| `manifest.json` | `manifest.json` dışındaki her dosya: yol, sha256, tür, sürüm ve yükler için beklenen karar. |

Yük dosyaları gönderilecek baytların kendisidir. Test onları değiştirmeden gövde olarak yollar. Çoğu iki boşlukla girintilidir. Boyut sınırını deneyen dört yük (`body_too_large`, iki `canonical_too_large`, `too_many_nodes`) tek satırdır, çünkü sınır gönderilen bayt sayısıyla ölçülür. `duplicate_key.json` bilerek geçersiz JSON'dur.

### Beklenen karar

`expectations.json` içindeki her kayıt:

- `decision`: `accepted` ya da `rejected`.
- `status` ve `error`: reddin HTTP durumu ve cevap gövdesindeki `detail`. Beklenen gövde tam olarak `{"detail": error}` olur.
- `cursor`: yalnız olay batch'inin 409 cevabında. Gövdeye `last_batch_sequence` ve `last_event_seq` olarak eklenir.
- `after`: önce aynı yeni cihaza gönderilen ve kabul edilen yükler. Yalnız 409 vakalarında vardır.
- `note`: kuralın kısa açıklaması. Manifest'e kopyalanmaz.

Şu anki ağaç 127 yük taşır: 27 kabul, 100 ret. Retlerin 88'i 422 (`invalid_request`), 7'si 409, 3'ü 413, 2'si 400'dür. Sürüme göre: olay v1 5 kabul/31 ret, olay v2 10/25, Snapshot V1 4/15, V2 4/10, V3 4/19. 2026-11-27'deki çalıştırmada Platform 127 yükün 127'sine beklenen kararı verdi.

### Altın cevap

Her altın dosya dört alan taşır:

- `payload`: yükün yolu.
- `ack`: kabul cevabı.
- `timeline`: `GET /api/v1/tenants/{tenant}/devices/{device}/events` cevabı (varsayılan sayfa, 50 olay).
- `device`: `GET /api/v1/tenants/{tenant}/devices/{device}` cevabı. Ürünler ve `edr_agent` durumu buradadır.

Çalışmaya özgü değerler şöyle sabitlenir:

| Değer | Altın dosyada | Neden |
|---|---|---|
| Sunucu saati | `2030-01-02T03:04:05Z` | Test, servis modüllerindeki her `utc_now` kopyasını bu ana sabitler. `received_at`, `created_at`, `last_received_at`, ürün `received_at` ve `observation.age_seconds` bu saatten çıkar. Yer tutucu gerekmez. |
| Tenant kimliği | `11111111-1111-4111-8111-111111111111` | Her çalışma yeni bir tenant açar. |
| Cihaz kimliği | `22222222-2222-4222-8222-222222222222` | Her yük yeni bir cihaza gönderilir. |
| Cihaz etiketi | `Contract fixture device` | Testteki sabit etiket. |

Operatör JWT'si gerçek saatle imzalanır ve doğrulanır; o saat cevaplara girmez. Yük içindeki kimlikler (`batch_id`, `message_id`, `action_id`) dosyada sabittir ve olduğu gibi kalır. Test, gerçek tenant ve cihaz kimliğinin altın dosyada hiçbir metinde kalmadığını da denetler.

## Testler

`tests/integration/test_contract_fixtures.py` gerçek PostgreSQL ister:

- Her yük için bir cihaz kaydeder ve `after` yüklerini gönderir. Sonra yükü gerçek device route'una yollar ve durumu ve gövdeyi `expectations.json` ile karşılaştırır.
- Ret sonrası cihazın zaman çizelgesi ve detayı ret öncesiyle aynı olmalıdır; hiçbir şey yazılmaz.
- Kabulde yükü aynen tekrar yollar. İkinci cevap ilk kabul cevabıyla aynı olmalıdır. Sonra zaman çizelgesini ve detayı okur ve altın dosyayla karşılaştırır.
- Son test manifest'i ağaçtan yeniden hesaplar. Listede olmayan dosya, eksik veya fazla altın dosya ya da yanlış özet testi düşürür.

`operator-console/tests/contract-fixtures.test.ts` (`corepack pnpm run test`) her altın cevabı konsolun gerçek okuyucusundan geçirir. Önce `strictJson` çalışır, profil adaptörün o route için seçtiğidir. Sonra `normalizeTimelinePage` ve `normalizeDeviceDetail` çalışır. Altın cevap değişmeden kabul edilmelidir. Bozulmuş kopyaları reddedilmelidir: eksik zorunlu alan, yanlış tür, bilinmeyen enum değeri, fazladan anahtar, yükseltilmiş güven iddiası.

## Yeniden üretme

Yük eklemek veya değiştirmek için:

1. Dosyayı doğru dizine yazın: `events/v2/valid/...` ya da `snapshots/v3/invalid/...`.
2. Kararını `expectations.json`'a ekleyin.
3. Platform testini yeniden üretme kipinde çalıştırın. Altın dosyalar ve `manifest.json` yeniden yazılır; artık kabul edilmeyen bir yükün eski altın dosyası silinir:

   ```sh
   SP_REGENERATE_CONTRACT_GOLDENS=1 python -m pytest -p no:cacheprovider -q tests/integration/test_contract_fixtures.py
   ```

4. Testi bir kez de normal kipte çalıştırın; karşılaştırma geçmelidir.
5. Konsol testini çalıştırın: `cd operator-console && corepack pnpm run test`.

Yeniden üretme kipi kararları da denetler. Platform bir yüke beklenenden başka karar verirse test iki kipte de düşer ve `expectations.json` değişmez. Bu README de manifest'te listelenir; README'yi değiştirdikten sonra 3. adımı yeniden çalıştırın.

## Ajan deposu bunu nasıl kullanacak

Bu tur ajan tarafını kapsamaz. Plan (Round 2 kararı B.4):

- Ajan deposu bu ağacın bir kopyasını taşır veya Platform deposundan okur. Önce `manifest.json` içindeki her sha256'yı doğrular.
- Ajan testi, ajanın kendi ürettiği gövdeleri ve kendi test derlemlerini manifest'teki `valid` yüklerle karşılaştırır. Aynı sürüm ve tür için ajanın gönderdiği her alan sözleşmede olmalıdır.
- Ajan kendi doğrulamasıyla her `invalid` yükü de reddetmelidir. Böylece ajan Platform'un reddedeceği bir gövdeyi kuyruğa koymaz.
- `cursor` taşıyan 409 vakaları, ajanın 409 alınca batch'i bekletme davranışını sınamak için kullanılabilir.
- İki depoyu birlikte çalıştıran CI işi, sahibinden bir token gerektirir; o iş açık kalır.

Ajan A1 commit'i yapıldıktan sonra bu test yazılacaktır. Fikstürler değişirse manifest'in özetleri de değişir; ajan testi eski kopyayı bu sayede fark eder.
