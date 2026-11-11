# Phase30 kaynak adayı incelemesi

**DEMONSTRATION ONLY — RUST MODULE CANDIDATE EVIDENCE — NO COMPILER RESOLUTION VERIFIED**

Triage tüm gerçek Phase29 external reference ID'lerini korur. Yalnız seçili referanslar explicit aday incelemesine girer; diğerleri not_examined kalır. Inline module ve ordinary macro bu external paydasına eklenmez. Conditional ve external aynı reference'ın iki özelliği olabilir; iki ayrı kayıt sayılmaz.

| Durum | Dar anlamı |
| --- | --- |
| candidate_present_unresolved | İzinli dosya mevcut/hash'lenmiştir; Rust bağı bilinmez. |
| candidate_missing | İzinli yol güvenli biçimde yok olarak gözlenmiştir. |
| candidate_not_allowlisted | Bu candidate/reference için dosya gözlem izni yoktur; varlık bilinmez. |
| candidate_set_ambiguous | Birden fazla aday ilişkisi açıklığa kavuşmamıştır; otomatik seçim yoktur. |
| path_context_unresolved | Path bağlamı yeterli kaynak kanıtıyla kurulmamıştır. |
| not_examined | Bu external referansın candidate incelemesi yapılmamıştır. |

Permission, unsupported type, hash uyuşmazlığı veya race missing diye gösterilmez. Not-allowlisted yolun filesystem varlığı sorgulanmaz; boyut/hash/presence bilinmez kalır. İncelenmeyen reference candidate_missing değildir.

Reference sayısı, candidate binding sayısı ve tekil gözlenen fiziksel dosya sayısı ayrı paydalardır. Aynı dosya iki reference için bir kez okunabilir ama iki binding kaybolmaz. Present ve missing binding sayıları unique file sayısı gibi toplanmaz. Birincil triage sınıfı ikincil not-allowlisted/ambiguous/condition durumlarını gizlemez; bu alt sınıflar örtüşebilir.

Alternatives_exhaustive=false ve resolved_file=false korunur. Tek present candidate tamamlandı, doğru aday veya güvenli sonuç değildir. İnceleme sırası priority, SLA, risk puanı, hukukî karar veya uygulama yetkisi üretmez.

Phase24 global F üyeliği ile component F referansı ayrı gösterilir. Present dosyanın root/pin/path ve eski byte/hash ilişkisi ayrıca karşılaştırılır. Okunmamış veya missing candidate gözlenen inventory membership kazanmaz. F'de bulunmamak excluded/unused değildir; genel selected/excluded alanı eklenmez. Üç Phase28 delta uygulanmaz, yeni F yazılmaz ve eski sıfır owner sonucu yükseltilmez.

Gerçek seçili/unselected/payda sayıları yeni assembly sonrasında [teslim kaydına](DEMO_DELIVERY.tr.md) yazılır; 95/4/91 gibi ön beklentiler ürün fixture sonucu olarak sabitlenmez.
