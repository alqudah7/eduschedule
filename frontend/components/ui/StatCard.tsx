import clsx from 'clsx'
import { TrendingUp, TrendingDown } from 'lucide-react'

type StatCardProps = {
  title: string
  value: string | number
  icon: React.ReactNode
  iconBg: string
  trend?: { value: number; direction: 'up' | 'down'; isGood?: boolean; label?: string }
  accentColor?: 'teal' | 'green' | 'amber' | 'red'
}

const accentBorder = {
  teal:  'border-t-primary-500',
  green: 'border-t-emerald-500',
  amber: 'border-t-amber-500',
  red:   'border-t-red-500',
}

export function StatCard({ title, value, icon, iconBg, trend, accentColor = 'teal' }: StatCardProps) {
  const isPositive = trend?.isGood !== false ? trend?.direction === 'up' : trend?.direction === 'down'
  return (
    <div className={clsx(
      'bg-white rounded-lg border border-gray-200 p-6 shadow-sm border-t-2',
      accentBorder[accentColor],
    )}>
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs font-mono text-gray-500 uppercase tracking-wide mb-1">{title}</p>
          <p className="text-3xl font-syne font-bold text-gray-900">{value}</p>
          {trend && (
            <div className={clsx(
              'flex items-center gap-1 mt-2 text-xs',
              isPositive ? 'text-emerald-600' : 'text-red-500',
            )}>
              {trend.direction === 'up' ? <TrendingUp size={12} /> : <TrendingDown size={12} />}
              <span className="font-mono">{trend.value}%</span>
              {trend.label && <span className="text-gray-600">{trend.label}</span>}
            </div>
          )}
        </div>
        <div className={clsx('w-10 h-10 rounded-lg flex items-center justify-center', iconBg)}>
          {icon}
        </div>
      </div>
    </div>
  )
}
