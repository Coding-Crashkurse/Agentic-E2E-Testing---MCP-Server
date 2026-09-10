import { PackageOpen } from 'lucide-react'
import { CheckoutForm } from '../components/checkout/CheckoutForm'
import { buttonClassName } from '../components/ui/buttonStyles'
import { EmptyState } from '../components/ui/EmptyState'
import { ROUTES } from '../router'
import { useCart } from '../store/cartContext'

export function CheckoutView() {
  const { state } = useCart()

  if (state.items.length === 0) {
    return (
      <EmptyState
        data-testid="checkout-empty"
        icon={<PackageOpen aria-hidden="true" />}
        title="Nothing to check out"
        description="Checkout needs at least one item. The cart is only kept for the current session."
        action={
          <a href={ROUTES.catalog} data-testid="go-to-catalog" className={buttonClassName()}>
            Browse the catalog
          </a>
        }
      />
    )
  }

  return <CheckoutForm />
}
