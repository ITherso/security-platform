import { useRef } from 'react';
import type { PolicyReviewErrorCode, PolicyReviewFilter, PolicyReviewState } from './policyReviewModel';
import { filteredPolicyReviewScenarios } from './policyReviewState';
import { PolicySummary } from './PolicySummary';
import { ScenarioComparison } from './ScenarioComparison';
import { DecisionExplanation } from './DecisionExplanation';
import { PreconditionPanel } from './PreconditionPanel';
import type { PolicyReviewTextKey } from '../../i18n/catalogs/policyReview';
import { useLocale } from '../../i18n/LocaleProvider';
import './policyReview.css';

export interface PolicyReviewPageProps {
  state: PolicyReviewState;
  onImportFile: (file: File) => void;
  onInvalidSelection: () => void;
  onLoadExample: (kind: 'comparison' | 'blocked') => void;
  onClear: () => void;
  onQueryChange: (query: string) => void;
  onFilterChange: (filter: PolicyReviewFilter) => void;
  onSelectScenario: (scenarioId: string) => void;
  onShowDetailsChange: (show: boolean) => void;
}
const ERROR_KEYS: Readonly<Record<PolicyReviewErrorCode, PolicyReviewTextKey>> = {
  file_too_large: 'policyReview.error.file_too_large', invalid_utf8: 'policyReview.error.invalid_utf8',
  invalid_json: 'policyReview.error.invalid_json', unsupported_artifact: 'policyReview.error.unsupported_artifact',
  unsupported_version: 'policyReview.error.unsupported_version', invalid_artifact: 'policyReview.error.invalid_artifact',
  reader_unavailable: 'policyReview.error.reader_unavailable',
};

/** File reads and their race/context guards remain in the existing caller. */
export function PolicyReviewPage({ state, onImportFile, onInvalidSelection, onLoadExample, onClear, onQueryChange,
  onFilterChange, onSelectScenario, onShowDetailsChange }: PolicyReviewPageProps) {
  const { t } = useLocale();
  const fileInput = useRef<HTMLInputElement>(null);
  const document = state.status === 'ready' ? state.document : null;
  const visible = filteredPolicyReviewScenarios(state);
  const selected = visible.find(row => row.scenarioId === state.selectedScenarioId) ?? null;
  const ordinal = selected && document ? document.scenarios.findIndex(row => row.scenarioId === selected.scenarioId) + 1 : 0;
  return <div className="policy-review-page">
    <section className="panel policy-review-import">
      <div className="policy-review-import-actions">
        <input ref={fileInput} type="file" accept=".json,application/json" hidden onChange={(event) => {
          const files = event.currentTarget.files;
          const count = files?.length ?? 0;
          const file = count === 1 ? files?.[0] : undefined;
          event.currentTarget.value = '';
          if (count > 1) { onInvalidSelection(); return; }
          if (file) onImportFile(file);
        }} />
        <button type="button" className="btn btn-primary" onClick={() => fileInput.current?.click()}>{t('policyReview.openFile')}</button>
        <button type="button" className="btn btn-ghost" onClick={() => onLoadExample('comparison')}>{t('policyReview.loadExample')}</button>
        <button type="button" className="btn btn-ghost" onClick={() => onLoadExample('blocked')}>{t('policyReview.loadBlockedExample')}</button>
        <button type="button" className="btn btn-ghost" disabled={state.status === 'empty'} onClick={onClear}>{t('policyReview.clear')}</button>
      </div>
      <p className="policy-review-help">{t('policyReview.importHelp')}</p>
      <p className="policy-review-boundary">{t('policyReview.boundary')}</p>
    </section>
    {state.status === 'loading' && <section className="panel empty-state" role="status">{t('policyReview.loading')}</section>}
    {state.status === 'error' && <section className="panel empty-state policy-review-import-error" role="alert">
      <p>{t(state.errorCode !== null ? ERROR_KEYS[state.errorCode] : 'policyReview.error.invalid_artifact')}</p>
    </section>}
    {state.status === 'empty' && <section className="panel empty-state"><h2>{t('policyReview.emptyTitle')}</h2><p>{t('policyReview.emptyDescription')}</p></section>}
    {document && <>
      <PolicySummary document={document} />
      <section className="panel policy-review-presentation">
        <label><input type="checkbox" checked={state.showDetails} onChange={(event) => onShowDetailsChange(event.target.checked)} /><span>{t('policyReview.showDetails')}</span></label>
        <p className="policy-review-help">{t('policyReview.detailsHelp')}</p>
        {state.showDetails && <p className="policy-review-details-warning" role="status">{t('policyReview.detailsVisible')}</p>}
        <p className="policy-review-help">{t('policyReview.notVerified')}</p>
      </section>
      {document.scenarios.length > 0 && <>
        <ScenarioComparison state={state} onQueryChange={onQueryChange} onFilterChange={onFilterChange} onSelectScenario={onSelectScenario} />
        {selected ? <DecisionExplanation scenario={selected} ordinal={ordinal} showDetails={state.showDetails} />
          : <p className="panel empty-state">{t('policyReview.selectScenario')}</p>}
      </>}
      <PreconditionPanel document={document} />
    </>}
  </div>;
}
