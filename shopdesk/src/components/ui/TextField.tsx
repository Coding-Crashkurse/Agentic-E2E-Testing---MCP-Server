import { useId, type InputHTMLAttributes } from 'react'
import { cn } from '../../lib/cn'

interface TextFieldProps extends Omit<InputHTMLAttributes<HTMLInputElement>, 'name' | 'id'> {
  name: string
  label: string
  error?: string
  hint?: string
}

/**
 * Beschriftetes Eingabefeld mit Fehleranzeige.
 * Test-IDs: `field-<name>` für das Input, `error-<name>` für die Fehlermeldung.
 */
export function TextField({ name, label, error, hint, className, ...rest }: TextFieldProps) {
  const id = useId()
  const messageId = `${id}-message`
  const message = error ?? hint

  return (
    <div className={cn('flex flex-col gap-1.5', className)}>
      <label htmlFor={id} className="text-[13px] font-medium text-slate-600">
        {label}
      </label>
      <input
        id={id}
        name={name}
        data-testid={`field-${name}`}
        aria-invalid={error ? true : undefined}
        aria-describedby={message ? messageId : undefined}
        className={cn(
          'h-12 w-full rounded-2xl border bg-white px-4 text-[15px] text-slate-900 shadow-xs transition-[border-color,box-shadow] duration-200 placeholder:text-slate-400 focus:ring-4 focus:outline-none',
          error
            ? 'border-rose-300 focus:border-rose-500 focus:ring-rose-500/10'
            : 'border-slate-200 hover:border-slate-300 focus:border-indigo-500 focus:ring-indigo-500/10',
        )}
        {...rest}
      />
      {error ? (
        <p id={messageId} data-testid={`error-${name}`} role="alert" className="text-sm text-rose-600">
          {error}
        </p>
      ) : hint ? (
        <p id={messageId} className="text-sm text-slate-500">
          {hint}
        </p>
      ) : null}
    </div>
  )
}
