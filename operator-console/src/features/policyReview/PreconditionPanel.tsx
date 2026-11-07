import type { PolicyReviewDocument } from './policyReviewModel';
import { useLocale } from '../../i18n/LocaleProvider';

export function PreconditionPanel({ document }: { document: PolicyReviewDocument }) {
  const { t } = useLocale();
  return <section className="panel policy-review-preconditions">
    <div className="panel-heading"><h2>{t('policyReview.preconditionsTitle')}</h2><span className="badge" data-tone="warning">{t('policyReview.preconditionsMissing')}</span></div>
    <p>{t('policyReview.preconditionsDescription')}</p>
    <dl className="policy-review-evidence">
      <div><dt>{t('policyReview.precondition.controller')}</dt><dd>{t('policyReview.notInResult')}</dd></div>
      <div><dt>{t('policyReview.precondition.endpoint')}</dt><dd>{t('policyReview.notInResult')}</dd></div>
      <div><dt>{t('policyReview.precondition.cas')}</dt><dd>{t('policyReview.notInResult')}</dd></div>
      <div><dt>{t('policyReview.precondition.plan')}</dt><dd>{t('policyReview.notInResult')}</dd></div>
    </dl>
    <p className="policy-review-help">{t('policyReview.precondition.noMerge')}</p>
    <p className="policy-review-help">{t('policyReview.precondition.missingMeaning')}</p>
    <p className="policy-review-help">{t('policyReview.precondition.pauseMeaning')}</p>
    <dl className="policy-review-evidence policy-review-guards">
      <div><dt>{t('policyReview.guard.authorization')}</dt><dd>{t('policyReview.guard.authorizationValue')}<code>authorization={document.authorization}</code></dd></div>
      <div><dt>{t('policyReview.guard.execution')}</dt><dd>{t('policyReview.guard.executionValue')}<code>execution_authorized={String(document.executionAuthorized)}</code></dd></div>
      <div><dt>{t('policyReview.guard.verification')}</dt><dd>{t('policyReview.guard.verificationValue')}<code>verification={document.verification}</code></dd></div>
      <div><dt>{t('policyReview.guard.scope')}</dt><dd>{t('policyReview.guard.scopeValue')}<code>{document.scope}</code></dd></div>
    </dl>
    <p className="policy-review-help">{t('policyReview.noExecution')}</p>
  </section>;
}
