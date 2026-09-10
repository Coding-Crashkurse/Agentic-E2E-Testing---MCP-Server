import { CircleAlert, CircleCheck, Info, X } from 'lucide-react'
import { cn } from '../../lib/cn'
import type { ToastEntry, ToastKind } from './toastContext'

interface ToastViewportProps {
  toasts: readonly ToastEntry[]
  onDismiss: (id: number) => void
}

const ICONS: Record<ToastKind, { Icon: typeof CircleCheck; className: string }> = {
  success: { Icon: CircleCheck, className: 'text-emerald-400' },
  error: { Icon: CircleAlert, className: 'text-rose-400' },
  info: { Icon: Info, className: 'text-indigo-300' },
}

export function ToastViewport({ toasts, onDismiss }: ToastViewportProps) {
  return (
    <div
      data-testid="toast-region"
      aria-live="polite"
      aria-relevant="additions"
      className="pointer-events-none fixed inset-x-0 bottom-6 z-50 flex flex-col items-end gap-2 px-6"
    >
      {toasts.map((toast) => {
        const { Icon, className } = ICONS[toast.kind]
        return (
          <div
            key={toast.id}
            role="status"
            data-testid="toast"
            data-kind={toast.kind}
            className="animate-toast-in pointer-events-auto flex w-full max-w-sm items-start gap-3 rounded-2xl bg-slate-900/95 px-4 py-3.5 text-white shadow-lift ring-1 ring-white/10 backdrop-blur"
          >
            <Icon className={cn('mt-0.5 size-5 shrink-0', className)} aria-hidden="true" />
            <p className="flex-1 text-sm leading-snug text-slate-100">{toast.message}</p>
            <button
              type="button"
              onClick={() => onDismiss(toast.id)}
              aria-label="Dismiss notification"
              className="-m-1 rounded-md p-1 text-slate-400 transition-colors hover:bg-white/10 hover:text-white"
            >
              <X className="size-4" aria-hidden="true" />
            </button>
          </div>
        )
      })}
    </div>
  )
}
