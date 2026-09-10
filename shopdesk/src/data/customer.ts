import type { Address } from '../lib/address'

/**
 * Demo-Kundin, mit deren Daten die Kasse vorausgefüllt wird („angemeldet als …“).
 *
 * Die E-Mail-Adresse stammt aus einem simulierten Legacy-Kundenimport und enthält ABSICHTLICH
 * ein Leerzeichen am Ende. Eine korrekte Validierung muss Eingaben trimmen – genau das prüft
 * das Bug-Flag `submit-disabled`. Im Modus `none` ist die Adresse gültig.
 */
export const DEMO_CUSTOMER: Address = {
  name: 'Anna Schmidt',
  email: 'anna.schmidt@example.com ',
  street: 'Lindenweg 12',
  zip: '10115',
  city: 'Berlin',
}
