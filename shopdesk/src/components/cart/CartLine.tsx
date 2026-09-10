import { Minus, Plus, Trash2 } from 'lucide-react'
import { productImage } from '../../data/products'
import { formatCents } from '../../lib/money'
import { MAX_QUANTITY, type CartItem } from '../../store/cart'
import { useCart } from '../../store/cartContext'
import { useToast } from '../toast/toastContext'
import { Button } from '../ui/Button'

interface CartLineProps {
  item: CartItem
  position: number
}

export function CartLine({ item, position }: CartLineProps) {
  const { setQuantity, remove } = useCart()
  const toast = useToast()
  const { product, quantity } = item

  function handleRemove() {
    remove(product.id)
    toast.info(`“${product.name}” was removed from your cart.`)
  }

  return (
    <li
      data-testid="cart-line"
      data-product-id={product.id}
      data-position={position}
      className="flex items-center gap-5 p-5"
    >
      <img
        src={productImage(product)}
        alt=""
        width={96}
        height={96}
        className="size-24 shrink-0 rounded-2xl object-cover ring-1 ring-slate-900/5"
      />

      <div className="min-w-0 flex-1">
        <p className="text-[11px] font-semibold tracking-[0.14em] text-indigo-600 uppercase">{product.category}</p>
        <h3 data-testid="line-name" className="mt-0.5 truncate text-[15px] font-semibold tracking-tight text-slate-900">
          {product.name}
        </h3>
        <p className="mt-0.5 text-sm text-slate-500">
          <span data-testid="line-unit-price">{formatCents(product.price)}</span> each
        </p>
      </div>

      <div
        role="group"
        aria-label={`Quantity for ${product.name}`}
        className="flex items-center gap-0.5 rounded-full bg-slate-100 p-1"
      >
        <Button
          variant="secondary"
          size="icon"
          data-testid="qty-decrease"
          aria-label="Decrease quantity"
          disabled={quantity <= 1}
          onClick={() => setQuantity(product.id, quantity - 1)}
        >
          <Minus className="size-3.5" aria-hidden="true" />
        </Button>
        <span data-testid="qty-value" className="w-9 text-center text-sm font-semibold tabular-nums">
          {quantity}
        </span>
        <Button
          variant="secondary"
          size="icon"
          data-testid="qty-increase"
          aria-label="Increase quantity"
          disabled={quantity >= MAX_QUANTITY}
          onClick={() => setQuantity(product.id, quantity + 1)}
        >
          <Plus className="size-3.5" aria-hidden="true" />
        </Button>
      </div>

      <span
        data-testid="line-total"
        className="w-24 text-right text-[15px] font-semibold tracking-tight text-slate-900 tabular-nums"
      >
        {formatCents(product.price * quantity)}
      </span>

      <Button
        variant="danger"
        size="icon"
        data-testid="remove-line"
        aria-label={`Remove ${product.name}`}
        onClick={handleRemove}
      >
        <Trash2 className="size-4" aria-hidden="true" />
      </Button>
    </li>
  )
}
