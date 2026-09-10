import type { ReactNode } from 'react'
import { BugContext } from './bugContext'
import type { BugSet } from './flags'

interface BugProviderProps {
  bugs: BugSet
  children: ReactNode
}

export function BugProvider({ bugs, children }: BugProviderProps) {
  return <BugContext.Provider value={bugs}>{children}</BugContext.Provider>
}
