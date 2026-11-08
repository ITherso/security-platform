import { Component, Suspense, type ReactNode } from 'react';
import { useLocale } from '../i18n/LocaleProvider';

class ScreenFailureBoundary extends Component<{ children: ReactNode; fallback: ReactNode }, { failed: boolean }> {
  state = { failed: false };
  static getDerivedStateFromError() { return { failed: true }; }
  render() { return this.state.failed ? this.props.fallback : this.props.children; }
}

/** Loading UI has no loader, request, timer or state authority of its own. */
export function ScreenBoundary({ children, onBack }: { children: ReactNode; onBack: () => void }) {
  const { t } = useLocale();
  return <ScreenFailureBoundary fallback={<section className="panel empty-state" role="alert">
    <h2>{t('productHub.loadErrorTitle')}</h2><p>{t('productHub.loadErrorDescription')}</p>
    <button type="button" className="btn btn-ghost" onClick={onBack}>{t('productHub.backToHub')}</button>
  </section>}><Suspense fallback={<section className="panel empty-state" role="status" aria-live="polite">{t('productHub.loading')}</section>}>
    {children}
  </Suspense></ScreenFailureBoundary>;
}
