import type { ButtonHTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface ChipProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  active: boolean
  icon?: ReactNode
}

/** Umschaltbarer Filter-Chip. `aria-pressed` und `data-active` spiegeln den Zustand für Tests. */
export function Chip({ active, icon, className, children, ...rest }: ChipProps) {
  return (
    <button
      type="button"
      aria-pressed={active}
      data-active={active ? 'true' : 'false'}
      className={cn(
        'inline-flex h-9 items-center gap-1.5 rounded-full px-3.5 text-sm font-medium ring-1 transition-[background-color,box-shadow,color] duration-200 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600',
        active
          ? 'bg-linear-to-r from-indigo-600 to-violet-600 text-white shadow-glow ring-transparent'
          : 'bg-white text-slate-700 ring-slate-200 hover:bg-slate-50 hover:ring-slate-300',
        className,
      )}
      {...rest}
    >
      {icon}
      {children}
    </button>
  )
}
