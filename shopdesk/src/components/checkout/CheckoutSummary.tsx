import type { ReactNode } from 'react'
import type { Coupon } from '../../data/coupons'
import { productImage } from '../../data/products'
import { formatCents } from '../../lib/money'
import type { CartItem, CartTotals } from '../../store/cart'
import { TotalsList } from '../cart/TotalsList'
import { Card, CardTitle } from '../ui/Card'

interface CheckoutSummaryProps {
  items: readonly CartItem[]
  totals: CartTotals
  coupon: Coupon | null
  children: ReactNode
}

export function CheckoutSummary({ items, totals, coupon, children }: CheckoutSummaryProps) {
  return (
    <Card data-testid="checkout-summary">
      <CardTitle>Your order</CardTitle>

      <ul data-testid="checkout-lines" className="mt-4 divide-y divide-slate-100">
        {items.map((item) => (
          <li
            key={item.product.id}
            data-testid="checkout-line"
            data-product-id={item.product.id}
            className="flex items-center gap-3 py-3"
          >
            <span className="relative shrink-0">
              <img
                src={productImage(item.product)}
                alt=""
                width={56}
                height={56}
                className="size-14 rounded-xl object-cover ring-1 ring-slate-900/5"
              />
              <span className="absolute -top-1.5 -right-1.5 grid min-w-5 place-items-center rounded-full bg-slate-900 px-1 text-[10px] font-semibold text-white ring-2 ring-white tabular-nums">
                {item.quantity}
              </span>
            </span>
            <div className="min-w-0 flex-1">
              <p className="truncate text-sm font-semibold text-slate-900">{item.product.name}</p>
              <p className="text-xs text-slate-500">
                {item.quantity} × {formatCents(item.product.price)}
              </p>
            </div>
            <span className="text-sm font-semibold text-slate-900 tabular-nums">
              {formatCents(item.product.price * item.quantity)}
            </span>
          </li>
        ))}
      </ul>

      <div className="mt-2 border-t border-slate-100 pt-5">
        <TotalsList totals={totals} coupon={coupon} testIdPrefix="checkout" />
      </div>

      <div className="mt-6">{children}</div>
    </Card>
  )
}
