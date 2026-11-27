# API → DTO → görünüm eşleştirmesi

Kaynaklar: [operatör route'ları](../../src/security_platform/api/operator.py), [envanter yanıtları](../../src/security_platform/services/inventory.py), [audit yanıtları](../../src/security_platform/services/audit.py), [olay zaman çizelgesi](../../src/security_platform/services/events.py), [uyarılar](../../src/security_platform/services/alerts.py), [olay sözleşmesi](../../src/security_platform/event_contracts.py), [üyelik/sayfalama sınırı](../../src/security_platform/services/common.py), [ürün DTO'ları](../../src/security_platform/contracts.py) ve [yerel OpenAPI](../../docs/openapi.json). Bu GET'ler backend'de ayrı Pydantic `response_model` ilan etmez; gerçek response sözlüğü servis fonksiyonlarından, gömülü ürün state'i mevcut snapshot DTO'larından alınmıştır. OpenAPI tek başına tam typed response şeması değildir.

Frontend akışı `DTO → runtime normalize → view model → React bileşeni` şeklindedir. TypeScript cast'i doğrulama değildir. Örnek adapter da aynı normalizer'ı kullanır. UI adapter'ı aşağıdaki **altı GET** dışında HTTP operation açmaz. Aşama 2 adım 4 (ADR 0003 §7) yalnız iki okuma ekledi: cihaz olay zaman çizelgesi ve uyarı listesi. API'nin toplam 17 operation'ının mutation/device/operasyon yollarını (olay gönderme, uyarı onaylama ve kapatma dahil) genel çağrı aracına dönüştürmez.

> Snapshot V2 (Aşama 2 adım 3) yeni GET eklemedi: Altay EDR ajanı kartı mevcut cihaz ayrıntısı GET'inin `edr_agent` ürününü okur; typecheck (tsc, 0 hata) ve build (99 modül, 24 dosya) 2026-11-24'te geçti. Zaman çizelgesi ve uyarı arayüzü taşınabilir Node 24.22.1 ile typecheck (tsc, 0 hata) ve build (24 dosya, 32 dosya sınırı içinde) denetimlerinden geçti. Güncel build (bulgu düzeltmeleri ve Termivar ad değişikliğinden sonra) 2026-11-24'te örnek kipte tarayıcıda Türkçe ve İngilizce önizlendi: Ürün Merkezi, Uyarılar ekranı ve cihaz zaman çizelgesi Termivar Konsol / Termivar Console adıyla göründü, tarayıcı konsolunda hata görülmedi. Tarayıcı üzerinden canlı API bağlantısı denenmedi (yerel sertifika); canlı API kabulü yapılmadı. Ayrıntı [teslim kaydındadır](DELIVERY.tr.md).

## Ekran ve route tablosu

| Ekran/iş | Gerçek method/path | Principal ve sunucu yetkisi | Parametre ve sonuç |
|---|---|---|---|
| Tenant seçimi | `GET /api/v1/tenants` | `OperatorAccessToken`; güncel, iptal edilmemiş DB üyelikleri | `limit`, `offset`; `{items:[{id,name,role}], next_offset}`. `role`: `viewer` veya `tenant_admin`. |
| Genel görünüm ve cihaz listesi | `GET /api/v1/tenants/{tenant_id}/devices` | Operatör; seçili tenant'ta güncel viewer/admin üyeliği | UUID `tenant_id`, `limit`, `offset`; `{items:Device[], next_offset}`. Yalnız yüklenen sayfa için özet/arama/filtre/sıralama. |
| Cihaz ayrıntısı ve ürün kartları | `GET /api/v1/tenants/{tenant_id}/devices/{device_id}` | Operatör; tenant üyeliği; cihazın aynı tenant'a ait olması | İki UUID; `Device` alanlarına ek `products`, `missing_products`. Sayfalama yok. |
| Denetim kayıtları | `GET /api/v1/tenants/{tenant_id}/audit` | Operatör; güncel `tenant_admin` üyeliği | UUID `tenant_id`, `limit`, `offset`; `{items:AuditEvent[], next_offset}`. |
| Cihaz olay zaman çizelgesi (cihaz ayrıntısı penceresinde) | `GET /api/v1/tenants/{tenant_id}/devices/{device_id}/events` | Operatör; tenant viewer/admin üyeliği; cihazın aynı tenant'a ait olması | İki UUID, `limit`, `before_seq`; `{items:Event[], next_before_seq, cap_deleted_events, suppressed_alerts}`. |
| Uyarılar (yeni ekran) | `GET /api/v1/tenants/{tenant_id}/alerts` | Operatör; tenant viewer/admin üyeliği | UUID `tenant_id`, isteğe bağlı `status` ve `device_id`, `limit`, `before_seen_at` + `before_id`; `{items:AlertView[], next_before}`. |

Genel görünüm için ayrı aggregation endpoint'i yoktur. API toplam cihaz/ürün veya filo skoru sağlamaz. Kartlar “yüklenen kayıtlar/bu sayfa” anlamını korur. Cihaz listesi ürün durumlarını içermez; ürün state'i yalnız ayrıntı GET'inden gelir. Listeyi doldurmak için bütün ayrıntıları/bütün sayfaları arka planda çekmek yoktur. Ürün özeti görünümü mevcut seçili/yüklenmiş ayrıntının kapsamını açıkça belirtmelidir.

## Ortak pagination

Üç liste route'u `limit=1…100` (varsayılan **50**) ve `offset=0…10000` kabul eder. Cevap `next_offset: integer|null` döndürür; cursor, next URL/link veya toplam sayı yoktur. `null` son sayfayı ifade eder. “Sonraki” okuması kullanıcı eylemidir; ilk sayfada gizlice bütün sayfalar birleştirilmez. Dönen offset izin verilen route aralığı dışında ise keyfî hedefe gidilmez. Örnek kipte daha küçük gösterim sayfası kullanılması sunucunun toplamını değiştirmez.

Zaman çizelgesi ve uyarı listesi offset yerine **anahtar tabanlı** sayfalanır, çünkü offset 10000'de durur. Konsol `limit=50` ister (örnek kipte zaman çizelgesi 10, uyarılar 5). Sonraki sayfa yalnız **Daha eski olaylar / Daha eski uyarılar** düğmesiyle okunur ve yüklenenlerin altına eklenir; konsol bir pencerede en çok **1000 olay**, uyarı ekranında en çok **500 uyarı** tutar. Cursor yalnız doğrulanmış yanıttan alınır ve aynı sabit route'un query'sine çevrilir:

- Zaman çizelgesi: `next_before_seq`, sayfanın son (en küçük) `event_seq` değeri olmalıdır ve yalnız sayfa doluysa (`items` sayısı = `limit`) `null` dışı olabilir. Sonraki istek `before_seq=<değer>` gönderir. Gelen her olay bir öncekinden ve gönderilen `before_seq`'ten kesin küçük olmalıdır.
- Uyarılar: sıra (`last_seen_at` azalan, `id` azalan). `next_before` `{seen_at, id}` sayfanın son öğesini göstermeli ve yalnız dolu sayfada `null` dışı olmalıdır. Sonraki istek `before_seen_at` değerini altı kesir haneli UTC olarak (`…:42.000000Z`) ve `before_id` ile gönderir. Her öğe bu anahtara göre öncekinden kesin küçük olmalıdır; tekrar eden `id` reddedilir.

Kayıt arası sırasız/tekrarlı bir yanıt sözleşme hatasıdır; konsol boşluğu kendisi doldurmaz veya tahmin etmez.

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

`products[]` öğesi `product_id`, `snapshot_sequence`, `received_at`, `observation`, `state` içerir. `product_id` yalnız `hostbasedfirewall`, `termivar`, `antivirus` veya `edr_agent` (Snapshot V2, Aşama 2 adım 3) olabilir; dizi en çok dört öğedir. Sequence/alım bilgisi mevcut cihaz snapshot'ına ait olmalıdır; duplicate ürün veya tenant/cihaz uyuşmazlığı kabul edilmez. `missing_products`, dört ürünün bu snapshot'ta bulunmayanlarını listeler; her ürün ya `products` ya `missing_products` içindedir. Ajanı bildirmeyen cihazda `edr_agent` eksik listelenir. Eski ayrıntıdan state taşınmaz. Termivar Web zarfında ayrıca `report_import_age` vardır; `edr_agent` zarfı diğerleri gibidir.

Ortak state alanları: `product_id`, `catalog_available:bool|null`, `version:string|null`, `source_observed_at:string|null`, `source:self_reported`, `producer_verification:not_verified`.

| Ürün | State alanları | Görünüm |
|---|---|---|
| HBF | `status`, `installed`, `reported_running`, `reported_stale`, `firewall_mode`, `error_codes` | Kurulum/çalışma/mod/hata beyanları ayrı gösterilir. `status`: running/observing/degraded/stopped/unavailable/unknown; mod enforce/sniff/unknown. Nullable alanlar bilinmiyor kalır. |
| Termivar Web | `status`, `scanner_installed`, `execution_available`, `report_presence`, `latest_report` | Experimental/unknown ürün bildirimi ve rapor varlığı ayrılır. Merkezden tarama başlatma veya çalışır scanner iddiası yoktur. |
| AV | `status`, `availability`, `execution_available` | Planned/unknown ve unavailable/unknown; aktif AV/koruma/tarama sonucu üretilmez. |
| Altay EDR ajanı (`edr_agent`) | `status`, `agent_started_at`, `engine_id`, `rule_file_present`, `sensor_state`, `sensor_error_code`, `events_queue_dropped`, `events_write_failed`, `events_unmapped`, `events_skipped`, `events_evicted`, `events_discarded`, `events_degraded`, `outbox_backlog` | Ajanın kendi beyanı: sürüm, başlangıç zamanı, motor kimliği, kural dosyası "var / yok / bilinmiyor" (yalnız varlık; "yüklü" denmez), sensör durumu ve kodu, sayaçlar ve birikim, `self_reported`/`not_verified`. Not: "Ajan kendi durumunu bildirir; koruma veya kural yükleme iddiası değildir". |

`edr_agent` normalizer denetimi (`normalize.ts`, `edrAgentState`): anahtar kümesi `contracts.EdrAgentStatus`'un tam alanlarıdır; fazladan veya eksik anahtar bütün ayrıntıyı reddeder. `catalog_available` `null` olmalıdır. `status` running/unknown; `sensor_state` started/lost/failed/stopped/disabled/unknown; `sensor_error_code` `null` veya olay sözleşmesinin altı kodundan biridir ve yalnız `lost`/`failed` ile dolu olabilir. `engine_id` `null` ya da 1–128 karakter ASCII `^[A-Za-z0-9][A-Za-z0-9._+/ -]*$`, `version` ortak sürüm deseni, `agent_started_at` UTC metni veya `null`dır. Yedi sayaç ve `outbox_backlog` `null` ya da `0…2^53−1` safe integer'dır; boolean, kesir veya metin kabul edilmez. `null` "bilinmiyor" gösterilir, sıfır değildir. `tests/unit/test_console_edr_agent.py` bu listeleri Platform'un DTO'larıyla karşılaştırır.

`latest_report`, varsa `digest`, `report_schema=venom-rendered-assessment/v1`, `imported_at`, `subject_count`, `item_count`, `counts{informational,needs_review,confirmed}`, `severity_counts{unassigned,info,low,medium,high,critical}`, sabit source/verification ve `scope=offline_report_summary` içerir. Sayımlar item_count ile tutarlı olmalıdır. `imported_at` yerel içe aktarma zamanıdır; rapor üretim veya scanner çalıştırma zamanı değildir. Ham bulgu, URL/target, kanıt yolu veya HTML bu DTO'da yoktur; UI bunları icat etmez.

## Olay zaman çizelgesi alanları

Cihaz ayrıntısı başarıyla açılınca konsol aynı cihazın ilk olay sayfasını ayrı bir GET ile okur. Zaman çizelgesi hatası ayrıntıyı gizlemez; yalnız kendi bölümünde görünür. **Zaman çizelgesini yenile** ilk sayfayı yeniden okur; arka plan yenilemesi yoktur.

Üst düzey anahtarlar tam olarak `items`, `next_before_seq`, `cap_deleted_events`, `suppressed_alerts`'tir. İki sayaç negatif olmayan tam sayıdır ve platformun kendi sayımıdır: `cap_deleted_events` cihaz başına satır sınırının alışta sildiği en eski olayların toplamı (zamana göre saklama dahil değil), `suppressed_alerts` cihazın kapanmamış uyarı sınırı dolu olduğu için açılmayan yeni uyarılardır. İkisi de cihazın ilk batch'inden önce `0`'dır.

Her olay `event_seq` (≥ 1), `kind`, `observed_at`, `received_at`, türün alanları ve sabit `source=self_reported`, `producer_verification=not_verified` taşır; anahtar kümesi türe göre tamdır:

| `kind` | Alanlar ve konsol denetimi |
|---|---|
| `process_started` | `pid`, `parent_pid`, `session_id` (`0…4294967295`); `image` 1–1024 karakter, maskeleme kuralına uyar (her ara `Users` bileşeninden sonra `:` öncesi `*`). |
| `process_stopped` | `pid`; `exit_code` `0…4294967295` veya `null`; `image` `null` ya da `\` ve `/` içermeyen 1–260 karakterlik kısa ad. |
| `sensor_state` | `state`: started/lost/failed/stopped; `error_code`: `null` veya altı koddan biri, yalnız lost/failed için dolu olabilir. |

Metin alanlarında platformun reddettiği Unicode 16.0.0 Cc/Cf kod noktaları (yön değiştirme, sıfır genişlik vb.) ve eşlenmemiş vekil karakterler yanıtı geçersiz kılar. Tablo sütunları `event_seq`, tür, gözlem zamanı (cihaz saati), alım zamanı (sunucu), görüntü, pid, üst pid, çıkış kodu, sensör durumu ve hata kodudur; türün sahip olmadığı alan “bu olay türünde yok” olarak gösterilir. Zamanlar saniyesiyle UTC sunulur, tam metin `datetime` niteliğinde kalır.

Yüklenen sayfalarda ardışık iki olay arasındaki sıra boşluğu kesik çizgili bir satırla “n olay kayıp (sıra a–b)” olarak işaretlenir; sayfa sınırları dahildir. Konsol boşluğun nedenini bilmez: olaylar cihazda kaybolmuş ya da platformda silinmiş olabilir. En eski yüklü olaydan önceki numaralar boşluk sayılmaz (cihazın ilk batch'i 1'den büyük başlayabilir). Her olay cihazın beyanıdır; bölüm ve tablo başlığı bunu `self_reported`/`not_verified` olarak söyler.

## Uyarı alanları

`AlertView` anahtarları tam olarak `id`, `device_id`, `rule`, `severity`, `status`, `occurrences`, `first_event_seq`, `last_event_seq`, `first_seen_at`, `last_seen_at`, `evidence`, `acknowledged_at`, `closed_at`, `source=self_reported`, `producer_verification=not_verified`'dir. Konsol şu ilişkileri denetler:

| Kural (`rule`) | `severity` | `evidence` anahtarları |
|---|---|---|
| `user_writable_launch` — kullanıcının yazabildiği konumdan başlatma | `low` | `image` (maskeli yol), `pid` |
| `office_browser_spawned_tool` — ofis uygulamasının veya tarayıcının başlattığı sistem aracı | `medium` | `image`, `pid`, `parent_image`, `parent_pid` |
| `sensor_unstable` — sensör kayboldu veya başarısız | `medium` | `state` (lost/failed), `error_code` (kod veya `null`) |
| `event_loss` — olay kaybı (sıra boşluğu) | `medium` | `missing_events` (≥ 1, birikimli) |

- `status` open/acknowledged/closed. `open` ise `acknowledged_at` ve `closed_at` `null`; `acknowledged` ise `acknowledged_at` dolu, `closed_at` `null`; `closed` ise `closed_at` dolu, `acknowledged_at` dolu veya `null` (doğrudan kapatma).
- `occurrences` ≥ 1; `first_event_seq` ≤ `last_event_seq`, ikisi de ≥ 1. `first_seen_at`/`last_seen_at` eşleşen batch'lerin sunucu alım zamanıdır; sunucu saati geri gidebileceği için aralarındaki sıra denetlenmez.
- Filtre gönderildiyse her öğenin `status`/`device_id` değeri ona eşit olmalıdır.

Satır önem, kuralın TR/EN etiketi ve kodu, cihaz, tekrar, ilk/son görülme (olay sırasıyla), eşleşme bilgisi ve durumu (onay/kapanış zamanıyla) gösterir. Cihaz etiketi ve cihaz filtresi, ekran açılırken okunan **ilk cihaz sayfasından** (`GET …/devices?offset=0&limit=100`) gelir; başka sayfa okunmaz. Bu okuma isteğe bağlıdır: başarısız olursa (ör. sözleşme hatası, 429, zaman aşımı) uyarılar yine yüklenir, cihazlar kısa kimlikleriyle gösterilir, cihaz seçiminde cihaz listelenmez ve ekran nedeniyle birlikte küçük bir not gösterir; bir sonraki taze okuma etiketleri yeniden dener. İki okumadan birinin 401'i, her okumada olduğu gibi bağlantıyı kapatır. Listede olmayan cihaz kısa kimliğiyle gösterilir; o cihazın uyarıları cihaz ayrıntısındaki **Bu cihazın uyarıları** düğmesiyle açılır. Cihaz adı tıklanınca mevcut ayrıntı GET'i ve zaman çizelgesi açılır.

Ekran, **kural eşleşmesinin teşhis olmadığını** açıkça söyler: eşleşme kötü amaçlı yazılım, saldırı veya ihlal kanıtı değildir; kötü niyetli bir cihaz kendi uyarılarını tetikleyebilir veya bastırabilir. Ekran salt okunurdur: onaylama/kapatma düğmesi yoktur; bu geçişler Aşama 2'de yalnız API ile ve `tenant_admin` rolüyle yapılır (ADR 0003 §4, §7). Yeni eşleşmeler yalnız yenilemeyle görünür.

## Audit alanları ve erişim

`AuditEvent`: `id`, `tenant_id`, `actor_type`, nullable `actor_id`, `action`, `object_type`, `object_id`, `outcome`, `created_at`. Aktör türü operator/device/local_admin; actor_id yoksa kimlik uydurulmaz. Mevcut yazıcı başarılı yönetim olayları için `outcome=success` kaydeder. Sunulan eylemler tenant_created, membership_set/revoked, enrollment_grant_created/revoked, device_enrolled/revoked, device_credential_rotated, tenant_event_retention_set (nesne türü tenant; yerel yönetim CLI'ının `set-event-retention` komutu yazar), tenant_alert_retention_set (nesne türü tenant; `set-alert-retention` yazar), alerts_pruned (nesne türü tenant; `alerts prune` yazar, sayıları API'de dönmez) ile alert_acknowledged ve alert_closed'dur (nesne türü `alert`, `object_id` uyarı kimliği); nesne türleri tenant/membership/enrollment_grant/device/device_credential/alert'tir. Bilinmeyen bir eylem bütün audit sayfasını sözleşme hatası yapar; `tests/unit/test_console_audit_actions.py` konsol listesini API'nin yazdıklarıyla karşılaştırır.

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

API hedefi sayfanın aynı HTTPS origin'indeki sabit `/api/v1` tabanıdır. Altı sabit route fonksiyonu UUID'leri, limit/offset'i ve anahtar tabanlı `before_seq`, `before_seen_at`/`before_id`, `status`, `device_id` parametrelerini kodlar. `Authorization: Bearer …`, `credentials:omit`, `cache:no-store`, `redirect:error`; en fazla 512 KiB yanıt ve fetch+gövde boyunca 12 saniye. Token'dan rol çözümleme, mutation veya genel URL çalıştırıcısı yoktur. Adapter uygulanması gerçek token/IdP/API bağlantısı kabulü değildir.

Metin bütçesi: `strictJson`'un varsayılan profili tek bir metni en çok 1024 UTF-16 birimiyle sınırlar. Zaman çizelgesi ve uyarı listesi okumaları bunun yerine kapalı `sp-events-alerts-v1` profilini kullanır: varsayılanın aynısıdır, yalnız metin bütçesi 2048 birimdir. Profili yanıt değil, sabit route seçer. Platform görüntü yolunu 1024 karakterle (kod noktası) sınırlar ve 1024 kod noktası en çok 2048 UTF-16 birimi eder; bu yüzden sözleşmenin izin verdiği her yol, dört baytlık karakterlerle dolu olsa da sığar. `maskedImage()` aynı 2048 birimi kabul eder. `tests/unit/test_console_preview_server.py` profil kümesini, bağlantıyı ve tam 100 öğelik sayfaları denetler.

Tam sayılar: konsol JavaScript'in tam temsil sınırını (2^53−1) aşan bir tam sayıyı yuvarlamaz, bütün yanıtı reddeder. Platform bu yüzden `event_seq`'i 2^53−1 ile sınırlar (aşan batch 422 alır); zaman çizelgesindeki `event_seq`/`next_before_seq` ile uyarının `first_event_seq`/`last_event_seq` ve birikimli `missing_events` değerleri de bu aralıkta kalır. Snapshot V2 (Aşama 2, adım 3) adım 4'te not edilen son yolu kapattı: snapshot `sequence` iki şema sürümünde de 2^53−1 ile sınırlıdır (V1 için sıkılaştırma; önce 2^63−1 idi), böylece `last_sequence` ve `snapshot_sequence` konsolun aralığında kalır; ajanın sayaçları da 0…2^53−1'dir. Bu sınırdan önce kabul edilmiş daha büyük bir sıra varsa o kayıt yerinde kalır ([tehdit modeli](../../docs/THREAT_MODEL.tr.md)).

## Rapor görünümü: yeni route yok

[Seçili cihaz raporu](REPORTS.tr.md) yalnız mevcut `GET /api/v1/tenants/{tenant_id}/devices/{device_id}` sonucunun runtime denetiminden geçmiş ve görüntülenmiş ayrıntısını kullanır. Rapor eylemleri GET dahil yeni istek yapmaz; listeden toplu ayrıntı okuma veya N+1 yoktur.

| Mevcut kaynak | Rapor kullanımı |
|---|---|
| Seçili tenant `id/name`, Device `id/label` | Dahili kapsam bağı; ad/kimlik gösterme seçeneği varsayılan kapalıdır. |
| `identity_status`, `connection_status`, nullable zamanlar | Seçilme anındaki kayıt/bildirim bilgisi ve eksik veri açıklaması; yeni eşik yoktur. |
| Ayrıntı `products[].state` / `missing_products` | Ürün bildirim durumu, sağlanan sürüm ve izin verilen sınırlı özetler; eski state taşınmaz. Rapor üç ürünü (HBF, Termivar Web, AV) kapsamaya devam eder; ajanın `edr_agent` durumu rapora kopyalanmaz. |
| Termivar Web `latest_report` içindeki mevcut sayısal toplamlar | Yalnız sınırlı ürün özeti; ham rapor/target/kanıt/HTML veya doğrulanmış tarama sonucu değildir. |
| `source_observed_at`, `received_at`, source/verification | Ayrı kaynak/alım zamanı ve cihaz beyanı/doğrulanmadı açıklaması. Konsol okuma/rapor oluşturma zamanı frontend metadata'sıdır. |

Tüm DTO/view model/session nesnesi rapora aktarılmaz. API adresi, token/credential/JWT, audit/aktör, hata body'si ve policy içeriği kapsam dışıdır. Taslak yalnız bellekte aynı tenant+kip+oturum bağında, en fazla 20 cihaz/256 KiB UTF-8 veridir. Yeni backend DTO, snapshot/revision/receipt veya kanıt protokolü değildir.
