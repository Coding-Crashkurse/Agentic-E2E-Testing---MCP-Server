import { describe, expect, it } from 'vitest'
import { NO_BUGS, type ActiveBug, type BugSet } from '../bugs/flags'
import { COUPONS } from '../data/coupons'
import { PRODUCTS } from '../data/products'
import { createCartReducer, EMPTY_CART, type CartAction, type CartState } from './cart'

const headphones = PRODUCTS[0] // €149.00 – p-01
const speaker = PRODUCTS[1] // €79.00 – p-02
const keyboard = PRODUCTS[2] // sold out – p-03
const grinder = PRODUCTS[3] // €89.90 – p-04
const mug = PRODUCTS[4] // €14.50 – p-05
const save10 = COUPONS[0]

const only = (...flags: ActiveBug[]): BugSet => new Set(flags)

function run(bugs: BugSet, actions: CartAction[]): CartState {
  return actions.reduce(createCartReducer(bugs), EMPTY_CART)
}

const ids = (state: CartState) => state.items.map((item) => item.product.id)

describe('cartReducer ohne Bugs', () => {
  it('legt Artikel ab und berechnet Summen inklusive Versand', () => {
    const state = run(NO_BUGS, [{ type: 'add', product: mug }])
    expect(ids(state)).toEqual(['p-05'])
    expect(state.totals).toEqual({ subtotal: 1450, discount: 0, shipping: 490, total: 1940, itemCount: 1 })
  })

  it('erhöht beim erneuten Hinzufügen die Menge', () => {
    const state = run(NO_BUGS, [
      { type: 'add', product: mug },
      { type: 'add', product: mug },
    ])
    expect(state.items).toHaveLength(1)
    expect(state.items[0].quantity).toBe(2)
    expect(state.totals.itemCount).toBe(2)
  })

  it('ignoriert ausverkaufte Artikel', () => {
    const state = run(NO_BUGS, [{ type: 'add', product: keyboard }])
    expect(state.items).toHaveLength(0)
  })

  it('lässt den Versand ab €75 Warenwert entfallen', () => {
    const state = run(NO_BUGS, [{ type: 'add', product: headphones }])
    expect(state.totals.shipping).toBe(0)
    expect(state.totals.total).toBe(14900)
  })

  it('aktualisiert Summen bei Mengenänderung sofort', () => {
    const state = run(NO_BUGS, [
      { type: 'add', product: mug },
      { type: 'setQuantity', productId: 'p-05', quantity: 2 },
    ])
    expect(state.items[0].quantity).toBe(2)
    expect(state.totals.subtotal).toBe(2900)
    expect(state.totals.total).toBe(3390)
  })

  it('entfernt genau den gewählten Artikel', () => {
    const state = run(NO_BUGS, [
      { type: 'add', product: headphones },
      { type: 'add', product: speaker },
      { type: 'add', product: grinder },
      { type: 'remove', productId: 'p-02' },
    ])
    expect(ids(state)).toEqual(['p-01', 'p-04'])
  })

  it('zieht einen Gutschein von der Summe ab', () => {
    const state = run(NO_BUGS, [
      { type: 'add', product: headphones },
      { type: 'applyCoupon', coupon: save10 },
    ])
    expect(state.coupon).toBe(save10)
    expect(state.totals.discount).toBe(1490)
    expect(state.totals.total).toBe(13410)
  })

  it('leert den Warenkorb inklusive Gutschein', () => {
    const state = run(NO_BUGS, [
      { type: 'add', product: headphones },
      { type: 'applyCoupon', coupon: save10 },
      { type: 'clear' },
    ])
    expect(state.items).toHaveLength(0)
    expect(state.coupon).toBeNull()
    expect(state.totals.total).toBe(0)
  })
})

describe('Bug-Flags im Reducer', () => {
  it('coupon-noop: Gutschein gilt als aktiv, Summe bleibt unverändert', () => {
    const state = run(only('coupon-noop'), [
      { type: 'add', product: headphones },
      { type: 'applyCoupon', coupon: save10 },
    ])
    expect(state.coupon).toBe(save10)
    expect(state.totals.discount).toBe(0)
    expect(state.totals.total).toBe(14900)
  })

  it('coupon-noop: bleibt auch nach weiteren Aktionen ohne Rabatt', () => {
    const state = run(only('coupon-noop'), [
      { type: 'add', product: headphones },
      { type: 'applyCoupon', coupon: save10 },
      { type: 'setQuantity', productId: 'p-01', quantity: 2 },
    ])
    expect(state.totals.discount).toBe(0)
    expect(state.totals.total).toBe(29800)
  })

  it('remove-off-by-one: entfernt den Nachbarn statt des gewählten Artikels', () => {
    const state = run(only('remove-off-by-one'), [
      { type: 'add', product: headphones },
      { type: 'add', product: speaker },
      { type: 'add', product: grinder },
      { type: 'remove', productId: 'p-02' },
    ])
    expect(ids(state)).toEqual(['p-01', 'p-02'])
  })

  it('remove-off-by-one: beim letzten Eintrag passiert nichts', () => {
    const state = run(only('remove-off-by-one'), [
      { type: 'add', product: headphones },
      { type: 'add', product: speaker },
      { type: 'remove', productId: 'p-02' },
    ])
    expect(ids(state)).toEqual(['p-01', 'p-02'])
  })

  it('qty-stale-total: Summen hinken genau einen Schritt hinterher', () => {
    const reducer = createCartReducer(only('qty-stale-total'))
    const afterFirst = run(only('qty-stale-total'), [
      { type: 'add', product: mug },
      { type: 'setQuantity', productId: 'p-05', quantity: 2 },
    ])
    expect(afterFirst.items[0].quantity).toBe(2)
    expect(afterFirst.totals.subtotal).toBe(1450)
    expect(afterFirst.totals.itemCount).toBe(1)

    const afterSecond = reducer(afterFirst, { type: 'setQuantity', productId: 'p-05', quantity: 3 })
    expect(afterSecond.items[0].quantity).toBe(3)
    expect(afterSecond.totals.subtotal).toBe(2900)
  })

  it('flaky-race: jeder dritte Versuch geht verloren', () => {
    const add: CartAction = { type: 'add', product: mug }
    const state = run(only('flaky-race'), [add, add, add])
    expect(state.addAttempts).toBe(3)
    expect(state.items[0].quantity).toBe(2)

    const next = createCartReducer(only('flaky-race'))(state, add)
    expect(next.items[0].quantity).toBe(3)
  })

  it('mehrere Flags wirken gleichzeitig und unabhängig', () => {
    const bugs = only('coupon-noop', 'qty-stale-total', 'flaky-race')
    const add: CartAction = { type: 'add', product: headphones }
    const state = run(bugs, [
      add,
      add,
      add, // flaky-race: dritter Versuch geht verloren → Menge 2
      { type: 'setQuantity', productId: 'p-01', quantity: 3 }, // qty-stale-total: Summen noch von Menge 2
      { type: 'applyCoupon', coupon: save10 }, // coupon-noop: kein Rabatt
    ])
    expect(state.items[0].quantity).toBe(3)
    expect(state.addAttempts).toBe(3)
    expect(state.coupon).toBe(save10)
    expect(state.totals.discount).toBe(0)
    expect(state.totals.subtotal).toBe(44700)
  })

  it.each<ActiveBug>(['filter-ignored', 'submit-disabled', 'save-not-persisted', 'double-submit'])(
    '%s: Reducer verhält sich wie ohne Bugs',
    (bug) => {
      const actions: CartAction[] = [
        { type: 'add', product: headphones },
        { type: 'add', product: mug },
        { type: 'setQuantity', productId: 'p-05', quantity: 3 },
        { type: 'applyCoupon', coupon: save10 },
        { type: 'remove', productId: 'p-01' },
      ]
      expect(run(only(bug), actions)).toEqual(run(NO_BUGS, actions))
    },
  )
})
