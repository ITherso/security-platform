export type Locale = 'tr' | 'en';
export const LOCALES: readonly Locale[] = ['tr', 'en'];
/** Same keys and function arguments, with independent translated string values. */
export type CatalogShape<T> = { [K in keyof T]: T[K] extends (...args: infer A) => string ? (...args: A) => string : string };
