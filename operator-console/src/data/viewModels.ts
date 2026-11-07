/** Display-only mappings. No status, authorization, freshness or trust upgrade. */
import type { Device, DevicePage } from "./contracts";

export type DisplayTone = "good" | "warn" | "neutral";
export interface DeviceRowViewModel {
  readonly device: Device;
  readonly identityLabel: string;
  readonly connectionLabel: string;
  readonly connectionTone: DisplayTone;
}
export interface DeviceListViewModel {
  readonly rows: readonly DeviceRowViewModel[];
  readonly loadedCount: number;
  readonly scopeLabel: "Bu sayfada yüklenen kayıtlar";
  readonly nextOffset: number | null;
  readonly canNext: boolean;
}
/** Exact ordering for validated UTC timestamps, including up to six fractional digits. */
export function receivedSortKey(value: string | null): string {
  return value === null ? "" : value.replace(/(?:\.(\d{1,6}))?Z$/, (_match, fraction: string | undefined) =>
    `.${(fraction ?? "").padEnd(6, "0")}Z`);
}
export function toDeviceListViewModel(page: DevicePage): DeviceListViewModel {
  const connections: Readonly<Record<Device["connection_status"], { label: string; tone: DisplayTone }>> = {
    recent: { label: "Yakın zamanda rapor alındı", tone: "good" },
    stale: { label: "Eski rapor", tone: "warn" },
    never_seen: { label: "Henüz rapor alınmadı", tone: "neutral" },
  };
  return { rows: page.items.map((device) => ({ device,
    identityLabel: device.identity_status === "revoked" ? "Cihaz kaydı iptal edilmiş" : "Cihaz kaydı iptal edilmemiş",
    connectionLabel: connections[device.connection_status].label, connectionTone: connections[device.connection_status].tone,
  })), loadedCount: page.items.length, scopeLabel: "Bu sayfada yüklenen kayıtlar", nextOffset: page.next_offset,
  canNext: page.next_offset !== null && page.next_offset <= 10000 };
}
