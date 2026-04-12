'use client'
import { forwardRef } from 'react'
import clsx from 'clsx'

type ButtonProps = React.ButtonHTMLAttributes<HTMLButtonElement> & {
  variant?: 'primary' | 'secondary' | 'danger' | 'ghost' | 'success' | 'warning'
  size?: 'sm' | 'md' | 'lg'
  loading?: boolean
  icon?: React.ReactNode
  iconPosition?: 'left' | 'right'
}

const variantClasses = {
  primary:   'bg-primary-500 text-white hover:bg-primary-600 border border-primary-500',
  secondary: 'bg-white border border-gray-200 text-gray-700 hover:bg-gray-50',
  danger:    'bg-red-50 text-red-600 border border-red-200 hover:bg-red-100',
  ghost:     'text-gray-600 hover:bg-gray-100 border border-transparent',
  success:   'bg-emerald-50 text-emerald-700 border border-emerald-200 hover:bg-emerald-100',
  warning:   'bg-amber-50 text-amber-700 border border-amber-200 hover:bg-amber-100',
}

const sizeClasses = {
  sm:  'py-1.5 px-3 text-xs gap-1.5',
  md:  'py-2 px-4 text-sm gap-2',
  lg:  'py-2.5 px-5 text-base gap-2',
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  ({ variant = 'primary', size = 'md', loading, icon, iconPosition = 'left', children, className, disabled, ...props }, ref) => {
    return (
      <button
        ref={ref}
        disabled={disabled || loading}
        className={clsx(
          'inline-flex items-center justify-center font-medium rounded-md transition-all duration-150 cursor-pointer',
          'focus:outline-none focus-visible:ring-2 focus-visible:ring-primary-500 focus-visible:ring-offset-1',
          'disabled:opacity-50 disabled:cursor-not-allowed',
          variantClasses[variant],
          sizeClasses[size],
          className,
        )}
        {...props}
      >
        {loading && (
          <svg className="animate-spin h-3.5 w-3.5" fill="none" viewBox="0 0 24 24">
            <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
            <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
          </svg>
        )}
        {!loading && icon && iconPosition === 'left' && <span className="shrink-0">{icon}</span>}
        {children && <span>{children}</span>}
        {!loading && icon && iconPosition === 'right' && <span className="shrink-0">{icon}</span>}
      </button>
    )
  }
)
Button.displayName = 'Button'
