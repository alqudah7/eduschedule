'use client'
import { useMemo, useState } from 'react'
import { Clock, MapPin, Calendar, ChevronDown, ChevronUp, BookOpen, GraduationCap, Users, AlertTriangle, Zap } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Badge, Button, WorkloadBar } from '@/components/ui'
import { useTeachers } from '@/lib/hooks/useTeachers'
import {
  useSubstitutions, useSubstituteSuggestions, useAssignSubstitute,
  useLessonSubSuggestions,
  useWholeDayPlan, useAssignDay,
  type DayPlan, type DayPlanRow,
} from '@/lib/hooks/useSubstitutions'

const DAYS = [
  { key: 'SUN', label: 'Sunday'    },
  { key: 'MON', label: 'Monday'    },
  { key: 'TUE', label: 'Tuesday'   },
  { key: 'WED', label: 'Wednesday' },
  { key: 'THU', label: 'Thursday'  },
]

// Tier 1 = best; TIER_COLORS[1..4] map to badge variants.
const TIER_COLORS: Record<number, 'green' | 'teal' | 'blue' | 'amber' | 'gray'> = {
  0: 'green', 1: 'green', 2: 'teal', 3: 'blue', 4: 'amber',
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

function TierBadge({ tier, label }: { tier: number; label: string }) {
  return <Badge variant={TIER_COLORS[tier] ?? 'gray'} size="sm">{label}</Badge>
}

const LEVEL_COLOR: Record<string, string> = {
  PRESCHOOL:  'text-pink-600',
  ELEMENTARY: 'text-green-600',
  MIDDLE:     'text-blue-600',
  HIGH:       'text-purple-600',
  ALL:        'text-gray-400',
}

function SuggestionsPanel({
  suggestions, onAssign, isPending,
}: {
  suggestions: Suggestion[]
  onAssign: (teacherId: string) => void
  isPending: boolean
}) {
  return (
    <div className="space-y-3">
      {suggestions.map((s, i) => (
        <div key={i} className="flex items-center gap-3 rounded-lg p-2 hover:bg-gray-50 transition-colors">
          <Avatar
            name={s.teacher.name as string}
            initials={(s.teacher.initials as string) || (s.teacher.name as string).slice(0, 2)}
            size="sm"
            index={i + 2}
          />
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 mb-0.5">
              <p className="text-sm font-medium text-gray-800 truncate">{s.teacher.name as string}</p>
              <TierBadge tier={s.tier} label={s.tier_label} />
            </div>
            <div className="flex items-center gap-2 text-xs text-gray-500">
              <span className={`flex items-center gap-0.5 ${LEVEL_COLOR[s.teacher.school_level as string] ?? 'text-gray-400'}`}>
                <GraduationCap size={10} /> {s.teacher.school_level as string}
              </span>
              <span>
                {((s.teacher.subjects as string[]) ?? []).slice(0, 2).join(' · ') || s.teacher.department as string}
              </span>
              {s.subject_match && (
                <span className="flex items-center gap-0.5 text-green-600">
                  <BookOpen size={10} /> Match
                </span>
              )}
            </div>
          </div>
          <div className="w-28 shrink-0"><WorkloadBar value={s.load_pct} size="sm" /></div>
          <Button
            size="sm"
            variant="primary"
            loading={isPending}
            onClick={() => onAssign(s.teacher.id as string)}
          >
            Assign
          </Button>
        </div>
      ))}
      {suggestions.length === 0 && (
        <p className="text-xs text-gray-500 text-center py-4">No eligible substitutes found</p>
      )}
    </div>
  )
}

function DutySubCard({ sub }: { sub: Record<string, unknown> }) {
  const { data: suggestions = [] } = useSubstituteSuggestions(sub.id as string)
  const assign = useAssignSubstitute()
  const duty = sub.duty as Record<string, unknown> | undefined

  return (
    <div className="bg-white rounded-lg border border-amber-200 shadow-sm overflow-hidden">
      <div className="bg-amber-50 px-4 py-3 border-b border-amber-200 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Badge variant="amber" dot>Pending</Badge>
          <span className="text-sm font-semibold text-gray-800">{duty?.name as string ?? 'Unknown duty'}</span>
          <Badge variant="blue" size="sm">Duty</Badge>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 font-mono">
          <span className="flex items-center gap-1">
            <Clock size={10} />{duty?.start_time as string}–{duty?.end_time as string}
          </span>
          <span className="flex items-center gap-1">
            <MapPin size={10} />{duty?.location as string ?? '—'}
          </span>
          <span className="flex items-center gap-1">
            <Calendar size={10} />{duty?.day as string}
          </span>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
          <Avatar
            name={(sub.absent_teacher as { name?: string })?.name ?? 'Unknown'}
            initials={((sub.absent_teacher as { name?: string })?.name ?? 'U').slice(0, 2).toUpperCase()}
            size="sm"
            index={1}
          />
          <div>
            <p className="text-sm font-medium text-gray-800">{(sub.absent_teacher as { name?: string })?.name ?? '—'}</p>
            <p className="text-xs text-gray-500">Absent teacher</p>
          </div>
        </div>
        <p className="text-xs font-mono font-semibold text-gray-500 uppercase mb-3">Suggested Substitutes</p>
        <SuggestionsPanel
          suggestions={suggestions as Suggestion[]}
          onAssign={(substituteId) => assign.mutate({ subId: sub.id as string, substituteId })}
          isPending={assign.isPending}
        />
      </div>
    </div>
  )
}

function LessonSubCard({ sub }: { sub: Record<string, unknown> }) {
  const { data: suggestions = [] } = useLessonSubSuggestions(sub.id as string)
  const assign = useAssignSubstitute()
  const lesson = sub.lesson as Record<string, unknown> | undefined

  return (
    <div className="bg-white rounded-lg border border-purple-200 shadow-sm overflow-hidden">
      <div className="bg-violet-50 px-4 py-3 border-b border-purple-200 flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-3">
          <Badge variant="amber" dot>Pending</Badge>
          <span className="text-sm font-semibold text-gray-800">
            {lesson?.subject as string ?? 'Unknown'} · {lesson?.class as string ?? ''}
          </span>
          <Badge variant="purple" size="sm">Class Cover</Badge>
        </div>
        <div className="flex items-center gap-4 text-xs text-gray-500 font-mono">
          <span className="flex items-center gap-1">
            <Clock size={10} />{lesson?.start_time as string}–{lesson?.end_time as string}
          </span>
          <span className="flex items-center gap-1">
            <MapPin size={10} />{lesson?.room as string ?? '—'}
          </span>
          <span className="flex items-center gap-1">
            <Calendar size={10} />{lesson?.day as string}
          </span>
        </div>
      </div>
      <div className="p-4">
        <div className="flex items-center gap-3 mb-4 pb-4 border-b border-gray-100">
          <Avatar
            name={(sub.absent_teacher as { name?: string })?.name ?? 'Unknown'}
            initials={((sub.absent_teacher as { name?: string })?.name ?? 'U').slice(0, 2).toUpperCase()}
            size="sm"
            index={1}
          />
          <div>
            <p className="text-sm font-medium text-gray-800">{(sub.absent_teacher as { name?: string })?.name ?? '—'}</p>
            <p className="text-xs text-gray-500">Absent · {lesson?.school_level as string ?? ''}</p>
          </div>
        </div>
        <p className="text-xs font-mono font-semibold text-gray-500 uppercase mb-3">Available Teachers</p>
        <SuggestionsPanel
          suggestions={suggestions as Suggestion[]}
          onAssign={(substituteId) => assign.mutate({ subId: sub.id as string, substituteId })}
          isPending={assign.isPending}
        />
      </div>
    </div>
  )
}

// ─── Whole-day coverage panel ────────────────────────────────────────────────

function PlanRow({
  row, selectedId, onSelect, loadCounts, isCommitted,
}: {
  row: DayPlanRow
  selectedId: string
  onSelect: (subId: string) => void
  loadCounts: Record<string, number>
  isCommitted: boolean
}) {
  const l = row.lesson
  const top = row.suggestions[0]
  // The picked suggestion — used to render extras like tier badge and load.
  const picked = row.suggestions.find(s => s.teacher.id === selectedId) ?? top

  if (row.uncovered) {
    return (
      <div className="flex items-center gap-4 py-3 px-4 border-b border-gray-100 last:border-0 bg-red-50/40">
        <span className="w-8 shrink-0 text-xs font-mono text-gray-500">P{row.period_index}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">
            {l.subject} · <span className="text-gray-600">{l.class}</span>
          </p>
          <p className="text-xs text-gray-500 font-mono">
            {l.start_time}–{l.end_time} · {l.room}
          </p>
        </div>
        <div className="flex items-center gap-2 text-red-700 text-xs">
          <AlertTriangle size={14} />
          <span className="font-medium">No available teacher</span>
        </div>
      </div>
    )
  }

  if (isCommitted) {
    return (
      <div className="flex items-center gap-4 py-3 px-4 border-b border-gray-100 last:border-0 bg-green-50/30">
        <span className="w-8 shrink-0 text-xs font-mono text-gray-500">P{row.period_index}</span>
        <div className="flex-1 min-w-0">
          <p className="text-sm font-medium text-gray-800">
            {l.subject} · <span className="text-gray-600">{l.class}</span>
          </p>
          <p className="text-xs text-gray-500 font-mono">
            {l.start_time}–{l.end_time} · {l.room}
          </p>
        </div>
        <Badge variant={row.existing_status === 'ACCEPTED' ? 'green' : 'amber'} size="sm">
          {row.existing_status === 'ACCEPTED' ? 'Covered' : 'Pending'}
        </Badge>
      </div>
    )
  }

  return (
    <div className="flex items-center gap-4 py-3 px-4 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
      <span className="w-8 shrink-0 text-xs font-mono text-gray-500">P{row.period_index}</span>
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-800">
          {l.subject} · <span className="text-gray-600">{l.class}</span>
        </p>
        <p className="text-xs text-gray-500 font-mono">
          {l.start_time}–{l.end_time} · {l.room} · {l.school_level}
        </p>
      </div>
      <div className="w-72 shrink-0">
        <select
          value={selectedId}
          onChange={e => onSelect(e.target.value)}
          className="w-full text-sm border border-gray-200 rounded-md px-2 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
        >
          {row.suggestions.map(s => {
            const load = loadCounts[s.teacher.id] ?? 0
            const loadHint = load > 0 ? `  · ${load} today` : ''
            return (
              <option key={s.teacher.id} value={s.teacher.id}>
                {s.teacher.name} · {s.tier_label}{loadHint}
              </option>
            )
          })}
        </select>
      </div>
      {picked && (
        <div className="flex items-center gap-2 shrink-0">
          <Badge variant={TIER_COLORS[picked.tier] ?? 'gray'} size="sm">
            T{picked.tier}
          </Badge>
          {picked.continuity_bonus && (
            <span title="Bonus: covers an adjacent period">
              <Zap size={12} className="text-amber-500" />
            </span>
          )}
          <span className="text-xs text-gray-500 font-mono w-14 text-right">
            {loadCounts[picked.teacher.id] ?? 0} today
          </span>
        </div>
      )}
    </div>
  )
}

function WholeDayPlanPanel() {
  const { data: teachers = [] } = useTeachers()
  const [teacherId, setTeacherId] = useState('')
  const [day, setDay] = useState('')
  // Per-lesson selection overrides. Falls back to plan's top pick when unset.
  const [selections, setSelections] = useState<Record<string, string>>({})

  const { data: plan, isLoading, isError, error, isFetching } = useWholeDayPlan(teacherId, day)
  const assignDay = useAssignDay()

  const absentTeachers = teachers.filter(t => t.status === 'ABSENT')

  // Reset selections whenever the target changes.
  const planKey = `${teacherId}::${day}::${plan?.plan.length ?? 0}`
  useMemo(() => setSelections({}), [planKey])  // eslint-disable-line react-hooks/exhaustive-deps

  const rowsWithChoice = (plan?.plan ?? []).map(row => {
    if (row.existing_substitution_id || row.uncovered) return { row, chosen: '' }
    const chosen = selections[row.lesson.id] ?? row.suggestions[0]?.teacher.id ?? ''
    return { row, chosen }
  })

  // Load-per-teacher across the current plan's chosen picks (for the "spread" hint).
  const loadCounts: Record<string, number> = {}
  for (const { row, chosen } of rowsWithChoice) {
    if (!chosen) continue
    // Add the chosen sub's current_load as the baseline and count within-batch reuse.
    const s = row.suggestions.find(x => x.teacher.id === chosen)
    if (!s) continue
    loadCounts[chosen] = (loadCounts[chosen] ?? s.current_load) + 1
  }

  const toAssign = rowsWithChoice
    .filter(({ row, chosen }) => !row.existing_substitution_id && !row.uncovered && chosen)
    .map(({ row, chosen }) => ({ lesson_id: row.lesson.id, substitute_id: chosen }))

  const onAssignAll = () => {
    if (!teacherId || !day || toAssign.length === 0) return
    assignDay.mutate({ absent_teacher_id: teacherId, day, assignments: toAssign })
  }

  const teacherName = plan?.teacher_name ?? absentTeachers.find(t => t.id === teacherId)?.name ?? ''
  const dayLabel = DAYS.find(d => d.key === day)?.label ?? day

  return (
    <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden mb-8">
      <div className="bg-gray-50 px-4 py-3 border-b border-gray-200 flex items-center gap-3">
        <Users size={14} className="text-gray-500" />
        <span className="text-sm font-syne font-semibold text-gray-700">Whole-day Coverage Plan</span>
      </div>
      <div className="p-4 flex gap-4 flex-wrap border-b border-gray-100">
        <div className="flex-1 min-w-48">
          <label className="block text-xs font-mono text-gray-500 mb-1 uppercase tracking-wide">Absent Teacher</label>
          <select
            value={teacherId}
            onChange={e => setTeacherId(e.target.value)}
            disabled={absentTeachers.length === 0}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white disabled:opacity-50"
          >
            <option value="">{absentTeachers.length === 0 ? 'No absent teachers today' : 'Select teacher…'}</option>
            {absentTeachers.map(t => (
              <option key={t.id} value={t.id}>{t.name}</option>
            ))}
          </select>
        </div>
        <div className="min-w-40">
          <label className="block text-xs font-mono text-gray-500 mb-1 uppercase tracking-wide">Day</label>
          <select
            value={day}
            onChange={e => setDay(e.target.value)}
            className="w-full text-sm border border-gray-200 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-primary-500 bg-white"
          >
            <option value="">Select day…</option>
            {DAYS.map(d => <option key={d.key} value={d.key}>{d.label}</option>)}
          </select>
        </div>
      </div>

      <div>
        {absentTeachers.length === 0 ? (
          <p className="text-xs text-gray-400 text-center py-8">No teachers are currently marked as absent</p>
        ) : !teacherId || !day ? (
          <p className="text-xs text-gray-400 text-center py-8">Select a teacher and day to plan the whole-day cover</p>
        ) : isLoading ? (
          <p className="text-xs text-gray-500 text-center py-8">Building plan…</p>
        ) : isError ? (
          <div className="text-center py-8 space-y-1">
            <p className="text-xs font-medium text-red-600">Could not load the plan</p>
            <p className="text-xs text-gray-500">
              {(error as { message?: string } | undefined)?.message ?? 'The server did not respond. Try again in a moment.'}
            </p>
          </div>
        ) : !plan || plan.total_lessons === 0 ? (
          <p className="text-xs text-gray-500 text-center py-8">
            No lessons found for {teacherName || 'this teacher'} on {dayLabel}
          </p>
        ) : (
          <PlanSummary
            plan={plan}
            rowsWithChoice={rowsWithChoice}
            loadCounts={loadCounts}
            onSelect={(lessonId, subId) => setSelections(s => ({ ...s, [lessonId]: subId }))}
            onAssignAll={onAssignAll}
            assignPending={assignDay.isPending || isFetching}
            assignCount={toAssign.length}
          />
        )}
      </div>
    </div>
  )
}

function PlanSummary({
  plan, rowsWithChoice, loadCounts, onSelect, onAssignAll, assignPending, assignCount,
}: {
  plan: DayPlan
  rowsWithChoice: Array<{ row: DayPlanRow; chosen: string }>
  loadCounts: Record<string, number>
  onSelect: (lessonId: string, subId: string) => void
  onAssignAll: () => void
  assignPending: boolean
  assignCount: number
}) {
  return (
    <>
      <div className="px-4 py-2 border-b border-gray-100 flex items-center gap-3 text-xs text-gray-600 bg-gray-50/50">
        <span className="font-mono">
          {plan.total_lessons} lesson{plan.total_lessons === 1 ? '' : 's'}
        </span>
        <span>·</span>
        <span className={plan.uncovered_count > 0 ? 'text-red-600 font-medium' : ''}>
          {plan.uncovered_count} uncovered
        </span>
        {Object.keys(loadCounts).length > 0 && (
          <>
            <span>·</span>
            <span className="text-gray-500 font-mono">
              {Object.entries(loadCounts).length} substitute{Object.entries(loadCounts).length === 1 ? '' : 's'} in this plan
            </span>
          </>
        )}
        <div className="ml-auto flex items-center gap-3">
          <Button
            size="sm"
            variant="primary"
            loading={assignPending}
            disabled={assignCount === 0}
            onClick={onAssignAll}
          >
            {assignCount === 0 ? 'Nothing to assign' : `Assign All (${assignCount})`}
          </Button>
        </div>
      </div>
      {rowsWithChoice.map(({ row, chosen }) => (
        <PlanRow
          key={row.lesson.id}
          row={row}
          selectedId={chosen}
          onSelect={subId => onSelect(row.lesson.id, subId)}
          loadCounts={loadCounts}
          isCommitted={!!row.existing_substitution_id}
        />
      ))}
    </>
  )
}

export default function SubstitutionsPage() {
  const { data: allPending = [] } = useSubstitutions('PENDING')
  const { data: resolvedSubs = [] } = useSubstitutions('ACCEPTED')
  const [showResolved, setShowResolved] = useState(false)

  const lessonSubs = (allPending as Record<string, unknown>[]).filter(s => s.sub_type === 'lesson')
  const dutySubs   = (allPending as Record<string, unknown>[]).filter(s => s.sub_type === 'duty')

  return (
    <div>
      <PageHeader title="Substitutions" description="Manage substitution requests and assignments" />

      <WholeDayPlanPanel />

      <section className="mb-8">
        <h2 className="text-sm font-syne font-semibold text-gray-700 mb-4">
          Open Requests{' '}
          <span className="text-xs font-mono text-gray-500 ml-2">{allPending.length}</span>
        </h2>
        {allPending.length === 0 ? (
          <div className="bg-white border border-gray-200 rounded-lg py-12 text-center text-xs text-gray-500">
            No open substitution requests
          </div>
        ) : (
          <div className="space-y-4">
            {lessonSubs.map(sub => (
              <LessonSubCard key={sub.id as string} sub={sub} />
            ))}
            {dutySubs.map(sub => (
              <DutySubCard key={sub.id as string} sub={sub} />
            ))}
          </div>
        )}
      </section>

      <section>
        <button
          onClick={() => setShowResolved(v => !v)}
          className="flex items-center gap-2 text-sm font-syne font-semibold text-gray-500 hover:text-gray-700 mb-4 transition-colors"
        >
          Resolved Requests{' '}
          <span className="text-xs font-mono ml-1">{resolvedSubs.length}</span>
          {showResolved ? <ChevronUp size={14} /> : <ChevronDown size={14} />}
        </button>
        {showResolved && (
          <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-hidden">
            <table className="w-full text-sm">
              <thead>
                <tr className="bg-gray-50 border-b border-gray-200">
                  {['Type', 'Cover For', 'Absent Teacher', 'Substitute', 'Status'].map(h => (
                    <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-500 uppercase">{h}</th>
                  ))}
                </tr>
              </thead>
              <tbody className="divide-y divide-gray-100">
                {(resolvedSubs as Record<string, unknown>[]).map(s => (
                  <tr key={s.id as string}>
                    <td className="px-4 py-3">
                      <Badge variant={s.sub_type === 'lesson' ? 'purple' : 'blue'} size="sm">
                        {s.sub_type === 'lesson' ? 'Class Cover' : 'Duty'}
                      </Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-700">
                      {s.sub_type === 'lesson'
                        ? `${(s.lesson as { subject?: string })?.subject ?? '—'} · ${(s.lesson as { class?: string })?.class ?? ''}`
                        : (s.duty as { name?: string })?.name ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {(s.absent_teacher as { name?: string })?.name ?? '—'}
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">
                      {(s.substitute as { name?: string })?.name ?? '—'}
                    </td>
                    <td className="px-4 py-3">
                      <Badge variant="green" size="sm">Resolved</Badge>
                    </td>
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
