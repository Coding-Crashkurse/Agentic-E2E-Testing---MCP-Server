import { createContext, useContext } from 'react'
import type { Address } from '../lib/address'

export interface CustomerApi {
  /** Aktuelle Lieferadresse (gespeichert oder Demo-Vorgabe). */
  address: Address
  saveAddress: (address: Address) => void
}

export const CustomerContext = createContext<CustomerApi | null>(null)

export function useCustomer(): CustomerApi {
  const api = useContext(CustomerContext)
  if (!api) {
    throw new Error('useCustomer() muss innerhalb von <CustomerProvider> verwendet werden.')
  }
  return api
}
