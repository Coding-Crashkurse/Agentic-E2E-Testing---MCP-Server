import { describe, expect, it } from 'vitest'
import { parseRoute, ROUTES } from './router'

describe('parseRoute', () => {
  it('ordnet Hash-Pfade den Views zu', () => {
    expect(parseRoute('')).toBe('catalog')
    expect(parseRoute('#/')).toBe('catalog')
    expect(parseRoute('#/cart')).toBe('cart')
    expect(parseRoute('#/cart/')).toBe('cart')
    expect(parseRoute('#/checkout')).toBe('checkout')
    expect(parseRoute('#/confirmation')).toBe('confirmation')
  })

  it('fällt bei unbekannten Pfaden auf den Katalog zurück', () => {
    expect(parseRoute('#/gibt-es-nicht')).toBe('catalog')
  })

  it('kann alle definierten Routen wieder auflösen', () => {
    for (const [name, hash] of Object.entries(ROUTES)) {
      expect(parseRoute(hash)).toBe(name)
    }
  })
})
