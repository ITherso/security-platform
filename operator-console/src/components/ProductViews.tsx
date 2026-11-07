import type { ReactNode } from "react";
import type { AuditPage, DeviceDetail as DeviceDetailDto, ProductRecord, TermivarSummary } from "../data/contracts";
import { booleanLabel, displayText, formatAge, formatCount, formatDate, shortIdentifier } from "./display";

type Tone = "success" | "warning" | "danger" | "neutral" | "purple";
type ProductId = ProductRecord["product_id"];
type FirewallRecord = Extract<ProductRecord, { product_id: "hostbasedfirewall" }>;
type TermivarRecord = Extract<ProductRecord, { product_id: "termivar" }>;
type AntivirusRecord = Extract<ProductRecord, { product_id: "antivirus" }>;
type DisplayPair = readonly [label: string, value: ReactNode];

const PRODUCT_LABELS: Readonly<Record<ProductId, string>> = {
  hostbasedfirewall: "HostBasedFirewall", termivar: "Termivar", antivirus: "Antivirüs",
};
const ERROR_LABELS: Readonly<Record<string, string>> = {
  config_error: "Yapılandırma", policy_error: "Politika", temp_error: "Geçici engeller",
  runtime_error: "Motor", telemetry_error: "Telemetri", history_error: "Geçmiş",
  network_profile_error: "Ağ profili", recovery_error: "Yapılandırma kurtarma",
  application_rule_recovery_error: "Uygulama kuralı kurtarma", liveness_error: "Süreç canlılığı",
  application_usage_error: "Uygulama kullanımı", maintenance: "Bakım",
  health_unavailable: "Sağlık bilgisi yok", unknown_error: "Tanımsız bildirim",
};
const AUDIT_ACTIONS: Readonly<Record<string, string>> = {
  tenant_created: "Organizasyon oluşturuldu", membership_set: "Üyelik güncellendi",
  membership_revoked: "Üyelik iptal edildi", enrollment_grant_created: "Kayıt hakkı oluşturuldu",
  enrollment_grant_revoked: "Kayıt hakkı iptal edildi", device_enrolled: "Cihaz kaydedildi",
  device_revoked: "Cihaz kaydı iptal edildi", device_credential_rotated: "Cihaz kimliği yenilendi",
};
const ACTOR_LABELS: Readonly<Record<string, string>> = {
  operator: "Operatör", device: "Cihaz", local_admin: "Yerel yönetici",
};
const OBJECT_LABELS: Readonly<Record<string, string>> = {
  tenant: "Organizasyon", membership: "Üyelik", enrollment_grant: "Kayıt hakkı",
  device: "Cihaz", device_credential: "Cihaz kimliği",
};
const SEVERITIES = [
  ["critical", "Kritik"], ["high", "Yüksek"], ["medium", "Orta"],
  ["low", "Düşük"], ["info", "Bilgi"], ["unassigned", "Atanmamış"],
] as const;

function mapped<T>(values: Readonly<Record<string, T>>, key: string, fallback: T): T {
  return Object.hasOwn(values, key) ? values[key] ?? fallback : fallback;
}

export function Badge({ children, tone = "neutral" }: { children: ReactNode; tone?: Tone }) {
  return <span className="badge" data-tone={tone}>{children}</span>;
}

function KeyValues({ values }: { values: readonly DisplayPair[] }) {
  return <dl className="key-values">{values.map(([label, value]) =>
    <div key={label}><dt>{label}</dt><dd>{value}</dd></div>
  )}</dl>;
}

function Heading({ title, subtitle, eyebrow }: { title: string; subtitle?: string; eyebrow?: string }) {
  return <div className="view-heading">
    {eyebrow && <p className="eyebrow">{eyebrow}</p>}
    <h2>{title}</h2>
    {subtitle && <p className="muted">{subtitle}</p>}
  </div>;
}

function EmptyState({ title, description, role }: {
  title: string; description?: string; role?: "status" | "alert";
}) {
  return <div className="empty-state" role={role}>
    <h3>{title}</h3>{description && <p className="muted">{description}</p>}
  </div>;
}

function ProductHeading({ id, label, tone }: { id: ProductId; label: string; tone: Tone }) {
  return <div className="panel-heading"><h3>{PRODUCT_LABELS[id]}</h3><Badge tone={tone}>{label}</Badge></div>;
}

function MissingProduct({ id, selected }: { id: ProductId; selected: boolean }) {
  const catalog: Record<ProductId, { label: string; tone: Tone; description: string }> = {
    hostbasedfirewall: { label: "Yerel firewall", tone: "neutral", description: "Yerel firewall motorunun bildirilen durumu ve çalışma modu." },
    termivar: { label: "Deneysel", tone: "purple", description: "İçe aktarılmış web değerlendirmelerinin sayısal rapor özeti." },
    antivirus: { label: "Planlanan", tone: "neutral", description: "Antivirüs motoru ve aktif koruma henüz sunulmuyor." },
  };
  const item = catalog[id];
  return <article className="product-card">
    <ProductHeading id={id} label={selected ? "Bildirim yok" : item.label} tone={selected ? "neutral" : item.tone}/>
    <p className="product-description">{item.description}</p>
    <p className="muted">{selected
      ? "Bu cihazın son bildiriminde ürün durumu bulunmuyor. Kurulu olmadığı varsayılmaz."
      : "Bildirilen durumu görmek için bir cihaz seçin."}</p>
  </article>;
}

function FirewallCard({ record }: { record: FirewallRecord }) {
  const state = record.state;
  const statuses: Readonly<Record<string, readonly [string, Tone]>> = {
    running: ["Çalışıyor bildirimi", "success"], observing: ["Yalnız izleme", "purple"],
    degraded: ["Kontrol gerekli", "warning"], stopped: ["Durduruldu bildirimi", "danger"],
    unavailable: ["Kullanılamıyor", "neutral"], unknown: ["Bilinmiyor", "neutral"],
  };
  const [label, tone] = mapped(statuses, state.status, ["Bilinmiyor", "neutral"] as const);
  const mode = mapped({ enforce: "Filtreleme bildiriyor", sniff: "Yalnız izleme", unknown: "Bilinmiyor" }, state.firewall_mode, "Bilinmiyor");
  const errors = state.error_codes;
  const errorText = errors == null ? "Hata bilgisi bilinmiyor." : errors.length
    ? `Bildirilen sorunlar: ${errors.map(code => mapped(ERROR_LABELS, code, "Tanımsız bildirim")).join(" · ")}`
    : "Bu bildirimde hata kodu yok.";
  return <article className="product-card">
    <ProductHeading id="hostbasedfirewall" label={label} tone={tone}/>
    <p className="product-description">Cihazın yerel firewall için bildirdiği son durum.</p>
    <KeyValues values={[
      ["Sürüm", displayText(state.version)], ["Çalışma modu", mode],
      ["Kurulum beyanı", booleanLabel(state.installed)], ["Çalışma beyanı", booleanLabel(state.reported_running)],
      ["Eski bildirim beyanı", booleanLabel(state.reported_stale)],
      ["Merkeze ulaşma", formatDate(record.received_at)], ["Kaynak gözlem yaşı", formatAge(record.observation)],
    ]}/>
    <p className="state-note">{errorText}</p>
  </article>;
}

function SeveritySummary({ report }: { report: TermivarSummary }) {
  const values = report.severity_counts;
  if (!values || SEVERITIES.some(([key]) => !Number.isSafeInteger(values[key]) || values[key] < 0)) {
    return <p className="muted">Önem derecesi dağılımı bilinmiyor.</p>;
  }
  const total = SEVERITIES.reduce((sum, [key]) => sum + values[key], 0);
  if (total === 0) return <p className="muted">Bu raporda kayıt yok.</p>;
  return <div className="severity-legend" role="list" aria-label="Rapordaki önem derecesi kayıt sayıları">
    {SEVERITIES.map(([key, label]) =>
      <span key={key} role="listitem" data-severity={key}>{label} {formatCount(values[key])}</span>
    )}
  </div>;
}

function TermivarCard({ record }: { record: TermivarRecord }) {
  const state = record.state;
  const report = state.latest_report;
  return <article className="product-card">
    <ProductHeading id="termivar" label={state.status === "experimental" ? "Deneysel" : "Bilinmiyor"} tone="purple"/>
    <p className="product-description">İçe aktarılmış değerlendirmenin sayısal rapor özeti.</p>
    <KeyValues values={[
      ["Rapor", mapped({ present: "Özet mevcut", none: "Özet yok", unknown: "Bilinmiyor" }, state.report_presence, "Bilinmiyor")],
      ["Tarayıcı kurulum beyanı", booleanLabel(state.scanner_installed)],
      ["İçe aktarma yaşı", formatAge(record.report_import_age)], ["Kaynak gözlem yaşı", formatAge(record.observation)],
      ["Merkeze ulaşma", formatDate(record.received_at)],
    ]}/>
    {report && state.report_presence === "present" && <>
      <h4>Raporun bildirdiği kayıtlar</h4>
      <KeyValues values={[
        ["Konu", formatCount(report.subject_count)], ["Kayıt", formatCount(report.item_count)],
        ["Bilgi", formatCount(report.counts.informational)], ["İnceleme gerekli", formatCount(report.counts.needs_review)],
        ["Raporda doğrulandı", formatCount(report.counts.confirmed)], ["İçe aktarma", formatDate(report.imported_at)],
      ]}/>
      <SeveritySummary report={report}/>
    </>}
    <p className="state-note">Raporun varlığı tarayıcının kurulu olduğunu göstermez. Raporda doğrulandı işareti bağımsız doğrulama değildir.</p>
  </article>;
}

function AntivirusCard({ record }: { record: AntivirusRecord }) {
  const state = record.state;
  return <article className="product-card">
    <ProductHeading id="antivirus" label={state.status === "planned" ? "Planlanan" : "Bilinmiyor"} tone="neutral"/>
    <p className="product-description">Antivirüs motoru ve aktif koruma henüz sunulmuyor.</p>
    <KeyValues values={[
      ["Kullanılabilirlik", state.availability === "unavailable" ? "Henüz kullanılamıyor" : "Bilinmiyor"],
      ["Merkeze ulaşma", formatDate(record.received_at)], ["Kaynak gözlem yaşı", formatAge(record.observation)],
    ]}/>
    <p className="state-note">Bu kart aktif antivirüs koruması bildirimi değildir.</p>
  </article>;
}

function ProductGrid({ detail }: { detail: DeviceDetailDto | null }) {
  const firewall = detail?.products.find((product): product is FirewallRecord => product.product_id === "hostbasedfirewall");
  const termivar = detail?.products.find((product): product is TermivarRecord => product.product_id === "termivar");
  const antivirus = detail?.products.find((product): product is AntivirusRecord => product.product_id === "antivirus");
  return <div className="product-grid">
    {firewall ? <FirewallCard record={firewall}/> : <MissingProduct id="hostbasedfirewall" selected={detail !== null}/>}
    {termivar ? <TermivarCard record={termivar}/> : <MissingProduct id="termivar" selected={detail !== null}/>}
    {antivirus ? <AntivirusCard record={antivirus}/> : <MissingProduct id="antivirus" selected={detail !== null}/>}
  </div>;
}

export interface ProductCardsProps { detail?: DeviceDetailDto | null }

export function ProductCards({ detail = null }: ProductCardsProps) {
  return <section className="panel">
    <Heading title="Güvenlik ürünleri" eyebrow="ÜRÜN DURUMLARI" subtitle={detail
      ? `${displayText(detail.label, "Seçili cihaz")} için bildirilen son ürün durumları.`
      : "Cihaz seçtiğinizde bildirilen ürün ayrıntıları burada görünür."}/>
    <ProductGrid detail={detail}/>
    {detail && <p className="muted">Kaynak cihaz beyanıdır. Üretici ve koruma durumu bağımsız olarak doğrulanmadı.</p>}
  </section>;
}

export interface DeviceDetailProps { detail: DeviceDetailDto | null; onClose?: () => void; actions?: ReactNode }

export function DeviceDetail({ detail, onClose, actions }: DeviceDetailProps) {
  if (!detail) return <EmptyState title="Cihaz seçilmedi" description="Ayrıntıları görmek için cihaz listesinden bir kayıt seçin."/>;
  const connection: Readonly<Record<string, readonly [string, Tone]>> = {
    recent: ["Yakın zamanda bildirim alındı", "success"], stale: ["Bildirim güncel değil", "warning"],
    never_seen: ["Henüz bildirim alınmadı", "neutral"],
  };
  const [connectionLabel, connectionTone] = mapped(connection, detail.connection_status, ["Bağlantı bilgisi bilinmiyor", "neutral"] as const);
  return <section className="panel">
    <div className="panel-heading">
      <Heading title={displayText(detail.label, "Adsız cihaz")} subtitle={detail.id} eyebrow="CİHAZ AYRINTILARI"/>
      {onClose && <button type="button" className="btn btn-ghost" onClick={onClose} aria-label="Cihaz ayrıntılarını kapat">Kapat</button>}
    </div>
    <div className="detail-actions">
      <Badge tone={detail.identity_status === "revoked" ? "danger" : "neutral"}>{detail.identity_status === "revoked"
        ? "Cihaz kaydı iptal edildi" : detail.identity_status === "active" ? "Cihaz kaydı etkin" : "Kayıt durumu bilinmiyor"}</Badge>
      <Badge tone={connectionTone}>{connectionLabel}</Badge>
    </div>
    {actions}
    <KeyValues values={[
      ["Kayıt tarihi", formatDate(detail.created_at)], ["Son merkeze ulaşma", formatDate(detail.last_received_at)],
      ["Kaynak gözlem zamanı", formatDate(detail.source_observed_at)], ["Kaynak gözlem yaşı", formatAge(detail.source_observation)],
      ["Son bildirim sırası", formatCount(detail.last_sequence)], ["İptal tarihi", detail.revoked_at ? formatDate(detail.revoked_at) : "İptal kaydı yok"],
    ]}/>
    <p className="state-note">Cihaz kaydının etkin olması ve bildirimin yakın zamanda gelmesi, korumanın çalıştığını doğrulamaz. Kaynak zamanı cihazın beyanıdır.</p>
    <h3 className="detail-section">Ürün durumları</h3>
    <ProductGrid detail={detail}/>
    <p className="muted">Durumlar cihaz tarafından bildirildi; bağımsız üretici veya koruma doğrulaması yapılmadı.</p>
  </section>;
}

function AuditReference({ label, value }: { label: string; value: string | null }) {
  return <div className="audit-reference"><span>{label}</span><small className="muted" title={value ?? undefined}>{shortIdentifier(value)}</small></div>;
}

export interface AuditViewProps {
  page: AuditPage | null;
  tenantName?: string;
  status?: "ready" | "loading" | "error" | "idle";
  errorMessage?: string;
  onNext?: (offset: number) => void;
  onPrev?: () => void;
}

export function AuditView({ page, tenantName = "", status = "ready", errorMessage = "", onNext, onPrev }: AuditViewProps) {
  const nextOffset = page?.next_offset ?? null;
  const hasNext = nextOffset !== null && Number.isSafeInteger(nextOffset) && nextOffset >= 0 && nextOffset <= 10000;
  return <section className="panel" aria-busy={status === "loading"}>
    <Heading title="Denetim geçmişi" eyebrow="ETKİNLİKLER" subtitle={tenantName
      ? `${tenantName} için kayıtlı kimlik ve üyelik işlemleri.` : "Organizasyonun kayıtlı kimlik ve üyelik işlemleri."}/>
    {status === "loading" ? <EmptyState title="Etkinlikler yükleniyor…" role="status"/>
      : status === "error" ? <EmptyState title="Etkinlikler alınamadı" role="alert" description={displayText(errorMessage, "Bağlantıyı ve erişim yetkinizi kontrol edin.")}/>
      : status !== "ready" || !page ? <EmptyState title="Etkinlikler henüz yüklenmedi" description="Bir organizasyon seçin ve kayıtları yükleyin."/>
      : <>
        {!page.items.length ? <EmptyState title="Bu sayfada etkinlik yok" description="Yeni kayıt veya başka bir sayfa varsa burada görüntülenir."/>
          : <div className="table-scroll"><table className="data-table">
            <caption className="muted">{displayText(tenantName, "Seçili organizasyon")} denetim kayıtları</caption>
            <thead><tr>{["İşlem", "Nesne", "Gerçekleştiren", "Zaman", "Sonuç"].map(label => <th key={label} scope="col">{label}</th>)}</tr></thead>
            <tbody>{page.items.map(entry => <tr key={entry.id}>
              <td>{mapped(AUDIT_ACTIONS, entry.action, "Bilinmeyen işlem")}</td>
              <td><AuditReference label={mapped(OBJECT_LABELS, entry.object_type, "Nesne")} value={entry.object_id}/></td>
              <td><AuditReference label={mapped(ACTOR_LABELS, entry.actor_type, "Bilinmiyor")} value={entry.actor_id}/></td>
              <td>{formatDate(entry.created_at)}</td>
              <td><Badge tone={entry.outcome === "success" ? "success" : "neutral"}>{entry.outcome === "success" ? "Başarılı" : "Sonuç bilinmiyor"}</Badge></td>
            </tr>)}</tbody>
          </table></div>}
        <div className="audit-pagination">
          <span className="muted">Bu sayfada {formatCount(page.items.length)} kayıt</span>
          <div className="detail-actions">
            <button type="button" className="btn btn-ghost" disabled={!onPrev} onClick={onPrev}>Önceki</button>
            <button type="button" className="btn btn-ghost" disabled={!hasNext || !onNext} onClick={() => {
              if (hasNext && onNext && nextOffset !== null) onNext(nextOffset);
            }}>Sonraki</button>
          </div>
        </div>
        <p className="muted">Bu sayfa yüklenen kayıtları gösterir; tam veya bağımsız doğrulanmış olay geçmişi değildir.</p>
      </>}
  </section>;
}
