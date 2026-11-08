import type { ProductHubTextKey } from '../../i18n/catalogs/productHub';
import type { HubDestination } from './productCatalog';

export const GUIDE_FLOWS = ['endpoint', 'termivar', 'policy'] as const;
export type GuideFlow = typeof GUIDE_FLOWS[number];
export interface GuideState { readonly flow: GuideFlow; readonly index: number }
export interface GuideStep {
  readonly id: string;
  readonly destination: HubDestination;
  readonly titleKey: ProductHubTextKey;
  readonly instructionKey: ProductHubTextKey;
  readonly controlKey: ProductHubTextKey;
}
export const GUIDE_FLOW_LABELS: Readonly<Record<GuideFlow, ProductHubTextKey>> = Object.freeze({
  endpoint: 'productHub.flow.endpoint', termivar: 'productHub.flow.termivar', policy: 'productHub.flow.policy',
});
const steps = (value: readonly GuideStep[]): readonly GuideStep[] => Object.freeze(value.map(step => Object.freeze(step)));
/** Static instructions only. Advancing a step does not open its destination. */
export const GUIDE_STEPS: Readonly<Record<GuideFlow, readonly GuideStep[]>> = Object.freeze({
  endpoint: steps([
    { id: 'inventory', destination: 'devices', titleKey: 'productHub.guide.endpoint.inventory.title', instructionKey: 'productHub.guide.endpoint.inventory.instruction', controlKey: 'productHub.guide.endpoint.inventory.control' },
    { id: 'detail', destination: 'devices', titleKey: 'productHub.guide.endpoint.detail.title', instructionKey: 'productHub.guide.endpoint.detail.instruction', controlKey: 'productHub.guide.endpoint.detail.control' },
    { id: 'claims', destination: 'devices', titleKey: 'productHub.guide.endpoint.claims.title', instructionKey: 'productHub.guide.endpoint.claims.instruction', controlKey: 'productHub.guide.endpoint.claims.control' },
    { id: 'compare', destination: 'compare', titleKey: 'productHub.guide.endpoint.compare.title', instructionKey: 'productHub.guide.endpoint.compare.instruction', controlKey: 'productHub.guide.endpoint.compare.control' },
    { id: 'report', destination: 'reports', titleKey: 'productHub.guide.endpoint.report.title', instructionKey: 'productHub.guide.endpoint.report.instruction', controlKey: 'productHub.guide.endpoint.report.control' },
  ]),
  termivar: steps([
    { id: 'open', destination: 'termivarReview', titleKey: 'productHub.guide.termivar.open.title', instructionKey: 'productHub.guide.termivar.open.instruction', controlKey: 'productHub.guide.termivar.open.control' },
    { id: 'example', destination: 'termivarReview', titleKey: 'productHub.guide.termivar.example.title', instructionKey: 'productHub.guide.termivar.example.instruction', controlKey: 'productHub.guide.termivar.example.control' },
    { id: 'coverage', destination: 'termivarReview', titleKey: 'productHub.guide.termivar.coverage.title', instructionKey: 'productHub.guide.termivar.coverage.instruction', controlKey: 'productHub.guide.termivar.coverage.control' },
    { id: 'comparison', destination: 'termivarComparison', titleKey: 'productHub.guide.termivar.comparison.title', instructionKey: 'productHub.guide.termivar.comparison.instruction', controlKey: 'productHub.guide.termivar.comparison.control' },
    { id: 'before', destination: 'termivarComparison', titleKey: 'productHub.guide.termivar.before.title', instructionKey: 'productHub.guide.termivar.before.instruction', controlKey: 'productHub.guide.termivar.before.control' },
  ]),
  policy: steps([
    { id: 'open', destination: 'policyReview', titleKey: 'productHub.guide.policy.open.title', instructionKey: 'productHub.guide.policy.open.instruction', controlKey: 'productHub.guide.policy.open.control' },
    { id: 'example', destination: 'policyReview', titleKey: 'productHub.guide.policy.example.title', instructionKey: 'productHub.guide.policy.example.instruction', controlKey: 'productHub.guide.policy.example.control' },
    { id: 'identities', destination: 'policyReview', titleKey: 'productHub.guide.policy.identities.title', instructionKey: 'productHub.guide.policy.identities.instruction', controlKey: 'productHub.guide.policy.identities.control' },
    { id: 'preconditions', destination: 'policyReview', titleKey: 'productHub.guide.policy.preconditions.title', instructionKey: 'productHub.guide.policy.preconditions.instruction', controlKey: 'productHub.guide.policy.preconditions.control' },
    { id: 'boundary', destination: 'policyReview', titleKey: 'productHub.guide.policy.boundary.title', instructionKey: 'productHub.guide.policy.boundary.instruction', controlKey: 'productHub.guide.policy.boundary.control' },
  ]),
});
