import type { ComparisonChangedField, ComparisonProjection, ComparisonRecord } from './comparisonModel';
import { ComparisonFingerprint } from './ComparisonSummary';
import type { TermivarComparisonTextKey } from '../../i18n/catalogs/termivarComparison';
import { booleanLabel, formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

const CHANGED_FIELDS: Readonly<Record<ComparisonChangedField, TermivarComparisonTextKey>> = {
  title: 'termivarComparison.field.title', category: 'termivarComparison.field.category',
  disposition: 'termivarComparison.field.disposition', claim_basis: 'termivarComparison.field.claim_basis',
  severity: 'termivarComparison.field.severity', cwe: 'termivarComparison.field.cwe',
  confidence_ppm: 'termivarComparison.field.confidence_ppm', redacted_summary: 'termivarComparison.field.redacted_summary',
  remediation: 'termivarComparison.field.remediation', evidence: 'termivarComparison.field.evidence',
};

function Projection({ value, side, showDetails }: { value: ComparisonProjection | null; side: 'before' | 'after'; showDetails: boolean }) {
  const { locale, t } = useLocale();
  return <article className="termivar-comparison-projection"><h3>{t(side === 'before' ? 'termivarComparison.before' : 'termivarComparison.after')}</h3>
    {value === null ? <p className="termivar-comparison-missing">{t(side === 'before' ? 'termivarComparison.beforeMissing' : 'termivarComparison.afterMissing')}</p> : <>
      <dl className="termivar-comparison-values">
        <div><dt>{t('termivarReview.disposition')}</dt><dd>{t(`termivarReview.disposition.${value.disposition}`)}<code>{value.disposition}</code></dd></div>
        <div><dt>{t('termivarReview.claimBasis')}</dt><dd>{t(`termivarReview.basis.${value.claimBasis}`)}<code>{value.claimBasis}</code></dd></div>
        <div><dt>{t('termivarReview.severity')}</dt><dd>{t(`termivarReview.severity.${value.severity ?? 'unassigned'}`)}</dd></div>
        <div><dt>{t('termivarReview.confidence')}</dt><dd>{formatCount(value.confidencePpm, locale)} ppm</dd></div>
        <div><dt>{t('termivarReview.evidence.total')}</dt><dd>{formatCount(value.evidence.evidenceCount, locale)}</dd></div>
        <div><dt>{t('termivarReview.evidence.direct')}</dt><dd>{formatCount(value.evidence.directReferenceCount, locale)}</dd></div>
        <div><dt>{t('termivarReview.evidence.control')}</dt><dd>{formatCount(value.evidence.controlReferenceCount, locale)}</dd></div>
        <div><dt>{t('termivarReview.evidence.candidate')}</dt><dd>{formatCount(value.evidence.candidateReferenceCount, locale)}</dd></div>
        <div><dt>{t('termivarComparison.evidence.case')}</dt><dd>{booleanLabel(value.evidence.casePresent, locale)}</dd></div>
        <div><dt>{t('termivarComparison.evidence.outcome')}</dt><dd>{booleanLabel(value.evidence.outcomePresent, locale)}</dd></div>
        <div><dt>{t('termivarReview.verificationStage')}</dt><dd>{value.evidence.verificationStage === null ? t('termivarReview.notPresent') : t(`termivarReview.stage.${value.evidence.verificationStage}`)}</dd></div>
      </dl>
      {showDetails ? <section className="termivar-comparison-projection-metadata"><h4>{t('termivarReview.metadataTitle')}</h4><dl className="termivar-comparison-values">
        <div><dt>{t('termivarReview.metadata.title')}</dt><dd>{value.title}</dd></div>
        <div><dt>{t('termivarReview.metadata.summary')}</dt><dd>{value.redactedSummary}</dd></div>
        <div><dt>{t('termivarReview.metadata.category')}</dt><dd>{value.category}</dd></div>
        <div><dt>{t('termivarReview.metadata.cwe')}</dt><dd>{value.cwe ?? t('termivarReview.notPresent')}</dd></div>
        <div><dt>{t('termivarReview.metadata.remediationId')}</dt><dd>{value.remediation.id}</dd></div>
        <div><dt>{t('termivarReview.metadata.remediation')}</dt><dd>{value.remediation.summary}</dd></div>
      </dl><p className="termivar-comparison-help">{t('termivarReview.remediationNote')}</p></section>
        : <p className="termivar-comparison-help">{t('termivarComparison.detailsHidden')}</p>}
    </>}
  </article>;
}

export function ComparisonItemDetail({ record, ordinal, showDetails, example = false }: { record: ComparisonRecord | null; ordinal: number; showDetails: boolean; example?: boolean }) {
  const { t } = useLocale();
  return <section className="panel termivar-comparison-detail">
    <div className="termivar-comparison-heading"><h2>{t('termivarComparison.detailTitle')}</h2>{record && <span className="badge" data-tone="neutral">{t('termivarComparison.item', String(ordinal))}</span>}</div>
    {example && <p className="termivar-comparison-example">{t('termivarComparison.example')}</p>}
    {record === null ? <p className="termivar-comparison-empty">{t('termivarComparison.selectItem')}</p> : <>
      <p className="termivar-comparison-item-group"><span className="badge" data-tone="neutral">{t(`termivarComparison.group.${record.group}`)}</span></p>
      <p className="termivar-comparison-interpretation">{t(`termivarComparison.groupHelp.${record.group}`)}</p>
      <section className="termivar-comparison-changed-fields"><h3>{t('termivarComparison.changedFields')}</h3>
        {record.changedFields.length > 0 ? <ul>{record.changedFields.map(field => <li key={field}>{t(CHANGED_FIELDS[field])} <code>{field}</code></li>)}</ul>
          : <p className="termivar-comparison-help">{t('termivarComparison.noChangedFields')}</p>}
      </section>
      {showDetails && <section className="termivar-comparison-record-metadata"><dl className="termivar-comparison-values"><div><dt>{t('termivarReview.metadata.capability')}</dt><dd>{record.capabilityId}</dd></div></dl>
        <ComparisonFingerprint label={t('termivarComparison.itemFingerprint')} value={record.fingerprint} /></section>}
      <div className="termivar-comparison-projection-pair"><Projection value={record.before} side="before" showDetails={showDetails} />
        <Projection value={record.after} side="after" showDetails={showDetails} /></div>
      <p className="termivar-comparison-help">{t('termivarComparison.claimLimit')}</p>
      <p className="termivar-comparison-help">{t('termivarComparison.confidenceLimit')}</p>
      <p className="termivar-comparison-help">{t('termivarComparison.evidence.limit')}</p>
    </>}
  </section>;
}
