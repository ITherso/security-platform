import { messagesTr } from './messages.tr';
import { messagesEn } from './messages.en';
import type { Locale } from './types';
export type { Locale } from './types';
export type MessageKey = keyof typeof messagesTr;
export type MessageArgs<K extends MessageKey> = (typeof messagesTr)[K] extends (...args: infer A) => string ? A : [];
export type Translator = <K extends MessageKey>(key: K, ...args: MessageArgs<K>) => string;
// Static messages share the same empty tuple. Grouping them preserves key/args
// checking without expanding a separate object union for every catalog string.
type StaticMessageKey = { [K in MessageKey]: MessageArgs<K> extends [] ? K : never }[MessageKey];
type ArgumentMessageKey = Exclude<MessageKey, StaticMessageKey>;
export type UiMessage = { readonly key: StaticMessageKey; readonly args: []; readonly sample?: boolean }
  | { [K in ArgumentMessageKey]: { readonly key: K; readonly args: MessageArgs<K>; readonly sample?: boolean } }[ArgumentMessageKey];

function resolve(locale: Locale, key: MessageKey, args: readonly unknown[]): string {
  const value = (locale === 'en' ? messagesEn : messagesTr)[key];
  return typeof value === 'function' ? (value as (...values: readonly unknown[]) => string)(...args) : value;
}
export function translate<K extends MessageKey>(locale: Locale, key: K, ...args: MessageArgs<K>): string {
  return resolve(locale, key, args);
}
export function message<K extends MessageKey>(key: K, ...args: MessageArgs<K>): UiMessage {
  return { key, args } as UiMessage;
}
export function renderMessage(locale: Locale, value: UiMessage | null): string {
  if (!value) return '';
  const text = resolve(locale, value.key, value.args);
  return value.sample ? translate(locale, 'app.error.demo', text) : text;
}
