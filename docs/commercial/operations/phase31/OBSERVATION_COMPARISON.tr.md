# Phase31 gözlem karşılaştırması

**DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED**

Historical observation Phase30'un değişmemiş kaydıdır. Current observation yeni ID, gerçek presence/byte/hash ve bounded okuma stabilitesidir. Comparison yalnız bu iki kapalı kayıttan türetilir; dosya okumaz, eski başarıyı güncel gözlem diye yeniden adlandırmaz.

| Historical | Güvenli current | Karşılaştırma |
| --- | --- | --- |
| Present/hash | Aynı byte boyutu ve SHA256 | bytes_reobserved_equal |
| Present/hash | Farklı byte/hash | bytes_changed |
| Present | Güvenli yokluk | previously_present_now_missing |
| Missing | Present/hash | previously_missing_now_present |
| Missing | Güvenli yokluk | absence_reobserved |
| Yeniden okuma seçilmedi | Current yok | not_revalidated |
| Gerekli tarihsel veri yetersiz | Karşılaştırılamaz | revalidation_inconclusive |

Inconclusive güvenlik hatasını yutan fallback değildir. Current expectation uyuşmazlığı, root/type/reparse/permission/race veya limit hatasında başarılı ledger yayımlanmaz. Ayrı current_expected_sha256 verilmiş bir dosya yoksa bu beklenti doğrulanamaz; normal missing comparison yerine kapalı hata gerekir. Okuma sırasında değişim ile iki ayrı güvenli gözlem arasında değişim farklıdır. Missing yalnız izinli kök/parent zinciri doğrulanmış açık yolun yokluğudur; erişim reddi değildir.

Phase30 historical inode/handle/dev/time saklamadı. historical_physical_identity=not_recorded; identity_comparison=not_comparable kalır. Yeni physical identity dışarı verilmez; eski kayda yazılmaz. Aynı hash/byte boyutu aynı fiziksel dosya, üretici veya korunmuş inode demek değildir.

Aynı mantıksal file birden çok izinli candidate/reference'a bağlıysa bir kez okunur; bütün bağlar korunur. Çelişen scope veya expectation keyfî birleştirilmez. Seçilmemiş current gözlem yaratılmaz. CAND0004 için tarihsel file observation da yoktur; read_not_performed fiziksel missing olarak yorumlanmaz.

Karşılaştırma bu çağrının anlık gözlemidir. TTL, gelecekte değişmezlik, polling veya watcher yoktur. Beklenen üç equal-byte/bir equal-absence sonucu fixture olarak kodlanmaz; ancak gerçek yeni okumalar desteklerse raporlanır. Değişim/kaybolma/ortaya çıkma göstermek için native dosya mutasyonu yapılmaz.
