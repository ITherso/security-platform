# Phase30 aday kanıtı sözleşmesi

**DEMONSTRATION ONLY — RUST MODULE CANDIDATE EVIDENCE — NO COMPILER RESOLUTION VERIFIED**

Bağımsız araç, düzeltilmiş Phase29 external module referanslarına bağlanan açık operatör adaylarını ve izinli dosya gözlemlerini inceler. Mode yalnız demo'dur. Phase29 referans ID, parent source ID, kaynak konumu, lexical scope ve condition ID'leri korunur; inline module veya sıradan macro için external dosya adayı üretilmez.

| Belge | Sürümlü sözleşme |
| --- | --- |
| Scope | `termivar-offline-rust-module-candidate-scope/v1` |
| Candidate Evidence | `termivar-offline-rust-module-candidate-evidence/v1` |
| Reference Triage | `termivar-offline-module-candidate-triage/v1` |
| Source Coverage | `termivar-offline-module-candidate-coverage/v1` |

Girdi, Phase29 corrected beş dosyası ve Phase24 beş artefact'ının explicit byte/SHA256 descriptor'larını taşır. Üç Phase29 JSON'u strict parse/validate_documents, aynı Markdown projection ve gerçek dört payload manifest bağıyla tüketilir. Builder tek başına validator sayılmaz. İlk partial Phase29 dizini otorite değildir; eski Rust lexer veya CLI yeniden çalıştırılmaz.

Scope'taki candidate declaration ile dosya okuma allowlist'i ayrıdır. Her candidate gerçek external reference'a bağlanır; allowlist aynı candidate/reference/root/pin/path kimliğine exact izin verir. Allowlist dışında stat/exists/open yoktur. Candidate origin, operator selection veya path-context iddiasıdır; uzman/kurumsal onay değildir.

## Sınırlar

| Veri | Üst sınır |
| --- | ---: |
| Scope JSON | 128 KiB |
| Phase29 JSON / Markdown / manifest | 1 MiB / 256 KiB / 128 KiB |
| Phase24 JSON / manifest | 2 MiB / 128 KiB |
| Candidate dosyası / toplam candidate okuması | 512 KiB / 4 MiB |
| Toplam metadata / hash parçası | 8 MiB / 64 KiB |
| Yeni JSON / Markdown / manifest | 2 MiB / 256 KiB / 128 KiB |

En fazla 95 kaynak external reference, 32 seçili referans, referans başına 2 candidate, toplam 64 candidate/64 farklı dosya, 128 candidate-reference ilişkisi ve 512 F satırı kabul edilir. Yeniden kullanılan strict JSON tree sınırları: derinlik 16, toplam node 120.000, dize 2048 karakter, toplam UTF-8 metin 2 MiB, safe integer en fazla 2^53−1. Bütün float değerleri reddedilir; listeler ayrıca alan bazında sınırlıdır. Aşımda sessiz truncation yoktur.

Metadata JSON için strict UTF-8, duplicate key, NaN/Infinity, boolean-as-integer, yanlış tür, bilinmeyen sürüm, kapalı alanlar, duplicate kimlik ve yanlış parent/reference bağı denetlenir. Source context, 96 eski referans dahil inline parent ilişkilerini ve yalnız bu referansların kullandığı condition satırlarını tutar; 461 eski condition attribute'un tamamını yeni evidence'a kopyalamaz. Lexer yeniden çalıştırılmaz. Path/root/hash/identity veya güvenlik hatası başarılı presence/missing sonucuna dönüştürülmez. Output yeni dizindir; overwrite/silme yoktur.

Tüm önceki false güven bayrakları ve compiler_resolution_verified=false korunur. Inspector yalnız beş yeni dosyanın model/ref/count/Markdown ve byte/hash bağını inceler. content_consistent kaynak doğruluğu, compiler resolution veya release kabulü değildir. Gerçek sonuçlar [teslim kaydında](DEMO_DELIVERY.tr.md) tutulur.
