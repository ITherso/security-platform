# Offline Analyst Review Desk kullanımı

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Desk, [Phase18 inceleme paketini](../phase18/ANALYST_WORKFLOW.tr.md) anlaşılır bir yerel çalışma alanına taşır. Kaynakları doğrulayan Python hazırlayıcı ile tarayıcıdaki karar taslağı editörü ayrıdır. [Komutlar](../../../../tools/commercial_review_desk/README.md).

1. Packet, packet manifesti ve boş overlay template'i açık dosya argümanlarıyla hazırlayıcıya verilir. Phase18 doğrulayıcıları yeniden kullanılır; native assessment veya başka dosya açılmaz.
2. Üretilen `review-desk.html` doğrudan tarayıcıda açılır. Her gözlemde native disposition ile insan review/inclusion alanları ayrı okunur. Arama ve filtre yalnız yüklenmiş packet kayıtlarında çalışır.
3. Ayrıntıda assessment digest, pointer ve fingerprint görülür. Kısaltılmış fingerprint tekil güvenlik kimliği veya producer kanıtı değildir; tam değer ayrıca açılır. Kaynakta bulunmayan category/kanıt ayrıntısı uydurulmaz.
4. Editörde yalnız açık kullanıcı işlemiyle insan review, scope, inclusion ve izinli metinler hazırlanabilir. Durumlar birbirini otomatik yükseltmez. Kaydedilmemiş düzenleme ile kaynak seçimi/export karışmaz; geri alma eylemi görünürdür.
5. Bu fazdaki demo bütün gözlemleri `unreviewed / unknown / pending_decision` bırakır. Gerçek reviewer, tarih veya karar girilmez. Yalnız boş karar taslağı indirilebilir.
6. Tarayıcının indirme isteği mesajı dosyanın kaydedildiği anlamına gelmez. Dosya gerçekten elde edilirse Python sonlandırıcıya packet, manifest, orijinal Phase17 handoff ve bu taslak açıkça verilir. UI doğrulaması nihai güven sınırı değildir.
7. Sonlandırıcı kapalı taslağı tekrar doğrular ve mevcut Phase18 digest/bağlama fonksiyonlarıyla overlay üretir. Yeni overlay ancak ayrıca seçilen mevcut Phase18 reconciliation komutuna verilebilir. Gerçek müşteri teslim izni oluşmaz.

`scope_status` mevcut Phase18 insan alanıdır; kaynak assessment kapsamını veya yetkilendirmeyi kanıtlamaz. `include_with_limits` için uygun açık durum ve müşteri özeti gerekir. Reviewer/zaman bu ilk tarayıcı taslağında desteklenmez; finalizer bunları null bırakır. Phase18 insan incelemesini doğrulamaz; Phase16 müşteri seçiminin eksik reviewer/zaman engelleri de devam eder.

Sayfa yeniden açıldığında önceki kararlar kendiliğinden yüklenmez. Sekme belleği ve tarayıcının indirdiği dosyalar farklıdır; bellek temizleme indirilen dosyayı silmez. Kaynak dosyasının HTML'ye dönüştürülmesi anonimleştirme veya sır taraması değildir.

[Taslak alanları](DECISION_DRAFT_CONTRACT.tr.md), [güven sınırı](SOURCE_AND_TRUST_BOUNDARY.tr.md), [gerçek demo kanıtı ve açık gözlemler](DEMO_WORKFLOW.tr.md).
