import type { ReportDraft } from "./reportModel";
import { formatDate, formatCount } from "../../i18n/formatters";
import { useLocale } from "../../i18n/LocaleProvider";
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
  const { locale, t } = useLocale();
  return <section className="panel report-draft">
    <div className="report-draft-heading">
      <div><p className="eyebrow">{t("report.eyebrow")}</p><h2>{t("report.draftTitle")}</h2>
        <p className="muted">{t("report.draftIntro")}</p></div>
      <span className="badge" data-tone="purple">{t("report.draftCount", formatCount(draft.records.length, locale))}</span>
    </div>
    {message && <p className="report-message" role="status">{message}</p>}
    {!draft.records.length ? <div className="report-empty">
      <h3>{t("report.emptyTitle")}</h3>
      <p>{t("report.emptyDescription")}</p>
      {onBrowseDevices && <button type="button" className="btn btn-primary" onClick={onBrowseDevices}>{t("report.browseDevices")}</button>}
    </div> : <>
      <div className="report-scope">
        <p><strong>{t("report.organization")}:</strong> {first?.tenantName ?? t("report.genericOrganization")}</p>
        <p><strong>{t("report.dataMode")}:</strong> {example ? t("report.modeExample") : t("report.modeApi")}</p>
        <p>{t("report.scopeNote")}</p>
      </div>
      <ul className="report-draft-list" aria-label={t("report.selectedListAria")}>
        {draft.records.map((record) => <li key={record.deviceId} className="report-draft-row">
          <div><strong>{record.deviceName}</strong>
            <small>{t("report.consoleReadValue", formatDate(record.readAt, locale))}</small>
            <small>{t("report.receivedValue", formatDate(record.receivedAt, locale))}</small></div>
          <button type="button" className="btn btn-ghost" onClick={() => onRemove(record.deviceId)} aria-label={t("report.removeDeviceAria", record.deviceName)}>{t("report.remove")}</button>
        </li>)}
      </ul>
      <p className="muted">{t("report.updateNote")}</p>
      <label className="report-identifier-option">
        <input type="checkbox" checked={showIdentifiers} onChange={(event) => onShowIdentifiersChange(event.target.checked)}/>
        <span>{t("report.includeIdentifiers")}</span>
      </label>
      <p className="report-identifier-help">{t("report.identifiersHelp")}</p>
      <div className="report-draft-actions">
        <span className="muted">{t("report.limits")}</span>
        <div><button type="button" className="btn btn-ghost" onClick={onClear}>{t("report.clear")}</button>
          <button type="button" className="btn btn-primary" onClick={onPreview}>{t("report.preview")}</button></div>
      </div>
    </>}
  </section>;
}
