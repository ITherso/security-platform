import type { TermivarReviewFilter, TermivarReviewState } from './termivarModel';
import { filteredTermivarFindings } from './termivarReviewState';
import { formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';

export interface FindingsFiltersProps {
  state: TermivarReviewState;
  onQueryChange: (query: string) => void;
  onFilterChange: (filter: TermivarReviewFilter) => void;
  onShowDetailsChange: (show: boolean) => void;
}
export function FindingsFilters({ state, onQueryChange, onFilterChange, onShowDetailsChange }: FindingsFiltersProps) {
  const { t } = useLocale();
  return <section className="panel termivar-filters">
    <h2>{t('termivarReview.filtersTitle')}</h2>
    <label><span>{t('termivarReview.search')}</span><input type="search" maxLength={256} value={state.query}
      placeholder={t('termivarReview.searchPlaceholder')} onChange={(event) => onQueryChange(event.target.value)} /></label>
    <p className="termivar-help">{t(state.showDetails ? 'termivarReview.searchVisible' : 'termivarReview.searchHidden')}</p>
    <label><span>{t('termivarReview.filter')}</span><select value={state.filter} onChange={(event) => {
      const value = event.target.value;
      if (value === 'all' || value === 'informational' || value === 'needs_review' || value === 'confirmed') onFilterChange(value);
    }}><option value="all">{t('termivarReview.filter.all')}</option>
      {(['informational', 'needs_review', 'confirmed'] as const).map(kind => <option value={kind} key={kind}>{t(`termivarReview.disposition.${kind}`)}</option>)}
    </select></label>
    <label className="termivar-details-control"><input type="checkbox" checked={state.showDetails} onChange={(event) => onShowDetailsChange(event.target.checked)} /><span>{t('termivarReview.showDetails')}</span></label>
    <p className="termivar-help">{t('termivarReview.detailsHelp')}</p>
    {state.showDetails && <p className="termivar-sensitive-warning" role="status">{t('termivarReview.detailsVisible')}</p>}
  </section>;
}

export function FindingsList({ state, onSelectFinding }: { state: TermivarReviewState; onSelectFinding: (key: string) => void }) {
  const { locale, t } = useLocale();
  const document = state.document;
  const findings = filteredTermivarFindings(state);
  return <section className="panel termivar-findings">
    <div className="termivar-panel-heading"><h2>{t('termivarReview.findingsTitle')}</h2></div>
    {document && document.status !== 'complete' ? <p className="termivar-empty-message">{t('termivarReview.incompleteEmpty')}</p>
      : document && document.findings.length === 0 ? <p className="termivar-empty-message">{t('termivarReview.completeEmpty')}</p>
        : <>
          <p className="termivar-result-count" role="status">{t('termivarReview.visibleCount', formatCount(findings.length, locale), formatCount(document?.findings.length ?? 0, locale))}</p>
          {findings.length ? <ul className="termivar-findings-list">{findings.map(finding => {
            const ordinal = (document?.findings.findIndex(item => item.key === finding.key) ?? -1) + 1;
            const label = t('termivarReview.finding', String(ordinal));
            return <li key={finding.key}><button type="button" className="termivar-finding-button" aria-pressed={state.selectedFindingKey === finding.key}
              aria-label={t('termivarReview.openFinding', label)} onClick={() => onSelectFinding(finding.key)}>
              <span className="termivar-finding-heading"><strong>{label}</strong><span className="badge" data-tone={finding.disposition === 'needs_review' ? 'warning' : finding.disposition === 'confirmed' ? 'purple' : 'neutral'}>{t(`termivarReview.disposition.${finding.disposition}`)}</span></span>
              <span className="termivar-finding-codes"><code>{finding.disposition}</code><span>{t(`termivarReview.severity.${finding.severity ?? 'unassigned'}`)}</span><code>{finding.severity ?? 'unassigned'}</code></span>
              <span className="termivar-finding-basis"><code>{finding.claimBasis}</code><span>{t('termivarReview.evidence.total')}: {formatCount(finding.evidenceCount, locale)}</span></span>
              {state.showDetails && <span className="termivar-finding-source-title">{finding.title}</span>}
            </button></li>;
          })}</ul> : <p className="termivar-empty-message">{t('termivarReview.noMatches')}</p>}
        </>}
  </section>;
}
