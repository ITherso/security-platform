# Mevcut bağımsız sentetik girdiler

**DEMONSTRATION ONLY — PLAN AND ASSESSMENT EXECUTION LINK NOT ESTABLISHED**

Yeni assessment, comparison veya örnek run üretilmez. Aşağıdaki dosyalar
korunmuş mevcut girdilerdir; aynı çalışma tarafından üretildikleri varsayılmaz.

| CLI rolü | Workspace'e göre açık dosya |
| --- | --- |
| plan | `outputs/phase20-scope/assessment-plan-proposal.json` |
| preflight | `outputs/phase20-scope/scope-preflight.json` |
| catalog | `outputs/phase20-scope/capability-catalog.json` |
| plan-manifest | `outputs/phase20-scope/manifest.json` |
| assessment | `security-platform/docs/commercial/examples/assessment.json` |
| assessment-manifest | `security-platform/docs/commercial/examples/manifest.json` |
| source-mapping | `outputs/phase17-intake/source-mapping.json` |
| handoff-input | `outputs/phase17-intake/handoff-input.json` |
| intake-manifest | `outputs/phase17-intake/intake-manifest.json` |

Workspace kökünden kullanım biçimi:

```text
python -I -B security-platform/tools/commercial_traceability/assemble_traceability.py --plan outputs/phase20-scope/assessment-plan-proposal.json --preflight outputs/phase20-scope/scope-preflight.json --catalog outputs/phase20-scope/capability-catalog.json --plan-manifest outputs/phase20-scope/manifest.json --assessment security-platform/docs/commercial/examples/assessment.json --assessment-manifest security-platform/docs/commercial/examples/manifest.json --source-mapping outputs/phase17-intake/source-mapping.json --handoff-input outputs/phase17-intake/handoff-input.json --intake-manifest outputs/phase17-intake/intake-manifest.json --output-dir outputs/phase21-traceability
```

Bu yalnız offline rapor oluşturma satırıdır. Native tarama veya çalışma yetkisi
üretmez. Orijinal Phase20 proposal ve özet dosyası, Phase14 HTML, native checkout
ve JSON içindeki kaynak yolları bu komutla otomatik açılmaz.

Gerçek gerçekleştirilmiş çağrı, sonuçlar ve dosya kimlikleri
[teslim belgesinde](../../../docs/commercial/operations/phase21/DEMO_DELIVERY.tr.md)
kayıtlıdır. Eski örnekler bu ZIP'e yeniden eklenmez.
