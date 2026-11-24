import { createDemoClient } from './adapters/fixtures';
import { createApiClient } from './adapters/platformReadOnly';
import type { DataClient, Tenant, DevicePage, AuditPage, DeviceDetail, AlertOptions, AlertStatus, TimelineOptions } from './data/contracts';
import { selectDeviceRows } from './data/deviceRows';
import { isAlertStatus } from './data/normalize';
import { appendAlerts, appendTimeline, ALERT_DEVICE_PAGE, MAX_LOADED_ALERTS, MAX_TIMELINE_EVENTS } from './features/events/eventsModel';
import type { AlertListView, LoadStatus, TimelineView } from './features/events/eventsModel';
import type { ReportContext, ReportDraft, ReportModel } from './features/reports/reportModel';
import { captureRecord } from './features/reports/capture';
import { createDraft, addRecord, updateRecord, removeRecord, clearDraft, buildPreview } from './features/reports/reportDraft';
import type { CompareState } from './features/compare/compareModel';
import { captureComparableDevice } from './features/compare/capture';
import { createCompareState, addComparableDevice, updateComparableDevice, replaceSlot, removeComparableDevice, clearCompareState } from './features/compare/compareState';
import { MAX_POLICY_REVIEW_BYTES, POLICY_REVIEW_ERROR_CODES } from './features/policyReview/policyReviewModel';
import type { PolicyReviewState, PolicyReviewErrorCode, PolicyReviewFilter } from './features/policyReview/policyReviewModel';
import { createPolicyReviewState, beginPolicyReviewImport, completePolicyReviewImport, failPolicyReviewImport,
  clearPolicyReview as clearPolicyReviewState, setPolicyReviewQuery, setPolicyReviewFilter, selectPolicyReviewScenario,
  setPolicyReviewDetails } from './features/policyReview/policyReviewState';
import { MAX_TERMIVAR_REVIEW_BYTES, MAX_TERMIVAR_MANIFEST_BYTES, TERMIVAR_REVIEW_ERROR_CODES } from './features/termivarReview/termivarModel';
import type { AssessmentDocument, TermivarReviewState, TermivarReviewErrorCode, TermivarReviewFilter } from './features/termivarReview/termivarModel';
import { createTermivarReviewState, beginTermivarImport, completeTermivarImport, failTermivarImport,
  clearTermivarReview as clearTermivarReviewState, beginTermivarManifestImport, completeTermivarManifestImport,
  failTermivarManifestImport, setTermivarDetails, setTermivarQuery, setTermivarFilter, selectTermivarFinding } from './features/termivarReview/termivarReviewState';
import { MAX_COMPARISON_REVIEW_BYTES, COMPARISON_ERROR_CODES } from './features/termivarComparison/comparisonModel';
import type { TermivarComparisonState, ComparisonErrorCode, ComparisonFilter } from './features/termivarComparison/comparisonModel';
import { createComparisonState as createTermivarComparisonState, beginComparisonImport, completeComparisonImport, failComparisonImport,
  clearComparisonReview, setComparisonQuery, setComparisonFilter, selectComparisonRecord, setComparisonDetails } from './features/termivarComparison/comparisonState';
import type { GuideFlow, GuideState } from './features/productHub/guideModel';
import { createGuideState, currentGuideStep, moveGuideStep } from './features/productHub/guideState';

import { message, type UiMessage, type Locale } from './i18n';

export type View = 'productHub' | 'overview' | 'devices' | 'alerts' | 'products' | 'audit' | 'reports' | 'compare' | 'policyReview' | 'termivarReview' | 'termivarComparison';
export type Scenario = 'normal' | 'empty' | 'error';
const EMPTY_DEVICE_IDS: readonly string[] = Object.freeze([]);
const DEVICE_ID_TEXT = /^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/;
type Mutable<T> = { -readonly [K in keyof T]: T[K] };
interface DetailNavigationContext { readonly epoch: number; readonly tenantId: string; readonly generation: number }
const ERRORS: Readonly<Record<string, UiMessage>> = {
  unauthorized: message('app.error.unauthorized'),
  forbidden: message('app.error.forbidden'),
  not_found: message('app.error.not_found'),
  rate_limited: message('app.error.rate_limited'),
  offline: message('app.error.offline'),
  timeout: message('app.error.timeout'),
  malformed: message('app.error.malformed'),
  disconnected: message('app.error.disconnected'),
  https_required: message('app.error.https_required'),
  invalid_input: message('app.error.invalid_input'),
  server_error: message('app.error.server_error'),
};
function code(error: unknown): string {
  return error && typeof error === 'object' && 'code' in error && typeof error.code === 'string' ? error.code : '';
}
async function reviewModule<T>(operation: Promise<T>): Promise<T> {
  try { return await operation; }
  catch { throw { code: 'reader_unavailable' }; }
}
export function errorMessage(error: unknown): UiMessage {
  const key = code(error);
  if (Object.hasOwn(ERRORS, key)) return ERRORS[key];
  return message('app.error.generic');
}
interface State {
  locale: Locale; mode: 'demo' | 'api' | 'disconnected'; scenario: Scenario; view: View; mobile: boolean;
  tenants: readonly Tenant[]; nextTenant: number | null; tenant: Tenant | null;
  devices: DevicePage | null; offset: number; busy: boolean; loading: boolean;
  audit: AuditPage | null; auditOffset: number; auditStatus: 'idle' | 'loading' | 'ready' | 'error'; auditError: UiMessage | null;
  query: string; filter: string; sort: string; error: UiMessage | null; lastRead: string;
  detailOpen: boolean; detail: DeviceDetail | null; detailError: UiMessage | null; detailBusy: boolean;
  detailTargetId: string | null; detailNavigationIds: readonly string[];
  connectionOpen: boolean; connectionError: UiMessage | null;
  detailReadAt: string; reportDraft: ReportDraft | null; reportPreview: ReportModel | null;
  previewRevision: number | null; showIdentifiers: boolean; reportError: UiMessage | null; reportNotice: UiMessage | null;
  comparison: CompareState | null; compareError: UiMessage | null; compareNotice: UiMessage | null;
  policyReview: PolicyReviewState; policyReviewImportId: number;
  termivarReview: TermivarReviewState; termivarReviewImportId: number;
  termivarComparison: TermivarComparisonState; termivarComparisonImportId: number;
  guide: GuideState | null;
  timeline: TimelineView | null; timelineStatus: LoadStatus; timelineOlder: boolean; timelineError: UiMessage | null;
  alerts: AlertListView | null; alertsStatus: LoadStatus; alertsOlder: boolean; alertsError: UiMessage | null;
  alertStatusFilter: AlertStatus | 'all'; alertDeviceFilter: string | null; alertDevices: DevicePage | null;
  alertDevicesError: UiMessage | null;
}
/** The open detail's timeline; it never outlives that detail, tenant or session. */
const TIMELINE_CLEARED: Pick<State, 'timeline' | 'timelineStatus' | 'timelineOlder' | 'timelineError'> = {
  timeline: null, timelineStatus: 'idle', timelineOlder: false, timelineError: null };
const ALERTS_CLEARED: Pick<State, 'alerts' | 'alertsStatus' | 'alertsOlder' | 'alertsError' | 'alertDevices' | 'alertDevicesError'> = {
  alerts: null, alertsStatus: 'idle', alertsOlder: false, alertsError: null, alertDevices: null, alertDevicesError: null };
/** Device ids are tenant data: a tenant, session or source change starts from no filter. */
const ALERT_FILTERS_DEFAULT: Pick<State, 'alertStatusFilter' | 'alertDeviceFilter'> = { alertStatusFilter: 'all', alertDeviceFilter: null };
class ConsoleStore {
  private client: DataClient | null = createDemoClient();
  private epoch = 0;
  private scope = new AbortController();
  private detailRequest = new AbortController();
  private detailSequence = 0;
  private detailNavigationContext: DetailNavigationContext | null = null;
  private timelineRequest = new AbortController();
  private timelineSequence = 0;
  private contextGeneration = 1;
  private policyReviewReadSequence = 0;
  private termivarReadSequence = 0;
  private termivarManifestReadSequence = 0;
  private termivarComparisonReadSequence = 0;
  private guideGeneration: number | null = null;
  private listeners = new Set<() => void>();
  private state: State = { locale: 'tr', mode: 'demo', scenario: 'normal', view: 'productHub', mobile: false,
    tenants: [], nextTenant: null, tenant: null, devices: null, offset: 0, busy: false, loading: true,
    audit: null, auditOffset: 0, auditStatus: 'idle', auditError: null, query: '', filter: 'all', sort: 'name',
    error: null, lastRead: '', detailOpen: false, detail: null, detailBusy: false, detailError: null, connectionOpen: false, connectionError: null,
    detailTargetId: null, detailNavigationIds: EMPTY_DEVICE_IDS,
    detailReadAt: '', reportDraft: null, reportPreview: null, previewRevision: null, showIdentifiers: false, reportError: null, reportNotice: null,
    comparison: null, compareError: null, compareNotice: null, policyReview: createPolicyReviewState(), policyReviewImportId: 0,
    termivarReview: createTermivarReviewState(), termivarReviewImportId: 0,
    termivarComparison: createTermivarComparisonState(), termivarComparisonImportId: 0, guide: null,
    ...TIMELINE_CLEARED, ...ALERTS_CLEARED, ...ALERT_FILTERS_DEFAULT };
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private emit(patch: Partial<State> = {}) { this.state = { ...this.state, ...patch }; this.listeners.forEach((fn) => fn()); }
  private reset() {
    ++this.epoch; ++this.detailSequence; this.scope.abort(); this.detailRequest.abort(); this.cancelTimeline();
    this.detailNavigationContext = null;
    this.scope = new AbortController(); this.detailRequest = new AbortController();
    this.emit({ devices: null, audit: null, auditStatus: 'idle', auditError: null, error: null, lastRead: '',
      detail: null, detailOpen: false, detailError: null, detailBusy: false, detailReadAt: '',
      detailTargetId: null, detailNavigationIds: EMPTY_DEVICE_IDS, loading: false, busy: false, compareError: null, compareNotice: null,
      ...TIMELINE_CLEARED, ...ALERTS_CLEARED });
  }
  /** Aborts the timeline read in flight; its late answer fails the sequence check. */
  private cancelTimeline() {
    ++this.timelineSequence; this.timelineRequest.abort(); this.timelineRequest = new AbortController();
  }
  private clearReportContext() {
    this.guideGeneration = null;
    ++this.contextGeneration;
    this.emit({ guide: null, reportDraft: null, reportPreview: null, previewRevision: null, showIdentifiers: false, reportError: null, reportNotice: null,
      comparison: null, compareError: null, compareNotice: null, ...this.resetPolicyReviewPatch(), ...this.resetTermivarReviewPatch(), ...this.resetTermivarComparisonPatch() });
  }
  private bindReportContext(tenant: Tenant | null) {
    if (!tenant || !this.client || this.state.mode === 'disconnected') { this.clearReportContext(); return; }
    const draft = this.state.reportDraft;
    const comparison = this.state.comparison;
    const context = { tenantId: tenant.id, mode: this.state.mode === 'demo' ? 'example' as const : 'api' as const, generation: this.contextGeneration };
    if ([draft?.context, comparison?.context].some((value) => value && (value.tenantId !== context.tenantId || value.mode !== context.mode || value.generation !== context.generation))) this.clearReportContext();
    if (!this.state.reportDraft) {
      const context: ReportContext = { tenantId: tenant.id, mode: this.state.mode === 'demo' ? 'example' : 'api', generation: this.contextGeneration };
      this.emit({ reportDraft: createDraft(context) });
    }
    if (!this.state.comparison) this.emit({ comparison: createCompareState({ tenantId: tenant.id, mode: this.state.mode === 'demo' ? 'example' : 'api', generation: this.contextGeneration }) });
  }
  private reportFailure(error: unknown) {
    const messages: Readonly<Record<string, UiMessage>> = {
      duplicate_record: message('app.reportError.duplicate_record'), record_limit: message('app.reportError.record_limit'),
      size_limit: message('app.reportError.size_limit'), context_mismatch: message('app.reportError.context_mismatch'),
      record_not_found: message('app.reportError.record_not_found'), empty_report: message('app.reportError.empty_report')
    };
    const key = code(error);
    this.emit({ reportError: Object.hasOwn(messages, key) ? messages[key] : message('app.reportError.generic'), reportNotice: null });
  }

  private current(epoch: number, client: DataClient) { return epoch === this.epoch && client === this.client; }
  private limit() { return this.state.mode === 'demo' ? 5 : 50; }
  private readTime() { return new Date().toISOString(); }
  private fail(error: unknown, epoch: number, client: DataClient) {
    if (!this.current(epoch, client) || code(error) === 'aborted') return;
    const failureMessage: UiMessage = { ...errorMessage(error), sample: this.state.mode === 'demo' };
    if (code(error) === 'forbidden' || code(error) === 'not_found') this.clearReportContext();
    if (code(error) === 'unauthorized') {
      this.disconnect(); this.emit({ error: failureMessage }); return;
    }
    ++this.detailSequence; this.detailRequest.abort(); this.detailNavigationContext = null; this.cancelTimeline();
    this.emit({ devices: null, audit: null, detail: null, detailOpen: false, detailBusy: false, detailReadAt: '',
      detailTargetId: null, detailNavigationIds: EMPTY_DEVICE_IDS, busy: false, loading: false,
      auditStatus: 'error', auditError: failureMessage, error: failureMessage,
      ...TIMELINE_CLEARED, ...ALERTS_CLEARED, alertsStatus: 'error', alertsError: failureMessage });
  }
  reload = async () => {
    if (!this.client) { this.openConnection(); return; }
    this.closeGuide();
    this.clearPolicyReview();
    this.clearTermivarReview();
    this.clearTermivarComparison();
    const previous = this.state.tenant?.id;
    this.reset(); this.emit({ loading: true, tenants: [], tenant: null, nextTenant: null });
    const client = this.client, epoch = this.epoch;
    try {
      const page = await client.listTenants({ offset: 0, limit: 50, signal: this.scope.signal });
      if (!this.current(epoch, client)) return;
      const tenant = previous ? page.items.find((item) => item.id === previous) || null : page.items[0] || null;
      this.bindReportContext(tenant);
      // A refresh keeps the alert filters only for the same tenant.
      this.emit({ tenants: page.items, nextTenant: page.next_offset, tenant, loading: false, lastRead: this.readTime(),
        ...(tenant !== null && tenant.id === previous ? {} : ALERT_FILTERS_DEFAULT) });
      if (tenant) await this.loadView();
      else if (previous) this.emit({ error: message('app.error.previousTenant') });
    } catch (error) { this.fail(error, epoch, client); }
  };
  moreTenants = async () => {
    const { nextTenant } = this.state; if (!this.client || nextTenant === null || nextTenant > 10000 || this.state.loading) return;
    const client = this.client, epoch = this.epoch; this.emit({ loading: true });
    try {
      const page = await client.listTenants({ offset: nextTenant, limit: 50, signal: this.scope.signal });
      if (!this.current(epoch, client)) return;
      const existing = new Set(this.state.tenants.map((item) => item.id));
      this.emit({ tenants: [...this.state.tenants, ...page.items.filter((item) => !existing.has(item.id))], nextTenant: page.next_offset, loading: false, lastRead: this.readTime() });
    } catch (error) { this.fail(error, epoch, client); }
  };
  selectTenant = async (id: string) => {
    const tenant = this.state.tenants.find((item) => item.id === id); if (!tenant) return;
    if (id !== this.state.tenant?.id) { this.closeGuide(); this.clearPolicyReview(); this.clearTermivarReview(); this.clearTermivarComparison(); }
    this.bindReportContext(tenant);
    this.reset(); this.emit({ tenant, query: '', filter: 'all', offset: 0, ...ALERT_FILTERS_DEFAULT }); await this.loadView();
  };
  private loadView = async () => {
    if (this.state.view === 'audit') await this.loadAudit(0);
    else if (this.state.view === 'alerts') await this.loadAlerts();
    else if (this.state.view === 'overview' || this.state.view === 'devices') await this.loadDevices(0);
  };
  navigate = (view: View, filter = 'all') => {
    if (this.state.loading && view !== 'productHub' && view !== 'policyReview' && view !== 'termivarReview' && view !== 'termivarComparison') return;
    this.reset(); this.emit({ view, filter, query: '', offset: 0, mobile: false, reportPreview: null, previewRevision: null, ...ALERT_FILTERS_DEFAULT }); void this.loadView();
  };
  loadDevices = async (offset = 0) => {
    if (!this.client || !this.state.tenant || !Number.isInteger(offset) || offset < 0 || offset > 10000) return;
    this.reset(); this.emit({ busy: true, offset });
    const client = this.client, epoch = this.epoch, tenant = this.state.tenant.id;
    try {
      const page = await client.listDevices(tenant, { offset, limit: this.limit(), signal: this.scope.signal });
      if (!this.current(epoch, client)) return;
      this.bindReportContext(this.state.tenant);
      this.emit({ devices: page, busy: false, lastRead: this.readTime() });
    } catch (error) { this.fail(error, epoch, client); }
  };
  loadAudit = async (offset = 0) => {
    if (!this.client || !this.state.tenant || this.state.tenant.role !== 'tenant_admin' || !Number.isInteger(offset) || offset < 0 || offset > 10000) return;
    this.reset(); this.emit({ auditOffset: offset, auditStatus: 'loading' });
    const client = this.client, epoch = this.epoch, tenant = this.state.tenant.id;
    try {
      const page = await client.listAudit(tenant, { offset, limit: this.limit(), signal: this.scope.signal });
      if (!this.current(epoch, client)) return;
      this.emit({ audit: page, auditStatus: 'ready', lastRead: this.readTime() });
    } catch (error) { this.fail(error, epoch, client); }
  };
  openDevice = async (id: string) => {
    if (!this.client || !this.state.tenant) return;
    if (this.state.detailOpen && this.state.detailTargetId === id) return;
    const ids = this.state.busy || this.state.loading ? []
      : selectDeviceRows(this.state.devices, this.state.query, this.state.filter, this.state.sort).map((device) => device.id);
    const hasNavigation = ids.includes(id);
    this.detailNavigationContext = hasNavigation
      ? { epoch: this.epoch, tenantId: this.state.tenant.id, generation: this.contextGeneration } : null;
    this.emit({ detailNavigationIds: hasNavigation ? Object.freeze(ids) : EMPTY_DEVICE_IDS });
    await this.requestDevice(id);
  };
  private navigationCurrent() {
    const context = this.detailNavigationContext;
    if (!context || !this.client || context.epoch !== this.epoch || context.tenantId !== this.state.tenant?.id
      || context.generation !== this.contextGeneration || this.state.loading || this.state.busy) return false;
    const visible = selectDeviceRows(this.state.devices, this.state.query, this.state.filter, this.state.sort);
    return visible.length === this.state.detailNavigationIds.length
      && visible.every((device, index) => device.id === this.state.detailNavigationIds[index]);
  }
  private detailCurrent(epoch: number, client: DataClient, sequence: number, generation: number, tenantId: string, id: string) {
    return this.current(epoch, client) && sequence === this.detailSequence && generation === this.contextGeneration
      && tenantId === this.state.tenant?.id && this.state.detailOpen && this.state.detailTargetId === id
      && (this.detailNavigationContext === null || this.navigationCurrent());
  }
  moveDevice = async (direction: -1 | 1) => {
    if ((direction !== -1 && direction !== 1) || !this.state.detailOpen || !this.state.detailTargetId || this.detailNavigationContext === null) return;
    if (!this.navigationCurrent()) { this.closeDevice(); return; }
    const index = this.state.detailNavigationIds.indexOf(this.state.detailTargetId);
    if (index < 0) return;
    const id = this.state.detailNavigationIds[index + direction];
    if (id === undefined) return; // No wrap, page traversal or automatic skip.
    await this.requestDevice(id);
  };
  private requestDevice = async (id: string) => {
    if (!this.client || !this.state.tenant) return;
    if (this.detailNavigationContext !== null && (!this.navigationCurrent() || !this.state.detailNavigationIds.includes(id))) return;
    this.detailRequest.abort(); this.detailRequest = new AbortController(); this.cancelTimeline();
    const client = this.client, epoch = this.epoch, sequence = ++this.detailSequence, tenant = this.state.tenant.id, reportGeneration = this.contextGeneration;
    this.emit({ detail: null, detailOpen: true, detailBusy: true, detailError: null, detailReadAt: '',
      detailTargetId: id, reportError: null, reportNotice: null, compareError: null, compareNotice: null, ...TIMELINE_CLEARED });
    try {
      const detail = await client.getDevice(tenant, id, { signal: this.detailRequest.signal });
      if (!this.detailCurrent(epoch, client, sequence, reportGeneration, tenant, id)) return;
      this.bindReportContext(this.state.tenant);
      this.emit({ detail, detailBusy: false, detailReadAt: this.readTime() });
      // The timeline is a separate GET of the device just shown; its failure never hides the detail.
      void this.loadTimeline();
    } catch (error) {
      if (!this.detailCurrent(epoch, client, sequence, reportGeneration, tenant, id) || code(error) === 'aborted') return;
      const accessLost = code(error) === 'forbidden' || code(error) === 'not_found';
      if (accessLost) { this.clearReportContext(); this.detailNavigationContext = null; }
      if (code(error) === 'unauthorized') this.fail(error, epoch, client);
      else this.emit({ detail: null, detailBusy: false, detailError: errorMessage(error),
        ...(accessLost ? { detailTargetId: null, detailNavigationIds: EMPTY_DEVICE_IDS } : {}) });
    }
  };
  closeDevice = () => {
    ++this.detailSequence; this.detailRequest.abort(); this.detailNavigationContext = null; this.cancelTimeline();
    this.emit({ detailOpen: false, detail: null, detailError: null, detailBusy: false, detailReadAt: '',
      detailTargetId: null, detailNavigationIds: EMPTY_DEVICE_IDS, ...TIMELINE_CLEARED });
  };
  private timelineLimit() { return this.state.mode === 'demo' ? 10 : 50; }
  private timelineCurrent(epoch: number, client: DataClient, sequence: number, tenantId: string, deviceId: string) {
    return this.current(epoch, client) && sequence === this.timelineSequence && tenantId === this.state.tenant?.id
      && this.state.detailOpen && this.state.detail?.id === deviceId && this.state.detailTargetId === deviceId;
  }
  /** First page of the open device's events, or (older) the next page below the last loaded sequence. */
  loadTimeline = async (older = false) => {
    const { detail, tenant } = this.state;
    if (!this.client || !tenant || !detail || !this.state.detailOpen || this.state.detailBusy || this.state.detailError !== null
      || detail.tenant_id !== tenant.id || detail.id !== this.state.detailTargetId) return;
    const current = this.state.timeline !== null && this.state.timeline.deviceId === detail.id ? this.state.timeline : null;
    if (older && (current === null || current.nextBeforeSeq === null || this.state.timelineStatus !== 'ready'
      || this.state.timelineOlder || current.events.length >= MAX_TIMELINE_EVENTS)) return;
    this.cancelTimeline();
    const client = this.client, epoch = this.epoch, sequence = this.timelineSequence, tenantId = tenant.id, deviceId = detail.id;
    const signal = this.timelineRequest.signal;
    const beforeSeq = older && current !== null ? current.nextBeforeSeq : null;
    const limit = older && current !== null ? Math.min(this.timelineLimit(), MAX_TIMELINE_EVENTS - current.events.length) : this.timelineLimit();
    const request: TimelineOptions = beforeSeq === null ? { limit, signal } : { limit, signal, beforeSeq };
    this.emit(older ? { timelineOlder: true, timelineError: null }
      : { timeline: null, timelineStatus: 'loading', timelineOlder: false, timelineError: null });
    try {
      const page = await client.listDeviceEvents(tenantId, deviceId, request);
      if (!this.timelineCurrent(epoch, client, sequence, tenantId, deviceId)) return;
      const base = older ? this.state.timeline : null;
      if (older && (base === null || base.deviceId !== deviceId)) return;
      this.emit({ timeline: appendTimeline(base, page, deviceId, this.readTime()), timelineStatus: 'ready', timelineOlder: false, timelineError: null });
    } catch (error) {
      if (!this.timelineCurrent(epoch, client, sequence, tenantId, deviceId) || code(error) === 'aborted') return;
      if (code(error) === 'unauthorized') { this.fail(error, epoch, client); return; }
      const failure: UiMessage = { ...errorMessage(error), sample: this.state.mode === 'demo' };
      // An older page that fails keeps the loaded events; lost access clears the timeline.
      const keep = older && code(error) !== 'forbidden' && code(error) !== 'not_found';
      this.emit(keep ? { timelineOlder: false, timelineError: failure }
        : { timeline: null, timelineStatus: 'error', timelineOlder: false, timelineError: failure });
    }
  };
  /** Leaves the open detail for the alert list filtered to this device. */
  showDeviceAlerts = (deviceId: string) => {
    const { detail, tenant } = this.state;
    if (!this.client || !tenant || this.state.loading || !detail || detail.id !== deviceId || detail.tenant_id !== tenant.id) return;
    this.reset();
    this.emit({ view: 'alerts', filter: 'all', query: '', offset: 0, mobile: false, reportPreview: null, previewRevision: null,
      alertStatusFilter: 'all', alertDeviceFilter: deviceId });
    void this.loadView();
  };
  private alertsCurrent(epoch: number, client: DataClient, tenantId: string) {
    return this.current(epoch, client) && tenantId === this.state.tenant?.id && this.state.view === 'alerts';
  }
  /** Fresh read (filters, refresh, navigation) or the explicit next keyset page; never polled. */
  loadAlerts = async (older = false) => {
    if (!this.client || !this.state.tenant || this.state.view !== 'alerts') return;
    const current = this.state.alerts;
    if (older && (current === null || current.nextBefore === null || this.state.alertsStatus !== 'ready'
      || this.state.alertsOlder || current.items.length >= MAX_LOADED_ALERTS)) return;
    if (older) this.emit({ alertsOlder: true, alertsError: null });
    else { this.reset(); this.emit({ alertsStatus: 'loading' }); }
    const tenant = this.state.tenant;
    if (!tenant) return;
    const client = this.client, epoch = this.epoch, signal = this.scope.signal, tenantId = tenant.id;
    const status = this.state.alertStatusFilter, deviceId = this.state.alertDeviceFilter;
    const request: Mutable<AlertOptions> = {
      limit: older && current !== null ? Math.min(this.limit(), MAX_LOADED_ALERTS - current.items.length) : this.limit(), signal };
    if (status !== 'all') request.status = status;
    if (deviceId !== null) request.deviceId = deviceId;
    if (older && current !== null && current.nextBefore !== null) request.before = current.nextBefore;
    try {
      if (older) {
        const page = await client.listAlerts(tenantId, request);
        if (!this.alertsCurrent(epoch, client, tenantId) || this.state.alerts === null) return;
        this.emit({ alerts: appendAlerts(this.state.alerts, page, this.readTime()), alertsOlder: false, alertsError: null, lastRead: this.readTime() });
        return;
      }
      // Labels and the device filter come from the first device page; no other page is read for them. That read is
      // optional: when it fails, the alerts still load and show short device ids with a note. A 401 on either read
      // disconnects, as on every other read.
      const [alertRead, labelRead] = await Promise.allSettled([client.listAlerts(tenantId, request),
        client.listDevices(tenantId, { offset: 0, limit: ALERT_DEVICE_PAGE, signal })]);
      if (!this.alertsCurrent(epoch, client, tenantId)) return;
      for (const read of [alertRead, labelRead]) {
        if (read.status === 'rejected' && code(read.reason) === 'unauthorized') throw read.reason;
      }
      if (alertRead.status === 'rejected') throw alertRead.reason;
      const labelError: UiMessage | null = labelRead.status === 'rejected'
        ? { ...errorMessage(labelRead.reason), sample: this.state.mode === 'demo' } : null;
      this.emit({ alerts: appendAlerts(null, alertRead.value, this.readTime()),
        alertDevices: labelRead.status === 'fulfilled' ? labelRead.value : null, alertDevicesError: labelError,
        alertsStatus: 'ready', alertsOlder: false, alertsError: null, lastRead: this.readTime() });
    } catch (error) {
      if (!this.alertsCurrent(epoch, client, tenantId) || code(error) === 'aborted') return;
      const key = code(error);
      if (older && key !== 'unauthorized' && key !== 'forbidden' && key !== 'not_found') {
        this.emit({ alertsOlder: false, alertsError: { ...errorMessage(error), sample: this.state.mode === 'demo' } });
        return;
      }
      this.fail(error, epoch, client);
    }
  };
  setAlertStatusFilter = (value: string) => {
    const next = value === 'all' ? 'all' : isAlertStatus(value) ? value : null;
    if (next === null || next === this.state.alertStatusFilter || this.state.view !== 'alerts') return;
    this.emit({ alertStatusFilter: next }); void this.loadAlerts();
  };
  setAlertDeviceFilter = (value: string) => {
    const next = value === '' ? null : DEVICE_ID_TEXT.test(value) ? value : undefined;
    if (next === undefined || next === this.state.alertDeviceFilter || this.state.view !== 'alerts') return;
    this.emit({ alertDeviceFilter: next }); void this.loadAlerts();
  };
  addDetailToReport = (update = false) => {
    const { detail, tenant, reportDraft: draft } = this.state;
    if (!this.client || !tenant || !detail || !draft || !this.state.detailOpen || this.state.detailBusy || this.state.detailError
      || !this.state.detailReadAt || detail.tenant_id !== tenant.id || detail.id !== this.state.detailTargetId
      || (this.detailNavigationContext !== null && !this.navigationCurrent()) || draft.context.generation !== this.contextGeneration) return;
    try {
      const record = captureRecord(detail, { tenantName: tenant.name, readAt: this.state.detailReadAt, context: draft.context });
      const next = update ? updateRecord(draft, record) : addRecord(draft, record);
      this.emit({ reportDraft: next, reportPreview: null, previewRevision: null, reportError: null, reportNotice: message(update ? 'app.reportNotice.updated' : 'app.reportNotice.added') });
    } catch (error) { this.reportFailure(error); }
  };
  private compareFailure(error: unknown) {
    const messages: Readonly<Record<string, UiMessage>> = {
      invalid_comparison: message('compare.error.invalid_comparison'), context_mismatch: message('compare.error.context_mismatch'),
      duplicate_device: message('compare.error.duplicate_device'), selection_full: message('compare.error.selection_full'),
      device_not_found: message('compare.error.device_not_found'), record_size_limit: message('compare.error.record_size_limit'),
      size_limit: message('compare.error.size_limit'), invalid_slot: message('compare.error.invalid_slot')
    };
    const key = code(error);
    this.emit({ compareError: Object.hasOwn(messages, key) ? messages[key] : message('compare.error.invalid_comparison'), compareNotice: null });
  }
  private captureComparison(action: 'add' | 'update' | 'replace', side?: 'left' | 'right') {
    const { detail, tenant, comparison } = this.state;
    if (!this.client || !tenant || !detail || !comparison || !this.state.detailOpen || this.state.detailBusy || this.state.detailError !== null
      || !this.state.detailReadAt || detail.tenant_id !== tenant.id || detail.id !== this.state.detailTargetId
      || (this.detailNavigationContext !== null && !this.navigationCurrent()) || comparison.context.tenantId !== tenant.id
      || comparison.context.mode !== (this.state.mode === 'demo' ? 'example' : 'api') || comparison.context.generation !== this.contextGeneration) return;
    if (action === 'replace' && side !== 'left' && side !== 'right') return;
    try {
      const device = captureComparableDevice(detail, { tenantId: tenant.id, readAt: this.state.detailReadAt });
      const next = action === 'add' ? addComparableDevice(comparison, device)
        : action === 'update' ? updateComparableDevice(comparison, device) : replaceSlot(comparison, side!, device);
      this.emit({ comparison: next, compareError: null, compareNotice: message(action === 'add' ? 'compare.notice.added' : action === 'update' ? 'compare.notice.updated' : 'compare.notice.replaced') });
    } catch (error) { this.compareFailure(error); }
  }
  addDetailToComparison = () => this.captureComparison('add');
  updateDetailInComparison = () => this.captureComparison('update');
  replaceComparisonSide = (side: 'left' | 'right') => this.captureComparison('replace', side);
  removeCompareDevice = (id: string) => {
    if (!this.state.comparison) return;
    try { this.emit({ comparison: removeComparableDevice(this.state.comparison, id), compareError: null, compareNotice: null }); }
    catch (error) { this.compareFailure(error); }
  };
  clearComparison = () => {
    if (!this.state.comparison) return;
    try { this.emit({ comparison: clearCompareState(this.state.comparison), compareError: null, compareNotice: null }); }
    catch (error) { this.compareFailure(error); }
  };
  private resetPolicyReviewPatch() {
    return { policyReview: clearPolicyReviewState(this.state.policyReview), policyReviewImportId: ++this.policyReviewReadSequence };
  }
  private policyReviewReadCurrent(sequence: number, generation: number) {
    return sequence === this.policyReviewReadSequence && generation === this.contextGeneration;
  }
  private beginPolicyReviewRead() {
    const sequence = ++this.policyReviewReadSequence, generation = this.contextGeneration;
    this.emit({ policyReview: beginPolicyReviewImport(this.state.policyReview), policyReviewImportId: sequence });
    return { sequence, generation };
  }
  private policyReviewFailure(error: unknown, sequence: number, generation: number) {
    if (!this.policyReviewReadCurrent(sequence, generation)) return;
    const value = code(error);
    const errorCode: PolicyReviewErrorCode = POLICY_REVIEW_ERROR_CODES.includes(value as PolicyReviewErrorCode)
      ? value as PolicyReviewErrorCode : 'invalid_artifact';
    this.emit({ policyReview: failPolicyReviewImport(this.state.policyReview, errorCode) });
  }
  importPolicyReviewFile = async (file: File) => {
    const { sequence, generation } = this.beginPolicyReviewRead();
    try {
      if (!(file instanceof File)) { this.policyReviewFailure(null, sequence, generation); return; }
      if (file.size > MAX_POLICY_REVIEW_BYTES) {
        this.emit({ policyReview: failPolicyReviewImport(this.state.policyReview, 'file_too_large') }); return;
      }
      // File metadata, names and original bytes stay in this bounded local read.
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (!this.policyReviewReadCurrent(sequence, generation)) return;
      const { parsePolicyReview } = await reviewModule(import('./features/policyReview/policyReviewAdapter'));
      if (!this.policyReviewReadCurrent(sequence, generation)) return;
      const document = parsePolicyReview(bytes, 'file');
      this.emit({ policyReview: completePolicyReviewImport(this.state.policyReview, document) });
    } catch (error) { this.policyReviewFailure(error, sequence, generation); }
  };
  rejectPolicyReviewSelection = () => {
    const { sequence, generation } = this.beginPolicyReviewRead();
    this.policyReviewFailure(null, sequence, generation);
  };
  loadPolicyReviewExample = async (kind: 'comparison' | 'blocked') => {
    const { sequence, generation } = this.beginPolicyReviewRead();
    try {
      if (kind !== 'comparison' && kind !== 'blocked') { this.policyReviewFailure(null, sequence, generation); return; }
      const [{ parsePolicyReview }, example] = await reviewModule(Promise.all([
        import('./features/policyReview/policyReviewAdapter'),
        kind === 'comparison' ? import('./features/policyReview/examples/preview-output.json?raw') : import('./features/policyReview/examples/preview-missing-context-output.json?raw')
      ]));
      if (!this.policyReviewReadCurrent(sequence, generation)) return;
      const text = example.default;
      const document = parsePolicyReview(new TextEncoder().encode(text), 'example');
      if (this.policyReviewReadCurrent(sequence, generation)) this.emit({ policyReview: completePolicyReviewImport(this.state.policyReview, document) });
    } catch (error) { this.policyReviewFailure(error, sequence, generation); }
  };
  clearPolicyReview = () => this.emit(this.resetPolicyReviewPatch());
  setPolicyReviewQuery = (query: string) => {
    if (query.length > 256 || /[\u0000-\u001f]/.test(query)) return;
    this.emit({ policyReview: setPolicyReviewQuery(this.state.policyReview, query) });
  };
  setPolicyReviewFilter = (filter: PolicyReviewFilter) => this.emit({ policyReview: setPolicyReviewFilter(this.state.policyReview, filter) });
  selectPolicyReviewScenario = (id: string) => {
    if (!this.state.policyReview.document?.scenarios.some((scenario) => scenario.scenarioId === id)) return;
    this.emit({ policyReview: selectPolicyReviewScenario(this.state.policyReview, id) });
  };
  setPolicyReviewDetails = (show: boolean) => this.emit({ policyReview: setPolicyReviewDetails(this.state.policyReview, show) });
  private resetTermivarReviewPatch() {
    ++this.termivarManifestReadSequence;
    return { termivarReview: clearTermivarReviewState(this.state.termivarReview), termivarReviewImportId: ++this.termivarReadSequence };
  }
  private termivarReadCurrent(sequence: number, generation: number) {
    return sequence === this.termivarReadSequence && generation === this.contextGeneration;
  }
  private beginTermivarRead() {
    const sequence = ++this.termivarReadSequence, generation = this.contextGeneration;
    ++this.termivarManifestReadSequence;
    this.emit({ termivarReview: beginTermivarImport(this.state.termivarReview), termivarReviewImportId: sequence });
    return { sequence, generation };
  }
  private termivarErrorCode(error: unknown): TermivarReviewErrorCode {
    const value = code(error);
    return TERMIVAR_REVIEW_ERROR_CODES.includes(value as TermivarReviewErrorCode) ? value as TermivarReviewErrorCode : 'invalid_artifact';
  }
  private termivarFailure(error: unknown, sequence: number, generation: number) {
    if (this.termivarReadCurrent(sequence, generation)) this.emit({ termivarReview: failTermivarImport(this.state.termivarReview, this.termivarErrorCode(error)) });
  }
  importTermivarFile = async (file: File) => {
    const { sequence, generation } = this.beginTermivarRead();
    try {
      if (!(file instanceof File)) { this.termivarFailure(null, sequence, generation); return; }
      if (file.size > MAX_TERMIVAR_REVIEW_BYTES) {
        this.emit({ termivarReview: failTermivarImport(this.state.termivarReview, 'file_too_large') }); return;
      }
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (!this.termivarReadCurrent(sequence, generation)) return;
      const { parseTermivarAssessment } = await reviewModule(import('./features/termivarReview/termivarAdapter'));
      if (!this.termivarReadCurrent(sequence, generation)) return;
      const document = await parseTermivarAssessment(bytes, 'file');
      if (this.termivarReadCurrent(sequence, generation)) this.emit({ termivarReview: completeTermivarImport(this.state.termivarReview, document) });
    } catch (error) { this.termivarFailure(error, sequence, generation); }
  };
  rejectTermivarSelection = () => {
    const { sequence, generation } = this.beginTermivarRead(); this.termivarFailure(null, sequence, generation);
  };
  loadTermivarExample = async (kind: 'complete' | 'incomplete') => {
    const { sequence, generation } = this.beginTermivarRead();
    try {
      if (kind !== 'complete' && kind !== 'incomplete') { this.termivarFailure(null, sequence, generation); return; }
      const [{ parseTermivarAssessment }, example] = await reviewModule(Promise.all([
        import('./features/termivarReview/termivarAdapter'),
        kind === 'complete' ? import('./features/termivarReview/examples/assessment-example.json?raw') : import('./features/termivarReview/examples/incomplete-example.json?raw')
      ]));
      if (!this.termivarReadCurrent(sequence, generation)) return;
      const bytes = new TextEncoder().encode(example.default);
      const document = await parseTermivarAssessment(bytes, 'example');
      if (this.termivarReadCurrent(sequence, generation)) this.emit({ termivarReview: completeTermivarImport(this.state.termivarReview, document) });
    } catch (error) { this.termivarFailure(error, sequence, generation); }
  };
  private termivarManifestCurrent(sequence: number, generation: number, document: AssessmentDocument) {
    return sequence === this.termivarManifestReadSequence && generation === this.contextGeneration && document === this.state.termivarReview.document;
  }
  private beginTermivarManifestRead() {
    const document = this.state.termivarReview.document;
    if (!document || this.state.termivarReview.status !== 'ready') return null;
    const sequence = ++this.termivarManifestReadSequence, generation = this.contextGeneration;
    this.emit({ termivarReview: beginTermivarManifestImport(this.state.termivarReview) });
    return { sequence, generation, document };
  }
  importTermivarManifest = async (file: File) => {
    const read = this.beginTermivarManifestRead(); if (!read) return;
    const { sequence, generation, document } = read;
    try {
      if (!(file instanceof File)) throw { code: 'invalid_artifact' };
      if (file.size > MAX_TERMIVAR_MANIFEST_BYTES) throw { code: 'file_too_large' };
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (!this.termivarManifestCurrent(sequence, generation, document)) return;
      const { parseTermivarManifest } = await reviewModule(import('./features/termivarReview/termivarAdapter'));
      if (!this.termivarManifestCurrent(sequence, generation, document)) return;
      const manifest = parseTermivarManifest(bytes, document);
      this.emit({ termivarReview: completeTermivarManifestImport(this.state.termivarReview, manifest) });
    } catch (error) {
      if (this.termivarManifestCurrent(sequence, generation, document)) this.emit({ termivarReview: failTermivarManifestImport(this.state.termivarReview, this.termivarErrorCode(error)) });
    }
  };
  rejectTermivarManifestSelection = () => {
    if (this.beginTermivarManifestRead()) this.emit({ termivarReview: failTermivarManifestImport(this.state.termivarReview, 'invalid_artifact') });
  };
  clearTermivarReview = () => this.emit(this.resetTermivarReviewPatch());
  setTermivarQuery = (query: string) => {
    if (query.length > 256 || /[\u0000-\u001f]/.test(query)) return;
    this.emit({ termivarReview: setTermivarQuery(this.state.termivarReview, query) });
  };
  setTermivarFilter = (filter: TermivarReviewFilter) => this.emit({ termivarReview: setTermivarFilter(this.state.termivarReview, filter) });
  selectTermivarFinding = (itemKey: string) => this.emit({ termivarReview: selectTermivarFinding(this.state.termivarReview, itemKey) });
  setTermivarDetails = (show: boolean) => this.emit({ termivarReview: setTermivarDetails(this.state.termivarReview, show) });
  private resetTermivarComparisonPatch() {
    return { termivarComparison: clearComparisonReview(this.state.termivarComparison), termivarComparisonImportId: ++this.termivarComparisonReadSequence };
  }
  private termivarComparisonReadCurrent(sequence: number, generation: number) {
    return sequence === this.termivarComparisonReadSequence && generation === this.contextGeneration;
  }
  private beginTermivarComparisonRead() {
    const sequence = ++this.termivarComparisonReadSequence, generation = this.contextGeneration;
    this.emit({ termivarComparison: beginComparisonImport(this.state.termivarComparison), termivarComparisonImportId: sequence });
    return { sequence, generation };
  }
  private termivarComparisonFailure(error: unknown, sequence: number, generation: number) {
    if (!this.termivarComparisonReadCurrent(sequence, generation)) return;
    const value = code(error);
    const errorCode: ComparisonErrorCode = COMPARISON_ERROR_CODES.includes(value as ComparisonErrorCode) ? value as ComparisonErrorCode : 'invalid_comparison';
    this.emit({ termivarComparison: failComparisonImport(this.state.termivarComparison, errorCode) });
  }
  importTermivarComparisonFile = async (file: File) => {
    const { sequence, generation } = this.beginTermivarComparisonRead();
    try {
      if (!(file instanceof File)) { this.termivarComparisonFailure(null, sequence, generation); return; }
      if (file.size > MAX_COMPARISON_REVIEW_BYTES) {
        this.emit({ termivarComparison: failComparisonImport(this.state.termivarComparison, 'file_too_large') }); return;
      }
      const bytes = new Uint8Array(await file.arrayBuffer());
      if (!this.termivarComparisonReadCurrent(sequence, generation)) return;
      const { parseTermivarComparison } = await reviewModule(import('./features/termivarComparison/comparisonAdapter'));
      if (!this.termivarComparisonReadCurrent(sequence, generation)) return;
      const document = parseTermivarComparison(bytes, 'file');
      this.emit({ termivarComparison: completeComparisonImport(this.state.termivarComparison, document) });
    } catch (error) { this.termivarComparisonFailure(error, sequence, generation); }
  };
  rejectTermivarComparisonSelection = () => {
    const { sequence, generation } = this.beginTermivarComparisonRead(); this.termivarComparisonFailure(null, sequence, generation);
  };
  loadTermivarComparisonExample = async () => {
    const { sequence, generation } = this.beginTermivarComparisonRead();
    try {
      const [{ parseTermivarComparison }, example] = await reviewModule(Promise.all([
        import('./features/termivarComparison/comparisonAdapter'),
        import('./features/termivarComparison/examples/comparison-example.json?raw')
      ]));
      if (!this.termivarComparisonReadCurrent(sequence, generation)) return;
      const document = parseTermivarComparison(new TextEncoder().encode(example.default), 'example');
      if (this.termivarComparisonReadCurrent(sequence, generation)) this.emit({ termivarComparison: completeComparisonImport(this.state.termivarComparison, document) });
    } catch (error) { this.termivarComparisonFailure(error, sequence, generation); }
  };
  clearTermivarComparison = () => this.emit(this.resetTermivarComparisonPatch());
  setTermivarComparisonQuery = (query: string) => {
    if (query.length > 256 || /[\u0000-\u001f]/.test(query)) return;
    this.emit({ termivarComparison: setComparisonQuery(this.state.termivarComparison, query) });
  };
  setTermivarComparisonFilter = (filter: ComparisonFilter) => this.emit({ termivarComparison: setComparisonFilter(this.state.termivarComparison, filter) });
  selectTermivarComparisonRecord = (key: string) => this.emit({ termivarComparison: selectComparisonRecord(this.state.termivarComparison, key) });
  setTermivarComparisonDetails = (show: boolean) => this.emit({ termivarComparison: setComparisonDetails(this.state.termivarComparison, show) });
  startGuide = (flow: GuideFlow) => {
    if (this.state.mode !== 'demo' || !this.state.tenant || this.state.loading || this.state.busy
      || (flow !== 'endpoint' && flow !== 'termivar' && flow !== 'policy')) return;
    this.guideGeneration = this.contextGeneration;
    this.emit({ guide: createGuideState(flow) });
  };
  closeGuide = () => {
    this.guideGeneration = null;
    if (this.state.guide !== null) this.emit({ guide: null });
  };
  private guideCurrent() {
    if (this.state.guide !== null && this.state.mode === 'demo' && this.state.tenant !== null && this.guideGeneration === this.contextGeneration) return true;
    this.closeGuide(); return false;
  }
  previousGuideStep = () => {
    if (this.guideCurrent() && this.state.guide) this.emit({ guide: moveGuideStep(this.state.guide, -1) });
  };
  nextGuideStep = () => {
    if (this.guideCurrent() && this.state.guide) this.emit({ guide: moveGuideStep(this.state.guide, 1) });
  };
  openGuideStep = () => {
    if (!this.guideCurrent()) return;
    const step = currentGuideStep(this.state.guide);
    if (!step) { this.closeGuide(); return; }
    if (step.destination !== this.state.view) this.navigate(step.destination);
  };
  removeReportRecord = (id: string) => {
    if (!this.state.reportDraft) return;
    try { this.emit({ reportDraft: removeRecord(this.state.reportDraft, id), reportPreview: null, previewRevision: null, reportError: null, reportNotice: null }); }
    catch (error) { this.reportFailure(error); }
  };
  clearReport = () => {
    if (this.state.reportDraft) this.emit({ reportDraft: clearDraft(this.state.reportDraft), reportPreview: null, previewRevision: null, reportError: null, reportNotice: null });
  };
  setReportIdentifiers = (show: boolean) => this.emit({ showIdentifiers: show, reportPreview: null, previewRevision: null, reportError: null });
  createReportPreview = () => {
    if (!this.state.reportDraft || !this.state.tenant || !this.client || this.state.loading) return;
    try {
      const report = buildPreview(this.state.reportDraft, { includeIdentifiers: this.state.showIdentifiers, createdAt: this.readTime(), locale: this.state.locale });
      this.emit({ reportPreview: report, previewRevision: this.state.reportDraft.revision, reportError: null });
    } catch (error) { this.reportFailure(error); }
  };
  closeReportPreview = () => this.emit({ reportPreview: null, previewRevision: null, reportError: null });
  printReport = () => {
    if (!this.state.reportPreview || this.state.reportPreview.locale !== this.state.locale || !this.state.reportDraft || !this.client || !this.state.tenant || this.state.previewRevision !== this.state.reportDraft.revision || this.state.reportDraft.context.generation !== this.contextGeneration) return;
    try { window.print(); } catch { this.emit({ reportError: message('app.reportError.print') }); }
  };
  setFilter = (filter: string) => { if (filter !== this.state.filter && this.state.detailOpen) this.closeDevice(); this.emit({ filter }); };
  setQuery = (query: string) => { if (query !== this.state.query && this.state.detailOpen) this.closeDevice(); this.emit({ query }); };
  setSort = (sort: string) => { if (sort !== this.state.sort && this.state.detailOpen) this.closeDevice(); this.emit({ sort }); };
  setLocale = (locale: Locale) => {
    if ((locale !== 'tr' && locale !== 'en') || locale === this.state.locale) return;
    this.emit({ locale, reportPreview: null, previewRevision: null });
  };
  toggleMobile = () => this.emit({ mobile: !this.state.mobile });
  openConnection = () => this.emit({ connectionOpen: true, connectionError: null });
  closeConnection = () => this.emit({ connectionOpen: false, connectionError: null });
  disconnect = () => {
    this.client?.disconnect(); this.client = null; this.reset(); this.clearReportContext();
    this.emit({ mode: 'disconnected', tenants: [], tenant: null, nextTenant: null, query: '', filter: 'all',
      error: message('app.error.connectionClosed'), ...ALERT_FILTERS_DEFAULT });
  };
  useDemo = (scenario: Scenario) => {
    this.disconnect(); this.client = createDemoClient({ scenario });
    this.emit({ mode: 'demo', scenario, connectionOpen: false, connectionError: null }); void this.reload();
  };
  connect = (apiBase: string, accessToken: string) => {
    this.disconnect();
    try {
      this.client = createApiClient({ apiBase, accessToken });
      this.emit({ mode: 'api', connectionOpen: false, connectionError: null }); void this.reload();
    } catch (error) { this.emit({ connectionError: errorMessage(error) }); }
  };
  pagehide = () => this.disconnect();
}
export const consoleStore = new ConsoleStore();
