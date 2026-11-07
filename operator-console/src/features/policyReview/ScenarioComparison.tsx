import type { PolicyReviewFilter, PolicyReviewState } from './policyReviewModel';
import { filteredPolicyReviewScenarios } from './policyReviewState';
import type { PolicyReviewTextKey } from '../../i18n/catalogs/policyReview';
import { formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

const FILTERS: readonly [PolicyReviewFilter, PolicyReviewTextKey][] = [
  ['all', 'policyReview.filter.all'], ['changed', 'policyReview.filter.changed'],
  ['unchanged', 'policyReview.filter.unchanged'], ['allow_to_deny', 'policyReview.filter.allow_to_deny'],
  ['deny_to_allow', 'policyReview.filter.deny_to_allow'], ['other_changed', 'policyReview.filter.other_changed'],
];
export interface ScenarioComparisonProps {
  state: PolicyReviewState;
  onQueryChange: (query: string) => void;
  onFilterChange: (filter: PolicyReviewFilter) => void;
  onSelectScenario: (scenarioId: string) => void;
}

export function ScenarioComparison({ state, onQueryChange, onFilterChange, onSelectScenario }: ScenarioComparisonProps) {
  const { locale, t } = useLocale();
  const document = state.document;
  const scenarios = filteredPolicyReviewScenarios(state);
  return <section className="panel policy-review-scenarios">
    <div className="panel-heading"><h2>{t('policyReview.scenariosTitle')}</h2></div>
    <div className="policy-review-scenario-tools">
      <label><span>{t('policyReview.search')}</span><input type="search" value={state.query} maxLength={256}
        placeholder={t('policyReview.searchPlaceholder')} onChange={(event) => onQueryChange(event.target.value)} /></label>
      <label><span>{t('policyReview.filter')}</span><select value={state.filter} onChange={(event) => {
        const filter = event.target.value;
        if (FILTERS.some(([value]) => value === filter)) onFilterChange(filter as PolicyReviewFilter);
      }}>{FILTERS.map(([value, label]) => <option key={value} value={value}>{t(label)}</option>)}</select></label>
    </div>
    <p className="policy-review-help">{t(state.showDetails ? 'policyReview.searchDetailsHelp' : 'policyReview.searchHiddenHelp')}</p>
    <p className="policy-review-result-count" role="status">{t('policyReview.visibleScenarios', formatCount(scenarios.length, locale), formatCount(document?.scenarios.length ?? 0, locale))}</p>
    {scenarios.length ? <ul className="policy-review-scenario-list">{scenarios.map((scenario) => {
      const ordinal = (document?.scenarios.findIndex(row => row.scenarioId === scenario.scenarioId) ?? -1) + 1;
      const label = t('policyReview.scenario', String(ordinal));
      return <li key={scenario.scenarioId}><button type="button" className="policy-review-scenario-button"
        aria-pressed={state.selectedScenarioId === scenario.scenarioId} aria-label={t('policyReview.openScenario', label)} onClick={() => onSelectScenario(scenario.scenarioId)}>
        <span className="policy-review-scenario-heading"><strong>{label}</strong><span className="badge" data-tone={scenario.decisionChanged || scenario.matchedPolicyChanged ? 'purple' : 'neutral'}>{t(`policyReview.change.${scenario.changeType}`)}</span></span>
        <span className="policy-review-scenario-decisions"><span><small>{t('policyReview.base')}</small><strong>{t(`policyReview.action.${scenario.base.decision.action}`)}</strong><code>{scenario.base.decision.action}</code></span>
          <span aria-hidden="true" className="policy-review-arrow">→</span><span><small>{t('policyReview.candidate')}</small><strong>{t(`policyReview.action.${scenario.candidate.decision.action}`)}</strong><code>{scenario.candidate.decision.action}</code></span></span>
        {state.showDetails && <span className="policy-review-scenario-source-id">{scenario.scenarioId}</span>}
      </button></li>;
    })}</ul> : <p className="empty-state">{t('policyReview.noMatches')}</p>}
  </section>;
}
