/// <reference types="vitest/config" />
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

/**
 * Der Bug-Modus wird NICHT hier, sondern beim Start gewählt:
 *   npm run dev -- --bug=coupon-noop
 * scripts/shopdesk.mjs setzt dafür `import.meta.env.VITE_BUG` per `define`. Wird Vite direkt
 * gestartet (`npx vite`), läuft die fehlerfreie Version.
 *
 * Feste Ports (strictPort), damit Test-Harness und Tickets immer dieselbe URL verwenden können.
 */
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { host: '127.0.0.1', port: 5173, strictPort: true },
  preview: { host: '127.0.0.1', port: 4173, strictPort: true },
  test: {
    environment: 'node',
    include: ['src/**/*.test.ts'],
  },
})
