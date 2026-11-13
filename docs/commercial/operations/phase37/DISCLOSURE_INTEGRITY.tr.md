# Phase37 bütün referans disclosure ve ters ilişki

**OFFLINE DEMONSTRATION — DISCLOSED METADATA ONLY — NO CURRENT SOURCE VERIFICATION**

Yeni indeks yalnız `provided_limited_metadata` referansların gerçek typed projection'larını kullanır. Kaynak `reference_projection_links` ve `(reference_id,candidate_id,file_id)` ilişkisi olmadan yeni bağlantı oluşturulmaz. File metadata'sını indekslemek disclosure yetkisi değildir; invariant `lookup_disclosure ⊆ validated_inbox_disclosure`.

## All-or-nothing referans sonucu

Bir istenen File ID bir referansın tek projection'ıyla eşleşse bile lookup o referansın bütün mevcut izinli projection paketini döndürür. Eşleşen File ID'ler ayrı `matched_file_ids` listesidir; projection kümesine filter olarak uygulanmaz. Aynı referans farklı File ID sorgularında bir kez döner, projection paketi çoğaltılmaz. Status, tür, byte/hash, upstream observation/comparison ve limitation kodları kaynakla aynı kalır.

Sıralama deterministiktir: file/reference ve binding'ler kanonik sıralıdır; reference içindeki projection sırası korunur. Bu kural tekrar-determinism runtime kabulü iddiası değildir. Shared File ID'nin farklı gerçek provided referans bağlantıları korunur; duplicate bağ veya çelişkili file metadata'sı sessizce birleştirilmez. Yeni projection ID, candidate veya source observation oluşturulmaz.

## Bloke ve görünür indeks dışı kapsam

Withheld veya unavailable referans görünür file kayıtlarına veya olumlu lookup paketlerine alınmaz. Olumlu child candidate/file/hash/byte bilgisi başka audit/receipt bölümüne kopyalanmaz. Kaynak withheld sayımı yalnız aggregate toplam olarak kalabilir; kaynakta bloke bir ID'nin varlığı çıkarılmaz.

Biçimsel geçerli unknown veya görünür indeks dışı File ID aynı `not_in_disclosed_index` ve boş reference listesi döndürür. Sonuç fiziksel absence, source missing, bloke kayıtta bulunma veya başka kaynaktaki varlığı ayırt etmez. Unknown yanıtında pozitif fallback veya daha açıklayıcı saklı neden yoktur.

File ID fiziksel inode/Windows File ID veya source path değildir. Kayıtlı absence projection'ının File ID'si görünür indekste eşleşebilir; bu fiziksel dosyanın şimdi var olduğunu söylemez. Null byte/hash, integer count sıfırı, empty string ve sıfır-byte source dosyası birbirinin yerine geçirilmez. Mevcut DATA boolean desteklemez; false sıfıra coercion yapılmaz.

## Veri minimizasyonu ve gerçek demo sınırı

Index/lookup yalnız izinli mevcut 11 projection alanı, dört reference alanı, kaynak artefact identity/schema ve gerekli yeni ilişki/sayım alanlarını taşır. Tam Phase31 baseline, Phase35 CSV, kapsül ZIP'i, Rust, path/root/physical identity, credential, exception veya bloke olumlu metadata taşınmaz. ID/hash hassas olabilir; minimizasyon şifreleme veya anonimlik değildir.

Bu turdaki demo kaynakta mevcut iki File ID'yi birlikte sorar; aynı provided referansın tekilleştirilmiş bütün iki projection paketi beklenir. Beklenti başarı fixture'ı değildir, gerçek kaynaktan türetilir. Tek File ID ile genişleme, shared-file multiple-reference, unknown/nonvisible ID veya adversarial bağ senaryosu için yeni fixture üretilmez; gerçekten çalıştırılmadıkça NOT_RUN kalır. Kaynak kodunda kural bulunması bu runtime kapılarını geçmez.

`demo_only=true` ve nested `trust_flags` içindeki aynı 18 false alan korunur. Source freshness/producer/guard/compiler/module closure/ownership/native/human/legal/customer/production/release yetkisi kazanılmaz. Kayıtlı fresh kodları yeni gözlem/TTL garantisi değildir. Actual gözlemler ve komutlar teslim kaydındadır.
