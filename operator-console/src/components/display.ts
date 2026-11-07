import type { AgeObservation } from "../data/contracts";

const DATE_FORMAT = new Intl.DateTimeFormat("tr-TR", {
  dateStyle: "medium", timeStyle: "short", timeZone: "UTC",
});
const NUMBERS = new Intl.NumberFormat("tr-TR");

export function displayText(value: string | null | undefined, fallback = "Bilinmiyor"): string {
  return typeof value === "string" && value.trim() ? value : fallback;
}

export function formatCount(value: number | null | undefined): string {
  return typeof value === "number" && Number.isSafeInteger(value) && value >= 0
    ? NUMBERS.format(value) : "—";
}

export function shortIdentifier(value: string | null | undefined): string {
  return typeof value === "string" && value ? value.slice(0, 8) : "Bilinmiyor";
}

/** Absolute supplied timestamp, never a claim about the browser's current time. */
export function formatDate(value: string | null | undefined): string {
  if (typeof value !== "string" || !value) return "Zaman bilgisi yok";
  const parsed = new Date(value);
  return Number.isFinite(parsed.getTime()) ? `${DATE_FORMAT.format(parsed)} UTC` : "Zaman bilgisi yok";
}

/** Only use the age and clock state returned by the selected data source. */
export function formatAge(observation: AgeObservation | null | undefined): string {
  if (!observation || observation.clock_state === "unknown") return "Yaş bilinmiyor";
  if (observation.clock_state === "future") return "Kaynak saati ileride";
  if (observation.clock_state !== "not_verified") return "Yaş bilinmiyor";
  const seconds = observation.age_seconds;
  if (typeof seconds !== "number" || !Number.isSafeInteger(seconds) || seconds < 0) return "Yaş bilinmiyor";
  if (seconds < 60) return `${NUMBERS.format(seconds)} sn önce`;
  if (seconds < 3600) return `${NUMBERS.format(Math.floor(seconds / 60))} dk önce`;
  if (seconds < 86400) return `${NUMBERS.format(Math.floor(seconds / 3600))} saat önce`;
  return `${NUMBERS.format(Math.floor(seconds / 86400))} gün önce`;
}

export function booleanLabel(value: boolean | null | undefined): string {
  return value === true ? "Evet" : value === false ? "Hayır" : "Bilinmiyor";
}
