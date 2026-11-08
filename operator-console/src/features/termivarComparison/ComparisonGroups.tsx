import type { ReactNode } from 'react';
import type { ComparisonFilter, ComparisonGroup, TermivarComparisonState } from './comparisonModel';
import { filteredComparisonRecords } from './comparisonState';
import { useLocale } from '../../i18n/LocaleProvider';
import { formatCount } from '../../i18n/formatters';

const GROUPS: readonly ComparisonGroup[] = ['only_in_after', 'only_in_before', 'changed', 'unchanged'];
export interface ComparisonGroupsProps {
  state: TermivarComparisonState;
  onQueryChange: (query: string) => void;
  onFilterChange: (filter: ComparisonFilter) => void;
  onSelectItem: (key: string) => void;
  children?: ReactNode;
}
export function ComparisonGroups({ state, onQueryChange, onFilterChange, onSelectItem, children }: ComparisonGroupsProps) {
  const { locale, t } = useLocale();
  const document = state.document;
  const records = filteredComparisonRecords(state);
  if (!document) return null;
  const ordinals = new Map(document.records.map((record, index) => [record.key, index + 1] as const));
  return <section className="termivar-comparison-groups">
    <div className="termivar-comparison-group-cards">{GROUPS.map(group => <button type="button" className="termivar-comparison-group-card" key={group}
      aria-pressed={state.filter === group} onClick={() => onFilterChange(group)}>
      <span>{t(`termivarComparison.group.${group}`)}</span><strong>{formatCount(document.counts[group], locale)}</strong>
      <code>{group}</code><small>{t(`termivarComparison.groupHelp.${group}`)}</small>
    </button>)}</div>
    <p className="termivar-comparison-help">{t('termivarComparison.countsHelp')}</p>
    <div className="panel termivar-comparison-filter-bar"><label><span>{t('termivarComparison.search')}</span><input type="search" value={state.query} maxLength={256}
      placeholder={t('termivarComparison.searchPlaceholder')} onChange={(event) => onQueryChange(event.target.value)} /></label>
      <label><span>{t('termivarComparison.groupFilter')}</span><select value={state.filter} onChange={(event) => {
        const value = event.target.value;
        if (value === 'all' || GROUPS.some(group => group === value)) onFilterChange(value as ComparisonFilter);
      }}><option value="all">{t('termivarComparison.filter.all')}</option>{GROUPS.map(group => <option value={group} key={group}>{t(`termivarComparison.group.${group}`)}</option>)}</select></label>
      <p className="termivar-comparison-help">{t(state.showDetails ? 'termivarComparison.searchVisible' : 'termivarComparison.searchHidden')}</p>
    </div>
    <div className="termivar-comparison-results">
      <section className="panel termivar-comparison-items"><h2>{t('termivarComparison.itemsTitle')}</h2>
        <p className="termivar-comparison-result-count" role="status">{t('termivarComparison.visibleCount', formatCount(records.length, locale), formatCount(document.records.length, locale))}</p>
        {records.length > 0 ? <ul>{records.map(record => {
          const ordinal = ordinals.get(record.key)!;
          const label = t('termivarComparison.item', String(ordinal));
          return <li key={record.key}><button type="button" className="termivar-comparison-item-button" aria-pressed={state.selectedRecordKey === record.key}
            aria-label={t('termivarComparison.openItem', label)} onClick={() => onSelectItem(record.key)}>
            <span className="termivar-comparison-item-heading"><strong>{label}</strong><span className="badge" data-tone="neutral">{t(`termivarComparison.group.${record.group}`)}</span></span>
            <code className="termivar-comparison-group-code">{record.group}</code>
            <span className="termivar-comparison-item-preview">
              {record.before && <span><small>{t('termivarComparison.before')}</small><span>{t(`termivarReview.disposition.${record.before.disposition}`)}</span><code>{record.before.disposition} · {record.before.severity ?? 'unassigned'}</code></span>}
              {record.after && <span><small>{t('termivarComparison.after')}</small><span>{t(`termivarReview.disposition.${record.after.disposition}`)}</span><code>{record.after.disposition} · {record.after.severity ?? 'unassigned'}</code></span>}
            </span>
            {state.showDetails && <span className="termivar-comparison-source-title">{record.after?.title ?? record.before?.title}</span>}
          </button></li>;
        })}</ul> : <p className="termivar-comparison-empty">{t(document.records.length === 0 ? 'termivarComparison.noItems' : 'termivarComparison.noMatches')}</p>}
      </section>
      {children}
    </div>
  </section>;
}
