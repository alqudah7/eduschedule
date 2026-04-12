import clsx from 'clsx'

type BadgeVariant = 'teal' | 'green' | 'amber' | 'red' | 'blue' | 'gray' | 'purple' | 'orange'

type BadgeProps = {
  variant: BadgeVariant
  size?: 'sm' | 'md'
  dot?: boolean
  children: React.ReactNode
  className?: string
}

const variantClasses: Record<BadgeVariant, string> = {
  teal:   'bg-primary-50 text-primary-700 border-primary-200',
  green:  'bg-emerald-50 text-emerald-700 border-emerald-200',
  amber:  'bg-amber-50 text-amber-700 border-amber-200',
  red:    'bg-red-50 text-red-700 border-red-200',
  blue:   'bg-blue-50 text-blue-700 border-blue-200',
  gray:   'bg-gray-100 text-gray-600 border-gray-200',
  purple: 'bg-violet-50 text-violet-700 border-violet-200',
  orange: 'bg-orange-50 text-orange-700 border-orange-200',
}

const dotColors: Record<BadgeVariant, string> = {
  teal: 'bg-primary-500', green: 'bg-emerald-500', amber: 'bg-amber-500',
  red: 'bg-red-500', blue: 'bg-blue-500', gray: 'bg-gray-400',
  purple: 'bg-violet-500', orange: 'bg-orange-500',
}

export function Badge({ variant, size = 'sm', dot, children, className }: BadgeProps) {
  return (
    <span className={clsx(
      'inline-flex items-center gap-1.5 rounded-full border font-medium font-mono',
      size === 'sm' ? 'px-2 py-0.5 text-xs' : 'px-2.5 py-1 text-xs',
      variantClasses[variant],
      className,
    )}>
      {dot && <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', dotColors[variant])} />}
      {children}
    </span>
  )
}
