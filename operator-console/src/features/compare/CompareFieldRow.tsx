import type { ReactNode } from 'react';
import type { CompareTextKey } from '../../i18n/catalogs/compare';
import { useLocale } from '../../i18n/LocaleProvider';

export type CompareFieldStatus = 'same' | 'different' | 'missing' | 'incomparable';
export interface CompareFieldRowProps {
  label: string;
  status: CompareFieldStatus;
  leftLabel: string;
  rightLabel: string;
  leftValue: ReactNode;
  rightValue: ReactNode;
  note?: string;
}
const STATUS_KEYS: Record<CompareFieldStatus, CompareTextKey> = {
  same: 'compare.status.same', different: 'compare.status.different',
  missing: 'compare.status.missing', incomparable: 'compare.status.incomparable',
};

export function CompareFieldRow({ label, status, leftLabel, rightLabel, leftValue, rightValue, note }: CompareFieldRowProps) {
  const { t } = useLocale();
  return <div className="compare-field" data-comparison={status}>
    <div className="compare-field-heading"><h4>{label}</h4>
      <span className="badge" data-tone={status === 'different' ? 'purple' : status === 'missing' || status === 'incomparable' ? 'warning' : 'neutral'}>{t(STATUS_KEYS[status])}</span>
      {note && <p className="muted">{note}</p>}
    </div>
    <div className="compare-field-value"><span className="compare-device-label">{leftLabel}</span>
      <span className="compare-repeat-label">{label}</span><div>{leftValue}</div></div>
    <div className="compare-field-value"><span className="compare-device-label">{rightLabel}</span>
      <span className="compare-repeat-label">{label}</span><div>{rightValue}</div></div>
  </div>;
}
