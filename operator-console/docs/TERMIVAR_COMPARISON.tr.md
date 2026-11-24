# Termivar Web değerlendirme karşılaştırması

Bu görünüm, mevcut **`termivar report compare` tarafından önceden üretilmiş** karşılaştırma JSON'unu yerel tarayıcıda inceler. CLI'nin çevrimdışı belge işlemini tarayıcıda yeniden çalıştırmaz; iki assessment seçip eşleştirme yapmaz, scanner veya yeni karşılaştırma algoritması içermez. [English guide](TERMIVAR_COMPARISON.en.md).

## Açma ve gezinme

1. **Termivar Web Değerlendirmeleri** içindeki karşılaştırma görünümünü açın. **Karşılaştırma dosyası aç** ile tek yerel `termivar-report-comparison/v1` JSON dosyasını seçin; sınır **8 MiB**'dir. `assessment.json`, manifest, HTML veya before/after dosya çifti bu importer'ın girdisi değildir.
2. Önce before/after kaynak metadata'sını ve kapsam sınırlarını okuyun. Dört grup kartındaki sayılar, doğrulanmış gerçek dizilerin uzunluklarından gelir; belgede olmayan bir top-level `counts` alanı beklenmez.
3. Grup kartı/filtre ve arama yalnız yüklenmiş kayıtları kapsar. Bir kayıt seçerek mevcut before/after projection'ını inceleyin. Boş filtre sonucu, yalnız o grupta gösterilecek kayıt olmadığı anlamındadır; “güvenlik sorunu yok” sonucu değildir.
4. **İzin verilen karşılaştırma metadata'sını göster** tercihi import'a özeldir. Başlık/capability/category/CWE/summary/remediation ve kaynak/item fingerprint'leri başlangıçta DOM'a çizilmez. Açıldığında yalnız izinli metinler düz metindir; fingerprint önce kısadır, tam değer için ayrı genişletme gerekir. Metin HTML, link veya komut olarak yorumlanmaz. “Redacted” adı, güvenilir olmayan dosyanın sır içermediği garantisi değildir.
5. Yeni dosya seçimi önceki karşılaştırmayı ve görünürlük tercihini temizler. Geçersiz yeni import eski başarıyı korumaz. Temizleme bütün türetilmiş modeli kaldırır; reload geri yüklemez. Normal gezinme ve TR/EN importu korur; tenant/kaynak/oturum değişimi, disconnect ve mevcut erişim temizliği konservatif temizler.

Assessment incelemesi, politika önizlemesi, cihaz karşılaştırması ve rapor taslağı ayrı alanlardır. Buraya dosya açmak bunlara veri eklemez, cihaz/tenant'ın doğrulanmış güvenlik durumunu değiştirmez. Kaynak SHA veya hedef adıyla cihaz eşleştirilmez.

## Dört grubun anlamı

| Gerçek grup | Yalnız söylenebilen |
|---|---|
| `only_in_after` | Yalnız sağlanan sonraki raporda bulunan gözlem; ilk ortaya çıkış zamanı veya yeni zafiyet olduğu doğrulanmaz. |
| `only_in_before` | Yalnız sağlanan önceki raporda bulunan gözlem; **Fixed/Resolved/Remediated/Temizlendi** anlamına gelmez. |
| `changed` | Eşleşen kimliğin desteklenen karşılaştırılabilir içeriği farklı; risk artışı/azalışı veya farklı bir zafiyet olduğu sonucu değildir. |
| `unchanged` | Desteklenen item projection'ı eşit; aynı güvenlik koşulu, aynı hedef veya eşdeğer assessment kapsamı kanıtı değildir. |

Kaynağın eşleştirmesi stable fingerprint ve uyumlu capability kimliğini kullanır. UI yalnız bu hazır grupları doğrular/görüntüler; yeni eşleşme üretmez. Yerel referans numarası, başlık veya sıra aynı hedefin kanıtı değildir. Severity/confidence varsa kaynağın değeridir; UI yeniden hesaplamaz. Remediation metni öneridir, uygulanmış veya doğrulanmış düzeltme değildir. CVSS, risk/güvenlik skoru veya zafiyet doğrulaması türetilmez.

`changed_fields` de içe aktarılan kaynağın beyanıdır. Şekil/sıra/benzersizlik ve grup bağları denetlenir; tarayıcı before/after projection farkını yeniden hesaplayıp yeni grup veya karar üretmez.

## Gerçek JSON alanları → UI

| Alan | Gösterim ve güven sınırı |
|---|---|
| `schema` | Desteklenen `termivar-report-comparison/v1`; farklı sürüm açıkça reddedilir. |
| `scope_assurance=operator-declared` | CLI `--same-scope` seçiminin operatör beyanı; kapsam eşitliği veya hedef authority kanıtı değildir. |
| `coverage_equivalence=not-established` | Eşdeğer kontrol/evidence kapsamı kurulmamıştır. |
| `source_authenticity=not-established-by-parsing` | Başarılı parse üretici/source doğrulamaz. |
| `interpretation_limits` | Kaynak sözleşmesinin sınırlama alanı; olumlu güvenlik hükmüne çevrilmez. |
| `before`, `after` | Her biri SHA256, assessment/source/run/profile şemaları, profile/status, subject/item sayıları ve boş `optional_audits` metadata'sı taşır. Zaman/üretici/target alanı yoksa uydurulmaz. |
| Dört grup dizisi | Gerçek kayıt sayısı dizi uzunluğudur. İki kaynakta en fazla 4.096'şar item ve tutarlı en fazla 8.192 birleşik kayıt; sessiz kesme yoktur. |
| Kayıt `fingerprint`, `capability_id`, `before`, `after`, `changed_fields` | Kimlik, mevcut tek/iki taraflı projection ve bildirilen değişim alanları. Bir tarafta null, o grubun tek taraflı oluşudur; sıfır/temiz sonuç değildir. |
| Projection `title`, `category`, `disposition`, `claim_basis`, `severity`, `cwe`, `confidence_ppm`, `redacted_summary` | Kaynağın metadata'sı/düz metni; bağımsız onay yoktur. `severity=null` atanmamış, gerçek `0` ise sağlanan değer olarak kalır. |
| Projection `remediation{id,summary}` | Kaynak önerisi; fix uygulanması veya doğrulanması değil. |
| Projection `evidence` | `evidence_count`, direct/control/candidate referans sayıları, case/outcome varlık bayrakları ve varsa verification stage. Ham evidence içermez; haricî kanıt açma veya doğruluk kanıtı değildir. |

Before/after SHA256 değerleri **tedarik edilmiş kaynak byte'larını** tanımlar. UI ilgili kaynak dosyaları aramaz, açmaz ve bu digest'leri yeniden kaynak byte'larından doğrulamaz. Hash eşitliği üretici, hedef, kapsam, yetki veya güncellik doğrulaması değildir. `--same-scope`, source dosyalarının karşılaştırma için seçildiği operatör beyanıdır; parse ile kapsam eşitliği kurulmaz.

## Opsiyonel bölümlerin açık sınırı

Bu sürüm yalnız **temel comparison v1** alt kümesini destekler. Herhangi bir opsiyonel kök comparison bölümü veya before/after içinde boş olmayan `optional_audits`, dosyanın tamamını açık **`unsupported_section`** hatasıyla reddettirir. Çekirdek grupları gösterip geri kalanı yorumlanmış gibi sunma veya bilinmeyen bölümü sessizce atma yoktur. Bu sürümde saklanan/yorumlanmayan kısmi ek bölüm modeli de yoktur.

Birincil yerel kaynakta `control_reference_mapping_comparison` ve `wordpress_review_comparison` bulunur; WordPress nested comparison `/v1`–`/v4` sabitleri vardır. Bunlar **bu UI sürümünde desteklenmez**, birbirine dönüştürülmez. Diğer ek comparison/audit alanları da aynı sınırdadır. Kaynak CLI'nin daha geniş desteği bu görüntüleyiciye otomatik taşınmaz. Mapping/catalogue/metodoloji değişimi hedefte zafiyet, remediation veya compliance değişimi sayılmaz. Eksik/tek taraflı audit için desteklenen bir karar bu UI tarafından hesaplanmaz.

## Boyut, ayrıştırma ve gizlilik

Dosya File API ile açıkça seçilir. **8 MiB**, CLI kapasitesi değil UI byte sınırıdır. Comparison'a özgü kapalı `termivar-comparison-v1` ayrıştırma profili: **12 derinlik**, **250.000 düğüm**, **750.000 token**, dizi başına **4.096**, nesne başına **32** anahtar, metin başına **1.024 UTF-16 kod birimi**; native alanlara özgü UTF-8 sınırları ayrıca uygulanır. UTF-8, duplicate key, NaN/Infinity, yanlış sayısal tür, safe-integer, sürüm, alan ve kayıt-bağ tutarlılığı denetlenir. Daha büyük geçerli CLI belgesi açık hata ile reddedilebilir; ilk N kaydı almak yoktur. API parser'ının varsayılan sınırları değişmez. Termivar Web assessment ve politika önizlemesi içe aktarmaları kendi kapalı profillerini (`termivar-assessment-v1`, `sp-hbf-preview-v1`) kullanır; bunlar ilgili kılavuzlarda açıklanır.

Ham JSON global store'a veya envanter DTO'suna taşınmaz; izinli alanlardan kapalı immutable view model hazırlanır. Dosya adı, özel hedef ve ham veri title/URL/log/audit/telemetriye veya kalıcı tarayıcı deposuna yazılmaz. Upload/ağ, dış dosya arama, URL/path/HTML/komut çalıştırma, raw request/response veya kanıt açma, kopyalama/export/print/PDF yoktur. Gizli değerler CSS ile saklanmış DOM/attribute olarak tutulmaz; gizli serbest metin üzerinden arama oracle'ı kurulmaz.

İzinli opt-in title/summary/metadata metni HTTP içeriği veya sır barındırabilir; gösterme tercihi sanitizasyon, anonimleştirme veya şifreleme değildir. Temizleme OS/tarayıcı belleğinin adli olarak silindiği garantisini vermez.

## Kaynak ve örnek provenance

Yerel `ITherso/termivar` kaynağı `6a2639348c2366d0bf71b9a34e5484d40aa393a3` commit'inde salt okunur incelendi: [comparison.rs](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/crates/termivar-scanner/src/reporting/comparison.rs), [reporting.md](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/reporting.md), [örnek kayıt](https://github.com/ITherso/termivar/blob/6a2639348c2366d0bf71b9a34e5484d40aa393a3/docs/examples/report-compare/README.md).

Mevcut dört gruplu sentetik CLI karşılaştırma örneği **değişmeden kopyalandı**; bu tur CLI/scanner çalıştırılmadı. **Örnek karşılaştırma — gerçek hedefteki güvenlik değişimini kanıtlamaz.** Her grupta bir kayıt vardır; `changed` yalnız kasıtlı summary düzenlemesini gösterir. Kaynak commit, tarihsel üretim kimliği, tam byte/SHA256 ve örnek ayrımı [provenance belgesindedir](../src/features/termivarComparison/examples/README.md). Örnek açık seçim olmadan açılmaz; kullanıcı artefaktıyla birleşmez.

Gerçek kurulum/typecheck/build, chunk uyarısı ve sınırlı manuel ürün gözlemleri [Phase12 teslim kaydında](DELIVERY.tr.md) ayrı tutulur. Test/runner/coverage, CLI/scanner/runtime, canlı API/IdP/PG, Windows/VM/yönetici, yeni policy/enforcement yetkisi, PDF/export veya deploy/push/release bu işin kabulü değildir ve çalıştırılmaz. Tarihsel sonuçlar yeni güvenlik kabulü sayılmaz.
