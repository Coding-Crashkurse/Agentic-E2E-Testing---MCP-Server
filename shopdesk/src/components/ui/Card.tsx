import type { HTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

interface CardProps extends HTMLAttributes<HTMLElement> {
  /** `false`, wenn der Inhalt (z. B. eine Liste) bis an den Rand laufen soll. */
  padded?: boolean
}

export function Card({ padded = true, className, ...rest }: CardProps) {
  return (
    <section
      className={cn('rounded-3xl bg-white shadow-card ring-1 ring-slate-900/5', padded && 'p-6', className)}
      {...rest}
    />
  )
}

export function CardTitle({ className, ...rest }: HTMLAttributes<HTMLHeadingElement>) {
  return <h2 className={cn('text-base font-semibold tracking-tight text-slate-900', className)} {...rest} />
}
