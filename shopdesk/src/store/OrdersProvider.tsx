import { useCallback, useMemo, useRef, useState, type ReactNode } from 'react'
import { FIRST_ORDER_NUMBER, OrdersContext, type Order, type OrderDraft, type OrdersApi } from './ordersContext'

/** Simulierte Backend-Latenz. Lang genug, dass ein Doppelklick innerhalb des Fensters landet. */
const ORDER_PROCESSING_MS = 1200

function delay(ms: number): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

export function OrdersProvider({ children }: { children: ReactNode }) {
  const [orders, setOrders] = useState<Order[]>([])
  const nextNumber = useRef(FIRST_ORDER_NUMBER)

  const placeOrder = useCallback(async (draft: OrderDraft): Promise<Order> => {
    await delay(ORDER_PROCESSING_MS)
    const order: Order = { ...draft, number: nextNumber.current }
    nextNumber.current += 1
    setOrders((previous) => [...previous, order])
    return order
  }, [])

  const api = useMemo<OrdersApi>(() => ({ orders, placeOrder }), [orders, placeOrder])

  return <OrdersContext.Provider value={api}>{children}</OrdersContext.Provider>
}
