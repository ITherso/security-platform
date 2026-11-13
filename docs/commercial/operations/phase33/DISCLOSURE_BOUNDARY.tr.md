# Phase33 disclosure ve veri minimizasyonu

**OFFLINE DEMONSTRATION — INTERNAL CONTENT INTEGRITY ONLY — NO CURRENT SOURCE OR PRODUCER VERIFICATION**

Assembly, dört açık Phase32 dosyasını strict parse → gerçek `consumer_contracts.validate_documents(response, selection)` → gerçek `output_renderer.render_summary` byte eşliği → gerçek üç payload için `artifact_manifest.manifest_data` eşliği sırasıyla doğrular. Request'teki iki SHA256 beklentisi gerçek response/selection byte'larına bağlanır. Phase31 guard'ı veya eski builder yeniden çalıştırılmaz; bu doğrulama özgün upstream guard doğruluğunun bağımsız kabulü değildir.

## Taşınabilen alanlar

Kapsül yalnız doğrulanmış Phase32 wire modelinden açık alan seçimiyle oluşturulur; kaynak nesne kontrolsüz serialize edilmez. İzinli her projection tam şu 11 alanı kullanır:

| Alan | Korunan anlam |
| --- | --- |
| `reference_id` | Projection'ın kapsüldeki referans bağı |
| `candidate_id` | Mevcut candidate kimliği |
| `file_id` | Mevcut file kimliği; filesystem path değildir |
| `upstream_projection_kind` | Kayıtlı Phase31 projection kodu |
| `source_file_presence` | Kayıtlı present/absent durumu; şu anki dosya sorgusu değildir |
| `observed_byte_size` | Gerçekten raporlanmış kayıtlı byte; absence için `null` |
| `observed_sha256` | Gerçekten raporlanmış kayıtlı SHA256; absence için `null` |
| `phase31_current_observation_id` | Önceki Phase31 gözlem kaydının kimliği |
| `phase31_comparison_id` | Önceki Phase31 comparison kaydının kimliği |
| `upstream_comparison_status` | Kayıtlı upstream comparison kodu |
| `interpretation_limitations` | Mevcut kapalı yorumlama sınırlama kodları |

`fresh_candidate_byte_metadata_only` ve `fresh_absence_metadata_only` yalnız eski upstream karar isimleridir. Kapsül üretimi, açılışı veya lookup yeni gözlem değildir. Null yokluk metadata'sı bilinen sıfır-byte dosya ile aynı değildir.

## Referans engeli bütün alt kayıtlara uygulanır

Phase32 `withheld_by_existing_guard` sonucu kapsülde aynen kalır ve `projections=[]` zorunludur. Olumlu alt dosyanın hash/size bilgisi başka metadata, summary, manifest, README, source bindings veya lookup alanına taşınmaz. Mevcut kapsam dışında projection yoksa otomatik sağlıklı veya başarılı varsayımı yapılmaz.

Demo request mevcut `outcome`, `authorization_review`, `report_compare` kimliklerini ister. Kaynaktaki `authorization_review` CAND0004 engeli, olumlu CAND0003 alt metadata'sını da kapatır. Gerçek örnek gözlemleri ve actual çağrı sayıları yalnız teslim kaydında tutulur; sözleşmedeki beklentiler çalışmış ürün başarısı olarak sunulmaz. Diğer 92 referans kapsüle eklenmez veya taranmış gibi gösterilmez.

Tam Phase31 baseline, raw Phase32 nesnesi, historical içerik, Rust kodu, root/kullanıcı path'i, physical file identity, configuration, credential/token/API key, raw exception, insan review notu veya müşteri kimliği taşınmaz. Source bindings yalnız dört eski artefact'ın sözleşme/byte/SHA256 kimlikleridir. Kapsül içindeki dosya isimleri sabit aktarım biçimidir; otomatik takip edilecek source path değildir.

## Yetki ve zaman sınırı

`demo_only=true`; Phase32'den gelen 17 false bayrak ile `upstream_guard_independently_verified=false` korunur. Yeni kaynak gözlemi, reference context, bağımsız observation, compiler/module closure, ownership, producer/human, build/runtime, lisans/hukukî veya release otoritesi kazanılmaz. İç hash/model eşliği üretici kimliği, kullanıcı yetkisi, özgün kaynak doğruluğu, TTL veya canlı tazelik garantisi değildir.

Kimlik ve hash hassas olabilir. Minimizasyon şifreleme veya anonimlik değildir; taşınabilir kopyanın kimlere verileceği bu demo aracı tarafından yetkilendirilmez. Otomatik sender, müşteri teslimi, risk skoru veya güvenlik sertifikası üretilmez.

Kaynak incelemesi yalnız izinli alan geçişini değerlendirir. Hostile JSON/UTF-8, sahte guard, unknown status, injected projection, path/link/ratio/limit/race/crash veya farklı shared-file düzenleri çalıştırılmadıkça NOT_RUN kalır. Koruma kodu genel güvenlik kabulü değildir.
