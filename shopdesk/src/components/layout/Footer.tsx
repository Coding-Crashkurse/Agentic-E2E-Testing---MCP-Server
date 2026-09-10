import { RotateCcw } from 'lucide-react'
import { clearSavedAddress } from '../../lib/storage'

function resetDemo() {
  clearSavedAddress()
  window.location.reload()
}

export function Footer() {
  return (
    <footer className="relative border-t border-slate-900/5 bg-white/60">
      <div className="mx-auto flex w-full max-w-6xl flex-wrap items-center justify-between gap-3 px-6 py-6 text-sm text-slate-500">
        <p className="flex items-center gap-2">
          <span aria-hidden="true" className="size-1.5 rounded-full bg-emerald-500" />
          ShopDesk is a demo store. No real orders are placed.
        </p>
        <button
          type="button"
          data-testid="reset-demo"
          onClick={resetDemo}
          className="inline-flex items-center gap-1.5 rounded-full px-3 py-1.5 transition-colors hover:bg-slate-900/5 hover:text-slate-900"
        >
          <RotateCcw className="size-4" aria-hidden="true" />
          Reset demo
        </button>
      </div>
    </footer>
  )
}
