# Phase20 sentetik demo teslimi — 2026-11-11

**DEMONSTRATION ONLY — NO TARGET ASSESSED — NO EXECUTION AUTHORIZED**

Dal `feat/offline-assessment-scope-planner`; üretimde kullanılan kod ve ilk üç
belge commit'i `0e45afc8238e9cac9a457c825cb3510f5ecac857`. Bu teslim belgesi
gerçek üretimden sonra eklendi. Üretimde kullanılan kaynakların byte kimlikleri
`outputs/phase20-generation-source-snapshot.json` kaydında ayrıca korunur.
Son commit/tree ve arşiv kimliği dış teslim manifestindedir.

Native kaynak commit'i `6a2639348c2366d0bf71b9a34e5484d40aa393a3`; yalnız
17 sabit dosya byte/SHA ve HEAD kimliği bağlandı. Okunamayan pinlenmiş dosya
yok. İncelenmeyen yetenekler, bütün repository veya compiled binary kabulü
olarak yorumlanmaz. Kaynak incelemesi test değildir.

Örnek girdi [demo_scope.json](../../../../tools/commercial_scope/examples/demo_scope.json):
`DEMO-TERMIVAR-SCOPE-020`, `web-review`, tek kurgusal
`https://assessment.example.invalid` origin, GET/HEAD ve dört passive header
capability. Authenticated context `not_provided`, context marker listesi boş.
Authorization yok, veri işleme kararı bekleniyor; gerçek müşteri veya credential
yok. Proposal SHA256:
`773631db780b43dedd17ba5052684415f0971ae4b58b1a794d545a988f7efd5e`.

Gerçekte workspace kökünde çalıştırılan PowerShell komutu:

```powershell
$phase20SourceRoot = [System.IO.Path]::GetFullPath((Join-Path (Get-Location).Path '..\..\2026-07-31\github-plugin-github-openai-curated-remote\termivar'))
python -I -B security-platform/tools/commercial_scope/assemble_scope.py --proposal security-platform/tools/commercial_scope/examples/demo_scope.json --termivar-source $phase20SourceRoot --output-dir outputs/phase20-scope
```

**Bir** ürün çağrısı yapıldı, exit code **0**, gözlenen süre yaklaşık **0,443 s**.
Bu süre performans ölçümü/SLA değildir. İzin verilen tek çağrı tüketildi;
tekrar çalıştırma, test veya başka ürün komutu yapılmadı. Yerel Git yalnız
HEAD metadata'sını okudu. Native Termivar CLI/scanner/runtime çalıştırılmadı.
Üretim kaydı `outputs/phase20-generation-record.json` içindedir.

Gerçek çıktı dosyaları (`outputs/phase20-scope/`):

| Dosya | Bayt | SHA256 |
| --- | ---: | --- |
| `capability-catalog.json` | 46771 | `6afee69dd632c1baafecd4a5b4a2fc45ba59f2e9123266180309d0b240cf9369` |
| `scope-preflight.json` | 14331 | `a9d9b15faa715b5bf8bf05eac8718ad59fcfaaa6c99551e10492431b56a38e65` |
| `assessment-plan-proposal.json` | 22262 | `49d3389c4b83bcc02504a7eb6d84dc9ea7c69bd374a4cd3e8c827b2a8fd23986` |
| `assessment-plan-summary.md` | 10274 | `c6388d8e815d6152e988d7df41878b517cc14cdca68f3fba106410905aac5460` |
| `manifest.json` | 5143 | `adbaf8e7ad19418d177a29ccbc22a8b2d446a1d858b3739392a9843f23cf7316` |

Plan kimliği:
`termivar-scope-plan:sha256:2b03806b9f5388b866fb64602964f492c91b4aed868b2117bc7af172832eae93`.
Manifest payload'ların gerçek boyut/hash'leriyle eşleşir. Manifest kendisini
hash listesine eklemez; kendi hash'i yukarıda ve dış teslim kaydındadır.
Proposal/katalog digest bağı ve mevcut planın tarif edilen content digest'i
okunarak karşılaştırıldı. Bu işlem tekrar üretim determinism kabulü değildir.

Manuel kaynak ve çıktı incelemesinde gözlenenler:

- 11 katalog tanımı kendi namespace'iyle korunuyor. Dört seçili header
  capability kaynakla eşleşti. Informational tanımlar gerçek bulgu üretmedi.
- Yedi bütçe gerçek native kaynak envelope'u ile karşılaştırıldı:
  256 request, 300000 ms, 64 subject, depth 2, 10 active verification,
  262144 body byte ve 16777216 aggregate response byte. Bunlar ticari kabul
  veya kullanılabilir custom CLI bayrakları değildir.
- 23 ayrı check satırının 18'i `supported_by_source`, beş insan kararı
  `pending_authorization`. Genel sonuç `pending_authorization`; demo, yetki,
  veri işleme, scope owner, insan incelemesi ve runtime engelleri korunuyor.
- Seçili demo için `source_gaps=[]`. Katalog dışı capability'lerin desteği
  belirsiz kalır; GraphQL metadata-only aile ve CLI API stub desteklenmez.
  Opsiyonel bağlam, POST bileşimi ve child allowance sınırları açıkça belgeli.
- Dört JSON çıktısı ve Markdown özeti `demo_only=true`,
  `execution_authorized=false`, `authorization_verified=false`,
  `production_ready=false` sınırını koruyor. Plan native runtime config veya
  yürütme komutu içermiyor.
- Gerçek Markdown UTF-8 metni okundu. Shell stdout gösteriminde Türkçe/em dash
  karakterleri replacement gibi görünebildi; dosya metninde replacement
  karakteri bulunmuyor. Görsel tarayıcı veya UI kabulü yapılmadı.

İnceleme kayıtları `outputs/phase20-manual-output-review.json` ve
`outputs/phase20-preservation-review.json` içindedir. Önceki 122 artefact,
91 korunan kaynak dosyası, 21 mevcut frontend asset'i ve 60030 bayt üretim
wheel'i byte/SHA karşılaştırmasında değişmedi. HBF ve Termivar checkout'ları
temiz ve pinlenmiş commit'lerinde kaldı. Backend, frontend, auth/rol/DB,
runtime, lockfile, wheel, lisans veya önceki Phase14–19 kaynakları değiştirilmedi.

Yeni repository dosyaları yalnız `tools/commercial_scope/` içindeki sekiz
Python modülü, README ve sentetik örnek ile bu dizindeki dört belgedir.
Tam değişen dosya listesi ve gerçek hash'ler `phase20-scope-source-manifest.json`
teslim kaydındadır. ZIP bu yeni kaynakları, sentetik beş çıktıyı ve yeni metadata
kayıtlarını taşır; önceki kaynakları/ZIP'leri, özel çalışma dosyalarını veya
native checkout'u kopyalamaz. Korunmuş Phase16/17/18 helper'ları ve Termivar
checkout'u çalıştırma önkoşuludur. Arşivin gerçek boyut/SHA256 bilgisi
`outputs/phase20-scope-delivery-manifest.json` dış kaydındadır; döngüsel self-hash
oluşturmak için ZIP'in içine kendi kimliği yazılmaz.

**NOT_RUN:** malformed/hostile encoding, duplicate key, sayı/boyut/depth sınır
senaryoları, unknown field/version/capability, alternatif profil, bağlam
eksikliği/çelişkisi, bütçe çatışması, permission, symlink/reparse, race, crash,
tekrarlı determinism, otomatik test/runner/coverage/acceptance, typecheck/build,
native binary/runtime qualification, gerçek hedef/ağ/DNS, gerçek uzman/kurum/
müşteri/pilot ve veri işleme kabulü. Bunlara ilişkin kod yolları statik
incelendi; çalıştırılmış test veya geçmiş kabul olarak sunulmaz.

Gerçek çalışma yetkisi, kapsam sahibi, veri işleme kararı ve runtime/ürün
güvenlik kabulü açık kalır. Phase20 teknik geliştirme ve sentetik teslimi burada
biter; gerçek değerlendirme, pilot, üretim kullanımı veya Phase21 başlatılmaz.
