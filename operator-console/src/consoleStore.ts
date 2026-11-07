import { createDemoClient } from './adapters/fixtures';
import { createApiClient } from './adapters/platformReadOnly';
import type { DataClient, Tenant, DevicePage, AuditPage, DeviceDetail } from './data/contracts';
import type { ReportContext, ReportDraft, ReportModel } from './features/reports/reportModel';
import { captureRecord } from './features/reports/capture';
import { createDraft, addRecord, updateRecord, removeRecord, clearDraft, buildPreview } from './features/reports/reportDraft';

export type View = 'overview' | 'devices' | 'products' | 'audit' | 'reports';
export type Scenario = 'normal' | 'empty' | 'error';
const ERRORS: Record<string, string> = {
  unauthorized: 'Operatör oturumu geçersiz veya süresi dolmuş. Yeniden bağlanın.',
  forbidden: 'Bu görünüm için güncel şirket yetkiniz bulunmuyor.',
  not_found: 'Kayıt bulunamadı veya bu şirket kapsamında erişilemiyor.',
  rate_limited: 'İstek sınırına ulaşıldı. Bir süre sonra elle yenileyin.',
  offline: 'Platforma ulaşılamadı. Bağlantıyı kontrol edip yeniden deneyin.',
  timeout: 'Veri alma süresi doldu. Önceki veriler güncelmiş gibi gösterilmez.',
  malformed: 'Yanıt bu konsolun veri sözleşmesiyle uyumlu değil.',
  disconnected: 'Bağlantı kapatıldı. Veri kaynağından yeniden bağlanabilirsiniz.',
  https_required: 'Canlı okuma için konsol aynı HTTPS adresinden sunulmalıdır.',
  invalid_input: 'Bağlantı veya sayfalama bilgisi geçerli değil.',
  server_error: 'Platform isteği tamamlayamadı. Daha sonra yeniden deneyin.'
};
function code(error: unknown): string {
  return error && typeof error === 'object' && 'code' in error && typeof error.code === 'string' ? error.code : '';
}
export function errorMessage(error: unknown) { return ERRORS[code(error)] || 'Veri alınamadı. Bağlantıyı kontrol edip yeniden deneyin.'; }
interface State {
  mode: 'demo' | 'api' | 'disconnected'; scenario: Scenario; view: View; mobile: boolean;
  tenants: readonly Tenant[]; nextTenant: number | null; tenant: Tenant | null;
  devices: DevicePage | null; offset: number; busy: boolean; loading: boolean;
  audit: AuditPage | null; auditOffset: number; auditStatus: 'idle' | 'loading' | 'ready' | 'error'; auditError: string;
  query: string; filter: string; sort: string; error: string; lastRead: string;
  detailOpen: boolean; detail: DeviceDetail | null; detailError: string; detailBusy: boolean;
  connectionOpen: boolean; connectionError: string;
  detailReadAt: string; reportDraft: ReportDraft | null; reportPreview: ReportModel | null;
  previewRevision: number | null; showIdentifiers: boolean; reportError: string; reportNotice: string;
}
class ConsoleStore {
  private client: DataClient | null = createDemoClient();
  private epoch = 0;
  private scope = new AbortController();
  private detailRequest = new AbortController();
  private detailSequence = 0;
  private contextGeneration = 1;
  private listeners = new Set<() => void>();
  private state: State = { mode: 'demo', scenario: 'normal', view: 'overview', mobile: false,
    tenants: [], nextTenant: null, tenant: null, devices: null, offset: 0, busy: false, loading: true,
    audit: null, auditOffset: 0, auditStatus: 'idle', auditError: '', query: '', filter: 'all', sort: 'name',
    error: '', lastRead: '', detailOpen: false, detail: null, detailBusy: false, detailError: '', connectionOpen: false, connectionError: '',
    detailReadAt: '', reportDraft: null, reportPreview: null, previewRevision: null, showIdentifiers: false, reportError: '', reportNotice: '' };
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private emit(patch: Partial<State> = {}) { this.state = { ...this.state, ...patch }; this.listeners.forEach((fn) => fn()); }
  private reset() {
    ++this.epoch; ++this.detailSequence; this.scope.abort(); this.detailRequest.abort();
    this.scope = new AbortController(); this.detailRequest = new AbortController();
    this.emit({ devices: null, audit: null, auditStatus: 'idle', auditError: '', error: '', lastRead: '',
      detail: null, detailOpen: false, detailError: '', detailBusy: false, detailReadAt: '', loading: false, busy: false });
  }
  private clearReportContext() {
    ++this.contextGeneration;
    this.emit({ reportDraft: null, reportPreview: null, previewRevision: null, showIdentifiers: false, reportError: '', reportNotice: '' });
  }
  private bindReportContext(tenant: Tenant | null) {
    if (!tenant || !this.client || this.state.mode === 'disconnected') { this.clearReportContext(); return; }
    const draft = this.state.reportDraft;
    if (draft && (draft.context.tenantId !== tenant.id || draft.context.mode !== (this.state.mode === 'demo' ? 'example' : 'api') || draft.context.generation !== this.contextGeneration)) this.clearReportContext();
    if (!this.state.reportDraft) {
      const context: ReportContext = { tenantId: tenant.id, mode: this.state.mode === 'demo' ? 'example' : 'api', generation: this.contextGeneration };
      this.emit({ reportDraft: createDraft(context) });
    }
  }
  private reportFailure(error: unknown) {
    const messages: Record<string, string> = {
      duplicate_record: 'Bu cihaz zaten raporda. Güncellemek için görüntülenen bilgilerle güncelle eylemini kullanın.',
      record_limit: 'Taslak en fazla 20 cihaz içerebilir. Yeni cihaz eklemek için bir kaydı kaldırın.',
      size_limit: 'Rapor taslağı 256 KiB sınırını aşıyor. Önce bir kaydı kaldırın.',
      context_mismatch: 'Veri bağlamı değişti. Cihaz ayrıntısını yeniden açıp yeni taslağa ekleyin.',
      record_not_found: 'Bu cihaz taslakta bulunmuyor. Ayrıntısını yeniden açıp rapora ekleyin.',
      empty_report: 'Önce bir cihazın ayrıntısını açıp durum raporuna ekleyin.'
    };
    this.emit({ reportError: messages[code(error)] || 'Bu bilgilerle rapor taslağı oluşturulamadı. Geçerli cihaz ayrıntısını yeniden açın.', reportNotice: '' });
  }
  private current(epoch: number, client: DataClient) { return epoch === this.epoch && client === this.client; }
  private limit() { return this.state.mode === 'demo' ? 5 : 50; }
  private readTime() { return new Date().toISOString(); }
  private fail(error: unknown, epoch: number, client: DataClient) {
    if (!this.current(epoch, client) || code(error) === 'aborted') return;
    const message = (this.state.mode === 'demo' ? 'Örnek senaryo · ' : '') + errorMessage(error);
    if (code(error) === 'forbidden' || code(error) === 'not_found') this.clearReportContext();
    if (code(error) === 'unauthorized') {
      this.disconnect(); this.emit({ error: message }); return;
    }
    this.emit({ devices: null, audit: null, detail: null, detailOpen: false, busy: false, loading: false,
      auditStatus: 'error', auditError: message, error: message });
  }
  reload = async () => {
    if (!this.client) { this.openConnection(); return; }
    const previous = this.state.tenant?.id;
    this.reset(); this.emit({ loading: true, tenants: [], tenant: null, nextTenant: null });
    const client = this.client, epoch = this.epoch;
    try {
      const page = await client.listTenants({ offset: 0, limit: 50, signal: this.scope.signal });
      if (!this.current(epoch, client)) return;
      const tenant = previous ? page.items.find((item) => item.id === previous) || null : page.items[0] || null;
      this.bindReportContext(tenant);
      this.emit({ tenants: page.items, nextTenant: page.next_offset, tenant, loading: false, lastRead: this.readTime() });
      if (tenant) await this.loadView();
      else if (previous) this.emit({ error: 'Önceki şirket bu yetki sayfasında bulunmuyor. Diğer şirketleri yükleyip yeniden seçin; şirket kapsamı kendiliğinden değiştirilmedi.' });
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
    this.bindReportContext(tenant);
    this.reset(); this.emit({ tenant, query: '', filter: 'all', offset: 0 }); await this.loadView();
  };
  private loadView = async () => {
    if (this.state.view === 'audit') await this.loadAudit(0);
    else if (this.state.view === 'overview' || this.state.view === 'devices') await this.loadDevices(0);
  };
  navigate = (view: View, filter = 'all') => {
    if (this.state.loading) return;
    this.reset(); this.emit({ view, filter, query: '', offset: 0, mobile: false, reportPreview: null, previewRevision: null }); void this.loadView();
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
    this.detailRequest.abort(); this.detailRequest = new AbortController();
    const client = this.client, epoch = this.epoch, sequence = ++this.detailSequence, tenant = this.state.tenant.id, reportGeneration = this.contextGeneration;
    this.emit({ detail: null, detailOpen: true, detailBusy: true, detailError: '', detailReadAt: '', reportError: '', reportNotice: '' });
    try {
      const detail = await client.getDevice(tenant, id, { signal: this.detailRequest.signal });
      if (!this.current(epoch, client) || sequence !== this.detailSequence || reportGeneration !== this.contextGeneration) return;
      this.bindReportContext(this.state.tenant);
      this.emit({ detail, detailBusy: false, detailReadAt: this.readTime() });
    } catch (error) {
      if (!this.current(epoch, client) || sequence !== this.detailSequence || code(error) === 'aborted') return;
      if (code(error) === 'forbidden' || code(error) === 'not_found') this.clearReportContext();
      if (code(error) === 'unauthorized') this.fail(error, epoch, client);
      else this.emit({ detail: null, detailBusy: false, detailError: errorMessage(error) });
    }
  };
  closeDevice = () => { ++this.detailSequence; this.detailRequest.abort(); this.emit({ detailOpen: false, detail: null, detailError: '', detailBusy: false, detailReadAt: '' }); };
  addDetailToReport = (update = false) => {
    const { detail, tenant, reportDraft: draft } = this.state;
    if (!this.client || !tenant || !detail || !draft || !this.state.detailOpen || this.state.detailBusy || this.state.detailError || !this.state.detailReadAt || detail.tenant_id !== tenant.id || draft.context.generation !== this.contextGeneration) return;
    try {
      const record = captureRecord(detail, { tenantName: tenant.name, readAt: this.state.detailReadAt, context: draft.context });
      const next = update ? updateRecord(draft, record) : addRecord(draft, record);
      this.emit({ reportDraft: next, reportPreview: null, previewRevision: null, reportError: '', reportNotice: update ? 'Rapordaki kayıt bu görüntülenen bilgilerle güncellendi.' : 'Görüntülenen cihaz bilgileri rapor taslağına eklendi.' });
    } catch (error) { this.reportFailure(error); }
  };
  removeReportRecord = (id: string) => {
    if (!this.state.reportDraft) return;
    try { this.emit({ reportDraft: removeRecord(this.state.reportDraft, id), reportPreview: null, previewRevision: null, reportError: '', reportNotice: '' }); }
    catch (error) { this.reportFailure(error); }
  };
  clearReport = () => {
    if (this.state.reportDraft) this.emit({ reportDraft: clearDraft(this.state.reportDraft), reportPreview: null, previewRevision: null, reportError: '', reportNotice: '' });
  };
  setReportIdentifiers = (show: boolean) => this.emit({ showIdentifiers: show, reportPreview: null, previewRevision: null, reportError: '' });
  createReportPreview = () => {
    if (!this.state.reportDraft || !this.state.tenant || !this.client || this.state.loading) return;
    try {
      const report = buildPreview(this.state.reportDraft, { includeIdentifiers: this.state.showIdentifiers, createdAt: this.readTime() });
      this.emit({ reportPreview: report, previewRevision: this.state.reportDraft.revision, reportError: '' });
    } catch (error) { this.reportFailure(error); }
  };
  closeReportPreview = () => this.emit({ reportPreview: null, previewRevision: null, reportError: '' });
  printReport = () => {
    if (!this.state.reportPreview || !this.state.reportDraft || !this.client || !this.state.tenant || this.state.previewRevision !== this.state.reportDraft.revision || this.state.reportDraft.context.generation !== this.contextGeneration) return;
    try { window.print(); } catch { this.emit({ reportError: 'Tarayıcı yazdırma penceresi açılamadı. Bu tarayıcıda yazdırma kullanılamıyor olabilir.' }); }
  };
  setFilter = (filter: string) => this.emit({ filter });
  setQuery = (query: string) => this.emit({ query });
  setSort = (sort: string) => this.emit({ sort });
  toggleMobile = () => this.emit({ mobile: !this.state.mobile });
  openConnection = () => this.emit({ connectionOpen: true, connectionError: '' });
  closeConnection = () => this.emit({ connectionOpen: false, connectionError: '' });
  disconnect = () => {
    this.client?.disconnect(); this.client = null; this.reset(); this.clearReportContext();
    this.emit({ mode: 'disconnected', tenants: [], tenant: null, nextTenant: null, query: '', filter: 'all',
      error: 'Bağlantı kapalı. Veri kaynağından örnek görünümü veya mevcut platformu seçin.' });
  };
  useDemo = (scenario: Scenario) => {
    this.disconnect(); this.client = createDemoClient({ scenario });
    this.emit({ mode: 'demo', scenario, connectionOpen: false, connectionError: '' }); void this.reload();
  };
  connect = (apiBase: string, accessToken: string) => {
    this.disconnect();
    try {
      this.client = createApiClient({ apiBase, accessToken });
      this.emit({ mode: 'api', connectionOpen: false, connectionError: '' }); void this.reload();
    } catch (error) { this.emit({ connectionError: errorMessage(error) }); }
  };
  pagehide = () => this.disconnect();
}
export const consoleStore = new ConsoleStore();
