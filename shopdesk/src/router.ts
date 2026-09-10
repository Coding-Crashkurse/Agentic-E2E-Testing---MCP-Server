import { useSyncExternalStore } from 'react'

export type RouteName = 'catalog' | 'cart' | 'checkout' | 'confirmation'

/**
 * Hash-Routing ohne Bibliothek: Der Query-String (`?bug=…`) bleibt bei jeder Navigation erhalten,
 * Deep-Links wie `#/checkout` funktionieren auch nach einem Reload.
 */
export const ROUTES: Record<RouteName, string> = {
  catalog: '#/',
  cart: '#/cart',
  checkout: '#/checkout',
  confirmation: '#/confirmation',
}

export function parseRoute(hash: string): RouteName {
  const path = hash.replace(/^#/, '').replace(/\/+$/, '') || '/'
  switch (path) {
    case '/cart':
      return 'cart'
    case '/checkout':
      return 'checkout'
    case '/confirmation':
      return 'confirmation'
    default:
      return 'catalog'
  }
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener('hashchange', onChange)
  return () => window.removeEventListener('hashchange', onChange)
}

function getSnapshot(): string {
  return window.location.hash
}

function getServerSnapshot(): string {
  return ''
}

export function useRoute(): RouteName {
  return parseRoute(useSyncExternalStore(subscribe, getSnapshot, getServerSnapshot))
}

export function navigate(route: RouteName): void {
  window.location.hash = ROUTES[route]
}
