import { describe, expect, it } from 'vitest'
import { COUPONS, couponDiscount, lookupCoupon } from './coupons'

const save10 = COUPONS[0]
const minus5 = COUPONS[1]

describe('lookupCoupon', () => {
  it('findet Codes unabhängig von Schreibweise und Whitespace', () => {
    const result = lookupCoupon('  save10 ', 1000)
    expect(result).toEqual({ ok: true, coupon: save10 })
  })

  it('lehnt unbekannte Codes ab', () => {
    expect(lookupCoupon('GRATIS', 10000)).toEqual({ ok: false, reason: 'unknown' })
  })

  it('prüft den Mindestbestellwert', () => {
    expect(lookupCoupon('MINUS5', 1999)).toEqual({ ok: false, reason: 'min-subtotal', coupon: minus5 })
    expect(lookupCoupon('MINUS5', 2000).ok).toBe(true)
  })
})

describe('couponDiscount', () => {
  it('rundet Prozentrabatte kaufmännisch auf Cent', () => {
    expect(couponDiscount(save10, 8990)).toBe(899)
    expect(couponDiscount(save10, 14900)).toBe(1490)
  })

  it('begrenzt Festbeträge auf den Warenwert und respektiert den Mindestwert', () => {
    expect(couponDiscount(minus5, 1500)).toBe(0)
    expect(couponDiscount(minus5, 2000)).toBe(500)
    expect(couponDiscount({ ...minus5, minSubtotal: 0 }, 300)).toBe(300)
  })
})
