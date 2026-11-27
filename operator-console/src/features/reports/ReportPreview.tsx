import type { ReactNode } from "react";
import type { ReportAgentMetricKey, ReportMetricKey, ReportModel } from "./reportModel";
import { AGENT_FIELD_LABELS, agentStateLabel, agentStatusLabel, isAgentStateField, ruleFileLabel,
  sensorErrorAbsentLabel } from "../agentLabels";
import { translate } from "../../i18n";
import type { Locale } from "../../i18n/types";
import { LanguageSelect } from "../../i18n/LocaleProvider";
import { booleanLabel, formatCount, formatDate } from "../../i18n/formatters";
import "./print.css";

type PrintableDevice = ReportModel["records"][number];
type PrintableProduct = PrintableDevice["products"][number];
type PrintableMetric = PrintableProduct["metrics"][number];
type ReportRow = readonly [label: string, value: ReactNode];

function isAgentMetric(key: ReportMetricKey): key is ReportAgentMetricKey {
  return Object.hasOwn(AGENT_FIELD_LABELS, key);
}
/** The device-detail card's wording for each agent value. null is "not supplied": never 0, absent or stopped. */
function agentValue(product: PrintableProduct, key: ReportAgentMetricKey, value: PrintableMetric["value"], locale: Locale): ReactNode {
  if (key === "sensor_error_code") return typeof value === "string" ? <code>{value}</code>
    : translate(locale, sensorErrorAbsentLabel(product.metrics.find((row) => row.key === "sensor_state")?.value));
  if (value === null) return translate(locale, "report.notSupplied");
  if (key === "rule_file_present") return translate(locale, ruleFileLabel(value));
  if (isAgentStateField(key)) return translate(locale, agentStateLabel(key, value));
  if (key === "agent_started_at" || key === "isolation_until" || key === "isolation_checked_at")
    return formatDate(typeof value === "string" ? value : null, locale);
  if (key === "heartbeat_interval_seconds" && typeof value === "number")
    return translate(locale, "product.edrV3.seconds", formatCount(value, locale), value);
  if (key === "rule_set_id") return <code>{String(value)}</code>;
  return typeof value === "number" ? formatCount(value, locale) : String(value);
}

function metric(item: PrintableMetric, locale: Locale): string {
  const value = item.value;
  if (item.key === "firewall_mode") return value === "enforce" ? translate(locale, "report.value.enforce")
    : value === "sniff" ? translate(locale, "report.value.sniff") : translate(locale, "report.unknown");
  if (item.key === "report_presence") return value === "present" ? translate(locale, "report.value.present")
    : value === "none" ? translate(locale, "report.value.none") : translate(locale, "report.unknown");
  if (item.key === "availability" || item.key === "execution_available") return value === "unavailable" || value === false
    ? translate(locale, "report.value.unavailable") : translate(locale, "report.unknown");
  if (typeof value === "number") return formatCount(value, locale);
  if (typeof value === "boolean") return booleanLabel(value, locale);
  return value ?? translate(locale, "report.notSupplied");
}
function clockState(observation: PrintableDevice["sourceObservation"] | null, locale: Locale): string {
  if (!observation || observation.clock_state === "unknown") return translate(locale, "report.notSupplied");
  return observation.clock_state === "future" ? translate(locale, "report.clockFuture") : translate(locale, "report.clockNotVerified");
}
function ReportTable({ rows }: { rows: readonly ReportRow[] }) {
  return <table className="report-product-table"><tbody>{rows.map(([label, value], index) =>
    <tr key={index}><th scope="row">{label}</th><td>{value}</td></tr>
  )}</tbody></table>;
}
function productStatus(product: PrintableProduct, locale: Locale): string {
  if (product.presence === "missing") return translate(locale, "report.missingProduct");
  if (product.product === "hostbasedfirewall") {
    switch (product.status) {
      case "running": return translate(locale, "report.status.running");
      case "observing": return translate(locale, "report.status.observing");
      case "degraded": return translate(locale, "report.status.degraded");
      case "stopped": return translate(locale, "report.status.stopped");
      case "unavailable": return translate(locale, "report.status.unavailable");
      default: return translate(locale, "report.unknown");
    }
  }
  if (product.product === "termivar") return product.status === "experimental"
    ? translate(locale, "report.status.experimental") : translate(locale, "report.unknown");
  if (product.product === "edr_agent") return translate(locale, agentStatusLabel(product.status));
  return product.status === "planned" ? translate(locale, "report.status.planned") : translate(locale, "report.antivirusUnknown");
}
function ProductSection({ product, locale }: { product: PrintableProduct; locale: Locale }) {
  const present = product.presence === "reported";
  const agent = product.product === "edr_agent";
  // Snapshot V3 is the agent state with rule_set_state (normalize.ts isEdrAgentStateV3).
  const agentV3 = agent && product.metrics.some((row) => row.key === "rule_set_state");
  // Every value the agent reported about itself carries its claim, not only the source and verification rows.
  const claim = (value: ReactNode): ReactNode => agent && present
    ? <>{value}<span className="report-claim">{translate(locale, "report.agentClaim")}</span></> : value;
  const rows: ReportRow[] = [
    [translate(locale, "report.reportStatus"), claim(productStatus(product, locale))],
    [translate(locale, "report.version"), claim(product.version ?? translate(locale, "report.notSupplied"))],
  ];
  if (present) {
    rows.push([translate(locale, "report.sourceObservedAt"), claim(formatDate(product.sourceObservedAt, locale))],
      [translate(locale, "report.receivedAt"), formatDate(product.receivedAt, locale)],
      [translate(locale, "report.sourceClockAtRead"), clockState(product.observation, locale)],
      [translate(locale, "report.source"), translate(locale, "report.deviceReported")],
      [translate(locale, "report.verification"), translate(locale, "report.notVerified")]);
    if (product.product === "termivar") rows.push([translate(locale, "report.importedAt"), formatDate(product.reportImportedAt, locale)],
      [translate(locale, "report.importClockAtRead"), clockState(product.reportImportAge, locale)]);
    for (const item of product.metrics) rows.push(isAgentMetric(item.key)
      ? [translate(locale, AGENT_FIELD_LABELS[item.key]), claim(agentValue(product, item.key, item.value, locale))]
      : [translate(locale, `report.metric.${item.key}`), metric(item, locale)]);
  }
  return <section className="report-product-section">
    <h3>{translate(locale, `report.product.${product.product}`)}</h3><ReportTable rows={rows}/>
    {!present && <p className="report-trust-note">{translate(locale, "report.missingProductNote")}</p>}
    {product.product === "termivar" && <p className="report-trust-note">{translate(locale, "report.termivarNote")}</p>}
    {product.product === "antivirus" && <p className="report-trust-note">{translate(locale, "report.antivirusNote")}</p>}
    {/* The agent's note covers its marked values, so a missing agent has none; V3 also keeps the card's scan note and
      its response note (the console sends the agent no actions). */}
    {agent && present && <p className="report-trust-note">{translate(locale, "report.agentNote")}</p>}
    {agentV3 && <p className="report-trust-note">{translate(locale, "product.edrV3.scanNote")}</p>}
    {agentV3 && <p className="report-trust-note">{translate(locale, "product.edrV3.responseScope")}</p>}
    {agent && present && <p className="report-trust-note">
      {translate(locale, agentV3 ? "product.edrV3.countersScope" : "product.edr.countersScope")}</p>}
  </section>;
}
function DeviceSection({ device, ordinal, locale, exampleNotice, includeIdentifiers }: {
  device: PrintableDevice; ordinal: number; locale: Locale; exampleNotice: string | null; includeIdentifiers: boolean;
}) {
  return <section className="report-device">
    <header className="report-device-heading">
      {exampleNotice && <p className="report-source-label">{exampleNotice}</p>}
      <p>{translate(locale, "report.selectedDevice", formatCount(ordinal, locale))}</p><h2>{device.label}</h2>
      {includeIdentifiers && device.identifier && <p>{translate(locale, "report.deviceIdentifier", device.identifier)}</p>}
    </header>
    <ReportTable rows={[
      [translate(locale, "report.registrationAtSelection"), device.identityStatus === "revoked"
        ? translate(locale, "report.registrationRevoked") : device.identityStatus === "active"
          ? translate(locale, "report.registrationActive") : translate(locale, "report.unknown")],
      [translate(locale, "report.connectionFreshness"), translate(locale, `report.connection.${device.connectionStatus}`)],
      [translate(locale, "report.revokedAt"), device.revokedAt ? formatDate(device.revokedAt, locale) : translate(locale, "report.revocationNotSupplied")],
      [translate(locale, "report.deviceObservedAt"), formatDate(device.sourceObservedAt, locale)],
      [translate(locale, "report.sourceClockAtRead"), clockState(device.sourceObservation, locale)],
      [translate(locale, "report.receivedAt"), formatDate(device.receivedAt, locale)],
      [translate(locale, "report.consoleReadAt"), formatDate(device.readAt, locale)],
      [translate(locale, "report.source"), translate(locale, "report.deviceReported")],
      [translate(locale, "report.verification"), translate(locale, "report.notVerified")],
    ]}/>
    <p className="report-trust-note">{translate(locale, "report.revocationNote")}</p>
    {device.products.map((product, index) => <ProductSection key={index} product={product} locale={locale}/>)}
  </section>;
}
export interface ReportPreviewProps { report: ReportModel; onBack?: () => void; onPrint?: () => void }

/** Every printable string uses the model's fixed locale, never current context. */
export function ReportPreview({ report, onBack, onPrint }: ReportPreviewProps) {
  const locale = report.locale;
  const example = report.mode === "example";
  if (!report.records.length) return <section className="report-preview" lang={locale}><div className="report-empty">
    <h2>{translate(locale, "report.noPreviewTitle")}</h2><p>{translate(locale, "report.noPreviewDescription")}</p>
    {onBack && <button type="button" className="btn btn-ghost report-controls" onClick={onBack}>{translate(locale, "report.back")}</button>}
  </div></section>;
  return <section className="report-preview" lang={locale}>
    <div className="report-controls">
      <div>{onBack && <button type="button" className="btn btn-ghost" onClick={onBack}>{translate(locale, "report.back")}</button>}
        <button type="button" className="btn btn-primary" disabled={!onPrint} onClick={onPrint}>{translate(locale, "report.print")}</button>
        <LanguageSelect/></div>
      <p>{translate(locale, "report.printHelp")}</p>
    </div>
    <article className="report-document" aria-label={translate(locale, "report.documentAria")}>
      <p className="report-print-source">{example ? report.exampleNotice : translate(locale, "report.apiSourceNotice")}</p>
      <header className="report-header">
        <h1>{report.title}</h1>
        {example && <p className="report-source-label">{report.exampleNotice}</p>}
        <dl className="report-meta">
          <div><dt>{translate(locale, "report.organization")}</dt><dd>{report.tenant.label}</dd></div>
          {report.includeIdentifiers && report.tenant.identifier && <div><dt>{translate(locale, "report.organizationIdentifier")}</dt><dd>{report.tenant.identifier}</dd></div>}
          <div><dt>{translate(locale, "report.dataMode")}</dt><dd>{example ? translate(locale, "report.modeExampleShort") : translate(locale, "report.modeApiShort")}</dd></div>
          <div><dt>{translate(locale, "report.selectedCount")}</dt><dd>{formatCount(report.selectedCount, locale)}</dd></div>
          <div><dt>{translate(locale, "report.generatedAt")}</dt><dd>{formatDate(report.generatedAt, locale)}</dd></div>
        </dl>
        <p className="report-scope-note">{report.scopeNote}</p>
        <p className="report-scope-note">{translate(locale, "report.timestampNote")}</p>
      </header>
      {report.records.map((device, index) => <DeviceSection key={index} device={device} ordinal={index + 1} locale={locale}
        exampleNotice={report.exampleNotice} includeIdentifiers={report.includeIdentifiers}/>)}
      <footer className="report-footer">{translate(locale, "report.footer")}</footer>
    </article>
  </section>;
}
