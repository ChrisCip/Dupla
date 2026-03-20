import type { ButtonHTMLAttributes, ReactNode } from 'react'

type Props = ButtonHTMLAttributes<HTMLButtonElement> & {
  children: ReactNode
}

export function PrimaryButton({ children, className = '', ...rest }: Props) {
  return (
    <button
      type="button"
      className={`inline-flex items-center justify-center rounded-md bg-primary px-4 py-2 text-sm font-semibold uppercase tracking-wide text-white shadow-sm transition hover:opacity-90 disabled:cursor-not-allowed disabled:opacity-50 ${className}`}
      {...rest}
    >
      {children}
    </button>
  )
}
