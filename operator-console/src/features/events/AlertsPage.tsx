import type { ReactNode } from 'react';
import { ALERT_RULES, ALERT_STATUSES } from '../../data/contracts';
import type { Alert, AlertStatus, Device, DevicePage } from '../../data/contracts';
import type { AlertListView, BadgeTone, LoadStatus } from './eventsModel';
import { MAX_LOADED_ALERTS, RULE_DESCRIPTIONS, RULE_LABELS, SENSOR_STATE_LABELS, SEVERITY_LABELS, SEVERITY_TONES, STATUS_LABELS,
  STATUS_TONES, shortDeviceId } from './eventsModel';
import { AgentStateFieldList, BehaviorFields, PersistenceFields, ScanFields, TamperFields } from './EventFields';
import { formatCount, formatPreciseDate } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';
import './events.css';

export interface AlertsPageProps {
  page: AlertListView | null;
  status: LoadStatus;
  older: boolean;
  errorMessage: string;
  tenantSelected: boolean;
  statusFilter: AlertStatus | 'all';
  deviceFilter: string | null;
  devices: DevicePage | null;
  /** Why the optional device-label read failed; empty when it succeeded. */
  labelsErrorMessage: string;
  onStatusFilterChange: (value: string) => void;
  onDeviceFilterChange: (value: string) => void;
  onOlder: () => void;
  onOpenDevice: (deviceId: string) => void;
}

const COLUMNS = ['alerts.column.severity', 'alerts.column.rule', 'alerts.column.device', 'alerts.column.occurrences',
  'alerts.column.firstSeen', 'alerts.column.lastSeen', 'alerts.column.evidence', 'alerts.column.status'] as const;

function Badge({ children, tone }: { children: ReactNode; tone: BadgeTone }) {
  return <span className="badge" data-tone={tone}>{children}</span>;
}
function Instant({ value }: { value: string }) {
  const { locale } = useLocale();
  return <time dateTime={value} title={value}>{formatPreciseDate(value, locale)}</time>;
}
function EvidenceItem({ label, children, path = false }: { label: string; children: ReactNode; path?: boolean }) {
  return <div><dt>{label}</dt><dd className={path ? 'event-path' : undefined}>{children}</dd></div>;
}

/** Exactly the evidence keys of each rule; device-reported values are shown as plain text. */
function Evidence({ alert }: { alert: Alert }) {
  const { locale, t } = useLocale();
  if (alert.rule === 'user_writable_launch') return <dl className="alert-evidence">
    <EvidenceItem label={t('alerts.evidence.image')} path>{alert.evidence.image}</EvidenceItem>
    <EvidenceItem label={t('alerts.evidence.pid')}>{String(alert.evidence.pid)}</EvidenceItem>
  </dl>;
  if (alert.rule === 'office_browser_spawned_tool') return <dl className="alert-evidence">
    <EvidenceItem label={t('alerts.evidence.image')} path>{alert.evidence.image}</EvidenceItem>
    <EvidenceItem label={t('alerts.evidence.pid')}>{String(alert.evidence.pid)}</EvidenceItem>
    <EvidenceItem label={t('alerts.evidence.parentImage')} path>{alert.evidence.parent_image}</EvidenceItem>
    <EvidenceItem label={t('alerts.evidence.parentPid')}>{String(alert.evidence.parent_pid)}</EvidenceItem>
  </dl>;
  if (alert.rule === 'sensor_unstable') return <dl className="alert-evidence">
    <EvidenceItem label={t('alerts.evidence.state')}>{t(SENSOR_STATE_LABELS[alert.evidence.state])}</EvidenceItem>
    <EvidenceItem label={t('alerts.evidence.errorCode')}>{alert.evidence.error_code === null ? t('alerts.evidence.noErrorCode')
      : <code className="event-code">{alert.evidence.error_code}</code>}</EvidenceItem>
  </dl>;
  if (alert.rule === 'event_loss') return <p className="alert-evidence-text">
    {t('alerts.evidence.missing', formatCount(alert.evidence.missing_events, locale), alert.evidence.missing_events)}</p>;
  // The five Stage 3 event rules carry the triggering event's own fields under the same names.
  if (alert.rule === 'scan_detection') return <ScanFields fields={alert.evidence} />;
  if (alert.rule === 'behavior_match') return <BehaviorFields fields={alert.evidence} />;
  if (alert.rule === 'persistence_added') return <PersistenceFields fields={alert.evidence} />;
  if (alert.rule === 'capability_down') return <AgentStateFieldList fields={alert.evidence} />;
  if (alert.rule === 'tamper_signal') return <TamperFields fields={alert.evidence} />;
  // agent_silent: the server's own record of the device's last contact, and the threshold the sweep used.
  return <dl className="alert-evidence">
    <EvidenceItem label={t('alerts.evidence.lastReceived')}><Instant value={alert.evidence.last_received_at} /></EvidenceItem>
    <EvidenceItem label={t('alerts.evidence.threshold')}>
      {t('alerts.evidence.seconds', formatCount(alert.evidence.threshold_seconds, locale), alert.evidence.threshold_seconds)}</EvidenceItem>
  </dl>;
}

/** The rule's label; agent_silent names the device's last contact time (the server's). */
function RuleLabel({ alert }: { alert: Alert }) {
  const { locale, t } = useLocale();
  return <strong>{alert.rule === 'agent_silent'
    ? t('alerts.rule.agent_silent.since', formatPreciseDate(alert.evidence.last_received_at, locale))
    : t(RULE_LABELS[alert.rule])}</strong>;
}

/** An event rule's row names the matched event sequences; agent_silent comes from the sweep and has none. */
function SeenAt({ at, sequence }: { at: string; sequence: number | null }) {
  const { t } = useLocale();
  return <><Instant value={at} /><span className="cell-sub">{sequence === null ? t('alerts.sweep')
    : t('alerts.sequence', String(sequence))}</span></>;
}

/** Read-only alert list: filters and "Older" are explicit reads; there is no acknowledge or close control. */
export function AlertsPage({ page, status, older, errorMessage, tenantSelected, statusFilter, deviceFilter, devices,
  labelsErrorMessage, onStatusFilterChange, onDeviceFilterChange, onOlder, onOpenDevice }: AlertsPageProps) {
  const { locale, t } = useLocale();
  const deviceItems: readonly Device[] = devices?.items ?? [];
  const labels = new Map(deviceItems.map((device) => [device.id, device.label] as const));
  const loaded = page?.items.length ?? 0;
  const full = loaded >= MAX_LOADED_ALERTS;
  const busy = status === 'loading' || older;
  return <div className="alerts-page">
    <section className="panel alerts-boundary" aria-labelledby="alerts-boundary-title">
      <h2 id="alerts-boundary-title">{t('alerts.diagnosis.title')}</h2>
      <p>{t('alerts.diagnosis.note')}</p>
      <p className="alerts-read-only">{t('alerts.readOnly')}</p>
      <details className="alert-rules">
        <summary>{t('alerts.rules.title')}</summary>
        <dl>{ALERT_RULES.map((rule) => <div key={rule}>
          <dt>{t(RULE_LABELS[rule])} <code>{rule}</code></dt><dd>{t(RULE_DESCRIPTIONS[rule])}</dd></div>)}</dl>
      </details>
    </section>
    <section className="panel" aria-busy={busy}>
      <div className="panel-heading">
        <div><p className="eyebrow">{t('alerts.list.eyebrow')}</p><h2>{t('alerts.list.title')}</h2><p>{t('alerts.list.subtitle')}</p></div>
        <Badge tone="neutral">{t('app.claim.device')} · {t('app.claim.notVerified')}</Badge>
      </div>
      <div className="list-toolbar">
        <select className="filter-select" aria-label={t('alerts.filter.status')} value={statusFilter} disabled={!tenantSelected || busy}
          onChange={(event) => onStatusFilterChange(event.target.value)}>
          <option value="all">{t('alerts.filter.statusAll')}</option>
          {ALERT_STATUSES.map((value) => <option key={value} value={value}>{t(STATUS_LABELS[value])}</option>)}
        </select>
        <select className="filter-select alerts-device-filter" aria-label={t('alerts.filter.device')} value={deviceFilter ?? ''}
          disabled={!tenantSelected || busy} onChange={(event) => onDeviceFilterChange(event.target.value)}>
          <option value="">{t('alerts.filter.deviceAll')}</option>
          {deviceFilter !== null && !labels.has(deviceFilter)
            && <option value={deviceFilter}>{t('alerts.filter.deviceOther', shortDeviceId(deviceFilter))}</option>}
          {deviceItems.map((device) => <option key={device.id} value={device.id}>
            {t('alerts.filter.deviceOption', device.label, shortDeviceId(device.id))}</option>)}
        </select>
      </div>
      {devices !== null && devices.next_offset !== null
        && <p className="scope-note">{t('alerts.filter.deviceScope', formatCount(deviceItems.length, locale))}</p>}
      {status === 'ready' && labelsErrorMessage
        && <p className="scope-note" role="status">{t('alerts.device.labelsFailed')} {labelsErrorMessage}</p>}
      {status === 'loading' ? <div className="empty-state" role="status">{t('alerts.loading')}</div>
        : status === 'error' ? <div className="empty-state" role="alert"><h3>{t('alerts.error')}</h3>
          <p className="muted">{errorMessage || t('alerts.errorHelp')}</p></div>
          : !tenantSelected ? <div className="empty-state"><h3>{t('alerts.notLoaded')}</h3><p className="muted">{t('alerts.selectTenant')}</p></div>
            : status !== 'ready' || page === null ? <div className="empty-state">{t('alerts.notLoaded')}</div>
              : <>
                {!page.items.length ? <div className="empty-state"><h3>{t('alerts.empty')}</h3><p className="muted">{t('alerts.emptyHelp')}</p></div>
                  : <div className="table-scroll"><table className="data-table alert-table">
                    <caption className="muted">{t('alerts.caption')}</caption>
                    <thead><tr>{COLUMNS.map((key) => <th key={key} scope="col">{t(key)}</th>)}</tr></thead>
                    <tbody>{page.items.map((alert) => {
                      const label = labels.get(alert.device_id);
                      const name = label ?? shortDeviceId(alert.device_id);
                      return <tr key={alert.id}>
                        <td><Badge tone={SEVERITY_TONES[alert.severity]}>{t(SEVERITY_LABELS[alert.severity])}</Badge></td>
                        <td className="alert-rule-cell"><RuleLabel alert={alert} /><span className="cell-sub"><code>{alert.rule}</code></span></td>
                        <td><button type="button" className="device-link" onClick={() => onOpenDevice(alert.device_id)}
                          aria-label={t('alerts.device.open', name)}>{name}</button>
                          <span className="device-sub">{label === undefined ? t('alerts.device.unlisted') : shortDeviceId(alert.device_id)}</span></td>
                        <td>{formatCount(alert.occurrences, locale)}</td>
                        <td><SeenAt at={alert.first_seen_at} sequence={alert.first_event_seq} /></td>
                        <td><SeenAt at={alert.last_seen_at} sequence={alert.last_event_seq} /></td>
                        <td className="alert-evidence-cell"><Evidence alert={alert} /></td>
                        <td><div className="status-stack"><Badge tone={STATUS_TONES[alert.status]}>{t(STATUS_LABELS[alert.status])}</Badge>
                          {alert.acknowledged_at !== null
                            && <span className="cell-sub">{t('alerts.acknowledgedAt', formatPreciseDate(alert.acknowledged_at, locale))}</span>}
                          {alert.closed_at !== null
                            && <span className="cell-sub">{t('alerts.closedAt', formatPreciseDate(alert.closed_at, locale))}</span>}</div></td>
                      </tr>;
                    })}</tbody>
                  </table></div>}
                <div className="audit-pagination">
                  <span className="muted">{t('alerts.loaded', formatCount(loaded, locale), loaded)}</span>
                  {page.nextBefore === null ? <span className="muted">{t('alerts.end')}</span>
                    : full ? <span className="muted">{t('alerts.limit', formatCount(MAX_LOADED_ALERTS, locale))}</span>
                      : <button type="button" className="btn btn-ghost" disabled={busy} onClick={onOlder}>
                        {t(older ? 'alerts.olderLoading' : 'alerts.older')}</button>}
                </div>
                {errorMessage && <p className="inline-error event-inline-error" role="alert">{t('alerts.olderFailed')} {errorMessage}</p>}
              </>}
      <p className="scope-note">{t('alerts.scope')}</p>
    </section>
  </div>;
}
