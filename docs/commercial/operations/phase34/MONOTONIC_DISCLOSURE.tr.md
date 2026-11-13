# Phase34 monotonic disclosure sınırı

**OFFLINE DEMONSTRATION — CAPSULE SUBSET ONLY — NO ORIGINAL SOURCE OR PRODUCER VERIFICATION**

Temel ilişki `derived_disclosure ⊆ source_disclosure`. Türetme yalnız mevcut seçilmiş referansları taşır; yeni reference, candidate, file, hash, byte, upstream observation veya olumlu metadata üretmez. Daha küçük veri kapsamı daha yüksek güven değildir.

## Birebir korunan seçilmiş sonuç

Derived ID listesi kaynak kapsül ID'lerinin strict alt kümesidir. Request boş, duplicate, unknown veya tüm kaynak kapsamını değiştirmeden seçen bir sonuç üretemez. Kaynak referans status değeri yeniden değerlendirilmez. `withheld_by_existing_guard` sonucu provided olamaz; mevcut kapalı diğer durumlar da aynen korunur.

Her seçilmiş referansın projection listesi kaynakla içerik bakımından birebir aynıdır. Reference/candidate/file kimliği, observed SHA256/byte, upstream projection türü, presence, observation/comparison kimliği ve limitation alanları değiştirilmez. Null absence byte/hash bilinen sıfıra çevrilmez. Kanonik sıralama içerik değişikliğini haklı çıkarmaz. Kaynak model değiştirilmez ve eksik alan varsayılanla tamamlanmaz.

Bloke referansta `projections=[]` zorunlu. Olumlu alt dosya bilgisi derived JSON, summary, manifest, README, dış ledger veya lookup sonucuna taşınmaz. Yeni bir guard, risk kararı, otomatik düzeltme veya insan/kurum yetkilendirmesi üretilmez.

## Seçilmemiş kayıtların kaldırılması

Seçilmeyen referans ve projection metadata'sı derived kapsülde bulunmaz. Çıkarılan ID, context adı, candidate/file kimliği, olumlu native hash/byte veya başka payload'ı listeleyen disclosure log'u oluşturulmaz. Dış ledger yalnız iki ZIP'in aggregate byte/SHA256 kimliği, strict request'teki seçilmiş ID'ler ve toplam sayımları taşır. Bu ZIP hash'leri projection hash'i değildir.

Demo mevcut kaynak kapsülden `outcome` ve `authorization_review` referanslarını seçer; diğer mevcut bağlam dışarıda kalır. Kayıtlı olumlu alt veri engeli aşmaz. Beklenen kaynak→derived reference 3→2, provided 2→1, withheld 1→1 ve projection 3→2 sayımları üreticide başarı sabiti değildir; gerçek doğrulanmış kapsülden türetilir. Gerçek örnek gözlemleri teslim kaydında tutulur; saldırgan omitted-metadata sızıntı kabulü yerine geçmez.

## Şema ve güven sınırı

Derived ZIP Phase33 şemasında kalır. Mevcut kapsül renderer, iç manifest ve README güven açıklamaları yeniden kullanılır. Türetme ilişkisi dış ledger'dadır; iç kapsüle yeni producer, provenance veya onay alanı eklenmez. Kaynak/derived capsule birlikte incelenmeden derived dosya tek başına kaynağından geldiğini bağımsız kanıtlamaz.

`source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`, `producer_verified=false`, `release_authorized=false`, `production_ready=false` ve diğer mevcut false alanlar korunur. Mevcut artifact/source bağları imza veya attestation değildir. Upstream `fresh_*` adları önceki kodlardır; türetme yeni gözlem, bugünkü source durumu veya TTL garantisi değildir.

Native kaynak, Phase31/32 baseline, root/path, physical identity, credential, raw exception, müşteri kimliği veya insan review notu açıklanmaz. ID ve hash hassas olabilir; minimizasyon anonimlik/şifreleme değildir. Otomatik paylaşım veya müşteri onayı yoktur.

Hostile/duplicate JSON, unknown ID/status, yanlış digest, blocked projection enjeksiyonu, omitted metadata sızıntısı saldırıları, ZIP/link/ratio/limit/race/crash ve farklı runtime düzenleri çalıştırılmadıkça NOT_RUN kalır. İçerik eşitliği kontrolü kaynak üreticisini veya gerçek Phase31 guard'ını doğrulamaz.
