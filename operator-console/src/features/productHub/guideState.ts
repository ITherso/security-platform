import { GUIDE_STEPS } from './guideModel';
import type { GuideFlow, GuideState, GuideStep } from './guideModel';

export function createGuideState(flow: GuideFlow): GuideState {
  if (!Object.hasOwn(GUIDE_STEPS, flow)) throw new Error('invalid_guide_flow');
  return Object.freeze({ flow, index: 0 });
}
export function currentGuideStep(state: GuideState | null): GuideStep | null {
  if (state === null || !Object.hasOwn(GUIDE_STEPS, state.flow) || !Number.isSafeInteger(state.index) || state.index < 0) return null;
  return GUIDE_STEPS[state.flow][state.index] ?? null;
}
export function guideStepCount(state: GuideState | null): number {
  return currentGuideStep(state) !== null && state !== null ? GUIDE_STEPS[state.flow].length : 0;
}
/** Pure state movement, with no route, file, example, network or store action. */
export function moveGuideStep(state: GuideState, direction: -1 | 1): GuideState | null {
  if (currentGuideStep(state) === null || (direction !== -1 && direction !== 1)) return null;
  const index = state.index + direction;
  if (index < 0 || index >= GUIDE_STEPS[state.flow].length) return state;
  return Object.freeze({ flow: state.flow, index });
}
