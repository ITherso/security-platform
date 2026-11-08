import { PRODUCT_HUB_ENTRIES } from './productCatalog';
import type { HubDestination, ProductHubEntry } from './productCatalog';
import { GUIDE_FLOWS, GUIDE_FLOW_LABELS } from './guideModel';
import type { GuideFlow } from './guideModel';
import { useLocale } from '../../i18n/LocaleProvider';
import './productHub.css';

export interface HubPageProps {
  onNavigate: (view: HubDestination) => void;
  onStartGuide: (flow: GuideFlow) => void;
  guideAvailable: boolean;
}
const SYMBOLS: Readonly<Record<ProductHubEntry['id'], string>> = {
  hostbasedfirewall: '◈', termivar: '⌁', 'policy-impact-workbench': '≍', 'security-platform': '▦', antivirus: '◇',
};

export function HubPage({ onNavigate, onStartGuide, guideAvailable }: HubPageProps) {
  const { t } = useLocale();
  return <div className="product-hub-page">
    <section className="panel product-hub-intro"><h2>{t('productHub.introTitle')}</h2><p>{t('productHub.intro')}</p></section>
    <section className="product-hub-catalog" aria-label={t('productHub.catalogLabel')}>
      {PRODUCT_HUB_ENTRIES.map(entry => <article key={entry.id} className="panel product-hub-card">
        <div className="product-hub-card-heading"><span className="product-hub-symbol" aria-hidden="true">{SYMBOLS[entry.id]}</span>
          <div><p className="eyebrow">{t(entry.kind === 'product' ? 'productHub.kind.product' : 'productHub.kind.component')}</p><h2>{t(entry.titleKey)}</h2><code>{entry.id}</code></div></div>
        <p className="product-hub-description">{t(entry.descriptionKey)}</p>
        <dl className="product-hub-capability">
          <div><dt>{t('productHub.currentFeature')}</dt><dd>{t(entry.featureKey)}</dd></div>
          <div><dt>{t('productHub.limitation')}</dt><dd>{t(entry.limitationKey)}</dd></div>
          <div><dt>{t('productHub.dataSource')}</dt><dd>{t(entry.dataSourceKey)}</dd></div>
        </dl>
        <dl className="product-hub-assurance">
          <div><dt>{t('productHub.availability')}</dt><dd><span className="badge" data-tone={entry.availability === 'planned_unavailable' ? 'neutral' : 'purple'}>{t(entry.availability === 'planned_unavailable' ? 'productHub.availability.planned' : 'productHub.availability.available')}</span></dd></div>
          <div><dt>{t('productHub.verification')}</dt><dd>{t('productHub.verification.notVerified')}</dd></div>
        </dl>
        <button type="button" className="btn btn-ghost" onClick={() => onNavigate(entry.destination)}>{t(entry.actionKey)}</button>
      </article>)}
    </section>
    <p className="product-hub-boundary">{t('productHub.catalogBoundary')}</p>
    <section className="panel product-hub-guides"><div className="product-hub-guides-heading"><h2>{t('productHub.explore')}</h2><p>{t('productHub.guidesTitle')}</p></div>
      <p className="product-hub-help">{t('productHub.guidesDescription')}</p>
      {!guideAvailable && <p className="product-hub-guide-unavailable">{t('productHub.guideUnavailable')}</p>}
      <div className="product-hub-guide-options">{GUIDE_FLOWS.map(flow => <article key={flow}><h3>{t(GUIDE_FLOW_LABELS[flow])}</h3>
        <p>{t(`productHub.flowDescription.${flow}`)}</p>
        <button type="button" className="btn btn-primary" disabled={!guideAvailable} aria-label={t('productHub.startFlow', t(GUIDE_FLOW_LABELS[flow]))} onClick={() => {
          if (guideAvailable) onStartGuide(flow);
        }}>{t('productHub.explore')}</button>
      </article>)}</div>
    </section>
  </div>;
}
