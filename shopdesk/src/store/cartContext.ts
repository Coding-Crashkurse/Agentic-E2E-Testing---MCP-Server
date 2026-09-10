import { createContext, useContext } from 'react'
import type { Coupon } from '../data/coupons'
import type { Product } from '../data/products'
import type { CartState } from './cart'

export interface CartApi {
  state: CartState
  add: (product: Product) => void
  setQuantity: (productId: string, quantity: number) => void
  remove: (productId: string) => void
  applyCoupon: (coupon: Coupon) => void
  removeCoupon: () => void
  clear: () => void
}

export const CartContext = createContext<CartApi | null>(null)

export function useCart(): CartApi {
  const api = useContext(CartContext)
  if (!api) {
    throw new Error('useCart() muss innerhalb von <CartProvider> verwendet werden.')
  }
  return api
}
