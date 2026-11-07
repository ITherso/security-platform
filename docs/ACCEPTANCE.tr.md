# Kabul kaydı — 7 Kasım 2026

Bu kayıt ikinci turun `platform-02-excerpt.txt` ve `platform-02-continuation.txt` görevindeki 27 kapıyı ayrı sonuçla izler. `passed` belirtilen test kapsamını, `not_run` çalıştırılmamış dış kabulü ifade eder. Fixture cihazlar fiziksel filo veya üretim kabulü sayılmaz. Sonraki saf politika turunun 160 testi ve güncel birleşik 344 passed / 1 skipped sonucu [POLICY_PREVIEW_ACCEPTANCE.tr.md](POLICY_PREVIEW_ACCEPTANCE.tr.md) içinde ayrıca kaydedilir; aşağıdaki 183 sonucu ikinci turun tarihsel koşusudur.

## Korunan firewall başlangıcı

HostBasedFirewall sürümü 1.4.3; yerel commit `94037a261b63e2443f04d56356cd525a3d3445df`. Kaynak ZIP SHA256:

```text
bb4e4c876ae56047aa114023bbf1059fc9f979908f7f65f0fbe849713b332261
```

Kullanıcının başlangıç ZIP SHA256 değeri `85f1cc8f66040e8b319aabca581d02bd2e35fc59234fdbfe78bfb27d7ec9f1de`; ayrı baseline kopyasında **1807 Python testi + 47 alt test** geçti. Tamamlanan firewall kaynağında **2106 + 47**, sekiz fixture Edge paketi ve gerçek izole localhost dashboard'unda **11 kontrol** geçti. Gerçek UI örnek rapor importu ve `outputs/ecosystem-live-dashboard.png` görüntüsü alınmıştır. Bu sonuçlar yerel log, commit ve manifestten doğrulandı; prompttaki eski 2028 sayısı nihai kanıt olarak kullanılmadı.

İkinci aşamada yerel ürün merkezine dar bir salt okunur UI köprüsü eklenir: mevcut authenticated `GET /ecosystem` cevabını `ecosystem-overview.json` olarak indiren düğme. Otomatik merkezî aktarım veya server/config yazımı yoktur. Başlangıç commit/arşivi korunur; köprü sonrası kaynak kimliği ayrı manifestte yer alır. EXE, GitHub push veya yayıncı imzası üretilmedi. Yerel Windows sürücüsü/servis/reboot/iki hesap kabulü tamamlanmış sayılmaz.

Köprü sonrası firewall commit'i `74a88ed336cb8a0a2fab16e20389c9410590c292`; çalışma ağacı temiz olarak doğrulandı. Bu commit ilk aşama hash'inin yerine geçirilmez.

## Gerçek çalıştırmalar ve kanıt türleri

| Koşu | Kaydedilen sonuç ve kapsam |
|---|---|
| İkinci tur birleşik platform koşusu | Tarihsel ikinci tur kaydı: **183 passed, 1 POSIX-only skipped**, 1 mevcut bağımlılık uyarısı; 22,29 saniye. Gerçek PG, güvenlik incelemesi, migration kaynak seçimi ve ayrı süreç TLS E2E dahildir. Güncel aynı adlı teslimat logu sonraki turun birleşik sonucunu tutar. |
| Mapper/manuel istemci/transport | **85 passed, 1 skipped**; üç odaklı dosya. Gerçek TCP cevap kaybı/redirect/boyut ve self-signed TLS reddi içerir. Atlanan yalnız POSIX chmod testidir; gerçek Windows owner/DACL denetimleri çalıştı. |
| Portable PostgreSQL yardımcı aracı | **22 birim testi geçti**. Yabancı cluster/yol/URL kontrolü, secret çıktı koruması ve Windows pg_ctl capture sınırı. |
| Gerçek PostgreSQL servis transaction'ları | **17 test geçti**; composite FK, tenant kapsamı, enrollment/rotasyon yarışları, rollback, snapshot sırası ve retention. |
| API/JWT/boundary/güvenlik incelemesi | **55 test geçti**; gerçek PG ve gerçek RS256 fixture JWT'leri. HTTP TestClient kullanır; auth dependency'si bypass edilmez. Ayrı TCP/TLS süreç kabulü aşağıdadır. |
| Gerçek ayrı API ve üç fixture istemci | `scripts/demo_acceptance.py`: **1 E2E testi geçti**, 13,51 saniye. Gerçek PostgreSQL, CA doğrulamalı TLS, iki tenant, üç cihaz/üç bağımsız istemci süreci, iki API restart'ı. Kanıt: `reports/e2e-inventory-flow.json`. |
| DB rol ve stop/start kanıtı | `reports/postgres-fixture.json`: gerçek PostgreSQL 18.6 stop/start, veri ve credential korunması; runtime DDL ve audit UPDATE reddi, owner/non-superuser ayrımı. |
| Kurulu wheel migration kabulü | `reports/wheel-acceptance.json`: gerçek wheel oluşturuldu, ayrı hedefe kuruldu, kod kurulu wheel'den import edildi, migration kaynakları bulundu ve CLI gerçek PostgreSQL'e migration çalıştırdı. Üç kaynak seçimi regresyon testi nihai pakete dahildir; wheel yayımlanmadı. |

Odaklı koşular ortak testler içerir; bu sayılar toplanarak tek büyük sonuç üretilmez. Tek uyarı FastAPI/Starlette test istemcisinin httpx kullanım dışı kalma bildirimidir. Bağımlılık tutarlılığı (`pip check`) ve Python derleme kontrolü (`compileall`) de geçti. SQLite bu kabulün yerine kullanılmadı. Windows'ta atlanan POSIX testi, Windows ACL kabulünü atlamak değildir.

## Zorunlu kapılar 1–27

| No | Durum | Doğrulanan kapı ve kanıt sınırı |
|---|---|---|
| 1 | `passed` | İki tenant, tenant_admin/viewer ve üç bağımsız fixture cihaz: gerçek PostgreSQL + API/JWT testleri ve gerçek TLS E2E. Fiziksel cihaz değildir. |
| 2 | `passed` | A kullanıcısının B tenant'ına liste/detay/sayfalama/audit/grant/iptal erişimi reddedilir. V1 cursor yerine sınırlı offset kullanır; aynı kapsam uygulanır. |
| 3 | `passed` | Aynı principal A'da admin, B'de viewer; rol tenant'a göre değişir. `test_roles_come_from_current_tenant_membership_and_revocation`. |
| 4 | `passed` | Geçerli imzalı token'da sahte `roles`, `tenant`, `is_admin` claim'leri DB rolünü yükseltmez. JWT ve API testleri. |
| 5 | `passed` | Güncel üyelik iptali, süresi dolmamış token'ın yeni tenant isteğini kapatır. Gerçek PG üyelik/HTTP testleri. |
| 6 | `passed` | Operatör, ID token, grant ve device credential yanlış endpoint ailesinde reddedilir. Amaç ayrımı gerçek imza/digest yoluyla testlidir. |
| 7 | `passed` | Yanlış issuer/audience/imza/algoritma, expiry, mandatory claim/kid ve token key URL'si reddi; key URL'sine ağ çağrısı olmadığını test yakalar. |
| 8 | `passed` | Paralel enrollment en fazla bir cihaz üretir; audit hatasında cihaz/credential/consumption rollback. Gerçek PostgreSQL transaction ve HTTP yarışları. |
| 9 | `passed` | Tüketilmiş, süresi dolmuş ve iptal edilmiş grant reddi; aynı hak ikinci cihaz üretmez. |
| 10 | `passed` | Commit sonrası enrollment cevabını kaybeden istemci modeli, aynı hakkı yeniden kullanarak ikinci cihaz/secret alamaz. DB'de plaintext recovery cache yoktur; yönetici iptal/yeni grant akışı belgelenmiştir. |
| 11 | `passed` | Device A'nın body/path/header ile B seçememesi. Kimlik bearer'dan türetilir; yasak body alanı 422, sahte kimlik başlıkları yetki vermez. |
| 12 | `passed` | İptal snapshot transaction'ında tekrar kontrol edilir; yeni API instance ve gerçek süreç restart'ından sonra yeni bildirim 401. Gerçek TLS E2E'de iki tenant iptal akışı. |
| 13 | `passed` | Paralel rotation en fazla bir yeni credential; eski sır 401. Cevabı kaybetme modeli eski sırdan plaintext geri alamaz; yeni kayıt gereksinimi açık. Audit failure rotasyonu da rollback eder. |
| 14 | `passed` | Son aynı mesaj aynı kabul cevabı verir; `received_at`, sayaç ve audit artmaz. Gerçek PG/HTTP ve offline pending retry. |
| 15 | `passed` | Aynı son sıra/UUID farklı içerik 409; eski/aşılmış sıra güncel snapshot'ı ezmez. Retry penceresi son kabul olarak belgelenmiştir. |
| 16 | `passed` | Paralel sıralar bütün son duruma serialize olur. İstemci pending'i restart'ta aynı UUID/sıra/içerikle gönderir; credential rotasyonu sıra dönemini sıfırlamaz. |
| 17 | `passed` | Kontrollü sunucu saatiyle recent→stale; gelecek kaynak saati bağlantıyı recent tutamaz, kaynak `future` olarak ayrılır. |
| 18 | `passed` | Kimliği doğrulanmış aktarım `self_reported/not_verified` değerlerini yükseltmez; mapper/strict DTO ve gerçek E2E gözlemi. |
| 19 | `passed` | Termivar raporu scanner kurulum/çalışma iddiasına dönüşmez; online/enforce bildirimi enforcement kanıtı değildir; AV planned/unavailable kalır. |
| 20 | `passed` | Gerçek byte boyutu, duplicate key, NaN/Infinity, derinlik, boolean sayaç, extra alan ve ham veri atomik reddi. Yeni cihaz invalid snapshot sonrası never_seen kalır. |
| 21 | `passed` | Secret digest-only DB, sınırlı audit ve sabit hata cevapları; E2E DB/audit/server loglarında secret ve ham kaynak canary'si tarandı. Gerekli tek başarılı credential cevabı açık istisnadır; tüm olası veri kodlamaları için otomatik sır algılama iddiası yoktur. |
| 22 | `passed` | Gerçek PostgreSQL 18.6 migration, composite FK, yarış/rollback/retention; runtime ve migration hesapları ayrı. DB stop/start veri koruması ve kurulu wheel CLI migration yolu ayrıca geçti. |
| 23 | `passed` | Merkezî API ayrı süreç; CA imzalı TLS üzerinden üç bağımsız fixture istemci/iki tenant kayıt, snapshot, rotasyon ve iptal akışını tamamladı. `reports/e2e-inventory-flow.json`. |
| 24 | `passed` | Gerçek self-signed/yanlış güven sunucu sertifikası HTTP body gönderilmeden reddedildi. E2E fixture CA/hostname doğrulanır; verify=False yoktur. |
| 25 | `passed` | Saf mapper ve sender yerel kaynak/export dosyalarını değiştirmez; merkez offline olduğunda pending korunur ve hata döner. Gerçek TCP/TLS fixture ve kaynak bütünlüğü kanıtıdır; canlı Windows enforcement kesintisi denenmedi. |
| 26 | `passed` | Dar salt okunur indirme köprüsü `src/static/security_ecosystem.js` ve `tests/test_ecosystem_ui.js` içindedir; Python/server değişmez ve 2106+47 başlangıç sonucu korunur. Köprü sonrası sekiz UI paketi ve gerçek Edge oturum/UI import smoke'u 11 kontrolle tekrar geçti; gerçek panel görüntüsü yenilendi. |
| 27 | `passed` | Bu kayıt fixture/TestClient, gerçek PG, gerçek TCP/TLS süreçleri, gerçek tarayıcı ve çalıştırılmamış canlı Windows kabulünü ayrı gösterir. |

## Dış kabul ve üretim kapıları

| Kapı | Durum | Açıklama |
|---|---|---|
| Gerçek üretim IdP/API erişim token dağıtımı | `not_run` | Fixture issuer gerçek RS256 token üretir; kurumsal IdP kurulumu yapılmadı. |
| Fiziksel filo ve cihaz attestation | `not_run` | Üç fixture istemci fiziksel Windows makinesi değildir. |
| Canlı WinDivert/SCM/reboot/UAC/iki hesap | `not_run` | Önceki yerel Windows kabulü ayrıca açık kalır. |
| Yayıncı imzası ve gerçek Setup dağıtımı | `not_run` | EXE üretimi, imzalama veya dağıtım yapılmadı. |
| Üretim DB HA/backup-restore/felaket tatbikatı | `not_run` | Yerel fixture stop/start veri sürekliliği bunun yerine geçmez. |
| Docker/Compose kabulü | `not_run` | Docker mevcut değildi; resmî portable PostgreSQL yolu kullanıldı. |
| Otomatik yayın veya GitHub push | `not_run` | Yerel kaynak teslimatıdır. |

## Tekrarlama

Önce [OPERATIONS.tr.md](OPERATIONS.tr.md) ile gerçek portable PostgreSQL, migration ve dar runtime haklarını hazırlayın. Secret DSN veya JWT içeren dosyaları/exception locals yazdırmayın.

```powershell
./.venv/Scripts/python.exe -m pytest -q --tb=short
./.venv/Scripts/python.exe scripts/demo_acceptance.py
```

E2E komutu geçici public/özel fixture anahtarları, kendi API süreci ve kendi fixture istemcilerini oluşturur; üretim IdP veya Windows servisi kurmaz. Normal kaynak/delivery paketine secret dosyaları, DB data dizini, `.tooling`, sanal ortam veya gerçek credential girmez. Raporlarda yalnız sabit sonuçlar/sınırlı metrikler tutulur.

İkinci turun sonraki kapısı olan **sürümlü politika önizleme ve kontrollü dağıtım sözleşmesi**, saf ve yürütülemeyen kapsamıyla ayrı [kabul kaydında](POLICY_PREVIEW_ACCEPTANCE.tr.md) tamamlandı. Kalıcı revision/lineage, yeni komut yetkisi ve canlı Windows kabulü ayrıca değerlendirilmelidir.
