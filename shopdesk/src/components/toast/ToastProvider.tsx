import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import { ToastContext, type ToastApi, type ToastEntry, type ToastKind } from './toastContext'
import { ToastViewport } from './ToastViewport'

/** Anzeigedauer einer Meldung. Lang genug für einen Screenshot, kurz genug für flüssige Bedienung. */
const TOAST_DURATION_MS = 3500
/** Mehr gleichzeitige Meldungen würden die Bestellzusammenfassung verdecken. */
const MAX_VISIBLE_TOASTS = 3

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<ToastEntry[]>([])
  const nextId = useRef(1)
  const timers = useRef(new Map<number, ReturnType<typeof setTimeout>>())

  const dismiss = useCallback((id: number) => {
    const timer = timers.current.get(id)
    if (timer !== undefined) {
      clearTimeout(timer)
      timers.current.delete(id)
    }
    setToasts((previous) => previous.filter((toast) => toast.id !== id))
  }, [])

  const notify = useCallback(
    (kind: ToastKind, message: string) => {
      const id = nextId.current
      nextId.current += 1
      setToasts((previous) => [...previous.slice(-(MAX_VISIBLE_TOASTS - 1)), { id, kind, message }])
      timers.current.set(
        id,
        setTimeout(() => dismiss(id), TOAST_DURATION_MS),
      )
    },
    [dismiss],
  )

  useEffect(() => {
    const pending = timers.current
    return () => pending.forEach((timer) => clearTimeout(timer))
  }, [])

  const api = useMemo<ToastApi>(
    () => ({
      success: (message) => notify('success', message),
      error: (message) => notify('error', message),
      info: (message) => notify('info', message),
    }),
    [notify],
  )

  return (
    <ToastContext.Provider value={api}>
      {children}
      <ToastViewport toasts={toasts} onDismiss={dismiss} />
    </ToastContext.Provider>
  )
}
