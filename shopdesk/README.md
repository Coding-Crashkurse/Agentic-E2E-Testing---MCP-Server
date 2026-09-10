# ShopDesk – Mini-Warenkorb mit absichtlich eingebauten Bugs

ShopDesk ist eine kleine React-Seite (Vite, TypeScript, Tailwind CSS 4, kein Backend, State im Speicher),
die als **Zielsystem für End-to-End-Testagenten** dient. Die Oberfläche ist komplett **englisch**,
der Ablauf ist ein klassischer Mini-Shop:

**Catalog mit Filter → Cart (Menge ±, Entfernen, Coupon) → Checkout → Order confirmation**

Die Bugs werden **beim Start** gewählt und fest ins Bundle eingebrannt. Eine Instanz kann einen
oder mehrere Fehler haben, die URL verrät nichts davon. Ohne Flag funktioniert alles; dieser Fall
ist der wichtigste: Ein Agent muss das Ticket dann als **nicht reproduzierbar** melden.

## Schnellstart

```bash
npm install

npm run dev                                                 # funktionierende Version → http://127.0.0.1:5173/
npm run dev -- --bug=coupon-noop                            # ein Bug (vorher die andere Instanz stoppen)
npm run dev -- --bug=coupon-noop,qty-stale-total,flaky-race # drei Bugs gleichzeitig in EINER Instanz
npm run dev -- --bug=double-submit --port=5174              # zweite Instanz parallel auf 5174
```

Der Launcher gibt beim Start die aktiven Bugs aus, zum Beispiel:

```
ShopDesk mode: 3 bugs active
    - coupon-noop: Coupon is accepted, but the discount is missing
    - qty-stale-total: Totals lag one click behind after a quantity change
    - flaky-race: An item sometimes does not end up in the cart
```

In der Seite selbst ist davon nichts sichtbar.

Wichtig ist das doppelte `--`: Alles danach geht an den Launcher (`scripts/shopdesk.mjs`), nicht an npm.
`node scripts/shopdesk.mjs --help` zeigt alle Optionen.

Empfohlene Test-URL (Animationen aus, Katalog):

```
http://127.0.0.1:5173/?motion=off#/
```

### Statische Builds pro Variante

```bash
npm run build                                          # dist/ – funktionierende Version
npm run build -- --bug=coupon-noop --out-dir=dist-coupon-noop
npm run preview -- --out-dir=dist-coupon-noop --port=4174
```

`preview` liefert einen Build so aus, wie er gebaut wurde; `--bug` gehört deshalb zu `build`.
Varianten am besten in Geschwister-Ordner wie `dist-<flag>` bauen: Vite leert `dist/` bei jedem
Standard-Build, ein Unterordner darin wäre danach weg.

### Weitere Skripte

| Skript | Zweck |
| --- | --- |
| `npm run lint` | ESLint (inkl. `scripts/`) |
| `npm run typecheck` | `tsc -b` |
| `npm test` | Vitest (Reducer, Validierung, Filter, Flags, Runtime-Optionen, Router) |
| `npm run images:placeholders` | Separate Platzhalter-Vorschauen nach `output/placeholders/` erzeugen; Produktfotos bleiben erhalten |

## Startoptionen, URL-Parameter und Routen

| Option | Wo | Wirkung |
| --- | --- | --- |
| `--bug=<flag>[,<flag>…]` | Launcher (`dev`, `build`) | Aktiviert einen oder mehrere Fehler aus dem Bug-Katalog, kommagetrennt oder mehrfach angegeben. Unbekannte Werte brechen den Start mit einer Fehlermeldung ab, `none` lässt sich nicht kombinieren. Standard: kein Bug. |
| `--port=<n>`, `--host=<host>` | Launcher (`dev`, `preview`) | Port/Host überschreiben, z. B. für parallele Instanzen. Die Ports sind `strictPort`. |
| `--out-dir=<dir>` | Launcher (`build`, `preview`) | Ausgabeordner für Varianten-Builds. |
| `?motion=off` | URL | Schaltet alle Transitions/Animationen ab (`html[data-motion="off"]`), Toasts erscheinen ohne Einblendung. |

Ein `?bug=…` in der URL hat keine Wirkung mehr; die App schreibt lediglich eine Warnung in die Browser-Konsole.
Alternativ zum Flag akzeptiert Vite auch `VITE_BUG=<flag>` in einer `.env.local` – das Flag des Launchers hat Vorrang.

Die Navigation ist hash-basiert, `?motion=off` bleibt dabei erhalten (auch nach Reload):

| Route | View |
| --- | --- |
| `#/` | Catalog |
| `#/cart` | Cart |
| `#/checkout` | Checkout (bei leerem Warenkorb: Hinweis + Link zum Katalog) |
| `#/confirmation` | Order confirmation + „Orders this session“ |

## Demo-Daten (fest, kein Zufall)

- **12 Produkte**, 3 davon ausverkauft: Tastwerk 75 Keyboard (p-03), Alltag Canvas Tote (p-09), Fjord Wool Beanie (p-12).
  Das Keyboard steht bewusst in der ersten Reihe, damit der Verfügbarkeitsfilter sofort sichtbar wirkt.
- **Kategorien:** Audio, Kitchen, Office, Bags, Outdoor.
- **Coupons:** `SAVE10` (10 % auf den Warenwert), `MINUS5` (€5 ab €20 Warenwert).
- **Versand:** €4.90, kostenlos ab €75 Warenwert (nach Rabatt). Preise werden englisch formatiert (`€149.00`).
- **Demo-Kundin (vorausgefüllt im Checkout):** Anna Schmidt, `anna.schmidt@example.com`, Lindenweg 12, 10115 Berlin.
  Die E-Mail-Adresse enthält in den Seed-Daten absichtlich ein Leerzeichen am Ende (simulierter Legacy-Import) – im Modus `none` wird es korrekt weggetrimmt.
- **Bestellnummern:** fortlaufend ab `#10001` pro Sitzung. Simulierte Backend-Latenz beim Bestellen: 1,2 s.
- **Persistenz:** Nur die gespeicherte Adresse landet im `localStorage` (`shopdesk:address:v1`). Warenkorb und Bestellungen leben im Speicher und sind nach einem Reload weg.
  „Reset demo“ im Footer löscht die gespeicherte Adresse und lädt neu.

## Bug-Katalog

Symptom und Ursache je Flag stehen in `src/bugs/catalog.json` (Launcher, Tests und diese Tabelle;
der Katalog landet nicht im ausgelieferten Bundle). Alle Injektionsstellen sind im Code mit
`// BUG <flag>:` markiert – `grep -rn "BUG " src` listet sie.
Die Anführungszeichen in der Tabelle zitieren die englischen UI-Texte wörtlich.

Die Flags sind unabhängig voneinander und lassen sich beliebig kombinieren; jede Injektionsstelle
prüft nur ihr eigenes Flag. Zwei Wechselwirkungen sind zu beachten: `submit-disabled` blockiert auch
„Save address“, bis die E-Mail neu eingetippt ist, und `coupon-noop` sowie `qty-stale-total`
wirken beide auf die Order summary – für ein eindeutiges Ticket pro Symptom lieber getrennt testen.

| Flag | Ticket-Symptom | Reproduktion | Erwartet | Tatsächlich | Visuelle Signatur |
| --- | --- | --- | --- | --- | --- |
| `coupon-noop` | „Coupon is accepted, discount is missing“ | Nordlicht Headphones in den Warenkorb → Cart → Total merken → `SAVE10` mit „Apply“ einlösen | Zeile „Discount (SAVE10) -€14.90“, Total €134.10 | Toast „Coupon SAVE10 applied ✓“ und grüne Box „SAVE10 applied“, aber Total bleibt €149.00, keine Discount-Zeile | Nur der Zahlenvergleich vorher/nachher entlarvt es – Toast und Chip sind „grün“ |
| `remove-off-by-one` | „Wrong item disappears“ | Headphones, Speaker, Coffee Grinder hinzufügen → Cart → beim Speaker (2. Zeile) auf den Papierkorb | Speaker weg | Coffee Grinder verschwindet, Speaker bleibt; Toast nennt trotzdem den Speaker. Beim letzten Eintrag passiert gar nichts | Listen-Screenshot vorher/nachher |
| `qty-stale-total` | „Total lags behind“ | Morgenrot Ceramic Mug (€14.50) hinzufügen → Cart → „+“ | Menge 2, Zeilensumme €29.00, Subtotal €29.00, Total €33.90 | Menge und Zeilensumme stimmen, Subtotal bleibt €14.50 (Total €19.40) und springt erst beim nächsten Klick nach; Header-Badge hinkt ebenfalls | Zeilensumme ≠ Order summary im selben Screenshot |
| `filter-ignored` | „Filter ‘In stock only’ still shows everything“ | Catalog → Chip „In stock only“ | „9 of 12 products“, keine „Sold out“-Karten | Chip ist aktiv/farbig (`aria-pressed=true`), Zähler bleibt „12 of 12“, Tastwerk 75 mit Badge „Sold out“ bleibt in Reihe 1 | Aktiver Chip + unveränderte Liste |
| `submit-disabled` | „Place order button stays grey“ | Beliebigen Artikel hinzufügen → Checkout → vorausgefüllte Adresse prüfen → Checkbox „I accept the terms …“ setzen | Button „Place order“ wird aktiv (Verlauf Indigo/Violett) | Button bleibt grau, obwohl alle Felder gefüllt aussehen und keine Fehlermeldung sichtbar ist. Erst wenn die E-Mail neu eingetippt wird, wird er aktiv | Gefülltes Formular, gesetzte Checkbox, grauer Button |
| `save-not-persisted` | „Address is gone after reload“ | Artikel hinzufügen → Checkout → Straße ändern (z. B. „Bergstraße 7“) → „Save address“ → Toast → **Seite neu laden** → Artikel erneut hinzufügen → Checkout | „Bergstraße 7“ | Wieder „Lindenweg 12“. Ohne Reload (Cart ↔ Checkout) bleibt die neue Adresse sichtbar – der Fehler zeigt sich **nur** nach Reload | Mehrstufiger Flow, Screenshot vor und nach Reload |
| `double-submit` | „Order is sometimes placed twice“ | Artikel hinzufügen → Checkout → Checkbox → „Place order“ **zweimal schnell** klicken (Latenz 1,2 s) | Button sperrt sich sofort („Placing order…“), genau eine Bestellung #10001 | Button bleibt klickbar (kein Spinner), Bestätigung zeigt „Orders this session“ mit Badge 2 (#10001, #10002). Ein Einzelklick erzeugt korrekt eine Bestellung – daher „sometimes“ | Fehlender Pending-Zustand; Zähler-Badge 2 |
| `flaky-race` | „Item sometimes doesn’t end up in the cart“ | Dasselbe Produkt **dreimal** mit „Add to cart“ hinzufügen | Badge 3 | Badge 2, obwohl dreimal der Erfolgs-Toast erschien. Jeder 3., 6., 9. … Klick der Sitzung geht verloren; ein einzelner Versuch reproduziert nichts | Toast-Anzahl ≠ Badge-Wert |
| `none` | identisches Ticket wie oben | – | – | Alles funktioniert | Muss als **not reproducible** zurückkommen |

Die Wirkung jedes Flags ist in `src/store/cart.test.ts`, `src/lib/address.test.ts` und `src/lib/filters.test.ts` durch Unit-Tests abgesichert;
`src/config/runtime.test.ts` stellt sicher, dass die URL den Modus nicht umschalten kann.

## Determinismus

- Feste Seed-Daten, kein `Math.random()`, kein `Date.now()` in der Anzeige. Bestellnummern zählen ab 10001, `flaky-race` nutzt einen Zähler statt Zufall.
- `data-testid` an allen relevanten Elementen (siehe unten), zusätzlich `data-product-id`, `data-active`, `aria-pressed`, `data-route`, `data-kind`.
- `?motion=off` schaltet Animationen ab (Seitenwechsel-Einblendung, Hover-Effekte, Toast-Animation); `prefers-reduced-motion` wird ebenfalls respektiert.
- Schrift (Inter) wird lokal gebündelt, keine externen Requests; Bilder sind statische, kleine WebP-Dateien.
- Empfohlene Viewport-Größe: **1280 × 800** (4 Produktspalten, erste Reihe vollständig sichtbar, Sidebar rechts). `document.title` wechselt pro View („Catalog · ShopDesk“, „Cart · ShopDesk“, „Checkout · ShopDesk“, „Order confirmation · ShopDesk“).
- Toasts bleiben 3,5 s sichtbar (`data-testid="toast"`, `role="status"`), erscheinen unten rechts, maximal drei gleichzeitig.

## Test-IDs (Auszug)

| Bereich | Test-IDs |
| --- | --- |
| Header | `nav-home`, `nav-catalog`, `nav-cart`, `customer-name`, `cart-button`, `cart-badge` |
| Catalog | `filter-search`, `filter-in-stock`, `filter-category-all`, `filter-category-{audio,kitchen,office,bags,outdoor}`, `filter-reset`, `result-count`, `product-grid`, `product-card`, `product-name`, `product-price`, `product-stock`, `add-to-cart`, `catalog-empty` |
| Cart | `cart-view`, `cart-empty`, `cart-lines`, `cart-line`, `line-name`, `line-unit-price`, `line-total`, `qty-decrease`, `qty-value`, `qty-increase`, `remove-line`, `coupon-input`, `coupon-apply`, `coupon-error`, `coupon-active`, `coupon-remove`, `cart-summary`, `summary-subtotal`, `summary-discount`, `summary-shipping`, `summary-total`, `shipping-progress`, `go-to-checkout` |
| Checkout | `checkout-form`, `checkout-empty`, `field-{name,email,street,zip,city}`, `error-{name,…}`, `save-address`, `accept-terms`, `checkout-summary`, `checkout-line`, `checkout-{subtotal,discount,shipping,total}`, `place-order` |
| Confirmation | `order-confirmation`, `order-number`, `order-lines`, `order-line`, `order-address`, `order-{subtotal,discount,shipping,total}`, `order-history`, `order-history-count`, `order-history-entry`, `continue-shopping`, `confirmation-empty` |
| Global | `toast-region`, `toast` (mit `data-kind=success|error|info`), `reset-demo` |

## Bilder

`public/images/products/*.webp` enthält zwölf **KI-generierte, fotorealistische Produktbilder**
mit einheitlichem Studio-Look (800 × 800 px, ca. 15–90 KB pro Bild). Sie wurden mit dem
integrierten Bildgenerierungswerkzeug erzeugt und ersetzen die bisherigen Illustrationen direkt
in Katalog und Warenkorb. Die unveränderten Originale (PNG, 1254 × 1254 px, je ca. 2 MB) liegen in
`assets/product-originals/` außerhalb des Web-Roots, damit ein frischer Browser-Kontext nicht 24 MB
laden muss, bevor ein Screenshot vollständig ist.
Die verwendeten Prompts und Bildvorgaben stehen in
[`public/images/products/PROMPTS.md`](public/images/products/PROMPTS.md).

Das optionale Platzhalter-Skript schreibt ausschließlich nach `output/placeholders/`,
damit es die Produktfotos nicht überschreibt. Nach einem Bildaustausch die Seite neu laden
(bei einem alten Browser-Cache mit `Strg+F5`).

## Projektstruktur

```
shopdesk/
├─ index.html
├─ vite.config.ts              # Vite + React + Tailwind + Vitest, feste Ports
├─ scripts/shopdesk.mjs        # Launcher: dev | build | preview, --bug=<flag>, --port, --out-dir
├─ scripts/generate_placeholders.py
├─ assets/product-originals/   # PNG-Originale der Produktfotos (nicht ausgeliefert)
├─ public/images/products/     # Produktfotos als 800×800-WebP + PROMPTS.md
└─ src/
   ├─ main.tsx                 # liest VITE_BUG (eingebrannt) und ?motion, mountet <App>
   ├─ App.tsx                  # Provider-Baum + Hash-Routing
   ├─ router.ts                # useRoute / navigate (Hash-Routing ohne Bibliothek)
   ├─ index.css                # Tailwind-Theme, Hintergrund, Motion-Off, Animationen
   ├─ bugs/                    # flags.ts, catalog.json (Symptome/Ursachen), bugContext.ts, BugProvider.tsx
   ├─ config/runtime.ts        # Build-Umgebung + URL → RuntimeOptions
   ├─ data/                    # products.ts, coupons.ts, customer.ts (Seed-Daten)
   ├─ lib/                     # address.ts (Validierung), filters.ts, money.ts, storage.ts, cn.ts
   ├─ store/                   # cart.ts (Reducer), Cart-/Orders-/CustomerProvider + Contexts
   ├─ components/
   │  ├─ ui/                   # Button, Badge, Chip, TextField, Card, EmptyState, PageHeader
   │  ├─ layout/               # Header, Footer
   │  ├─ toast/                # ToastProvider, ToastViewport
   │  ├─ catalog/              # FilterBar, ProductGrid, ProductCard
   │  ├─ cart/                 # CartLine, CouponForm, CartSummary, TotalsList
   │  └─ checkout/             # CheckoutForm, CheckoutSummary
   └─ views/                   # CatalogView, CartView, CheckoutView, ConfirmationView
```

## Hinweise für den Einsatz mit Testagenten

- Der Agent bekommt nur Ticket und Basis-URL. Welche Variante läuft, entscheidet, wer die Instanz gestartet hat – die Seite und die URL verraten es nicht. Für Kontrollläufe dasselbe Ticket gegen eine Instanz ohne `--bug` fahren.
- Zwei Instanzen parallel (z. B. ohne Flag auf 5173, `coupon-noop` auf 5174) erlauben direkte Vergleiche mit identischen Schritten.
- Mehrere Tickets gegen eine einzige Instanz: `--bug=a,b,c` starten und die Tickets nacheinander abarbeiten; jedes Ticket sieht nur sein eigenes Symptom.
- Für Zahlenvergleiche `summary-total` bzw. `checkout-total` **vor und nach** der Aktion auslesen – DOM-Prüfungen wie „Toast sichtbar“ sind bei `coupon-noop` bewusst grün.
- `save-not-persisted` und `double-submit` brauchen einen Reload bzw. einen Doppelklick; `flaky-race` mindestens drei Versuche.
