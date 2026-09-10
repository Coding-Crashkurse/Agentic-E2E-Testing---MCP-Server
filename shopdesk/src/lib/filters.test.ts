import { describe, expect, it } from 'vitest'
import type { BugSet } from '../bugs/flags'
import { PRODUCTS } from '../data/products'
import { DEFAULT_FILTER, filterProducts, isFilterActive } from './filters'

const FILTER_IGNORED: BugSet = new Set(['filter-ignored'])

describe('filterProducts', () => {
  it('liefert ohne Filter alle 12 Produkte', () => {
    expect(filterProducts(PRODUCTS, DEFAULT_FILTER)).toHaveLength(12)
  })

  it('„In stock only“ blendet die 3 ausverkauften Produkte aus', () => {
    const visible = filterProducts(PRODUCTS, { ...DEFAULT_FILTER, inStockOnly: true })
    expect(visible).toHaveLength(9)
    expect(visible.every((product) => product.inStock)).toBe(true)
  })

  it('filter-ignored: „In stock only“ hat keine Wirkung', () => {
    const visible = filterProducts(PRODUCTS, { ...DEFAULT_FILTER, inStockOnly: true }, FILTER_IGNORED)
    expect(visible).toHaveLength(12)
  })

  it('filter-ignored: Kategorie und Suche funktionieren weiterhin', () => {
    expect(filterProducts(PRODUCTS, { ...DEFAULT_FILTER, category: 'Office' }, FILTER_IGNORED)).toHaveLength(3)
    expect(filterProducts(PRODUCTS, { ...DEFAULT_FILTER, query: 'mahlwerk' }, FILTER_IGNORED)).toHaveLength(1)
  })

  it('kombiniert Kategorie, Suche und Verfügbarkeit', () => {
    const visible = filterProducts(PRODUCTS, { query: 'tast', category: 'Office', inStockOnly: true })
    expect(visible).toHaveLength(0)
  })
})

describe('isFilterActive', () => {
  it('erkennt Standard und Abweichungen', () => {
    expect(isFilterActive(DEFAULT_FILTER)).toBe(false)
    expect(isFilterActive({ ...DEFAULT_FILTER, inStockOnly: true })).toBe(true)
    expect(isFilterActive({ ...DEFAULT_FILTER, query: '  ' })).toBe(false)
  })
})
