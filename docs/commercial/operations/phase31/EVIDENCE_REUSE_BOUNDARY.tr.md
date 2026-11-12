# Phase31 sınırlı evidence reuse sınırı

**DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED**

Guard yalnız bu yeni aracın metadata tüketici yolundadır. Önceki araçlar ve ecosystem tüketicileri değiştirilmediğinden genel zorunlu enforcement veya bütün kanıt zincirinin tazelendiği iddia edilmez.

bytes_reobserved_equal yalnız küçük CURRENT candidate byte metadata projection'ına izin verir. absence_reobserved yalnız CURRENT izinli yol yokluğu projection'ına izin verir. İki projection da yeni observation ID/presence/byte/hash alanlarından gelir; historical başarı alanı değildir.

Diğer beş comparison durumunda projection null ve reuse blocked kalır. Changed/disappeared/appeared, not_revalidated veya inconclusive kayıtta eski başarılı gözlem fallback olarak döndürülmez. Yeni farklı gözlem raporlanabilir; eski kanıtın hâlâ güncel olduğunu söylemez. Guard caller'ın equal iddiasını tek başına kabul etmez; doğrulanmış historical/current metadata'dan karşılaştırmayı yeniden türetir.

Dosya kararı eski izinli file → candidate → Phase29 reference bağlarına yayılır. Bir changed veya yeniden incelenmemiş candidate, başka unchanged candidate tarafından maskelenmez. Unique dosya, candidate ve reference sayıları ayrıdır; aynı dosya birkaç referansa etki edebilir. Yeni module/ownership edge veya candidate oluşturulmaz.

Allowlist dışındaki CAND0004 sorgulanmaz ve current projection kazanmaz. Eski 92 external reference candidate kapsamı dışındadır; outside_scope sağlıklı/unchanged/unaffected demek değildir. Gözlenmemiş durum bilinmez kalır.

Rust giriş dosyaları, lexical koşul/path context ve Phase24 kaynakları yeniden okunmadığından reference_context_revalidated=false kalır. Eski F membership veya ownership metadata'sı current candidate hash'inden otomatik yenilenmez. Byte eşitliği compiler/module resolution, source completeness, producer veya build/release kabulü değildir. Guard anlık metadata koşulunu denetler; TTL veya gelecek geçerlilik garantisi üretmez.
