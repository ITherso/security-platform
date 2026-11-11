# Termivar Offline Assessment Scope Planner — Phase20

**DEMONSTRATION ONLY — NO TARGET ASSESSED — NO EXECUTION AUTHORIZED**

Bağımsız Python standart kütüphane aracı, sentetik `.invalid` kapsam önerisini
pinlenmiş Termivar kaynaklarının sınırlı kataloğuyla karşılaştırır. Native CLI,
scanner, ağ, DNS veya değerlendirme çalıştırmaz. Platform startup/wheel parçası
değildir; yeni dependency gerektirmez.

[Kullanım](../../docs/commercial/operations/phase20/SCOPE_PLANNER.tr.md),
[kaynak eşlemesi](../../docs/commercial/operations/phase20/CAPABILITY_MAPPING.tr.md),
[güven sınırı](../../docs/commercial/operations/phase20/TRUST_AND_AUTHORIZATION.tr.md),
[gerçek demo teslimi](../../docs/commercial/operations/phase20/DEMO_DELIVERY.tr.md).

Workspace kökünden kullanım biçimi:

```text
python -I -B security-platform/tools/commercial_scope/assemble_scope.py --proposal security-platform/tools/commercial_scope/examples/demo_scope.json --termivar-source <pinlenmiş-Termivar-checkout-mutlak-yolu> --output-dir outputs/phase20-scope
```

Bu satır yalnız offline planlayıcıya aittir. Native tarama komutu üretmez.
Çıktı dizini mevcut olmamalı; üst dizini mevcut olmalı. Proposal/output yolları
workspace'e göre güvenli göreli yollar, kaynak yolu açıkça seçilmiş yerel mutlak
repository yoludur. Yerel Git yalnız HEAD kimliğini okumak için çağrılır.

Beş çıktı: `capability-catalog.json`, `scope-preflight.json`,
`assessment-plan-proposal.json`, `assessment-plan-summary.md`, `manifest.json`.
Manifest son yayımlanır; hata yarım yeni dizin bırakabilir, önceki dosyalar
sahiplenilmez veya üzerine yazılmaz. SHA256 kimlik doğrulama değildir.

Kod, korunmuş Phase16/17/18 JSON/path/serialization yardımcılarını import eder.
Phase20 ZIP bu eski kaynakları yeniden içermez; mevcut security-platform
checkout'u ve pinlenmiş Termivar kaynakları gereklidir. Native kaynaklar okunur,
Python modülü olarak yüklenmez. Paket bağımsız native scanner dağıtımı değildir.

Bu fazın üretim sınırı bir sentetik çağrıdır. Teslim belgesindeki gerçekleşen
çağrı bu sınırı tüketir; yeniden çalışma ve güvenlik kabulleri bu turda yapılmaz.
