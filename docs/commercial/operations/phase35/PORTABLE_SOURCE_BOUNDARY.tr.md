# Phase35 portatif kapsül ve tabular kaynak sınırı

**OFFLINE DEMONSTRATION — TABULAR DISCLOSURE ONLY — NO CURRENT SOURCE VERIFICATION**

Assembly ve tabular inspector yalnız açık Phase34 kapsülünü mevcut Phase33/34 sahibiyle doğrular. Eski Phase31/32 artefact, guard veya native kaynak açılmaz; kaynak kapsül değiştirilmez. İkinci ZIP parser veya paralel güvenlik reader'ı oluşturulmaz.

## Gerçek API ayrımları

Korunmuş Phase34 `load_validated_source(path, selected_ids, InputBudget)` immutable `ValidatedSourceCapsule` byte snapshot'ı üretir. `read_validated_source(snapshot)` exact-type immutable byte'ları mevcut sahibiyle yeniden doğrular ve ayrı `(capsule, identity)` modelleri döndürür. Identity yalnız gerçek ZIP byte/SHA256 ve kapsül kimliğidir; modelin kendisi değildir. Caller'ın mutable allow/validated etiketi otorite değildir.

Phase33 `inspect_bundle(path, requested_ids)` `(inspection, lookup)` döndürür. Lookup selected sonuçları tam capsule veya bağımsız producer kanıtı sayılmaz. Yeni adapter public owner byte bağını ve tam model ayrımını korur; eski reader'ın sıkı path/member/model/README/summary/manifest limitlerini gevşetmez. Derivation veya eski capsule CLI yeniden çalıştırılmaz.

`build_tabular_dataset` mevcut doğrulanmış kapsülden açık seçilmiş ID'lerin kapalı reference/projection kayıtlarını oluşturur. İş mantığı saf ve immutable metadata sınırındadır. CSV ile Markdown aynı dataset'ten türetilir. Disk erişimi adapter, CLI ve publisher sınırında kalır; JSON içindeki URL/path başka input açtırmaz.

## Inspector'ın gerçekten değerlendirebileceği ilişki

Inspector açık kaynak ZIP kimliğini ve kapsül sahibini doğrular; dataset'in strict scope/model/ID/count/flag ilişkisini; kaynaktaki durum ve izinli projection içerik eşliğini; bloke projection yokluğunu; iki CSV'nin header/sütun/satır/typed encoding ve yeniden üretilebilir byte ilişkisini; dataset'ten Markdown eşliğini ve dört gerçek payload manifest bağını inceler. Manifest kendisini kapsamaz.

`internal_content_status=content_consistent` yalnız kaynak kapsül ile dataset/iki CSV/summary/manifest arasındaki iç ilişkiyi anlatabilir. Kaynak kapsül üreticisi, Phase31 guard, gerçek dosya güncelliği, imza, Rust/compiler/ownership veya native davranış yeniden doğrulanmaz. SHA256 byte bağıdır; attestation değildir.

Yeni araç standalone binary veya production wheel değildir. Korunmuş Phase34 adapter/budget ve Phase33 owner contract/reader/renderer/manifest modülleri gereklidir. Yeni kaynak paketi önceki kaynak ağacını veya eski kapsülleri otomatik kopyalamaz. İkinci offline host'a modül/veri aktarımı ve gerçek spreadsheet uygulamasında CSV import kabulü çalıştırılmadıkça NOT_RUN kalır. Kaynak import grafiğinin incelenmesi runtime kabulünün yerine geçmez.

## Güven, mahremiyet ve açık kapılar

`demo_only=true`; `source_files_reobserved=false`, `reference_context_revalidated=false`, `independent_observation_verified=false`, `upstream_guard_independently_verified=false`, producer/ownership/release/production ve diğer kaynak false alanları korunur. Mevcut 18 güven alanı olumluya yükselmez. Kayıtlı `fresh_*` kodları yeni gözlem/TTL garantisi değildir. CSV üretimi hukukî onay veya insan/kurum yetkisi değildir.

Scope 32 KiB, ZIP 256 KiB/üye 128 KiB/expanded 256 KiB/tam dört üye/ratio 20; reference 8/projection 64; dataset/her CSV/MD 128 KiB; depth 12/node 20.000/text 512, hücre 4096 B/satır 65536 B limitleri korunur. Strict UTF-8/JSON, duplicate/unknown key/version/record, invalid sayı/bool-as-int, wrong digest/ID reddi; path/link/encryption/unsupported compression reddi. Limitte kesme veya mevcut output üzerine yazma yoktur.

Hostile/duplicate JSON/UTF-8, wrong digest/ID, blocked projection enjeksiyonu, adversarial formula/control/multiline/null-empty-zero, değiştirilmiş kapsül, ZIP bomb/link/ratio/limit, permission/crash/partial write/repeat determinism, ikinci offline host ve gerçek spreadsheet import; guard/source freshness/compiler/module closure/ownership/native/human/legal/customer/release kabulleri çalıştırılmadıkça NOT_RUN kalır. Test/runner/coverage/typecheck/build/install yapılmaz; Phase19 UI tarayıcı kısıtı aşılmaz. Actual komutlar ve byte kimlikleri yalnız teslim kaydındadır.
