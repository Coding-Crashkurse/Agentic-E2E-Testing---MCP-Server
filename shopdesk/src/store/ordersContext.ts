import { createContext, useContext } from 'react'
import type { Coupon } from '../data/coupons'
import type { Address } from '../lib/address'
import type { CartItem, CartTotals } from './cart'

/** Erste Bestellnummer einer Sitzung – fortlaufend, ohne Zufall oder Zeitstempel. */
export const FIRST_ORDER_NUMBER = 10001

export interface OrderDraft {
  items: readonly CartItem[]
  totals: CartTotals
  coupon: Coupon | null
  address: Address
}

export interface Order extends OrderDraft {
  number: number
}

export interface OrdersApi {
  orders: readonly Order[]
  /** Simuliert das Backend (feste Latenz) und legt danach die Bestellung an. */
  placeOrder: (draft: OrderDraft) => Promise<Order>
}

export const OrdersContext = createContext<OrdersApi | null>(null)

export function useOrders(): OrdersApi {
  const api = useContext(OrdersContext)
  if (!api) {
    throw new Error('useOrders() muss innerhalb von <OrdersProvider> verwendet werden.')
  }
  return api
}

export function countItems(items: readonly CartItem[]): number {
  return items.reduce((sum, item) => sum + item.quantity, 0)
}
