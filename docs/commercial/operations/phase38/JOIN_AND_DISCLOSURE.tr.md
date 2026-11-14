# Phase38 görünür küme kesişimi ve bütün referans disclosure

**OFFLINE DEMONSTRATION — DISCLOSED CO-REFERENCE ONLY — NO PHYSICAL FILE OR SOURCE RELATIONSHIP VERIFIED**

Co-reference yalnız açık File ID'lerin mevcut visible reference kümeleri arasında pairwise kesişimdir. Yeni edge, candidate, projection ID veya fiziksel/source ilişkisi keşfedilmez. İsim, dosya adı, candidate veya native hash benzerliği join gerekçesi değildir.

## Gerçek pair desteği

Her unordered File ID çifti kanonik sırada bir kez değerlendirilir. Her iki file matched ve kesişim boş değilse shared reference ID'ler yalnız gerçek provided kayıtlardan gelir. Her shared referans için left ve right File ID'nin source `projection_bindings` üçlüleri gerçekten bulunmalıdır. Bir file aynı referansta farklı candidate'larla yer alıyorsa bütün gerçek üçlüler korunur.

Bir çiftte duplicate/çelişkili binding reddedilir; fakat aynı gerçek üçlü farklı çiftleri destekleyebilir. Bu nedenle occurrence sayısı ile unique `(reference_id,candidate_id,file_id)` sayısı ayrı tutulur. Birden fazla shared pair aynı referansı lookup'ta çoğaltmaz. Deterministik pair sıralaması tekrar-determinism runtime kabulü değildir.

Her iki file visible fakat kesişim boşsa `no_shared_disclosed_reference` yalnız bu disclosure kapsamını anlatır. Dosyalar ilişkisizdir, farklı fiziksel dosyadır veya başka source'ta ortak referansları yoktur sonucu çıkarılmaz. Herhangi bir file nonvisible/unknown ise ortak `not_in_disclosed_index` ve boş shared/support listeleri kullanılır; fiziksel yokluk veya bloke kayıtta varlık nedeni açıklanmaz.

## All-or-nothing lookup

Shared referansın bütün kaynak izinli projection paketi döner; yalnız requested file projection'larına göre filtre yapılmaz. Mevcut Phase37 pure lookup ve doğrulanmış packet'lar yeniden kullanılır. Lookup result dört alanla sınırlıdır; tam eski paket join `reference_packets` içinde korunur, böylece yeni inspector whole-packet iç eşliğini inceleyebilir. Bu ek özgün kaynak bağlılığını bağımsız kanıtlamaz.

Shared-reference union dışındaki full catalog veya bloke metadata kopyalanmaz. Bloke reference ID/adı, olumlu file/candidate/hash/byte veya eski global bloke aggregate yeni join/lookup/receipt/summary'ye taşınmaz. Source counts yalnız eski visible indeksin altı sayımıdır. Daha küçük/birleştirilmiş metadata daha yüksek disclosure yetkisi değildir.

Lookup'un 11-alan projection kayıtları source tür/değer/sıra/limitation anlamlarını korur. Null absence byte/hash integer count sıfırı veya empty string değildir; sıfır-byte source dosyası iddiasına çevrilmez. Absence metadata'sı gerçek visible referansta yer alabilir, fakat şimdi fiziksel dosyanın varlığı veya iki dosyanın fiziksel bağı hakkında kanıt oluşturmaz.

## Gerçek demo ve NOT_RUN ayrımı

Bu tur mevcut iki visible File ID'yi birlikte ister: beklenti bir gerçek pair, tek shared provided referans, iki supporting binding ve bütün iki projection'dır. Sayımlar source kayıtlarından türetilir; sabit başarılı fixture değildir. İkinci ortak referans, no-shared pair, unknown ID veya negatif fixture uydurulmaz.

No-shared/unknown/nonvisible, shared-file multiple-reference, duplicate/çelişkili binding veya sahte shared-reference, modified index ve hostile JSON/limit/race/crash kabulü gerçekten çalıştırılmadıkça NOT_RUN kalır. Kodda kural bulunması runtime kabulü değildir. Actual gözlem ve source/output byte kimlikleri teslim kaydındadır.

`files_share_disclosed_reference ≠ same_physical_file`. Ortak referans content equality, source ownership, compiler/module resolution, güvenlik veya nedensellik ilişkisi değildir. 18 false nested trust flag korunur; producer/guard/source freshness/human/legal/release yetkisi kazanılmaz. ID/hash hassas olabilir; minimizasyon şifreleme/anonimlik değildir.
