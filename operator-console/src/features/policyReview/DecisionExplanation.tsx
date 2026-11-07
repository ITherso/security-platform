import type { PolicyReviewEvaluation, PolicyReviewScenario } from './policyReviewModel';
import { booleanLabel, formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

function Evaluation({ evaluation, label, showDetails }: { evaluation: PolicyReviewEvaluation; label: string; showDetails: boolean }) {
  const { locale, t } = useLocale();
  const decision = evaluation.decision;
  return <article className="policy-review-evaluation">
    <h3>{label}</h3><p className="policy-review-decision"><span>{t('policyReview.decision')}</span><strong>{t(`policyReview.action.${decision.action}`)}</strong></p>
    <dl className="policy-review-evaluation-values">
      <div><dt>{t('policyReview.matchedRule')}</dt><dd>{decision.policyId === null ? t('policyReview.defaultRule') : showDetails
        ? <>{t('policyReview.rule', String(decision.policyId))}{decision.policyName !== null && <span>{decision.policyName}</span>}</>
        : t('policyReview.ruleHidden')}</dd></div>
      <div><dt>{t('policyReview.reason')}</dt><dd>{showDetails ? decision.reason : t('policyReview.hidden')}</dd></div>
      <div><dt>{t('policyReview.natIntent')}</dt><dd>{booleanLabel(decision.natIntent, locale)}</dd></div>
      <div><dt>{t('policyReview.logIntent')}</dt><dd>{booleanLabel(decision.logIntent, locale)}</dd></div>
      {decision.tempBlockSeconds !== null && <div><dt>{t('policyReview.tempBlock')}</dt><dd>{t('policyReview.seconds', formatCount(decision.tempBlockSeconds, locale))}</dd></div>}
    </dl>
    <h4>{t('policyReview.traceTitle')}</h4>
    <p className="policy-review-help">{t('policyReview.traceCount', formatCount(evaluation.trace.length, locale), formatCount(evaluation.traceTotal, locale))}</p>
    {!showDetails && <p className="policy-review-help">{t('policyReview.traceHiddenHelp')}</p>}
    {!evaluation.traceComplete && <p className="policy-review-trace-warning">{t('policyReview.traceIncomplete')}</p>}
    {evaluation.trace.length ? <ol className="policy-review-trace">{evaluation.trace.map((entry, index) => <li key={index}>
      <div><strong>{t('policyReview.traceOrdinal', formatCount(index + 1, locale))}</strong><span className="badge" data-tone={entry.selected ? 'purple' : 'neutral'}>
        {t(entry.selected ? 'policyReview.trace.selected' : entry.matched ? 'policyReview.trace.matched' : 'policyReview.trace.notMatched')}</span></div>
      {showDetails && <><p>{t('policyReview.rule', String(entry.policyId))} · {entry.policyName}</p>
        {entry.reasons.length > 0 && <ul>{entry.reasons.map((reason, reasonIndex) => <li key={reasonIndex}>{reason}</li>)}</ul>}</>}
    </li>)}</ol> : <p className="policy-review-help">{t('policyReview.traceEmpty')}</p>}
  </article>;
}

export function DecisionExplanation({ scenario, ordinal, showDetails }: { scenario: PolicyReviewScenario; ordinal: number; showDetails: boolean }) {
  const { locale, t } = useLocale();
  const explanation = scenario.base.decision.action !== scenario.candidate.decision.action
    ? t('policyReview.changeExplanation.action', t(`policyReview.action.${scenario.base.decision.action}`), t(`policyReview.action.${scenario.candidate.decision.action}`))
    : scenario.decisionChanged ? t('policyReview.changeExplanation.fields')
      : scenario.matchedPolicyChanged ? t('policyReview.changeExplanation.policy')
        : t('policyReview.changeExplanation.unchanged');
  return <section className="panel policy-review-explanation">
    <div className="panel-heading"><div><h2>{t('policyReview.explanationTitle')}</h2><p>{t('policyReview.scenario', formatCount(ordinal, locale))}</p></div></div>
    <p className="policy-review-help">{t('policyReview.explanationScope')}</p>
    <h3 className="policy-review-subheading">{t('policyReview.whatChanged')}</h3>
    <p className="policy-review-help">{explanation}</p>
    <div className="policy-review-decision-pair"><Evaluation evaluation={scenario.base} label={t('policyReview.base')} showDetails={showDetails} />
      <Evaluation evaluation={scenario.candidate} label={t('policyReview.candidate')} showDetails={showDetails} /></div>
    <p className="policy-review-help">{t('policyReview.intentHelp')}</p>
    {showDetails && <section className="policy-review-context"><h3>{t('policyReview.contextTitle')}</h3><dl>
      <div><dt>{t('policyReview.context.id')}</dt><dd>{scenario.scenarioId}</dd></div>
      <div><dt>{t('policyReview.context.source')}</dt><dd>{scenario.context.sourceIp}</dd></div>
      <div><dt>{t('policyReview.context.destination')}</dt><dd>{scenario.context.destinationIp}</dd></div>
      <div><dt>{t('policyReview.context.protocol')}</dt><dd>{scenario.context.protocol}</dd></div>
      <div><dt>{t('policyReview.context.port')}</dt><dd>{String(scenario.context.destinationPort)}</dd></div>
      <div><dt>{t('policyReview.context.profile')}</dt><dd>{scenario.context.networkProfile ?? t('policyReview.notProvided')}</dd></div>
      <div><dt>{t('policyReview.context.localTime')}</dt><dd>{scenario.context.localTime ?? t('policyReview.notProvided')}</dd></div>
      <div><dt>{t('policyReview.context.country')}</dt><dd>{scenario.context.sourceCountry ?? t('policyReview.notProvided')}</dd></div>
    </dl></section>}
  </section>;
}
