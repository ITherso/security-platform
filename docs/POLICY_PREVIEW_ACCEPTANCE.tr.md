# Saf politika önizleme kabulü

Bu kayıt yalnız üçüncü turun saf politika sözleşmesini kapsar. Önceki PostgreSQL/TLS inventory kabulü, bu tur için policy push, gerçek DB CAS'i veya canlı Windows uygulama kabulü sayılmaz.

Başlangıç kaynakları: security-platform `2755336`; ayrı ve gözden geçirilmiş inventory read-coherence düzeltmesi `9c2ce8c`; HostBasedFirewall `1.4.3`, `74a88ed`. HBF kaynakları korunur. Legacy zone/hash sorununun yerel motorda bütünüyle düzeltildiği iddia edilmez; yeni adapter belirsiz girdiyi reddeder.

## Doğrulama kaydı

| Kontrol | Durum | Gerçek sonuç |
|---|---|---|
| Gate 21 yüzey koruması | passed | `tests/policy_contracts/test_surface_preservation.py`: 11 passed. Gerçek uygulamanın router/OpenAPI'si, iki dependency kilidi dahil 34 korunan platform dosyası, snapshot retleri, mevcut entrypoint'ler, Alembic head/model envanteri karşılaştırıldı. DB lifespan başlatılmadı; auth dependency bypass edilmedi. |
| Gate 22 legacy kaynak ve regresyon koruması | passed | Sekiz HBF policy/hash/trial/backup/config/evaluator kaynağı `74a88ed` SHA-256 baseline'ıyla eşleşti. HBF'nin kendi ortamında ilgili regresyonlar: 200 passed + 23 subtest; iki mevcut uyarı, 20,99 saniye. Canlı sürücü/servis kabulü değildir. |
| Saf model/önizleme/CAS/rollout kabulü | passed | 160 passed, 2,17 saniye: 38 core/bridge, 82 CAS/receipt/rollout, 17 CLI, 12 offline I/O, 11 yüzey koruması. |
| Platformun tamamı | passed | 344 passed, 1 POSIX-only skip, 1 mevcut uyarı; 22,33 saniye. Bu toplam 160 yeni politika testi ve 184 mevcut platform testini içerir. Gerçek PostgreSQL ve ayrı süreçli, doğrulamalı TLS inventory kabulü de bu çalıştırmadadır. |
| HBF odaklı regresyonları | passed | Aşağıdaki komutla 200 passed + 23 subtest. Kaynak değişikliği yoktur; önceki 2106 + 47 tam suite sonucu başlangıç kanıtı olarak kalır. |
| Gerçek offline CLI örnekleri | passed | Güncel manifest ile preview ALLOW → DENY; CAS `precondition_evidence_missing`; rollout `would_pause` ve `execution_plan=not_created`. Bütününde execution_authorized false. |
| Bağımlılık ve derleme kontrolü | passed | `pip check` ve `compileall` başarılı. |

Odaklı yüzey komutu:

```powershell
.venv\Scripts\python.exe -m pytest tests\policy_contracts\test_surface_preservation.py -q --tb=short
```

HBF çalışma dizininde çalıştırılan odaklı regresyon komutu:

```powershell
.venv\Scripts\python.exe -m pytest tests/test_policy.py tests/test_policy_workspace.py tests/test_policy_analysis.py tests/test_policy_analysis_api.py tests/test_policy_logging.py tests/test_backup_trial.py -q --tb=short
```

Çıktı çalışma alanındaki `policy-hbf-regression.log` dosyasında tutulur.

Bu tur için çalıştırılan merkezi proje komutları:

```powershell
.venv\Scripts\python.exe -m pytest tests\policy_contracts -q --tb=short
.venv\Scripts\python.exe -m pytest -q --tb=short
.venv\Scripts\python.exe -m pip check
.venv\Scripts\python.exe -m compileall -q src scripts migrations
```

Odaklı ve tam pytest kayıtları çalışma alanındaki `policy-contract-tests.log` ve `platform-final-tests.log` dosyalarındadır. Tek skip, Windows'ta uygulanmayan POSIX dosya-mode kontrolüdür; native Windows owner/DACL kontrolleri ayrıca çalıştırılmıştır.

Bu kontrol fixture'ını test sırasında yeniden üretmez. Baseline, önceki commit'ten yakalanmış yollar, hash'ler, OpenAPI ve izinli tek offline CLI ilavesini açıkça içerir. Bağımsız merkezi paket HBF kaynağı olmadan açılmışsa legacy source testi gerekçesiyle skip olur; passed olarak sunulmaz. Yerel tam çalışma alanındaki 11 testin tamamı geçmiştir.

## Zorunlu kapı matrisi

22 kapının tamamı aşağıdaki sınırlı, saf sözleşme kapsamında geçmiştir. Buradaki passed değerleri gerçek policy uygulaması, yetkilendirilmiş dağıtım veya Windows enforcement kabulü değildir.

| Gate | Kriter | Durum |
|---:|---|---|
| 1 | Eşit prefix A-first DENY/B-first ALLOW ve aynı legacy hash fixture'ı | passed |
| 2 | Belirsiz base/candidate'ın iki sırasının da adapter'da reddi | passed |
| 3 | Sabit girdi/sıra değişimi için sıra koruyan fingerprint | passed |
| 4 | Host-bit ve eşdeğer IPv6 normalizasyonu | passed |
| 5 | Aynı zone tekrarı, ayrı aile/ağ ve farklı prefix'in yanlış reddedilmemesi | passed |
| 6 | Sıra tersken `/8`–`/24` longest-prefix sonucunun korunması | passed |
| 7 | Candidate değişiminde aday/preview kimliğinin değişmesi; workspace base version ayrımı | passed |
| 8 | Politika sırası, nesne, default action ve davranış ayarlarının fingerprint'e girmesi | passed |
| 9 | Aynı base/candidate/adapter/senaryoda deterministik çıktı | passed |
| 10 | Adapter kaynağı değişiminde eski preview bağının geçersiz olması | passed |
| 11 | Açık saat/profilin gerçek evaluator'a geçmesi; ambient değişiklikten etkilenmeme | passed |
| 12 | Eksik bağlam retleri; schedule/profil senaryoları | passed |
| 13 | Base/revision/lineage/tenant/cihaz/ürün/kapsam conflict'i | passed |
| 14 | ABA ve eksik kalıcı revision fixture'larının ret/bloke sonucu | passed |
| 15 | Eski receipt'in yeni plana taşınamaması ve otomatik terfi olmaması | passed |
| 16 | verified/execute/apply/command alanlarının DTO'da reddi | passed |
| 17 | DENY_TEMP/NAT niyetinin mutasyon oluşturmaması | passed |
| 18 | Çekirdek I/O/saat/ortam/COM tripwire'ları ve ayrı CLI I/O sınırı | passed |
| 19 | Girdi değişmezliği ve bozuk/büyük girdide yarım çıktı olmaması | passed |
| 20 | Aynı HBF evaluator'ı ile bridge uyumu; yaklaşık ikinci motor olmaması | passed |
| 21 | API/auth/DB/snapshot/sender yüzeyi değişmemesi | passed |
| 22 | Legacy policy_version/trial/backup kaynak protokolünün korunması | passed |

Kapıların tekrar izlenebileceği test grupları:

| Kapılar | Kanıt |
|---|---|
| 1–12, 17, 20 | [test_preview_core.py](../tests/policy_contracts/test_preview_core.py): gerçek kaynak A/B hash çakışması, normalized/sıralı fingerprint, manifest byte değişimi, açık schedule/profil/ülke, unavailable ve DENY_TEMP/NAT tripwire'ları. |
| 13–16 | [test_preconditions.py](../tests/policy_contracts/test_preconditions.py), [test_rollout.py](../tests/policy_contracts/test_rollout.py): ayrı revision/lineage CAS, ABA, eski/çelişkili receipt, alan/kapsam bağları, immutable hedefler ve sabit yürütme blocker'ları. |
| 18–19 | Core/CAS/rollout tripwire'ları ile [test_offline_io.py](../tests/policy_contracts/test_offline_io.py), [test_offline_cli.py](../tests/policy_contracts/test_offline_cli.py): disk/ağ/saat/ortam/süreç/timer denemeleri, açık CLI dosyaları, bozuk/büyük girdi ve atomik çıktı. |
| 21–22 | [test_surface_preservation.py](../tests/policy_contracts/test_surface_preservation.py), [baseline](../tests/fixtures/policy_surface_baseline_v1.json) ve yukarıdaki gerçek HBF regresyon komutu. |

## Kapsam dışı kabul kapıları

| Kapı | Durum | Sınır |
|---|---|---|
| Gerçek DB atomik policy CAS'i | not_run | Bu turda policy DB tablosu veya kalıcı revision kaydı yoktur. |
| Cihaza gönderim/uygulama/geri alma yürütücüsü | not_run | Yürütme yolu özellikle oluşturulmaz. |
| Bağımsız received/applied/verified kanıtı | not_run | Receipt fixture'ları yalnız biçim ve bağ kontrolüdür. |
| Canlı Windows WinDivert/SCM/UAC/reboot | not_run | Önizleme sürücü veya servis başlatmaz. |
| Fiziksel Windows filosu, VPN/uyku, 24–72 saatlik kabul | not_run | Saf fixture ve inventory TLS kabulü bunu kanıtlamaz. |
| Üretim IdP/sertifika ve imzalı installer | not_run | Önceki fixture kabulü gerçek dağıtım kabulü değildir. |

Bu fazın sonucundaki `ok` veya `consistent_fixture_only`, yürütme izni değildir. Bütün çıktılarda authorization `not_evaluated`, execution_authorized `false`, verification `not_performed` olarak kalır. Sonraki adım ancak ayrı kararla kalıcı revision/lineage, açık Windows kabulü ve yetkilendirilmiş yürütücünün tasarımı olabilir.
