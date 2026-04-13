'use client'
import { useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { ArrowLeft, UserX, Edit, ClipboardPlus } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Badge, Button, WorkloadBar, Card } from '@/components/ui'
import { useTeacher, useMarkAbsent } from '@/lib/hooks/useTeachers'
import { STATUS_BADGE, DAYS } from '@/lib/constants'
import { formatDate } from '@/lib/utils'
import type { BadgeVariant } from '@/lib/types'

const TABS = ['Overview', 'Schedule', 'Duties', 'History']

export default function TeacherProfilePage() {
  const { id } = useParams<{ id: string }>()
  const router = useRouter()
  const { data: teacher, isLoading } = useTeacher(id)
  const markAbsent = useMarkAbsent()
  const [activeTab, setActiveTab] = useState('Overview')

  if (isLoading) return <div className="animate-pulse space-y-4"><div className="h-32 bg-gray-200 rounded-lg" /><div className="h-64 bg-gray-200 rounded-lg" /></div>
  if (!teacher) return <div className="text-center py-16 text-gray-500">Teacher not found</div>

  return (
    <div>
      <PageHeader
        title={teacher.name}
        breadcrumb={[{ label: 'Teachers', href: '/teachers' }, { label: teacher.name }]}
        actions={
          <div className="flex gap-2">
            <Button variant="ghost" size="sm" icon={<ArrowLeft size={14} />} onClick={() => router.push('/teachers')}>Back</Button>
            <Button variant="warning" size="sm" icon={<UserX size={14} />} loading={markAbsent.isPending} onClick={() => markAbsent.mutate(id)}>Mark Absent</Button>
            <Button variant="secondary" size="sm" icon={<Edit size={14} />}>Edit</Button>
          </div>
        }
      />

      {/* Profile header card */}
      <Card className="mb-6 flex items-center gap-6">
        <Avatar name={teacher.name} initials={teacher.initials} size="xl" index={0} />
        <div className="flex-1">
          <div className="flex items-center gap-3 mb-1">
            <h2 className="text-xl font-syne font-bold text-gray-900">{teacher.name}</h2>
            <Badge variant={(STATUS_BADGE[teacher.status] ?? 'gray') as BadgeVariant} dot>{teacher.status.replace('_', ' ')}</Badge>
          </div>
          <p className="text-sm text-gray-600 mb-2">{teacher.department}</p>
          <div className="flex items-center gap-6 text-xs text-gray-600 font-mono">
            <span>{teacher.email}</span>
            {teacher.phone && <span>{teacher.phone}</span>}
          </div>
        </div>
        <div className="text-right">
          <p className="text-xs font-mono text-gray-500 mb-1">Workload</p>
          <div className="w-40"><WorkloadBar value={teacher.workloadPct} /></div>
          <p className="text-xs text-gray-500 font-mono mt-1">{teacher.dutyCount} / {teacher.maxDuties} duties</p>
        </div>
      </Card>

      {/* Tabs */}
      <div className="flex gap-0.5 border-b border-gray-200 mb-6">
        {TABS.map(tab => (
          <button
            key={tab} onClick={() => setActiveTab(tab)}
            className={`px-4 py-2 text-sm font-medium transition-colors border-b-2 -mb-px ${activeTab === tab ? 'border-primary-500 text-primary-700' : 'border-transparent text-gray-500 hover:text-gray-700'}`}
          >
            {tab}
          </button>
        ))}
      </div>

      {/* Tab content */}
      {activeTab === 'Overview' && (
        <div className="grid grid-cols-2 gap-6">
          <Card>
            <h3 className="text-sm font-syne font-semibold text-gray-800 mb-3">Qualifications</h3>
            <div className="flex flex-wrap gap-2">
              {teacher.qualifications.map(q => <Badge key={q} variant="teal">{q}</Badge>)}
            </div>
          </Card>
          <Card>
            <h3 className="text-sm font-syne font-semibold text-gray-800 mb-3">Subjects</h3>
            <div className="flex flex-wrap gap-2">
              {teacher.subjects.map(s => <Badge key={s} variant="blue">{s}</Badge>)}
            </div>
          </Card>
          <Card className="col-span-2">
            <h3 className="text-sm font-syne font-semibold text-gray-800 mb-3">Quick Stats</h3>
            <div className="grid grid-cols-4 gap-4 text-center">
              {[
                { label: 'Total Duties', value: teacher.dutyCount },
                { label: 'Workload', value: `${teacher.workloadPct}%` },
                { label: 'Max Duties', value: teacher.maxDuties },
                { label: 'Status', value: teacher.status },
              ].map(s => (
                <div key={s.label} className="bg-gray-50 rounded-lg p-4">
                  <p className="text-2xl font-syne font-bold text-gray-900">{s.value}</p>
                  <p className="text-xs text-gray-500 font-mono mt-1">{s.label}</p>
                </div>
              ))}
            </div>
          </Card>
        </div>
      )}

      {activeTab === 'Duties' && (
        <Card padding="none">
          <table className="w-full text-sm">
            <thead><tr className="bg-gray-50 border-b border-gray-200">
              {['Name', 'Type', 'Day', 'Time', 'Location', 'Status'].map(h => (
                <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-500 uppercase">{h}</th>
              ))}
            </tr></thead>
            <tbody className="divide-y divide-gray-100">
              {((teacher as { duties?: Record<string, unknown>[] }).duties ?? []).map((d) => (
                <tr key={d.id as string} className="hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-800">{d.name as string}</td>
                  <td className="px-4 py-3"><Badge variant="blue" size="sm">{d.type as string}</Badge></td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{d.day as string}</td>
                  <td className="px-4 py-3 font-mono text-xs text-gray-500">{d.start_time as string}–{d.end_time as string}</td>
                  <td className="px-4 py-3 text-xs text-gray-500">{d.location as string}</td>
                  <td className="px-4 py-3"><Badge variant={(STATUS_BADGE[d.status as string] ?? 'gray') as BadgeVariant} size="sm">{(d.status as string).replace('_',' ')}</Badge></td>
                </tr>
              ))}
              {!(teacher as { duties?: unknown[] }).duties?.length && <tr><td colSpan={6} className="py-8 text-center text-xs text-gray-500">No duties assigned</td></tr>}
            </tbody>
          </table>
        </Card>
      )}

      {activeTab === 'History' && (
        <Card>
          <h3 className="text-sm font-syne font-semibold text-gray-800 mb-4">Absence History</h3>
          {((teacher as { absences?: Record<string, unknown>[] }).absences ?? []).length === 0 ? (
            <p className="text-xs text-gray-500 text-center py-8">No absences recorded</p>
          ) : (
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50"><th className="px-4 py-2 text-left text-xs font-mono text-gray-500">Date</th><th className="px-4 py-2 text-left text-xs font-mono text-gray-500">Reason</th></tr></thead>
              <tbody>
                {((teacher as { absences?: Record<string, unknown>[] }).absences ?? []).map(a => (
                  <tr key={a.id as string} className="border-t border-gray-100">
                    <td className="px-4 py-2 text-xs font-mono text-gray-600">{formatDate(a.date as string)}</td>
                    <td className="px-4 py-2 text-xs text-gray-500">{(a.reason as string) || '—'}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          )}
        </Card>
      )}

      {activeTab === 'Schedule' && (
        <Card>
          <p className="text-sm text-gray-500 text-center py-8">Schedule view — select teacher on the <a href="/schedule" className="text-primary-600 hover:underline">Schedule page</a></p>
        </Card>
      )}
    </div>
  )
}
