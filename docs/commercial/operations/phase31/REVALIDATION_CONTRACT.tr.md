# Phase31 yeniden gözlem sözleşmesi

**DEMONSTRATION ONLY — CANDIDATE EVIDENCE REVALIDATION — NO COMPILER RESOLUTION VERIFIED**

Bağımsız araç, doğrulanmış Phase30 dosya gözlemlerini değiştirmeden yeni izinli gözlemlerle karşılaştırır. Mode yalnız demo'dur. Yeni aday veya allowlist genişlemesi yoktur; seçili file/root/pin/path ve bütün izinli candidate bağları eski kaydın alt kümesinden gelir. CAND0004 erişim yetkisi kazanmaz.

| Belge | Sözleşme | İçerik |
| --- | --- | --- |
| Scope | `termivar-offline-candidate-revalidation-scope/v1` | Beş baseline artefact, kaynak ZIP byte kimliği, izin alt kümesi, yeni expectation ve reuse politikası. |
| Ledger | `termivar-offline-candidate-revalidation/v1` | Historical/current gözlemleri ve karşılaştırmaları ayrı tutar. |
| Reuse | `termivar-offline-candidate-evidence-reuse/v1` | Sınırlı güncel projection, blocked kararlar ve eski reference etkisi. |

Yeni modeller eski Phase30 validator'ına benzetilmez. Eski strict üç JSON → validate_documents → aynı Markdown → gerçek dört payload manifest bağı yalnız nested baseline için kullanılır. Yeni modeller ayrı kapalı sözleşmeyle ve saf yeniden türetmeyle doğrulanır. Baseline metadata'sı tutulur; eski JSON metni, dependency/license gövdesi veya Rust body kopyalanmaz.

baseline_sha256 tarihsel içeriktir. current_expected_sha256 yeni scope'un ayrı nullable beklentisidir; current_observed_sha256 yeni başarılı bounded okumada ölçülür. Null yeni expectation, eski mandatory-hash reader'ını None ile aşmak değildir; yeni dar reader kendi current beklenti mantığını uygular. Eski hash/expectation yeniden yazılmaz.

## Bütçeler

Scope 128 KiB; baseline JSON 2 MiB, Markdown 256 KiB, manifest 128 KiB; kaynak ZIP 2 MiB; toplam metadata 8 MiB. Candidate dosyası 512 KiB, toplam current okuma 4 MiB ve hash parçası en fazla 64 KiB. Yeni JSON 2 MiB, Markdown 256 KiB, manifest 128 KiB'dir. Strict JSON derinlik 16, node 120.000, dize 2048 karakter ve safe integer 2^53−1 sınırları korunur; float, duplicate key, NaN/Infinity, boolean-as-integer, bilinmeyen sürüm ve yanlış tür kapalı reddedilir.

Kaynak ZIP yalnız binary byte/hash olarak okunur; archive decode/extract/member doğrulaması değildir. Root/path/type/hash/identity/permission/race/limit hatası normal changed veya missing sonucuna çevrilmez. Yeni output dizini gerekir; overwrite yoktur. Eksik güncel hash baseline'dan doldurulmaz.

Manifest yalnız ledger/reuse/Markdown üç payload'ının gerçek boyut/SHA256 değerini bağlar; own hash ve henüz olmayan inspector sonucu içermez. Inspector dört yeni dosyanın iç metadata/byte tutarlılığını inceler; eski artefact, ZIP veya candidate/Rust kaynağı açmaz. content_consistent independent file truth veya compiler kabulü değildir. Gerçek sonuçlar [teslim kaydına](DEMO_DELIVERY.tr.md) yazılır.
