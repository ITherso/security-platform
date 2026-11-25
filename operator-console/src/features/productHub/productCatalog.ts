import type { ProductHubTextKey } from '../../i18n/catalogs/productHub';

/** Existing frontend destinations only; no product command or remote action. */
export type HubDestination = 'overview' | 'devices' | 'products' | 'audit' | 'reports' | 'compare'
  | 'termivarReview' | 'termivarComparison' | 'policyReview';
export type CatalogProductId = 'hostbasedfirewall' | 'termivar' | 'antivirus' | 'edr_agent';
export type CatalogComponentId = 'policy-impact-workbench' | 'security-platform';
/** Console availability only. `prototype_pending_acceptance`: the console view exists, the product is a prototype. */
export type HubAvailability = 'available_workspace' | 'prototype_pending_acceptance' | 'planned_unavailable';
interface HubEntryMetadata {
  readonly titleKey: ProductHubTextKey;
  readonly descriptionKey: ProductHubTextKey;
  readonly featureKey: ProductHubTextKey;
  readonly limitationKey: ProductHubTextKey;
  readonly dataSourceKey: ProductHubTextKey;
  readonly actionKey: ProductHubTextKey;
  readonly destination: HubDestination;
  readonly availability: HubAvailability;
  readonly verification: 'not_verified';
}
export type ProductHubEntry = HubEntryMetadata & (
  { readonly kind: 'product'; readonly id: CatalogProductId }
  | { readonly kind: 'component'; readonly id: CatalogComponentId }
);

/** Frontend introduction metadata, never a device DTO or installation claim. */
export const PRODUCT_HUB_ENTRIES: readonly ProductHubEntry[] = Object.freeze(([
  { kind: 'product', id: 'hostbasedfirewall', titleKey: 'productHub.hbf.name', descriptionKey: 'productHub.hbf.description',
    featureKey: 'productHub.hbf.feature', limitationKey: 'productHub.hbf.limit', dataSourceKey: 'productHub.hbf.source',
    actionKey: 'productHub.hbf.action', destination: 'devices', availability: 'available_workspace', verification: 'not_verified' },
  { kind: 'product', id: 'termivar', titleKey: 'productHub.termivar.name', descriptionKey: 'productHub.termivar.description',
    featureKey: 'productHub.termivar.feature', limitationKey: 'productHub.termivar.limit', dataSourceKey: 'productHub.termivar.source',
    actionKey: 'productHub.termivar.action', destination: 'termivarReview', availability: 'available_workspace', verification: 'not_verified' },
  { kind: 'product', id: 'edr_agent', titleKey: 'productHub.edr.name', descriptionKey: 'productHub.edr.description',
    featureKey: 'productHub.edr.feature', limitationKey: 'productHub.edr.limit', dataSourceKey: 'productHub.edr.source',
    actionKey: 'productHub.edr.action', destination: 'devices', availability: 'prototype_pending_acceptance', verification: 'not_verified' },
  { kind: 'component', id: 'policy-impact-workbench', titleKey: 'productHub.policy.name', descriptionKey: 'productHub.policy.description',
    featureKey: 'productHub.policy.feature', limitationKey: 'productHub.policy.limit', dataSourceKey: 'productHub.policy.source',
    actionKey: 'productHub.policy.action', destination: 'policyReview', availability: 'available_workspace', verification: 'not_verified' },
  { kind: 'component', id: 'security-platform', titleKey: 'productHub.platform.name', descriptionKey: 'productHub.platform.description',
    featureKey: 'productHub.platform.feature', limitationKey: 'productHub.platform.limit', dataSourceKey: 'productHub.platform.source',
    actionKey: 'productHub.platform.action', destination: 'overview', availability: 'available_workspace', verification: 'not_verified' },
  { kind: 'product', id: 'antivirus', titleKey: 'productHub.antivirus.name', descriptionKey: 'productHub.antivirus.description',
    featureKey: 'productHub.antivirus.feature', limitationKey: 'productHub.antivirus.limit', dataSourceKey: 'productHub.antivirus.source',
    actionKey: 'productHub.antivirus.action', destination: 'products', availability: 'planned_unavailable', verification: 'not_verified' },
] satisfies ProductHubEntry[]).map((entry) => Object.freeze(entry)));
