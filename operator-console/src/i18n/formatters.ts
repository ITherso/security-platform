import type { AgeObservation } from '../data/contracts';
import { translate, type Locale } from './index';
const DATES = {
  tr: new Intl.DateTimeFormat('tr-TR', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' }),
  en: new Intl.DateTimeFormat('en-GB', { dateStyle: 'medium', timeStyle: 'short', timeZone: 'UTC' })
};
const NUMBERS = { tr: new Intl.NumberFormat('tr-TR'), en: new Intl.NumberFormat('en-GB') };
export function displayText(value: string | null | undefined, fallback?: string, locale: Locale = 'tr'): string {
  return typeof value === 'string' && value.trim() ? value : fallback ?? translate(locale, 'display.unknown');
}
export function shortIdentifier(value: string | null | undefined, locale: Locale = 'tr'): string {
  return typeof value === 'string' && value ? value.slice(0, 8) : translate(locale, 'display.unknown');
}
export function formatCount(value: number | null | undefined, locale: Locale = 'tr'): string {
  return typeof value === 'number' && Number.isSafeInteger(value) && value >= 0 ? NUMBERS[locale].format(value) : '—';
}
export function formatDate(value: string | null | undefined, locale: Locale = 'tr'): string {
  if (typeof value !== 'string' || !value) return translate(locale, 'display.noTimestamp');
  const parts = /^(\d{4})-(\d{2})-(\d{2})T(\d{2}):(\d{2}):(\d{2})(?:\.(\d{1,6}))?Z$/.exec(value);
  if (!parts) return translate(locale, 'display.noTimestamp');
  const [year, month, day, hour, minute, second] = parts.slice(1, 7).map(Number);
  const date = new Date(0);
  date.setUTCFullYear(year, month - 1, day);
  date.setUTCHours(hour, minute, second, Number((parts[7] ?? '').padEnd(3, '0').slice(0, 3)));
  if (year < 1 || date.getUTCFullYear() !== year || date.getUTCMonth() !== month - 1 || date.getUTCDate() !== day
    || date.getUTCHours() !== hour || date.getUTCMinutes() !== minute || date.getUTCSeconds() !== second)
    return translate(locale, 'display.noTimestamp');
  return `${DATES[locale].format(date)} UTC`;
}
export function booleanLabel(value: boolean | null | undefined, locale: Locale = 'tr'): string {
  return translate(locale, value === true ? 'display.yes' : value === false ? 'display.no' : 'display.unknown');
}
/** No clock or freshness threshold: present only the source's supplied observation. */
export function formatAge(observation: AgeObservation | null | undefined, locale: Locale = 'tr'): string {
  if (!observation || observation.clock_state === 'unknown') return translate(locale, 'display.unknownAge');
  if (observation.clock_state === 'future') return translate(locale, 'display.futureClock');
  const seconds = observation.age_seconds;
  if (observation.clock_state !== 'not_verified' || typeof seconds !== 'number' || !Number.isSafeInteger(seconds) || seconds < 0) return translate(locale, 'display.unknownAge');
  const key = seconds < 60 ? 'display.secondsAgo' : seconds < 3600 ? 'display.minutesAgo' : seconds < 86400 ? 'display.hoursAgo' : 'display.daysAgo';
  const count = seconds < 60 ? seconds : Math.floor(seconds / (seconds < 3600 ? 60 : seconds < 86400 ? 3600 : 86400));
  return translate(locale, key, formatCount(count, locale), count);
}
