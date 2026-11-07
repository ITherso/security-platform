import { createDemoClient } from './adapters/fixtures';
import { createApiClient } from './adapters/platformReadOnly';
import type { DataClient, Tenant, DevicePage, AuditPage, DeviceDetail } from './data/contracts';

export type View = 'overview' | 'devices' | 'products' | 'audit';
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
}
class ConsoleStore {
  private client: DataClient | null = createDemoClient();
  private epoch = 0;
  private scope = new AbortController();
  private detailRequest = new AbortController();
  private detailSequence = 0;
  private listeners = new Set<() => void>();
  private state: State = { mode: 'demo', scenario: 'normal', view: 'overview', mobile: false,
    tenants: [], nextTenant: null, tenant: null, devices: null, offset: 0, busy: false, loading: true,
    audit: null, auditOffset: 0, auditStatus: 'idle', auditError: '', query: '', filter: 'all', sort: 'name',
    error: '', lastRead: '', detailOpen: false, detail: null, detailBusy: false, detailError: '', connectionOpen: false, connectionError: '' };
  snapshot = () => this.state;
  subscribe = (listener: () => void) => { this.listeners.add(listener); return () => { this.listeners.delete(listener); }; };
  private emit(patch: Partial<State> = {}) { this.state = { ...this.state, ...patch }; this.listeners.forEach((fn) => fn()); }
  private reset() {
    ++this.epoch; ++this.detailSequence; this.scope.abort(); this.detailRequest.abort();
    this.scope = new AbortController(); this.detailRequest = new AbortController();
    this.emit({ devices: null, audit: null, auditStatus: 'idle', auditError: '', error: '', lastRead: '',
      detail: null, detailOpen: false, detailError: '', detailBusy: false, loading: false, busy: false });
  }
  private current(epoch: number, client: DataClient) { return epoch === this.epoch && client === this.client; }
  private limit() { return this.state.mode === 'demo' ? 5 : 50; }
  private readTime() { return new Date().toISOString(); }
  private fail(error: unknown, epoch: number, client: DataClient) {
    if (!this.current(epoch, client) || code(error) === 'aborted') return;
    const message = (this.state.mode === 'demo' ? 'Örnek senaryo · ' : '') + errorMessage(error);
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
    this.reset(); this.emit({ tenant, query: '', filter: 'all', offset: 0 }); await this.loadView();
  };
  private loadView = async () => {
    if (this.state.view === 'audit') await this.loadAudit(0);
    else if (this.state.view !== 'products') await this.loadDevices(0);
  };
  navigate = (view: View, filter = 'all') => {
    this.reset(); this.emit({ view, filter, query: '', offset: 0, mobile: false }); void this.loadView();
  };
  loadDevices = async (offset = 0) => {
    if (!this.client || !this.state.tenant || !Number.isInteger(offset) || offset < 0 || offset > 10000) return;
    this.reset(); this.emit({ busy: true, offset });
    const client = this.client, epoch = this.epoch, tenant = this.state.tenant.id;
    try {
      const page = await client.listDevices(tenant, { offset, limit: this.limit(), signal: this.scope.signal });
      if (!this.current(epoch, client)) return;
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
    const client = this.client, epoch = this.epoch, sequence = ++this.detailSequence, tenant = this.state.tenant.id;
    this.emit({ detail: null, detailOpen: true, detailBusy: true, detailError: '' });
    try {
      const detail = await client.getDevice(tenant, id, { signal: this.detailRequest.signal });
      if (!this.current(epoch, client) || sequence !== this.detailSequence) return;
      this.emit({ detail, detailBusy: false });
    } catch (error) {
      if (!this.current(epoch, client) || sequence !== this.detailSequence || code(error) === 'aborted') return;
      if (code(error) === 'unauthorized') this.fail(error, epoch, client);
      else this.emit({ detail: null, detailBusy: false, detailError: errorMessage(error) });
    }
  };
  closeDevice = () => { ++this.detailSequence; this.detailRequest.abort(); this.emit({ detailOpen: false, detail: null, detailError: '', detailBusy: false }); };
  setFilter = (filter: string) => this.emit({ filter });
  setQuery = (query: string) => this.emit({ query });
  setSort = (sort: string) => this.emit({ sort });
  toggleMobile = () => this.emit({ mobile: !this.state.mobile });
  openConnection = () => this.emit({ connectionOpen: true, connectionError: '' });
  closeConnection = () => this.emit({ connectionOpen: false, connectionError: '' });
  disconnect = () => {
    this.client?.disconnect(); this.client = null; this.reset();
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
