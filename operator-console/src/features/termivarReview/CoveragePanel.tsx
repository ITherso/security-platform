import type { AssessmentDocument } from './termivarModel';
import { booleanLabel, formatCount, formatDate } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

export function CoveragePanel({ document }: { document: AssessmentDocument }) {
  const { locale, t } = useLocale();
  const coverage = document.coverage;
  const count = (value: number | null) => value === null ? t('termivarReview.notPresent') : formatCount(value, locale);
  return <section className="panel termivar-coverage">
    <div className="termivar-panel-heading"><h2>{t('termivarReview.coverageTitle')}</h2></div>
    <p><span className="badge" data-tone={coverage.projectionStatus === 'unavailable' ? 'warning' : 'neutral'}>{t(coverage.projectionStatus === 'unavailable' ? 'termivarReview.projection.unavailable' : 'termivarReview.projection.available')}</span></p>
    <dl className="termivar-key-values">
      <div><dt>{t('termivarReview.scope')}</dt><dd>{coverage.scope === 'exact-origin' ? t('termivarReview.scope.exactOrigin') : t('termivarReview.notPresent')}</dd></div>
      <div><dt>{t('termivarReview.startedAt')}</dt><dd>{coverage.startedAt === null ? t('termivarReview.notPresent') : formatDate(coverage.startedAt, locale)}</dd></div>
      <div><dt>{t('termivarReview.finishedAt')}</dt><dd>{coverage.finishedAt === null ? t('termivarReview.notPresent') : formatDate(coverage.finishedAt, locale)}</dd></div>
      <div><dt>{t('termivarReview.requestLimit')}</dt><dd>{count(coverage.requestLimit)}</dd></div>
      <div><dt>{t('termivarReview.wallTimeLimit')}</dt><dd>{count(coverage.wallTimeLimitMs)}</dd></div>
      <div><dt>{t('termivarReview.requestsUsed')}</dt><dd>{count(coverage.requestsUsed)}</dd></div>
      <div><dt>{t('termivarReview.activeVerifications')}</dt><dd>{count(coverage.activeVerifications)}</dd></div>
      <div><dt>{t('termivarReview.responseBytes')}</dt><dd>{count(coverage.responseBytes)}</dd></div>
      <div><dt>{t('termivarReview.elapsedMs')}</dt><dd>{count(coverage.elapsedMs)}</dd></div>
      <div><dt>{t('termivarReview.semanticTruncated')}</dt><dd>{coverage.semanticTruncated === null ? t('termivarReview.notPresent') : booleanLabel(coverage.semanticTruncated, locale)}</dd></div>
      <div><dt>{t('termivarReview.omittedReceipts')}</dt><dd>{count(coverage.omittedDispatchReceipts)}</dd></div>
      <div><dt>{t('termivarReview.inventoryConsistent')}</dt><dd>{coverage.inventoryConsistent === null ? t('termivarReview.notPresent') : booleanLabel(coverage.inventoryConsistent, locale)}</dd></div>
      <div><dt>{t('termivarReview.unrepresentedSubjects')}</dt><dd>{count(coverage.unrepresentedLedgerSubjects)}</dd></div>
      <div><dt>{t('termivarReview.committedObservations')}</dt><dd>{count(coverage.committedPassiveObservations)}</dd></div>
      {coverage.projectionCode !== null && <div><dt>{t('termivarReview.projectionCode')}</dt><dd><code>{coverage.projectionCode}</code></dd></div>}
    </dl>
    {(coverage.inventoryConsistent === false || (coverage.unrepresentedLedgerSubjects !== null && coverage.unrepresentedLedgerSubjects > 0)) && <p className="termivar-sensitive-warning">{t('termivarReview.inventoryWarning')}</p>}
    <p className="termivar-help">{t(document.artifactType === 'rendered_assessment' ? 'termivarReview.coverageMissing' : 'termivarReview.coverageUsageNote')}</p>
    {document.incompleteReasons.length > 0 && <section className="termivar-incomplete-reasons"><h3>{t('termivarReview.incompleteReasons')}</h3>
      <p className="termivar-help">{t('termivarReview.incompleteReasonCount', formatCount(document.incompleteReasons.length, locale))}</p>
      <ul>{document.incompleteReasons.map((reason, index) => <li key={index}><code>{reason}</code></li>)}</ul>
    </section>}
    <p className="termivar-help">{t('termivarReview.coverageLimit')}</p>
    <p className="termivar-help">{t('termivarReview.knowledgeOnly')}</p>
    <p className="termivar-help">{t('termivarReview.comparisonLimit')}</p>
  </section>;
}
