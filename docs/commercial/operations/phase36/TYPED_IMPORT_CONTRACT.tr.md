# Phase36 typed import sözleşmesi

**OFFLINE DEMONSTRATION — TYPED CSV IMPORT ONLY — NO CURRENT SOURCE VERIFICATION**

Yeni inbox'ın reference/projection kayıtları gerçekten parse edilmiş Phase35 CSV DATA hücrelerinden oluşturulur. Phase35 dataset JSON kapalı owner doğrulaması ve alan/tür/değer eşliği için kullanılır; kayıtları kopyalamak CSV import değildir. Kapsül ZIP'i veya eski guard açılmaz. Typed parsing, ilişki doğrulaması, snapshot ve query saf metadata işlemleridir.

## Beş girdi ve request

Girdi yalnız açık `tabular-dataset.json`, `reference-register.csv`, `projection-register.csv`, `tabular-summary.md`, `manifest.json`. Gerçek manifest dört payload'ın byte/SHA256 bağını taşır. Dataset mevcut owner validator ile doğrulanır; Markdown owner renderer ile byte eşlenir; iki CSV gerçekten parse edilip typed kayıtları dataset'le eşlenir ve mevcut CSV renderer ile tam canonical byte reconciliation sağlanır. Ancak sonra exact immutable validated import oluşturulur.

`termivar-offline-tabular-inbox-request/v1` tam beş alan:

| Alan | Anlam |
| --- | --- |
| `schema_version` | Yalnız desteklenen request v1 |
| `mode` | Yalnız `demo` |
| `request_reference` | Sınırlı yerel demo kimliği; kullanıcı yetkisi değildir |
| `source_manifest_sha256` | Gerçek kaynak Phase35 manifest byte'larının SHA256 beklentisi |
| `requested_reference_ids` | İçe alınmış inbox'ta bulunan 1–8 farklı açık reference ID |

Boş/duplicate/unknown seçim veya yanlış hash kapalı hatadır. Yeni candidate/path, override, risk skoru veya sorgu ifadesi yoktur.

## Immutable typed inbox

`termivar-offline-tabular-inbox/v1` ortak schema/demo etiketi/`demo_only=true`/18 false bayrakları; `source_artifacts`, `source_dataset_schema`, `reference_records`, `projection_records`, `reference_projection_links`, dokuz `counts`, `import_scope` ve sabit `limitations` taşır. Source artefact listesi yalnız beş sabit dosya adı/gerçek byte/SHA256 descriptor'ıdır; yerel source path veya kapsül payload'ı değildir.

Reference kaydı mevcut dört alanı korur: `reference_id`, `disclosure_status`, `projection_count`, `interpretation_limitations`. Projection kaydı mevcut 11 izinli alanı korur. `reference_projection_links` her reference için yalnız `reference_id` ve izinli `candidate_ids` listesidir; bloke referansta liste boştur. Reference projection count ile gerçek typed kayıt/ilişki sayısı eşleşir. Bilinen fakat projection'sız referans otomatik missing sayılmaz.

Saf `build_typed_inbox(validated_tabular_import)` yalnız gerçek owner doğrulaması ve canonical CSV reconciliation sonrası oluşturulan exact immutable modeli tüketir. Caller'ın `validated=true`, `trusted=true`, `guard_passed=true`, `source_verified=true` alanları otorite değildir. Model dışındaki metadata veya eksik alan için default/pozitif tahmin yoktur.

## Query ve receipt

`termivar-offline-tabular-reference-query/v1` ortak güven alanlarını, tam request'i, kaynak manifest descriptor'ını, reference bazlı sonuçları, seçilmiş sonucun dokuz sayımını, query scope ve sınırlamaları taşır. Her sonuç mevcut reference'ın dört alanı ve `projections` listesidir. `query_reference_metadata(validated_inbox, requested_ids)` yalnız içe alınmış kayıtları kullanır. All-or-nothing korunur: provided ref'in izinli projection'ları bütündür; withheld için `projections=[]`; olumlu child metadata audit'e kopyalanmaz.

`termivar-offline-tabular-import-receipt/v1` ortak güven alanları, beş artefact descriptor'ı, kaynak dataset/manifest schema kimlikleri, iki fixed header listesi, reference/projection veri satırı sayıları, import sayımları ve kaydedilmiş reconciliation durumlarını taşır. `canonical_CSV_reconciliation=matched_during_import`, `dataset_CSV_relation=typed_values_equal_during_import` import anının kayıtlarıdır; bağımsız özgün kaynak doğrulaması değildir. Receipt projection payload'ı taşımaz.

Inbox kapsamı beş açık Phase35 artefact ve canonical CSV typed records; query kapsamı yalnız bellekte içe alınmış reference metadata; receipt kapsamı yalnız beş-artefact import ilişkisidir. Kaynak CSV'leri yeniden parse etmeyen yeni inspector bu kaydedilmiş import davranışını bağımsız kanıtlamaz.

Yeni dış manifest `termivar-offline-tabular-inbox-manifest/v1`, inspector çıktısı `termivar-offline-tabular-inbox-inspection/v1` sözleşmesidir. Manifest ilk dört gerçek yeni payload'ı bağlar; kendisini veya inspector çıktısını kapsamaz.

## Tip ve limit sınırları

Null, empty string, integer zero, string zero ve empty list ayrı kalır. Mevcut Phase35 DATA hücre türleri boolean kabul etmez: false sıfıra coercion yapılmadan reddedilir. Ortak false güven bayrakları ise ayrı boolean metadata'dır. Alanın daha sıkı sözleşmesi boş string/list gibi değerleri ayrıca reddedebilir. Float/NaN/Infinity ve bool-as-int kabul edilmez.

Request 32 KiB; kaynak dataset/CSV/MD 128 KiB, kaynak manifest 64 KiB/toplam açık girdi 1 MiB. Inbox 256 KiB, query/MD 128 KiB, receipt 64 KiB; reference 8/projection 64/depth 12/node 20.000/text 512. DATA hücre 4096 B/satır 65536 B owner sınırı korunur. Strict UTF-8, duplicate/unknown schema/field/record reddi; truncation, overwrite, otomatik silme veya kısmi başarılı kabul yoktur.

Bu sözleşme producer/source freshness/guard/compiler/ownership/insan/hukukî/release kanıtı değildir. Actual komutlar ve çıktı kimlikleri teslim kaydındadır; hostile runtime kabulü bu belgeden çıkarılmaz.
