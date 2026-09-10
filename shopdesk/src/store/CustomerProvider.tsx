import { useCallback, useMemo, useState, type ReactNode } from 'react'
import { useBugs } from '../bugs/bugContext'
import { DEMO_CUSTOMER } from '../data/customer'
import type { Address } from '../lib/address'
import { loadSavedAddress, persistAddress } from '../lib/storage'
import { CustomerContext, type CustomerApi } from './customerContext'

export function CustomerProvider({ children }: { children: ReactNode }) {
  const bugs = useBugs()
  const [address, setAddress] = useState<Address>(() => loadSavedAddress() ?? DEMO_CUSTOMER)

  const saveAddress = useCallback(
    (next: Address) => {
      setAddress(next)

      // BUG save-not-persisted: Nur der React-State wird aktualisiert – der Write in den
      // localStorage fehlt. Innerhalb der Sitzung sieht alles korrekt aus, nach einem Reload nicht mehr.
      if (!bugs.has('save-not-persisted')) {
        persistAddress(next)
      }
    },
    [bugs],
  )

  const api = useMemo<CustomerApi>(() => ({ address, saveAddress }), [address, saveAddress])

  return <CustomerContext.Provider value={api}>{children}</CustomerContext.Provider>
}
