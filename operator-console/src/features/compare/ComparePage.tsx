import { useState, type ReactNode } from 'react';
import type { ComparableDevice, CompareFieldKey, CompareFieldKind, CompareSection, CompareState } from './compareModel';
import { compareFields } from './compareFields';
import { CompareFieldRow } from './CompareFieldRow';
import { booleanLabel, formatCount, formatDate } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';
import type { CompareTextKey } from '../../i18n/catalogs/compare';
import './compare.css';

export interface ComparePageProps {
  state: CompareState;
  onRemove: (deviceId: string) => void;
  onClear: () => void;
  onBrowseDevices?: () => void;
}

const SECTIONS: readonly [CompareSection, CompareTextKey][] = [
  ['device', 'compare.section.device'], ['hbf', 'compare.section.hostbasedfirewall'],
  ['termivar', 'compare.section.termivar'], ['antivirus', 'compare.section.antivirus'],
];
const SECTION_NOTES: Readonly<Record<CompareSection, CompareTextKey>> = {
  device: 'compare.sectionNote.device', hbf: 'compare.sectionNote.hbf',
  termivar: 'compare.sectionNote.termivar', antivirus: 'compare.sectionNote.antivirus',
};
const FIELD_LABELS: Readonly<Record<CompareFieldKey, CompareTextKey>> = {
  'device.registration': 'compare.field.device.registration',
  'device.connection': 'compare.field.device.connection',
  'device.received_at': 'compare.field.device.received_at',
  'device.observed_at': 'compare.field.device.observed_at',
  'device.read_at': 'compare.field.device.read_at',
  'device.revoked_at': 'compare.field.device.revoked_at',
  'device.source': 'compare.field.device.source',
  'device.verification': 'compare.field.device.verification',
  'hbf.status': 'compare.field.hbf.status',
  'hbf.version': 'compare.field.hbf.version',
  'hbf.installed': 'compare.field.hbf.installed',
  'hbf.running': 'compare.field.hbf.running',
  'hbf.stale': 'compare.field.hbf.stale',
  'hbf.mode': 'compare.field.hbf.mode',
  'hbf.received_at': 'compare.field.hbf.received_at',
  'hbf.observed_at': 'compare.field.hbf.observed_at',
  'hbf.source': 'compare.field.hbf.source',
  'hbf.verification': 'compare.field.hbf.verification',
  'termivar.status': 'compare.field.termivar.status',
  'termivar.version': 'compare.field.termivar.version',
  'termivar.scanner_installed': 'compare.field.termivar.scanner_installed',
  'termivar.execution_available': 'compare.field.termivar.execution_available',
  'termivar.report_presence': 'compare.field.termivar.report_presence',
  'termivar.subject_count': 'compare.field.termivar.subject_count',
  'termivar.item_count': 'compare.field.termivar.item_count',
  'termivar.informational': 'compare.field.termivar.informational',
  'termivar.needs_review': 'compare.field.termivar.needs_review',
  'termivar.confirmed': 'compare.field.termivar.confirmed',
  'termivar.unassigned': 'compare.field.termivar.unassigned',
  'termivar.info': 'compare.field.termivar.info',
  'termivar.low': 'compare.field.termivar.low',
  'termivar.medium': 'compare.field.termivar.medium',
  'termivar.high': 'compare.field.termivar.high',
  'termivar.critical': 'compare.field.termivar.critical',
  'termivar.imported_at': 'compare.field.termivar.imported_at',
  'termivar.received_at': 'compare.field.termivar.received_at',
  'termivar.observed_at': 'compare.field.termivar.observed_at',
  'termivar.source': 'compare.field.termivar.source',
  'termivar.verification': 'compare.field.termivar.verification',
  'av.status': 'compare.field.av.status',
  'av.availability': 'compare.field.av.availability',
  'av.execution_available': 'compare.field.av.execution_available',
  'av.received_at': 'compare.field.av.received_at',
  'av.observed_at': 'compare.field.av.observed_at',
  'av.source': 'compare.field.av.source',
  'av.verification': 'compare.field.av.verification',
};
const ENUM_LABELS: Readonly<Record<string, CompareTextKey>> = {
  active: 'compare.value.active', revoked: 'compare.value.revoked', recent: 'compare.value.recent',
  stale: 'compare.value.stale', never_seen: 'compare.value.never_seen', running: 'compare.value.running',
  observing: 'compare.value.observing', degraded: 'compare.value.degraded', stopped: 'compare.value.stopped',
  unavailable: 'compare.value.unavailable', enforce: 'compare.value.enforce', sniff: 'compare.value.sniff',
  experimental: 'compare.value.experimental', planned: 'compare.value.planned', unknown: 'compare.value.unknown',
  present: 'compare.value.present', none: 'compare.value.none', self_reported: 'compare.value.self_reported',
  not_verified: 'compare.value.not_verified', future: 'compare.value.future',
};

function DeviceSlot({ device, side, example, onRemove, onBrowseDevices, hasOne }: {
  device: ComparableDevice | null; side: 'left' | 'right'; example: boolean;
  onRemove: (deviceId: string) => void; onBrowseDevices?: () => void; hasOne: boolean;
}) {
  const { locale, t } = useLocale();
  return <article className={`compare-device${device ? '' : ' compare-device-empty'}`}>
    <div className="compare-slot-heading"><p className="eyebrow">{t(side === 'left' ? 'compare.slot.left' : 'compare.slot.right')}</p>
      {device && <button type="button" className="btn btn-ghost" onClick={() => onRemove(device.deviceId)} aria-label={t('compare.removeAria', device.deviceName)}>{t('compare.remove')}</button>}</div>
    {device ? <>
      <h3>{device.deviceName}</h3>
      {example && <p className="compare-example">{t('compare.example')}</p>}
      <p className="compare-claims">{t('compare.source')} · {t('compare.verification')}</p>
      <dl className="compare-device-times">
        <div><dt>{t('compare.field.device.observed_at')}</dt><dd>{formatDate(typeof device.fields['device.observed_at'] === 'string' ? device.fields['device.observed_at'] : null, locale)}</dd></div>
        <div><dt>{t('compare.field.device.received_at')}</dt><dd>{formatDate(typeof device.fields['device.received_at'] === 'string' ? device.fields['device.received_at'] : null, locale)}</dd></div>
        <div><dt>{t('compare.field.device.read_at')}</dt><dd>{formatDate(typeof device.fields['device.read_at'] === 'string' ? device.fields['device.read_at'] : null, locale)}</dd></div>
      </dl>
    </> : <div className="compare-slot-guidance"><h3>{t('compare.slot.emptyTitle')}</h3><p>{t(hasOne ? 'compare.slot.emptySecond' : 'compare.slot.emptyFirst')}</p>
      {onBrowseDevices && <button type="button" className="btn btn-primary" onClick={onBrowseDevices}>{t('compare.browse')}</button>}</div>}
  </article>;
}

export function ComparePage({ state, onRemove, onClear, onBrowseDevices }: ComparePageProps) {
  const { locale, t } = useLocale();
  const [differencesOnly, setDifferencesOnly] = useState(false);
  const [left, right] = state.slots;
  const count = Number(left !== null) + Number(right !== null);
  const example = state.context.mode === 'example';
  const rows = left && right ? compareFields(state) : [];
  const visible = rows.filter((row) => !differencesOnly || row.result !== 'same');
  const differentCount = visible.filter((row) => row.result === 'different').length;
  const uncertainCount = visible.filter((row) => row.result === 'missing' || row.result === 'incomparable').length;
  const value = (raw: string | number | boolean | null, kind: CompareFieldKind): ReactNode => {
    if (raw === null) return <span className="muted">{t('compare.value.missing')}</span>;
    if (kind === 'count') return formatCount(typeof raw === 'number' ? raw : null, locale);
    if (kind === 'boolean') return booleanLabel(typeof raw === 'boolean' ? raw : null, locale);
    if (kind === 'timestamp' && typeof raw === 'string') return <time dateTime={raw}>{formatDate(raw, locale)}<small className="compare-exact-time">{raw}</small></time>;
    if (kind === 'version') return String(raw);
    return t(typeof raw === 'string' && Object.hasOwn(ENUM_LABELS, raw) ? ENUM_LABELS[raw]! : 'compare.value.unknown');
  };
  return <section className="compare-page">
    <div className="panel compare-overview">
      <div className="compare-page-heading"><div><h2>{t('compare.selectionTitle')}</h2></div>
        <span className="badge" data-tone="purple">{t('compare.selectedCount', formatCount(count, locale))}</span></div>
      {example && <p className="compare-example compare-example-banner">{t('compare.exampleNote')}</p>}
      <p className="compare-scope">{t('compare.scopeNote')}</p>
      <p className="muted">{t('compare.timeNote')}</p>
      <div className="compare-slots"><DeviceSlot device={left} side="left" example={example} onRemove={onRemove} onBrowseDevices={onBrowseDevices} hasOne={count === 1} />
        <DeviceSlot device={right} side="right" example={example} onRemove={onRemove} onBrowseDevices={onBrowseDevices} hasOne={count === 1} /></div>
      <div className="compare-page-actions"><button type="button" className="btn btn-ghost" disabled={count === 0} onClick={onClear}>{t('compare.clear')}</button>
        {onBrowseDevices && <button type="button" className="btn btn-ghost" onClick={onBrowseDevices}>{t('compare.browse')}</button>}</div>
    </div>
    {left && right ? <>
      <div className="panel compare-options"><label><input type="checkbox" checked={differencesOnly} onChange={(event) => setDifferencesOnly(event.target.checked)} /><span>{t('compare.differencesOnly')}</span></label>
        <p className="muted">{t('compare.filterNote')}</p>
        <p role="status">{t('compare.summary', formatCount(differentCount, locale), formatCount(uncertainCount, locale), formatCount(visible.length, locale))}</p></div>
      {SECTIONS.map(([section, title]) => {
        const fields = visible.filter((field) => field.section === section);
        return fields.length ? <section className="panel compare-section" key={section} aria-label={t(title)}><h3>{t(title)}</h3>
          <p className="compare-section-note">{t(SECTION_NOTES[section])}</p>
          {fields.map((field) => <CompareFieldRow key={field.key} label={t(FIELD_LABELS[field.key])} status={field.result}
            leftLabel={left.deviceName} rightLabel={right.deviceName} leftValue={value(field.left, field.kind)} rightValue={value(field.right, field.kind)}
            note={field.reason === 'scope_not_established' ? t('compare.note.scope') : field.result === 'missing' ? t('compare.note.missing')
              : field.result === 'incomparable' ? t('compare.note.incomparable') : field.key.endsWith('.verification') ? t('compare.note.verification') : undefined} />)}
        </section> : null;
      })}
      {!visible.length && <p className="panel empty-state">{t('compare.noDifferences')}</p>}
    </> : <p className="panel empty-state">{t('compare.emptyPair')}</p>}
  </section>;
}
