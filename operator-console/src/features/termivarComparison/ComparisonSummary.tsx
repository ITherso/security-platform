import { useState } from 'react';
import type { ComparisonSourceMetadata, TermivarComparisonDocument } from './comparisonModel';
import { useLocale } from '../../i18n/LocaleProvider';
import { formatCount } from '../../i18n/formatters';

/** Mounted only inside the explicit metadata view. Full values require a second action. */
export function ComparisonFingerprint({ label, value }: { label: string; value: string }) {
  const { t } = useLocale();
  const [expandedValue, setExpandedValue] = useState<string | null>(null);
  const expanded = expandedValue === value;
  const prefix = value.startsWith('sha256:') ? 'sha256:' : '';
  const digest = value.slice(prefix.length);
  return <div className="termivar-comparison-fingerprint"><strong>{label}</strong>
    <code>{expanded ? value : `${prefix}${digest.slice(0, 8)}…${digest.slice(-8)}`}</code>
    <button type="button" className="text-button" aria-expanded={expanded} onClick={() => setExpandedValue(expanded ? null : value)}>{t(expanded ? 'termivarComparison.collapse' : 'termivarComparison.expand')}</button>
  </div>;
}

function SourceSummary({ source, label, showDetails }: { source: ComparisonSourceMetadata; label: string; showDetails: boolean }) {
  const { locale, t } = useLocale();
  return <article className="termivar-comparison-source"><h3>{label}</h3>
    <dl className="termivar-comparison-values">
      <div><dt>{t('termivarReview.schema')}</dt><dd><code>{source.schema}</code></dd></div>
      <div><dt>{t('termivarReview.profile')}</dt><dd><code>{source.profile}</code></dd></div>
      <div><dt>{t('termivarReview.subjectCount')}</dt><dd>{formatCount(source.subjectCount, locale)}</dd></div>
      <div><dt>{t('termivarReview.itemCount')}</dt><dd>{formatCount(source.itemCount, locale)}</dd></div>
    </dl>
    <p className="termivar-comparison-source-status"><span className="badge" data-tone="neutral">{t('termivarReview.status.complete')}</span></p>
    {showDetails ? <><ComparisonFingerprint label={t('termivarComparison.sourceHash')} value={source.sha256} />
      <p className="termivar-comparison-help">{t('termivarComparison.sourceHashClaim')}</p></>
      : <p className="termivar-comparison-help">{t('termivarComparison.detailsHidden')}</p>}
  </article>;
}

export function ComparisonSummary({ document, showDetails }: { document: TermivarComparisonDocument; showDetails: boolean }) {
  const { t } = useLocale();
  return <section className="panel termivar-comparison-summary">
    <div className="termivar-comparison-heading"><div><h2>{t('termivarComparison.summaryTitle')}</h2><p>{t(document.source === 'example' ? 'termivarComparison.source.example' : 'termivarComparison.source.file')}</p></div>
      <code>{document.schema}</code></div>
    <section className="termivar-comparison-assurance"><h3>{t('termivarComparison.scopeTitle')}</h3>
      <ul><li>{t('termivarComparison.scope')} <code>{document.scopeAssurance}</code></li>
        <li>{t('termivarComparison.coverage')} <code>{document.coverageEquivalence}</code></li>
        <li>{t('termivarComparison.authenticity')} <code>{document.sourceAuthenticity}</code></li></ul>
      <p>{t('termivarComparison.scopeHelp')}</p>
    </section>
    <div className="termivar-comparison-sources"><SourceSummary source={document.before} label={t('termivarComparison.before')} showDetails={showDetails} />
      <SourceSummary source={document.after} label={t('termivarComparison.after')} showDetails={showDetails} /></div>
    <p className="termivar-comparison-help">{t('termivarComparison.fingerprintHelp')}</p>
    <p className="termivar-comparison-help">{t('termivarComparison.optionalLimit')}</p>
  </section>;
}
