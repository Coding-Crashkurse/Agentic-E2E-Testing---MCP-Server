import { ADDRESS_FIELDS, type Address } from './address'

const ADDRESS_KEY = 'shopdesk:address:v1'

function storage(): Storage | null {
  try {
    return window.localStorage
  } catch {
    return null
  }
}

function isAddress(value: unknown): value is Address {
  if (typeof value !== 'object' || value === null) return false
  const record = value as Record<string, unknown>
  return ADDRESS_FIELDS.every((field) => typeof record[field] === 'string')
}

export function loadSavedAddress(): Address | null {
  const raw = storage()?.getItem(ADDRESS_KEY)
  if (!raw) return null
  try {
    const parsed: unknown = JSON.parse(raw)
    return isAddress(parsed) ? parsed : null
  } catch {
    return null
  }
}

export function persistAddress(address: Address): void {
  storage()?.setItem(ADDRESS_KEY, JSON.stringify(address))
}

export function clearSavedAddress(): void {
  storage()?.removeItem(ADDRESS_KEY)
}
