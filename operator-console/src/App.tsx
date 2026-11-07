import { useEffect, useRef, useState, useSyncExternalStore, type ReactNode } from 'react';
import { consoleStore as store, type Scenario, type View } from './consoleStore';
import { ProductCards, DeviceDetail, AuditView } from './components/ProductViews';
import { formatDate } from './components/display';
import { toDeviceListViewModel, receivedSortKey } from './data/viewModels';
export { consoleStore } from './consoleStore';

const TITLES: Record<View, [string, string, string]> = {
  overview: ['Güvenlik görünümü', 'Cihazların bildirdiği durumu, veri güncelliğinden ayrı takip edin.', 'Genel bakış'],
  devices: ['Cihaz envanteri', 'Şirket kapsamındaki cihazları ve son merkez kabulünü inceleyin.', 'Cihazlar'],
  products: ['Ürün görünürlüğü', 'Kurulum, çalışma beyanı ve rapor varlığı ayrı değerlendirilir.', 'Ürünler'],
  audit: ['İşlem geçmişi', 'Seçili şirket için API tarafından sunulan işlem kayıtları.', 'İşlem geçmişi']
};
const CONNECTION: Record<string, [string, string]> = {
  recent: ['Yakın zamanda bildirdi', 'success'], stale: ['Bildirim eski', 'warning'], never_seen: ['Henüz bildirmedi', 'neutral']
};
function Icon({ name = 'device' }: { name?: string }) {
  return <svg viewBox="0 0 24 24" aria-hidden="true">{name === 'overview' ? <><rect x="3" y="3" width="7" height="7" rx="1.5" /><rect x="14" y="3" width="7" height="7" rx="1.5" /><rect x="3" y="14" width="7" height="7" rx="1.5" /><rect x="14" y="14" width="7" height="7" rx="1.5" /></>
    : name === 'products' ? <><path d="M12 3 3 7.5 12 12l9-4.5ZM3 12l9 4.5 9-4.5M3 16.5l9 4.5 9-4.5" /></>
    : name === 'audit' ? <path d="M9 4h10v17H5V4h2M9 3h6v4H9zM8 12h8M8 16h5" />
    : name === 'refresh' ? <path d="M20 7v5h-5M4 17v-5h5M6 7a7 7 0 0 1 12-1l2 3M4 15l2 3a7 7 0 0 0 12-1" />
    : name === 'recent' ? <><circle cx="12" cy="12" r="9" /><path d="m7 12 3 3 7-7" /></>
    : name === 'stale' ? <><circle cx="12" cy="12" r="9" /><path d="M12 7v6l4 2" /></>
    : name === 'waiting' ? <path d="m12 3 10 18H2ZM12 8v5M12 17v.1" />
    : <><rect x="3" y="4" width="18" height="13" rx="2" /><path d="M8 21h8M12 17v4" /></>}</svg>;
}
function Badge({ children, tone = 'neutral' }: { children: ReactNode; tone?: string }) { return <span className="badge" data-tone={tone}>{children}</span>; }
function Modal({ open, onClose, children, className, label }: { open: boolean; onClose: () => void; children: ReactNode; className: string; label: string }) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => { const el = ref.current; if (!el) return; if (open && !el.open) el.showModal(); else if (!open && el.open) el.close(); }, [open]);
  return <dialog ref={ref} className={className} aria-label={label} onCancel={(event) => { event.preventDefault(); onClose(); }} onClose={onClose}>{open && children}</dialog>;
}
function Metrics() {
  const s = useSyncExternalStore(store.subscribe, store.snapshot); const items = s.devices?.items || [];
  const rows: [string, number, string, string, string, string][] = [
    ['Yüklenen cihazlar', items.length, 'Bu sayfada görüntülenen kayıt', 'device', 'purple', 'all'],
    ['Yakın zamanda bildiren', items.filter((d) => d.connection_status === 'recent').length, 'Koruma doğrulaması değildir', 'recent', 'success', 'recent'],
    ['Bildirimi eski', items.filter((d) => d.connection_status === 'stale').length, 'Son kabul zamanına göre', 'stale', 'warning', 'stale'],
    ['Henüz bildirmeyen', items.filter((d) => d.connection_status === 'never_seen').length, 'İlk ürün bildirimi bekleniyor', 'waiting', 'neutral', 'never_seen']
  ];
  return <section className="metrics" aria-label="Bu sayfadaki cihaz özeti">{rows.map(([label, value, note, icon, tone, filter]) =>
    <button key={filter} className="metric" data-tone={tone} onClick={() => store.navigate('devices', filter)}><span className="metric-top"><span className="metric-label">{label}</span><span className="metric-icon"><Icon name={icon} /></span></span><span className="metric-value">{s.devices ? value : '—'}</span><span className="metric-note">{note}</span></button>)}</section>;
}
function DeviceList() {
  const s = useSyncExternalStore(store.subscribe, store.snapshot), items = s.devices?.items || [];
  const model = s.devices ? toDeviceListViewModel(s.devices) : null;
  const query = s.query.trim().toLocaleLowerCase('tr-TR');
  const rows = items.filter((d) => (!query || `${d.label} ${d.id}`.toLocaleLowerCase('tr-TR').includes(query)) &&
    (s.filter === 'all' || (s.filter === 'revoked' ? d.identity_status === 'revoked' : d.connection_status === s.filter)))
    .sort((a, b) => s.sort === 'received' ? receivedSortKey(b.last_received_at).localeCompare(receivedSortKey(a.last_received_at)) : a.label.localeCompare(b.label, 'tr'));
  return <section className="panel"><div className="panel-heading"><div><h2>Cihazlar</h2><p>Kayıt ve bildirim durumlarını ayrı inceleyin.</p></div><Badge>Bu sayfa</Badge></div>
    <div className="list-toolbar"><div className="search-wrap"><input type="search" value={s.query} onChange={(e) => store.setQuery(e.target.value)} placeholder="Yüklü cihazlarda ara…" aria-label="Bu sayfadaki cihazlarda ara" /></div>
      <select className="filter-select" aria-label="Cihazları duruma göre filtrele" value={s.filter} onChange={(e) => store.setFilter(e.target.value)}>
        <option value="all">Tüm durumlar</option><option value="recent">Yakın bildirim</option><option value="stale">Bildirim eski</option><option value="never_seen">Henüz bildirmedi</option><option value="revoked">Cihaz kaydı iptal</option></select>
      <select className="filter-select" aria-label="Yüklenen cihazları sırala" value={s.sort} onChange={(e) => store.setSort(e.target.value)}><option value="name">Ada göre</option><option value="received">Son kabul önce</option></select></div>
    {s.busy || s.loading ? <div className="empty-state" role="status">Cihazlar yükleniyor…</div> : !s.devices ? <div className="empty-state">{s.error ? 'Güncel cihaz verisi alınamadı.' : 'Şirket seçildiğinde cihaz kayıtları burada görünür.'}</div>
      : !rows.length ? <div className="empty-state">{items.length ? 'Yüklenen sayfada bu filtreye uyan cihaz yok.' : 'Bu şirket için henüz cihaz kaydı yok.'}</div>
        : <div className="table-scroll"><table className="data-table"><thead><tr><th scope="col">CİHAZ</th><th scope="col">KAYIT / BİLDİRİM</th><th scope="col">SON MERKEZ KABULÜ</th><th scope="col">KAYNAK</th><th scope="col"><span className="sr-only">Ayrıntı</span></th></tr></thead><tbody>{rows.map((d) => <tr key={d.id}>
          <td><div className="device-cell"><span className="device-symbol"><Icon /></span><div><button className="device-link" onClick={() => void store.openDevice(d.id)}>{d.label}</button><div className="device-sub">{d.id.slice(0, 8).toUpperCase()}</div></div></div></td>
          <td><div className="status-stack"><Badge tone={CONNECTION[d.connection_status]?.[1]}>{CONNECTION[d.connection_status]?.[0] || 'Bilinmiyor'}</Badge>{d.identity_status === 'revoked' && <Badge tone="danger">Cihaz kaydı iptal</Badge>}</div></td>
          <td>{d.last_received_at ? formatDate(d.last_received_at) : 'Henüz yok'}{d.last_sequence !== null && <span className="cell-sub">Bildirilen sıra {d.last_sequence}</span>}</td>
          <td>Cihazın bildirdiği<span className="cell-sub">Bağımsız doğrulanmadı</span></td><td><button className="inspect-button" onClick={() => void store.openDevice(d.id)} aria-label={`${d.label} ayrıntılarını aç`}>↗</button></td></tr>)}</tbody></table></div>}
    <p className="scope-note">Arama, sıralama, filtre ve sayaçlar yalnız yüklenen sayfayı kapsar. Ürün özetleri cihaz ayrıntısında bulunur.</p>
    <div className="list-footer"><span>{s.devices ? `${s.offset + (items.length ? 1 : 0)}–${s.offset + items.length} · ${model?.loadedCount ?? items.length} yüklenen kayıt` : 'Veri bekleniyor'}</span><div className="pagination">
      <button className="btn btn-ghost" disabled={s.busy || s.offset === 0} onClick={() => void store.loadDevices(Math.max(0, s.offset - (s.mode === 'demo' ? 5 : 50)))}>‹ Önceki</button>
      <button className="btn btn-ghost" disabled={s.busy || s.devices?.next_offset == null || s.devices.next_offset > 10000} onClick={() => void store.loadDevices(s.devices?.next_offset ?? 0)}>Sonraki ›</button></div></div>
  </section>;
}
function Attention() {
  const s = useSyncExternalStore(store.subscribe, store.snapshot), items = s.devices?.items || [];
  return <section className="panel side-card"><h2>Gözden geçirilecekler</h2><p>Yalnız yüklenen sayfadaki kayıtlar.</p><div className="attention-list">{[
    { label: 'Bildirimi eski', note: 'Yeni bildirim bekleyen cihazlar', filter: 'stale', tone: 'warning', symbol: '◷', count: items.filter((d) => d.connection_status === 'stale').length },
    { label: 'Cihaz kaydı iptal', note: 'Firewall çalışma durumu değildir', filter: 'revoked', tone: 'danger', symbol: '⊘', count: items.filter((d) => d.identity_status === 'revoked').length },
    { label: 'İlk bildirim bekleniyor', note: 'Ürün durumu henüz bilinmiyor', filter: 'never_seen', tone: 'neutral', symbol: '⋯', count: items.filter((d) => d.connection_status === 'never_seen').length }
  ].map((item) => <div className="attention-row" data-tone={item.tone} key={item.filter}><span className="attention-dot">{item.symbol}</span><div><strong>{item.label}</strong><p>{item.note}</p></div><button onClick={() => store.navigate('devices', item.filter)} aria-label={`${item.label} cihazları göster`}>{s.devices ? item.count : '—'} ›</button></div>)}</div>
    <div className="trust-note"><strong>Bildirim, koruma kanıtı değildir</strong><p>Yeni bir rapor, firewall engellemesinin veya bulguların merkez tarafından doğrulandığını göstermez.</p></div></section>;
}
function Catalog() {
  return <section className="panel side-card"><h2>Ürünler</h2><p>Cihaz ayrıntılarında ayrı değerlendirilir.</p><div className="catalog-list">{[['◈', 'HostBasedFirewall', 'Motor ve çalışma beyanı', 'Beyan'], ['⌁', 'Termivar', 'Sayısal rapor özeti', 'Deneysel'], ['◇', 'Antivirüs', 'Kullanıma hazır değil', 'Planlanan']].map(([symbol, name, description, status]) =>
    <div className="catalog-item" key={name}><span className="product-symbol">{symbol}</span><div><strong>{name}</strong><p>{description}</p></div><span className="product-state">{status}</span></div>)}</div></section>;
}
function ConnectionPanel() {
  const s = useSyncExternalStore(store.subscribe, store.snapshot);
  const token = useRef<HTMLInputElement>(null), base = useRef<HTMLInputElement>(null);
  const [scenario, setScenario] = useState<Scenario>('normal');
  const close = () => { if (token.current) token.current.value = ''; store.closeConnection(); };
  return <Modal open={s.connectionOpen} onClose={close} className="connection-dialog" label="Veri kaynağı">
    <div className="connection-heading"><div><p className="eyebrow">VERİ KAYNAĞI</p><h2>Görünümü bağla</h2></div><button className="icon-button" onClick={close} aria-label="Pencereyi kapat">×</button></div>
    <p className="muted">Örnek görünümü keşfedin veya aynı adreste sunulan mevcut platform API’sini okuyun. Bu panel bir giriş veya SSO hizmeti değildir.</p>
    <div className="source-option"><span className="source-option-icon">◈</span><div><strong>Örnek şirket ve cihazlar</strong><p>Gerçek cihazlara bağlı değildir.</p><label className="sr-only" htmlFor="demo-scenario">Örnek senaryo</label><select id="demo-scenario" value={scenario} onChange={(e) => setScenario(e.target.value as Scenario)}><option value="normal">Cihaz ve ürün örnekleri</option><option value="empty">Boş envanter örneği</option><option value="error">Bağlantı hatası örneği</option></select></div><button className="btn btn-ghost" onClick={() => store.useDemo(scenario)}>Örneği aç</button></div>
    <form autoComplete="off" onSubmit={(event) => { event.preventDefault(); const value = token.current?.value || ''; if (token.current) token.current.value = ''; store.connect(base.current?.value || '', value); }}>
      <h3>Mevcut platform bağlantısı</h3><p className="small muted">{location.protocol === 'https:' ? 'API aynı HTTPS adresinde /api/v1 altında sunulmalıdır.' : 'Yerel HTTP önizlemesi örnek veri içindir. Canlı okuma aynı HTTPS adresini gerektirir.'}</p>
      <label htmlFor="api-base">API adresi</label><input ref={base} id="api-base" type="url" defaultValue={`${location.origin}/api/v1`} spellCheck={false} onInput={() => { if (store.snapshot().mode === 'api') store.disconnect(); }} />
      <label htmlFor="access-token">Mevcut operatör erişim token’ı</label><input ref={token} id="access-token" type="password" autoComplete="off" autoCapitalize="off" spellCheck={false} placeholder="Yetkili sağlayıcınızdan alınan erişim token’ı" onInput={() => { if (store.snapshot().mode === 'api') store.disconnect(); }} />
      <p className="field-help">Yalnız açık sayfanın belleğinde tutulur; bağlanınca alan temizlenir. Bağlantı kapanınca veya sayfadan ayrılınca oturum verileri temizlenir. Token’ın sunucudaki yetkileri değişmez.</p>
      {s.connectionError && <p className="inline-error" role="alert">{s.connectionError}</p>}
      <div className="connection-actions"><button className="btn btn-ghost" type="button" onClick={() => { store.disconnect(); close(); }}>Bağlantıyı kapat</button><button className="btn btn-primary" type="submit" disabled={location.protocol !== 'https:'}>Salt okunur bağlan</button></div>
    </form></Modal>;
}
export function App() {
  const s = useSyncExternalStore(store.subscribe, store.snapshot), demo = s.mode === 'demo';
  useEffect(() => { window.addEventListener('pagehide', store.pagehide); return () => window.removeEventListener('pagehide', store.pagehide); }, []);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [s.view, s.tenant?.id]);
  const [title, subtitle, breadcrumb] = TITLES[s.view], admin = s.tenant?.role === 'tenant_admin';
  return <><a className="skip-link" href="#main">İçeriğe geç</a><div className="app-shell"><aside className={`sidebar ${s.mobile ? 'open' : ''}`} aria-label="Ana gezinme">
    <button className="icon-button mobile-only sidebar-close" aria-label="Menüyü kapat" onClick={store.toggleMobile}>×</button><a href="#" className="brand" onClick={(e) => { e.preventDefault(); store.navigate('overview'); }}><span className="brand-mark"><svg viewBox="0 0 40 44" aria-hidden="true"><path d="M20 2 36 8v13c0 10-16 20-16 20S4 31 4 21V8Z" /><path d="m12 21 5 5 11-12" /></svg></span><span>Güvenlik<span className="brand-second">KONSOLU</span></span></a>
    <div className="workspace-picker"><label htmlFor="tenant-select">ÇALIŞMA ALANI</label><div className="select-wrap"><span className="workspace-symbol">◈</span><select id="tenant-select" aria-label="Şirket seç" disabled={!s.tenants.length || s.loading} value={s.tenant?.id || ''} onChange={(e) => void store.selectTenant(e.target.value)}>{!s.tenant && <option value="">{s.loading ? 'Yükleniyor…' : 'Şirket seçilmedi'}</option>}{s.tenants.map((item) => <option key={item.id} value={item.id}>{item.name}</option>)}</select></div>
      {s.nextTenant !== null && <button className="sidebar-link" disabled={s.loading || s.nextTenant > 10000} onClick={() => void store.moreTenants()}>Diğer şirketleri yükle</button>}</div>
    <p className="nav-caption">GENEL</p><nav className="nav-list">{(Object.keys(TITLES) as View[]).map((view) => <button key={view} className={`nav-item ${view === s.view ? 'active' : ''}`} aria-current={view === s.view ? 'page' : undefined} onClick={() => store.navigate(view)}><Icon name={view} />{TITLES[view][2]}{view === 'audit' && !admin && <span className="nav-lock" aria-label="Yönetici rolü gerekir">⌑</span>}</button>)}</nav>
    <div className="sidebar-spacer" /><div className="sidebar-note"><span className="note-icon">↗</span><strong>Tek yerden görünürlük</strong><p>Cihaz kaydı, veri güncelliği ve ürün beyanlarını ayrı izleyin.</p><span className="sidebar-tag">Salt okunur konsol</span></div><div className="operator"><span className="avatar">O</span><div><strong>Operatör görünümü</strong><span>{s.tenant ? `${demo ? 'Örnek · ' : ''}${admin ? 'Şirket yöneticisi' : 'Görüntüleyici'}` : 'Şirket seçilmedi'}</span></div></div>
  </aside><div className="workspace"><header className="topbar"><button className="icon-button mobile-only" aria-label="Menüyü aç" aria-expanded={s.mobile} onClick={store.toggleMobile}>☰</button><div className="breadcrumb">Ürün merkezi <span>/</span><strong>{breadcrumb}</strong></div><div className="topbar-actions"><Badge tone={demo ? 'purple' : s.mode === 'api' ? 'success' : 'neutral'}>{demo ? 'Örnek veri' : s.mode === 'api' ? 'Canlı API' : 'Bağlantı kapalı'}</Badge><button className="icon-button" aria-label="Veri kaynağı" onClick={store.openConnection}>⚙</button></div></header>
    <main id="main" tabIndex={-1}><div className="mode-banner" data-mode={demo ? 'demo' : 'api'} role="status"><span className="banner-symbol">{demo ? '◉' : '◎'}</span><div><strong>{demo ? 'Örnek veri — gerçek cihazlara bağlı değil' : s.mode === 'api' ? 'Mevcut platform · salt okunur' : 'Veri kaynağı seçilmedi'}</strong><span>{demo ? s.scenario === 'normal' ? 'Şirketler, cihazlar ve işlem kayıtları kurgusaldır.' : s.scenario === 'empty' ? 'Boş envanter örnek senaryosu.' : 'Bağlantı hatası örnek senaryosu; gerçek bağlantı denenmedi.' : 'Ürün beyanları bağımsız doğrulanmış koruma göstermez.'}</span></div><button className="text-button" onClick={store.openConnection}>Veri kaynağı ↗</button></div>
      <section className="page-heading"><div><p className="eyebrow">{s.tenant?.name || 'OPERASYON GÖRÜNÜMÜ'}</p><h1>{title}</h1><p>{subtitle}</p></div><div className="heading-actions"><span className="refresh-caption">{s.lastRead && `Konsol okuması ${formatDate(s.lastRead)}`}</span><button className="btn btn-primary" disabled={s.loading || s.busy || s.auditStatus === 'loading'} onClick={() => void store.reload()}><Icon name="refresh" />Yenile</button></div></section>
      {s.error && <div className="page-message" role="alert">{s.error}</div>}
      {(s.view === 'overview' || s.view === 'devices') && <Metrics />}
      {s.view === 'overview' ? <div className="overview-grid"><DeviceList /><div className="side-stack"><Attention /><Catalog /></div></div> : s.view === 'devices' ? <DeviceList /> : s.view === 'products' ? <><ProductCards /><div className="panel product-page-note"><p>Ürün beyanlarını görmek için bir cihazın ayrıntısını açın. Bu görünüm, cihazlarda kurulum veya aktif koruma kanıtı değildir.</p><button className="btn btn-ghost" onClick={() => store.navigate('devices')}>Cihazlara git ↗</button></div></>
        : !admin ? <section className="panel empty-state"><h2>İşlem geçmişi yönetici rolü gerektirir</h2><p>{s.tenant ? 'Bu şirket için görüntüleyici rolündesiniz. Rol, API’nin şirket yanıtından gelir.' : 'Önce erişilebilen bir şirket seçin.'}</p></section> : <AuditView page={s.audit} tenantName={s.tenant?.name} status={s.auditStatus} errorMessage={s.auditError} onNext={(offset) => void store.loadAudit(offset)} onPrev={s.auditOffset > 0 ? () => void store.loadAudit(Math.max(0, s.auditOffset - (demo ? 5 : 50))) : undefined} />}
      <footer className="page-footer"><span><span className="footer-dot" />Salt okunur görünürlük</span><span>Güncel bildirim, doğrulanmış koruma anlamına gelmez.</span></footer>
    </main></div></div>
    <Modal open={s.detailOpen} onClose={store.closeDevice} className="detail-dialog" label="Cihaz ayrıntıları">{s.detailBusy ? <div className="empty-state" role="status">Cihaz ayrıntıları yükleniyor…</div> : s.detailError ? <div className="empty-state"><p role="alert">{s.detailError}</p><button className="btn btn-ghost" onClick={store.closeDevice}>Kapat</button></div> : <DeviceDetail detail={s.detail} onClose={store.closeDevice} />}</Modal>
    <ConnectionPanel /></>;
}
