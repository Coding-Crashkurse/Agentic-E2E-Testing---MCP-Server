import { NO_BUGS, type BugSet } from '../bugs/flags'

export interface Address {
  name: string
  email: string
  street: string
  zip: string
  city: string
}

export type AddressField = keyof Address
export type AddressErrors = Partial<Record<AddressField, string>>

export const ADDRESS_FIELDS: readonly AddressField[] = ['name', 'email', 'street', 'zip', 'city']

export const EMPTY_ADDRESS: Address = { name: '', email: '', street: '', zip: '', city: '' }

const EMAIL_PATTERN = /^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/
const ZIP_PATTERN = /^\d{5}$/

/** Trimmt alle Felder und normalisiert die E-Mail-Adresse – wird vor Speichern und Bestellen angewendet. */
export function normalizeAddress(address: Address): Address {
  return {
    name: address.name.trim(),
    email: address.email.trim().toLowerCase(),
    street: address.street.trim(),
    zip: address.zip.trim(),
    city: address.city.trim(),
  }
}

export function validateAddress(address: Address, bugs: BugSet = NO_BUGS): AddressErrors {
  const errors: AddressErrors = {}

  if (address.name.trim().length < 2) {
    errors.name = 'Please enter your name.'
  }

  // BUG submit-disabled: Validierung ohne .trim() – das Leerzeichen aus dem Kundenimport
  // lässt eine eigentlich gültige E-Mail-Adresse durchfallen.
  const email = bugs.has('submit-disabled') ? address.email : address.email.trim()
  if (!EMAIL_PATTERN.test(email)) {
    errors.email = 'Please enter a valid email address.'
  }

  if (address.street.trim().length < 3) {
    errors.street = 'Please enter your street and house number.'
  }
  if (!ZIP_PATTERN.test(address.zip.trim())) {
    errors.zip = 'The ZIP code must have 5 digits.'
  }
  if (address.city.trim().length < 2) {
    errors.city = 'Please enter your city.'
  }

  return errors
}

export function isAddressValid(address: Address, bugs: BugSet = NO_BUGS): boolean {
  return Object.keys(validateAddress(address, bugs)).length === 0
}
