# Çevrimdışı analyst review iş akışı

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Phase18, [Phase17 aktarımı](../phase17/ASSESSMENT_INTAKE.tr.md) ile [Phase16 teslim taslağı](../phase16/HANDOFF_BUILDER.tr.md) arasındaki kaynakla bağlı karar kaydını hazırlar. Bu fazda gerçek uzman incelemesi yapılmaz. [Komutlar ve dosya adları](../../../../tools/commercial_review/README.md).

1. Üç mevcut Phase17 JSON dosyasını açık argümanlarla seçin. Hazırlama, gerçek byte hash'lerini intake manifestiyle ve gözlem metadata'sını mapping/handoff ile karşılaştırır. Assessment veya manifestte adı geçen başka dosya açılmaz.
2. Üretilen packet'ta her kaydın assessment digest, pointer, fingerprint ve mevcut durumlarını görün. Worksheet kaynak ve insan kararı alanlarını ayrı gösterir; karar, yetki veya uzman kimliği doldurmaz.
3. Bu turda `decision-overlay.template.json` dosyasını boş bırakın. Dört kayıt hâlâ `unreviewed / unknown / pending_decision` durumundadır.
4. Ayrı reconciliation komutuna packet, manifest, orijinal handoff girdisi ve boş overlay'i verin. Bilinmeyen/çelişkili bağ kabul edilmez; uygun girdi yeni bir dizine yazılır. Var olan dosya değiştirilmez.
5. İç uzlaştırma raporunu ve yeni manifesti okuyun. Yeni Phase16-compatible girdiyi istenirse builder'a ayrı komutla verin. Builder'ın iç özeti bütün kayıtları, müşteri taslağı yalnız ayrı seçim koşullarını karşılayan kayıtları gösterir. Demoda seçilen kayıt yoktur; bu, güvenlik açığı bulunmadığı anlamına gelmez.

## Gelecekte açıkça doldurulacak karar

Gerçek kullanım bu fazda yetkilendirilmemiştir. Ayrı yetkili bir insan incelemesinde yeni overlay dosyası oluşturulabilir; kaynak bağı değiştirilmeden yalnız izinli karar alanları doldurulur. Her kararın tam içeriği `decision_context_digest` ile bağlanır; metin değişirse digest de değişmelidir. [Alan sözleşmesi](REVIEW_CONTRACT.tr.md) ve [bağlama tarifi](SOURCE_BINDING.tr.md) birlikte okunmalıdır.

Reviewer ve UTC zamanı yalnız beyan niteliğindedir; araç kişiyi, uzmanlığı veya kanıta erişimi doğrulamaz. Kaynak disposition insan review durumuna otomatik çevrilmez. Dahil etme kararı ve güvenli müşteri anlatımı ayrıca verilmelidir. Eksik karar pending kalır; hariç bırakma iç kaynak kaydını silmez.

Hazır karar içeren bir handoff üzerine başka overlay uygulanmaz; ilk profil kapalı conflict üretir. Phase15'in revision/supersedes/geçmiş kayıtları bu yeni v1'e sessizce aktarılmaz. Bunun için ayrı kurumsal süreç gerekir; eski Phase15 kayıtlarını değiştirmeyin.

`human_review_verified=false`, `producer_verified=false`, `release_authorized=false` kalır. Phase16-compatible JSON'a bu eski sözleşmede bulunmayan alanlar eklenmez; `mode=demo` ve ayrı Phase18 manifest/raporundaki güven sınırı korunur. [Açık kabul kapıları](TRUST_BOUNDARY.tr.md).
