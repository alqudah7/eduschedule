import clsx from 'clsx'

type CardProps = {
  children: React.ReactNode
  className?: string
  padding?: 'none' | 'sm' | 'md' | 'lg'
}

const paddingClasses = {
  none: '',
  sm:   'p-4',
  md:   'p-6',
  lg:   'p-8',
}

export function Card({ children, className, padding = 'md' }: CardProps) {
  return (
    <div className={clsx(
      'bg-white rounded-lg border border-gray-200 shadow-sm',
      paddingClasses[padding],
      className,
    )}>
      {children}
    </div>
  )
}
