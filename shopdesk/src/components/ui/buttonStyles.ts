import { cn } from '../../lib/cn'

export type ButtonVariant = 'primary' | 'secondary' | 'ghost' | 'danger'
export type ButtonSize = 'sm' | 'md' | 'lg' | 'icon'

const BASE =
  'inline-flex items-center justify-center gap-2 font-semibold whitespace-nowrap transition-[background-color,box-shadow,color,transform] duration-200 select-none focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-indigo-600 active:scale-[0.98] disabled:cursor-not-allowed disabled:active:scale-100'

/** Deaktivierte Primär-Buttons werden bewusst GRAU – „button stays grey“ ist ein Ticket-Symptom. */
const VARIANTS: Record<ButtonVariant, string> = {
  primary:
    'bg-linear-to-r from-indigo-600 to-violet-600 text-white shadow-glow hover:from-indigo-500 hover:to-violet-500 hover:shadow-glow-lg disabled:from-slate-200 disabled:to-slate-200 disabled:text-slate-500 disabled:shadow-none',
  secondary:
    'bg-white text-slate-800 shadow-xs ring-1 ring-slate-200 hover:bg-slate-50 hover:ring-slate-300 disabled:bg-slate-100 disabled:text-slate-400 disabled:shadow-none',
  ghost: 'text-slate-600 hover:bg-slate-900/5 hover:text-slate-900 disabled:text-slate-400 disabled:hover:bg-transparent',
  danger: 'text-slate-400 hover:bg-rose-50 hover:text-rose-600 disabled:text-slate-300 disabled:hover:bg-transparent',
}

const SIZES: Record<ButtonSize, string> = {
  sm: 'h-9 rounded-xl px-4 text-sm',
  md: 'h-11 rounded-2xl px-5 text-sm',
  lg: 'h-13 rounded-2xl px-6 text-[15px]',
  icon: 'size-9 rounded-full p-0',
}

export interface ButtonStyleOptions {
  variant?: ButtonVariant
  size?: ButtonSize
  className?: string
}

/** Auch für Links nutzbar, die wie Buttons aussehen sollen (`<a className={buttonClassName(...)}>`). */
export function buttonClassName({ variant = 'primary', size = 'md', className }: ButtonStyleOptions = {}): string {
  return cn(BASE, VARIANTS[variant], SIZES[size], className)
}
