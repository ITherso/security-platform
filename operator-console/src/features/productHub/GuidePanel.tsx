import { useEffect, useId } from 'react';
import type { GuideState } from './guideModel';
import { GUIDE_FLOW_LABELS } from './guideModel';
import { currentGuideStep, guideStepCount } from './guideState';
import { useLocale } from '../../i18n/LocaleProvider';
import { formatCount } from '../../i18n/formatters';
import './productHub.css';

export interface GuidePanelProps {
  state: GuideState | null;
  onPrevious: () => void;
  onNext: () => void;
  onClose: () => void;
  onOpenStep: () => void;
}

/** An in-page instruction region; it never opens controls or moves focus. */
export function GuidePanel({ state, onPrevious, onNext, onClose, onOpenStep }: GuidePanelProps) {
  const { locale, t } = useLocale();
  const headingId = useId();
  const isOpen = state !== null;
  useEffect(() => {
    if (!isOpen) return;
    const escape = (event: KeyboardEvent) => {
      if (event.key !== 'Escape' || event.defaultPrevented || document.querySelector('dialog[open]')) return;
      event.preventDefault(); onClose();
    };
    window.addEventListener('keydown', escape);
    return () => window.removeEventListener('keydown', escape);
  }, [isOpen, onClose]);
  if (state === null) return null;
  const step = currentGuideStep(state), total = guideStepCount(state);
  return <aside className="panel product-guide-panel" aria-labelledby={headingId}>
    <div className="product-guide-heading"><div><p className="product-guide-example">{t('productHub.guide.example')}</p>
      <h2 id={headingId}>{step ? t(GUIDE_FLOW_LABELS[state.flow]) : t('productHub.guide.label')}</h2></div>
      <button type="button" className="btn btn-ghost" aria-label={t('productHub.guide.closeAria')} onClick={onClose}>{t('productHub.guide.close')}</button></div>
    {step ? <>
      <p className="product-guide-position" role="status" aria-atomic="true">{t('productHub.guide.step', formatCount(state.index + 1, locale), formatCount(total, locale))}</p>
      <h3>{t(step.titleKey)}</h3><p className="product-guide-instruction">{t(step.instructionKey)}</p>
      <dl className="product-guide-control"><div><dt>{t('productHub.guide.control')}</dt><dd>{t(step.controlKey)}</dd></div></dl>
      <div className="product-guide-actions"><button type="button" className="btn btn-primary" onClick={onOpenStep}>{t('productHub.guide.openStep')}</button>
        <div><button type="button" className="btn btn-ghost" disabled={state.index === 0} onClick={onPrevious}>{t('productHub.guide.previous')}</button>
          <button type="button" className="btn btn-ghost" disabled={state.index >= total - 1} onClick={onNext}>{t('productHub.guide.next')}</button></div></div>
      <p className="product-hub-help">{t('productHub.guide.noAutomation')}</p><p className="product-hub-help">{t('productHub.guide.sampleOnly')}</p>
    </> : <p className="product-hub-help">{t('productHub.guide.invalid')}</p>}
  </aside>;
}
