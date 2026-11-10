# Kaynak alanları, aktarım kuralları ve sınırlar

Native owning kaynak, Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3` altındaki [rendered DTO](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting.rs#L18308-L18330) ve [base importer](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs#L75-L129) sözleşmeleridir. Yeni bridge bunların tamamının native constructor/import kabulü olduğunu iddia etmez; alanları okuyan daha dar, demo-only metadata aktarımıdır.

## Sürüm ve destek profili

Yeni intake metadata sözleşmesi `termivar-assessment-intake/v1`, adapter sürümü `termivar-base-passive-handoff/v1`dir. Ayrı `intake-manifest.json` metadata şeması `termivar-assessment-intake-manifest/v1` kullanır. Bunlar native assessment veya Phase16 şemasının yeni sürümü değildir. Üretilen girdi değişmemiş **`termivar-handoff-draft/v1`** kullanır; mevcut [schema.py](../../../../tools/commercial_handoff/schema.py) ve aggregate bütçeleri yeniden uygulanır.

Native root'un dokuz alanı zorunludur: `schema`, `source_schema`, `run_schema`, `profile_schema`, `profile`, `status`, `subject_count`, `item_count`, `items`. Sabit değerler sırasıyla `venom-rendered-assessment/v1`, `venom-assessment-run/v1`, `venom-run/v1`, `venom.scan-profile/v1`, `web-review`, `complete`. Subject sayısı 1–1024; item sayısı 0–256 ve gerçek listenin uzunluğuna eşit olmalıdır. Ayrı `web-assessment/v2` diagnostic veya comparison bu profile çevrilmez.

İlk adapter'ın capability allowlist'i:

- `web.passive.referrer-policy.missing@1`
- `web.passive.x-content-type-options.missing@1`
- `web.passive.permissions-policy.missing@1`
- `web.passive.csp.missing@1`

Category yalnız `browser-defense` veya `content-policy` olabilir. Diğer geçerli native capability/category değerleri bu v1 adapter için desteklenmez. Native optional audit bölümlerinin 17 bilinen adı reader'da tanınır; **boş/null olsalar da varlıkları `unsupported_source_extension`** olur. Bilinmeyen root/item/remediation alanı kapalı hata verir; serbest metadata sessizce eklenmez.

## Native öğe ve yeni alanın ilişkisi

Native öğenin 20 alanı kontrol edilir. DTO'da yalnız kapalı metadata tutulur; serbest metin yeni çıktılara kopyalanmaz.

| Kaynak alanı | Kontrol / aktarım |
| --- | --- |
| `schema` | Tam `venom-assessment-item/v1`; mevcut sözleşme kimliği |
| `fingerprint` | `sha256:` + 64 lowercase hex; yeniden hesaplanmaz. Handoff `observation_ref` ve mapping'de korunur |
| `capability_id`, `category` | Yukarıdaki dar allowlist; capability handoff'a, category yalnız source mapping'e gider |
| `subject_reference` | Subject prefix/u32 indeksi ve kaynak subject_count ilişkisi; yalnız mapping metadata'sı |
| `disposition`, `claim_basis` | Kaynak enumları ve evidence/verifier bağı kontrol edilir. Disposition handoff'ta aynen kalır, insan kararı değildir |
| `evidence_count`, üç evidence reference listesi | Prefix/sayı, benzersiz birleşim, count eşitliği ve en fazla 256 referans. Yalnız opaque metadata source mapping'e gider; ham kanıt değil |
| `case_reference`, `outcome_reference`, `verification_stage` | Native ilişki için kontrol edilir; verifier-linkage sınıfı yeni çıktıya aktarılmaz |
| `title`, `redacted_summary`, `remediation.id/summary`, `cwe`, `severity`, `confidence_ppm` | Native tür/boyut/enum sınırları kontrol edilir; DTO ve handoff'a kopyalanmaz. Aktarılmayan sınıf adı mapping'de listelenir, özgün değer yazılmaz |

Remediation tam iki alanlıdır. Display metinler en fazla 1024 UTF-8 byte, identifier/CWE/remediation ID 128 byte; category nonempty string'dir. Severity `null` veya `info/low/medium/high/critical`, confidence strict int 0–1000000. Subject/evidence/case/outcome ref'leri reader'ın prefix/decimal u32 biçimiyle sınırlıdır; target veya dosya yolu sayılmaz.

`observation → informational`, `differential → needs_review`, `verifier_transition → confirmed` kaynak etiket ilişkileridir. Direct/control/candidate ve verifier bağlarının native kuralları [kaynakta](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs#L444-L485) ve [reference denetiminde](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison/import.rs#L611-L665) tanımlıdır. Bunları okumak, imported etiketi bağımsız onaylamak değildir. Mevcut native capability'ler `Confirmed` üretmez; bu araç da üretmez veya etiketi yükseltmez.

## Kimlik, yinelenen etiket ve insan durumları

Eşleme kimliği **gerçek assessment byte SHA256 + `/items/i` + mevcut fingerprint** bileşimidir. `OBS-01` gibi observation_id'ler array sırasından oluşturulan dahili aktarım etiketleridir; native observation/run kimliği yerine geçmez. `ART-A1` kaynak alias'ı ve `DEMO-TERMIVAR-017` vaka kimliği adapter'ın sabit demo etiketleridir; gerçek müşteri veya yetki kaydı değildir.

Phase17 §5 gereği aynı fingerprint farklı source pointer'larda gelirse birleştirilmez: her source pozisyonu ayrı korunur, `fingerprint_reuse_detected` bayrağı kaydedilir. **Native importer'ın fingerprint benzersizliği kuralı ile açık fark:** bu bridge reported metadata'yı konumuyla taşır; native tam import geçerliliği veya benzersizlik kabulü yapıldığını iddia etmez (`native_import_validation_performed=false`). Duplicate-fingerprint yürütmesi yapılmadıysa bu davranış `not_run` kalır. Kaynakta tekil görünen fingerprint de özgünlük/üretici kanıtı değildir.

Handoff'ta her kayda zorunlu olarak `review_status=unreviewed`, `scope_status=unknown`, `client_inclusion=pending_decision`, `safe_summary=null`, `decision_ref=null` verilir; `review_decisions=[]`. Kaynak disposition ve capability aynen, açıklamalar yalnız sabit adapter metninden alınır. Native başlık/özet, kişi, hedef veya review sözlüğü bu alanlara otomatik kopyalanmaz.

## Üç ayrı kapasite katmanı

| Katman | Sınır / anlam |
| --- | --- |
| Native importer | Kaynakta 16 MiB / 4096 item; bridge'nin kapasitesi veya kapsam vaadi değildir |
| Yeni assessment reader | 1 MiB; 256 item; depth12; key'ler dahil 50000 node; key+value metni toplam512 KiB UTF-8; tek parsed string8192 karakter; native alan byte sınırları ayrıca uygulanır |
| Mevcut Phase16 girdisi | 256 KiB JSON; 256 observation; 10000 node; toplam128 KiB UTF-8 metin ve mevcut exact field/type/enum sınırları |

Kaynakta sığan 256 kayıt, üretilen Phase16 girdisinin bütün bütçelere de sığacağını garanti etmez. `validate`, depth/tree ve serialized byte sınırları **yayından önce** uygulanır; taşma kapalı hata olur. İlk N kayıt alınmaz; reddedilmiş zorunlu öğe varken başarı manifesti yazılmaz.

İki okuyucuda strict UTF-8/no BOM, duplicate JSON key reddi, float/exponent/NaN/Infinity reddi ve strict integer/bool ayrımı vardır. Integer literal 20 karakterle sınırlıdır. Girişteki başlık/path/URL gibi değerler dosya/ağ talimatı değildir. [Reader](../../../../tools/commercial_intake/assessment_reader.py), [handoff adapter](../../../../tools/commercial_intake/handoff_adapter.py) ve [source mapping](../../../../tools/commercial_intake/source_mapping.py) gerçek uygulamadır; hata, sınır ve alternatif profil davranışları çalıştırılmadıkça kabul edilmiş sayılmaz.
