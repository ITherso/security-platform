import type { ReactNode } from 'react';
import type { TimelineEvent } from '../../data/contracts';
import type { LoadStatus, TimelineView } from './eventsModel';
import { exitCodeText, KIND_LABELS, MAX_TIMELINE_EVENTS, SENSOR_STATE_LABELS, sequenceRange, timelineRows } from './eventsModel';
import { AgentStateFieldList, BehaviorFields, FieldList, Moment, PersistenceFields, ScanFields, TamperFields } from './EventFields';
import { formatCount, formatPreciseDate } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';
import './events.css';

export interface DeviceTimelineProps {
  timeline: TimelineView | null;
  status: LoadStatus;
  older: boolean;
  errorMessage: string;
  onOlder: () => void;
  onRefresh: () => void;
  onShowAlerts: () => void;
}

const COLUMNS = ['events.column.sequence', 'events.column.kind', 'events.column.observed', 'events.column.received',
  'events.column.image', 'events.column.pid', 'events.column.parentPid', 'events.column.exitCode', 'events.column.state',
  'events.column.errorCode', 'events.column.details'] as const;

function NotApplicable() {
  const { t } = useLocale();
  return <><span aria-hidden="true">—</span><span className="sr-only">{t('events.notApplicable')}</span></>;
}

/** UTC presentation with seconds; the exact stored text stays in the machine-readable attribute. */
function Instant({ value }: { value: string }) {
  const { locale } = useLocale();
  return <time dateTime={value} title={value}>{formatPreciseDate(value, locale)}</time>;
}

/** Each kind fills only the fields it has; the rest are marked as not part of that kind. A process image and PID go
 * in their columns; every other field of a kind is in its details, under the field's own name. A v1 row has no v2
 * field and shows it as not reported. Only scan_detected has a SHA-256 (ScanFields). */
function EventRow({ event }: { event: TimelineEvent }) {
  const { locale, t } = useLocale();
  const none = <NotApplicable />;
  let image: ReactNode = none, pid: ReactNode = none, parentPid: ReactNode = none;
  let exitCode: ReactNode = none, state: ReactNode = none, errorCode: ReactNode = none, details: ReactNode = none;
  switch (event.kind) {
    case 'process_started':
      image = <span className="event-path">{event.image}</span>;
      pid = String(event.pid);
      parentPid = String(event.parent_pid);
      details = <FieldList rows={[['events.field.session_id', String(event.session_id)],
        ['events.field.create_time', <Moment value={event.create_time} />],
        ['events.field.parent_create_time', <Moment value={event.parent_create_time} />]]} />;
      break;
    case 'process_stopped':
      image = event.image === null ? t('events.notReported') : <span className="event-path">{event.image}</span>;
      pid = String(event.pid);
      exitCode = event.exit_code === null ? t('events.notReported') : exitCodeText(event.exit_code);
      details = <FieldList rows={[['events.field.create_time', <Moment value={event.create_time} />]]} />;
      break;
    case 'sensor_state':
      state = t(SENSOR_STATE_LABELS[event.state]);
      errorCode = event.error_code !== null ? <code className="event-code">{event.error_code}</code>
        : event.state === 'lost' || event.state === 'failed' ? t('events.notReported') : none;
      break;
    case 'scan_detected':
      pid = event.pid === null ? t('events.notReported') : String(event.pid);
      details = <ScanFields fields={event} pidShown />;
      break;
    case 'behavior_match':
      image = <span className="event-path">{event.image}</span>;
      pid = String(event.pid);
      details = <BehaviorFields fields={event} processShown />;
      break;
    case 'persistence_change':
      details = <PersistenceFields fields={event} />;
      break;
    case 'agent_state':
      details = <AgentStateFieldList fields={event} />;
      break;
    case 'tamper_signal':
      details = <TamperFields fields={event} />;
      break;
    case 'coverage_gap':
      details = <FieldList rows={[['events.field.gap_source', <code className="event-code">{event.gap_source}</code>],
        ['events.field.reason', <code className="event-code">{event.reason}</code>],
        ['events.field.lost', event.lost === null ? t('events.notReported') : formatCount(event.lost, locale)]]} />;
      break;
  }
  return <tr>
    <td className="event-sequence">{String(event.event_seq)}</td>
    <td>{t(KIND_LABELS[event.kind])}<span className="cell-sub"><code>{event.kind}</code></span></td>
    <td><Instant value={event.observed_at} /></td>
    <td><Instant value={event.received_at} /></td>
    <td className="event-image-cell">{image}</td>
    <td>{pid}</td>
    <td>{parentPid}</td>
    <td>{exitCode}</td>
    <td>{state}</td>
    <td>{errorCode}</td>
    <td className="event-details-cell">{details}</td>
  </tr>;
}

/** Read-only timeline of the open device. Loads happen only through the store's explicit actions. */
export function DeviceTimeline({ timeline, status, older, errorMessage, onOlder, onRefresh, onShowAlerts }: DeviceTimelineProps) {
  const { locale, t } = useLocale();
  const loaded = timeline?.events.length ?? 0;
  const full = loaded >= MAX_TIMELINE_EVENTS;
  const canOlder = status === 'ready' && timeline !== null && timeline.nextBeforeSeq !== null && !older && !full;
  return <section className="panel event-timeline" aria-labelledby="event-timeline-title" aria-busy={status === 'loading' || older}>
    <div className="panel-heading">
      <div><p className="eyebrow">{t('events.timeline.eyebrow')}</p><h3 id="event-timeline-title">{t('events.timeline.title')}</h3>
        <p>{t('events.timeline.subtitle')}</p></div>
      <div className="event-actions">
        <button type="button" className="btn btn-ghost" disabled={status === 'loading'} onClick={onRefresh}>{t('events.timeline.refresh')}</button>
        <button type="button" className="btn btn-ghost" onClick={onShowAlerts}>{t('events.timeline.showAlerts')}</button>
      </div>
    </div>
    <p className="state-note">{t('events.timeline.trust')}</p>
    <p className="event-note">{t('events.timeline.matchNote')}</p>
    {status === 'loading' ? <div className="empty-state" role="status">{t('events.timeline.loading')}</div>
      : status === 'error' ? <div className="empty-state" role="alert"><h4>{t('events.timeline.error')}</h4><p className="muted">{errorMessage}</p></div>
        : status !== 'ready' || timeline === null ? <div className="empty-state">{t('events.timeline.notLoaded')}</div>
          : <>
            <dl className="key-values event-counters">
              <div><dt>{t('events.timeline.capDeleted')}</dt><dd>{formatCount(timeline.capDeletedEvents, locale)}</dd></div>
              <div><dt>{t('events.timeline.suppressed')}</dt><dd>{formatCount(timeline.suppressedAlerts, locale)}</dd></div>
              <div><dt>{t('events.timeline.loadedCount')}</dt><dd>{formatCount(loaded, locale)}</dd></div>
              <div><dt>{t('events.timeline.readAt')}</dt><dd><Instant value={timeline.readAt} /></dd></div>
            </dl>
            <p className="event-note">{t('events.timeline.countsNote')}</p>
            {!timeline.events.length ? <div className="empty-state">{t('events.timeline.empty')}</div>
              : <div className="table-scroll"><table className="data-table event-table">
                <caption className="muted">{t('events.timeline.caption')}</caption>
                <thead><tr>{COLUMNS.map((key) => <th key={key} scope="col">{t(key)}</th>)}</tr></thead>
                <tbody>{timelineRows(timeline.events).map((row) => row.type === 'gap'
                  ? <tr key={`gap-${String(row.to)}`} className="event-gap"><td colSpan={COLUMNS.length}>
                    {t('events.timeline.gap', formatCount(row.missing, locale), row.missing, sequenceRange(row.from, row.to))}</td></tr>
                  : <EventRow key={`event-${String(row.event.event_seq)}`} event={row.event} />)}</tbody>
              </table></div>}
            <div className="audit-pagination">
              <span className="muted">{t('events.timeline.loaded', formatCount(loaded, locale), loaded)}</span>
              {timeline.nextBeforeSeq === null ? <span className="muted">{t('events.timeline.end')}</span>
                : full ? <span className="muted">{t('events.timeline.limit', formatCount(MAX_TIMELINE_EVENTS, locale))}</span>
                  : <button type="button" className="btn btn-ghost" disabled={!canOlder} onClick={onOlder}>
                    {t(older ? 'events.timeline.olderLoading' : 'events.timeline.older')}</button>}
            </div>
            {errorMessage && <p className="inline-error event-inline-error" role="alert">{t('events.timeline.olderFailed')} {errorMessage}</p>}
            {timeline.events.length > 0 && <p className="event-note">{t('events.timeline.gapNote')}</p>}
          </>}
  </section>;
}
