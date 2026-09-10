import { ShoppingBag, ShoppingCart } from 'lucide-react'
import type { ReactNode } from 'react'
import { cn } from '../../lib/cn'
import { ROUTES, useRoute } from '../../router'
import { useCart } from '../../store/cartContext'
import { useCustomer } from '../../store/customerContext'

interface NavLinkProps {
  href: string
  active: boolean
  testId: string
  children: ReactNode
}

function NavLink({ href, active, testId, children }: NavLinkProps) {
  return (
    <a
      href={href}
      data-testid={testId}
      aria-current={active ? 'page' : undefined}
      className={cn(
        'rounded-full px-2 py-1.5 text-sm font-medium transition-[background-color,color,box-shadow] duration-200 sm:px-4',
        active ? 'bg-white text-slate-900 shadow-sm ring-1 ring-slate-900/5' : 'text-slate-600 hover:text-slate-900',
      )}
    >
      {children}
    </a>
  )
}

function initialsOf(name: string): string {
  return name
    .split(/\s+/)
    .filter(Boolean)
    .slice(0, 2)
    .map((part) => part.charAt(0).toUpperCase())
    .join('')
}

export function Header() {
  const route = useRoute()
  const { state } = useCart()
  const { address } = useCustomer()
  const count = state.totals.itemCount

  return (
    <header className="glass sticky top-0 z-40 border-b border-slate-900/5">
      <div className="mx-auto flex h-16 w-full max-w-6xl items-center justify-between gap-1 px-3 sm:gap-6 sm:px-6">
        <a href={ROUTES.catalog} data-testid="nav-home" className="flex items-center gap-2.5">
          <span className="grid size-9 place-items-center rounded-xl bg-linear-to-br from-indigo-500 via-violet-500 to-fuchsia-500 text-white shadow-glow">
            <ShoppingBag className="size-[18px]" aria-hidden="true" />
          </span>
          <span className="text-[17px] font-semibold tracking-tight text-slate-900">ShopDesk</span>
        </a>

        <nav aria-label="Main navigation" className="flex items-center gap-0.5 rounded-full bg-slate-900/5 p-1">
          <NavLink href={ROUTES.catalog} active={route === 'catalog'} testId="nav-catalog">
            Catalog
          </NavLink>
          <NavLink href={ROUTES.cart} active={route === 'cart'} testId="nav-cart">
            Cart
          </NavLink>
        </nav>

        <div className="flex items-center gap-3">
          <span className="hidden items-center gap-2 rounded-full bg-white py-1 pr-3.5 pl-1.5 text-sm font-medium text-slate-700 shadow-xs ring-1 ring-slate-900/5 sm:inline-flex">
            <span
              aria-hidden="true"
              className="grid size-6 place-items-center rounded-full bg-linear-to-br from-indigo-500 to-violet-500 text-[10px] font-bold text-white"
            >
              {initialsOf(address.name)}
            </span>
            <span data-testid="customer-name">{address.name}</span>
          </span>
          <a
            href={ROUTES.cart}
            data-testid="cart-button"
            aria-label={`Cart, ${count} ${count === 1 ? 'item' : 'items'}`}
            className="relative grid size-10 place-items-center rounded-full bg-slate-900 text-white shadow-sm transition-colors hover:bg-slate-800"
          >
            <ShoppingCart className="size-[18px]" aria-hidden="true" />
            <span
              data-testid="cart-badge"
              className={cn(
                'absolute -top-1 -right-1 min-w-5 rounded-full px-1.5 text-center text-[11px] leading-5 font-semibold tabular-nums ring-2 ring-white',
                count > 0 ? 'bg-linear-to-r from-indigo-500 to-violet-500 text-white' : 'bg-slate-200 text-slate-600',
              )}
            >
              {count}
            </span>
          </a>
        </div>
      </div>
    </header>
  )
}
