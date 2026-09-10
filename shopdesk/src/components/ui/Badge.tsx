import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

export type BadgeTone = 'neutral' | 'success' | 'brand' | 'dark'

const TONES: Record<BadgeTone, string> = {
  neutral: 'bg-white/90 text-slate-700 ring-slate-900/10',
  success: 'bg-emerald-50 text-emerald-700 ring-emerald-600/15',
  brand: 'bg-indigo-50 text-indigo-700 ring-indigo-600/15',
  dark: 'bg-slate-900 text-white ring-slate-900',
}

const DOTS: Record<BadgeTone, string> = {
  neutral: 'bg-slate-400',
  success: 'bg-emerald-500',
  brand: 'bg-indigo-500',
  dark: 'bg-emerald-400',
}

interface BadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone
  /** Zeigt einen Status-Punkt vor dem Text. */
  dot?: boolean
}

export function Badge({ tone = 'neutral', dot = false, className, children, ...rest }: BadgeProps) {
  return (
    <span
      className={cn(
        'inline-flex items-center gap-1.5 rounded-full px-2.5 py-1 text-xs font-medium ring-1',
        TONES[tone],
        className,
      )}
      {...rest}
    >
      {dot ? <span aria-hidden="true" className={cn('size-1.5 rounded-full', DOTS[tone])} /> : null}
      {children}
    </span>
  )
}
