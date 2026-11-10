# Phase17 — assessment'tan demo teslim girdisine aktarım

Yeni [commercial_intake aracı](../../../../tools/commercial_intake/README.md), seçilmiş native assessment dosyasını okuyup mevcut Phase16'nın kabul ettiği JSON'u üretir. Observation alanları elle yazılmaz. Kaynak fingerprint ve gerçek array konumu korunur; her kayıt için insan durumu `unreviewed`, kapsam `unknown`, müşteri tercihi `pending_decision` olur. `safe_summary` ve karar referansı `null`, karar listesi boş kalır.

## Desteklenen dar kullanım

Kaynak biçimi Phase14 benign örneğinin base-only `venom-rendered-assessment/v1` / `web-review` / `complete` profilidir. En fazla **1 MiB / 256 item**, dört mevcut pasif capability ve iki kapalı category desteklenir. Native kaynağın daha geniş kapasitesi bu aracın sınırı değildir. Optional audit veya desteklenmeyen alan/sürüm açık hata olur; ilk N kayıt alınarak kısmi başarı üretilmez. [Kesin eşleme ve sınırlar](SOURCE_MAPPING.tr.md).

Yalnız Python standart kütüphanesi ve korunmuş Phase16 yardımcıları kullanılır. Native Termivar CLI/scanner, üretim wheel'i, backend/frontend veya servis başlangıcı değildir. Eski Phase16 kodu değiştirilmez. Çalışma için `tools/commercial_handoff/` kardeş dizini mevcut olmalıdır. Yeni ZIP önceki çalışma kopyalarını içermez; korunmuş Phase16 kaynağına eklenir.

## İki açık komut

`security-platform/` ve `outputs/` dizinlerini içeren workspace kökünden:

```text
python -I -B security-platform/tools/commercial_intake/assemble_intake.py --assessment security-platform/docs/commercial/examples/assessment.json --manifest security-platform/docs/commercial/examples/manifest.json --output-dir outputs/phase17-intake
python -I -B security-platform/tools/commercial_handoff/assemble.py --input outputs/phase17-intake/handoff-input.json --output-dir outputs/phase17-handoff
```

İlk komut üç dosya üretir: `handoff-input.json`, `source-mapping.json`, `intake-manifest.json`. İkinci komut mevcut builder ile iç özet, Markdown müşteri taslağı, statik HTML müşteri taslağı ve builder manifestini üretir. Bridge ikinci komutu kendiliğinden başlatmaz. Gerçekte yapılan çağrılar ve sonuçlar [entegrasyon kaydında](DEMO_INTEGRATION.tr.md) ayrıca gösterilir.

`--assessment` zorunlu, `--manifest` ayrı ve isteğe bağlı seçimdir. Dosyalardaki path/URL/entry adları takip edilmez. CLI yolları cwd-relative olmalı; mutlak/drive/UNC/`..`/ADS ile symlink/reparse yönlendirmesi reddedilir. Çıktı üst dizini mevcut, seçilen çıktı dizini hiç bulunmayan yeni yol olmalıdır. Mevcut boş dizin bile kullanılmaz; overwrite veya kullanıcı dosyalarını silme modu yoktur. Daha sonra yeniden üretmek için her iki çıktıya da farklı yeni dizin adı seçilir.

## İnceleme ve teslim sınırı

Aktarım gözlem türünü değiştirmez; kaynak `informational` etiketi insan `informational_only` kararı değildir. Yeni adapter inceleme veya inclusion kararı üretmez. Phase16'nın müşteri modeli yalnız kendi koşullarıyla seçilmiş alanları alır; mevcut dört incelenmemiş örnek müşteri bulgusu olarak aktarılmaz. Boş seçim, güvenlik açığı bulunmadığı anlamına gelmez.

Her müşteri taslağında **DEMONSTRATION ONLY — NOT APPROVED FOR CLIENT DELIVERY** etiketi kalır. `demo_only=true`, `human_review_verified=false`, `producer_verified=false`, `release_authorized=false`; gerçek müşteri modu, gizli override veya yeni yetki yoktur. [Güven sınırı](TRUST_BOUNDARY.tr.md) ve korunmuş [Phase16 sözleşmesi](../phase16/INPUT_CONTRACT.tr.md) gerçek müşteri kabulünün yerini tutmaz.
