import { Check, Receipt } from 'lucide-react'
import { TotalsList } from '../components/cart/TotalsList'
import { Badge } from '../components/ui/Badge'
import { buttonClassName } from '../components/ui/buttonStyles'
import { Card, CardTitle } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { productImage } from '../data/products'
import { formatCents } from '../lib/money'
import { ROUTES } from '../router'
import { countItems, useOrders } from '../store/ordersContext'

export function ConfirmationView() {
  const { orders } = useOrders()
  const latest = orders.at(-1)

  if (!latest) {
    return (
      <EmptyState
        data-testid="confirmation-empty"
        icon={<Receipt aria-hidden="true" />}
        title="No order found"
        description="No order has been completed in this session yet."
        action={
          <a href={ROUTES.catalog} data-testid="go-to-catalog" className={buttonClassName()}>
            Browse the catalog
          </a>
        }
      />
    )
  }

  const { address } = latest

  return (
    <div data-testid="order-confirmation" data-order-number={latest.number} className="flex flex-col gap-6">
      <section className="relative overflow-hidden rounded-3xl bg-slate-950 px-8 py-12 text-center text-white shadow-lift">
        <div aria-hidden="true" className="absolute -top-24 left-1/4 size-72 rounded-full bg-emerald-500/30 blur-3xl" />
        <div aria-hidden="true" className="absolute -right-10 -bottom-28 size-80 rounded-full bg-indigo-500/40 blur-3xl" />
        <div className="relative flex flex-col items-center gap-4">
          <span className="animate-pop-in grid size-16 place-items-center rounded-full bg-linear-to-br from-emerald-400 to-teal-500 text-white shadow-[0_16px_40px_-12px_rgb(16_185_129/0.7)]">
            <Check className="size-8" strokeWidth={3} aria-hidden="true" />
          </span>
          <h1 className="text-3xl font-semibold tracking-tight text-balance">Thank you for your order!</h1>
          <p className="max-w-lg text-slate-300">
            Your order number is{' '}
            <strong
              data-testid="order-number"
              className="rounded-full bg-white/10 px-2.5 py-0.5 font-semibold text-white ring-1 ring-white/15 tabular-nums"
            >
              #{latest.number}
            </strong>
            . Delivery in 2–3 business days.
          </p>
          <a
            href={ROUTES.catalog}
            data-testid="continue-shopping"
            className={buttonClassName({ variant: 'secondary', className: 'mt-2' })}
          >
            Continue shopping
          </a>
        </div>
      </section>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start">
        <Card>
          <CardTitle>Items ordered</CardTitle>
          <ul data-testid="order-lines" className="mt-4 divide-y divide-slate-100">
            {latest.items.map((item) => (
              <li
                key={item.product.id}
                data-testid="order-line"
                data-product-id={item.product.id}
                className="flex items-center gap-4 py-3.5"
              >
                <img
                  src={productImage(item.product)}
                  alt=""
                  width={64}
                  height={64}
                  className="size-16 shrink-0 rounded-2xl object-cover ring-1 ring-slate-900/5"
                />
                <div className="min-w-0 flex-1">
                  <p className="truncate font-semibold tracking-tight text-slate-900">{item.product.name}</p>
                  <p className="text-sm text-slate-500">
                    {item.quantity} × {formatCents(item.product.price)}
                  </p>
                </div>
                <span className="font-semibold text-slate-900 tabular-nums">
                  {formatCents(item.product.price * item.quantity)}
                </span>
              </li>
            ))}
          </ul>
        </Card>

        <div className="flex flex-col gap-6">
          <Card data-testid="order-address">
            <CardTitle>Shipping address</CardTitle>
            <address className="mt-3 text-[15px] leading-7 text-slate-700 not-italic">
              {address.name}
              <br />
              {address.street}
              <br />
              {address.zip} {address.city}
              <br />
              <span className="text-slate-500">{address.email}</span>
            </address>
          </Card>
          <Card>
            <CardTitle>Summary</CardTitle>
            <div className="mt-4">
              <TotalsList totals={latest.totals} coupon={latest.coupon} testIdPrefix="order" />
            </div>
          </Card>
        </div>
      </div>

      <Card data-testid="order-history">
        <div className="flex items-center justify-between gap-4">
          <CardTitle>Orders this session</CardTitle>
          <Badge tone="brand" data-testid="order-history-count">
            {orders.length}
          </Badge>
        </div>
        <ul className="mt-4 divide-y divide-slate-100">
          {orders.map((order) => (
            <li
              key={order.number}
              data-testid="order-history-entry"
              data-order-number={order.number}
              className="flex items-center justify-between gap-4 py-3 text-sm"
            >
              <span className="font-semibold text-slate-900 tabular-nums">#{order.number}</span>
              <span className="text-slate-500">
                {countItems(order.items)} {countItems(order.items) === 1 ? 'item' : 'items'}
              </span>
              <span className="font-semibold text-slate-900 tabular-nums">{formatCents(order.totals.total)}</span>
            </li>
          ))}
        </ul>
      </Card>
    </div>
  )
}
