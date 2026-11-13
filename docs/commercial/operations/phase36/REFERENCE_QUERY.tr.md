# Phase36 immutable inbox üzerinde reference query

**OFFLINE DEMONSTRATION — TYPED CSV IMPORT ONLY — NO CURRENT SOURCE VERIFICATION**

Sorgunun veri kaynağı gerçekten parse edilmiş Phase35 CSV hücrelerinden oluşturulan immutable typed inbox'tır. Kaynak kapsül lookup'ı taklit edilmez; ZIP/Phase31/Phase34/native dosyası veya internet açılmaz. Dataset JSON yalnız owner doğrulama ve CSV içerik karşılaştırmasıdır. Yeni snapshot caller'ın mutable trusted/allow işaretine güvenmez.

## Reference merkezli kapalı sorgu

Request schema/mode/request reference/source manifest SHA256/requested reference ID listesiyle sınırlıdır. Yalnız demo; 1–8 farklı içe alınmış ID; boş/duplicate/unknown ID veya yanlış manifest hash'i kapalı hata. Query ifadesi, candidate seçimi, dosya yolu, override veya risk skoru yoktur.

`query_reference_metadata(validated_inbox, requested_ids)` her istenen referansın ID, disclosure status, projection count, interpretation limitations ve izinliyse bütün typed projection listesini döndürür. Referans düzeyinde all-or-nothing: olumlu bir alt kayıt bloke kararı aşmaz; `withheld_by_existing_guard` için `projections=[]`. Bloke candidate/file/hash/byte başka query/audit alanına kopyalanmaz. Bilinen fakat projection'sız reference otomatik source missing sayılmaz.

Reference-to-projection candidate ilişkileri ve gerçek sayılar kaynak CSV kayıtlarından türetilir. Bir reference kaydının bulunması olumlu file metadata yetkisi değildir. Query sayımları yalnız istenen subset'e aittir; inbox/receipt sayımları bütün import kapsamıdır. Bu paydalar karıştırılmaz. Source absence null; reference count integer zero; string zero ve empty list ayrı tür/değerlerdir. Mevcut DATA boolean desteklemez ve false sıfıra coercion yapılmaz.

## Receipt ve inspector sınırı

Receipt beş gerçek kaynak artefact'ın sabit adı/byte/SHA256 kimliğini, dataset/manifest schema, fixed iki header listesi, CSV data-row sayıları, import counts ve kaydedilmiş canonical CSV/dataset eşliğini taşır. Hash'ler imza veya yetkili üretici kimliği değildir. Saldırganın bütün girdileri beraber değiştirmesine karşı producer attestation sağlanmaz. Receipt ikinci host'a aktarım veya source freshness kanıtı değildir.

Yeni inspector yalnız beş açık yeni inbox/query/receipt/summary/manifest dosyasını okur; query'nin inbox'tan yeniden türetilebilmesi, typed ref/projection bağları, null/zero/boolean ayrımı, receipt kaynak kimlikleri, sayımlar, Markdown ve dört payload manifest byte eşliğiyle sınırlıdır. Kaynak Phase35 CSV'lerini yeniden parse etmez ve import davranışını bağımsız doğrulamaz; kapsül/guard veya native source açmaz. `content_consistent` yalnız bu yeni modellerin iç tutarlılığıdır.

`demo_only=true`; kaynak/context/independent observation ve upstream guard dahil 18 güven alanı false kalır. Producer/compiler/module closure/ownership/native/human/legal/customer/production/release yetkisi kazanılmaz. Kayıtlı upstream fresh kodları önceki metadata'dır; yeni gözlem veya TTL garantisi değildir. Kimlik/hash hassas olabilir; minimizasyon şifreleme/anonimlik değildir.

## Kod bağımlılığı ve açık kabuller

Yeni kaynak delta paketi standalone binary/wheel değildir. Korunmuş Phase35 validator/CSV encoder/renderer/manifest ve güvenli yardımcı kodları gerekir; bu kod bağımlılığı eski kapsül veya kaynak çalışma alanı verisine erişim değildir. Yeni ZIP eski dependency kodunu veya eski faz verilerini kopyalamaz. İkinci offline host'ta çalıştırma/aktarım veya gerçek spreadsheet import kabulü yapılmadıkça NOT_RUN kalır. Kaynak import grafiği incelemesi bu runtime kapılarını geçmez.

Hostile JSON/UTF-8/BOM, formula/quoting/header/canonical cell/null-empty-zero adversarial, duplicate ref/projection, wrong hash veya değiştirilmiş CSV/dataset, limit/permission/crash/partial write/repeat determinism, gerçek guard/source freshness/compiler/module closure/ownership/native/producer/human/legal/customer/release kabulleri NOT_RUN olabilir; actual kapsam teslim kaydındadır. Test/runner/coverage/typecheck/build/install ve Phase19 UI kabulü beklemededir. Kodda koruma olması testlerin geçtiği anlamına gelmez.
