const EUR = new Intl.NumberFormat('en-GB', { style: 'currency', currency: 'EUR' })

/** Formatiert einen Cent-Betrag als Euro, z. B. 14900 → „€149.00“. */
export function formatCents(cents: number): string {
  return EUR.format(cents / 100)
}
