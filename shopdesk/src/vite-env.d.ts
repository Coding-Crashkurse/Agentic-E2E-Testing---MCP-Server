/// <reference types="vite/client" />

interface ImportMetaEnv {
  /** Bug-Modus, den der Launcher beim Start über `--bug=<flag>` einbrennt (siehe scripts/shopdesk.mjs). */
  readonly VITE_BUG?: string
}

interface ImportMeta {
  readonly env: ImportMetaEnv
}
