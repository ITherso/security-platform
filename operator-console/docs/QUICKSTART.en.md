# Security Console quick start

The console opens in Turkish with **sample data**. It is a read-only view; no real device, platform connection or sign-in is required to explore it. Choose **English** from **Dil / Language** in the top bar. The choice lasts for the open page only; reloading starts in Turkish again.

## Open the local console

If the supplied `operator-console/dist/` build is present, run this from `operator-console/`:

```text
python serve.py --port 8787
```

Open `http://127.0.0.1:8787/`. The local HTTP preview is for sample data. For source installation and the pinned Node/pnpm build commands, see [SETUP](SETUP.tr.md). The preview server is not a production deployment.

## Explore the sample records

1. Choose one of the two fictional organizations in the sidebar. Organization and device names are data, so they may remain Turkish when the interface is English.
2. Open the device list. Search, filters and sorting cover **the loaded page**, not the whole fleet. Move between pages explicitly; the console does not silently load every device.
3. Open a device. Read device registration, last server receipt, source observation and product claims separately. HostBasedFirewall, Termivar and the planned antivirus have separate sections. A recent receipt does not mean that the device is online or protected.
4. Add the displayed detail to the status report. Only a detail you actually opened and that passed DTO validation is eligible. Adding it does not fetch new data. Reopening a device does not silently update an existing report copy; use the explicit update action.
5. Open the report draft. Remove a record or clear the draft as needed. It holds at most **20 devices / 256 KiB** in memory. Names and identifiers are hidden by default in the report preview; this is a display choice, not an anonymity guarantee.
6. Create the report's HTML preview. It covers only the selected records, which may have different read times. Returning to edit or changing fields requires a new preview. Changing language preserves the draft but invalidates a ready preview; create it again in the new language.

Changing language keeps the selected organization, sample scenario, page, search, filters and draft. It does not reconnect, refresh or fetch. Changing organization, source mode, sample scenario or connection session clears the draft under the existing context rules. Reloading does not restore it from storage.

The connection panel can select normal, empty and error sample scenarios. Those scenarios are labeled examples, not evidence of an actual access or network failure. The English interface does not translate API names, device names or user-entered search text.

## Move between device details

Use the previous/next controls inside the existing device dialog to move through **the displayed, filtered and sorted devices on the loaded page**. This is not the entire organization inventory. The first and last records are boundaries: navigation does not wrap, prefetch a neighbour or fetch another page. Each explicit move reads only the chosen device through the existing detail GET.

Closing the dialog keeps your list search, filter, sort and page. Switching language keeps the current target device. A loading/error view is not a completed product report. Moving between devices does not add to or update the status report automatically; use the explicit report action after the chosen detail has loaded successfully.

## Understand the labels

- **Reported by the device / Not independently verified** remains the trust level. Successful API access or TLS does not verify the product's claims.
- **Unknown**, **No data**, **Stale**, an error and the number **0** have different meanings. Missing values are not replaced with zero or a healthy status.
- **Device registration revoked** describes that registration; it does not say the firewall was disabled or removed.
- A Termivar summary does not prove an installed/running scanner or a scan performed by the console.
- **Planned product — unavailable** is not active antivirus protection.

Dates use **en-GB with UTC**; changing language changes presentation, not the underlying time. Report creation time is browser metadata, not a new device observation. Loaded/selected records are not a complete organization inventory, security score, policy application receipt or compliance certificate.

The existing browser print/PDF action is user-controlled; the console cannot infer that a PDF was saved. Native print preview was not available in the earlier product review, and no PDF was saved. This language delivery does not retry printing or produce a PDF. The normal browser's final destination/save/cancel choice remains the user's.

The real API adapter is implemented but was not connected or accepted with a real token/IdP in this work. No onboarding/enrollment or real API setup is needed for this guide. Test runs, Windows acceptance and remote execution remain outside this product work.
