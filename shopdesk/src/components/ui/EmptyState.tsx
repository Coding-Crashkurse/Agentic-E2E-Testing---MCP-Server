import type { HTMLAttributes, ReactNode } from 'react'
import { cn } from '../../lib/cn'

interface EmptyStateProps extends HTMLAttributes<HTMLDivElement> {
  icon: ReactNode
  title: string
  description: string
  action?: ReactNode
}

export function EmptyState({ icon, title, description, action, className, ...rest }: EmptyStateProps) {
  return (
    <div
      className={cn(
        'flex flex-col items-center gap-3 rounded-3xl bg-white px-6 py-20 text-center shadow-card ring-1 ring-slate-900/5',
        className,
      )}
      {...rest}
    >
      <span className="grid size-16 place-items-center rounded-2xl bg-linear-to-br from-indigo-50 to-violet-50 text-indigo-600 ring-1 ring-indigo-100 [&>svg]:size-7">
        {icon}
      </span>
      <h2 className="text-xl font-semibold tracking-tight text-slate-900">{title}</h2>
      <p className="max-w-md text-[15px] text-slate-500">{description}</p>
      {action ? <div className="mt-3">{action}</div> : null}
    </div>
  )
}
