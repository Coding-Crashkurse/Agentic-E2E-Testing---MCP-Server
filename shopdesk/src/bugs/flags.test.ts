import { afterEach, describe, expect, it, vi } from 'vitest'
import catalog from './catalog.json'
import { BUG_FLAGS, formatBugFlags, isBugFlag, NO_BUGS, parseBugFlags } from './flags'

describe('parseBugFlags', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('liest ein einzelnes Flag, auch mit Whitespace und Großschreibung', () => {
    expect([...parseBugFlags('coupon-noop')]).toEqual(['coupon-noop'])
    expect([...parseBugFlags(' Double-Submit ')]).toEqual(['double-submit'])
  })

  it('kombiniert mehrere Flags, kommagetrennt oder mit Leerzeichen, ohne Duplikate', () => {
    const bugs = parseBugFlags('coupon-noop, qty-stale-total flaky-race,coupon-noop')
    expect([...bugs]).toEqual(['coupon-noop', 'qty-stale-total', 'flaky-race'])
    expect(bugs.has('coupon-noop')).toBe(true)
    expect(bugs.has('double-submit')).toBe(false)
  })

  it('ergibt ohne Wert oder mit none eine leere Menge', () => {
    expect(parseBugFlags(null).size).toBe(0)
    expect(parseBugFlags('').size).toBe(0)
    expect(parseBugFlags(undefined).size).toBe(0)
    expect(parseBugFlags('none').size).toBe(0)
    expect(parseBugFlags('none,flaky-race').has('flaky-race')).toBe(true)
  })

  it('warnt bei unbekannten Flags und ignoriert sie', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    const bugs = parseBugFlags('gibt-es-nicht,coupon-noop')
    expect([...bugs]).toEqual(['coupon-noop'])
    expect(warn).toHaveBeenCalledOnce()
  })
})

describe('formatBugFlags', () => {
  it('gibt none oder die Liste zurück', () => {
    expect(formatBugFlags(NO_BUGS)).toBe('none')
    expect(formatBugFlags(parseBugFlags('flaky-race,coupon-noop'))).toBe('flaky-race,coupon-noop')
  })
})

describe('catalog.json', () => {
  it('beschreibt genau die Flags außer none', () => {
    const documented = Object.keys(catalog).sort()
    const expected = BUG_FLAGS.filter((flag) => flag !== 'none').sort()
    expect(documented).toEqual(expected)
    expect(documented.every(isBugFlag)).toBe(true)
  })

  it('hat für jedes Flag Symptom und Ursache', () => {
    for (const entry of Object.values(catalog)) {
      expect(entry.symptom.length).toBeGreaterThan(10)
      expect(entry.cause.length).toBeGreaterThan(10)
    }
  })
})
