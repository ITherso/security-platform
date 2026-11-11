# Component attribution ve kaynak sahipliği sınırı

**DEMONSTRATION ONLY — DIRECT DEPENDENCY SOURCE EVIDENCE — NO BUILD OR DISTRIBUTION AUTHORIZED**

[Sözleşme](DIRECT_DEPENDENCY_CONTRACT.tr.md), [Rust semantiği](RUST_MANIFEST_SEMANTICS.tr.md),
[güven sınırı](TRUST_BOUNDARY.tr.md), [gerçek teslim](DEMO_DELIVERY.tr.md).

Manifestte bir kaynak paketinin bulunması, o paketin Phase24'teki mantıksal
ürün component id'sine kesin sahipliğini vermez. Scope seçimi, dizin veya isim
benzerliği de yetki değildir. İlgili F kapsamı adayları ve primary-manifest
adayları ayrı gösterilir; birden fazla adaydan sessiz seçim yapılmaz.

Genel definite ownership koşulu: kaynak package mevcut, yalnız bir gerçek
F-scope component adayı ve aynı component'in primary manifest F/path/root/pin
ilişkisi uyumlu. Diğer durumlarda ambiguous_ownership veya
ownership_not_established korunur. Gerekçe, adaylar, source fingerprint ve
limitations sınırlı metadata olarak kalır.

Mevcut scanner ve CLI F referansları iki native component'in kaynak listesinde
de vardır; primary manifest metadata'sı bunlardan birini kesin owner yapmaz.
Core F yalnız assessment source listesinde görünür, fakat onun primary manifesti
değildir. Virtual workspace root ortak dependency template havuzudur. Bu kaynak
kapsamı için sıfır component_owns_manifest edge'i dürüst ve izinli sonuçtur;
olumlu edge üretmek için kaynak belirsizliği kapatılmaz.

Manifest_declares_dependency ve açık crate_inherits_workspace_dependency
kenarları ownership kurulmasa da gerçek kaynak bildirimlerini gösterir.
Declaration_matches_phase24_record yalnız tekil eski metadata projection bağı;
may_match kenarı bütün belirsiz D adaylarına possible olarak gider. Hiçbiri
build dependency graph veya binary kanıtı değildir.

Python helper'lar ortak F0004/pyproject kaydını paylaşır. Project adı/sürümü
security-platform/0.1.0'dır; üç registered script security_platform modüllerine
aittir ve packages.find src kapsamını gösterir. Bu, sekiz helper'ın distribution
metadata'sı veya PyPI paket/sürüm bağı değildir. Sınırlı 12 entry-file okumasında
stdlib ve commercial_* kardeş importları görülmesi tam dependency closure veya
her helper'ın sıfır haricî runtime dependency'si olduğunu kanıtlamaz.44 excluded
backend-context satırı helper ownership'e yükseltilmez.

Yeni varyant overlay'i eski iki component seçimini kullanır. Ambiguous binding
seçimle definite olmaz; ownership belirsizse source_scope_only sınırı korunur.
Workspace pool crate'in dependency listesi değildir. Koşullar ayrı declaration
id'leriyle görünür kalsa da aktivasyon bilinmezdir. B'ye sekiz helper eklenmesi
fazladan runtime dependency sayısı veya hukukî yükümlülük farkı üretmez.

Eski Phase26 enum ve dosyaları değiştirilmez. Lisans subject461, unknown459,
önceki scoped MIT2, yeni kanıt1/eksik460 ve açık review/release engelleri yeni
source edge nedeniyle kapanmaz. Gerçek reviewer, üretici veya hukukî onay yoktur.
