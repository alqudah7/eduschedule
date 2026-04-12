'use client'
import { useState } from 'react'
import { AlertTriangle, AlertCircle, Info, CheckCircle, ShieldAlert } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Badge, Button } from '@/components/ui'
import { useAlerts, useAlertSummary, useResolveAlert } from '@/lib/hooks/useAlerts'
import { SEVERITY_CONFIG } from '@/lib/constants'
import { formatRelative } from '@/lib/utils'
import type { Severity } from '@/lib/types'
import clsx from 'clsx'

const SEVERITY_ICONS: Record<Severity, React.ElementType> = {
  CRITICAL: ShieldAlert, HIGH: AlertTriangle, MEDIUM: AlertCircle, LOW: Info, INFO: CheckCircle,
}

const SEVERITY_BADGE: Record<Severity, string> = {
  CRITICAL: 'red', HIGH: 'amber', MEDIUM: 'blue', LOW: 'gray', INFO: 'teal',
}

export default function AlertsPage() {
  const [filter, setFilter] = useState<string>('all')
  const { data: alerts = [], isLoading } = useAlerts(false)
  const { data: summary } = useAlertSummary()
  const resolve = useResolveAlert()

  const filtered = filter === 'all' ? alerts : alerts.filter(a => a.severity === filter)
  const severities: Severity[] = ['CRITICAL', 'HIGH', 'MEDIUM', 'LOW', 'INFO']

  return (
    <div>
      <PageHeader title="Alerts" description="Scheduling conflicts and system alerts" />

      {/* Summary pills */}
      <div className="flex flex-wrap gap-2 mb-6">
        {summary && severities.map(s => {
          const count = summary[s.toLowerCase() as keyof typeof summary] as number
          const cfg = SEVERITY_CONFIG[s]
          return (
            <div key={s} className={clsx('flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-mono', cfg.bgClass, cfg.borderClass, cfg.colorClass)}>
              <span className="uppercase">{s}</span>
              <span className="font-bold">{count}</span>
            </div>
          )
        })}
      </div>

      {/* Filter bar */}
      <div className="flex gap-1 mb-4 flex-wrap">
        {['all', ...severities].map(s => (
          <button
            key={s}
            onClick={() => setFilter(s)}
            className={clsx(
              'px-3 py-1.5 text-xs rounded-md font-medium transition-colors capitalize',
              filter === s ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-100',
            )}
          >
            {s.toLowerCase()}
          </button>
        ))}
        {(filter === 'LOW' || filter === 'INFO') && filtered.length > 0 && (
          <Button
            size="sm" variant="ghost"
            className="ml-auto"
            onClick={() => filtered.forEach(a => resolve.mutate(a.id))}
          >
            Resolve all
          </Button>
        )}
      </div>

      {/* Alert cards */}
      <div className="space-y-3">
        {isLoading ? (
          Array.from({ length: 3 }).map((_, i) => <div key={i} className="h-20 bg-gray-200 rounded-lg animate-pulse" />)
        ) : filtered.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg py-16 text-center text-xs text-gray-400">No alerts</div>
        ) : (
          filtered.map(alert => {
            const cfg = SEVERITY_CONFIG[alert.severity as Severity]
            const Icon = SEVERITY_ICONS[alert.severity as Severity]
            return (
              <div key={alert.id} className={clsx('rounded-lg border p-4', cfg.bgClass, cfg.borderClass)}>
                <div className="flex items-start gap-3">
                  <Icon size={16} className={clsx('shrink-0 mt-0.5', cfg.colorClass)} />
                  <div className="flex-1 min-w-0">
                    <div className="flex items-center gap-2 mb-1">
                      <p className={clsx('text-sm font-semibold', cfg.colorClass)}>{alert.title}</p>
                      <Badge variant={(SEVERITY_BADGE[alert.severity as Severity] ?? 'gray') as 'teal' | 'green' | 'amber' | 'red' | 'blue' | 'gray' | 'purple' | 'orange'} size="sm">{alert.severity}</Badge>
                      <span className="text-xs text-gray-400 font-mono ml-auto">{formatRelative(alert.createdAt)}</span>
                    </div>
                    <p className="text-xs text-gray-600">{alert.message}</p>
                  </div>
                  <Button size="sm" variant="secondary" onClick={() => resolve.mutate(alert.id)} loading={resolve.isPending}>Resolve</Button>
                </div>
              </div>
            )
          })
        )}
      </div>
    </div>
  )
}
