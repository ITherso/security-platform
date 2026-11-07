import { useEffect, useId, useState } from 'react';
import { formatCount } from '../../i18n/formatters';
import { useLocale } from '../../i18n/LocaleProvider';
import './compare.css';

export type CompareSide = 'left' | 'right';
export interface CompareCaptureActionsProps {
  deviceId: string;
  selected: boolean;
  count: number;
  leftLabel: string | null;
  rightLabel: string | null;
  disabled?: boolean;
  notice?: string;
  errorMessage?: string;
  onAdd: () => void;
  onUpdate: () => void;
  onReplace: (side: CompareSide) => void;
  onOpen: () => void;
}

/** Presentation only: the existing detail loader and store own all capture guards. */
export function CompareCaptureActions({ deviceId, selected, count, leftLabel, rightLabel,
  disabled = false, notice = '', errorMessage = '', onAdd, onUpdate, onReplace, onOpen }: CompareCaptureActionsProps) {
  const { locale, t } = useLocale();
  const [replacementOpen, setReplacementOpen] = useState(false);
  const [side, setSide] = useState<CompareSide | null>(null);
  const choiceId = useId();
  useEffect(() => { setReplacementOpen(false); setSide(null); }, [deviceId]);
  const cancel = () => { setReplacementOpen(false); setSide(null); };
  const add = () => {
    if (disabled) return;
    if (count >= 2) { setSide(null); setReplacementOpen(true); }
    else onAdd();
  };
  return <section className="compare-capture">
    <p>{t('compare.capture.description')}</p>
    <div className="compare-actions">
      <button type="button" className="btn btn-primary" disabled={disabled} onClick={selected ? onUpdate : add}>
        {t(selected ? 'compare.capture.update' : 'compare.capture.add')}
      </button>
      <button type="button" className="btn btn-ghost" onClick={onOpen}>{t('compare.capture.open', formatCount(count, locale))}</button>
    </div>
    {replacementOpen && !selected && count >= 2 && <fieldset className="compare-replacement" disabled={disabled}>
      <legend>{t('compare.capture.replaceTitle')}</legend>
      <p>{t('compare.capture.replaceDescription')}</p>
      <label><input type="radio" name={choiceId} checked={side === 'left'} onChange={() => setSide('left')} />
        <span>{t('compare.capture.chooseLeft', leftLabel ?? t('compare.slot.left'))}</span></label>
      <label><input type="radio" name={choiceId} checked={side === 'right'} onChange={() => setSide('right')} />
        <span>{t('compare.capture.chooseRight', rightLabel ?? t('compare.slot.right'))}</span></label>
      <div className="compare-actions">
        <button type="button" className="btn btn-primary" disabled={side === null} onClick={() => {
          if (side === null || disabled) return;
          onReplace(side); cancel();
        }}>{t('compare.capture.confirm')}</button>
        <button type="button" className="btn btn-ghost" onClick={cancel}>{t('compare.capture.cancel')}</button>
      </div>
    </fieldset>}
    {notice && <p role="status">{notice}</p>}
    {errorMessage && <p className="inline-error" role="alert">{errorMessage}</p>}
  </section>;
}
