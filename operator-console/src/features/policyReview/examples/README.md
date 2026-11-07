# Synthetic CLI artefacts / Sentetik CLI artefaktları

These JSON output files were produced by the existing offline `security-policy` CLI, not by the browser or a hand-written evaluator. They are examples, not real device assessments. All addresses and the policy name are synthetic. No packet was sent and no policy was applied.

Bu JSON çıktıları mevcut çevrimdışı `security-policy` CLI ile üretildi. Tarayıcı veya elle yazılmış bir evaluator üretmedi. Gerçek cihaz değerlendirmesi değildir; adresler ve politika adı sentetiktir. Paket gönderilmedi, politika uygulanmadı.

| File | Purpose | Bytes | SHA256 |
|---|---|---:|---|
| `preview-input.json` | CLI input only; not a workbench import | 1057 | `0e2739def07ae2b5cf9ad95e1dab689c281ed34d8c45ada623ec63c009e06c74` |
| `preview-output.json` | Actual `PreviewOutcome` v1, `status=ok` | 5767 | `3d3c9605619c230a6495c8c5c8fac617498530470964a4418754a9f6f53013e8` |
| `preview-missing-context-input.json` | CLI input with one missing network profile | 1055 | `285607a199367f026bf9a1218f942f4b0acef2e3ed1483c92698390beafb3cbb` |
| `preview-missing-context-output.json` | Actual `PreviewOutcome` v1, `blocked/insufficient_context` | 2920 | `7db82e84506464b3eb44eb7521c40b7824e69dbdb1d2838d5c7df619fa5bf08c` |

## Production commands / Üretim komutları

Run from the `security-platform` source root with the existing environment and the separately preserved HBF source. These are ordinary offline CLI commands, not test commands. `-B` disables Python bytecode-file writes. The output directory already exists.

```powershell
.\.venv\Scripts\python.exe -B -m security_platform.policy_contracts.cli preview `
  --hbf-root ..\HostBasedFirewall-main `
  --input operator-console\src\features\policyReview\examples\preview-input.json `
  --output operator-console\src\features\policyReview\examples\preview-output.json

.\.venv\Scripts\python.exe -B -m security_platform.policy_contracts.cli preview `
  --hbf-root ..\HostBasedFirewall-main `
  --input operator-console\src\features\policyReview\examples\preview-missing-context-input.json `
  --output operator-console\src\features\policyReview\examples\preview-missing-context-output.json
```

Both commands completed with exit `0` and the fixed stdout `{"status":"output_written","execution_authorized":false}`. Exit `0` means the output was written, including a blocked output. Only the **output** files match the workbench's supported import type; the CLI input envelope does not.

The actual generation environment was Python **3.14.7**, Pydantic **2.13.5**, with HBF source baseline `74a88ed336cb8a0a2fab16e20389c9410590c292`. The output's `adapter_identity` records the actual source-file digests and runtime. Its adapter fingerprint is `sp-hbf-adapter-v1:sha256:704d9ff518623761a14e934fd1472a70873efa0a21dfd3b8d2aae59f99fe1afe`. Another runtime or source version may produce a different adapter/preview fingerprint; no cross-environment byte-identity promise is made.

The successful input uses one `OFFICE` zone (`192.0.2.0/24`), an empty default-ALLOW base and a candidate containing one OFFICE-source DENY rule. `office-https` is `ALLOW→DENY`; `outside-dns` is `ALLOW→ALLOW`. The blocked input differs only in the first scenario's `network_profile=null`. The actual CLI returns `insufficient_context`, no results and no successful preview fingerprint. It does not fill in PUBLIC or invent decisions.

Neither output contains controller/endpoint revision evidence, a CAS result or rollout validation. The workbench must report those as absent, not merge separate artefact types or infer readiness. Hashes here record file integrity; they do not establish producer identity, authorization, live enforcement or independent verification. This generation was not a software-test run, Windows acceptance or a live-policy check.
