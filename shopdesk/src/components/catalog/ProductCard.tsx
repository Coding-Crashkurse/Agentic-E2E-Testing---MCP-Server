import { Plus } from 'lucide-react'
import { productImage, type Product } from '../../data/products'
import { cn } from '../../lib/cn'
import { formatCents } from '../../lib/money'
import { Badge } from '../ui/Badge'
import { Button } from '../ui/Button'

interface ProductCardProps {
  product: Product
  onAdd: (product: Product) => void
}

export function ProductCard({ product, onAdd }: ProductCardProps) {
  return (
    <article
      data-testid="product-card"
      data-product-id={product.id}
      data-in-stock={product.inStock ? 'true' : 'false'}
      className="group relative flex h-full flex-col overflow-hidden rounded-3xl bg-white shadow-card ring-1 ring-slate-900/5 transition-[transform,box-shadow] duration-300 hover:-translate-y-1 hover:shadow-lift"
    >
      <div className="relative aspect-square overflow-hidden bg-slate-100">
        <img
          src={productImage(product)}
          alt={product.name}
          width={800}
          height={800}
          decoding="async"
          className={cn(
            'size-full object-cover transition-transform duration-500 group-hover:scale-[1.04]',
            !product.inStock && 'opacity-70 saturate-50',
          )}
        />
        <Badge
          dot
          tone={product.inStock ? 'success' : 'neutral'}
          data-testid="product-stock"
          className="absolute top-3 left-3 shadow-sm backdrop-blur"
        >
          {product.inStock ? 'In stock' : 'Sold out'}
        </Badge>
      </div>

      <div className="flex flex-1 flex-col gap-2 p-4">
        <p
          data-testid="product-category"
          className="text-[11px] font-semibold tracking-[0.14em] text-indigo-600 uppercase"
        >
          {product.category}
        </p>
        <h3 data-testid="product-name" className="text-[15px] font-semibold tracking-tight text-slate-900">
          {product.name}
        </h3>
        <p className="line-clamp-2 text-sm leading-relaxed text-slate-500">{product.description}</p>

        <div className="mt-auto flex items-baseline justify-between pt-2">
          <span data-testid="product-price" className="text-xl font-semibold tracking-tight text-slate-900 tabular-nums">
            {formatCents(product.price)}
          </span>
          <span className="text-xs text-slate-400">incl. VAT</span>
        </div>
        <Button
          size="sm"
          className="w-full"
          data-testid="add-to-cart"
          disabled={!product.inStock}
          icon={<Plus className="size-4" aria-hidden="true" />}
          onClick={() => onAdd(product)}
        >
          {product.inStock ? 'Add to cart' : 'Sold out'}
        </Button>
      </div>
    </article>
  )
}
