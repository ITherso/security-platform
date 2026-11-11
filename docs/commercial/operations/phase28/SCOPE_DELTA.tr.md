# Phase28 uygulanmamış kaynak kapsamı önerileri

**DEMONSTRATION ONLY — ENTRY-POINT SOURCE COVERAGE — NO INVENTORY UPDATE OR BUILD AUTHORIZED**

Delta belgesi bir kaynak envanteri değişiklik taslağıdır. Desteklenen eylem `propose_selected_source_inclusion` olarak kalır. Bu teknik eylem adı eski Phase24 F satırlarında genel bir selected alanı bulunduğunu veya envanterin güncellendiğini söylemez.

## Bir önerinin kanıtı

Repository-level öneri yalnız manifestte explicit target path, exact allowlist izni, güvenli root/path, gerçek regular-file varlığı, ölçülen byte/SHA256, tutarlı kaynak kimliği ve doğrulanmış global F kapsam boşluğu birlikte varsa oluşturulur. Okunmamış, izin verilmeyen, değişen, kimliği uyuşmayan veya eksik dosya için başarılı inclusion önerisi üretilmez.

Her öneri target/manifest/dosya referanslarını, gözlenen byte/hash değerlerini, mevcut coverage durumunu, destekleyen kanıtı, ownership sınırlamasını ve sonraki uygulama önkoşullarını taşır. Kimlikler yereldir; imza, release veya build artefact kimliği değildir.

Gerçek kaynak kimliği aynı olan dosya için gereksiz yinelenen global öneri üretilmez. Birden çok target ilişkisi destekleyen referanslar olarak korunabilir; farklı root/pin/dosya kimliği salt path eşitliğiyle birleştirilmez. Deterministik sıralama öncelik veya onay değildir.

## Sahiplik ve uygulama sınırı

Phase27'de kesin component_owns_manifest edge sayısı 0'dır. Scanner ve CLI scope'ları ortaktır; core'un component primary bağı kurulmamıştır. Dosya bulunması bu sınırı çözmez. Yeni öneri repository-level source coverage düzeyindedir; assessment/reporting component'ine atama yapmaz. Component-specific karar için ayrıca açık sahiplik kanıtı gerekir.

Her öneride `application_authorized=false`, `application_performed=false`, `phase24_inventory_modified=false` ve `component_ownership_verified=false` kalır. Araç eski envanteri patch etmez; yeni F numarası atamaz, component listesi güncellemez, dosya taşımaz veya native kaynak gövdesini paketlemez. Phase28 teslim manifesti eski envanterin yerine geçmez.

İleride source inclusion ayrı bir kararla uygulansa bile bu, source completeness, dependency closure, binary/runtime inclusion, lisans veya ticari release yetkisi sağlamaz.

## Varyant projection

Mevcut Phase26 native-assessment iki native component'i; native-offline-support aynı ikiyi ve sekiz offline helper'ı seçer. Kaynak destekli potansiyel ilgi, `candidate_scope_relevant_ownership_unresolved` gibi açık bir ilişkiyle tutulabilir. Kesin component-owned entry-point iddiası oluşturulmaz.

Global tekil öneriler tek kez sayılır; varyantlar yalnız bu önerilere referans verir. A/B referans sayıları toplanarak global öneri sayısı şişirilmez. Sekiz helper için native target veya ek dependency uydurulmaz. Coverage oranı, risk/güvenlik puanı, kaynak completeness veya production readiness artışı hesaplanmaz. Gerçek projection ve öneri sayıları yeni çıktıdan sonra [teslim kaydına](DEMO_DELIVERY.tr.md) yazılır.
