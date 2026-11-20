# Phase44 içe alma akışı, doğrulama ve hata davranışı

**OFFLINE DEMONSTRATION — UNTRUSTED CAPSULE RECONCILIATION ONLY — NO TASK DISPATCH, ASSIGNMENT, APPROVAL, EXECUTION OR SUBMISSION**

## Akış

1. **Açık girdiler.** CLI yalnız komut satırında verilen yolları açar; çalışma alanını taramaz. Okumalar mevcut Phase43 `phase42_adapter.InputBudget` ile yapılır: göreli yol, link/reparse reddi, tek hard-link, boyut sınırı ve toplam 1 MiB bütçe. İstek en fazla 8 KiB, capsule dosyası en fazla 131072 byte olabilir.
2. **Yerel referans anlık görüntüsü** (`local_task_records.py`). Yalnız isteğin belirttiği gruplar yüklenir, ikisi de owner'lar üzerinden:
   - Phase42 beşlisi `phase42_adapter.load_source/read_source` ile yüklenir. Owner register, classification, receipt, summary ve tam manifest eşliğini doğrular.
   - Phase43 beşlisi değiştirilmemiş Phase43 `inspect_task_exchange()` fonksiyonuyla doğrulanır. Ardından aynı beş dosya bütçeyle yeniden okunur ve byte kimliklerinin owner raporundakilerle aynı olduğu kontrol edilir; arada değişen dosya reddedilir. Açıklanan görevler Phase43 recipient reader ile kayıtlı capsule'dan okunur.
   - İki grup verilmişse Phase43 kaynak digest'leri yerel Phase42 register ve manifest hash'lerine eşit olmalıdır. Aksi halde girdi reddedilir.
3. **ZIP envanteri** (`capsule_zip_inventory.py`). Bellekte, central directory metadata'sı okunur. Hiçbir şey diske açılmaz. Sınırlar ve kontroller:
   - En fazla 16 üye listelenir; fazlası sayılır ve bulgu üretilir.
   - Ad tehlikeleri: mutlak yol, `..`, ters bölü, iç içe yol, dizin girdisi, kontrol karakteri, ASCII dışı karakter, boş veya aşırı uzun ad, büyük-küçük harf çakışması.
   - Duplicate ve beklenmeyen üyeler.
   - ZIP_STORED dışı sıkıştırma, şifreleme bayrağı, düzenli dosya olmayan girdi (örneğin symlink).
   - Central directory'de extra alanı veya ZIP64 işareti (`0xFFFFFFFF` boyut ya da offset).
   - Duplicate adlar ilk 16 üye için ad başına bulgu üretir; sonrası tek bir toplu bulguda birleşir. Bir rapordaki bulgu sayısı en fazla 400'dür; aşılırsa `FINDINGS_TRUNCATED` eklenir.
   - Üye başına Phase43 sınırları, toplam açılmış boyut (131072 byte), üye sırası ve arşiv yorumu.
4. **Byte okuma kapısı.** Üye byte'ları yalnız bütün container kapıları geçildiğinde okunur. Okuma `limit+1` ile sınırlıdır; boyut veya CRC uyuşmazlığı `MEMBER_READ_ERROR` bulgusu üretir. STORED olmayan bir üye asla açılmaz.
5. **İçerik yorumu** (`capsule_claims.py`). Her kural bir Phase43 owner fonksiyonudur:
   - Owner `parse_json`: strict UTF-8, duplicate anahtar, float/NaN, derinlik ve düğüm sınırı.
   - Alan başına owner validator'lar: `task_id`, `digest_id`, `identifier`, `sha256`, `fixed`.
   - Owner `exchange_counts`, `validate_portable_request`, `validate_response_contract`.
   - Canonical `json_bytes` karşılaştırması.
   - Sabit README byte'ları.
   - Owner `capsule_manifest_data` ile inner manifest eşliği.
6. **Phase43 owner reader.** `recipient_reader.inspect_task_exchange_capsule` aynı byte'lar üzerinde değiştirilmeden çalıştırılır. Uyumluluk kararını yalnız bu reader verir.
7. **Fail-closed çapraz kontrol.** Owner reader kabul ettiği halde Phase44 tanılaması engelleyici bir sorun bulursa ya da beyan edilen kimlik owner'ın okuduğu kimlikten farklıysa `DIAGNOSTIC_OWNER_DISAGREEMENT` bulgusu üretilir ve sonuç `STRUCTURAL_REJECTION` olur.
8. **Yerel mutabakat** (`identity_reconciliation.py`). Yalnız yapısal olarak geçerli capsule için yapılır; reddedilen capsule'da yerel kayıtlara hiç bakılmaz. Ardından uygunluk durumu, inbox kaydı, rapor, Markdown özet ve manifest üretilir.
9. **Yayın.** Girdi kararlılığı tekrar kontrol edilir. Çıktılar yalnız **yeni** bir dizine yazılır; var olan dizin reddedilir. Yol kuralları owner'dan gelir (`capsule_manifest.explicit_path`, `check_path`, `same_directory`): göreli yol, `..` yok, link/reparse yok, üst dizin mevcut ve dizin olmalı. Yayının kendisi Phase44'e aittir ve **hard link gerektirmez**:
   - Çıktının üst dizininde `tempfile.mkdtemp` ile bu çalıştırmaya ait bir stage dizini (`.task-reconciliation-*`) açılır.
   - Her dosya `open(..., "xb")` ile yazılır, `flush` ve `os.fsync` yapılır.
   - Stage dizini tek bir `os.rename` ile çıktı adına taşınır. Stage aynı üst dizinde olduğu için işlem tek volume'da kalır; Windows var olan hedefe rename'i reddeder.
   - Herhangi bir hatada yalnız bu çalıştırmanın stage içinde yazdığı dosyalar (aynı cihaz ve inode) silinir, stage dizini kaldırılır ve hata yeniden yükseltilir. Boş veya yarım çıktı dizini kalmaz, bu yüzden aynı `--output-dir` ile yeniden deneme engellenmez. Çalıştırmanın oluşturmadığı hiçbir şey silinmez; arada başka biri hedefi oluşturduysa hedefe dokunulmaz ve `..._output_directory_must_be_new` kodu verilir.
   - Inspector'ın `inspection-summary.json` dosyası da aynı yolla yayımlanır: stage içinde yazılır, sonra tek dosya rename edilir.

   POSIX notu: Kontrol ile rename arasında aynı yolda bir hedef oluşturulursa POSIX `rename` iki durumda o hedefin yerine geçebilir: hedef **boş** bir dizinse veya inspector'ın tek dosyalık `inspection-summary.json` çıktısıysa. Bu yarış penceresi kısa bir ön kontrolle daraltılır ama kapatılmaz. Windows'ta rename mevcut hedefi reddeder. Demo Windows üzerinde çalıştırılmıştır.

## Capsule yapısı (Phase43, değişmedi)

Capsule tam olarak dört STORED üyeden oluşur, sıra önemlidir: `task-request.json`, `response-contract.json`, `README.txt`, `capsule-manifest.json`.

Üye sınırları sırasıyla 64, 32, 4 ve 32 KiB'dir. Inner manifest ilk üç üyeyi byte ve SHA256 ile bağlar; kendi hash'ini içermez. Canonical biçim: sabit 1980-01-01 tarihi, Unix regular 0600, boş extra/comment, flags 0. Phase44 bu biçimi değiştirmez ve onarmaz.

## Fail-closed davranışı

| Durum | Sonuç |
| --- | --- |
| Duplicate üye, traversal, mutlak yol, beklenmeyen üye, aşırı büyük üye veya arşiv, sıkıştırma, şifreleme, eksik üye | Container `REJECTED`, içerik `NOT_EVALUATED`, `STRUCTURAL_REJECTION` |
| Bozuk JSON, duplicate anahtar, desteklenmeyen şema, canonical olmayan JSON | İlgili `MEMBER_*` / `SCHEMA_*` bulgusu, `STRUCTURAL_REJECTION` |
| README farkı | `README_FIXED_TEXT_MISMATCH` bulgusu, `STRUCTURAL_REJECTION` |
| Inner manifest hash uyuşmazlığı, eksik, duplicate veya bilinmeyen manifest kaydı | `MANIFEST_*` bulgusu, `STRUCTURAL_REJECTION` |
| Görev kimlik alanlarında (task_id, reference_id, candidate_id, file_id, binding_digest) bozuk, eksik, null veya boş değer | `IDENTITY_*` bulgusu, `STRUCTURAL_REJECTION`. Geçersiz string yazılmaz; integer, boolean ve null değerler yazılır. Envelope düzeyindeki alanlar (request_reference, kaynak digest'leri) `FIELD_*` bulgusu üretir. |
| Sayı beyanı uyuşmazlığı, duplicate görev veya binding, sırasız görevler, görev nesne değil | `TASK_*` bulgusu, `STRUCTURAL_REJECTION` |
| Geçerli capsule ama yerel değer farklı veya binding başka göreve ait | `IDENTITY_MISMATCH` |
| Geçerli capsule ama yerel kayıt yok veya görev bulunamadı | `LOCAL_RECONCILIATION_UNAVAILABLE` |

Bozuk capsule hiçbir zaman onarılmaz, normalize edilmez veya kısmen kabul edilmez. Rapor yalnız neyin neden reddedildiğini anlatır.

## CLI

İçe alma için komutu çalışma alanı kökünden çalıştırın; bütün yollar o köke göreli olmalıdır:

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_reconciliation/import_task_capsule.py --capsule <capsule.zip> --request <request.json> [--local-register R --local-classification C --local-intake-receipt I --local-intake-summary S --local-intake-manifest M] [--disclosed-capsule Z --disclosed-index X --disclosed-receipt P --disclosed-summary Q --disclosed-manifest N] --output-dir <yeni-dizin>
```

Yerel gruplar ya tamamen verilir ya hiç verilmez. Verilen gruplar isteğin `local_reference_mode` değeriyle eşleşmelidir.

Çıkış kodları:

| Kod | Anlamı |
| ---: | --- |
| 0 | Çıktılar yayımlandı, durum `STRUCTURALLY_VALID_REQUIRES_MANUAL_REVIEW` |
| 3 | Çıktılar yayımlandı, durum uygun değil (red, uyuşmazlık veya yerel kayıt yok) |
| 2 | Argüman, girdi, pin veya yerel kayıt reddedildi; hiçbir şey yayımlanmadı. 131072 byte'tan büyük capsule dosyası da bu koddadır, çünkü okunmadan reddedilir. |
| 1 | Beklenmeyen hata; başarı iddia edilmez. Yayın sırasında olduysa stage geri alınır, çıktı dizini oluşmaz. |

Exit 2'de stderr sabit hata kodunu yazar:

```text
task_reconciliation: rejected: <kod>; nothing published
```

Kod yalnız `[A-Za-z0-9_]` karakterlerinden oluşur (`capsule_claims.owner_code`). Kod bu biçime uymuyorsa `owner_code_unrepresentable` yazılır. Dosya yolu, token, politika içeriği veya kullanıcı verisi yazılmaz. Sık görülen kodlar:

| Kod | Anlamı ve çözüm |
| --- | --- |
| `task_reconciliation_invalid_output_directory_must_be_new` | `--output-dir` zaten var. Yeni bir ad verin. |
| `task_reconciliation_output_parent_missing` | `--output-dir` üst dizini yok. Önce üst dizini oluşturun. |
| `task_reconciliation_publication_path_or_state_rejected` | Çıktı yolu owner kurallarını ihlal ediyor: mutlak yol, `..`, link/reparse, üst yol dizin değil veya yayın sırasında dizin değişti. |
| `task_reconciliation_invalid_partial_local_record_group` | Bir yerel grubun beş seçeneğinin hepsi verilmedi. |
| `task_reconciliation_invalid_local_path_groups_do_not_match_request_mode` | Verilen gruplar isteğin `local_reference_mode` değeriyle uyuşmuyor. |
| `task_reconciliation_invalid_local_phase42_register_pin` (ve benzer `..._pin` kodları) | Yerel dosya hash'i istekteki pin ile eşleşmiyor. |
| `task_exchange_binary_input_rejected`, `task_exchange_text_input_rejected` | Girdi yolu reddedildi: mutlak yol, `..`, link/reparse veya okunamayan dosya. |
| `task_exchange_binary_size_or_hardlink_rejected` | Capsule dosyası 0 byte, sınırdan büyük ya da birden fazla hard link'e sahip. 0 byte capsule için rapor üretilmez. |

Açıkça verilen bir girdi dosyası yoksa stderr `task_reconciliation: missing_explicit_input` yazar (exit 2). Exit 1'de stderr `task_reconciliation: rejected; no reconciliation is claimed` yazar.

Bağımsız inceleme aynı girdileri alır, ek olarak dört çıktıyı ve yeni bir `--output` JSON yolunu ister:

```powershell
python -I -B security-platform-phase43-source/tools/commercial_task_reconciliation/inspect_task_reconciliation.py <aynı girdiler> --inbox <d>/task-inbox-record.json --report <d>/capsule-reconciliation-report.json --summary <d>/capsule-reconciliation-summary.md --manifest <d>/manifest.json --output <d>/inspection-summary.json
```

Inspector çıkış kodları: 0 uyumlu; 2 uyuşmazlık veya ret (dosya yazılmaz); 1 beklenmeyen hata.

Exit 2'de stderr bir neden ve sabit kodu yazar:

```text
task_reconciliation_inspection: <neden>: <kod>; nothing published
```

| Neden | Kod | Anlamı |
| --- | --- | --- |
| `outputs_disagree_with_independent_recomputation` | `task_reconciliation_inspection_disagreement_<kontrol>` | İlk başarısız kontrolün adı sondadır: `non_canonical_*`, `output_manifest_identity`, `input_identity`, `capsule_identity`, `request_reference`, `local_reference_mode`, `phase43_owner_reader`, `eligibility`, `mismatch_without_finding`, `lifecycle`, `rejected_capsule_admitted`, `inbox_report_tasks`, açıklama sınırı kontrolleri (`forbidden_disclosure_key`, `local_reference_not_input_identity`, `rejected_capsule_local_value`, `echoed_value_without_local_record`, `echoed_value_differs_from_local_record`, `match_local_value_differs`, `undisclosed_local_value_echoed`, `lookup_names_unclaimed_task`), `summary`, `regeneration`. |
| `inspection_output_already_exists` | `task_reconciliation_invalid_inspection_output_must_be_new` | `--output` dosyası zaten var; mevcut dosyaya dokunulmaz. Yeni bir ad verin. |
| `input_or_contract_rejected` | örneğin `task_reconciliation_inspection_output_parent_missing`, `task_reconciliation_invalid_inspection_json_required`, `task_reconciliation_inspection_publication_rejected` veya import tablosundaki girdi kodları | Girdi, çıktı yolu veya sözleşme reddedildi. |

Açıkça verilen bir dosya yoksa stderr `task_reconciliation_inspection: missing_explicit_input_or_output_file` yazar (exit 2).

Inspector şu on kontrolü yapar:

1. Çıktı modelleri kapalı ve canonical mı.
2. Manifest gerçek çıktı byte'larıyla eşleşiyor mu.
3. Manifestteki girdi kimlikleri şu anki girdilerle eşleşiyor mu.
4. Capsule kimliği yeniden hesaplanıyor.
5. Phase43 owner reader bağımsız olarak yeniden çalıştırılıyor.
6. Uygunluk, raporun kendi kanıtından ayrı bir kural kodu ile yeniden türetiliyor.
7. Inbox'ın rapordan türediği kontrol ediliyor.
8. Açıklama sınırı kontrol ediliyor:
   - yasak anahtarlar;
   - `local_reference` alanının yalnız girdi kimliklerinden oluşması;
   - reddedilen capsule'da hiç yerel değer bulunmaması;
   - yazılan her yerel değerin, yerel kayıtta o satırın (kaynak, konu, alan) üçlüsü için tutulan değerle aynı olması. `MATCH` satırları da bu kontrole girer. Beklenen değer, inspector'ın owner reader'dan kendisinin okuduğu görevler ve yerel kayıt üzerinden ayrıca hesaplanır;
   - `MATCH` olmayan bir satırda yazılan yerel değerin o satır için açıklanmış sayılması. Phase43 açıklama kaydındaki değerler (çok görevli kayıtta virgülle birleştirilmiş `task_id_list` dahil) ve açık girdi dosyalarının kimlikleri açıklanmış sayılır. Bir Phase42 görev değeri ise ancak Phase43 kaydı aynı görev ve alan için aynı değeri belirtiyorsa açıklanmış sayılır;
   - görev aramalarının (`task_lookups`) yalnız capsule'ın beyan ettiği görevleri adlandırması.

   Bu kontrol yapısaldır. Builder yerel kayıt verisini yalnız karşılaştırma `local_value`, `local_reference` ve manifest `inputs` alanlarına yazar; inspector tam olarak bu alanları denetler. Çıktı byte'larında substring araması yapılmaz, çünkü capsule kaynaklı metin (üye adları, JSON kaçışlı değerler, Phase44'ün hesapladığı hash'ler) yerel bir kimliğe benzeyebilir.
9. Markdown özet yeniden render ediliyor.
10. Bütün mutabakat yeniden üretiliyor ve byte-identical olması isteniyor.

## Çıktı yapısı

| Dosya | İçerik |
| --- | --- |
| `task-inbox-record.json` | Güvenilmeyen inbox kaydı: yaşam döngüsü aşaması, uygunluk ve karantinadaki görevler |
| `capsule-reconciliation-report.json` | Tam deterministik rapor |
| `capsule-reconciliation-summary.md` | Raporun inert Markdown görünümü |
| `manifest.json` | İlk üç dosyanın byte/SHA256 kimliği ve her açık girdinin rol/byte/SHA256 kimliği (kendisi hariç) |
| `inspection-summary.json` | Ayrı inspector çağrısının sonucu |

Çıktılarda saat, mutlak yol veya kullanıcı adı yoktur. Aynı capsule, istek ve yerel girdiler aynı byte'ları üretir.
