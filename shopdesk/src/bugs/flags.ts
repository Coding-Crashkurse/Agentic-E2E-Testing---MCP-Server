/**
 * Bug-Flags von ShopDesk.
 *
 * Jedes Flag steht für einen ABSICHTLICH eingebauten Fehler. Die aktiven Flags werden beim Start
 * festgelegt (`npm run dev -- --bug=coupon-noop,qty-stale-total`, siehe scripts/shopdesk.mjs)
 * und sind im Bundle eingebrannt. Ohne Flag verhält sich die App korrekt. Mehrere Flags dürfen
 * kombiniert werden; jede Injektionsstelle prüft nur ihr eigenes Flag.
 *
 * Symptom und Ursache je Flag stehen in `catalog.json` – bewusst NICHT hier importiert, damit
 * der Katalog nicht im ausgelieferten Bundle landet. Launcher, Tests und README lesen ihn direkt.
 * Alle Injektionsstellen im Code sind mit `// BUG <flag>:` kommentiert –
 * `grep -rn "BUG " src` listet sie vollständig auf.
 */
export const BUG_FLAGS = [
  'none',
  'coupon-noop',
  'remove-off-by-one',
  'qty-stale-total',
  'filter-ignored',
  'submit-disabled',
  'save-not-persisted',
  'double-submit',
  'flaky-race',
] as const

export type BugFlag = (typeof BUG_FLAGS)[number]

/** Ein tatsächlich einschaltbarer Fehler (`none` ist nur der Name für „nichts aktiv“). */
export type ActiveBug = Exclude<BugFlag, 'none'>

/** Menge der aktiven Fehler – leer bedeutet: alles funktioniert. */
export type BugSet = ReadonlySet<ActiveBug>

export const NO_BUGS: BugSet = new Set<ActiveBug>()

const KNOWN_FLAGS: ReadonlySet<string> = new Set(BUG_FLAGS)

export function isBugFlag(value: string): value is BugFlag {
  return KNOWN_FLAGS.has(value)
}

/**
 * Zerlegt eine Liste wie `"coupon-noop, qty-stale-total"` in ein Set.
 * Leerstring und `none` ergeben keine Einträge, Unbekanntes wird mit Warnung ignoriert.
 */
export function parseBugFlags(raw: string | null | undefined): BugSet {
  const bugs = new Set<ActiveBug>()
  for (const token of (raw ?? '').split(/[\s,]+/)) {
    const value = token.trim().toLowerCase()
    if (value === '' || value === 'none') continue
    if (isBugFlag(value) && value !== 'none') {
      bugs.add(value)
    } else {
      console.warn(`[ShopDesk] Unknown bug flag "${token}" – ignored.`)
    }
  }
  return bugs
}

/** Gegenstück zu `parseBugFlags`, z. B. für Log-Ausgaben: `"none"` oder `"coupon-noop,flaky-race"`. */
export function formatBugFlags(bugs: BugSet): string {
  return bugs.size === 0 ? 'none' : [...bugs].join(',')
}
