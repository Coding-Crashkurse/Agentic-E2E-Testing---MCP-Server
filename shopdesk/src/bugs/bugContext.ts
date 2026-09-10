import { createContext, useContext } from 'react'
import { NO_BUGS, type BugSet } from './flags'

export const BugContext = createContext<BugSet>(NO_BUGS)

/** Liefert die aktiven Bugs – Injektionsstellen prüfen damit `bugs.has('<flag>')`. */
export function useBugs(): BugSet {
  return useContext(BugContext)
}
