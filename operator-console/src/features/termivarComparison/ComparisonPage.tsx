import { useRef } from 'react';
import type { ComparisonErrorCode, ComparisonFilter, TermivarComparisonState } from './comparisonModel';
import { filteredComparisonRecords } from './comparisonState';
import { ComparisonSummary } from './ComparisonSummary';
import { ComparisonGroups } from './ComparisonGroups';
import { ComparisonItemDetail } from './ComparisonItemDetail';
import type { TermivarComparisonTextKey } from '../../i18n/catalogs/termivarComparison';
import { useLocale } from '../../i18n/LocaleProvider';
import './comparison.css';

export interface ComparisonPageProps {
  state: TermivarComparisonState;
  onImportFile: (file: File) => void;
  onInvalidSelection: () => void;
  onLoadExample: () => void;
  onClear: () => void;
  onQueryChange: (query: string) => void;
  onFilterChange: (filter: ComparisonFilter) => void;
  onSelectItem: (key: string) => void;
  onShowDetailsChange: (show: boolean) => void;
}
const ERROR_KEYS: Readonly<Record<ComparisonErrorCode, TermivarComparisonTextKey>> = {
  file_too_large: 'termivarComparison.error.file_too_large', invalid_utf8: 'termivarComparison.error.invalid_utf8',
  invalid_json: 'termivarComparison.error.invalid_json', unsupported_artifact: 'termivarComparison.error.unsupported_artifact',
  unsupported_version: 'termivarComparison.error.unsupported_version', unsupported_section: 'termivarComparison.error.unsupported_section',
  invalid_comparison: 'termivarComparison.error.invalid_comparison',
};

export function ComparisonPage({ state, onImportFile, onInvalidSelection, onLoadExample, onClear,
  onQueryChange, onFilterChange, onSelectItem, onShowDetailsChange }: ComparisonPageProps) {
  const { t } = useLocale();
  const input = useRef<HTMLInputElement>(null);
  const document = state.status === 'ready' ? state.document : null;
  const visible = filteredComparisonRecords(state);
  const selected = visible.find(record => record.key === state.selectedRecordKey) ?? null;
  const ordinal = document && selected ? document.records.findIndex(record => record.key === selected.key) + 1 : 0;
  return <div className="termivar-comparison-page">
    <section className="panel termivar-comparison-import"><div className="termivar-comparison-import-actions">
      <input ref={input} type="file" accept=".json,application/json" hidden onChange={(event) => {
        const files = event.currentTarget.files, count = files?.length ?? 0;
        const file = count === 1 ? files?.[0] : undefined;
        event.currentTarget.value = '';
        if (count > 1) { onInvalidSelection(); return; }
        if (file) onImportFile(file);
      }} />
      <button type="button" className="btn btn-primary" onClick={() => input.current?.click()}>{t('termivarComparison.openFile')}</button>
      <button type="button" className="btn btn-ghost" onClick={onLoadExample}>{t('termivarComparison.loadExample')}</button>
      <button type="button" className="btn btn-ghost" disabled={state.status === 'empty'} onClick={onClear}>{t('termivarComparison.clear')}</button>
    </div><p className="termivar-comparison-help">{t('termivarComparison.fileHelp')}</p>
      <p className="termivar-comparison-boundary">{t('termivarComparison.boundary')}</p></section>
    {state.status === 'empty' && <section className="panel empty-state"><h2>{t('termivarComparison.emptyTitle')}</h2><p>{t('termivarComparison.emptyDescription')}</p></section>}
    {state.status === 'loading' && <section className="panel empty-state" role="status">{t('termivarComparison.loading')}</section>}
    {state.status === 'error' && <section className="panel empty-state"><p className="termivar-comparison-error" role="alert">{t(state.errorCode === null ? 'termivarComparison.error.invalid_comparison' : ERROR_KEYS[state.errorCode])}</p></section>}
    {document && <>
      {document.source === 'example' && <p className="termivar-comparison-example termivar-comparison-example-banner">{t('termivarComparison.example')}</p>}
      <section className="panel termivar-comparison-presentation"><label><input type="checkbox" checked={state.showDetails} onChange={(event) => onShowDetailsChange(event.target.checked)} /><span>{t('termivarComparison.showDetails')}</span></label>
        <p className="termivar-comparison-help">{t('termivarComparison.detailsHelp')}</p>
        {state.showDetails && <p className="termivar-comparison-sensitive-warning" role="status">{t('termivarComparison.detailsWarning')}</p>}</section>
      <ComparisonSummary document={document} showDetails={state.showDetails} />
      <ComparisonGroups state={state} onQueryChange={onQueryChange} onFilterChange={onFilterChange} onSelectItem={onSelectItem}>
        <ComparisonItemDetail record={selected} ordinal={ordinal} showDetails={state.showDetails} example={document.source === 'example'} />
      </ComparisonGroups>
    </>}
  </div>;
}
