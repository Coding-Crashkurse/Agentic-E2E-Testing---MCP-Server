import { CreditCard, Lock, MapPin, Save, ShieldCheck, Undo2 } from 'lucide-react'
import { useMemo, useRef, useState, type ChangeEvent, type FormEvent, type ReactNode } from 'react'
import { useBugs } from '../../bugs/bugContext'
import {
  ADDRESS_FIELDS,
  normalizeAddress,
  validateAddress,
  type Address,
  type AddressField,
} from '../../lib/address'
import { navigate } from '../../router'
import { useCart } from '../../store/cartContext'
import { useCustomer } from '../../store/customerContext'
import { useOrders } from '../../store/ordersContext'
import { useToast } from '../toast/toastContext'
import { Button } from '../ui/Button'
import { Card, CardTitle } from '../ui/Card'
import { PageHeader } from '../ui/PageHeader'
import { TextField } from '../ui/TextField'
import { CheckoutSummary } from './CheckoutSummary'

type Touched = Partial<Record<AddressField, true>>

const ALL_TOUCHED: Touched = Object.fromEntries(ADDRESS_FIELDS.map((field) => [field, true])) as Touched

function SectionTitle({ icon, title, description }: { icon: ReactNode; title: string; description: string }) {
  return (
    <div className="flex items-start gap-3.5">
      <span className="grid size-10 shrink-0 place-items-center rounded-2xl bg-indigo-50 text-indigo-600 [&>svg]:size-5">
        {icon}
      </span>
      <div>
        <CardTitle>{title}</CardTitle>
        <p className="mt-0.5 text-sm text-slate-500">{description}</p>
      </div>
    </div>
  )
}

export function CheckoutForm() {
  const bugs = useBugs()
  const cart = useCart()
  const orders = useOrders()
  const customer = useCustomer()
  const toast = useToast()

  const [form, setForm] = useState<Address>(customer.address)
  const [touched, setTouched] = useState<Touched>({})
  const [termsAccepted, setTermsAccepted] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const inFlight = useRef(false)

  const errors = useMemo(() => validateAddress(form, bugs), [form, bugs])
  const addressValid = Object.keys(errors).length === 0

  // BUG double-submit: Weder Sperre noch Pending-Zustand greifen – der Button bleibt klickbar,
  // zeigt keinen Spinner, und ein Doppelklick innerhalb der Backend-Latenz erzeugt zwei Bestellungen.
  const preventDoubleSubmit = !bugs.has('double-submit')
  const pending = preventDoubleSubmit && submitting

  const canSubmit = addressValid && termsAccepted && !pending

  function updateField(field: AddressField, value: string) {
    setForm((previous) => ({ ...previous, [field]: value }))
  }

  function touch(field: AddressField) {
    setTouched((previous) => (previous[field] ? previous : { ...previous, [field]: true }))
  }

  function fieldProps(field: AddressField) {
    return {
      name: field,
      value: form[field],
      error: touched[field] ? errors[field] : undefined,
      onChange: (event: ChangeEvent<HTMLInputElement>) => updateField(field, event.target.value),
      onBlur: () => touch(field),
    }
  }

  function handleSaveAddress() {
    if (!addressValid) {
      setTouched(ALL_TOUCHED)
      toast.error('Please fill in all fields correctly first.')
      return
    }
    const normalized = normalizeAddress(form)
    customer.saveAddress(normalized)
    setForm(normalized)
    toast.success('Address saved ✓')
  }

  async function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (preventDoubleSubmit && inFlight.current) return
    if (!addressValid || !termsAccepted) {
      setTouched(ALL_TOUCHED)
      return
    }

    inFlight.current = true
    setSubmitting(true)
    try {
      await orders.placeOrder({
        items: cart.state.items,
        totals: cart.state.totals,
        coupon: cart.state.coupon,
        address: normalizeAddress(form),
      })
      // Erst navigieren, dann leeren: So rendert React direkt die Bestätigung statt kurz den leeren Warenkorb.
      navigate('confirmation')
      cart.clear()
    } finally {
      inFlight.current = false
      setSubmitting(false)
    }
  }

  return (
    <form
      id="checkout-form"
      data-testid="checkout-form"
      onSubmit={handleSubmit}
      noValidate
      className="flex flex-col gap-6"
    >
      <PageHeader title="Checkout" description="Review your shipping address and complete your order." />

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_400px] lg:items-start">
        <div className="flex flex-col gap-6">
          <Card>
            <div className="flex flex-wrap items-start justify-between gap-4">
              <SectionTitle
                icon={<MapPin aria-hidden="true" />}
                title="Shipping address"
                description="Prefilled from your account."
              />
              <Button
                variant="secondary"
                size="sm"
                data-testid="save-address"
                icon={<Save className="size-4" aria-hidden="true" />}
                onClick={handleSaveAddress}
              >
                Save address
              </Button>
            </div>

            <div className="mt-6 grid gap-4 sm:grid-cols-2">
              <TextField label="Full name" autoComplete="name" className="sm:col-span-2" {...fieldProps('name')} />
              <TextField
                label="Email address"
                type="email"
                autoComplete="email"
                inputMode="email"
                className="sm:col-span-2"
                {...fieldProps('email')}
              />
              <TextField
                label="Street and house number"
                autoComplete="street-address"
                className="sm:col-span-2"
                {...fieldProps('street')}
              />
              <TextField label="ZIP code" inputMode="numeric" autoComplete="postal-code" maxLength={5} {...fieldProps('zip')} />
              <TextField label="City" autoComplete="address-level2" {...fieldProps('city')} />
            </div>
          </Card>

          <Card>
            <SectionTitle
              icon={<CreditCard aria-hidden="true" />}
              title="Payment"
              description="Demo store: the order is simulated as payment by invoice. No payment is taken."
            />

            <div className="mt-5 flex items-center gap-3 rounded-2xl border-2 border-indigo-500 bg-indigo-50/40 p-4">
              <span className="grid size-5 place-items-center rounded-full border-2 border-indigo-600" aria-hidden="true">
                <span className="size-2.5 rounded-full bg-indigo-600" />
              </span>
              <div>
                <p className="text-sm font-semibold text-slate-900">Pay by invoice</p>
                <p className="text-xs text-slate-500">Due 14 days after delivery.</p>
              </div>
            </div>

            <label className="mt-4 flex cursor-pointer items-start gap-3 rounded-2xl border border-slate-200 p-4 transition-colors hover:bg-slate-50">
              <input
                type="checkbox"
                data-testid="accept-terms"
                checked={termsAccepted}
                onChange={(event) => setTermsAccepted(event.target.checked)}
                className="mt-0.5 size-4 shrink-0 rounded border-slate-300 accent-indigo-600"
              />
              <span className="text-sm text-slate-700">
                I accept the terms of service and the cancellation policy.
              </span>
            </label>
          </Card>
        </div>

        <div className="lg:sticky lg:top-24">
          <CheckoutSummary items={cart.state.items} totals={cart.state.totals} coupon={cart.state.coupon}>
            <Button
              type="submit"
              size="lg"
              className="w-full"
              data-testid="place-order"
              disabled={!canSubmit}
              loading={pending}
              icon={<Lock className="size-4" aria-hidden="true" />}
            >
              {pending ? 'Placing order…' : 'Place order'}
            </Button>
            <ul className="mt-4 flex items-center justify-center gap-4 text-xs text-slate-400">
              <li className="flex items-center gap-1.5">
                <ShieldCheck className="size-3.5" aria-hidden="true" />
                Secure checkout
              </li>
              <li className="flex items-center gap-1.5">
                <Undo2 className="size-3.5" aria-hidden="true" />
                Free 30-day returns
              </li>
            </ul>
          </CheckoutSummary>
        </div>
      </div>
    </form>
  )
}
