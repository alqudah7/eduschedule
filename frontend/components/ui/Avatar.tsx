import clsx from 'clsx'

const GRADIENTS = [
  'from-primary-500 to-primary-800',
  'from-blue-500 to-blue-800',
  'from-emerald-500 to-emerald-700',
  'from-amber-500 to-amber-700',
  'from-rose-500 to-rose-700',
  'from-cyan-500 to-cyan-700',
  'from-orange-400 to-red-600',
  'from-slate-500 to-slate-700',
]

const sizeClasses = {
  xs: 'w-6 h-6 text-xs',
  sm: 'w-8 h-8 text-xs',
  md: 'w-10 h-10 text-sm',
  lg: 'w-12 h-12 text-base',
  xl: 'w-16 h-16 text-lg',
}

type AvatarProps = {
  name: string
  initials: string
  size?: 'xs' | 'sm' | 'md' | 'lg' | 'xl'
  index?: number
  className?: string
}

export function Avatar({ name, initials, size = 'md', index = 0, className }: AvatarProps) {
  const gradient = GRADIENTS[index % GRADIENTS.length]
  return (
    <div
      className={clsx(
        'rounded-full bg-gradient-to-br flex items-center justify-center text-white font-semibold shrink-0',
        gradient,
        sizeClasses[size],
        className,
      )}
      title={name}
      aria-label={name}
    >
      {initials}
    </div>
  )
}
