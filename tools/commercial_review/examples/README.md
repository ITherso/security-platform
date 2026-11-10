# Mevcut sentetik kaynaklar

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

Yeni assessment, pozitif karar fixture'ı veya reviewer örneği bulunmaz. Hazırlama, workspace'teki mevcut `outputs/phase17-intake/handoff-input.json`, `source-mapping.json` ve `intake-manifest.json` dosyalarını açık argümanlarla kullanır. Bunlar önceki Phase17 üretimidir; Phase18 paketi eski dosyaları kopyalamaz.

Packet'ın ürettiği `decision-overlay.template.json` dosyasında `decisions=[]` kalır. Bu şablon aynı packet'ın gerçek byte digest'ine bağlıdır. Demo reconciliation'da şablon değişmeden kullanılır. Worksheet içindeki boşluklar, gerçek karar veya inceleme tarihi değildir.

Kaynak zinciri: mevcut Phase14 benign assessment → Phase17 intake → Phase18 review packet → boş overlay reconciliation → ayrı mevcut Phase16 builder. Bağımsız comparison ve elle yazılmış incomplete diagnostic bu akışa eklenmez.

[Komutlar](../README.md), [gerçek demo kayıtları](../../../docs/commercial/operations/phase18/DEMO_REVIEW_NOTES.md).
