# API → DTO → görünüm eşleştirmesi

Kaynaklar: [operatör route'ları](../../src/security_platform/api/operator.py), [envanter yanıtları](../../src/security_platform/services/inventory.py), [audit yanıtları](../../src/security_platform/services/audit.py), [üyelik/sayfalama sınırı](../../src/security_platform/services/common.py), [ürün DTO'ları](../../src/security_platform/contracts.py) ve [yerel OpenAPI](../../docs/openapi.json). Bu GET'ler backend'de ayrı Pydantic `response_model` ilan etmez; gerçek response sözlüğü servis fonksiyonlarından, gömülü ürün state'i mevcut snapshot DTO'larından alınmıştır. OpenAPI tek başına tam typed response şeması değildir.

Frontend akışı `DTO → runtime normalize → view model → React bileşeni` şeklindedir. TypeScript cast'i doğrulama değildir. Örnek adapter da aynı normalizer'ı kullanır. UI adapter'ı aşağıdaki **dört GET** dışında HTTP operation açmaz; önceki 12 operation'ın mutation/device/operasyon yollarını genel çağrı aracına dönüştürmez.

## Ekran ve route tablosu

| Ekran/iş | Gerçek method/path | Principal ve sunucu yetkisi | Parametre ve sonuç |
|---|---|---|---|
| Tenant seçimi | `GET /api/v1/tenants` | `OperatorAccessToken`; güncel, iptal edilmemiş DB üyelikleri | `limit`, `offset`; `{items:[{id,name,role}], next_offset}`. `role`: `viewer` veya `tenant_admin`. |
| Genel görünüm ve cihaz listesi | `GET /api/v1/tenants/{tenant_id}/devices` | Operatör; seçili tenant'ta güncel viewer/admin üyeliği | UUID `tenant_id`, `limit`, `offset`; `{items:Device[], next_offset}`. Yalnız yüklenen sayfa için özet/arama/filtre/sıralama. |
| Cihaz ayrıntısı ve ürün kartları | `GET /api/v1/tenants/{tenant_id}/devices/{device_id}` | Operatör; tenant üyeliği; cihazın aynı tenant'a ait olması | İki UUID; `Device` alanlarına ek `products`, `missing_products`. Sayfalama yok. |
| Denetim kayıtları | `GET /api/v1/tenants/{tenant_id}/audit` | Operatör; güncel `tenant_admin` üyeliği | UUID `tenant_id`, `limit`, `offset`; `{items:AuditEvent[], next_offset}`. |

Genel görünüm için ayrı aggregation endpoint'i yoktur. API toplam cihaz/ürün veya filo skoru sağlamaz. Kartlar “yüklenen kayıtlar/bu sayfa” anlamını korur. Cihaz listesi ürün durumlarını içermez; ürün state'i yalnız ayrıntı GET'inden gelir. Listeyi doldurmak için bütün ayrıntıları/bütün sayfaları arka planda çekmek yoktur. Ürün özeti görünümü mevcut seçili/yüklenmiş ayrıntının kapsamını açıkça belirtmelidir.

## Ortak pagination

Üç liste route'u `limit=1…100` (varsayılan **50**) ve `offset=0…10000` kabul eder. Cevap `next_offset: integer|null` döndürür; cursor, next URL/link veya toplam sayı yoktur. `null` son sayfayı ifade eder. “Sonraki” okuması kullanıcı eylemidir; ilk sayfada gizlice bütün sayfalar birleştirilmez. Dönen offset izin verilen route aralığı dışında ise keyfî hedefe gidilmez. Örnek kipte daha küçük gösterim sayfası kullanılması sunucunun toplamını değiştirmez.

## Device alanları

| Alan | Gerçek anlamı ve UI sınırı |
|---|---|
| `id`, `tenant_id`, `label` | Cihaz UUID'si, tenant UUID'si, kayıt etiketi. Dönen tenant/cihaz bağı istenen bağlamla uyuşmalıdır. Etiket düz metindir. |
| `identity_status` | `active` veya `revoked`; cihaz kaydının kimlik durumu. Firewall'ın çalıştığı/durduğu anlamına gelmez. |
| `connection_status` | `recent`, `stale`, `never_seen`; API'nin son merkez alımına göre sınıflandırması. UI yeni eşik/SLA üretmez. |
| `created_at`, `revoked_at` | UTC kayıt zamanı ve nullable iptal zamanı. `revoked` ile iptal zamanı ilişkisi korunur. |
| `last_sequence` | Nullable pozitif snapshot sequence; frontend safe integer sınırını aşarsa yanıt hatadır. Policy revision/CAS değildir. |
| `last_received_at` | Merkezin son snapshot kabulü; nullable. Konsolun son okuma saati değildir. |
| `source_observed_at` | Cihazın bildirdiği kaynak gözlem zamanı; nullable. Bağımsız saat doğrulaması değildir. |
| `source_observation` | `{age_seconds:integer|null, clock_state:unknown|future|not_verified}`. Kaynak zamanı yoksa unknown; gelecek kaynak zamanı için yaş yoktur. |
| `source`, `producer_verification` | `self_reported`, `not_verified`; API/TLS başarısı bunları yükseltmez. |

Liste, tenant creation/id sırasını kullanır. Frontend'in yerel arama/sıralama/filtre işlemleri yalnız yüklenen sayfa üzerinde çalışır; filtrelenmiş tüm filonun sonucu gibi sunulmaz. Konsolun “son yükleme” zamanı ayrı görüntüleme metadata'sıdır.

## Ayrıntı ürün zarfı

`products[]` öğesi `product_id`, `snapshot_sequence`, `received_at`, `observation`, `state` içerir. `product_id` yalnız `hostbasedfirewall`, `termivar`, `antivirus` olabilir. Sequence/alım bilgisi mevcut cihaz snapshot'ına ait olmalıdır; duplicate ürün veya tenant/cihaz uyuşmazlığı kabul edilmez. `missing_products`, üç ürünün bu snapshot'ta bulunmayanlarını listeler; eski ayrıntıdan state taşınmaz. Termivar zarfında ayrıca `report_import_age` vardır.

Ortak state alanları: `product_id`, `catalog_available:bool|null`, `version:string|null`, `source_observed_at:string|null`, `source:self_reported`, `producer_verification:not_verified`.

| Ürün | State alanları | Görünüm |
|---|---|---|
| HBF | `status`, `installed`, `reported_running`, `reported_stale`, `firewall_mode`, `error_codes` | Kurulum/çalışma/mod/hata beyanları ayrı gösterilir. `status`: running/observing/degraded/stopped/unavailable/unknown; mod enforce/sniff/unknown. Nullable alanlar bilinmiyor kalır. |
| Termivar | `status`, `scanner_installed`, `execution_available`, `report_presence`, `latest_report` | Experimental/unknown ürün bildirimi ve rapor varlığı ayrılır. Merkezden tarama başlatma veya çalışır scanner iddiası yoktur. |
| AV | `status`, `availability`, `execution_available` | Planned/unknown ve unavailable/unknown; aktif AV/koruma/tarama sonucu üretilmez. |

`latest_report`, varsa `digest`, `report_schema=venom-rendered-assessment/v1`, `imported_at`, `subject_count`, `item_count`, `counts{informational,needs_review,confirmed}`, `severity_counts{unassigned,info,low,medium,high,critical}`, sabit source/verification ve `scope=offline_report_summary` içerir. Sayımlar item_count ile tutarlı olmalıdır. `imported_at` yerel içe aktarma zamanıdır; rapor üretim veya scanner çalıştırma zamanı değildir. Ham bulgu, URL/target, kanıt yolu veya HTML bu DTO'da yoktur; UI bunları icat etmez.

## Audit alanları ve erişim

`AuditEvent`: `id`, `tenant_id`, `actor_type`, nullable `actor_id`, `action`, `object_type`, `object_id`, `outcome`, `created_at`. Aktör türü operator/device/local_admin; actor_id yoksa kimlik uydurulmaz. Mevcut yazıcı başarılı yönetim olayları için `outcome=success` kaydeder. Sunulan eylemler tenant_created, membership_set/revoked, enrollment_grant_created/revoked, device_enrolled/revoked ve device_credential_rotated; nesne türleri tenant/membership/enrollment_grant/device/device_credential'dır.

Audit yeni → eski sırasıyla, bounded retention ile gelir. UI “yüklenen kayıtlar” der; tam, değişmez veya bağımsız doğrulanmış olay geçmişi iddiası kurmaz. Snapshot sayısını, başarısız tüm girişimleri veya tarama sonuçlarını audit'ten türetmez. Viewer için bu görünüm yetkisizdir; UI rol etiketi yardımcıdır, yetki API'de yeniden kontrol edilir.

## Hata ve taşıma davranışı

| Sonuç | UI davranışı |
|---|---|
| `401` | Canlı bağlantı/token/özel veriler temizlenir; yeniden açık bağlantı gerekir. |
| `403` | İlgili görünüm temizlenir ve erişim reddi gösterilir; boş liste değildir. |
| `404` | Kayıt yok veya erişilebilir tenant kapsamı dışında. Üyelik/nesne varlığı hakkında fazladan çıkarım yapılmaz. |
| `422`, uyumsuz JSON/DTO/enum veya unsafe integer | Görünür sözleşme/girdi hatası; sıfır/boş/sağlıklı varsayımı yoktur. |
| `429`, `5xx` | Sınır/servis hatası; sessiz tekrar veya örneğe dönüş yoktur. |
| Ağ, abort, 12 saniye veya 512 KiB sınırı | Sabit güvenli hata; yanıt/token konsola dökülmez. Ağ hatası kesin CORS/401 teşhisi değildir. |

API hedefi sayfanın aynı HTTPS origin'indeki sabit `/api/v1` tabanıdır. Dört sabit route fonksiyonu UUID ve limit/offset'i kodlar. `Authorization: Bearer …`, `credentials:omit`, `cache:no-store`, `redirect:error`; en fazla 512 KiB yanıt ve fetch+gövde boyunca 12 saniye. Token'dan rol çözümleme, mutation veya genel URL çalıştırıcısı yoktur. Adapter uygulanması gerçek token/IdP/API bağlantısı kabulü değildir.

## Rapor görünümü: yeni route yok

[Seçili cihaz raporu](REPORTS.tr.md) yalnız mevcut `GET /api/v1/tenants/{tenant_id}/devices/{device_id}` sonucunun runtime denetiminden geçmiş ve görüntülenmiş ayrıntısını kullanır. Rapor eylemleri GET dahil yeni istek yapmaz; listeden toplu ayrıntı okuma veya N+1 yoktur.

| Mevcut kaynak | Rapor kullanımı |
|---|---|
| Seçili tenant `id/name`, Device `id/label` | Dahili kapsam bağı; ad/kimlik gösterme seçeneği varsayılan kapalıdır. |
| `identity_status`, `connection_status`, nullable zamanlar | Seçilme anındaki kayıt/bildirim bilgisi ve eksik veri açıklaması; yeni eşik yoktur. |
| Ayrıntı `products[].state` / `missing_products` | Ürün bildirim durumu, sağlanan sürüm ve izin verilen sınırlı özetler; eski state taşınmaz. |
| Termivar `latest_report` içindeki mevcut sayısal toplamlar | Yalnız sınırlı ürün özeti; ham rapor/target/kanıt/HTML veya doğrulanmış tarama sonucu değildir. |
| `source_observed_at`, `received_at`, source/verification | Ayrı kaynak/alım zamanı ve cihaz beyanı/doğrulanmadı açıklaması. Konsol okuma/rapor oluşturma zamanı frontend metadata'sıdır. |

Tüm DTO/view model/session nesnesi rapora aktarılmaz. API adresi, token/credential/JWT, audit/aktör, hata body'si ve policy içeriği kapsam dışıdır. Taslak yalnız bellekte aynı tenant+kip+oturum bağında, en fazla 20 cihaz/256 KiB UTF-8 veridir. Yeni backend DTO, snapshot/revision/receipt veya kanıt protokolü değildir.
