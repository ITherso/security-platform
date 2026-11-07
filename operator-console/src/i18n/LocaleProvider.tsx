import { createContext, useContext, useEffect, useMemo, type ReactNode } from 'react';
import { translate, type Locale, type Translator } from './index';

interface LocaleState { locale: Locale; t: Translator; setLocale: (locale: Locale) => void }
const Context = createContext<LocaleState | null>(null);
export function LocaleProvider({ locale, setLocale, children }: { locale: Locale; setLocale: (locale: Locale) => void; children: ReactNode }) {
  const value = useMemo<LocaleState>(() => ({ locale, setLocale, t: (key, ...args) => translate(locale, key, ...args) }), [locale, setLocale]);
  useEffect(() => { document.documentElement.lang = locale; document.title = translate(locale, 'app.documentTitle'); }, [locale]);
  return <Context.Provider value={value}>{children}</Context.Provider>;
}
export function useLocale(): LocaleState {
  const context = useContext(Context);
  if (!context) throw new Error('locale_provider_unavailable');
  return context;
}
export function LanguageSelect() {
  const { locale, setLocale } = useLocale();
  return <label className="language-select"><span>Dil / Language</span><select aria-label="Dil / Language" value={locale} onChange={(event) => {
    const value = event.target.value, control = event.currentTarget;
    if (value !== 'tr' && value !== 'en') return;
    setLocale(value);
    requestAnimationFrame(() => { if (!control.isConnected) document.querySelector<HTMLSelectElement>('select[aria-label="Dil / Language"]')?.focus(); });
  }}><option value="tr">Türkçe</option><option value="en">English</option></select></label>;
}
