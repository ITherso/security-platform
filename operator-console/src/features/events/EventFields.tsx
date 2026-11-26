/** The fields of the v2 event kinds, also the evidence of the alerts they raise (same names). Every value is the
 * device's own claim, shown as plain text; closed-set values keep their contract name. */
import type { ReactNode } from 'react';
import type { AgentStateFields, BehaviorMatchFields, PersistenceChangeFields, ScanDetectedFields, TamperSignalFields }
  from '../../data/contracts';
import type { EventsTextKey } from '../../i18n/catalogs/events';
import { booleanLabel, formatCount, formatPreciseDate } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';
import { HIT_SEVERITY_LABELS } from './eventsModel';

export type FieldRow = readonly [label: EventsTextKey, value: ReactNode, path?: boolean];

export function FieldList({ rows, className = 'event-details' }: { rows: readonly FieldRow[]; className?: string }) {
  const { t } = useLocale();
  return <dl className={className}>{rows.map(([label, value, path = false]) => <div key={label}>
    <dt>{t(label)}</dt><dd className={path ? 'event-path' : undefined}>{value}</dd></div>)}</dl>;
}

function Code({ value }: { value: string }) {
  return <code className="event-code">{value}</code>;
}
/** A device-clock instant with seconds, or "not reported"; the exact text stays in the machine-readable attribute. */
export function Moment({ value }: { value: string | null }) {
  const { locale, t } = useLocale();
  return value === null ? <>{t('events.notReported')}</>
    : <time dateTime={value} title={value}>{formatPreciseDate(value, locale)}</time>;
}
function useOptional() {
  const { t } = useLocale();
  return (value: ReactNode | null): ReactNode => value ?? t('events.notReported');
}

/** scan_detected: the only kind with a file SHA-256 and size. `pidShown`: the timeline's PID column has it. */
export function ScanFields({ fields, pidShown = false }: { fields: ScanDetectedFields; pidShown?: boolean }) {
  const { locale, t } = useLocale();
  const optional = useOptional();
  const rows: FieldRow[] = [
    ['events.field.trigger', <Code value={fields.trigger} />],
    ['events.field.path', fields.path, true],
    ['events.field.size', t('events.field.bytes', formatCount(fields.size, locale), fields.size)],
    ['events.field.sha256', <Code value={fields.sha256} />],
    ['events.field.rule_set_id', <Code value={fields.rule_set_id} />],
    ['events.field.hits', <ul className="event-hits">{fields.hits.map((hit, index) =>
      <li key={`${String(index)}-${hit.rule}`}><Code value={hit.rule} /> · {t(HIT_SEVERITY_LABELS[hit.severity])}</li>)}</ul>],
    ['events.field.omitted_hits', formatCount(fields.omitted_hits, locale)],
  ];
  if (!pidShown) rows.push(['events.field.pid', fields.pid === null ? optional(null) : String(fields.pid)]);
  rows.push(['events.field.create_time', <Moment value={fields.create_time} />],
    ['events.field.action_id', optional(fields.action_id === null ? null : <Code value={fields.action_id} />)]);
  return <FieldList rows={rows} />;
}

/** behavior_match: a rule ID evaluated on the device; the command line never leaves it. `processShown`: the timeline's
 * image and PID columns have those two. */
export function BehaviorFields({ fields, processShown = false }: { fields: BehaviorMatchFields; processShown?: boolean }) {
  const { locale } = useLocale();
  const optional = useOptional();
  const rows: FieldRow[] = [['events.field.rule', <Code value={fields.rule} />],
    ['events.field.rule_version', String(fields.rule_version)]];
  if (!processShown) rows.push(['events.field.pid', String(fields.pid)], ['events.field.image', fields.image, true]);
  rows.push(['events.field.create_time', <Moment value={fields.create_time} />],
    ['events.field.parent_image', optional(fields.parent_image), fields.parent_image !== null],
    ['events.field.found_at_start', booleanLabel(fields.found_at_start, locale)],
    ['events.field.command_line_source', <Code value={fields.command_line_source} />]);
  return <FieldList rows={rows} />;
}

export function PersistenceFields({ fields }: { fields: PersistenceChangeFields }) {
  const { locale } = useLocale();
  const optional = useOptional();
  return <FieldList rows={[
    ['events.field.location', <Code value={fields.location} />],
    ['events.field.scope', <Code value={fields.scope} />],
    ['events.field.change', <Code value={fields.change} />],
    ['events.field.entry_id', <Code value={fields.entry_id} />],
    ['events.field.target_image', optional(fields.target_image), fields.target_image !== null],
    ['events.field.found_at_start', booleanLabel(fields.found_at_start, locale)],
  ]} />;
}

/** agent_state, and capability_down's evidence: the agent's report about one of its own parts. */
export function AgentStateFieldList({ fields }: { fields: AgentStateFields }) {
  const optional = useOptional();
  return <FieldList rows={[
    ['events.field.subject', <Code value={fields.subject} />],
    ['events.field.state', <Code value={fields.state} />],
    ['events.field.code', optional(fields.code === null ? null : <Code value={fields.code} />)],
    ['events.field.rule_set_id', optional(fields.rule_set_id === null ? null : <Code value={fields.rule_set_id} />)],
  ]} />;
}

export function TamperFields({ fields }: { fields: TamperSignalFields }) {
  const optional = useOptional();
  return <FieldList rows={[
    ['events.field.signal', <Code value={fields.signal} />],
    ['events.field.detail', optional(fields.detail === null ? null : <Code value={fields.detail} />)],
  ]} />;
}
