import { CircleCheck, TicketPercent } from 'lucide-react'
import { useId, useState, type FormEvent } from 'react'
import { lookupCoupon } from '../../data/coupons'
import { formatCents } from '../../lib/money'
import { useCart } from '../../store/cartContext'
import { useToast } from '../toast/toastContext'
import { Button } from '../ui/Button'
import { Card, CardTitle } from '../ui/Card'

export function CouponForm() {
  const { state, applyCoupon, removeCoupon } = useCart()
  const toast = useToast()
  const inputId = useId()
  const [code, setCode] = useState('')
  const [error, setError] = useState<string | null>(null)
  const active = state.coupon

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    const result = lookupCoupon(code, state.totals.subtotal)

    if (!result.ok) {
      setError(
        result.reason === 'unknown'
          ? 'This coupon code is not valid.'
          : `Minimum order value of ${formatCents(result.coupon.minSubtotal)} not reached.`,
      )
      return
    }

    applyCoupon(result.coupon)
    toast.success(`Coupon ${result.coupon.code} applied ✓`)
    setCode('')
    setError(null)
  }

  function handleRemove() {
    removeCoupon()
    toast.info('Coupon removed.')
  }

  return (
    <Card data-testid="coupon-card" className="p-5">
      <CardTitle className="flex items-center gap-2 text-sm">
        <span className="grid size-7 place-items-center rounded-lg bg-indigo-50 text-indigo-600">
          <TicketPercent className="size-4" aria-hidden="true" />
        </span>
        Coupon code
      </CardTitle>

      {active ? (
        <div
          data-testid="coupon-active"
          data-code={active.code}
          className="mt-4 flex items-center justify-between gap-3 rounded-2xl border border-emerald-200 bg-emerald-50 px-4 py-3"
        >
          <div className="flex items-center gap-2.5">
            <CircleCheck className="size-4 shrink-0 text-emerald-600" aria-hidden="true" />
            <div>
              <p className="text-sm font-semibold text-emerald-900">{active.code} applied</p>
              <p className="text-xs text-emerald-700">{active.description}</p>
            </div>
          </div>
          <Button variant="ghost" size="sm" data-testid="coupon-remove" onClick={handleRemove}>
            Remove
          </Button>
        </div>
      ) : (
        <form onSubmit={handleSubmit} noValidate className="mt-4 flex flex-col gap-2">
          <div className="flex gap-2">
            <label htmlFor={inputId} className="sr-only">
              Coupon code
            </label>
            <input
              id={inputId}
              data-testid="coupon-input"
              value={code}
              onChange={(event) => {
                setCode(event.target.value)
                setError(null)
              }}
              placeholder="Enter code"
              autoComplete="off"
              spellCheck={false}
              aria-invalid={error ? true : undefined}
              className="h-11 min-w-0 flex-1 rounded-2xl border border-slate-200 bg-slate-50 px-4 text-sm font-medium tracking-wide text-slate-900 uppercase transition-[border-color,background-color,box-shadow] duration-200 placeholder:font-normal placeholder:tracking-normal placeholder:normal-case placeholder:text-slate-400 hover:border-slate-300 focus:border-indigo-500 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:outline-none"
            />
            <Button type="submit" variant="secondary" data-testid="coupon-apply" disabled={code.trim() === ''}>
              Apply
            </Button>
          </div>
          {error ? (
            <p data-testid="coupon-error" role="alert" className="text-sm text-rose-600">
              {error}
            </p>
          ) : (
            <p className="text-xs text-slate-400">Demo codes: SAVE10 · MINUS5</p>
          )}
        </form>
      )}
    </Card>
  )
}
