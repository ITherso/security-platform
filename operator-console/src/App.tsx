import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react';
import { consoleStore as store, type Scenario, type View } from './consoleStore';
import { ProductCards, DeviceDetail, AuditView } from './components/ProductViews';
import { formatDate, formatCount } from './i18n/formatters';
import { renderMessage, type MessageKey } from './i18n';
import { LocaleProvider, LanguageSelect, useLocale } from './i18n/LocaleProvider';
import { toDeviceListViewModel } from './data/viewModels';
import { selectDeviceRows } from './data/deviceRows';
import { ReportPage } from './features/reports/ReportPage';
import { ReportPreview } from './features/reports/ReportPreview';
import { ComparePage } from './features/compare/ComparePage';
import { CompareCaptureActions } from './features/compare/CompareCaptureActions';
import { PolicyReviewPage } from './features/policyReview/PolicyReviewPage';
import { TermivarReviewPage } from './features/termivarReview/TermivarReviewPage';
import './features/reports/print.css';
import './features/compare/compare.css';
export { consoleStore } from './consoleStore';

const TITLES: Record<View, [MessageKey, MessageKey, MessageKey]> = {
  overview: ['app.view.overview.title', 'app.view.overview.subtitle', 'app.nav.overview'],
  devices: ['app.view.devices.title', 'app.view.devices.subtitle', 'app.nav.devices'],
  products: ['app.view.products.title', 'app.view.products.subtitle', 'app.nav.products'],
  audit: ['app.view.audit.title', 'app.view.audit.subtitle', 'app.view.audit.title'],
  reports: ['app.view.reports.title', 'app.view.reports.subtitle', 'app.view.reports.title'],
  compare: ['compare.title', 'compare.subtitle', 'compare.title'],
  policyReview: ['policyReview.title', 'policyReview.subtitle', 'policyReview.nav'],
  termivarReview: ['termivarReview.title', 'termivarReview.subtitle', 'termivarReview.nav']
};
const CONNECTION: Record<string, [MessageKey, string]> = {
  recent: ['app.connection.recent', 'success'], stale: ['app.connection.stale', 'warning'], never_seen: ['app.connection.never', 'neutral']
};
function Icon({ name = 'device' }: { name?: string }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true">{name === 'overview' ? <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>
    : name === 'products' ? <><path d="M12 3 3 7.5 12 12l9-4.5ZM3 12l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5" /></>
    : name === 'compare' ? <><rect x="2" y="4" width="8" height="16" rx="1.5" /><rect x="14" y="4" width="8" height="16" rx="1.5" /><path d="M5 9h2M17 9h2M5 14h2M17 14h2" /></>
    : name === 'audit' || name === 'reports' || name === 'policyReview' || name === 'termivarReview' ? <path d="M9 4h10v17H5V4h2M9 3h6v4H9zM8 12h8M8 16h5" />
    : name === 'refresh' ? <path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1" />
    : name === 'recent' ? <><circle cx="12" cy="12" r="9" /><path d="m7 12 3 3 7-7" /></>
    : name === 'stale' ? <><circle cx="12" cy="12" r="9" /><path d="M12 7v6l4 2" /></>
    : name === 'waiting' ? <path d="m12 3 10 18H2ZM12 8v5M12 17v.1" />
    : <><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8M12 17v4" /></>}</svg>;
}
function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) { return <span className="badge" data-tone={tone}>{children}</span>; }
function Modal({ open, onClose, children, className, label, restorePageFocus = false }: { open: boolean; onClose: () => void; children: ReactNode; className: string; label: string; restorePageFocus?: boolean }) {
  const ref = useRef<HTMLDialogElement>(null);
  const opener = useRef<HTMLElement | null>(null), scroll = useRef({ x: 0, y: 0 });
  useEffect(() => {
    const el = ref.current; if (!el) return;
    if (open && !el.open) {
      if (restorePageFocus) { opener.current = document.activeElement instanceof HTMLElement ? document.activeElement : null; scroll.current = { x: window.scrollX, y: window.scrollY }; }
      el.showModal();
    } else if (!open && el.open) el.close();
  }, [open, restorePageFocus]);
  const closed = () => {
    onClose();
    if (!restorePageFocus) return;
    const original = opener.current;
    const canReturn = original?.isConnected && !original.matches(':disabled');
    const target = canReturn ? original : document.querySelector<HTMLInputElement>('main input[type="search"]') || document.getElementById('main');
    target?.focus({ preventScroll: true });
    if (canReturn) window.scrollTo({ left: scroll.current.x, top: scroll.current.y });
    opener.current = null;
  };
  return <dialog ref={ref} className={className} aria-label={label} onCancel={(event) => { event.preventDefault(); onClose(); }} onClose={closed}>{open && <><div className="modal-locale"><LanguageSelect /></div>{children}</>}</dialog>;
}
function Metrics() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot); const items = s.devices?.items || [];
  const rows: [string, number, string, string, string, string][] = [
    [t('app.metrics.loaded'), items.length, t('app.metrics.loadedNote'), 'device', 'purple', 'all'],
    [t('app.metrics.recent'), items.filter((d) => d.connection_status === 'recent').length, t('app.metrics.recentNote'), 'recent', 'success', 'recent'],
    [t('app.metrics.stale'), items.filter((d) => d.connection_status === 'stale').length, t('app.metrics.staleNote'), 'stale', 'warning', 'stale'],
    [t('app.metrics.never'), items.filter((d) => d.connection_status === 'never_seen').length, t('app.metrics.neverNote'), 'waiting', 'neutral', 'never_seen']
  ];
  return <section className="metrics" aria-label={t('app.metrics.label')}>{rows.map(([label, value, note, icon, tone, filter]) =>
    <button key={filter} className="metric" data-tone={tone} onClick={() => store.navigate('devices', filter)}><span className="metric-top"><span className="metric-label">{label}</span><span className="metric-icon"><Icon name={icon} /></span></span><span className="metric-value">{s.devices ? formatCount(value, locale) : '—'}</span><span className="metric-note">{note}</span></button>)}</section>;
}
function DeviceList() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot), items = s.devices?.items || [];
  const model = s.devices ? toDeviceListViewModel(s.devices) : null;
  const rows = selectDeviceRows(s.devices, s.query, s.filter, s.sort);
  return <section className="panel"><div className="panel-heading"><div><h2>{t('app.nav.devices')}</h2><p>{t('app.devices.subtitle')}</p></div><Badge>{t('app.thisPage')}</Badge></div>
    <div className="list-toolbar"><div className="search-wrap"><input type="search" value={s.query} onChange={(e) => store.setQuery(e.target.value)} placeholder={t('app.search.placeholder')} aria-label={t('app.search.label')} /></div>
      <select className="filter-select" aria-label={t('app.filter.label')} value={s.filter} onChange={(e) => store.setFilter(e.target.value)}>
        <option value="all">{t('app.filter.all')}</option><option value="recent">{t('app.filter.recent')}</option><option value="stale">{t('app.connection.stale')}</option><option value="never_seen">{t('app.connection.never')}</option><option value="revoked">{t('app.filter.revoked')}</option></select>
      <select className="filter-select" aria-label={t('app.sort.label')} value={s.sort} onChange={(e) => store.setSort(e.target.value)}><option value="name">{t('app.sort.name')}</option><option value="received">{t('app.sort.received')}</option></select></div>
    {s.busy || s.loading ? <div className="empty-state" role="status">{t('app.devices.loading')}</div> : !s.devices ? <div className="empty-state">{s.error ? t('app.devices.failed') : t('app.devices.select')}</div>
      : !rows.length ? <div className="empty-state">{items.length ? t('app.devices.noMatch') : t('app.devices.empty')}</div>
        : <div className="table-scroll"><table className="data-table"><thead><tr><th scope="col">{t('app.column.device')}</th><th scope="col">{t('app.column.status')}</th><th scope="col">{t('app.column.received')}</th><th scope="col">{t('app.column.source')}</th><th scope="col"><span className="sr-only">{t('app.detail')}</span></th></tr></thead><tbody>{rows.map((d) => <tr key={d.id}>
          <td><div className="device-cell"><span className="device-symbol"><Icon /></span><div><button className="device-link" onClick={() => void store.openDevice(d.id)}>{d.label}</button><div className="device-sub">{d.id.slice(0, 8).toUpperCase()}</div></div></div></td>
          <td><div className="status-stack"><Badge tone={CONNECTION[d.connection_status]?.[1]}>{t(CONNECTION[d.connection_status]?.[0] || 'display.unknown')}</Badge>{d.identity_status === 'revoked' && <Badge tone="danger">{t('app.filter.revoked')}</Badge>}</div></td>
          <td>{d.last_received_at ? formatDate(d.last_received_at, locale) : t('app.notYet')}{d.last_sequence !== null && <span className="cell-sub">{t('app.sequence', d.last_sequence)}</span>}</td>
          <td>{t('app.claim.device')}<span className="cell-sub">{t('app.claim.notVerified')}</span></td><td><button className="inspect-button" onClick={() => void store.openDevice(d.id)} aria-label={t('app.inspect', d.label)}>↗</button></td></tr>)}</tbody></table></div>}
    <p className="scope-note">{t('app.devices.scope')}</p>
    <div className="list-footer"><span>{s.devices ? t('app.loadedRange', formatCount(s.offset + (items.length ? 1 : 0), locale), formatCount(s.offset + items.length, locale), formatCount(model?.loadedCount ?? items.length, locale), items.length) : t('app.waitingData')}</span><div className="pagination">
      <button className="btn btn-ghost" disabled={s.busy || s.offset === 0} onClick={() => void store.loadDevices(Math.max(0, s.offset - (s.mode === 'demo' ? 5 : 50)))}>{t('app.previous')}</button>
      <button className="btn btn-ghost" disabled={s.busy || s.devices?.next_offset == null || s.devices.next_offset > 10000} onClick={() => void store.loadDevices(s.devices?.next_offset ?? 0)}>{t('app.next')}</button></div></div>
  </section>;
}
function Attention() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot), items = s.devices?.items || [];
  return <section className="panel side-card"><h2>{t('app.attention.title')}</h2><p>{t('app.loadedOnly')}</p><div className="attention-list">{[
    { label: t('app.metrics.stale'), note: t('app.attention.staleNote'), filter: 'stale', tone: 'warning', symbol: '◷', count: items.filter((d) => d.connection_status === 'stale').length },
    { label: t('app.filter.revoked'), note: t('app.attention.revokedNote'), filter: 'revoked', tone: 'danger', symbol: '⊘', count: items.filter((d) => d.identity_status === 'revoked').length },
    { label: t('app.attention.never'), note: t('app.attention.neverNote'), filter: 'never_seen', tone: 'neutral', symbol: '⋯', count: items.filter((d) => d.connection_status === 'never_seen').length }
  ].map((item) => <div className="attention-row" data-tone={item.tone} key={item.filter}><span className="attention-dot">{item.symbol}</span><div><strong>{item.label}</strong><p>{item.note}</p></div><button onClick={() => store.navigate('devices', item.filter)} aria-label={t('app.attention.show', item.label)}>{s.devices ? formatCount(item.count, locale) : '—'} ›</button></div>)}</div>
    <div className="trust-note"><strong>{t('app.trust.title')}</strong><p>{t('app.trust.note')}</p></div></section>;
}
function Catalog() {
  const { locale, t } = useLocale();
  return <section className="panel side-card"><h2>{t('app.nav.products')}</h2><p>{t('app.catalog.subtitle')}</p><div className="catalog-list">{[['◈', 'HostBasedFirewall', t('app.catalog.hbf'), t('app.catalog.reported')], ['⌁', 'Termivar', t('app.catalog.termivar'), t('app.catalog.experimental')], ['◇', t('app.catalog.av'), t('app.catalog.unavailable'), t('app.catalog.planned')]].map(([symbol, name, description, status]) =>
    <div className="catalog-item" key={name}><span className="product-symbol">{symbol}</span><div><strong>{name}</strong><p>{description}</p></div><span className="product-state">{status}</span></div>)}</div></section>;
}
function ConnectionPanel() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot);
  const token = useRef<HTMLInputElement>(null), base = useRef<HTMLInputElement>(null);
  const [scenario, setScenario] = useState<Scenario>('normal');
  const close = () => { if (token.current) token.current.value = ''; store.closeConnection(); };
  return <Modal open={s.connectionOpen} onClose={close} className="connection-dialog" label={t('app.source')}>
    <div className="connection-heading"><div><p className="eyebrow">{t('app.source.heading')}</p><h2>{t('app.source.open')}</h2></div><button className="icon-button" onClick={close} aria-label={t('app.closeWindow')}>×</button></div>
    <p className="muted">{t('app.source.description')}</p>
    <div className="source-option"><span className="source-option-icon">◈</span><div><strong>{t('app.demo.title')}</strong><p>{t('app.demo.notReal')}</p><label className="sr-only" htmlFor="demo-scenario">{t('app.demo.scenario')}</label><select id="demo-scenario" value={scenario} onChange={(e) => setScenario(e.target.value as Scenario)}><option value="normal">{t('app.demo.normal')}</option><option value="empty">{t('app.demo.empty')}</option><option value="error">{t('app.demo.error')}</option></select></div><button className="btn btn-ghost" onClick={() => store.useDemo(scenario)}>{t('app.demo.open')}</button></div>
    <form autoComplete="off" onSubmit={(event) => { event.preventDefault(); const value = token.current?.value || ''; if (token.current) token.current.value = ''; store.connect(base.current?.value || '', value); }}>
      <h3>{t('app.api.heading')}</h3><p className="small muted">{location.protocol === 'https:' ? t('app.api.https') : t('app.api.local')}</p>
      <label htmlFor="api-base">{t('app.api.address')}</label><input ref={base} id="api-base" type="url" defaultValue={`${location.origin}/api/v1`} spellCheck={false} onInput={() => { if (store.snapshot().mode === 'api') store.disconnect(); }} />
      <label htmlFor="access-token">{t('app.api.token')}</label><input ref={token} id="access-token" type="password" autoComplete="off" autoCapitalize="off" spellCheck={false} placeholder={t('app.api.tokenHint')} onInput={() => { if (store.snapshot().mode === 'api') store.disconnect(); }} />
      <p className="field-help">{t('app.api.tokenLifetime')}</p>
      {s.connectionError && <p className="inline-error" role="alert">{renderMessage(locale, s.connectionError)}</p>}
      <div className="connection-actions"><button className="btn btn-ghost" type="button" onClick={() => { store.disconnect(); close(); }}>{t('app.disconnect')}</button><button className="btn btn-primary" type="submit" disabled={location.protocol !== 'https:'}>{t('app.connect')}</button></div>
    </form></Modal>;
}
function CaptureReportActions() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot);
  if (!s.detail || s.detailBusy || s.detailError || !s.detailOpen) return null;
  const selected = s.reportDraft?.records.some((record) => record.deviceId === s.detail?.id) ?? false;
  return <section className="report-capture"><p>{t('app.capture.description')}</p><div className="detail-actions"><button className="btn btn-primary" onClick={() => store.addDetailToReport(selected)}>{selected ? t('app.capture.update') : t('app.capture.add')}</button><button className="btn btn-ghost" onClick={() => store.navigate('reports')}>{t('app.capture.open', formatCount(s.reportDraft?.records.length || 0, locale))}</button></div>{s.reportNotice && <p role="status">{renderMessage(locale, s.reportNotice)}</p>}{s.reportError && <p className="inline-error" role="alert">{renderMessage(locale, s.reportError)}</p>}</section>;
}
function CaptureComparisonActions() {
  const { locale } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot);
  if (!s.detail || s.detailBusy || s.detailError || !s.detailOpen || !s.comparison) return null;
  const slots = s.comparison.slots;
  return <CompareCaptureActions deviceId={s.detail.id} selected={slots.some((device) => device?.deviceId === s.detail?.id)}
    count={slots.filter((device) => device !== null).length} leftLabel={slots[0]?.deviceName ?? null} rightLabel={slots[1]?.deviceName ?? null}
    notice={renderMessage(locale, s.compareNotice)} errorMessage={renderMessage(locale, s.compareError)}
    onAdd={store.addDetailToComparison} onUpdate={store.updateDetailInComparison} onReplace={store.replaceComparisonSide}
    onOpen={() => store.navigate('compare')} />;
}
function DetailNavigator() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot);
  const status = useRef<HTMLParagraphElement>(null);
  const index = s.detailTargetId === null ? -1 : s.detailNavigationIds.indexOf(s.detailTargetId);
  const move = (direction: -1 | 1) => {
    // This node remains mounted while the detail body loads or reports an error.
    status.current?.focus();
    void store.moveDevice(direction);
  };
  return <section className="detail-navigation" aria-label={t('app.detailNav.label')}>
    <div className="detail-navigation-heading"><p ref={status} tabIndex={-1} role="status" aria-atomic="true">{index >= 0 ? t('app.detailNav.position', formatCount(index + 1, locale), formatCount(s.detailNavigationIds.length, locale)) : t('app.detailNav.current')}</p><button type="button" className="btn btn-ghost" onClick={store.closeDevice}>{t('app.close')}</button></div>
    {index >= 0 && <><p className="detail-navigation-scope">{t('app.detailNav.scope')}</p>
    <div className="detail-navigation-actions"><button type="button" className="btn btn-ghost" disabled={s.detailBusy || index === 0} onClick={() => move(-1)}>{t('app.detailNav.previous')}</button><button type="button" className="btn btn-ghost" disabled={s.detailBusy || index >= s.detailNavigationIds.length - 1} onClick={() => move(1)}>{t('app.detailNav.next')}</button></div></>}
  </section>;
}
export function App() {
  const s = useSyncExternalStore(store.subscribe, store.snapshot);
  return <LocaleProvider locale={s.locale} setLocale={store.setLocale}><AppContent /></LocaleProvider>;
}
function AppContent() {
  const { locale, t } = useLocale();
  const s = useSyncExternalStore(store.subscribe, store.snapshot), demo = s.mode === 'demo', localTermivar = s.view === 'termivarReview';
  const localReview = localTermivar || s.view === 'policyReview';
  const localLabel = t(localTermivar ? 'termivarReview.localWorkspace' : 'policyReview.localWorkspace');
  useEffect(() => { window.addEventListener('pagehide', store.pagehide); return () => window.removeEventListener('pagehide', store.pagehide); }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [s.view, s.tenant?.id, s.reportPreview]);
  const [titleKey, subtitleKey, breadcrumbKey] = TITLES[s.view], admin = s.tenant?.role === 'tenant_admin';
  if (s.reportPreview) return <div id="print-root">{s.reportError && <p className="report-controls page-message" role="alert">{renderMessage(locale, s.reportError)}</p>}<ReportPreview report={s.reportPreview} onBack={store.closeReportPreview} onPrint={store.printReport} /></div>;
  return <><a className="skip-link" href="#main">{t('app.skip')}</a><div className="app-shell"><aside className={`sidebar ${s.mobile ? 'open' : ''}`} aria-label={t('app.navigation')}>
    <button className="icon-button mobile-only sidebar-close" aria-label={t('app.menu.close')} onClick={store.toggleMobile}>×</button><a href="#" className="brand" onClick={(e) => { e.preventDefault(); store.navigate('overview'); }}><span className="brand-mark"><svg viewBox="0 0 40 44" aria-hidden="true"><path d="M20 2 36 8v13c0 10-16 20-16 20S4 31 4 21V8Z" /><path d="m12 21 5 5 11-12" /></svg></span><span>{t('app.brand.first')}<span className="brand-second">{t('app.brand.second')}</span></span></a>
    <div className="workspace-picker"><label htmlFor="tenant-select">{t('app.workspace')}</label><div className="select-wrap"><span className="workspace-symbol">◈</span><select id="tenant-select" aria-label={t('app.selectTenant')} disabled={!s.tenants.length || s.loading} value={s.tenant?.id || ''} onChange={(e) => void store.selectTenant(e.target.value)}>{!s.tenant && <option value="">{s.loading ? t('app.loading') : t('app.noTenant')}</option>}{s.tenants.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
      {s.nextTenant !== null && <button className="sidebar-link" disabled={s.loading || s.nextTenant > 10000} onClick={() => void store.moreTenants()}>{t('app.moreTenants')}</button>}</div>
    <p className="nav-caption">{t('app.general')}</p><nav className="nav-list">{(Object.keys(TITLES) as View[]).map((view) => <button key={view} className={`nav-item ${view === s.view ? 'active' : ''}`} aria-current={view === s.view ? 'page' : undefined} disabled={s.loading && view !== 'policyReview' && view !== 'termivarReview'} onClick={() => store.navigate(view)}><Icon name={view} />{view === 'reports' ? t('app.nav.reportCount', formatCount(s.reportDraft?.records.length || 0, locale)) : view === 'compare' ? t('compare.nav', formatCount(s.comparison?.slots.filter((device) => device !== null).length || 0, locale)) : t(TITLES[view][2])}{view === 'audit' && !admin && <span className="nav-lock" aria-label={t('app.adminRequired')}>⌑</span>}</button>)}</nav>
    <div className="sidebar-spacer" /><div className="sidebar-note"><span className="note-icon">↗</span><strong>{t('app.sidebar.title')}</strong><p>{t('app.sidebar.note')}</p><span className="sidebar-tag">{t('app.readOnlyConsole')}</span></div><div className="operator"><span className="avatar">O</span><div><strong>{t('app.operator')}</strong><span>{s.tenant ? t(demo ? admin ? 'app.role.sampleAdmin' : 'app.role.sampleViewer' : admin ? 'app.role.admin' : 'app.role.viewer') : t('app.noTenant')}</span></div></div>
  </aside><div className="workspace"><header className="topbar"><button className="icon-button mobile-only" aria-label={t('app.menu.open')} aria-expanded={s.mobile} onClick={store.toggleMobile}>☰</button><div className="breadcrumb">{t('app.productCenter')} <span>/</span><strong>{t(breadcrumbKey)}</strong></div><div className="topbar-actions"><LanguageSelect /><Badge tone={localReview ? 'neutral' : demo ? 'purple' : s.mode === 'api' ? 'success' : 'neutral'}>{localReview ? localLabel : demo ? t('app.mode.demo') : s.mode === 'api' ? t('app.mode.api') : t('app.mode.closed')}</Badge>{!localReview && <button className="icon-button" aria-label={t('app.source')} onClick={store.openConnection}>⚙</button>}</div></header>
    <main id="main" tabIndex={-1}><div className="mode-banner" data-mode={localReview ? 'local' : demo ? 'demo' : 'api'} role="status"><span className="banner-symbol">{localReview ? '▤' : demo ? '◉' : '◎'}</span><div><strong>{localReview ? localLabel : demo ? t('app.banner.demo') : s.mode === 'api' ? t('app.banner.api') : t('app.banner.none')}</strong><span>{localReview ? t(localTermivar ? 'termivarReview.localNote' : 'policyReview.localNote') : demo ? s.scenario === 'normal' ? t('app.banner.normal') : s.scenario === 'empty' ? t('app.banner.empty') : t('app.banner.error') : t('app.banner.trust')}</span></div>{!localReview && <button className="text-button" onClick={store.openConnection}>{t('app.source.link')}</button>}</div>
      <section className="page-heading"><div><p className="eyebrow">{localReview ? localLabel : s.tenant?.name || t('app.workspaceFallback')}</p><h1>{t(titleKey)}</h1><p>{t(subtitleKey)}</p></div>{!localReview && <div className="heading-actions"><span className="refresh-caption">{s.lastRead && t('app.readAt', formatDate(s.lastRead, locale))}</span><button className="btn btn-primary" disabled={s.loading || s.busy || s.auditStatus === 'loading'} onClick={() => void store.reload()}><Icon name="refresh" />{t('app.refresh')}</button></div>}</section>
      {!localReview && s.error && <div className="page-message" role="alert">{renderMessage(locale, s.error)}</div>}
      {(s.view === 'overview' || s.view === 'devices') && <Metrics />}
      {s.view === 'overview' ? <div className="overview-grid"><DeviceList /><div className="side-stack"><Attention /><Catalog /></div></div> : s.view === 'devices' ? <DeviceList /> : s.view === 'products' ? <><ProductCards /><div className="panel product-page-note"><p>{t('app.productNote')}</p><button className="btn btn-ghost" onClick={() => store.navigate('devices')}>{t('app.goDevices')}</button></div></>
        : s.view === 'termivarReview' ? <TermivarReviewPage key={s.termivarReviewImportId} state={s.termivarReview} onImportFile={store.importTermivarFile} onInvalidSelection={store.rejectTermivarSelection} onImportManifest={store.importTermivarManifest} onInvalidManifestSelection={store.rejectTermivarManifestSelection} onLoadExample={store.loadTermivarExample} onClear={store.clearTermivarReview} onQueryChange={store.setTermivarQuery} onFilterChange={store.setTermivarFilter} onSelectFinding={store.selectTermivarFinding} onShowDetailsChange={store.setTermivarDetails} />
        : s.view === 'policyReview' ? <PolicyReviewPage key={s.policyReviewImportId} state={s.policyReview} onImportFile={store.importPolicyReviewFile} onInvalidSelection={store.rejectPolicyReviewSelection} onLoadExample={store.loadPolicyReviewExample} onClear={store.clearPolicyReview} onQueryChange={store.setPolicyReviewQuery} onFilterChange={store.setPolicyReviewFilter} onSelectScenario={store.selectPolicyReviewScenario} onShowDetailsChange={store.setPolicyReviewDetails} />
        : s.view === 'reports' ? s.reportDraft ? <><ReportPage draft={s.reportDraft} showIdentifiers={s.showIdentifiers} onShowIdentifiersChange={store.setReportIdentifiers} onRemove={store.removeReportRecord} onClear={store.clearReport} onPreview={store.createReportPreview} onBrowseDevices={() => store.navigate('devices')} />{s.reportError && <p className="page-message" role="alert">{renderMessage(locale, s.reportError)}</p>}</> : <section className="panel empty-state"><h2>{t('app.report.selectTenant')}</h2><p>{t('app.report.emptyTenant')}</p></section>
        : s.view === 'compare' ? s.comparison ? <><ComparePage state={s.comparison} onRemove={store.removeCompareDevice} onClear={store.clearComparison} onBrowseDevices={() => store.navigate('devices')} />{s.compareError && <p className="page-message" role="alert">{renderMessage(locale, s.compareError)}</p>}</> : <section className="panel empty-state"><h2>{t('compare.selectTenant')}</h2></section>
        : !admin ? <section className="panel empty-state"><h2>{t('app.audit.adminTitle')}</h2><p>{s.tenant ? t('app.audit.viewerNote') : t('app.audit.selectTenant')}</p></section> : <AuditView page={s.audit} tenantName={s.tenant?.name} status={s.auditStatus} errorMessage={renderMessage(locale, s.auditError)} onNext={(offset) => void store.loadAudit(offset)} onPrev={s.auditOffset > 0 ? () => void store.loadAudit(Math.max(0, s.auditOffset - (demo ? 5 : 50))) : undefined} />}
      <footer className="page-footer"><span><span className="footer-dot" />{t('app.footer.readOnly')}</span><span>{localReview ? t(localTermivar ? 'termivarReview.footer' : 'policyReview.footer') : t('app.footer.trust')}</span></footer>
    </main></div></div>
    <Modal open={s.detailOpen} onClose={store.closeDevice} className="detail-dialog" label={t('app.detail.title')} restorePageFocus><DetailNavigator />{s.detailBusy ? <div className="empty-state" role="status">{t('app.detail.loading')}</div> : s.detailError ? <div className="empty-state"><p role="alert">{renderMessage(locale, s.detailError)}</p></div> : <DeviceDetail detail={s.detail} actions={<><CaptureReportActions /><CaptureComparisonActions /></>} />}</Modal>
    <ConnectionPanel /></>;
}
