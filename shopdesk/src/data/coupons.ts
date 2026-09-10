export interface Coupon {
  code: string
  kind: 'percent' | 'fixed'
  /** Prozentwert (kind = percent) bzw. Betrag in Cent (kind = fixed). */
  value: number
  /** Mindestwarenwert in Cent, ab dem der Gutschein gilt. */
  minSubtotal: number
  description: string
}

export const COUPONS: readonly Coupon[] = [
  { code: 'SAVE10', kind: 'percent', value: 10, minSubtotal: 0, description: '10% off your order' },
  { code: 'MINUS5', kind: 'fixed', value: 500, minSubtotal: 2000, description: '€5 off orders over €20' },
]

export type CouponLookup =
  | { ok: true; coupon: Coupon }
  | { ok: false; reason: 'unknown' }
  | { ok: false; reason: 'min-subtotal'; coupon: Coupon }

export function normalizeCouponCode(raw: string): string {
  return raw.trim().toUpperCase()
}

export function lookupCoupon(rawCode: string, subtotal: number): CouponLookup {
  const code = normalizeCouponCode(rawCode)
  const coupon = COUPONS.find((candidate) => candidate.code === code)
  if (!coupon) return { ok: false, reason: 'unknown' }
  if (subtotal < coupon.minSubtotal) return { ok: false, reason: 'min-subtotal', coupon }
  return { ok: true, coupon }
}

/** Rabattbetrag in Cent für einen Warenwert; nie größer als der Warenwert selbst. */
export function couponDiscount(coupon: Coupon, subtotal: number): number {
  if (subtotal <= 0 || subtotal < coupon.minSubtotal) return 0
  const raw = coupon.kind === 'percent' ? Math.round((subtotal * coupon.value) / 100) : coupon.value
  return Math.min(raw, subtotal)
}
