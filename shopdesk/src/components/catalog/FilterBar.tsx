import { PackageCheck, Search, X } from 'lucide-react'
import { CATEGORIES, CATEGORY_SLUGS } from '../../data/products'
import { DEFAULT_FILTER, isFilterActive, type CatalogFilter } from '../../lib/filters'
import { Button } from '../ui/Button'
import { Chip } from '../ui/Chip'

interface FilterBarProps {
  filter: CatalogFilter
  onChange: (next: CatalogFilter) => void
  resultCount: number
  totalCount: number
}

export function FilterBar({ filter, onChange, resultCount, totalCount }: FilterBarProps) {
  const active = isFilterActive(filter)

  return (
    <section
      aria-label="Filters"
      data-testid="filter-bar"
      className="glass flex flex-wrap items-center gap-2 rounded-3xl p-2.5 shadow-card ring-1 ring-slate-900/5"
    >
      <label className="relative min-w-60 flex-1">
        <span className="sr-only">Search products</span>
        <Search
          className="pointer-events-none absolute top-1/2 left-3.5 size-4 -translate-y-1/2 text-slate-400"
          aria-hidden="true"
        />
        <input
          type="search"
          data-testid="filter-search"
          placeholder="Search products…"
          autoComplete="off"
          value={filter.query}
          onChange={(event) => onChange({ ...filter, query: event.target.value })}
          className="h-10 w-full rounded-2xl border border-transparent bg-slate-900/5 pr-3.5 pl-10 text-sm text-slate-900 transition-[background-color,border-color,box-shadow] duration-200 placeholder:text-slate-400 hover:bg-slate-900/[0.07] focus:border-indigo-400 focus:bg-white focus:ring-4 focus:ring-indigo-500/10 focus:outline-none"
        />
      </label>

      <div className="flex flex-wrap gap-1.5" role="group" aria-label="Category">
        <Chip
          active={filter.category === 'all'}
          data-testid="filter-category-all"
          onClick={() => onChange({ ...filter, category: 'all' })}
        >
          All
        </Chip>
        {CATEGORIES.map((category) => (
          <Chip
            key={category}
            active={filter.category === category}
            data-testid={`filter-category-${CATEGORY_SLUGS[category]}`}
            onClick={() => onChange({ ...filter, category })}
          >
            {category}
          </Chip>
        ))}
      </div>

      <span aria-hidden="true" className="mx-1 hidden h-6 w-px bg-slate-200 lg:block" />

      <Chip
        active={filter.inStockOnly}
        data-testid="filter-in-stock"
        icon={<PackageCheck className="size-4" aria-hidden="true" />}
        onClick={() => onChange({ ...filter, inStockOnly: !filter.inStockOnly })}
      >
        In stock only
      </Chip>

      {active ? (
        <Button
          variant="ghost"
          size="sm"
          data-testid="filter-reset"
          icon={<X className="size-4" aria-hidden="true" />}
          onClick={() => onChange(DEFAULT_FILTER)}
        >
          Reset
        </Button>
      ) : null}

      <p data-testid="result-count" className="ml-auto pr-2 text-sm text-slate-500">
        <span className="font-semibold text-slate-900 tabular-nums">{resultCount}</span> of {totalCount} products
      </p>
    </section>
  )
}
