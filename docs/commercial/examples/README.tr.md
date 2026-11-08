# Sentetik teslimat örnekleri ve kaynak kaydı

**Demonstration only — No real system assessed.**

Bu dizin, mevcut benign/sentetik artefaktların **değiştirilmemiş kopyaları** ile yeni, insan tarafından yazılmış [Türkçe açıklama raporunu](DEMONSTRATION_REPORT.tr.md) içerir. Türkçe rapor native renderer çıktısı değildir. Bu tur Termivar/CLI/scanner, sunucu, test, build veya HTML/PDF renderer çalıştırılmadı; gerçek müşteri/uzman incelemesi veya düzeltme sonucu üretilmedi. Etiket bu rehber ve rapor için geçerlidir; native JSON şemalarını bozmamak için orijinal JSON byte'larına eklenmedi.

Üç ayrı örnek vardır: complete assessment + kısmi manifest çifti, bağımsız karşılaştırma ve elle yazılmış incomplete diagnostic. Bunlar tek bir çalışma, müşteri veya zaman çizgisi altında birleştirilmez. Gerçek hedef, credential, kullanıcı sırrı veya özel güvenlik kanıtı eklenmemiştir. Diagnostic içindeki `https://example.invalid` yalnız önceden var olan sentetik placeholder'dır; açılmamış veya değerlendirilmemiştir.

## Dosyalar ve byte kimlikleri

| Bu dizindeki dosya | Byte | SHA256 |
| --- | ---: | --- |
| `assessment.json` | 3907 | `c3104e05c372eab172f2247ae748d867b5e5e01d2adf4daa40d21e5515267ab9` |
| `manifest.json` | 711 | `c77ce74508e8efaff7ebf1b0203331b4295d468c726e4acd7bad709eb85813df` |
| `comparison.json` | 5674 | `291f5e7b407a247cb786119a249fe6f3cb9f5526e6700605c4a0008bee91a1d0` |
| `comparison-before.json` | 3795 | `33f709237ffea142d892891d818815251c1cb35d888abe155f7175e15d7d481f` |
| `comparison-after.json` | 3812 | `5ea44cfd6dbab132aa96e62813c32c12e35f0bf32c09b43a102a16e9ff7bbe64` |
| `incomplete-diagnostic.json` | 3465 | `85881c1d3883bb719cd05e7fbd63f564188371ddab58be94eb7e56c9e84d4f0a` |
| `TERMIVAR_LICENSE.txt` | 1085 | `d308383be39c28054876444bc46a410a5e753c7df982afce644fab1e7e9f754d` |

Dosya kopyalarının boyut ve SHA256'sı kaynak byte'larla karşılaştırıldı; JSON'lar parse edilip yeniden yazılmadı, satır sonları değiştirilmedi. Bu ölçüm kaynak kimliğini tanımlar; imza veya üretici attestation'ı değildir. Bu kayıttaki SHA256'lar, native öğelerin `sha256:` fingerprint alanlarından farklı olarak **tam dosya byte hash'leridir**.

[Termivar lisans bildirimi](TERMIVAR_LICENSE.txt), aynı pinli Termivar checkout'undaki [LICENSE](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/LICENSE) dosyasının değiştirilmemiş kopyasıdır; Termivar'dan kopyalanan örneklere eşlik eder. Platformdan gelen ayrı incomplete fixture veya diğer ürünler için yeni lisans vermez; mevcut lisanslar değiştirilmedi.

## 1. Ana complete örnek ve kısmi manifest

Kaynak checkout: `ITherso/termivar`, commit `6a2639348c2366d0bf71b9a34e5484d40aa393a3`. Bu tur kaynak salt okunur incelendi. Tam kaynak konumları:

- [assessment.json](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-bundle/assessment-001/assessment.json)
- [manifest.json](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-bundle/assessment-001/manifest.json)
- [Tarihsel generation kaydı L1–38](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-bundle/README.md#L1-L38)

Kaynak kayıt, örneği development source revision `e747db4153eb52e06664bcec9dcb3411daef6fe6`, `termivar 0.10.0-alpha.2` binary ve repository-owned sayısal loopback fixture üzerinde eski bir yerel çalışmaya bağlar. Üç assessment request'i ve ayrı self-comparison kaydı oradaki **tarihsel gözlemlerdir**; bu tur tekrar çalıştırılmadı. İncelenen güncel checkout hash'i, tarihsel generation hash'iyle karıştırılmaz.

`assessment.json` gerçek `venom-rendered-assessment/v1` alanlarını taşır: profile `web-review`, status `complete`, 1 subject ve 4 informational/observation öğe. Severity'ler `null`; case/outcome/verification stage yoktur. Opaque evidence referansları vardır, ham request/response teslim edilmez. Bu örnek NeedsReview veya Confirmed üretildiğini göstermez. Türkçe rapor, source başlık ve önerilerin insan tarafından açıklanmasıdır; yeni native bulgu veya Türkçe renderer özelliği değildir.

Manifestin JSON-entry hash/uzunluk/özet alanları bu ana dosyaya bağlanır. Manifest ayrıca `assessment.html` (8000 byte, SHA256 `a43070ee91860782a1eb47cd081b5fe628423a847bcc172e1a039cb6055cf1c1`) bildirir. **HTML buraya kopyalanmadı, okunmadı, render edilmedi veya doğrulanmadı.** Bu dizin tam report bundle değildir; yalnız JSON + manifest metadata'sıdır. Native `termivar report verify` çalıştırılmadı. Tarihsel source README'deki doğrulama sonucu bu dizinin güncel full-bundle kabulü olarak sunulmaz.

Native tam verifier'ın sınırları: sabit üç dosyalı layout, 64 KiB manifest, her payload için pozitif uzunluk ve en fazla 16 MiB, sabit format/media type, lowercase SHA256, producer SemVer (en fazla 128 byte), 1–1024 subject ve en fazla 4096 item; [parse_manifest L313–355](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-cli/src/report_verify.rs#L313-L355). Byte eşleşmesi özgünlük, scan scope/yetki, bulgu doğruluğu, düzeltme veya HTML güvenliği/anlamsal eşitliği değildir; [sınır kaynağı L411–419](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L411-L419).

## 2. Bağımsız dört gruplu karşılaştırma

Üç native dosya aynı checkout'taki şu kaynaklardan birebir kopyalandı:

- [comparison.json](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/comparison.json)
- [before.json](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/before.json) → yerel `comparison-before.json`
- [after.json](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/after.json) → yerel `comparison-after.json`

[Kaynak provenance.json](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/provenance.json), tarihsel çıktıyı source commit `664d385bd455a4fc5002b98a2103078cfba1be29` ve development package `0.10.0-alpha.2` ile kaydeder. [Kaynak rehber L1–27](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/README.md#L1-L27), girdilerin dört grubu göstermek için düzenlenmiş sentetik belge işleme verisi olduğunu açıkça belirtir. Bu tur CLI çalıştırılmadı; JSON çıktısı elle üretilmedi veya yeniden hesaplanmadı.

Gerçek projection `termivar-report-comparison/v1`; `only_in_after`, `only_in_before`, `changed`, `unchanged` gruplarında birer kayıt vardır. Changed kaydın tek `changed_fields` değeri `redacted_summary`'dir. Bu sayı ve alanlar var olan JSON'un açıklamasıdır; yeni güvenlik karşılaştırması yapılmış değildir.

Before/after özetleri, yukarıdaki iki dosyanın 3'er item içeren digestlerine bağlıdır. Ana `assessment.json` hash'i bunlardan farklıdır; **karşılaştırma ana assessment'ın retest'i veya müşteri değişim raporu değildir**. Kaynak `operator-declared`, `not-established`, `not-established-by-parsing` sınırlarını korur. Only-in-before düzeltilmiş; only-in-after yeni oluşmuş; unchanged güvenli veya eşit kapsamlı anlamına gelmez. [Yorum sınırları L567–597](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L567-L597).

## 3. Ayrı incomplete örnek

Kaynak, bu platformun önceden var olan `operator-console/src/features/termivarReview/examples/incomplete-example.json` dosyasıdır. Phase13 baseline platform commit `aa643d40797998d5f615cb5ba5b71b972596abc9` altındaki [aynı dosya](../../../operator-console/src/features/termivarReview/examples/incomplete-example.json) byte'ları korunarak kopyalandı. Bu bağlantı checkout içi kaynak yoludur; SHA256 yukarıda sabittir.

Bu dosya Phase11'de kaynak DTO'larından **elle yazılmış sentetik fixture** olarak hazırlanmıştı; CLI/scanner çıktısı, tarihsel runtime measurement veya expert bulgusu değildir. Kaynak semantiği [web-assessment/v2 diagnostic ayrımı L599–603](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md#L599-L603) ile ayrılır. `incomplete`, pending root subject, explicit sıfır wall-time bütçesi, `subject_execution_incomplete` / `wall_time_limit` ve unavailable item projection alanları korunmuştur. Authored sıfır sayaçlar ölçülmüş scan kullanımı olarak anlatılmaz.

Bu diagnostic ana complete örnekle veya karşılaştırmayla aynı çalışmaya ait değildir. Unavailable item projection, complete boş rapor veya “0 zafiyet” değildir. Bu dosya sözleşmenin eksik çalışma ayrımını gösterir; native constructor/CLI acceptance bu tur çalıştırılmadı.

## Kullanım sınırı

Dosyaları müşteri sonucu diye sunmayın. Bu dizin scope approval, raw evidence erişimi, uzman incelemesi, doğrulanmış zafiyet, düzeltme veya müşteri kabulü içermez. Gereken alanlar [örnek raporda](DEMONSTRATION_REPORT.tr.md) açıkça eksik bırakılmıştır. Gerçek müşteri raporu için [teslimat standardı](../DELIVERABLE_SPEC.tr.md) ve ayrıca onaylanmış pilot kapsamı gerekir. Burada yeni assessment veya satış süreci başlatılmaz.
