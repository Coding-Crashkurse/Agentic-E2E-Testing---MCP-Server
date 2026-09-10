import { useEffect } from 'react'
import { BugProvider } from './bugs/BugProvider'
import { Footer } from './components/layout/Footer'
import { Header } from './components/layout/Header'
import { ToastProvider } from './components/toast/ToastProvider'
import type { RuntimeOptions } from './config/runtime'
import { useRoute, type RouteName } from './router'
import { CartProvider } from './store/CartProvider'
import { CustomerProvider } from './store/CustomerProvider'
import { OrdersProvider } from './store/OrdersProvider'
import { CartView } from './views/CartView'
import { CatalogView } from './views/CatalogView'
import { CheckoutView } from './views/CheckoutView'
import { ConfirmationView } from './views/ConfirmationView'

const TITLES: Record<RouteName, string> = {
  catalog: 'Catalog · ShopDesk',
  cart: 'Cart · ShopDesk',
  checkout: 'Checkout · ShopDesk',
  confirmation: 'Order confirmation · ShopDesk',
}

function View({ route }: { route: RouteName }) {
  switch (route) {
    case 'cart':
      return <CartView />
    case 'checkout':
      return <CheckoutView />
    case 'confirmation':
      return <ConfirmationView />
    default:
      return <CatalogView />
  }
}

function Shell() {
  const route = useRoute()

  useEffect(() => {
    document.title = TITLES[route]
    window.scrollTo({ top: 0 })
  }, [route])

  return (
    <div className="relative flex min-h-screen flex-col">
      <div aria-hidden="true" className="bg-aurora pointer-events-none absolute inset-x-0 top-0 h-[42rem]" />
      <Header />
      <main id="main" data-route={route} className="relative mx-auto w-full max-w-6xl flex-1 px-6 py-5">
        <div key={route} className="animate-fade-up">
          <View route={route} />
        </div>
      </main>
      <Footer />
    </div>
  )
}

interface AppProps {
  options: RuntimeOptions
}

export function App({ options }: AppProps) {
  return (
    <BugProvider bugs={options.bugs}>
      <ToastProvider>
        <CustomerProvider>
          <CartProvider>
            <OrdersProvider>
              <Shell />
            </OrdersProvider>
          </CartProvider>
        </CustomerProvider>
      </ToastProvider>
    </BugProvider>
  )
}
