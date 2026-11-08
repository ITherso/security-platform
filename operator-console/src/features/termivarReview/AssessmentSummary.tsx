import type { TermivarReviewErrorCode, TermivarReviewState } from './termivarModel';
import type { TermivarReviewTextKey } from '../../i18n/catalogs/termivarReview';
import { booleanLabel, formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

const ERRORS: Readonly<Record<TermivarReviewErrorCode, TermivarReviewTextKey>> = {
  file_too_large: 'termivarReview.error.file_too_large', invalid_utf8: 'termivarReview.error.invalid_utf8',
  invalid_json: 'termivarReview.error.invalid_json', unsupported_artifact: 'termivarReview.error.unsupported_artifact',
  unsupported_version: 'termivarReview.error.unsupported_version', unsupported_extension: 'termivarReview.error.unsupported_extension',
  invalid_artifact: 'termivarReview.error.invalid_artifact', digest_unavailable: 'termivarReview.error.digest_unavailable',
  unsupported_manifest: 'termivarReview.error.unsupported_manifest',
  reader_unavailable: 'termivarReview.error.reader_unavailable',
};
export function TermivarReviewErrorMessage({ code }: { code: TermivarReviewErrorCode | null }) {
  const { t } = useLocale();
  return <p className="termivar-error" role="alert">{t(code !== null ? ERRORS[code] : 'termivarReview.error.invalid_artifact')}</p>;
}

export function AssessmentSummary({ state }: { state: TermivarReviewState }) {
  const { locale, t } = useLocale();
  const document = state.document;
  if (!document) return null;
  const manifest = state.manifestStatus === 'ready' ? state.manifest : null;
  return <section className="panel termivar-summary">
    <div className="termivar-panel-heading"><h2>{t('termivarReview.summaryTitle')}</h2>
      <span className="badge" data-tone={document.status === 'complete' ? 'neutral' : 'warning'}>{t(`termivarReview.status.${document.status}`)}</span></div>
    <p className="termivar-source-label">{t(document.source === 'example' ? 'termivarReview.source.example' : 'termivarReview.source.file')}</p>
    <p className="termivar-artifact-kind">{t(document.artifactType === 'rendered_assessment' ? 'termivarReview.artifact.rendered' : 'termivarReview.artifact.diagnostic')}</p>
    <dl className="termivar-key-values">
      <div><dt>{t('termivarReview.schema')}</dt><dd><code>{document.schema}</code></dd></div>
      <div><dt>{t('termivarReview.profile')}</dt><dd><code>{document.profile}</code></dd></div>
      <div><dt>{t('termivarReview.subjectCount')}</dt><dd>{formatCount(document.subjectCount, locale)}</dd></div>
      <div><dt>{t('termivarReview.itemCount')}</dt><dd>{document.itemCount === null ? t('termivarReview.itemsWithheld') : formatCount(document.itemCount, locale)}</dd></div>
    </dl>
    {document.counts !== null && <><h3>{t('termivarReview.countsTitle')}</h3><dl className="termivar-type-counts">
      {(['informational', 'needs_review', 'confirmed'] as const).map(kind => <div key={kind}><dt>{t(`termivarReview.disposition.${kind}`)}</dt><dd>{formatCount(document.counts![kind], locale)}</dd></div>)}
    </dl><p className="termivar-help">{t('termivarReview.countsNote')}</p></>}
    <p className="termivar-help">{document.status === 'complete' ? t('termivarReview.completeNote') : t('termivarReview.incompleteEmpty')}</p>
    <p className="termivar-claims">{t('termivarReview.sourceClaim')} · {t('termivarReview.notVerified')}</p>
    <section className="termivar-manifest">
      <h3>{t('termivarReview.manifest.title')}</h3>
      {state.manifestStatus === 'not_selected' && <p className="termivar-help">{t('termivarReview.manifest.notSelected')}</p>}
      {state.manifestStatus === 'loading' && <p className="termivar-help" role="status">{t('termivarReview.manifest.loading')}</p>}
      {state.manifestStatus === 'error' && <TermivarReviewErrorMessage code={state.manifestErrorCode} />}
      {manifest && <>
        <p className="termivar-manifest-status"><span className="badge" data-tone={manifest.status === 'mismatch' ? 'danger' : 'neutral'}>{t(manifest.status === 'mismatch' ? 'termivarReview.manifest.mismatch' : 'termivarReview.manifest.matches')}</span></p>
        <dl className="termivar-key-values">
          <div><dt>{t('termivarReview.manifest.hash')}</dt><dd>{booleanLabel(manifest.jsonHashMatches, locale)}</dd></div>
          <div><dt>{t('termivarReview.manifest.length')}</dt><dd>{booleanLabel(manifest.jsonLengthMatches, locale)}</dd></div>
          <div><dt>{t('termivarReview.manifest.summary')}</dt><dd>{booleanLabel(manifest.summaryMatches, locale)}</dd></div>
          <div><dt>{t('termivarReview.manifest.producer')}</dt><dd>{manifest.producerProduct}</dd></div>
          <div><dt>{t('termivarReview.manifest.version')}</dt><dd>{state.showDetails ? manifest.producerVersion : t('termivarReview.detailsHidden')}</dd></div>
        </dl>
        <p className="termivar-help">{t('termivarReview.manifest.html')}</p>
      </>}
      <p className="termivar-help">{t('termivarReview.manifest.limits')}</p>
    </section>
  </section>;
}
