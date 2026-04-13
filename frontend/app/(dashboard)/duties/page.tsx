'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { Plus, Search } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Badge, Button, EmptyState } from '@/components/ui'
import { useDuties, useDeleteDuty } from '@/lib/hooks/useDuties'
import { DUTY_TYPE_CONFIG, STATUS_BADGE } from '@/lib/constants'
import type { BadgeVariant } from '@/lib/types'

const FILTER_TABS = [
  { key: '', label: 'All' },
  { key: 'CONFIRMED', label: 'Confirmed' },
  { key: 'SUBSTITUTE_NEEDED', label: 'Sub Needed' },
  { key: 'CONFLICT', label: 'Conflicts' },
  { key: 'UNASSIGNED', label: 'Unassigned' },
]

export default function DutiesPage() {
  const router = useRouter()
  const [statusFilter, setStatusFilter] = useState('')
  const { data: duties = [], isLoading } = useDuties(statusFilter ? { status: statusFilter } : undefined)
  const deleteDuty = useDeleteDuty()

  const counts: Record<string, number> = duties.reduce((acc, d) => ({
    ...acc, [d.status]: (acc[d.status] ?? 0) + 1,
  }), {} as Record<string, number>)

  return (
    <div>
      <PageHeader
        title="Duties"
        description="Manage teacher duty assignments"
        actions={<Button variant="primary" size="md" icon={<Plus size={14} />} onClick={() => router.push('/duties/new')}>New Duty</Button>}
      />

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        {/* Filter tabs */}
        <div className="px-4 pt-3 border-b border-gray-200 flex gap-0.5 overflow-x-auto">
          {FILTER_TABS.map(t => (
            <button
              key={t.key}
              onClick={() => setStatusFilter(t.key)}
              className={`px-4 py-2.5 text-xs font-medium rounded-t-md border-b-2 -mb-px flex items-center gap-1.5 transition-colors ${statusFilter === t.key ? 'border-primary-500 text-primary-700 bg-primary-50' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
            >
              {t.label}
              {t.key && counts[t.key] ? <span className="bg-gray-200 text-gray-600 rounded-full px-1.5 py-0.5 text-xs font-mono">{counts[t.key]}</span> : null}
            </button>
          ))}
        </div>

        <table className="w-full text-sm">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              {['Duty', 'Type', 'Day & Time', 'Location', 'Teacher', 'Status', 'Actions'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-500 uppercase tracking-wide">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {isLoading ? (
              Array.from({ length: 5 }).map((_, i) => (
                <tr key={i}>{Array.from({ length: 7 }).map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-200 rounded animate-pulse" /></td>)}</tr>
              ))
            ) : duties.length === 0 ? (
              <tr><td colSpan={7}><EmptyState title="No duties found" description="Create your first duty assignment" action={{ label: 'New Duty', onClick: () => router.push('/duties/new') }} /></td></tr>
            ) : (
              duties.map(duty => {
                const typeConfig = DUTY_TYPE_CONFIG[duty.type]
                return (
                  <tr key={duty.id} className="hover:bg-gray-50">
                    <td className="px-4 py-3 font-medium text-gray-800">{duty.name}</td>
                    <td className="px-4 py-3"><Badge variant={(typeConfig?.color ?? 'gray') as BadgeVariant} size="sm">{typeConfig?.label ?? duty.type}</Badge></td>
                    <td className="px-4 py-3 font-mono text-xs text-gray-500">{duty.day} · {duty.startTime}–{duty.endTime}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{duty.location}</td>
                    <td className="px-4 py-3">
                      {duty.teacher ? (
                        <div className="flex items-center gap-2">
                          <Avatar name={duty.teacher.name ?? ''} initials={duty.teacher.initials ?? '?'} size="xs" index={0} />
                          <span className="text-xs text-gray-700 truncate max-w-28">{duty.teacher.name}</span>
                        </div>
                      ) : <span className="text-xs text-gray-300">Unassigned</span>}
                    </td>
                    <td className="px-4 py-3"><Badge variant={(STATUS_BADGE[duty.status] ?? 'gray') as BadgeVariant} size="sm">{duty.status.replace('_', ' ')}</Badge></td>
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-1">
                        {duty.status === 'SUBSTITUTE_NEEDED' && <Button size="sm" variant="warning" onClick={() => router.push('/substitutions')}>Find Sub</Button>}
                        <Button size="sm" variant="ghost" onClick={() => deleteDuty.mutate(duty.id)}>Delete</Button>
                      </div>
                    </td>
                  </tr>
                )
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
