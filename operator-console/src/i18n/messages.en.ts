import { appEn } from './catalogs/app';
import { productsEn } from './catalogs/products';
import { reportsEn } from './catalogs/reports';
import { compareEn } from './catalogs/compare';
import { policyReviewEn } from './catalogs/policyReview';
import type { messagesTr } from './messages.tr';
import type { CatalogShape } from './types';
export const messagesEn = { ...appEn, ...productsEn, ...reportsEn, ...compareEn, ...policyReviewEn } satisfies CatalogShape<typeof messagesTr>;
