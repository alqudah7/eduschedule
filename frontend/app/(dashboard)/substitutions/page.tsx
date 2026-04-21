'use client'
import { useState } from 'react'
import { Clock, MapPin, Calendar, ChevronDown, ChevronUp, BookOpen, GraduationCap } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Badge, Button, WorkloadBar } from '@/components/ui'
import { useSubstitutions, useSubstituteSuggestions, useAssignSubstitute } from '@/lib/hooks/useSubstitutions'

const TIER_COLORS: Record<number, 'green' | 'teal' | 'blue' | 'gray'> = {
  0: 'green',
  1: 'teal',
  2: 'blue',
  3: 'gray',
}

function TierBadge({ tier, label }: { tier: number; label: string }) {
  return (
    <Badge variant={TIER_COLORS[tier] ?? 'gray'} size="sm">
      {label}
    </Badge>
  )
}

type Suggestion = {
  teacher: Record<string, unknown>
  load_pct: number
  score: number
  tier: number
  tier_label: string
  subject_match: boolean
  level_match: boolean
}

function SubCard({ sub }: { sub: Record<string, unknown> }) {
  const { data: suggestions = [] } = useSubstituteSuggestions(sub.id as string)
  const assign = useAssignSubstitute()

  return (
    <div className="bg-white rounded-lg border border-amber-200 shadow-sm overflow-hidden">
      <div className="bg-amber-50 px-4 py-3 border-b border-amber-200 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Badge variant="amber" dot>Pending</Badge>
          <span className="text-sm font-semibold text-gray-800">{(sub.duty as { name?: string })?.name ?? 'Unknown duty'}</span>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 font-mono">
          <span className="flex items-center gap-1"><Clock size={10} />{(sub.duty as { start_time?: string })?.start_time}–{(sub.duty as { end_time?: string })?.end_time}</span>
          <span className="flex items-center gap-1"><MapPin size={10} />{(sub.duty as { location?: string })?.location ?? '—'}</span>
          <span className="flex items-center gap-1"><Calendar size={10} />{(sub.duty as { day?: string })?.day}</span>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
          <Avatar name={(sub.absent_teacher as { name?: string })?.name ?? 'Unknown'} initials={((sub.absent_teacher as { name?: string })?.name ?? 'U').slice(0,2).toUpperCase()} size="sm" index={1} />
          <div>
            <p className="text-sm font-medium text-gray-800">{(sub.absent_teacher as { name?: string })?.name ?? '—'}</p>
            <p className="text-xs text-gray-500">Absent · {(sub.absent_teacher as { school_level?: string })?.school_level ?? 'All Levels'}</p>
          </div>
        </div>
        <p className="text-xs font-mono font-semibold text-gray-500 uppercase mb-3">Suggested Substitutes</p>
        <div className="space-y-3">
          {(suggestions as Suggestion[]).map((s, i) => (
            <div key={i} className="flex items-center gap-3 rounded-lg p-2 hover:bg-gray-50 transition-colors">
              <Avatar name={s.teacher.name as string} initials={(s.teacher.initials as string) || (s.teacher.name as string).slice(0,2)} size="sm" index={i + 2} />
              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 mb-0.5">
                  <p className="text-sm font-medium text-gray-800 truncate">{s.teacher.name as string}</p>
                  <TierBadge tier={s.tier} label={s.tier_label} />
                </div>
                <div className="flex items-center gap-2 text-xs text-gray-500">
                  <span>{s.teacher.department as string}</span>
                  {s.subject_match && (
                    <span className="flex items-center gap-0.5 text-green-600"><BookOpen size={10} /> Subject match</span>
                  )}
                  {s.level_match && (
                    <span className="flex items-center gap-0.5 text-teal-600"><GraduationCap size={10} /> {s.teacher.school_level as string}</span>
                  )}
                </div>
              </div>
              <div className="w-28 shrink-0"><WorkloadBar value={s.load_pct} size="sm" /></div>
              <Button
                size="sm"
                variant="primary"
                loading={assign.isPending}
                onClick={() => assign.mutate({ subId: sub.id as string, substituteId: s.teacher.id as string })}
              >
                Assign
              </Button>
            </div>
          ))}
          {suggestions.length === 0 && <p className="text-xs text-gray-500 text-center py-4">No eligible substitutes found</p>}
        </div>
      </div>
    </div>
  )
}

export default function SubstitutionsPage() {
  const { data: openSubs = [] } = useSubstitutions('PENDING')
  const { data: resolvedSubs = [] } = useSubstitutions('ACCEPTED')
  const [showResolved, setShowResolved] = useState(false)

  return (
    <div>
      <PageHeader title="Substitutions" description="Manage substitution requests and assignments" />

      <section className="mb-8">
        <h2 className="text-sm font-syne font-semibold text-gray-700 mb-4">
          Open Requests <span className="text-xs font-mono text-gray-500 ml-2">{openSubs.length}</span>
        </h2>
        {openSubs.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg py-12 text-center text-xs text-gray-500">No open substitution requests</div>
        ) : (
          <div className="space-y-4">
            {(openSubs as Record<string,unknown>[]).map(sub => <SubCard key={sub.id as string} sub={sub} />)}
          </div>
        )}
      </section>

      <section>
        <button
          onClick={() => setShowResolved(v => !v)}
          className="flex items-center gap-2 text-sm font-syne font-semibold text-gray-500 hover:text-gray-700 mb-4 transition-colors"
        >
          Resolved Requests <span className="text-xs font-mono ml-1">{resolvedSubs.length}</span>
          {showResolved ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {showResolved && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead><tr className="bg-gray-50 border-b border-gray-200">
                {['Duty', 'Absent Teacher', 'Substitute', 'Status'].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-500 uppercase">{h}</th>
                ))}
              </tr></thead>
              <tbody className="divide-y divide-gray-100">
                {(resolvedSubs as Record<string,unknown>[]).map(s => (
                  <tr key={s.id as string}>
                    <td className="px-4 py-3 text-xs text-gray-700">{(s.duty as { name?: string })?.name ?? '—'}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{(s.absent_teacher as { name?: string })?.name ?? '—'}</td>
                    <td className="px-4 py-3 text-xs text-gray-500">{(s.substitute as { name?: string })?.name ?? '—'}</td>
                    <td className="px-4 py-3"><Badge variant="green" size="sm">Resolved</Badge></td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </section>
    </div>
  )
}
