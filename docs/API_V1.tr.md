# API V1 sözleşmesi

Temel adres dağıtım yöneticisinin seçtiği HTTPS origin'idir. Uygulama 17 operation sunar; signup, komut, policy push, shell veya scan endpointi yoktur. Gerçek `app.openapi()` çıktısı [openapi.json](openapi.json) dosyasındadır. Public `/docs`, `/redoc` ve `/openapi.json` yolları kapalıdır; statik dosya inceleme içindir. Route/spec eşitliği entegrasyon testinde denetlenir.

## Üç bearer türü

| OpenAPI scheme | Kaynak ve yetki |
|---|---|
| `OperatorAccessToken` | Güvenilir IdP'nin RS256 API erişim token'ı. Tenant rolü güncel DB üyeliğinden gelir. |
| `EnrollmentGrant` | `spg_` + 43 base64url karakter; yalnız tek kullanımlık cihaz kaydı. |
| `DeviceCredential` | `spd_` + 43 base64url karakter; tek tenant ve cihaza bağlı snapshot, olay gönderimi ve rotasyon. |

Hepsi `Authorization: Bearer ...` başlığı kullanır, fakat birbirinin yerine geçmez. `X-Device-ID`, `X-Tenant-ID`, `X-Client-Cert` veya body alanı credential'ın bağlı olduğu cihazı değiştirmez. Enrollment ve device sırları 32 rastgele bayttır; DB'de SHA256 digest saklanır. Başarılı grant/enroll/rotate cevabı sırın gerekli tek seferlik gösterimidir; cevabı loglamayın. Cevaplarda `Cache-Control: no-store` bulunur.

Operatör profili:

- Algoritma yalnız `RS256`; `typ=at+jwt` veya `application/at+jwt`.
- Zorunlu `iss`, `aud`, `sub`, `exp`, `iat`, `jti`, `client_id`; `nbf` varsa doğrulanır.
- Issuer ve audience dağıtım ayarından tam eşleşir. Zaman alanları strict integer, tolerans 30 saniye; `0 < exp-iat <= 3600`.
- `sub` en fazla 256, `client_id` ve `jti` en fazla 128 karakterdir. Yerel üyelik CLI'ında subject sınırı 255'tir; üyelik için bu dar sınır kullanılmalıdır.
- `kid` yalnız başlangıçta okunan sabit public JWKS anahtarlarından seçilir. JWKS en fazla 64 KiB/16 RSA anahtarıdır; anahtarlar 2048–8192 bit, `use=sig`, `alg=RS256`, varsa `key_ops=[verify]` olmalıdır. Private key alanları reddedilir.
- `jku`, `x5u`, gömülü `jwk`, `crit`, `b64` başlıkları reddedilir. Token verisiyle discovery/key URL isteği yapılmaz.

JWKS yenilemesi: yöneticinin doğruladığı dosyaya eski+yeni public anahtarları benzersiz `kid` ile yerleştirin, dosyayı atomik değiştirin ve servisi yeniden başlatın. Yeni anahtar kullanımını doğrulayın; eski token süresi ve toleransı tamamlanınca eski anahtarı kaldırıp yeniden başlatın. Dosya değişikliği çalışan verifier'ı kendiliğinden yenilemez. Üretim IdP burada kurulmaz; fixture issuer üretim sağlayıcısı değildir.

## Endpointler

| Yöntem/yol | Aktör | Body ve sonuç |
|---|---|---|
| `GET /livez` | Kimliksiz operasyon | `200 {status:alive}`; HTTPS/Host sınırları devam eder. |
| `GET /readyz` | Kimliksiz operasyon | DB bağlantısı hazırsa `200 {status:ready}`, aksi halde 503. Runtime rolü ayrıca startup'ta doğrulanır. |
| `GET /api/v1/tenants` | Operatör | Yalnız güncel üyelikler; `items`, `next_offset`. |
| `POST /api/v1/tenants/{tenant_id}/enrollment-grants` | Tenant admin | `{}` veya `ttl_seconds`; 201: `grant_id`, `tenant_id`, `enrollment_token`, `expires_at`. |
| `POST /api/v1/tenants/{tenant_id}/enrollment-grants/{grant_id}/revoke` | Tenant admin | Boş body/`{}`; `grant_id`, `revoked:true`. Tüketilmiş hak 409. |
| `GET /api/v1/tenants/{tenant_id}/devices` | Tenant viewer/admin | Sınırlı liste; tenant kapsamı zorunlu. |
| `GET /api/v1/tenants/{tenant_id}/devices/{device_id}` | Tenant viewer/admin | Cihaz, son ürünler (ajanın kendi durumu `edr_agent` dahil), eksik ürünler ve ayrı kaynak/bağlantı yaşları. |
| `GET /api/v1/tenants/{tenant_id}/devices/{device_id}/events` | Tenant viewer/admin | Cihazın kendi beyanı olan olaylar; en yeni önce, `before_seq` ile anahtar tabanlı sayfa: `items`, `next_before_seq`, `cap_deleted_events`, `suppressed_alerts`. |
| `GET /api/v1/tenants/{tenant_id}/alerts` | Tenant viewer/admin | Kural uyarıları; en son etkinlik önce, `before_seen_at` + `before_id` ile anahtar tabanlı sayfa, isteğe bağlı `status` ve `device_id`: `items`, `next_before`. |
| `POST /api/v1/tenants/{tenant_id}/alerts/{alert_id}/acknowledge` | Tenant admin | Boş body/`{}`; `open` → `acknowledged`, cevap uyarının `AlertView`'i. Kapalı uyarı 409. |
| `POST /api/v1/tenants/{tenant_id}/alerts/{alert_id}/close` | Tenant admin | Boş body/`{}`; `open` veya `acknowledged` → `closed`, cevap uyarının `AlertView`'i. |
| `POST /api/v1/tenants/{tenant_id}/devices/{device_id}/revoke` | Tenant admin | Boş body/`{}`; bütün cihaz credential'larını etkisizleştirir. |
| `GET /api/v1/tenants/{tenant_id}/audit` | Tenant admin | Bounded başarılı yönetim olayları; sır veya ham payload içermez. |
| `POST /api/v1/enroll` | Enrollment grant | `{label:"..."}`; 201: `tenant_id`, `device_id`, `credential_id`, `credential_secret`, `credential_expires_at`. |
| `PUT /api/v1/device/snapshot` | Device credential | Strict V1 veya V2 snapshot (`schema_version` 1 ya da 2); 200 kabul cevabı. |
| `POST /api/v1/device/events` | Device credential | Strict `altay-edr-event/v1` olay batch'i; 200 kabul cevabı. |
| `POST /api/v1/device/credentials/rotate` | Device credential | `{}` veya `ttl_seconds`; yeni credential cevabı (süre yapılandırılmış credential süresini aşmaz), eski sır aynı transaction'da iptal edilir. |

Liste yolları `limit=1..100` (varsayılan 50), `offset=0..10000` alır ve offset sayfalaması kullanır. İki istisna offset yerine anahtar tabanlı sayfalanır (aşağıda): olay zaman çizelgesi (`before_seq`) ve uyarı listesi (`before_seen_at` + `before_id`). Liste ve detay aynı tenant üyeliğini uygular. Bilinmeyen extra body alanları reddedilir.

Kayıt hakkı varsayılanı 600 saniye, API üst sınırı 3600 saniyedir; yapılandırılmış daha dar üst sınır da uygulanır. Credential süresi `SP_CREDENTIAL_TTL_SECONDS` ile ayarlanır (60–2592000, varsayılan 86400). Rotasyon body aralığı 60–2592000 saniyedir, fakat verilen süre yapılandırılmış credential süresiyle sınırlanır: daha uzun istek bu değere indirilir, daha kısa istek olduğu gibi uygulanır; gerçek süre cevaptaki `credential_expires_at` alanıdır. Snapshot credential süresini uzatmaz; süresi dolmuş credential rotasyon yapamaz (401). Yeni cihaz ilk snapshot'a kadar `never_seen` kalır. Enrollment veya rotasyon commit'inden sonra cevap kaybolursa plaintext sır yeniden üretilemez; yönetici cihazı iptal edip yeni grant ile kayıt yaptırır.

Tenant cihaz kotası (`SP_MAX_DEVICES_PER_TENANT`, varsayılan 1000) yalnız iptal edilmemiş (aktif) cihazları sayar. İptal edilen cihaz satırı geçmiş olarak kalır, fakat kota yeri tutmaz; iptal + yeniden kayıt kurtarması tenant'ı kilitlemez. İptal edilmiş satırları silen bir komut yoktur.

Audit kaydı tenant başına sınırlıdır (`SP_MAX_AUDIT_EVENTS_PER_TENANT`, varsayılan 10000). Sınıra ulaşıldığında yeni olay cihazdan geliyorsa önce en eski cihaz olayı silinir; cihaz olayı kalmamışsa en eski olay silinir. Yönetim olayları (`operator`, `local_admin`) her zaman en eski olayı siler. Toplam sınır değişmez; tekrarlanan cihaz rotasyonları yönetim geçmişini silemez.

## Snapshot zarfı

```json
{
  "schema_version": 1,
  "message_id": "00000000-0000-4000-8000-000000000001",
  "sequence": 1,
  "source_observed_at": null,
  "products": [
    {
      "product_id": "hostbasedfirewall",
      "status": "unknown",
      "source": "self_reported",
      "producer_verification": "not_verified",
      "firewall_mode": "unknown"
    },
    {
      "product_id": "antivirus",
      "status": "planned",
      "availability": "unavailable",
      "execution_available": false
    }
  ]
}
```

`schema_version` strict integer `1` veya `2`'dir (Snapshot V2, Aşama 2 adım 3; ADR 0003 §5). İki sürüm aynı uç noktayı ve aynı gövdeyi kullanır; V2 yalnız Altay EDR ajanının kendi durumu olan `edr_agent` ürününü ekler. `sequence` iki sürümde de strict integer `1..2^53-1`'dir (`9007199254740991`); `message_id` lower-case kanonik UUID'dir. UTC metni `YYYY-MM-DDTHH:MM:SS[.fraction]Z` biçiminde doğrulanıp normalize edilir. Ürünler benzersizdir: V2'de en fazla dört (`hostbasedfirewall`, `termivar`, `antivirus`, `edr_agent`); V1'de eskisi gibi en fazla üç ve `edr_agent` yalnız `schema_version=2` ile kabul edilir (V1'de 422). Boş liste kabul edilir ve önceki ürün satırlarını kaldırır; detayda eksik ürünler `missing_products` ile bildirilir. Ajanı olmayan bir cihazın detayı `edr_agent`'ı eksik listeler.

**V1 için sıkılaştırma.** Snapshot V2 iki kuralı V1 için de daraltır. Birincisi `sequence`: üst sınır önceden `2^63-1` idi; Snapshot V2 ile iki sürümde de `2^53-1`'dir. Operatör konsolu yalnız `2^53-1`'e (`Number.MAX_SAFE_INTEGER`) kadar tamsayı okur ve cihaz listesi `last_sequence` değerini taşır; daha büyük bir sıra o kaydı taşıyan cihaz listesi sayfasını ve cihaz ayrıntısını okunamaz yapardı. Artık böyle bir snapshot diğer sözleşme ihlalleri gibi 422 alır ve hiçbir şey yazılmaz. Dürüst bir gönderici bu sınıra yaklaşmaz; numarası `2^53-1`'e ulaşan bir cihazın kurtarması yeniden kayıttır. `contracts.MAX_SEQUENCE` (`2^63-1`) diğer kullanıcıları için (olay `batch_sequence`, zaman çizelgesinin `before_seq` parametresi) değişmez. İkincisi zarfın `source_observed_at` değeridir: `null` değilse, normalize edilmiş değer olay `observed_at`'i gibi `1970-01-01T00:00:00Z <= source_observed_at < 9999-01-01T00:00:00Z` aralığında olmalıdır; dışındaki değer iki sürümde de 422 alır ve hiçbir şey yazılmaz. Değer `devices.source_observed_at` (`timestamptz`) sütununda saklanır. PostgreSQL bu sütunu oturumun saat diliminde döndürür ve Python sürücüsü 9999'dan sonraki veya 1'den önceki yılı okuyamaz. Bu aralığın dışındaki bir an UTC dışındaki bir oturumda bu yılların dışına düşebilir: kabul edilmiş bir `9999-12-31T23:59:59Z`, UTC'nin doğusundaki bir oturumda (ör. Europe/Bucharest) 10000 yılına düşer ve o cihazın satırını okunamaz yapardı; o cihazı taşıyan cihaz listesi sayfası, cihaz ayrıntısı, cihazın sonraki istekleri ve operatörün iptali 503 alırdı. Ürünlerin kendi `source_observed_at` ve `agent_started_at` değerleri JSONB yükünde metin olarak saklanır, her saat diliminde okunur ve bu aralıkla sınırlanmaz. Gerçek göndericiler bu aralığın dışına çıkmaz: Altay EDR ajanı yalnız bu aralıktaki anları gönderir, HBF göndericisi zarfta `null` gönderir. `sequence` değeri en çok `2^53-1` olan ve zarf `source_observed_at` değeri `null` ya da bu aralıkta olan, daha önce geçerli her V1 gövdesi aynı kanonik JSON ve özetle geçerli kalır (`tests/unit/test_snapshot_v2_contracts.py` bilinen iki V1 gövdesinin özetini sabitler).

V2 örneği (ajanın servis döngüsü, sensörsüz çalışma):

```json
{
  "schema_version": 2,
  "message_id": "00000000-0000-4000-8000-000000000003",
  "sequence": 8,
  "source_observed_at": "2030-01-01T00:00:00.000000Z",
  "products": [
    {
      "product_id": "edr_agent",
      "status": "running",
      "version": "0.3.0",
      "source_observed_at": "2030-01-01T00:00:00.000000Z",
      "agent_started_at": "2029-12-31T22:00:00.000000Z",
      "engine_id": "edr-agent/0.3.0",
      "rule_file_present": false,
      "sensor_state": "disabled",
      "sensor_error_code": null,
      "events_queue_dropped": 0, "events_write_failed": 0, "events_unmapped": 0, "events_skipped": 0,
      "events_evicted": 0, "events_discarded": 0, "events_degraded": 0, "outbox_backlog": 0
    }
  ]
}
```

| Ürün | Alanlar ve yorum |
|---|---|
| Ortak | `catalog_available`, `version`, `source_observed_at`; gözlenmeyen değer `null`/`unknown`. `source=self_reported`, `producer_verification=not_verified` sabittir. Sürüm en fazla 64 güvenli karakterdir. |
| HostBasedFirewall | `status`, `installed`, `reported_running`, `reported_stale`, `firewall_mode=enforce|sniff|unknown`, kapalı listeden en fazla 16 benzersiz `error_codes`. Merkezin enforcement doğrulaması değildir. |
| Termivar Web | `status=experimental|unknown`, `scanner_installed`, `execution_available`, `report_presence=present|none|unknown`, `latest_report`. Çalıştırma iddiası `true` olamaz. Rapor varlığı scanner kurulumunu kanıtlamaz. |
| Antivirüs | `status=planned|unknown`, `availability=unavailable|unknown`; aktif katalog/çalıştırma veya sürüm iddiası reddedilir. |
| Altay EDR ajanı (`edr_agent`, yalnız V2) | Ajanın kendisi hakkında söyledikleri; tamamı `self_reported`/`not_verified`. Ayrıntı aşağıda. |

**`edr_agent` alanları** (alan sırası önemsizdir; Platform ayrıştırılmış modeli kanonikleştirir):

| Alan | Tür ve varsayılan | Anlamı |
|---|---|---|
| `status` | `running` veya `unknown` (varsayılan `unknown`) | `running` yalnız ajanın servis döngüsünün bunu bildirdiğini söyler. |
| `version` | ortak sürüm metni veya `null` | Ajan sürümü. |
| `source_observed_at` | UTC metni veya `null` | Ajanın bu durumu oluşturduğu an (cihaz saati). |
| `agent_started_at` | UTC metni veya `null` | Ajan sürecinin başlangıcı; mikrosaniyeyle normalize edilir. |
| `engine_id` | 1–128 karakter ASCII `^[A-Za-z0-9][A-Za-z0-9._+/ -]*$` veya `null` | Motor kimliği. |
| `rule_file_present` | boolean veya `null` | Yalnız kural dosyasının var olup olmadığı. Kuralların yüklendiği iddiası değildir; servis Aşama 2'de kural yüklemez. |
| `sensor_state` | `started`, `lost`, `failed`, `stopped`, `disabled`, `unknown` (varsayılan `unknown`) | `disabled`: servis sensörsüz çalışıyor (`--no-sensor`). |
| `sensor_error_code` | olay sözleşmesinin altı kodu veya `null` | Yalnız `sensor_state` `lost` ya da `failed` iken dolu olabilir; aksi 422. |
| `events_queue_dropped`, `events_write_failed`, `events_unmapped`, `events_skipped`, `events_evicted`, `events_discarded`, `events_degraded`, `outbox_backlog` | strict integer `0..2^53-1` veya `null` | Ajan sürecinin başlangıcından beri sayaçlar ve giden kutusu birikimi. Boolean sayı değildir; ajan sınırda doyurur. `null`, değerin bildirilmediğidir (ör. tek seferlik `edr-agent heartbeat` komutu), sıfır değildir. |

`catalog_available` `null` olmalıdır: ajan katalog iddiası taşımaz. `source` ve `producer_verification` sabittir. Başka her anahtar (ör. koruma, gerçek zamanlı koruma veya yüklenmiş kural iddiası) `extra=forbid` ile 422 alır. Bu ürün hiçbir zaman "koruma aktif", "gerçek zamanlı koruma" veya "kurallar yüklü" anlamına gelmez. Cihaz detayında görünümü diğer ürünler gibidir: `product_id`, `snapshot_sequence`, `received_at`, `observation` (ajanın `source_observed_at` değerine göre yaş) ve kanonik yükün kendisi olan `state`.

Termivar Web `latest_report` yalnız digest, sabit rapor şeması, yerel `imported_at`, konu/kayıt sayıları, disposition ve severity sayıları, sabit kaynak/doğrulama/scope alanlarını içerir. `subject_count=1..1024`, `item_count` ve her sayaç `0..4096`; boolean sayı değildir. Her iki sayı grubunun toplamı `item_count` olmalıdır. `present` ile özet varlığı tutarlı olmalıdır. Ham hedef/URL/IP, kanıt, HTML, komut veya serbest metadata alanı yoktur.

200 kabul cevabı:

```json
{"accepted":true,"message_id":"00000000-0000-4000-8000-000000000001","sequence":1,"received_at":"2030-01-01T00:00:00Z"}
```

Sunucu `received_at` atar. Son mesaj aynı sıra/UUID/kanonik içerikle tekrarlanırsa aynı cevap döner ve tazelik yenilenmez. Son sıra veya son UUID farklı içerikle 409; eski sıra 409'dur. V1 yalnız son kabulün retry penceresini tutar; bütün tarihsel mesaj UUID'leri için sınırsız tombstone deposu yoktur. Daha yüksek sıra önceki tam ürün durumunu atomik değiştirir. Credential rotasyonu cihazın son sırasını korur. Bu kurallar V1 ve V2 için ortaktır ve sıra iki sürümde tek sayaçtır: V1'den sonra V2 (ya da tersi) yalnız daha yüksek sırayla kabul edilir; aynı sıra ve UUID'nin yalnız `schema_version`'ı farklı gönderilmesi farklı içeriktir ve 409 alır. Daha yüksek sıralı bir V1 mesajı ajanın `edr_agent` durumunu da kaldırır.

## Olay batch'i (`altay-edr-event/v1`)

`POST /api/v1/device/events` yalnız cihaz credential'ı kabul eder. Tenant ve cihaz yalnız bu credential'dan gelir; gövdede kimlik alanı yoktur ve bilinmeyen her alan reddedilir (422).

```json
{
  "schema_version": 1,
  "batch_id": "00000000-0000-4000-8000-000000000002",
  "batch_sequence": 1,
  "events": [
    {"kind": "process_started", "event_seq": 1, "observed_at": "2030-01-01T00:00:00.000001Z",
     "pid": 4321, "parent_pid": 1234, "session_id": 1,
     "image": "\\Device\\HarddiskVolume3\\Users\\*\\Downloads\\setup.exe"},
    {"kind": "process_stopped", "event_seq": 2, "observed_at": "2030-01-01T00:00:05.000000Z",
     "pid": 4321, "exit_code": 0, "image": "setup.exe"},
    {"kind": "sensor_state", "event_seq": 3, "observed_at": "2030-01-01T00:00:06.000000Z",
     "state": "lost", "error_code": "session_in_use"}
  ]
}
```

- `schema_version` strict integer `1`; `batch_id` lower-case kanonik UUID; `batch_sequence` strict integer `1..2^63-1`.
- `events` 1–200 olaydır ve `kind` alanına göre ayrılır. `event_seq` ajanın giden kutusundaki kayıt numarasıdır; strict integer `1..2^53-1`'dir (`9007199254740991`) ve batch içinde kesin artar. Numaralardaki boşluk, olayların cihazda kaybolduğunu gösterir (kuyruk taşması, giden kutusundan atılan kayıt, okunamayan veya eşlenemeyen kayıt). Bir cihazın ilk batch'inde `batch_sequence` ve ilk `event_seq` 1'den büyük veya eşit herhangi bir değer olabilir (ör. yeniden kayıttan sonra kayıt numaraları kaldığı yerden sürer).
- **`event_seq` üst sınırı `2^53-1`:** operatör konsolunun tam okuyabildiği en büyük tamsayıdır (`Number.MAX_SAFE_INTEGER`); konsol daha büyük bir tamsayı içeren yanıtın tamamını sözleşme hatası sayar. Daha büyük bir `event_seq` taşıyan batch, diğer sözleşme ihlalleri gibi bütünüyle 422 alır: hiçbir olayı saklanmaz, hiçbir kural çalışmaz, imleç ilerlemez. Böylece Platform'un `event_seq`'ten türettiği sayılar da konsolun aralığında kalır: zaman çizelgesindeki `event_seq` ve `next_before_seq`, uyarının `first_event_seq`/`last_event_seq` değerleri ve `missing_events` (bir cihazın kesin artan numaraları arasındaki boşlukların birikimli toplamı, en çok `2^53-3`). `batch_sequence` ve zaman çizelgesinin `before_seq` parametresi `1..2^63-1` kalır; snapshot `sequence` Snapshot V2'den beri `1..2^53-1`'dir (yukarıda). Numarası `2^53-1`'e ulaşmış bir cihazın sonraki her batch'i 422 alır; kurtarma yeniden kayıttır. Ajanın numaraları pratikte bu sınıra ulaşmaz.
- `observed_at` cihaz saatidir ve doğrulanmaz. Snapshot'taki UTC metin kuralı geçerlidir: yalnız `Z`, en çok 6 kesir hanesi; değer mikrosaniyeyle normalize edilip saklanır. Normalize edilmiş değer `1970-01-01T00:00:00Z <= observed_at < 9999-01-01T00:00:00Z` aralığında olmalıdır; dışındaki değer 422 alır. PostgreSQL zamanı oturumun saat diliminde döndürür ve Python sürücüsü 9999'dan sonraki veya 1'den önceki yılı okuyamaz; bu aralıktaki her an her saat diliminde okunur, böylece tek bir olay zaman çizelgesini okunamaz hâle getiremez. Veritabanı aynı sınırı `ck_endpoint_event_observed_at` CHECK kısıtıyla uygular.

| Tür | Alanlar |
|---|---|
| `process_started` | `pid`, `parent_pid`, `session_id` (`0..4294967295`). `image`: çekirdeğin bildirdiği 1–1024 karakterlik süreç görüntüsü yolu; kontrol veya Unicode biçim karakteri (ör. yön değiştirme, sıfır genişlik) içermez. Yol ayırıcısı zorunlu değildir: `Registry` gibi yalın bir ad da kabul edilir. |
| `process_stopped` | `pid`, `exit_code` (`0..4294967295` veya `null`). `image`: `null` ya da 1–260 karakterlik kısa süreç adı; `\`, `/`, kontrol veya biçim karakteri içeremez (aşağıdaki ajan dönüşümü). |
| `sensor_state` | `state`: `started`, `lost`, `failed`, `stopped`. `error_code`: `null` ya da `session_name_invalid`, `session_in_use`, `access_denied`, `session_start_failed`, `session_stop_failed`, `unknown`; `started` ve `stopped` için `null` olmalıdır. |

Reddedilen kontrol ve biçim karakterleri Unicode 16.0.0'ın Cc ve Cf genel kategorileridir. Küme sabit bir kod noktası tablosudur (`event_contracts.REFUSED_TEXT_RANGES`); sunucudaki Python'un Unicode veritabanından okunmaz. Böylece bir Python yükseltmesi, ajanın geçerli saydığı olayları sessizce reddetmeye başlayamaz. Çalışan yorumlayıcının veritabanı bu tablodan farklıysa birim testi başarısız olur.

`null` olabilen alanlar (`exit_code`, kısa `image`, `error_code`) gövdede yazılmazsa `null` sayılır. Komut satırı, kullanıcı adı veya SID, dosya içeriği veya özeti, ağ verisi ve serbest metin alınmaz.

**Kısa süreç adı (`process_stopped.image`):** çekirdeğin kısa adı dosya adındaki her UTF-16 biriminin yalnız düşük baytını tutar. Bu yüzden Kiril, Arapça, CJK veya Hangul adlarda `\` ya da `/` baytı oluşabilir (ör. `Яндекс.exe` → `/=45:A.exe`, `桜.exe` → `\.exe`) veya ad boş kalabilir. Ajan göndermeden önce kısa addaki her `\` ve `/` karakterini U+FFFD (`�`) ile değiştirir (`�=45:A.exe`, `�.exe`); sonuç boşsa `null` gönderir. Platform ayırıcı içeren kısa adı reddeder (422): bu yasak, maskelenmemiş bir tam yolun kısa ad alanında taşınmasını engeller.

**Gizlilik kuralı (sözleşmede zorunlu):** `process_started.image` `\` ve `/` işaretlerinden bileşenlere ayrılır (Win32 `/` işaretini de ayırıcı sayar). Bütünüyle `Users` olan (ASCII, büyük/küçük harf duyarsız) ve son bileşen olmayan her bileşenden sonraki bileşenin ilk `:` işaretinden önceki kısmı tam olarak `*` olmalıdır. İlk `:` işaretinden sonrası (NTFS akış adı) ve sonraki bileşenler korunur. `Users` ile biten yolda maskelenecek bir şey yoktur. `Users:akış` bir `Users` bileşeni değildir; akışın alt bileşeni olmaz.

- Kabul: `\Device\HarddiskVolume3\Users\*\Downloads\setup.exe`, `\Device\HarddiskVolume3\Users\*:payload.exe`, `\Users\*`, `\Users\*:`, `Registry`.
- Ret (422): `\Device\HarddiskVolume3\Users\ahmet\Downloads\setup.exe`, `\Users\ahmet:payload.exe`, `\Users\**`, `\Users\*x:y`, `\Users\:x`, `\Users\` (ardından boş bileşen).
- Bilinen sınır: kural `Users` altındaki bir dosyayı profil klasöründen ayıramaz. Doğrudan `Users` altındaki dosyanın adı da `*` olarak maskelenir: `\Users\setup.exe` → `\Users\*`, akışıyla `\Users\setup.exe:x` → `\Users\*:x`.

Ajan göndermeden önce maskeler, Platform maskelenmemiş yolu reddeder. Bu bir sözleşme kuralıdır, veri sızıntısı önleme (DLP) değildir. Yalnız bütünüyle `Users` olan bileşenden hemen sonraki ad (ilk `:` öncesi) denetlenir. NTFS akış adı (`\Users\*:payload.exe`) tespit için korunur ve kişisel bilgi taşıyabilir. Klasör veya dosya adlarındaki kişisel bilgi, profil dışı konumlar (ör. `D:\ahmet\araç.exe`), Win32'nin eşdeğer saydığı başka yazımlar (sondaki nokta/boşluk, `Users::$INDEX_ALLOCATION` gibi akış nitelikli dizin yazımları, ASCII olmayan büyük/küçük harf eşdeğerleri) ve maskeyi uygulamayan kötü niyetli bir ajan tanınmaz. Ayrıntı [tehdit modelindedir](THREAT_MODEL.tr.md).

**Güven:** her olay `source=self_reported` ve `producer_verification=not_verified` kalır. Batch güven iddiası taşıyamaz, sunucu bu değerleri hiçbir zaman yükseltmez. Olaylar cihazın heartbeat'ini ve snapshot tazeliğini yenilemez: cihaz listesindeki ve detayındaki `last_received_at`, `connection_status` ve kaynak yaşı yalnız snapshot ile değişir; yalnız olay gönderen cihaz `never_seen` veya `stale` kalır. Olay alımı audit kaydı yazmaz.

**Kanonik biçim ve sınırlar:** içerik özeti snapshot'taki gibi hesaplanır: normalize edilmiş model, sıralı anahtarlar, boşluksuz ayırıcılar, UTF-8 ve SHA256. Kanonik biçim en çok 16 KiB olabilir. Normalizasyon (mikrosaniye, açık `null`) gövdeyi büyüttüğü için 16 KiB'lık gövdeye sığan bir batch bu sınırı aşabilir; o zaman `413 {"detail":"Event batch too large"}` döner. Her olayın PostgreSQL'de saklanan JSONB metni de en çok 4096 bayttır; aşan olay 422 alır (1024 karakterlik bir yol dört baytlık karakterlerle bu sınırı geçebilir). Genel gövde sınırları (16 KiB, 2048 düğüm, dakikada 120 istek) aynen geçerlidir.

200 kabul cevabı (4 KiB'a sığar):

```json
{"accepted":true,"batch_id":"00000000-0000-4000-8000-000000000002","batch_sequence":1,"last_event_seq":3,"received_at":"2030-01-01T00:00:10Z"}
```

`received_at` sunucu zamanıdır ve snapshot cevabındaki gibi yazılır. Ajan aynı anda yalnız bir batch gönderir (dur ve bekle). Tekrar oynatma kuralları cihaz başına tek imleçle uygulanır:

- Son batch aynı `batch_sequence`, `batch_id` ve kanonik içerikle tekrarlanırsa saklanan aynı cevap döner; satır eklenmez, `received_at` yenilenmez.
- Aynı `batch_sequence` veya aynı `batch_id` farklı içerikle gelirse 409 (`Event batch identity or sequence conflicts with current state`).
- Son kabulden küçük `batch_sequence` 409 (`Event batch sequence is stale`).
- İlk `event_seq` son kabul edilen `last_event_seq`'ten büyük değilse 409 (`Event sequence does not follow the last accepted event`).

Olay batch'inin her 409 cevabı cihazın imlecini taşır: `last_batch_sequence` son kabul edilen batch'in sırası, `last_event_seq` son kabul edilen olayın sırasıdır. Bu iki alan tanı içindir. Ajan 409 alınca bekleyen batch'i korur, aynı baytları daha sonra yeniden dener ve bunu kaydeder; imlece göre kendiliğinden ilerlemez. Kurtarma, heartbeat'te olduğu gibi cihazın yeniden kaydıdır. Bir sonraki batch'in kabul edilmesi için `batch_sequence` değeri `last_batch_sequence`'ten, ilk `event_seq` değeri `last_event_seq`'ten büyük olmalıdır. Diğer yolların 409 gövdesi yalnız `detail` içerir.

```json
{"detail":"Event sequence does not follow the last accepted event","last_batch_sequence":5,"last_event_seq":11}
```

İmleç cihaza aittir; credential rotasyonu onu sıfırlamaz. PostgreSQL'de (`tenant_id`, `device_id`, `event_seq`) birincil anahtardır.

**`POST /api/v1/device/events` durum kodları:**

| HTTP | Gövde ve anlam |
|---|---|
| 200 | Kabul veya son batch'in tam tekrarı (aynı cevap). |
| 400 | Yalnız istek sınırı: geçersiz/tekrarlı JSON, düğüm/derinlik bütçesi, başlık veya HTTPS gereksinimi (ör. `{"detail":"invalid_json"}`). |
| 401 | Eksik, yanlış amaçlı, süresi geçmiş, iptal edilmiş veya geçersiz cihaz credential'ı. |
| 409 | Tekrar oynatma kuralı ihlali; gövde `{"detail","last_batch_sequence","last_event_seq"}` (imleç alanları tanı içindir; ajan batch'i bekletir, kurtarma yeniden kayıttır). |
| 413 | Gövde 16 KiB'ı aşıyor (`{"detail":"request_too_large"}`) veya şemaya uyan batch'in kanonik biçimi 16 KiB'ı aşıyor (`{"detail":"Event batch too large"}`). |
| 415 | JSON olmayan veya sıkıştırılmış gövde. |
| 422 | Sözleşmeye uymayan gövde (`{"detail":"invalid_request"}`); servisin yeniden doğrulamasında bulunan sözleşme ihlali (`{"detail":"Invalid event batch"}`). Girdi geri döndürülmez. |
| 429 | İstek bütçesi. |
| 503 | DB kullanılamıyor; başarı uydurulmaz. |

**Cihaz başına üst sınır:** `SP_MAX_EVENTS_PER_DEVICE` (varsayılan 250000, aralık 1000–10000000). Sınır aşılınca aynı işlemde cihazın en eski satırları (en küçük `event_seq`) silinir. Bir istek en çok batch'teki olay sayısı + 5000 satır siler ve batch'in kendi olaylarını hiçbir zaman silmez (sınır en az 1000, batch en çok 200 olaydır). Sınır düşürülürse fazlası tek istekte değil, sonraki batch'lerde bu parçalar hâlinde silinir; ayrıntı [OPERATIONS.tr.md](OPERATIONS.tr.md) içindedir. Sınırın sildiği satırların tam sayısı cihaz imlecinde `cap_deleted_events` olarak birikir ve zaman çizelgesi cevabında döner (aşağıda); zamana göre saklama bu sayacı değiştirmez. Zamana göre saklama ayrı `security-platform events prune` komutudur; tenant başına gün ayarı ve günlük zamanlama da [OPERATIONS.tr.md](OPERATIONS.tr.md) içindedir.

## Cihaz olay zaman çizelgesi

`GET /api/v1/tenants/{tenant_id}/devices/{device_id}/events?before_seq=&limit=` tenant viewer ve admin içindir. Cihaz bu tenant'ta yoksa cihaz detayındaki gibi 404 döner. Sonuç en yeni olay önce sıralanır. Offset 10.000'de durduğu için sayfalama anahtar tabanlıdır: `before_seq` (dahil değil, `1..2^63-1`) ve `limit` (`1..100`, varsayılan 50). Sonraki sayfa için cevaptaki `next_before_seq` verilir; son sayfada değer `null` olur.

```json
{"items":[{"event_seq":3,"kind":"sensor_state","observed_at":"2030-01-01T00:00:06Z","received_at":"2030-01-01T00:00:10Z","state":"lost","error_code":"session_in_use","source":"self_reported","producer_verification":"not_verified"}],"next_before_seq":null,"cap_deleted_events":0,"suppressed_alerts":0}
```

Her öğe `event_seq`, `kind`, `observed_at`, `received_at`, türün alanları ve sabit `source`/`producer_verification` değerlerini içerir. Üst düzeydeki `cap_deleted_events`, cihaz başına üst sınırın bu cihazın satırlarından alış sırasında sildiği satırların toplamıdır; `events prune` ile zamana göre silinen satırlar bu sayıya katılmaz. `suppressed_alerts`, cihazın kapanmamış uyarı sınırı dolu olduğu için açılmayan uyarıların toplamıdır (aşağıda, "Uyarılar"). Cihazın henüz kabul edilmiş bir olay batch'i yoksa (imleci yoksa) iki değer de `0`'dır. Değerler sayfaya bağlı değildir ve sunucunun kendi sayımıdır, cihaz beyanı değildir. Operatör konsolu bu yolu cihaz ayrıntısındaki olay zaman çizelgesinde okur.

## Uyarılar

**Kural tespiti teşhis değildir.** Bir uyarı, cihazın kendi beyanı olan olayların yerleşik ve basit bir kurala uyduğunu söyler; kötü amaçlı yazılım, saldırı veya ihlal kanıtı değildir. Kötü niyetli bir cihaz kendi uyarılarını üretebilir veya bastırabilir ([tehdit modeli](THREAT_MODEL.tr.md)). Her uyarı, olaylar gibi `source=self_reported` ve `producer_verification=not_verified` kalır.

**Nerede çalışır.** Kurallar olay alımının içinde, aynı transaction'da ve yalnız yeni kabul edilen batch'in olayları için çalışır; olaylar ve uyarıları birlikte commit edilir ya da birlikte geri alınır. Son batch'in tam tekrarı, 409, 413 ve 422 hiçbir kural çalıştırmaz. Kurallar yalnız sözleşme alanlarını okur: saklanan maskeli görüntü yolu, pid'ler, tür, durum ve kodlar. Kullanıcı tanımlı kural yoktur.

| Kural | Önem | Eşleşme | Anahtar metni | `evidence` |
|---|---|---|---|---|
| `user_writable_launch` | `low` | Kullanıcının yazabildiği bir konumdan başlayan `process_started` | Görüntü yolu, casefold | `{"image","pid"}` |
| `office_browser_spawned_tool` | `medium` | Ofis uygulamasının veya tarayıcının başlattığı sistem aracı | `<üst dosya adı>><çocuk dosya adı>` | `{"image","pid","parent_image","parent_pid"}` |
| `sensor_unstable` | `medium` | `state` değeri `lost` veya `failed` olan `sensor_state` | Durum (`lost` / `failed`) | `{"state","error_code"}` |
| `event_loss` | `medium` | `event_seq` boşluğu | `event_loss` | `{"missing_events"}` |

- **`user_writable_launch`:** görüntü yolu `\` ve `/` işaretlerinden bileşenlere ayrılır; her bileşenin yalnız ilk `:` öncesi kısmı büyük/küçük harf duyarsız (Unicode casefold) karşılaştırılır. Bir `Users` bileşeninden sonra maskeli profil `*` ve ardından `AppData` veya `Downloads` geliyorsa, `Users`'tan hemen sonra `Public` geliyorsa ya da herhangi bir bileşen `Temp` ise eşleşir. `\Users\*\AppData\Local\x.exe`, `\Users\*:akış\Downloads\x.exe` ve `\Windows\Temp\x.exe` eşleşir; `\Windows\Temporary\x.exe`, `\Tools\temp.exe` ve `\Users\*\Documents\x.exe` eşleşmez. Ajan `Users\Public`'i de profil klasörü gibi maskeler (`Users\*`); bu yüzden `Public` dalı yalnız alışılmadık `Users` yazımlarında (ör. `Users:x`) çalışır ve `C:\Users\Public\Documents` gibi bir konum yakalanmaz.
- **`office_browser_spawned_tool`:** dosya adı (son bileşen, casefold, ilk `:` öncesi) `mshta.exe`, `regsvr32.exe`, `rundll32.exe`, `wscript.exe`, `cscript.exe`, `powershell.exe`, `pwsh.exe`, `cmd.exe`, `certutil.exe`, `bitsadmin.exe`, `msbuild.exe`, `installutil.exe`, `wmic.exe` veya `schtasks.exe` olan bir `process_started`. Üst sürecin dosya adı `winword.exe`, `excel.exe`, `powerpnt.exe`, `outlook.exe`, `msaccess.exe`, `mspub.exe`, `onenote.exe`, `visio.exe`, `chrome.exe`, `msedge.exe`, `firefox.exe`, `brave.exe`, `opera.exe` veya `iexplore.exe` olmalıdır. Üst süreç, aynı cihazın `pid == parent_pid` olan ve daha küçük `event_seq`'li en son `process_started` olayıdır; ikisinin arasında o pid'in `process_stopped` olayı olmamalıdır. pid yeniden kullanılmışsa en son başlangıç geçerlidir. Önce bu batch'e, sonra saklanan olaylara bakılır. Arama cihazın önceki 2000 `event_seq` değeriyle sınırlıdır (çocuk `n` ise `n−2000 … n−1`). Bu pencerenin dışındaki ya da zamana göre saklama veya cihaz başına üst sınır nedeniyle silinmiş bir üst süreç bulunmaz ve kural sessiz kalır.
- **`sensor_unstable`:** `lost` ve `failed` ayrı anahtarlardır. `occurrences` tekrarları ("tekrar tekrar düşme") sayar; `evidence` en son eşleşmenin durumu ve kodudur (kod `null` olabilir).
- **`event_loss`:** batch içinde ardışık iki olay arasında birden büyük fark ya da imlecin `last_event_seq` değeri ile batch'in ilk olayı arasındaki boşluk. Yalnız imleci olan cihazda çalışır: cihazın ilk batch'i 1'den büyük başlayabilir ve içindeki boşluklar kayıp sayılmaz. `occurrences` boşluk sayısı kadar artar; `missing_events` kayıp numaraların uyarı kapanana kadar birikimli toplamıdır.

**Tekilleştirme.** Bir (tenant, cihaz, kural, anahtar) için kapanmamış (`open` veya `acknowledged`) bir uyarı varken yeni eşleşme yenisini açmaz, onu günceller: `occurrences` eşleşme sayısı kadar artar, `last_event_seq` en yüksek eşleşen `event_seq`, `last_seen_at` bu batch'in `received_at` değeri olur, `evidence` en son eşleşmeninkiyle değişir (`missing_events` birikir), durum değişmez. Kapatılmış bir uyarıdan sonraki eşleşme yeni bir uyarı açar. `dedup_key`, anahtar metninin küçük harfli onaltılık SHA-256 özetidir. Batch'teki her farklı anahtar tek bir `INSERT … ON CONFLICT` deyimidir; kısmi tekil indeks (`status <> 'closed'`) anahtar başına kapanmamış tek uyarıyı garanti eder. Bir kapatma ile aynı anahtarın alımı yarışırsa sonuç ya kapalı uyarı ile yeni açık bir uyarı ya da eşleşmeyi içeren kapalı uyarıdır; iki kapanmamış uyarı veya hata olmaz.

**Kanıt sınırı.** `evidence` PostgreSQL'de en çok 4096 bayttır (`ck_alert_evidence_bytes`). Yalnız `office_browser_spawned_tool` iki olayın yolunu taşıdığı için bunu aşabilir; o zaman iki yol başlarından kısaltılır, önlerine `…` konur ve dosya adları korunur. Baştan kısaltma maskeli bir profil klasörünü açığa çıkarmaz.

**Cihaz başına sınır.** `SP_MAX_OPEN_ALERTS_PER_DEVICE` (varsayılan 500, aralık 10–100000): cihazın kapanmamış uyarı sayısı bu değere ulaşmışsa yeni bir uyarı açacak eşleşme hiçbir şey açmaz ve cihaz imlecindeki `suppressed_alerts` sayacı bir artar (batch ve anahtar başına bir). Mevcut uyarıların güncellenmesi hiçbir zaman bastırılmaz; onaylanmış uyarı da sınıra sayılır; kapatma yer açar. Sayaç olay zaman çizelgesi cevabında döner.

**Saklama yok.** Uyarılar bu adımda silinmez: runtime hesabının `alerts` üzerinde DELETE hakkı yoktur ve `events prune` uyarılara dokunmaz. Olayları silinmiş bir uyarı kalır; kanıtı uyarının kendi satırındadır.

### Uyarı listesi

`GET /api/v1/tenants/{tenant_id}/alerts` tenant'ın her üyesi (viewer veya admin) içindir. Sorgu parametreleri:

- `status`: isteğe bağlı; `open`, `acknowledged` veya `closed`.
- `device_id`: isteğe bağlı cihaz UUID'si. Cihaz bu tenant'ta yoksa (bilinmeyen ya da başka tenant'ın) olay zaman çizelgesindeki gibi 404.
- `limit`: `1..100`, varsayılan 50.
- `before_seen_at` ve `before_id`: anahtar tabanlı sayfa; ikisi birlikte verilir ya da hiç verilmez. `before_seen_at` tam altı kesir haneli UTC metnidir (`2030-01-01T00:00:10.000000Z`).

Sıra en son etkinlik öncedir: (`last_seen_at` azalan, `id` azalan). Aynı batch'in uyarıları aynı `last_seen_at` değerini paylaşır; eşitliği `id` bozar. Sonraki sayfa için cevaptaki `next_before` (`{"seen_at","id"}`) değerleri `before_seen_at` ve `before_id` olarak verilir; son sayfada `null` olur. İki sayfa okuması arasında yeni eşleşme alan bir uyarı başa geçer ve sonraki sayfalarda tekrar görünmez. Geçersiz parametre (tek başına cursor değeri, başka biçimde ya da var olmayan bir zaman, aralık dışı `limit`, bilinmeyen `status`) olay zaman çizelgesindeki gibi `422 {"detail":"invalid_request"}` alır. `offset` bir sayfalama denetimi değildir.

```json
{"items":[{"id":"00000000-0000-4000-8000-000000000003","device_id":"00000000-0000-4000-8000-000000000004","rule":"office_browser_spawned_tool","severity":"medium","status":"open","occurrences":2,"first_event_seq":41,"last_event_seq":57,"first_seen_at":"2030-01-01T00:00:10Z","last_seen_at":"2030-01-01T00:05:10.250000Z","evidence":{"image":"\\Device\\HarddiskVolume3\\Windows\\System32\\cmd.exe","pid":4400,"parent_image":"\\Device\\HarddiskVolume3\\Program Files\\Microsoft Office\\root\\Office16\\WINWORD.EXE","parent_pid":4321},"acknowledged_at":null,"closed_at":null,"source":"self_reported","producer_verification":"not_verified"}],"next_before":null}
```

**`AlertView`** anahtarları tam olarak `id`, `device_id`, `rule`, `severity`, `status`, `occurrences`, `first_event_seq`, `last_event_seq`, `first_seen_at`, `last_seen_at`, `evidence`, `acknowledged_at`, `closed_at`, `source` ve `producer_verification`'dır. `first_seen_at` ve `last_seen_at` eşleşen batch'lerin sunucu alım zamanıdır (`received_at`), cihaz saati değildir; zamanlar diğer cevaplardaki gibi yazılır. `evidence` kurala göre yukarıdaki anahtarları taşır. `acknowledged_at` ve `closed_at` geçiş zamanlarıdır, yoksa `null`. Onaylayan ve kapatan operatörün kimliği satırda tutulur, cevapta yoktur.

### Onaylama ve kapatma

`POST /api/v1/tenants/{tenant_id}/alerts/{alert_id}/acknowledge` ve `POST /api/v1/tenants/{tenant_id}/alerts/{alert_id}/close` yalnız `tenant_admin` içindir; rol cihaz iptalindeki gibi güncel üyelikten okunur (viewer 403). Body boş veya `{}`'dur; başka alan 422 alır. Geçiş için uyarı satırı kilitlenir. Cevap uyarının `AlertView`'idir.

| İstek | `open` uyarı | `acknowledged` uyarı | `closed` uyarı |
|---|---|---|---|
| `acknowledge` | `acknowledged` olur; audit `alert_acknowledged` | 200, değişmez, audit yok | `409 {"detail":"Alert is closed"}` |
| `close` | `closed` olur; audit `alert_closed` | `closed` olur; audit `alert_closed` | 200, değişmez, audit yok |

Bilinmeyen ya da başka tenant'ın uyarısı 404'tür. Audit satırı nesneyi `alert` türü ve uyarının kimliğiyle (`object_id`) adlandırır; kanıtı hiçbir zaman taşımaz. Audit tablosunda ayrıntı sütunu olmadığı için uyarının cihazı ve kuralı audit satırında değil, silinmeyen uyarı satırındadır. Konsol Aşama 2'de salt okunurdur; onaylama ve kapatma yalnız bu API ile yapılır.

## Hatalar ve sınırlar

| HTTP | Anlam |
|---|---|
| 400 | Geçersiz/tekrarlı JSON, yapı bütçesi, başlık/uzunluk veya HTTPS gereksinimi. |
| 401 | Eksik, yanlış amaçlı, süresi geçmiş, iptal edilmiş veya geçersiz credential. |
| 403 | Kendi tenant'ında yetersiz rol veya yabancı Origin. |
| 404 | Kaynak yok veya bu tenant üyeliğiyle görünmez. |
| 409 | Sıra/içerik çakışması, aşılmış mesaj veya olay batch'i, tüketilmiş grant iptali ya da kapalı uyarının onaylanması (`Alert is closed`). Olay batch'inin 409'u tanı için cihaz imlecini de (`last_batch_sequence`, `last_event_seq`) taşır. |
| 408 / 413 / 415 | Body süresi / boyut-parça sayısı veya kanonik biçimi 16 KiB'ı aşan olay batch'i (`Event batch too large`) / JSON olmayan veya sıkıştırılmış body. |
| 422 | DTO tipi, extra alan, geçersiz sorgu parametresi (ör. uyarı listesinin eksik veya bozuk cursor'ı), ürün/semantik doğrulama hatası; olay servisinin yeniden doğrulamasındaki sözleşme ihlali (`Invalid event batch`); girdinin tamamı geri döndürülmez. |
| 429 | İstek bütçesi veya tenant kotası. |
| 503 | DB kullanılamıyor; başarı uydurulmaz. |

Gerçek body en fazla 16 KiB, en fazla 1024 chunk, derinlik 12 ve 2048 düğüm; varsayılan okuma süresi 5 saniyedir. Sadece Content-Length'e güvenilmez. Authorization başlığı en fazla 16 KiB'dir. Content-Encoding yalnız identity; body varsa `application/json` gerekir. Süreç/IP başına varsayılan 120/dakika bütçe vardır; bu dağıtık rate limiter değildir.

## Sırları argv'ye koymayan manuel API örneği

Önce güvenilir IdP'den bu API için erişim token'ı alın. Aşağıdaki Python kodu açık kullanıcı işlemiyle private dosya oluşturur; değerler kaynakta veya çıktıda tutulmaz. Private dizin parent zinciri owner/DACL veya POSIX izin denetiminden geçmelidir; paylaşılan/yazılabilir çalışma dizini reddedilebilir.

```python
from getpass import getpass
from pathlib import Path
from security_platform.connectors.hostbased_firewall.private_files import create_private_directory, write_private_json

private = create_private_directory(Path.home() / "Documents" / "SecurityPlatformPrivate")
write_private_json(private / "operator.json", {
    "base_url": "https://inventory.example.test",  # Gerçek güvenilir TLS origin'i.
    "access_token": getpass("API access token: "),
})
```

Açıkça seçilen tenant için grant ve cihaz oluşturma örneği:

```python
import httpx
from security_platform.connectors.hostbased_firewall.private_files import read_private_json, write_private_json

operator = read_private_json(private / "operator.json")
tenant_id = input("Yetkili tenant UUID: ").strip()
with httpx.Client(verify=True, trust_env=False, follow_redirects=False, timeout=5) as api:
    reply = api.post(operator["base_url"] + f"/api/v1/tenants/{tenant_id}/enrollment-grants",
        headers={"Authorization": "Bearer " + operator["access_token"]}, json={})
    if reply.status_code != 201:
        raise RuntimeError("Kayıt hakkı oluşturulamadı")
    grant = reply.json()
    write_private_json(private / "grant.json", grant)
    reply = api.post(operator["base_url"] + "/api/v1/enroll",
        headers={"Authorization": "Bearer " + grant["enrollment_token"]}, json={"label": "Elle kaydedilen cihaz"})
    if reply.status_code != 201:
        raise RuntimeError("Cihaz kaydedilemedi")
    device = reply.json()
    write_private_json(private / "device.json", {"schema_version": 1,
        "base_url": operator["base_url"], "device_id": device["device_id"],
        "credential_secret": device["credential_secret"]})
```

Bu örnekteki `private` ilk blokta oluşturulan dizindir. Grant veya credential cevaplarını yazdırmayın. Enrollment grant yalnız bir defa tüketilir. Snapshot gönderimi ve credential rotasyonu ayrı `security-snapshot` komutuyla açıkça yapılır.

## `security-snapshot` istemcisi

```text
security-snapshot --credential-file device.json --state-dir state --snapshot-file export.json [--initialize-state] [--ca-file ca.pem]
security-snapshot --credential-file device.json --rotate-credential [--ca-file ca.pem]
```

- Snapshot modunda `--state-dir` zorunludur. `--initialize-state` yalnız yeni kaydedilen cihaz için sıra 1'i açıkça başlatır. İstemci V1 gönderir; sırası sözleşmenin üst sınırına (`2^53-1`) ulaşınca yeni mesaj oluşturmaz ve ağ isteği yapmadan `device_sequence_exhausted` ile durur.
- `--rotate-credential` açık, tek seferlik operatör işlemidir; otomatik veya zamanlanmış rotasyon yoktur. `--snapshot-file`, `--state-dir` ve `--initialize-state` ile birlikte verilemez (argparse hatası, çıkış 2) ve snapshot göndermez. Mevcut sırla `POST /api/v1/device/credentials/rotate` `{}` body ile çağrılır, böylece sunucunun yapılandırılmış süresi uygulanır.
- Yeni `credential_secret` aynı `device.json` dosyasına mevcut private dosya yardımcılarıyla yazılır: owner/DACL veya POSIX izin denetimi, geçici dosya ve atomik replace. `base_url`, `device_id`, client state ve sıra korunur. İstekten önce dosya aynı içerikle yeniden yazılarak yazılabilirlik denetlenir; yazılamıyorsa istek gönderilmez (`credential_file_not_writable`). Eşzamanlı yenilemeler credential dizinindeki `client.lock` ile sıralanır. Snapshot gönderimi credential'ı state dizininin kilidi altında okur. Bu yüzden gönderim ile yenileme yalnız credential dosyası state dizinindeyse birbirine göre sıralanır. Dosyalar ayrı dizinlerdeyse yenileme sırasında başlayan bir gönderim eski sırla reddedilebilir. Bekleyen mesaj korunur ve yeniden denemek yeterlidir.
- Başarıda stdout yalnız sabit JSON yazar: `{"credential_expires_at":"…","credential_rotated":true}`. Sunucu süre döndürmezse yalnız `credential_rotated` yazılır. Sır hiçbir zaman yazdırılmaz.
- Kurtarılamayan durum: sunucu eski sırrı aynı transaction'da iptal eder. Bu yüzden yeni sır kaybolursa geri getirilemez. Bu durum şu hallerde olabilir: istek gönderildikten sonra bağlantı veya süre hatası (`credential_rotation_failed`, `credential_rotation_deadline_exceeded`), geçersiz/büyük/sıkıştırılmış cevap (`credential_rotation_response_invalid`, `credential_rotation_response_too_large`, `credential_rotation_response_encoding_unsupported`) ya da başarılı cevaptan sonra dosya yazılamaması (`credential_file_write_failed`). Dosya bu hallerde normalde eski sırrı tutar. Önce normal bir snapshot gönderimi deneyin; `snapshot_delivery_rejected` dönerse yönetici cihazı iptal eder, yeni grant ile yeniden kaydeder ve yeni state'i `--initialize-state` ile başlatır.
- `credential_rotation_rejected` sunucunun 200 dışı cevabıdır (ör. 401 süresi dolmuş/iptal edilmiş credential, 429); dosya değişmez. Süresi dolmuş credential rotasyon yapamaz. `credential_expires_at` değerini izleyip rotasyonu süre dolmadan elle çalıştırın; aksi halde yeniden kayıt gerekir.
- `--ca-file PATH` özel veya kurumsal CA kullanan sunucular içindir. PEM CA paketi `ssl.create_default_context(cafile=...)` ile yüklenir. Sertifika zinciri ve hostname doğrulaması açık kalır. Verilen paket varsayılan certifi paketinin yerine geçer; yalnız bu CA'lara güvenilir. Seçenek verilmezse certifi kullanılır; `SSL_CERT_FILE` ve sistem deposu okunmaz. Doğrulamayı kapatan bir seçenek yoktur. Python 3.13 ve sonrası bu bağlamda katı X.509 denetimi (`VERIFY_X509_STRICT`) uygular; CA sertifikasında kritik `basicConstraints CA:TRUE` ve `keyCertSign` bulunmalıdır. Dosya en fazla 1 MiB olabilir. Okunamayan veya geçersiz dosya, ağ isteği ya da state oluşturulmadan `ca_file_invalid` ile reddedilir. CA dosyasını yalnız yöneticinin değiştirebileceği bir konumda tutun.
- Hatalar stderr'e tek satır sabit kod olarak yazılır, çıkış kodu 1'dir. Dosya yolu, sır veya sunucu gövdesi yazılmaz.
