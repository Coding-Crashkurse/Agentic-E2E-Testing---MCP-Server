import { ArrowLeft, ArrowRight, ShoppingCart } from 'lucide-react'
import { CartLine } from '../components/cart/CartLine'
import { CartSummary } from '../components/cart/CartSummary'
import { CouponForm } from '../components/cart/CouponForm'
import { buttonClassName } from '../components/ui/buttonStyles'
import { Card } from '../components/ui/Card'
import { EmptyState } from '../components/ui/EmptyState'
import { PageHeader } from '../components/ui/PageHeader'
import { ROUTES } from '../router'
import { useCart } from '../store/cartContext'

export function CartView() {
  const { state } = useCart()

  if (state.items.length === 0) {
    return (
      <EmptyState
        data-testid="cart-empty"
        icon={<ShoppingCart aria-hidden="true" />}
        title="Your cart is empty"
        description="Add products from the catalog to proceed to checkout."
        action={
          <a href={ROUTES.catalog} data-testid="go-to-catalog" className={buttonClassName()}>
            Browse the catalog
          </a>
        }
      />
    )
  }

  const lines = state.items.length

  return (
    <div data-testid="cart-view" className="flex flex-col gap-6">
      <PageHeader title="Your cart" description={`${lines} ${lines === 1 ? 'product' : 'products'} in your cart`}>
        <a href={ROUTES.catalog} className={buttonClassName({ variant: 'ghost', size: 'sm' })}>
          <ArrowLeft className="size-4" aria-hidden="true" />
          Continue shopping
        </a>
      </PageHeader>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,1fr)_380px] lg:items-start">
        <Card padded={false}>
          <ul data-testid="cart-lines" className="divide-y divide-slate-100">
            {state.items.map((item, index) => (
              <CartLine key={item.product.id} item={item} position={index} />
            ))}
          </ul>
        </Card>

        <div className="flex flex-col gap-4 lg:sticky lg:top-24">
          <CouponForm />
          <CartSummary totals={state.totals} coupon={state.coupon}>
            <a
              href={ROUTES.checkout}
              data-testid="go-to-checkout"
              className={buttonClassName({ size: 'lg', className: 'w-full' })}
            >
              Proceed to checkout
              <ArrowRight className="size-5" aria-hidden="true" />
            </a>
          </CartSummary>
        </div>
      </div>
    </div>
  )
}
