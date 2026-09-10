import type { Product } from '../../data/products'
import { ProductCard } from './ProductCard'

interface ProductGridProps {
  products: readonly Product[]
  onAdd: (product: Product) => void
}

export function ProductGrid({ products, onAdd }: ProductGridProps) {
  return (
    <ul data-testid="product-grid" className="grid grid-cols-1 gap-5 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
      {products.map((product) => (
        <li key={product.id}>
          <ProductCard product={product} onAdd={onAdd} />
        </li>
      ))}
    </ul>
  )
}
