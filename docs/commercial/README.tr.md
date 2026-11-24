# Termivar Web ticari pilot hazırlık paketi — Phase14

**Termivar Web & API Security Assessment**, ilk ticari ürün adayı olarak tanımlanır. Bu dizin hizmet modeli ve teslimat belgeleridir; satış, müşteri iletişimi, canlı değerlendirme veya üretime çıkış yetkisi vermez.

| Belge | Kullanım |
|---|---|
| [PRODUCT_OFFERING](PRODUCT_OFFERING.tr.md) | İlk hedef müşteri hipotezi, ürün kapsamı, üç teklif seviyesi ve fiyatlandırma için ölçülecek değişkenler. |
| [PILOT_SCOPE](PILOT_SCOPE.tr.md) | Yetki, hedef sınırları, teknik bütçe, durdurma ve veri işleme kararları. |
| [DELIVERABLE_SPEC](DELIVERABLE_SPEC.tr.md) | Yönetici/teknik rapor standardı ve kaynak/inceleme/eksiklik ayrımı. |
| [CAPABILITY_CLAIMS](CAPABILITY_CLAIMS.tr.md) | Kaynakta mevcut, kısıtlı ve bulunmayan yetenekler; pinli kaynaklar ve gerekli kabul kapıları. |
| [PILOT_READINESS](PILOT_READINESS.tr.md) | Ücretli pilot öncesi teknik, işletimsel ve hukuki/kurumsal kararlar ile ölçülebilir kapanış ölçütleri. |
| [Sentetik teslimat](examples/README.tr.md) | Yalnız önceden mevcut artefact'ların kopyaları ve bunların insan tarafından yazılmış örnek açıklaması. |

[Phase15 uzman inceleme ve teslim kiti](operations/README.tr.md), bu belgelerin elle doldurulabilir kayıtlar ve ayrı müşteri handoff taslağıyla nasıl uygulanacağını gösterir; gerçek değerlendirme veya teslim izni oluşturmaz.

**Demonstration only — No real system assessed.** Örnek kaynak JSON'lara yeni bulgu veya alan eklenmez. Bunlar müşteri verisi veya bu fazda çalıştırılmış scanner çıktısı değildir. Tam kaynak/byte ilişkileri örnek provenance kaydında bulunur.

İncelenen kaynaklar: Termivar `6a2639348c2366d0bf71b9a34e5484d40aa393a3`, Security Platform/operator-console `aa643d40797998d5f615cb5ba5b71b972596abc9`, HostBasedFirewall `74a88ed336cb8a0a2fab16e20389c9410590c292`. Termivar kaynak hattı `0.10.0-alpha.3`, örneklerin tarihsel üretim sürümü ve seçilecek pilot binary'si ayrı kimliklerdir. Kodda mevcut olmak production güvenilirliğini kanıtlamaz.

Bu faz yalnız Markdown belgeleri, mevcut sentetik JSON ve Termivar lisans bildirimi kopyaları ile kök README bağlantısını değiştirir. Yeni scanner/backend/frontend, CLI çalıştırma, test/runner/coverage, build, canlı API/PG/IdP/Windows/VM, yönetici işlemi, PDF, müşteri iletişimi, GitHub push/release/deploy yoktur. Phase7–13 teknik kaynak ve teslimatları korunur.

Teslimde kaynak git dışında `phase14-commercial-source-manifest.json` yeni belgelerin ve kopyaların byte/SHA256 listesini, okunan kaynak referanslarını ve koruma kaydını taşır. Ayrı ticari belge ZIP'inin boyut/tam SHA256 kimliği dış teslim kaydındadır. ZIP yalnız bu ticari belgeleri ve sentetik kopyaları taşır; uygulama, executable veya teknik kaynak dağıtımı değildir. Platforma verilen dizin bağlantılarının teknik kaynakları korunmuş Phase13 kaynak arşivinde/checkout'undadır; Termivar referansları pinli kaynak commit'ine gider. Hash; imza, müşteri onayı, rapor doğruluğu veya pilot yetkisi değildir. Kaynak belgeleri kendi arşiv hash'ini içermez.
