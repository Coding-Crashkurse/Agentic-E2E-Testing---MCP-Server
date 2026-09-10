import { NO_BUGS, type BugSet } from '../bugs/flags'
import type { Category, Product } from '../data/products'

export interface CatalogFilter {
  query: string
  category: Category | 'all'
  inStockOnly: boolean
}

export const DEFAULT_FILTER: CatalogFilter = { query: '', category: 'all', inStockOnly: false }

export function isFilterActive(filter: CatalogFilter): boolean {
  return filter.query.trim() !== '' || filter.category !== 'all' || filter.inStockOnly
}

export function filterProducts(
  products: readonly Product[],
  filter: CatalogFilter,
  bugs: BugSet = NO_BUGS,
): Product[] {
  const query = filter.query.trim().toLowerCase()

  // BUG filter-ignored: Der Chip „In stock only“ schaltet um, das Prädikat wertet ihn nicht aus.
  const inStockOnly = bugs.has('filter-ignored') ? false : filter.inStockOnly

  return products.filter((product) => {
    if (filter.category !== 'all' && product.category !== filter.category) return false
    if (inStockOnly && !product.inStock) return false
    if (query === '') return true
    return (
      product.name.toLowerCase().includes(query) || product.description.toLowerCase().includes(query)
    )
  })
}
