import { NO_BUGS, type BugSet } from '../bugs/flags'
import { couponDiscount, type Coupon } from '../data/coupons'
import type { Product } from '../data/products'

/** Versandkosten in Cent. */
export const SHIPPING_FEE = 490
/** Ab diesem Warenwert (nach Rabatt) entfällt der Versand. */
export const FREE_SHIPPING_FROM = 7500
export const MAX_QUANTITY = 99

export interface CartItem {
  product: Product
  quantity: number
}

export interface CartTotals {
  subtotal: number
  discount: number
  shipping: number
  total: number
  /** Summe aller Mengen – wird im Header-Badge angezeigt. */
  itemCount: number
}

export interface CartState {
  items: CartItem[]
  coupon: Coupon | null
  /** Denormalisierte Summen; werden bei jeder Änderung neu berechnet. */
  totals: CartTotals
  /** Zähler aller „In den Warenkorb“-Versuche (Grundlage für das Flag flaky-race). */
  addAttempts: number
}

export type CartAction =
  | { type: 'add'; product: Product }
  | { type: 'setQuantity'; productId: string; quantity: number }
  | { type: 'remove'; productId: string }
  | { type: 'applyCoupon'; coupon: Coupon }
  | { type: 'removeCoupon' }
  | { type: 'clear' }

export function computeTotals(items: readonly CartItem[], coupon: Coupon | null): CartTotals {
  const subtotal = items.reduce((sum, item) => sum + item.product.price * item.quantity, 0)
  const discount = coupon ? couponDiscount(coupon, subtotal) : 0
  const goods = subtotal - discount
  const shipping = items.length === 0 || goods >= FREE_SHIPPING_FROM ? 0 : SHIPPING_FEE
  const itemCount = items.reduce((sum, item) => sum + item.quantity, 0)
  return { subtotal, discount, shipping, total: goods + shipping, itemCount }
}

export const EMPTY_CART: CartState = {
  items: [],
  coupon: null,
  totals: computeTotals([], null),
  addAttempts: 0,
}

export function clampQuantity(quantity: number): number {
  if (!Number.isFinite(quantity)) return 1
  return Math.max(1, Math.min(MAX_QUANTITY, Math.trunc(quantity)))
}

/**
 * Erzeugt den Warenkorb-Reducer für die aktiven Bug-Flags. Der Reducer ist rein (keine
 * Seiteneffekte), damit er auch unter React StrictMode deterministisch bleibt.
 */
export function createCartReducer(bugs: BugSet = NO_BUGS) {
  // BUG coupon-noop: Der Gutschein liegt im State (Chip und Toast melden „aktiv“),
  // aber die Summenberechnung bekommt ihn nie übergeben.
  const totalsFor = (items: readonly CartItem[], coupon: Coupon | null): CartTotals =>
    computeTotals(items, bugs.has('coupon-noop') ? null : coupon)

  return function cartReducer(state: CartState, action: CartAction): CartState {
    switch (action.type) {
      case 'add': {
        const addAttempts = state.addAttempts + 1

        // BUG flaky-race: Jeder dritte Versuch geht verloren – der Aufrufer zeigt trotzdem den Erfolgs-Toast.
        if (bugs.has('flaky-race') && addAttempts % 3 === 0) {
          return { ...state, addAttempts }
        }
        if (!action.product.inStock) {
          return { ...state, addAttempts }
        }

        const existing = state.items.find((item) => item.product.id === action.product.id)
        const items = existing
          ? state.items.map((item) =>
              item === existing ? { ...item, quantity: clampQuantity(item.quantity + 1) } : item,
            )
          : [...state.items, { product: action.product, quantity: 1 }]

        return { ...state, items, addAttempts, totals: totalsFor(items, state.coupon) }
      }

      case 'setQuantity': {
        const quantity = clampQuantity(action.quantity)
        const items = state.items.map((item) =>
          item.product.id === action.productId ? { ...item, quantity } : item,
        )

        // BUG qty-stale-total: Die Summen werden aus dem ALTEN Zustand berechnet – immer einen Klick hinterher.
        const basis = bugs.has('qty-stale-total') ? state.items : items

        return { ...state, items, totals: totalsFor(basis, state.coupon) }
      }

      case 'remove': {
        const index = state.items.findIndex((item) => item.product.id === action.productId)
        if (index === -1) return state

        // BUG remove-off-by-one: Gelöscht wird der Nachbar (Index + 1); beim letzten Eintrag passiert gar nichts.
        const target = bugs.has('remove-off-by-one') ? index + 1 : index

        const items = state.items.filter((_, position) => position !== target)
        return { ...state, items, totals: totalsFor(items, state.coupon) }
      }

      case 'applyCoupon':
        return { ...state, coupon: action.coupon, totals: totalsFor(state.items, action.coupon) }

      case 'removeCoupon':
        return { ...state, coupon: null, totals: totalsFor(state.items, null) }

      case 'clear':
        return { ...EMPTY_CART, addAttempts: state.addAttempts }
    }
  }
}
