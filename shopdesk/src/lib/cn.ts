export type ClassValue = string | false | null | undefined

/** Minimaler Klassen-Joiner – vermeidet eine zusätzliche Abhängigkeit wie clsx. */
export function cn(...values: ClassValue[]): string {
  return values.filter(Boolean).join(' ')
}
