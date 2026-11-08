# Product Hub

**Product Hub / Ürün Merkezi** links the existing Security Ecosystem products and workspaces. It is a small typed frontend catalogue, not a calculation of installation, device health, protection, licence entitlement or independent verification. [Türkçe kullanım](PRODUCT_HUB.tr.md), [capability matrix](CAPABILITY_MATRIX.tr.md).

## Five entries and existing destinations

| Kind / stable ID | Product or component | Console destination | Source and boundary |
|---|---|---|---|
| product `hostbasedfirewall` | HostBasedFirewall | Devices (`devices`) | HBF state reported by a sample or explicitly connected API device. The local Windows product is separate; no central policy push/enforcement or completed live Windows acceptance is implied. |
| product `termivar` | Termivar | Assessment review (`termivarReview`) and sibling comparison | Supported precomputed local JSON. The console starts no scanner and authenticates neither target nor producer by opening an artefact. |
| component `policy-impact-workbench` | Policy Impact Workbench | Policy previews (`policyReview`) | Existing CLI preview output; no real policy revision/lineage authority, application or verification. |
| component `security-platform` | Security Platform | Overview (`overview`) | Existing tenant/device/product inventory and audit contracts. Example mode works and the API adapter exists; corporate IdP/production live acceptance has not been performed. |
| product `antivirus` | Antivirus | Products (`products`) | Planned-product information only: `planned/unavailable`. No engine, scanning, malware detection or real-time AV protection. |

The first four entries use `availability=available_workspace`; antivirus uses `planned_unavailable`. These describe **console workspace availability**. Separate `verification=not_verified` remains unchanged; it does not mean installed/protected/verified. Component IDs are frontend catalogue IDs, not additions to the backend's three-product DTO.

Cards navigate to existing pages. A destination in API mode may make its existing normal GET; the catalogue adds no endpoint, permission or client. It has no install/enable/buy/scan/protection action, payment or customer-registration screen. Brands and technical IDs remain unchanged across locales.

## Explore the platform: demo-only guide

The guide explains existing screens rather than running another application, autoplaying a demo or collecting data. Starting requires example mode, a selected DEMO tenant and no active loading/busy operation. It never silently switches an API/disconnected context to demo or changes a token, client or session. Example mode can be selected separately through the existing connection controls.

Three fixed flows, each with five steps:

| Flow ID | Existing features to inspect |
|---|---|
| `endpoint` | Sample device list, a detail explicitly opened by the user, reported HBF state and existing device comparison/product report. |
| `termivar` | Assessment workspace, explicitly loaded synthetic example, coverage/incomplete controls, existing comparison and the limit that only-in-before is not remediation. |
| `policy` | Policy Impact Workbench, explicitly opened synthetic preview, distinct base/candidate/adapter identities and missing CAS/revision evidence. |

Start/next/previous change guide flow/index metadata only. **Go to this step's screen** is a separate explicit navigation action. The guide opens no file/example/device detail, runs no scan/comparison and copies no data. Users operate the destination's existing controls normally. No DOM manipulation forces hidden elements open or reads hidden data.

Closing leaves the normal screen usable. Guide state exists only in memory; language changes preserve the step, tenant/mode/session changes and existing access cleanup close an inappropriate guide, and reload resets it. It adds no persistence, analytics or external request. Lazy local JS/CSS loads are application-code loads, not real device API requests. See [loading boundaries](FRONTEND_LOADING.tr.md).

## Trust labels remain intact

`self_reported`, `not_verified`, `unknown`, `stale`, `revoked` and `planned/unavailable` are never upgraded by catalogue or guide presentation. A fresh report is not protection proof, revoked registration does not prove the firewall stopped, and an assessment does not prove an installed/running scanner. Preview applies no firewall rule; an item disappearing from comparison does not prove a fix.

This is not a customer contract, SLA, certification, price/offer or production-readiness approval. Unmet technical and operational gates for a first paid enterprise product are separated in the [matrix](CAPABILITY_MATRIX.tr.md). Tests and live acceptance remain held; actual install/typecheck/build and limited manual observations belong to [Phase13 delivery](DELIVERY.tr.md).
