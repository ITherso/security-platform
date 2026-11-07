import type { ReactNode } from "react";
import type { ReportModel } from "./reportModel";
import { booleanLabel, displayText, formatCount, formatDate } from "../../components/display";
import "./print.css";

type PrintableDevice = ReportModel["records"][number];
type PrintableProduct = PrintableDevice["products"][number];
type PrintableMetric = PrintableProduct["metrics"][number];
type ProductId = PrintableProduct["product"];
type ReportRow = readonly [label: string, value: ReactNode];

const EXAMPLE_NOTICE = "ÖRNEK VERİ — GERÇEK CİHAZ RAPORU DEĞİLDİR";
const PRODUCT_LABELS: Record<ProductId, string> = {
  hostbasedfirewall: "HostBasedFirewall", termivar: "Termivar", antivirus: "Antivirüs",
};
const HBF_STATUS: Readonly<Record<string, string>> = {
  running: "Çalışıyor bildirimi", observing: "Yalnız izleme bildirimi", degraded: "Kontrol gerekli",
  stopped: "Durduruldu bildirimi", unavailable: "Kullanılamıyor", unknown: "Bilinmiyor",
};
const CONNECTION_STATUS: Readonly<Record<string, string>> = {
  recent: "Yakın zamanda bildirim alındı", stale: "Bildirim güncel değil", never_seen: "Henüz bildirim alınmadı",
};
const METRIC_LABELS: Readonly<Record<string, string>> = {
  installed: "Kurulum beyanı", reported_running: "Çalışma beyanı", reported_stale: "Kaynağın eski veri bildirimi",
  firewall_mode: "Çalışma modu", scanner_installed: "Tarayıcı kurulum beyanı", execution_available: "Yürütme kullanılabilirliği",
  report_presence: "Rapor özeti", subject_count: "Konu sayısı", item_count: "Kayıt sayısı",
  informational: "Bilgi", needs_review: "İnceleme gerekli", confirmed: "Raporda doğrulandı",
  unassigned: "Önem derecesi atanmamış", info: "Önem derecesi: bilgi", low: "Önem derecesi: düşük",
  medium: "Önem derecesi: orta", high: "Önem derecesi: yüksek", critical: "Önem derecesi: kritik",
  availability: "Ürün kullanılabilirliği",
};

function mapped(values: Readonly<Record<string, string>>, key: string | null, fallback: string): string {
  return key !== null && Object.hasOwn(values, key) ? values[key] ?? fallback : fallback;
}

function metric(item: PrintableMetric): string {
  const value = item.value;
  if (item.key === "firewall_mode") return mapped({ enforce: "Filtreleme bildiriyor", sniff: "Yalnız izleme", unknown: "Bilinmiyor" }, typeof value === "string" ? value : null, "Bilinmiyor");
  if (item.key === "report_presence") return mapped({ present: "Özet mevcut", none: "Özet yok", unknown: "Bilinmiyor" }, typeof value === "string" ? value : null, "Bilinmiyor");
  if (item.key === "availability") return value === "unavailable" ? "Henüz kullanılamıyor" : "Bilinmiyor";
  if (item.key === "execution_available") return value === false ? "Kullanılamıyor" : "Bilinmiyor";
  if (typeof value === "number") return formatCount(value);
  if (typeof value === "boolean") return booleanLabel(value);
  return displayText(value, "Bilinmiyor / sağlanmıyor");
}

function clockState(observation: PrintableDevice["sourceObservation"] | null): string {
  if (!observation || observation.clock_state === "unknown") return "Bilinmiyor / sağlanmıyor";
  if (observation.clock_state === "future") return "Okuma anında kaynak saati ileride olarak bildirildi";
  return "Kaynak saati bağımsız doğrulanmadı";
}

function ReportTable({ rows }: { rows: readonly ReportRow[] }) {
  return <table className="report-product-table"><tbody>{rows.map(([label, value], index) =>
    <tr key={index}><th scope="row">{label}</th><td>{value}</td></tr>
  )}</tbody></table>;
}

function productStatus(product: PrintableProduct): string {
  if (product.presence === "missing") return "Ürün bildirimi yok";
  if (product.product === "hostbasedfirewall") return mapped(HBF_STATUS, product.status, "Bilinmiyor");
  if (product.product === "termivar") return product.status === "experimental" ? "Deneysel rapor özeti" : "Bilinmiyor";
  return product.status === "planned" ? "Planlanan ürün — kullanıma hazır değil" : "Durum bilinmiyor; aktif antivirüs koruması sunulmuyor";
}

function ProductSection({ product }: { product: PrintableProduct }) {
  const present = product.presence === "reported";
  const rows: ReportRow[] = [
    ["Bildirim durumu", productStatus(product)],
    ["Sürüm", displayText(product.version, "Bilinmiyor / sağlanmıyor")],
  ];
  if (present) {
    rows.push(["Kaynak bildirim zamanı", formatDate(product.sourceObservedAt)],
      ["Sunucunun alım zamanı", formatDate(product.receivedAt)],
      ["Kaynak saat bilgisi (okuma anı)", clockState(product.observation)],
      ["Kaynak", "Cihazın bildirdiği"], ["Doğrulama", "Bağımsız doğrulanmadı"]);
    if (product.product === "termivar") rows.push(["Rapor içe aktarma zamanı", formatDate(product.reportImportedAt)],
      ["İçe aktarma saat bilgisi (okuma anı)", clockState(product.reportImportAge)]);
    for (const item of product.metrics) rows.push([mapped(METRIC_LABELS, item.key, item.label), metric(item)]);
  }
  return <section className="report-product-section">
    <h3>{PRODUCT_LABELS[product.product]}</h3>
    <ReportTable rows={rows}/>
    {!present && <p className="report-trust-note">Bu ürünün bilgisi seçilen cihaz bildiriminde bulunmuyor. Eksik veri, ürünün kurulu olmadığı veya koruma sağladığı anlamına gelmez.</p>}
    {product.product === "termivar" && <p className="report-trust-note">Sayısal rapor özeti tarayıcının kurulu veya çalışır olduğunu, merkezden tarama yapıldığını ya da bulguların bağımsız doğrulandığını kanıtlamaz. “Raporda doğrulandı” yalnız raporun kendi işaretidir.</p>}
    {product.product === "antivirus" && <p className="report-trust-note">Planlanan ürün — kullanıma hazır değil. Aktif antivirüs motoru, koruma veya tarama sonucu bildirilmez.</p>}
  </section>;
}

function DeviceSection({ device, ordinal, example, includeIdentifiers }: {
  device: PrintableDevice; ordinal: number; example: boolean; includeIdentifiers: boolean;
}) {
  return <section className="report-device">
    <header className="report-device-heading">
      {example && <p className="report-source-label">{EXAMPLE_NOTICE}</p>}
      <p>Seçili cihaz {formatCount(ordinal)}</p><h2>{device.label}</h2>
      {includeIdentifiers && device.identifier && <p>Cihaz kimliği: {device.identifier}</p>}
    </header>
    <ReportTable rows={[
      ["Seçildiği andaki cihaz kaydı", device.identityStatus === "revoked" ? "Cihaz kaydı iptal edildi"
        : device.identityStatus === "active" ? "Cihaz kaydı etkin" : "Bilinmiyor"],
      ["Bildirim güncelliği", mapped(CONNECTION_STATUS, device.connectionStatus, "Bilinmiyor")],
      ["Kayıt iptal zamanı", device.revokedAt ? formatDate(device.revokedAt) : "İptal zamanı sağlanmıyor"],
      ["Cihazın bildirim zamanı", formatDate(device.sourceObservedAt)],
      ["Kaynak saat bilgisi (okuma anı)", clockState(device.sourceObservation)],
      ["Sunucunun alım zamanı", formatDate(device.receivedAt)],
      ["Konsol okuma zamanı", formatDate(device.readAt)],
      ["Kaynak", "Cihazın bildirdiği"], ["Doğrulama", "Bağımsız doğrulanmadı"],
    ]}/>
    <p className="report-trust-note">Cihaz kaydının iptali firewall’ın durduğu veya kaldırıldığı anlamına gelmez. Güncel bildirim, doğrulanmış koruma değildir.</p>
    {device.products.map((product, index) => <ProductSection key={index} product={product}/>)}
  </section>;
}

export interface ReportPreviewProps {
  report: ReportModel;
  onBack?: () => void;
  onPrint?: () => void;
}

/** Only a sanitized, fixed ReportModel is accepted; no raw DTO or session props. */
export function ReportPreview({ report, onBack, onPrint }: ReportPreviewProps) {
  const example = report.mode === "example";
  if (!report.records.length) return <section className="report-preview"><div className="report-empty">
    <h2>Önizlenecek cihaz yok</h2><p>Yazdırılabilir bir rapor için taslağa cihaz ekleyin.</p>
    {onBack && <button type="button" className="btn btn-ghost report-controls" onClick={onBack}>Düzenlemeye dön</button>}
  </div></section>;
  return <section className="report-preview">
    <div className="report-controls">
      <div>{onBack && <button type="button" className="btn btn-ghost" onClick={onBack}>Düzenlemeye dön</button>}
        <button type="button" className="btn btn-primary" disabled={!onPrint} onClick={onPrint}>Yazdır / PDF olarak kaydet</button></div>
      <p>Tarayıcıda yazıcıyı veya PDF hedefini seçebilirsiniz. Yazdırma penceresinin açılması dosyanın kaydedildiğini göstermez. Üstbilgi ve altbilgi seçenekleri tarayıcıya aittir.</p>
    </div>
    <article className="report-document" aria-label="Seçili cihazlar ürün bildirim özeti">
      <p className="report-print-source">{example ? EXAMPLE_NOTICE : "API’den okunmuş cihaz beyanı — bağımsız doğrulanmadı"}</p>
      <header className="report-header">
        <h1>{report.title}</h1>
        {example && <p className="report-source-label">{EXAMPLE_NOTICE}</p>}
        <dl className="report-meta">
          <div><dt>Kurum</dt><dd>{report.tenant.label}</dd></div>
          {report.includeIdentifiers && report.tenant.identifier && <div><dt>Kurum kimliği</dt><dd>{report.tenant.identifier}</dd></div>}
          <div><dt>Veri kipi</dt><dd>{example ? "Örnek veri" : "Mevcut API’den okunmuş veri"}</dd></div>
          <div><dt>Seçilmiş cihaz sayısı</dt><dd>{formatCount(report.selectedCount)}</dd></div>
          <div><dt>Rapor oluşturulma zamanı</dt><dd>{formatDate(report.generatedAt)}</dd></div>
        </dl>
        <p className="report-scope-note">{report.scopeNote}</p>
        <p className="report-scope-note">Rapor oluşturma zamanı tarayıcı metadata’sıdır. Cihaz bildirim, sunucu alım ve konsol okuma zamanları ayrıdır; kayıtlar aynı anda alınmış merkezi snapshot değildir. Yazdırma kaynak veriyi yenilemez.</p>
      </header>
      {report.records.map((device, index) => <DeviceSection key={index} device={device} ordinal={index + 1}
        example={example} includeIdentifiers={report.includeIdentifiers}/>)}
      <footer className="report-footer">Bu rapor yalnız seçili cihazların bildirim özetidir; tüm kurum envanteri, güvenlik skoru, politika uygulama kanıtı veya uyumluluk sertifikası değildir. Kaydedilen ya da yazdırılan kopyalar bağlantı kapatılınca geri alınamaz.</footer>
    </article>
  </section>;
}
