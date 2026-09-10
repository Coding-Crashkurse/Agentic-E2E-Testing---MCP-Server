import { Package, SearchX, Truck, Undo2 } from 'lucide-react'
import { useMemo, useState, type ReactNode } from 'react'
import { useBugs } from '../bugs/bugContext'
import { FilterBar } from '../components/catalog/FilterBar'
import { ProductGrid } from '../components/catalog/ProductGrid'
import { useToast } from '../components/toast/toastContext'
import { Button } from '../components/ui/Button'
import { EmptyState } from '../components/ui/EmptyState'
import { PRODUCTS, type Product } from '../data/products'
import { DEFAULT_FILTER, filterProducts, type CatalogFilter } from '../lib/filters'
import { formatCents } from '../lib/money'
import { FREE_SHIPPING_FROM } from '../store/cart'
import { useCart } from '../store/cartContext'

function HeroStat({ icon, children }: { icon: ReactNode; children: ReactNode }) {
  return (
    <li className="flex items-center gap-2 rounded-full bg-white/10 py-2 pr-4 pl-3 text-sm text-slate-100 ring-1 ring-white/10 backdrop-blur">
      <span className="text-indigo-300 [&>svg]:size-4">{icon}</span>
      {children}
    </li>
  )
}

function CatalogHero() {
  return (
    <section className="relative overflow-hidden rounded-3xl bg-slate-950 px-7 py-6 text-white shadow-lift">
      <div aria-hidden="true" className="absolute -top-28 -left-10 size-72 rounded-full bg-indigo-500/50 blur-3xl" />
      <div aria-hidden="true" className="absolute -right-10 -bottom-32 size-80 rounded-full bg-fuchsia-500/35 blur-3xl" />
      <div className="relative flex flex-wrap items-center justify-between gap-5">
        <div>
          <p className="text-[11px] font-semibold tracking-[0.18em] text-indigo-300 uppercase">Catalog</p>
          <h1 className="mt-1.5 text-[26px] leading-tight font-semibold tracking-tight text-balance">
            Everyday objects, thoughtfully made.
          </h1>
        </div>
        <ul className="flex flex-wrap gap-2">
          <HeroStat icon={<Package aria-hidden="true" />}>{PRODUCTS.length} products</HeroStat>
          <HeroStat icon={<Truck aria-hidden="true" />}>Free shipping from {formatCents(FREE_SHIPPING_FROM)}</HeroStat>
          <HeroStat icon={<Undo2 aria-hidden="true" />}>Free 30-day returns</HeroStat>
        </ul>
      </div>
    </section>
  )
}

export function CatalogView() {
  const bugs = useBugs()
  const { add } = useCart()
  const toast = useToast()
  const [filter, setFilter] = useState<CatalogFilter>(DEFAULT_FILTER)
  const visible = useMemo(() => filterProducts(PRODUCTS, filter, bugs), [filter, bugs])

  function handleAdd(product: Product) {
    add(product)
    // Der Toast meldet Erfolg unabhängig davon, ob der Reducer den Artikel angenommen hat (siehe flaky-race).
    toast.success(`“${product.name}” was added to your cart.`)
  }

  return (
    <div data-testid="catalog-view" className="flex flex-col gap-4">
      <CatalogHero />
      <FilterBar filter={filter} onChange={setFilter} resultCount={visible.length} totalCount={PRODUCTS.length} />
      {visible.length === 0 ? (
        <EmptyState
          data-testid="catalog-empty"
          icon={<SearchX aria-hidden="true" />}
          title="No products found"
          description="Nothing matches the current search and filters."
          action={
            <Button variant="secondary" data-testid="catalog-empty-reset" onClick={() => setFilter(DEFAULT_FILTER)}>
              Reset filters
            </Button>
          }
        />
      ) : (
        <ProductGrid products={visible} onAdd={handleAdd} />
      )}
    </div>
  )
}
