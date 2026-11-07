import { useEffect, useState } from 'react';
import type { PolicyReviewDocument } from './policyReviewModel';
import type { PolicyReviewTextKey } from '../../i18n/catalogs/policyReview';
import { useLocale } from '../../i18n/LocaleProvider';
import { formatCount } from '../../i18n/formatters';

const BLOCKERS: Readonly<Record<string, PolicyReviewTextKey>> = {
  evaluator_unavailable: 'policyReview.blocker.evaluator_unavailable',
  invalid_policy_bundle: 'policyReview.blocker.invalid_policy_bundle',
  ambiguous_equal_prefix_zones: 'policyReview.blocker.ambiguous_equal_prefix_zones',
  insufficient_context: 'policyReview.blocker.insufficient_context',
  input_limit_exceeded: 'policyReview.blocker.input_limit_exceeded',
  invalid_scenario: 'policyReview.blocker.invalid_scenario',
  invalid_evaluator_result: 'policyReview.blocker.invalid_evaluator_result',
  evaluator_failed: 'policyReview.blocker.evaluator_failed',
};

function Fingerprint({ label, value, help }: { label: string; value: string | null; help?: string }) {
  const { t } = useLocale();
  const [expanded, setExpanded] = useState(false);
  useEffect(() => { setExpanded(false); }, [value]);
  const prefix = value?.includes(':') ? value.slice(0, value.lastIndexOf(':') + 1) : '';
  const digest = value?.slice(prefix.length) ?? '';
  const abbreviated = value ? `${prefix}${digest.slice(0, 8)}…${digest.slice(-8)}` : t('policyReview.notInResult');
  return <div className="policy-review-fingerprint">
    <dt>{label}</dt><dd><code>{expanded && value !== null ? value : abbreviated}</code>
      {value !== null && <button type="button" className="text-button" aria-expanded={expanded} onClick={() => setExpanded(!expanded)}>
        {t(expanded ? 'policyReview.fingerprint.collapse' : 'policyReview.fingerprint.expand')}</button>}
      {help && <small>{help}</small>}
    </dd>
  </div>;
}

export function PolicySummary({ document }: { document: PolicyReviewDocument }) {
  const { locale, t } = useLocale();
  return <section className="panel policy-review-summary">
    <div className="panel-heading"><div><h2>{t('policyReview.summaryTitle')}</h2><p>{t(document.source === 'example' ? 'policyReview.exampleSource' : 'policyReview.fileSource')}</p></div>
      <span className="badge" data-tone={document.status === 'blocked' ? 'warning' : 'neutral'}>{t(document.status === 'blocked' ? 'policyReview.status.blocked' : 'policyReview.status.ok')}</span></div>
    {document.source === 'example' && <p className="policy-review-example">{t('policyReview.example')}</p>}
    <dl className="policy-review-stats">
      <div><dt>{t('policyReview.totalScenarios')}</dt><dd>{formatCount(document.scenarios.length, locale)}</dd></div>
      <div><dt>{t('policyReview.changedDecisions')}</dt><dd>{formatCount(document.scenarios.filter(row => row.decisionChanged).length, locale)}</dd></div>
      <div><dt>{t('policyReview.changedPolicies')}</dt><dd>{formatCount(document.scenarios.filter(row => row.matchedPolicyChanged).length, locale)}</dd></div>
    </dl>
    <p className="policy-review-help">{t('policyReview.summaryHelp')}</p>
    <p className="policy-review-contract"><strong>{t('policyReview.contractVersion')}:</strong> <code>{document.contractVersion}</code></p>
    {document.blockerCodes.length > 0 && <div className="policy-review-blockers"><h3>{t('policyReview.blockers')}</h3><ul>{document.blockerCodes.map((code, index) => <li key={index}>
      {t(Object.hasOwn(BLOCKERS, code) ? BLOCKERS[code]! : 'policyReview.blocker.unknown')}
    </li>)}</ul></div>}
    <h3 className="policy-review-subheading">{t('policyReview.fingerprints')}</h3>
    <p className="policy-review-help">{t('policyReview.fingerprint.help')} {t('policyReview.fingerprint.shortHelp')}</p>
    <dl className="policy-review-fingerprints">
      <Fingerprint label={t('policyReview.fingerprint.base')} value={document.baseFingerprint} />
      <Fingerprint label={t('policyReview.fingerprint.candidate')} value={document.candidateFingerprint} />
      <Fingerprint label={t('policyReview.fingerprint.adapter')} value={document.adapterFingerprint} />
      <Fingerprint label={t('policyReview.fingerprint.preview')} value={document.previewFingerprint} />
      <Fingerprint label={t('policyReview.fingerprint.legacy')} value={document.legacyBaseVersion} help={t('policyReview.fingerprint.legacyHelp')} />
    </dl>
  </section>;
}
