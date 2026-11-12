# Phase32 teslim kaydı — gerçek üretim bekliyor

**DEMONSTRATION ONLY — GUARDED REFERENCE METADATA — NO NEW SOURCE OBSERVATION**

Bu belge kaynak hazırlığı kaydıdır. Phase32 ürün çağrısı henüz **0**; gerçek response/selection/inspection başarısı, dosya/ZIP boyutu veya SHA256 değeri burada iddia edilmez. Önceki gözlem sonuçları yeni tüketici çıktısının yerine geçirilmez.

Demo request yalnız Phase31'in doğrulanmış mevcut `outcome`, `authorization_review` ve `report_compare` external reference ID'lerini isteyecektir. ID'ler isimden üretilmez; gerçek bağlamdan alınır. Mevcut source kararı korunuyorsa iki referansta sınırlı metadata, referans engeli taşıyan `authorization_review` için sıfır projection beklenir; bunlar source-derived sonuç olmalı, başarı fixture'ı olmamalıdır.

Gerçek çalışmadan sonra üç reference'ın tam ID/kararları, sunulan/bloke sonuçlar, candidate/projection/benzersiz file sayımları, iki exact çağrı ve exit kodları, beş çıktı byte/SHA256 kimliği bu kayda eklenecektir. Kaynak üretim snapshot'ı ile son dokümantasyon değişiklikleri ayrılır. Henüz oluşmayan ZIP kimliği yazılmaz.

En fazla iki root ürün çağrısı vardır. Inspector yalnız assembly exit 0, eksiksiz dört gerçek çıktı ve manuel inceleme sonrası çalışır. Başarısız çağrı tüketilir; otomatik retry, inspector hakkını assembly tekrarına dönüştürme veya üçüncü çağrı yoktur. Phase20–31 bütçeleri ve eski Phase24/29 insan istisnaları kapalıdır.

Manuel inceleme özellikle referans engelinin olumlu alt dosya metadata'sını da kaldırdığını gözlemleyecektir. Inspector yalnız dört yeni model/summary/manifest dosyasında iç tutarlılığı inceleyecek; upstream guard'ı, eski baseline'ı veya kaynak gözlemini bağımsız doğrulamayacaktır. Genel güvenlik veya native kabulü çıkarılmayacaktır.

`reference_context_revalidated=false`, `independent_observation_verified=false`, `source_files_reobserved=false` dahil 17 güven alanı false kalır. Upstream `fresh_*` kodları yeni source gözlemi değildir. Bloke reference'ın hash/size/path metadata'sı başka alana taşınmaz; yalnız istenen reference ID'leri görünür.

NOT_RUN: hostile JSON/UTF-8, duplicate/yanlış reference, request digest uyuşmazlığı, bozuk upstream, bilinmeyen guard durumu veya projection çelişkisi, limit/path/link/race/crash, shared-file/determinism ve gerçek source değişimi; native/compiler/Rust resolution/module closure/ownership/producer/uzman/hukukî/release kabulü. Test/runner/coverage/typecheck/build ve browser çalışması yapılmaz.

Teslim tamamlanınca durulur. Yeni faz, feature, kaynak mutasyonu, eski CLI/native/ağ çalışması veya ürün çağrısı başlatılmaz. Yeni kaynak paketi korunmuş kardeş owning araçlara ve dört ayrı Phase31 girdisine bağlıdır; eski artefact grupları/native/wheel paket içine kopyalanmaz.
