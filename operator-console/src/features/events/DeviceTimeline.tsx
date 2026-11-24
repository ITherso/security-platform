import type { ReactNode } from 'react';
import type { TimelineEvent } from '../../data/contracts';
import type { LoadStatus, TimelineView } from './eventsModel';
import { exitCodeText, KIND_LABELS, MAX_TIMELINE_EVENTS, SENSOR_STATE_LABELS, sequenceRange, timelineRows } from './eventsModel';
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
  'events.column.errorCode'] as const;

function NotApplicable() {
  const { t } = useLocale();
  return <><span aria-hidden="true">—</span><span className="sr-only">{t('events.notApplicable')}</span></>;
}

/** UTC presentation with seconds; the exact stored text stays in the machine-readable attribute. */
function Instant({ value }: { value: string }) {
  const { locale } = useLocale();
  return <time dateTime={value} title={value}>{formatPreciseDate(value, locale)}</time>;
}

/** Each kind fills only the fields it has; the rest are marked as not part of that kind. */
function EventRow({ event }: { event: TimelineEvent }) {
  const { t } = useLocale();
  const none = <NotApplicable />;
  let image: ReactNode = none, pid: ReactNode = none, parentPid: ReactNode = none;
  let exitCode: ReactNode = none, state: ReactNode = none, errorCode: ReactNode = none;
  if (event.kind === 'process_started') {
    image = <span className="event-path">{event.image}</span>;
    pid = String(event.pid);
    parentPid = String(event.parent_pid);
  } else if (event.kind === 'process_stopped') {
    image = event.image === null ? t('events.notReported') : <span className="event-path">{event.image}</span>;
    pid = String(event.pid);
    exitCode = event.exit_code === null ? t('events.notReported') : exitCodeText(event.exit_code);
  } else {
    state = t(SENSOR_STATE_LABELS[event.state]);
    errorCode = event.error_code !== null ? <code className="event-code">{event.error_code}</code>
      : event.state === 'lost' || event.state === 'failed' ? t('events.notReported') : none;
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
