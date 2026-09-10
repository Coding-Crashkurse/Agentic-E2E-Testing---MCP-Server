import { useMemo, useReducer, type ReactNode } from 'react'
import { useBugs } from '../bugs/bugContext'
import { createCartReducer, EMPTY_CART } from './cart'
import { CartContext, type CartApi } from './cartContext'

export function CartProvider({ children }: { children: ReactNode }) {
  const bugs = useBugs()
  const reducer = useMemo(() => createCartReducer(bugs), [bugs])
  const [state, dispatch] = useReducer(reducer, EMPTY_CART)

  const api = useMemo<CartApi>(
    () => ({
      state,
      add: (product) => dispatch({ type: 'add', product }),
      setQuantity: (productId, quantity) => dispatch({ type: 'setQuantity', productId, quantity }),
      remove: (productId) => dispatch({ type: 'remove', productId }),
      applyCoupon: (coupon) => dispatch({ type: 'applyCoupon', coupon }),
      removeCoupon: () => dispatch({ type: 'removeCoupon' }),
      clear: () => dispatch({ type: 'clear' }),
    }),
    [state],
  )

  return <CartContext.Provider value={api}>{children}</CartContext.Provider>
}
