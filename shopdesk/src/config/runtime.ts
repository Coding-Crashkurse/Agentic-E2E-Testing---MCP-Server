import { parseBugFlags, type BugSet } from '../bugs/flags'

export interface RuntimeOptions {
  /** Aktive Bugs – beim Start festgelegt, nicht zur Laufzeit umschaltbar. Leer = alles funktioniert. */
  bugs: BugSet
  /** `false`, wenn Animationen und Transitions per `?motion=off` deaktiviert wurden. */
  motion: boolean
}

/** Ausschnitt aus `import.meta.env`, den die App benötigt. */
export interface RuntimeEnv {
  VITE_BUG?: string
}

/**
 * Die Bugs kommen aus der Build-Umgebung (`--bug=<flag>[,<flag>…]` im Launcher setzt `VITE_BUG`)
 * und sind damit im Bundle eingebrannt. Die URL kann sie nicht umschalten – ein `bug`-Parameter
 * wird bewusst ignoriert. `?motion=off` bleibt ein reiner Anzeige-Schalter für stabile Screenshots.
 */
export function readRuntimeOptions(search: string, env: RuntimeEnv): RuntimeOptions {
  const params = new URLSearchParams(search)
  if (params.has('bug')) {
    console.warn('[ShopDesk] Bug flags are fixed at start-up – the "bug" URL parameter is ignored.')
  }
  return {
    bugs: parseBugFlags(env.VITE_BUG),
    motion: params.get('motion') !== 'off',
  }
}
