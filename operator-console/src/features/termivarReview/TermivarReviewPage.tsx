import { useRef } from 'react';
import type { TermivarReviewFilter, TermivarReviewState } from './termivarModel';
import { filteredTermivarFindings } from './termivarReviewState';
import { AssessmentSummary, TermivarReviewErrorMessage } from './AssessmentSummary';
import { FindingsFilters, FindingsList } from './FindingsList';
import { FindingDetail } from './FindingDetail';
import { CoveragePanel } from './CoveragePanel';
import { useLocale } from '../../i18n/LocaleProvider';
import './termivarReview.css';

export interface TermivarReviewPageProps {
  state: TermivarReviewState;
  onImportFile: (file: File) => void;
  onInvalidSelection: () => void;
  onImportManifest: (file: File) => void;
  onInvalidManifestSelection: () => void;
  onLoadExample: (kind: 'complete' | 'incomplete') => void;
  onClear: () => void;
  onQueryChange: (query: string) => void;
  onFilterChange: (filter: TermivarReviewFilter) => void;
  onSelectFinding: (key: string) => void;
  onShowDetailsChange: (show: boolean) => void;
}

export function TermivarReviewPage({ state, onImportFile, onInvalidSelection, onImportManifest, onInvalidManifestSelection,
  onLoadExample, onClear, onQueryChange, onFilterChange, onSelectFinding, onShowDetailsChange }: TermivarReviewPageProps) {
  const { t } = useLocale();
  const assessmentInput = useRef<HTMLInputElement>(null), manifestInput = useRef<HTMLInputElement>(null);
  const document = state.status === 'ready' ? state.document : null;
  const visible = filteredTermivarFindings(state);
  const selected = visible.find(item => item.key === state.selectedFindingKey) ?? null;
  const ordinal = selected && document ? document.findings.findIndex(item => item.key === selected.key) + 1 : 0;
  return <div className="termivar-review-page">
    <section className="panel termivar-import">
      <div className="termivar-import-actions">
        <input ref={assessmentInput} type="file" accept=".json,application/json" hidden onChange={(event) => {
          const files = event.currentTarget.files, count = files?.length ?? 0;
          const file = count === 1 ? files?.[0] : undefined;
          event.currentTarget.value = '';
          if (count > 1) { onInvalidSelection(); return; }
          if (file) onImportFile(file);
        }} />
        <input ref={manifestInput} type="file" accept=".json,application/json" hidden onChange={(event) => {
          const files = event.currentTarget.files, count = files?.length ?? 0;
          const file = count === 1 ? files?.[0] : undefined;
          event.currentTarget.value = '';
          if (count > 1) { onInvalidManifestSelection(); return; }
          if (file) onImportManifest(file);
        }} />
        <button type="button" className="btn btn-primary" onClick={() => assessmentInput.current?.click()}>{t('termivarReview.openFile')}</button>
        <button type="button" className="btn btn-ghost" disabled={document === null || document.status !== 'complete'} onClick={() => manifestInput.current?.click()}>{t('termivarReview.openManifest')}</button>
        <button type="button" className="btn btn-ghost" onClick={() => onLoadExample('complete')}>{t('termivarReview.loadComplete')}</button>
        <button type="button" className="btn btn-ghost" onClick={() => onLoadExample('incomplete')}>{t('termivarReview.loadIncomplete')}</button>
        <button type="button" className="btn btn-ghost" disabled={state.status === 'empty'} onClick={onClear}>{t('termivarReview.clear')}</button>
      </div>
      <p className="termivar-help">{t('termivarReview.fileHelp')} {t('termivarReview.manifestHelp')}</p>
      <p className="termivar-help">{t('termivarReview.manifestCompleteOnly')}</p>
      <p className="termivar-boundary">{t('termivarReview.boundary')}</p>
    </section>
    {state.status === 'empty' && <section className="panel empty-state"><h2>{t('termivarReview.emptyTitle')}</h2><p>{t('termivarReview.emptyDescription')}</p></section>}
    {state.status === 'loading' && <section className="panel empty-state" role="status">{t('termivarReview.loading')}</section>}
    {state.status === 'error' && <section className="panel empty-state"><TermivarReviewErrorMessage code={state.errorCode} /></section>}
    {document && <>
      {document.source === 'example' && <p className="termivar-example termivar-example-banner">{t('termivarReview.example')}</p>}
      <div className="termivar-workspace">
        <aside className="termivar-workspace-summary">
          <AssessmentSummary state={state} />
          <FindingsFilters state={state} onQueryChange={onQueryChange} onFilterChange={onFilterChange} onShowDetailsChange={onShowDetailsChange} />
          <CoveragePanel document={document} />
        </aside>
        <FindingsList state={state} onSelectFinding={onSelectFinding} />
        <FindingDetail finding={selected} ordinal={ordinal} showDetails={state.showDetails} example={document.source === 'example'} incomplete={document.status !== 'complete'} />
      </div>
    </>}
  </div>;
}
