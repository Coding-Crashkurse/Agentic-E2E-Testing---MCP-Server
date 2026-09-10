export const CATEGORIES = ['Audio', 'Kitchen', 'Office', 'Bags', 'Outdoor'] as const

export type Category = (typeof CATEGORIES)[number]

/** Kurzform der Kategorie für Test-IDs wie `filter-category-kitchen`. */
export const CATEGORY_SLUGS: Record<Category, string> = {
  Audio: 'audio',
  Kitchen: 'kitchen',
  Office: 'office',
  Bags: 'bags',
  Outdoor: 'outdoor',
}

export interface Product {
  id: string
  /** Dateiname des Produktbilds (ohne Endung), siehe `productImage`. */
  slug: string
  name: string
  category: Category
  /** Preis in Cent – Ganzzahlen vermeiden Rundungsfehler. */
  price: number
  inStock: boolean
  description: string
}

/**
 * Feste Seed-Daten. Reihenfolge, Preise und Verfügbarkeit sind Teil des Testvertrags:
 * 12 Produkte, davon 3 ausverkauft (p-03, p-09, p-12).
 */
export const PRODUCTS: readonly Product[] = [
  {
    id: 'p-01',
    slug: 'nordlicht-kopfhoerer',
    name: 'Nordlicht Headphones',
    category: 'Audio',
    price: 14900,
    inStock: true,
    description: 'Wireless over-ear headphones with active noise cancelling and 30 hours of battery life.',
  },
  {
    id: 'p-02',
    slug: 'klangkugel-lautsprecher',
    name: 'Klangkugel Speaker',
    category: 'Audio',
    price: 7900,
    inStock: true,
    description: 'Compact Bluetooth speaker with 360° sound, water-resistant to IPX5.',
  },
  {
    id: 'p-03',
    slug: 'tastwerk-tastatur',
    name: 'Tastwerk 75 Keyboard',
    category: 'Office',
    price: 12900,
    inStock: false,
    description: 'Mechanical 75% keyboard with dampened switches and PBT keycaps.',
  },
  {
    id: 'p-04',
    slug: 'mahlwerk-kaffeemuehle',
    name: 'Mahlwerk Coffee Grinder',
    category: 'Kitchen',
    price: 8990,
    inStock: true,
    description: 'Electric coffee grinder with stainless-steel conical burrs and 30 grind settings.',
  },
  {
    id: 'p-05',
    slug: 'morgenrot-tasse',
    name: 'Morgenrot Ceramic Mug',
    category: 'Kitchen',
    price: 1450,
    inStock: true,
    description: 'Hand-glazed stoneware mug, 350 ml, dishwasher safe.',
  },
  {
    id: 'p-06',
    slug: 'lumo-schreibtischlampe',
    name: 'Lumo Desk Lamp',
    category: 'Office',
    price: 5900,
    inStock: true,
    description: 'Dimmable LED desk lamp with three colour temperatures and USB-C charging.',
  },
  {
    id: 'p-07',
    slug: 'linie-notizbuch',
    name: 'Linie Notebook Set',
    category: 'Office',
    price: 1990,
    inStock: true,
    description: 'Three A5 notebooks with 120 gsm dotted paper and thread-bound spines.',
  },
  {
    id: 'p-08',
    slug: 'wanderer-rucksack',
    name: 'Wanderer Leather Backpack',
    category: 'Bags',
    price: 17900,
    inStock: true,
    description: 'Vegetable-tanned full-grain leather backpack with a padded laptop sleeve.',
  },
  {
    id: 'p-09',
    slug: 'alltag-tragetasche',
    name: 'Alltag Canvas Tote',
    category: 'Bags',
    price: 2990,
    inStock: false,
    description: 'Sturdy organic cotton tote with an inner pocket and long handles.',
  },
  {
    id: 'p-10',
    slug: 'quell-trinkflasche',
    name: 'Quell Water Bottle',
    category: 'Outdoor',
    price: 2490,
    inStock: true,
    description: 'Double-walled stainless-steel bottle, 750 ml, keeps drinks cold for 24 hours.',
  },
  {
    id: 'p-11',
    slug: 'glut-thermoskanne',
    name: 'Glut Thermos Flask',
    category: 'Outdoor',
    price: 3490,
    inStock: true,
    description: 'One-litre vacuum flask with a cup lid for hot drinks on the go.',
  },
  {
    id: 'p-12',
    slug: 'fjord-muetze',
    name: 'Fjord Wool Beanie',
    category: 'Outdoor',
    price: 2990,
    inStock: false,
    description: 'Knitted merino wool beanie with a pom-pom, one size.',
  },
]

/** Lokales, fotorealistisches Produktbild; feste Dateinamen für stabile Screenshots. */
export function productImage(product: Pick<Product, 'slug'>): string {
  return `/images/products/${product.slug}.webp`
}

export function findProduct(id: string): Product | undefined {
  return PRODUCTS.find((product) => product.id === id)
}
