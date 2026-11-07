import type { Device, DevicePage } from "./contracts";
import { receivedSortKey } from "./viewModels";

/** The displayed subset of one loaded page; never mutates the page or its rows. */
export function selectDeviceRows(
  page: DevicePage | null,
  query: string,
  filter: string,
  sort: string,
): readonly Device[] {
  const search = query.trim().toLocaleLowerCase("tr-TR");
  const items = page?.items ?? [];
  return items.filter((device) =>
    (!search || `${device.label} ${device.id}`.toLocaleLowerCase("tr-TR").includes(search)) &&
    (filter === "all" || (filter === "revoked"
      ? device.identity_status === "revoked"
      : device.connection_status === filter)),
  ).sort((a, b) => sort === "received"
    ? receivedSortKey(b.last_received_at).localeCompare(receivedSortKey(a.last_received_at))
    : a.label.localeCompare(b.label, "tr"));
}
