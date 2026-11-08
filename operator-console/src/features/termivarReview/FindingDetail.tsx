import type { TermivarFinding } from './termivarModel';
import { formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

export function FindingDetail({ finding, ordinal, showDetails, example = false, incomplete = false }: {
  finding: TermivarFinding | null; ordinal: number; showDetails: boolean; example?: boolean; incomplete?: boolean;
}) {
  const { locale, t } = useLocale();
  return <section className="panel termivar-finding-detail">
    <div className="termivar-panel-heading"><h2>{t('termivarReview.detailTitle')}</h2>{finding && <span className="badge" data-tone="neutral">{t('termivarReview.finding', String(ordinal))}</span>}</div>
    {example && <p className="termivar-example">{t('termivarReview.example')}</p>}
    {!finding ? <p className="termivar-empty-message">{t(incomplete ? 'termivarReview.incompleteEmpty' : 'termivarReview.selectFinding')}</p> : <>
      <dl className="termivar-key-values">
        <div><dt>{t('termivarReview.disposition')}</dt><dd>{t(`termivarReview.disposition.${finding.disposition}`)}<code>{finding.disposition}</code></dd></div>
        <div><dt>{t('termivarReview.severity')}</dt><dd>{t(`termivarReview.severity.${finding.severity ?? 'unassigned'}`)}</dd></div>
        <div><dt>{t('termivarReview.claimBasis')}</dt><dd>{t(`termivarReview.basis.${finding.claimBasis}`)}<code>{finding.claimBasis}</code></dd></div>
        <div><dt>{t('termivarReview.verificationStage')}</dt><dd>{finding.verificationStage === null ? t('termivarReview.notPresent') : t(`termivarReview.stage.${finding.verificationStage}`)}</dd></div>
      </dl>
      <p className="termivar-interpretation">{t(finding.disposition === 'needs_review' ? 'termivarReview.needsReviewNote'
        : finding.disposition === 'confirmed' ? 'termivarReview.confirmedNote' : 'termivarReview.observationNote')}</p>
      <h3>{t('termivarReview.evidenceTitle')}</h3>
      <dl className="termivar-evidence-counts">
        <div><dt>{t('termivarReview.evidence.total')}</dt><dd>{formatCount(finding.evidenceCount, locale)}</dd></div>
        <div><dt>{t('termivarReview.evidence.direct')}</dt><dd>{formatCount(finding.directEvidenceCount, locale)}</dd></div>
        <div><dt>{t('termivarReview.evidence.control')}</dt><dd>{formatCount(finding.controlEvidenceCount, locale)}</dd></div>
        <div><dt>{t('termivarReview.evidence.candidate')}</dt><dd>{formatCount(finding.candidateEvidenceCount, locale)}</dd></div>
      </dl>
      <p className="termivar-help">{t('termivarReview.evidence.limit')}</p>
      <dl className="termivar-key-values"><div><dt>{t('termivarReview.confidence')}</dt><dd>{formatCount(finding.confidencePpm, locale)} ppm</dd></div></dl>
      <p className="termivar-help">{t('termivarReview.confidenceNote')}</p>
      {showDetails ? <section className="termivar-permitted-metadata"><h3>{t('termivarReview.metadataTitle')}</h3><dl className="termivar-key-values">
        <div><dt>{t('termivarReview.metadata.title')}</dt><dd>{finding.title}</dd></div>
        <div><dt>{t('termivarReview.metadata.summary')}</dt><dd>{finding.redactedSummary}</dd></div>
        <div><dt>{t('termivarReview.metadata.capability')}</dt><dd>{finding.capabilityId}</dd></div>
        <div><dt>{t('termivarReview.metadata.category')}</dt><dd>{finding.category}</dd></div>
        <div><dt>{t('termivarReview.metadata.cwe')}</dt><dd>{finding.cwe ?? t('termivarReview.notPresent')}</dd></div>
        <div><dt>{t('termivarReview.metadata.remediationId')}</dt><dd>{finding.remediationId}</dd></div>
        <div><dt>{t('termivarReview.metadata.remediation')}</dt><dd>{finding.remediationSummary}</dd></div>
      </dl><p className="termivar-help">{t('termivarReview.remediationNote')}</p></section>
        : <p className="termivar-help">{t('termivarReview.detailsHidden')}</p>}
      <p className="termivar-claims">{t('termivarReview.sourceClaim')} · {t('termivarReview.notVerified')}</p>
    </>}
  </section>;
}
