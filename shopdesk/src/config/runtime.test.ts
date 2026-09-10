import { afterEach, describe, expect, it, vi } from 'vitest'
import { readRuntimeOptions } from './runtime'

describe('readRuntimeOptions', () => {
  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('liest die Bug-Flags aus der Build-Umgebung', () => {
    const bugs = readRuntimeOptions('', { VITE_BUG: 'double-submit,coupon-noop' }).bugs
    expect([...bugs]).toEqual(['double-submit', 'coupon-noop'])
    expect(readRuntimeOptions('', {}).bugs.size).toBe(0)
    expect(readRuntimeOptions('', { VITE_BUG: '' }).bugs.size).toBe(0)
  })

  it('ignoriert einen bug-Parameter in der URL und warnt', () => {
    const warn = vi.spyOn(console, 'warn').mockImplementation(() => {})
    expect(readRuntimeOptions('?bug=coupon-noop', { VITE_BUG: '' }).bugs.size).toBe(0)
    expect(warn).toHaveBeenCalledOnce()
  })

  it('schaltet Animationen nur per ?motion=off ab', () => {
    expect(readRuntimeOptions('', {}).motion).toBe(true)
    expect(readRuntimeOptions('?motion=off', {}).motion).toBe(false)
    expect(readRuntimeOptions('?motion=on', {}).motion).toBe(true)
  })
})
