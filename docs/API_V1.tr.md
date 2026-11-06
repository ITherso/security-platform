# API V1 sözleşmesi

Temel adres dağıtım yöneticisinin seçtiği HTTPS origin'idir. Uygulama 12 operation sunar; signup, komut, policy push, shell veya scan endpointi yoktur. Gerçek `app.openapi()` çıktısı [openapi.json](openapi.json) dosyasındadır. Public `/docs`, `/redoc` ve `/openapi.json` yolları kapalıdır; statik dosya inceleme içindir. Route/spec eşitliği entegrasyon testinde denetlenir.

## Üç bearer türü

| OpenAPI scheme | Kaynak ve yetki |
|---|---|
| `OperatorAccessToken` | Güvenilir IdP'nin RS256 API erişim token'ı. Tenant rolü güncel DB üyeliğinden gelir. |
| `EnrollmentGrant` | `spg_` + 43 base64url karakter; yalnız tek kullanımlık cihaz kaydı. |
| `DeviceCredential` | `spd_` + 43 base64url karakter; tek tenant ve cihaza bağlı snapshot/rotasyon. |

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
| `GET /api/v1/tenants/{tenant_id}/devices/{device_id}` | Tenant viewer/admin | Cihaz, son ürünler, eksik ürünler ve ayrı kaynak/bağlantı yaşları. |
| `POST /api/v1/tenants/{tenant_id}/devices/{device_id}/revoke` | Tenant admin | Boş body/`{}`; bütün cihaz credential'larını etkisizleştirir. |
| `GET /api/v1/tenants/{tenant_id}/audit` | Tenant admin | Bounded başarılı yönetim olayları; sır veya ham payload içermez. |
| `POST /api/v1/enroll` | Enrollment grant | `{label:"..."}`; 201: `tenant_id`, `device_id`, `credential_id`, `credential_secret`, `credential_expires_at`. |
| `PUT /api/v1/device/snapshot` | Device credential | Strict V1 snapshot; 200 kabul cevabı. |
| `POST /api/v1/device/credentials/rotate` | Device credential | `{}` veya `ttl_seconds`; yeni credential cevabı, eski sır aynı transaction'da iptal edilir. |

Liste yolları `limit=1..100` (varsayılan 50), `offset=0..10000` alır. Cursor yolu yoktur; V1 offset sayfalaması kullanır. Liste ve detay aynı tenant üyeliğini uygular. Bilinmeyen extra body alanları reddedilir.

Kayıt hakkı varsayılanı 600 saniye, API üst sınırı 3600 saniyedir; yapılandırılmış daha dar üst sınır da uygulanır. Credential varsayılanı 86400 saniye; rotasyon body aralığı 60–2592000 saniyedir. Snapshot credential süresini uzatmaz. Yeni cihaz ilk snapshot'a kadar `never_seen` kalır. Enrollment veya rotasyon commit'inden sonra cevap kaybolursa plaintext sır yeniden üretilemez; yönetici cihazı iptal edip yeni grant ile kayıt yaptırır.

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

`sequence` strict integer `1..2^63-1`; `message_id` lower-case kanonik UUID'dir. UTC metni `YYYY-MM-DDTHH:MM:SS[.fraction]Z` biçiminde doğrulanıp normalize edilir. En fazla üç benzersiz ürün: `hostbasedfirewall`, `termivar`, `antivirus`. Boş liste kabul edilir ve önceki ürün satırlarını kaldırır; detayda eksik ürünler `missing_products` ile bildirilir.

| Ürün | Alanlar ve yorum |
|---|---|
| Ortak | `catalog_available`, `version`, `source_observed_at`; gözlenmeyen değer `null`/`unknown`. `source=self_reported`, `producer_verification=not_verified` sabittir. Sürüm en fazla 64 güvenli karakterdir. |
| HostBasedFirewall | `status`, `installed`, `reported_running`, `reported_stale`, `firewall_mode=enforce|sniff|unknown`, kapalı listeden en fazla 16 benzersiz `error_codes`. Merkezin enforcement doğrulaması değildir. |
| Termivar | `status=experimental|unknown`, `scanner_installed`, `execution_available`, `report_presence=present|none|unknown`, `latest_report`. Çalıştırma iddiası `true` olamaz. Rapor varlığı scanner kurulumunu kanıtlamaz. |
| Antivirüs | `status=planned|unknown`, `availability=unavailable|unknown`; aktif katalog/çalıştırma veya sürüm iddiası reddedilir. |

Termivar `latest_report` yalnız digest, sabit rapor şeması, yerel `imported_at`, konu/kayıt sayıları, disposition ve severity sayıları, sabit kaynak/doğrulama/scope alanlarını içerir. `subject_count=1..1024`, `item_count` ve her sayaç `0..4096`; boolean sayı değildir. Her iki sayı grubunun toplamı `item_count` olmalıdır. `present` ile özet varlığı tutarlı olmalıdır. Ham hedef/URL/IP, kanıt, HTML, komut veya serbest metadata alanı yoktur.

200 kabul cevabı:

```json
{"accepted":true,"message_id":"00000000-0000-4000-8000-000000000001","sequence":1,"received_at":"2030-01-01T00:00:00Z"}
```

Sunucu `received_at` atar. Son mesaj aynı sıra/UUID/kanonik içerikle tekrarlanırsa aynı cevap döner ve tazelik yenilenmez. Son sıra veya son UUID farklı içerikle 409; eski sıra 409'dur. V1 yalnız son kabulün retry penceresini tutar; bütün tarihsel mesaj UUID'leri için sınırsız tombstone deposu yoktur. Daha yüksek sıra önceki tam ürün durumunu atomik değiştirir. Credential rotasyonu cihazın son sırasını korur.

## Hatalar ve sınırlar

| HTTP | Anlam |
|---|---|
| 400 | Geçersiz/tekrarlı JSON, yapı bütçesi, başlık/uzunluk veya HTTPS gereksinimi. |
| 401 | Eksik, yanlış amaçlı, süresi geçmiş, iptal edilmiş veya geçersiz credential. |
| 403 | Kendi tenant'ında yetersiz rol veya yabancı Origin. |
| 404 | Kaynak yok veya bu tenant üyeliğiyle görünmez. |
| 409 | Sıra/içerik çakışması, aşılmış mesaj veya tüketilmiş grant iptali. |
| 408 / 413 / 415 | Body süresi / boyut-parça sayısı / JSON olmayan veya sıkıştırılmış body. |
| 422 | DTO tipi, extra alan, ürün/semantik doğrulama hatası; girdinin tamamı geri döndürülmez. |
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

Bu örnekteki `private` ilk blokta oluşturulan dizindir. Grant veya credential cevaplarını yazdırmayın. Enrollment grant yalnız bir defa tüketilir. Snapshot gönderimi ayrı `security-snapshot` komutuyla açıkça yapılır. Rotasyon da `/api/v1/device/credentials/rotate` için geçerli cihaz bearer'ıyla açık API çağrısıdır; yeni `credential_secret` aynı private `device.json` dosyasına atomik yazılır, mevcut cihaz state'i sıfırlanmaz.
