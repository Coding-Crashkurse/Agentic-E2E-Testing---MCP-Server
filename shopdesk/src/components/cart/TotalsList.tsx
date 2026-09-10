import type { ReactNode } from 'react'
import type { Coupon } from '../../data/coupons'
import { cn } from '../../lib/cn'
import { formatCents } from '../../lib/money'
import type { CartTotals } from '../../store/cart'

interface RowProps {
  label: string
  testId: string
  emphasis?: boolean
  tone?: 'default' | 'success'
  children: ReactNode
}

function Row({ label, testId, emphasis = false, tone = 'default', children }: RowProps) {
  return (
    <div
      className={cn(
        'flex items-center justify-between gap-4',
        emphasis ? 'text-lg font-semibold tracking-tight text-slate-900' : 'text-sm',
      )}
    >
      <dt className={cn(!emphasis && 'text-slate-500')}>{label}</dt>
      <dd data-testid={testId} className={cn('tabular-nums', tone === 'success' && 'font-medium text-emerald-600')}>
        {children}
      </dd>
    </div>
  )
}

interface TotalsListProps {
  totals: CartTotals
  coupon: Coupon | null
  /** Präfix der Test-IDs, z. B. `summary` → `summary-total`. */
  testIdPrefix?: string
}

/** Subtotal, Discount (nur wenn > 0), Shipping und Total. */
export function TotalsList({ totals, coupon, testIdPrefix = 'summary' }: TotalsListProps) {
  return (
    <dl className="flex flex-col gap-3">
      <Row label="Subtotal" testId={`${testIdPrefix}-subtotal`}>
        {formatCents(totals.subtotal)}
      </Row>
      {totals.discount > 0 ? (
        <Row label={coupon ? `Discount (${coupon.code})` : 'Discount'} testId={`${testIdPrefix}-discount`} tone="success">
          -{formatCents(totals.discount)}
        </Row>
      ) : null}
      <Row label="Shipping" testId={`${testIdPrefix}-shipping`}>
        {totals.shipping === 0 ? 'Free' : formatCents(totals.shipping)}
      </Row>
      <div className="my-0.5 border-t border-dashed border-slate-200" role="presentation" />
      <Row label="Total" testId={`${testIdPrefix}-total`} emphasis>
        {formatCents(totals.total)}
      </Row>
    </dl>
  )
}
