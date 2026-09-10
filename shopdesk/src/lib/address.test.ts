import { describe, expect, it } from 'vitest'
import { NO_BUGS, type BugSet } from '../bugs/flags'
import { DEMO_CUSTOMER } from '../data/customer'
import { EMPTY_ADDRESS, isAddressValid, normalizeAddress, validateAddress } from './address'

const SUBMIT_DISABLED: BugSet = new Set(['submit-disabled'])

describe('validateAddress', () => {
  it('akzeptiert die Demo-Kundin ohne Bugs (Whitespace wird getrimmt)', () => {
    expect(DEMO_CUSTOMER.email.endsWith(' ')).toBe(true)
    expect(isAddressValid(DEMO_CUSTOMER, NO_BUGS)).toBe(true)
    expect(isAddressValid(DEMO_CUSTOMER)).toBe(true)
  })

  it('submit-disabled: Whitespace am Ende der E-Mail lässt die Validierung scheitern', () => {
    const errors = validateAddress(DEMO_CUSTOMER, SUBMIT_DISABLED)
    expect(Object.keys(errors)).toEqual(['email'])
  })

  it('submit-disabled: eine sauber eingetippte E-Mail bleibt gültig', () => {
    const typed = { ...DEMO_CUSTOMER, email: 'anna.schmidt@example.com' }
    expect(isAddressValid(typed, SUBMIT_DISABLED)).toBe(true)
  })

  it('meldet alle Pflichtfelder bei leerer Adresse', () => {
    const errors = validateAddress(EMPTY_ADDRESS)
    expect(Object.keys(errors).sort()).toEqual(['city', 'email', 'name', 'street', 'zip'])
  })

  it('verlangt eine fünfstellige PLZ', () => {
    expect(validateAddress({ ...DEMO_CUSTOMER, zip: '1011' }).zip).toBeDefined()
    expect(validateAddress({ ...DEMO_CUSTOMER, zip: '10115' }).zip).toBeUndefined()
  })
})

describe('normalizeAddress', () => {
  it('trimmt alle Felder und schreibt die E-Mail klein', () => {
    const normalized = normalizeAddress({
      name: '  Anna Schmidt ',
      email: ' Anna.Schmidt@Example.com ',
      street: ' Lindenweg 12 ',
      zip: ' 10115 ',
      city: ' Berlin ',
    })
    expect(normalized).toEqual({
      name: 'Anna Schmidt',
      email: 'anna.schmidt@example.com',
      street: 'Lindenweg 12',
      zip: '10115',
      city: 'Berlin',
    })
  })
})
