import type { ReportDraft } from "./reportModel";
import { formatDate, formatCount } from "../../components/display";
import "./print.css";

export interface ReportPageProps {
  draft: ReportDraft;
  showIdentifiers?: boolean;
  message?: string;
  onShowIdentifiersChange: (include: boolean) => void;
  onRemove: (deviceId: string) => void;
  onClear: () => void;
  onPreview: () => void;
  onBrowseDevices?: () => void;
}

export function ReportPage({ draft, showIdentifiers = false, message = "",
  onShowIdentifiersChange, onRemove, onClear, onPreview, onBrowseDevices }: ReportPageProps) {
  const first = draft.records[0];
  const example = draft.context?.mode === "example";
  return <section className="panel report-draft">
    <div className="report-draft-heading">
      <div><p className="eyebrow">DURUM RAPORU</p><h2>Seçili cihazların bildirimleri</h2>
        <p className="muted">İncelediğiniz cihazları seçin, raporun kapsamını gözden geçirin ve önizleyin.</p></div>
      <span className="badge" data-tone="purple">{formatCount(draft.records.length)} / 20 cihaz</span>
    </div>
    {message && <p className="report-message" role="status">{message}</p>}
    {!draft.records.length ? <div className="report-empty">
      <h3>Taslakta henüz cihaz yok</h3>
      <p>Bir cihazın ayrıntısını açın ve “Durum raporuna ekle”yi seçin. Yalnız gerçekten görüntülediğiniz bilgiler rapora alınır.</p>
      {onBrowseDevices && <button type="button" className="btn btn-primary" onClick={onBrowseDevices}>Cihazlara git</button>}
    </div> : <>
      <div className="report-scope">
        <p><strong>Kurum:</strong> {first?.tenantName ?? "Seçili kurum"}</p>
        <p><strong>Veri kipi:</strong> {example ? "Örnek veri — gerçek cihazlara bağlı değil" : "Mevcut API’den okunmuş cihaz beyanları"}</p>
        <p>Yalnız seçili cihazları kapsar; tüm kurum envanteri değildir. Kayıtlar farklı konsol okuma zamanlarına ait olabilir.</p>
      </div>
      <ul className="report-draft-list" aria-label="Rapora seçilen cihazlar">
        {draft.records.map((record) => <li key={record.deviceId} className="report-draft-row">
          <div><strong>{record.deviceName}</strong>
            <small>Konsol okuması: {formatDate(record.readAt)}</small>
            <small>Merkeze ulaşma: {formatDate(record.receivedAt)}</small></div>
          <button type="button" className="btn btn-ghost" onClick={() => onRemove(record.deviceId)} aria-label={`${record.deviceName} cihazını rapordan çıkar`}>Çıkar</button>
        </li>)}
      </ul>
      <p className="muted">Seçili bilgiler kendiliğinden yenilenmez. Bir kaydı değiştirmek için cihaz ayrıntısını yeniden açıp rapordaki kaydı güncellemeyi seçin.</p>
      <label className="report-identifier-option">
        <input type="checkbox" checked={showIdentifiers} onChange={(event) => onShowIdentifiersChange(event.target.checked)}/>
        <span>Kurum ve cihaz adlarını/kimliklerini rapora dahil et</span>
      </label>
      <p className="report-identifier-help">Kapalıyken “Seçili kurum”, “Cihaz 01” gibi rapora özel etiketler kullanılır. Ad ve kimlikleri gizlemek anonimleştirme garantisi değildir.</p>
      <div className="report-draft-actions">
        <span className="muted">En fazla 20 cihaz · 256 KiB taslak sınırı</span>
        <div><button type="button" className="btn btn-ghost" onClick={onClear}>Taslağı temizle</button>
          <button type="button" className="btn btn-primary" onClick={onPreview}>Raporu önizle</button></div>
      </div>
    </>}
  </section>;
}
