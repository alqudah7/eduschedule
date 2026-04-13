'use client'
import { useRouter } from 'next/navigation'
import Link from 'next/link'
import { Users, CheckCircle, ClipboardList, AlertTriangle, Clock, MapPin, Calendar } from 'lucide-react'
import { StatCard } from '@/components/ui/StatCard'
import { WorkloadBar } from '@/components/ui/WorkloadBar'
import { Avatar } from '@/components/ui/Avatar'
import { Badge } from '@/components/ui/Badge'
import { Button } from '@/components/ui/Button'
import { SkeletonCard } from '@/components/ui/Skeleton'
import { useReportSummary, useWorkloadReport, useAuditLog } from '@/lib/hooks/useReports'
import { useAlerts } from '@/lib/hooks/useAlerts'
import { useSubstitutions, useSubstituteSuggestions, useAssignSubstitute } from '@/lib/hooks/useSubstitutions'
import { useDuties } from '@/lib/hooks/useDuties'
import { formatRelative } from '@/lib/utils'
import { STATUS_BADGE } from '@/lib/constants'
import type { BadgeVariant } from '@/lib/types'

function SubRequestPanel({ sub }: { sub: Record<string, unknown> }) {
  const { data: suggestions = [] } = useSubstituteSuggestions(sub.id as string)
  const assign = useAssignSubstitute()

  return (
    <div className="bg-white rounded-lg border border-amber-200 shadow-sm">
      <div className="px-4 py-3 border-b border-amber-100 flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-mono font-medium text-amber-600 uppercase">Substitution Needed</span>
          <Badge variant="amber" dot>Pending</Badge>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-3">
          <Avatar name={(sub.absent_teacher as { name?: string })?.name ?? 'Unknown'} initials={((sub.absent_teacher as { name?: string })?.name ?? 'U').slice(0, 2).toUpperCase()} size="sm" index={1} />
          <div>
            <p className="text-sm font-medium text-gray-900">{(sub.absent_teacher as { name?: string })?.name ?? '—'}</p>
            <p className="text-xs text-gray-600">absent</p>
          </div>
          <div className="ml-auto text-right text-xs text-gray-500 font-mono space-y-0.5">
            <div className="flex items-center gap-1"><Clock size={10} />{(sub.duty as { start_time?: string })?.start_time}–{(sub.duty as { end_time?: string })?.end_time}</div>
            <div className="flex items-center gap-1"><MapPin size={10} />{(sub.duty as { location?: string })?.location ?? '—'}</div>
            <div className="flex items-center gap-1"><Calendar size={10} />{(sub.duty as { day?: string })?.day}</div>
          </div>
        </div>
        <p className="text-xs font-semibold text-gray-500 uppercase font-mono mb-2">Suggested Substitutes</p>
        <div className="space-y-2">
          {suggestions.slice(0, 3).map((s, i) => (
            <div key={i} className="flex items-center gap-3 py-1.5">
              <Avatar name={s.teacher.name as string} initials={(s.teacher.initials as string) || (s.teacher.name as string).slice(0,2).toUpperCase()} size="sm" index={i + 2} />
              <div className="flex-1 min-w-0">
                <p className="text-sm font-medium text-gray-800 truncate">{s.teacher.name as string}</p>
                <p className="text-xs text-gray-600">{s.teacher.department as string}</p>
              </div>
              <div className="w-24">
                <WorkloadBar value={s.load_pct} showLabel size="sm" />
              </div>
              <Button
                size="sm" variant="primary"
                loading={assign.isPending}
                onClick={() => assign.mutate({ subId: sub.id as string, substituteId: s.teacher.id as string })}
              >
                Assign
              </Button>
            </div>
          ))}
          {suggestions.length === 0 && <p className="text-xs text-gray-500 text-center py-2">No eligible substitutes available</p>}
        </div>
      </div>
    </div>
  )
}

export default function DashboardPage() {
  const { data: summary, isLoading: summaryLoading } = useReportSummary()
  const { data: workload = [] } = useWorkloadReport()
  const { data: criticalAlerts = [] } = useAlerts(false)
  const { data: openSubs = [] } = useSubstitutions('PENDING')
  const { data: todayDuties = [] } = useDuties()
  const { data: auditData } = useAuditLog()

  const criticalCount = criticalAlerts.filter(a => a.severity === 'CRITICAL').length

  return (
    <div className="space-y-6">
      {/* Conflict alert banner */}
      {criticalCount > 0 && (
        <div className="flex items-center justify-between bg-red-50 border border-red-200 rounded-lg px-4 py-3">
          <div className="flex items-center gap-2 text-red-700 text-sm">
            <AlertTriangle size={16} />
            <span className="font-medium">{criticalCount} scheduling conflict{criticalCount > 1 ? 's' : ''} detected.</span>
          </div>
          <Link href="/alerts">
            <Button size="sm" variant="danger">View Alerts →</Button>
          </Link>
        </div>
      )}

      {/* Stat cards */}
      <div className="grid grid-cols-4 gap-4">
        {summaryLoading ? (
          Array.from({ length: 4 }).map((_, i) => <SkeletonCard key={i} />)
        ) : (
          <>
            <StatCard title="Total Teachers" value={summary?.totalTeachers ?? 0} icon={<Users size={18} className="text-primary-600" />} iconBg="bg-primary-50" accentColor="teal" />
            <StatCard title="Active Today" value={summary?.activeToday ?? 0} icon={<CheckCircle size={18} className="text-emerald-600" />} iconBg="bg-emerald-50" accentColor="green" />
            <StatCard title="Duties Scheduled" value={summary?.totalDuties ?? 0} icon={<ClipboardList size={18} className="text-amber-600" />} iconBg="bg-amber-50" accentColor="amber" />
            <StatCard title="Issues Pending" value={summary?.issuesPending ?? 0} icon={<AlertTriangle size={18} className="text-red-500" />} iconBg="bg-red-50" accentColor="red" />
          </>
        )}
      </div>

      {/* Two-column layout */}
      <div className="grid grid-cols-3 gap-6">
        <div className="col-span-2 space-y-6">
          {openSubs.length > 0 && <SubRequestPanel sub={openSubs[0] as Record<string, unknown>} />}
          {/* Today's duties */}
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
            <div className="px-4 py-3 border-b border-gray-200">
              <h3 className="text-sm font-syne font-semibold text-gray-900">Today's Duties</h3>
            </div>
            <div className="divide-y divide-gray-100">
              {todayDuties.slice(0, 6).map(duty => (
                <div key={duty.id} className="px-4 py-3 flex items-center gap-3">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium text-gray-800 truncate">{duty.name}</p>
                    <p className="text-xs text-gray-500 font-mono">{duty.startTime}–{duty.endTime} · {duty.location}</p>
                  </div>
                  {duty.teacher && (
                    <div className="flex items-center gap-2 text-xs text-gray-500">
                      <Avatar name={duty.teacher.name ?? ''} initials={duty.teacher.initials ?? '?'} size="xs" index={0} />
                      <span className="truncate max-w-24">{duty.teacher.name}</span>
                    </div>
                  )}
                  <Badge variant={(STATUS_BADGE[duty.status] ?? 'gray') as BadgeVariant} size="sm">{duty.status.replace('_', ' ')}</Badge>
                </div>
              ))}
              {todayDuties.length === 0 && (
                <div className="py-8 text-center text-xs text-gray-500">No duties scheduled</div>
              )}
            </div>
          </div>
        </div>

        {/* Activity feed */}
        <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
          <div className="px-4 py-3 border-b border-gray-200">
            <h3 className="text-sm font-syne font-semibold text-gray-900">Activity Log</h3>
          </div>
          <div className="divide-y divide-gray-100">
            {(auditData?.logs ?? []).slice(0, 10).map(log => (
              <div key={log.id} className="px-4 py-3 flex gap-3">
                <div className="w-1.5 h-1.5 rounded-full bg-primary-400 mt-1.5 shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="text-xs text-gray-700 leading-relaxed">{log.details}</p>
                  <p className="text-xs text-gray-500 font-mono mt-0.5">{formatRelative(log.createdAt)}</p>
                </div>
              </div>
            ))}
            {!auditData?.logs?.length && (
              <div className="py-8 text-center text-xs text-gray-500">No activity yet</div>
            )}
          </div>
        </div>
      </div>

      {/* Workload overview */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-200">
          <h3 className="text-sm font-syne font-semibold text-gray-900">Workload Overview</h3>
        </div>
        <table className="w-full text-sm">
          <thead>
            <tr>
              {['Teacher', 'Department', 'Status', 'Duty Load', 'Qualifications'].map(h => (
                <th key={h} className="px-4 py-2.5 text-left text-xs font-mono text-gray-500 uppercase bg-gray-50 border-b border-gray-100">{h}</th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-gray-100">
            {workload.map((row, i) => (
              <tr key={row.teacherId} className="hover:bg-gray-50">
                <td className="px-4 py-3">
                  <div className="flex items-center gap-2">
                    <Avatar name={row.name} initials={row.name.slice(0,2).toUpperCase()} size="xs" index={i} />
                    <span className="font-medium text-gray-800 text-xs">{row.name}</span>
                  </div>
                </td>
                <td className="px-4 py-3 text-xs text-gray-500">{row.department}</td>
                <td className="px-4 py-3"><Badge variant="teal" size="sm">Active</Badge></td>
                <td className="px-4 py-3 w-48"><WorkloadBar value={row.workloadPct} size="sm" /></td>
                <td className="px-4 py-3 text-xs text-gray-500 font-mono">{row.dutyCount}/{row.maxDuties} duties</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
