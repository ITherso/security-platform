import { appEn } from './catalogs/app';
import { productsEn } from './catalogs/products';
import { reportsEn } from './catalogs/reports';
import { compareEn } from './catalogs/compare';
import type { messagesTr } from './messages.tr';
import type { CatalogShape } from './types';
export const messagesEn = { ...appEn, ...productsEn, ...reportsEn, ...compareEn } satisfies CatalogShape<typeof messagesTr>;
