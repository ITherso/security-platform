# Phase16 — Offline Handoff Builder

Araç, önceden seçilmiş kaynak kimlikleri ile ayrı insan review/inclusion beyanlarını birleştirerek **iç inceleme özeti** ve iki biçimde **müşteri taslağı** hazırlar. `termivar-handoff-draft/v1`, native Termivar rapor şeması değil bu bağımsız belge aracının giriş sözleşmesidir. Native scanner/CLI, yeni assessment veya comparison, backend/frontend, production wheel ve auth/DB yolları değişmez.

## İşlem sınırı

1. Kullanıcı tek JSON girişini ve yeni çıktı dizinini açıkça seçer.
2. Bounded loader JSON byte/tür/yapı sınırlarını, [schema.py](../../../../tools/commercial_handoff/schema.py) tam alan sözleşmesini uygular. Bilinmeyen alan ve gerçek müşteri modu kabul edilmez.
3. Review kuralları kaynak, insan durumu ve ayrı inclusion kararını inceler. Eksik veya uyumsuz referans sessizce atlanmış müşteri bulgusu olmaz; internal engel olarak görünmelidir.
4. İç özet tüm geçerli observation'ları ve neden dahil edilmediklerini tutar. Müşteri modeli izinli alanlardan ayrıca oluşturulur; iç DTO'nun tamamı kopyalanmaz.
5. Markdown ve HTML aynı müşteri modelinden üretilir. Dinamik metin güvenli sunuma çevrilir; giriş HTML'i aktif içerik sayılmaz.
6. Çıktı byte'ları için boyut/SHA256 kaydedilir. Manifest son aşama kaydıdır; oluşturulan taslaklara gerçek teslim veya doğrulama yetkisi vermez.

Bu maddeler araç akışını tanımlar. Kaynak kodu incelemesiyle görülen kontrol ile yürütülerek gözlenen davranış [demo notlarında](DEMO_DELIVERY_NOTES.md) ayrı tutulur; çalıştırılmamış senaryolar kabul edilmiş sayılmaz.

## Kullanım ve yollar

[Demo girdisi](../../../../tools/commercial_handoff/examples/demo_input.json) yeni yapılandırılmış kayıttır. Phase15 Markdown'ını veya Phase14 native JSON'unu otomatik parse etmez. Komut **workspace kökünden**, yani `security-platform/` ile `outputs/` dizinlerinin bulunduğu yerden verilir:

```text
python -I -B security-platform/tools/commercial_handoff/assemble.py --input security-platform/tools/commercial_handoff/examples/demo_input.json --output-dir outputs/phase16-demo
```

Kod Python 3.10+ sözdizimi ve standart kütüphane kullanır; dependency kurulumu gerekmez. Bu teslimatta yalnız Python **3.14.7** ile çalıştırılmıştır; diğer sürümlerin kabulü yapılmamıştır. `-I` Python ortam/path etkilerini sınırlar; `-B` bytecode dosyası yazımını kapatır. Bunlar uygulamanın filesystem veya OS güvenlik kabulü değildir.

Yollar çalışma dizinine göredir; mutlak/drive/UNC yol, üst dizin (`..`), ADS ve symlink/reparse yönlendirmeleri kabul edilmez. Girdi dosyası mevcut regular dosya, çıktı üst dizini mevcut, çıktı dizininin kendisi **yeni ve henüz bulunmayan** yol olmalıdır. Mevcut boş/önceki müşteri dizini sahiplenilmez; overwrite veya silme modu yoktur. JSON içindeki referans/path/URL metinleri takip edilmez. İşlem arka planda sürmez, shell/tarayıcı/native scanner başlatmaz veya dışarı veri göndermez.

## Internal ve client ayrımı

| Konu | İç inceleme özeti | Müşteri taslağı |
| --- | --- | --- |
| Kayıtlar | Bütün geçerli kaynak gözlemleri, insan review/inclusion değerleri | Yalnız gerekli review koşulları ve ayrı dahil etme kararı olan kayıtların izinli alanları |
| Gerekçeler | Eksik kanıt, engel ve dahil edilmeme nedeni | İç karar gerekçesi veya tam ledger taşınmaz |
| Özet | Kaynak metadata'sı ile insan beyanı ayrı | Varsa açıkça hazırlanmış `safe_summary`; alan adının “safe” olması içerik güvenliği kanıtı değil |
| Hassas içerik | Yalnız girdinin sınırlı izinli alanları; gerçek müşteri verisi bu fazda kabul edilmedi | Ham HTTP, token/cookie/credential, target/domain/IP, payload, iç yol/session veya iç uzman notu otomatik aktarılmaz |
| Yetki | İnceleme ihtiyacını belgeler | Görünür **DEMONSTRATION ONLY — NOT APPROVED FOR CLIENT DELIVERY**; gerçek teslim onayı yok |

`unreviewed`, `needs_manual_review`, `inconclusive`, `excluded_with_reason` müşteri bulgusu haline yükseltilmez. Kaynak disposition insan kararı değildir; `informational_only` zafiyet etiketi, `reviewed_for_delivery` bağımsız teknik doğrulama değildir. `client_inclusion=pending_decision` müşteri sonuç listesine alınmaz. Biçimsel olarak doldurulmuş reviewer/tarih alanı gerçek incelemeyi kanıtlamaz; araç insan kimliğini doğrulamaz.

Seçim için `informational_only` veya `reviewed_for_delivery` ile `include_with_limits` birlikte, kaynak/ref/karar/özet ve `in_scope` koşullarıyla sağlanmalıdır. Tam koşullar ve müşteri modelinin alan listesi [giriş sözleşmesinde](INPUT_CONTRACT.tr.md#müşteri-seçimi--ayrı-semantik-katman) bulunur. `incomplete_review` gerçek review bağımsız doğrulanmadığı için daima true'dur; seçilmiş kayıt sayısı bunu kapatmaz. Pozitif dahil etme dalı dört `unreviewed` demo kaydıyla yürütülmüş sayılmaz.

## Neden yalnız taslak?

Araç yetki, kapsam doğruluğu, kanıtın doğruluğu, gerçek reviewer, paylaşım uygunluğu veya kurumsal onay oluşturamaz. `mode=demo`, `demo_only=true`, `release_authorized=false`, `human_review_verified=false` sınırları kaldırılamaz. Gerçek müşteri modu, ortam değişkeni override'ı veya `--force` yoktur. Çıktı dosyalarının varlığı müşteri teslimi/kabulü veya pilot GO değildir.

[INPUT_CONTRACT](INPUT_CONTRACT.tr.md) alanları, [SECURITY_BOUNDARY](SECURITY_BOUNDARY.tr.md) veri ve güven sınırını, [DEMO_DELIVERY_NOTES](DEMO_DELIVERY_NOTES.md) gerçekten yapılan işlemi belirtir. [Phase15 akışı](../ASSESSMENT_WORKFLOW.tr.md) ve [manuel teslim kapısı](../DELIVERY_GATE.tr.md) korunur; araç onları veya [Phase14 pilot koşullarını](../../PILOT_READINESS.tr.md) otomatik kapatmaz.
