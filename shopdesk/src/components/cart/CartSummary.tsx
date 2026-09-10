import { ShieldCheck, Truck } from 'lucide-react'
import type { ReactNode } from 'react'
import type { Coupon } from '../../data/coupons'
import { formatCents } from '../../lib/money'
import { FREE_SHIPPING_FROM, type CartTotals } from '../../store/cart'
import { Card, CardTitle } from '../ui/Card'
import { TotalsList } from './TotalsList'

interface CartSummaryProps {
  totals: CartTotals
  coupon: Coupon | null
  children?: ReactNode
}

export function CartSummary({ totals, coupon, children }: CartSummaryProps) {
  const goods = totals.subtotal - totals.discount
  const remaining = Math.max(0, FREE_SHIPPING_FROM - goods)
  const progress = Math.min(100, Math.round((goods / FREE_SHIPPING_FROM) * 100))

  return (
    <Card data-testid="cart-summary">
      <CardTitle>Order summary</CardTitle>

      <div className="mt-5">
        <TotalsList totals={totals} coupon={coupon} />
      </div>

      <div data-testid="shipping-progress" className="mt-5 rounded-2xl bg-slate-50 p-3.5 ring-1 ring-slate-900/5">
        <p className="flex items-center gap-2 text-xs font-medium text-slate-600">
          <Truck className="size-3.5 text-indigo-500" aria-hidden="true" />
          {remaining > 0 ? `Add ${formatCents(remaining)} more for free shipping` : 'Free shipping unlocked'}
        </p>
        <div className="mt-2.5 h-1.5 overflow-hidden rounded-full bg-slate-200" role="presentation">
          <div
            className="h-full rounded-full bg-linear-to-r from-indigo-500 to-violet-500 transition-[width] duration-500"
            style={{ width: `${progress}%` }}
          />
        </div>
      </div>

      {children ? <div className="mt-5">{children}</div> : null}

      <p className="mt-4 flex items-center justify-center gap-1.5 text-xs text-slate-400">
        <ShieldCheck className="size-3.5" aria-hidden="true" />
        Secure checkout · Prices incl. VAT
      </p>
    </Card>
  )
}
