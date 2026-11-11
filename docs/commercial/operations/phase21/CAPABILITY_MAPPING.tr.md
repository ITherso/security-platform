# Plan ve assessment capability eşlemesi

**DEMONSTRATION ONLY — PLAN AND ASSESSMENT EXECUTION LINK NOT ESTABLISHED**

Kaynak Phase20 kataloğu 11 satırlık sınırlı envanterdir. `assessment_item`,
`graphql_catalog` ve `cli_surface` namespace'leri ayrıdır. Kimlik metninin
benzemesi namespace dönüşümü oluşturmaz. GraphQL metadata ailesi veya CLI API
stub'ı assessment gözlemi olarak sunulmaz.

Mevcut assessment okuyucusu korunmuş Phase17 base-passive alt kümesini kullanır:
`venom-rendered-assessment/v1`, `web-review`, `complete`, dört informational
capability. Yeni bir genel native importer/evaluator kurulmaz. Audit/opsiyonel
profil, farklı item türü veya desteklenmeyen şema bu alt kümede kabul edilmez.
Bu sınırlama native Termivar'ın bütün yeteneklerinin sınırı değildir.

| Phase20 gerçek assessment-item ID | Assessment alanı ve anlamı |
| --- | --- |
| `web.passive.referrer-policy.missing@1` | `items[i].capability_id`, informational/observation |
| `web.passive.x-content-type-options.missing@1` | `items[i].capability_id`, informational/observation |
| `web.passive.permissions-policy.missing@1` | `items[i].capability_id`, informational/observation |
| `web.passive.csp.missing@1` | `items[i].capability_id`, informational/observation |

Kimliklerin native kaynağı pinlenmiş Termivar commit'i
`6a2639348c2366d0bf71b9a34e5484d40aa393a3` altında
`crates/termivar-scanner/src/web_runtime/assessment_passive.rs:164–266`;
disposition sınırı `assessment_item.rs:1811–1869` ve `docs/reporting.md:156–163`.
Phase20 katalog entry'leri gerçek source ID/path/SHA/line referanslarını taşır.
Phase21 bu dosya yollarını otomatik açmaz veya güncel binary kabulü saymaz.

Somut reader/adapter kaynakları:

- `tools/commercial_scope/plan_builder.py`: gerçek plan alanları ve içerik ID tarifi.
- `tools/commercial_scope/capability_catalog.py`: namespace/kind ve sınırlı katalog.
- `tools/commercial_intake/assessment_reader.py`: kapalı native metadata DTO'su.
- `tools/commercial_intake/source_mapping.py`: gerçek `/items/i` observation bağı.
- `tools/commercial_intake/provenance.py`: kısmi JSON-entry manifest sınırı.
- `tools/commercial_review/packet_builder.py`: mevcut Phase17 payload bağları.

Assessment → Phase17 bağı gerçek assessment SHA/uzunluğu, tam mapping metadata'sı,
gerçek pointer, fingerprint, capability, disposition, subject ve evidence
ilişkileriyle karşılaştırılır. Gerçek mapping ve handoff dosyalarının byte/hash
kimlikleri intake manifestiyle bağlanır. Handoff kimliği tahmin edilmez; açık
argümanla seçilen dosya gerçekten okunur.

Tekrarlanan fingerprint ayrı kaynak pointer'larında kalır; native tam importer'ın
benzersizlik kabulü sağlanmış sayılmaz. Opaque evidence referansları HTTP
kanıtını içermez ve içeriğin doğruluğunu kanıtlamaz. Pointer uyuşmazlığında en
yakın fingerprint veya başka observation aranmaz.

Assessment JSON'u origin, target, run ID, zaman, effective limit veya tüketim
bildirmez. Native `reporting.rs` içindeki presentation target serialize edilmez.
Bu nedenle aynı profil ve dört capability eşleşse bile hedef/kapsam, bütçe
gerçekleşmesi ve plan execution bağı çıkarılamaz. Eksik gözlem başarısız kontrol
veya güvenli sistem sonucu değildir.
