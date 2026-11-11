# Offline License Evidence Binder & Review Queue — Phase25

**DEMONSTRATION ONLY — LICENSE EVIDENCE REVIEW — NO DISTRIBUTION AUTHORIZED**

Mevcut Phase24 dosyalarını değiştirmeyen bağımsız offline kanıt overlay'i.
Kayıt kimliği, açık evidence dosyası, kaynakla sınırlı bağ ve insan incelemesi
ayrı tutulur. Lisans tarayıcısı, dependency resolver, hukuk kararı veya release
yetkilendirme aracı değildir. Python standart kütüphanesini ve korunmuş Phase24
doğrulama/okuma yardımcılarını kullanır; wheel/startup entegrasyonu yoktur.

[Sözleşme](../../docs/commercial/operations/phase25/EVIDENCE_CONTRACT.tr.md),
[kimlik bağı](../../docs/commercial/operations/phase25/COMPONENT_BINDING.tr.md),
[iş akışı](../../docs/commercial/operations/phase25/LICENSE_REVIEW_WORKFLOW.tr.md),
[güven/veri](../../docs/commercial/operations/phase25/TRUST_AND_PRIVACY.tr.md),
[gerçek teslim](../../docs/commercial/operations/phase25/DEMO_DELIVERY.tr.md).

Workspace kökünden, açık repository kökleriyle:

```text
python -I -B security-platform/tools/commercial_license_review/assemble_evidence.py --scope security-platform/tools/commercial_license_review/examples/demo_evidence_scope.json --termivar-root ../../2026-07-31/github-plugin-github-openai-curated-remote/termivar --platform-root security-platform --output-dir outputs/phase25-license-evidence
python -I -B security-platform/tools/commercial_license_review/inspect_evidence.py --ledger outputs/phase25-license-evidence/license-evidence-ledger.json --queue outputs/phase25-license-evidence/review-queue.json --conflicts outputs/phase25-license-evidence/binding-conflicts.json --summary outputs/phase25-license-evidence/evidence-summary.md --manifest outputs/phase25-license-evidence/manifest.json --output outputs/phase25-license-evidence/inspection-summary.json
```

İkinci komut yalnız ilk komut başarılıysa çalıştırılır. Bu faz en fazla iki yeni
ürün çağrısıdır; önceki Phase24 retry istisnası kapanmıştır. Gerçek çağrı sonuçları
teslim belgesinde bulunur. Eski CLI, native scanner/runtime, package manager,
dependency indirme/çözümleme, test/coverage/typecheck/build veya ağ çalıştırılmaz.

Adapter beş açık Phase24 dosyasını okur: inventory, dependencies, constraints,
summary ve manifest. `summary`, dört gerçek payload'ın manifest byte/hash bağı
için açıkça seçilir; manifestten dosya keşfi yapılmaz. Eski strict modeller ve
saf blocker türetimi yeniden kullanılır. Native kaynaklar veya Cargo tekrar
taranmaz. Eski L/D/F kimlikleri artefact'a özgüdür; global package ID değildir.

Yeni source key, sahip artefact hash'i, gerçek kayıt konumu/digest'i ve kaynak
license ledger kaydıyla bağlanır. Aynı isimli declaration/lock veya farklı sürüm
kayıtları birleşmez. Kanıt bulunması Phase24'teki unknown beyanını veya gerekli
lisans incelemesini değiştirmez.

Demo: L0001/termivar-assessment-core için gerçek Termivar LICENSE; L0112/D0102
aho-corasick1.1.4 lock kaydı için açık missing_evidence. Yeni veya sahte lisans
metni üretilmez. Native LICENSE, başka dependency veya helper'a yayılmaz.
Diğer kayıtlar yeni evidence seçilmediğinde overlay'de evidence_missing olabilir;
bu, Phase24'te kayıtlı iki MIT beyanının silinmesi anlamına gelmez.

Metadata dosyasındaki project/workspace MIT beyanı üçüncü taraf dependency'nin
lisansını kanıtlamaz. Exact source row seçimi ile kanıtın pakete uygulanabilirliği
ayrıdır. Kaynak ilişkisi yetersizse bağ ambiguous/unverified kalır; dosya hash'i
veya adı bu belirsizliği yükseltmez. Harici evidence üreticisi doğrulanmaz.

Scope128 KiB; Phase24 dataJSON başına1 MiB, manifest64 KiB ve summary512 KiB;
evidence başına256 KiB/toplam2 MiB;64evidence/1024license record/256binding
request. Sınır aşımında ilk N kayıtla başarılı sonuç yoktur. YeniJSON4 MiB ve
MD512 KiB; korunmuş parser depth16/node120000/text2 MiB/string2048 sınırlarını
ayrıca uygular. Strict UTF-8, duplicate/float/nonfinite/unknown-field ret.

Yalnız açık dosyalar okunur; URL/path keşfi veya indirme yoktur. Phase24'ün
düzeltilmiş read_explicit_text yardımcısı symlink/reparse/hardlink, boyut ve
okuma boyunca kimlik/değişim kontrolleriyle yeniden kullanılır. ctime, lstat ve
fstat ailelerinin kendi önce/sonra kayıtlarında karşılaştırılır. Bu guards
hostile filesystem/race kabulü değildir. Kaynak metni/raw license, absolute
kök, müşteri verisi veya credential çıktıya kopyalanmaz; secret detection
ve anonimlik garantisi verilmez.

Yeni output zorunludur; overwrite yoktur. Dört payload staging üzerinden,
manifest son yayımlanır; hata kısmi yeni çıktı bırakabilir. Inspector yalnız
beş açık yeni dosyayı okur. `--summary` gerçek MD ilişkisi için ek açık
argümandır. Queue/conflicts/MD saf yeniden türetilir; base kaynak/evidence,
üretici, insan veya hukukî karar yeniden doğrulanmaz.

Teslim ZIP'i yeni araç/belge/sentetik metadata içindir. Korunmuş Phase24 ve
geçişli helper kaynakları ile açık seçilmiş kaynak dosyaları çalıştırma için
gereklidir; bunlar arşive kopyalanmaz. Bu bir müşteri runtime/release paketi
değildir. İki ürün çağrısı ve inceleme sonrası durulur; Phase26 başlatılmaz.
