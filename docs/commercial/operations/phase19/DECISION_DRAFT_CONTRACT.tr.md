# Geçici karar taslağı sözleşmesi

**DEMONSTRATION ONLY — NO HUMAN REVIEW PERFORMED**

`termivar-analyst-decision-draft/v1`, tarayıcının indirdiği küçük ve güvenilmeyen bir giriş dosyasıdır. Phase18'in `termivar-analyst-decision-overlay/v1` sözleşmesiyle aynı değildir. [Python sözleşmesi](../../../../tools/commercial_review_desk/desk_contracts.py), [Phase18 eşlemesi](../../../../tools/commercial_review_desk/desk_projection.py).

Kök alanlar tam olarak `schema_version`, `review_packet_digest`, `source_assessment_digest`, `decisions` olur. Şablon başlangıcında `decisions=[]`; HTML yüklenmesi karar satırı oluşturmaz. Digest'ler seçilen packet byte'ları ve packet'taki assessment metadata'sına bağlıdır.

Her açık karar satırında şu anahtarlar zorunludur:

| Alan | Sınır / anlam |
| --- | --- |
| `observation_key` | Packet'taki gerçek assessment SHA256 + `/items/i` bağı; bilinmeyen veya duplicate anahtar ret |
| `review_status` | Mevcut altılı Phase15/18 insan sözlüğü |
| `scope_status` | `in_scope`, `out_of_scope`, `unknown`; ayrı insan beyanı |
| `client_inclusion` | `pending_decision`, `include_with_limits`, `exclude_with_reason`; review seçimiyle otomatik değişmez |
| `safe_summary`, `reason` | Null veya 2048 karakter / 16 satır sınırlı açık metin |
| `missing_evidence`, `follow_up` | Null veya 1024 karakter / 16 satır sınırlı iç not |

Bilinmeyen alan, source fingerprint/disposition/pointer kopyası, reviewer/tarih/imza veya yeni onay bayrağı kabul edilmez. Kaynak alanları düzenlenebilir karar değildir. Tek kalıcı referans bilinen `observation_key` olur; finalizer diğer kaynak alanlarını doğrulanmış packet DTO'sundan alır.

İnsan review durumları: `unreviewed`, `needs_manual_review`, `informational_only`, `inconclusive`, `excluded_with_reason`, `reviewed_for_delivery`. Kaynak Termivar disposition bunların yerine geçmez. Son değer bağımsız teknik doğrulama veya genel teslim onayı değildir.

En fazla 256 karar / 256 KiB JSON; strict UTF-8, BOM/duplicate key/float/NaN/Infinity reddi, 12 derinlik, anahtarlar dahil 10.000 düğüm, toplam 128 KiB UTF-8 metin ve 8192 karakter tek JSON string sınırları eski Phase18 helper'larıyla korunur. Metinler kırpılmaz veya Unicode normalize edilmez; boş metin için null kullanılır. Satırlar CRLF/CR/LF üzerinden sınırlıdır; C0 kontroller (LF/CR/TAB hariç) ve C1/DEL reddedilir.

## Phase18 overlay'e geçiş

Tarayıcı context digest hesaplamaz. Sonlandırıcı packet/manifesti ve açık orijinal handoff dosyasını tekrar bağlar; kaynak satırlarını düzenlemeden Phase18'in tam 17 alanlı karar context'ini oluşturur. `decision_context_digest` doğrudan mevcut Phase18 yardımcı fonksiyonuyla hesaplanır; bütün metinler ve null'lar kapsamdadır.

`decision_id`, açıkça girilmiş bir karar satırı için `DESK-` + observation ID biçiminde yerel teknik referanstır; uzman kimliği veya native karar kanıtı değildir. Demo boş olduğu sürece böyle bir karar kaydı oluşmaz. `reviewer_ref` ve `reviewed_at` null kalır. Eksik gerekçe ve iç notların Phase16'ya aktarımı mevcut Phase18 kurallarını izler; yeni renderer veya müşteri allowlist'i yoktur.

Overlay mevcut `validate_overlay` ve `bind_decisions` ile yeniden kontrol edilir. Bu helper gerçek orijinal handoff girdisini istediği için finalizer'daki açık `--handoff-input` zorunludur; orijinal dosya byte'ları taklit edilmez. Boş taslak boş overlay'e dönüşebilir. Dolu/pozitif karar yolu bu fazdaki demoda yürütülmez.

Geçerli biçim veya tutarlı digest, kararın uzman tarafından verildiğini/doğru olduğunu kanıtlamaz. `mode=demo`; insan/producer/release doğrulama bayrakları false kalır. [Kaynak ve güven sınırı](SOURCE_AND_TRUST_BOUNDARY.tr.md).
