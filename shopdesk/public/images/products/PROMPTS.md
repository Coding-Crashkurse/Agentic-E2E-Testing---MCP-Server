# Produktbilder – fotorealistische ShopDesk-Fotos

Die zwölf WebP-Dateien in diesem Ordner sind **KI-generierte, fotorealistische Produktfotos**.
Erstellt am 10.09.2026 mit dem integrierten Werkzeug `image_gen`, jeweils eine separate
Generierung pro Produkt. Die bisherigen illustrierten Platzhalter wurden ersetzt.
Katalog und Warenkorb verwenden diese lokalen Dateien über `productImage()`.

## Format

- **Ausgeliefert:** `*.webp`, **800 × 800 px** (1:1), Qualität 88, ca. 60–120 KB pro Bild.
  Kleine Dateien sind wichtig, damit alle zwölf Bilder in einem frischen Browser-Kontext sofort
  geladen sind und Screenshots keine leeren Bildflächen zeigen.
- **Originale:** `assets/product-originals/*.png`, 1254 × 1254 px, unveränderte Ausgabe des
  Bildwerkzeugs (angefordert waren 1024 × 1024 px). Der Ordner liegt außerhalb von `public/` und
  wird nicht ausgeliefert. Neue Fotos zuerst dort ablegen und dann mit Pillow auf 800 × 800 WebP
  herunterskalieren (Lanczos, `quality=88`).
- Einheitlicher Look, damit das Raster ruhig wirkt (Style-Prefix für jeden Prompt):

> Use case: product-mockup. Asset type: square ecommerce product photo for ShopDesk. Photorealistic studio product photograph, product centered and fully visible with generous margin, three-quarter view, on a seamless light warm-grey backdrop, soft diffused natural light from the upper left, gentle contact shadow, realistic material textures, high detail, commercial e-commerce style. No text, no logos, no people, no props, no watermark. Square 1:1 composition, 1024 by 1024 pixels. Subject:

- Keine Schrift, keine Wasserzeichen, keine Marken.
- Bilder sollten deterministisch bleiben: Nach dem Generieren nicht mehr ändern, damit Screenshot-Vergleiche in Tests stabil sind.

## Dateien und Prompts

Die Produktnamen entsprechen der (englischen) Oberfläche in `src/data/products.ts`.

| Datei | Produkt | Prompt (an den Style-Prefix anhängen) |
| --- | --- | --- |
| `nordlicht-kopfhoerer.webp` | Nordlicht Headphones | Premium wireless over-ear headphones in matte graphite with slate-blue accents, plush memory-foam ear cushions, brushed aluminium hinges, standing upright. |
| `klangkugel-lautsprecher.webp` | Klangkugel Speaker | Compact spherical Bluetooth speaker in dark teal fabric mesh with a matte rubber base and a small metal control ring on top. |
| `tastwerk-tastatur.webp` | Tastwerk 75 Keyboard | Compact 75 percent mechanical keyboard with a deep indigo aluminium case and light lavender PBT keycaps, slightly angled, wireless. Keycaps may have realistic small keyboard legends, no branding. |
| `mahlwerk-kaffeemuehle.webp` | Mahlwerk Coffee Grinder | Electric burr coffee grinder with a cream enamel body, walnut-wood accents and a glass bean hopper, a few roasted beans visible in the hopper. |
| `morgenrot-tasse.webp` | Morgenrot Ceramic Mug | Handmade stoneware mug with a dusty rose reactive glaze fading to cream at the rim, speckled clay texture, handle turned to the right. |
| `lumo-schreibtischlampe.webp` | Lumo Desk Lamp | Minimalist LED desk lamp in warm mustard-yellow metal with a slim articulated arm and round weighted base, switched on with soft warm light. |
| `linie-notizbuch.webp` | Linie Notebook Set | Set of exactly three A5 dot-grid notebooks in navy, sky-blue and cream linen covers, fanned out in a stack with elastic closure bands visible. |
| `wanderer-rucksack.webp` | Wanderer Leather Backpack | Full-grain leather backpack in rich cognac brown with brass buckles, rolled top and a padded front pocket, standing upright. |
| `alltag-tragetasche.webp` | Alltag Canvas Tote | Heavy organic cotton canvas tote bag in olive green with natural long handles and a small inner pocket peeking out, standing slightly slouched. |
| `quell-trinkflasche.webp` | Quell Water Bottle | Double-walled stainless-steel water bottle, 750 ml, in matte ocean-blue powder coating with a brushed steel cap, standing upright. |
| `glut-thermoskanne.webp` | Glut Thermos Flask | One-litre vacuum flask in deep brick-red with a stainless-steel cup lid and a curved side handle, standing upright. |
| `fjord-muetze.webp` | Fjord Wool Beanie | Chunky knit merino wool beanie in heather violet with a folded ribbed brim and a matching pom-pom, resting upright. |

Für den zuerst generierten Kopfhörer wurde derselbe Look mit folgendem vollständigen Prompt beschrieben:

> Use case: product-mockup. Asset type: square ecommerce product photo for ShopDesk. Photorealistic studio product photograph of premium wireless over-ear headphones in matte graphite with slate-blue accents, plush memory-foam ear cushions and brushed aluminium hinges, standing upright. Entire product centered, three-quarter view, on a seamless light warm-grey backdrop, soft diffused natural light from the upper left, gentle contact shadow, realistic leather and metal textures, high detail, commercial e-commerce style. No text, no logos, no people, no props, no watermark. Square 1:1 composition, 1024 by 1024 pixels.

## Optionale Platzhalter-Vorschauen

```bash
npm run images:placeholders
```

Das Skript schreibt nach **`output/placeholders/`**, nicht in diesen Ordner. Die produktiv
verwendeten Fotos bleiben dadurch erhalten. Es läuft über uv (`uv run scripts/generate_placeholders.py`);
Pillow wird über die Inline-Skript-Metadaten (PEP 723) automatisch installiert. Ohne uv geht auch
`python scripts/generate_placeholders.py` mit installiertem Pillow.
