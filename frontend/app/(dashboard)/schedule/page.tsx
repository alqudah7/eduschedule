'use client'
import { useState } from 'react'
import { AlertTriangle } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar } from '@/components/ui/Avatar'
import { useTeachers } from '@/lib/hooks/useTeachers'
import { useTeacherSchedule } from '@/lib/hooks/useSchedule'
import { DAYS, TIME_SLOTS } from '@/lib/constants'
import clsx from 'clsx'

function ScheduleCell({ cell }: { cell: { type: string; lesson?: Record<string,unknown>; duty?: Record<string,unknown> } | undefined }) {
  if (!cell || cell.type === 'free') return <div className="h-full min-h-[52px] bg-white" />
  const isLesson = cell.type === 'lesson'
  const isConflict = cell.type === 'conflict'
  const item = isLesson ? cell.lesson : cell.duty
  return (
    <div className={clsx(
      'p-1.5 rounded-sm border-l-2 min-h-[52px] h-full',
      isConflict ? 'bg-red-50 border-red-500 animate-pulse' :
      isLesson   ? 'bg-primary-50 border-primary-400' :
                   'bg-amber-50 border-amber-400',
    )}>
      <p className={clsx('text-xs font-medium leading-tight truncate',
        isConflict ? 'text-red-700' : isLesson ? 'text-primary-700' : 'text-amber-700',
      )}>
        {isLesson ? (item?.subject as string) : (item?.name as string)}
      </p>
      <p className="text-xs text-gray-400 truncate leading-tight">
        {isLesson ? `${item?.class as string} · ${item?.room as string}` : item?.location as string}
      </p>
    </div>
  )
}

export default function SchedulePage() {
  const { data: teachers = [] } = useTeachers()
  const [selectedId, setSelectedId] = useState<string>('')
  const activeTeacherId = selectedId || teachers[0]?.id || ''
  const { data: schedule } = useTeacherSchedule(activeTeacherId)
  const grid = schedule?.grid ?? {}

  const hasConflicts = Object.values(grid).some(day =>
    Object.values(day).some(cell => cell.type === 'conflict')
  )

  return (
    <div>
      <PageHeader title="Schedule" description="Weekly schedule view — lessons and duties" />

      {/* Teacher selector */}
      <div className="flex gap-2 overflow-x-auto pb-3 mb-4">
        {teachers.map((t, i) => (
          <button
            key={t.id}
            onClick={() => setSelectedId(t.id)}
            className={clsx(
              'flex items-center gap-2 px-3 py-1.5 rounded-full border text-xs font-medium shrink-0 transition-all',
              (activeTeacherId === t.id)
                ? 'bg-primary-500 text-white border-primary-500'
                : 'bg-white text-gray-700 border-gray-200 hover:border-primary-300',
            )}
          >
            <Avatar name={t.name} initials={t.initials} size="xs" index={i} />
            <span>{t.name}</span>
          </button>
        ))}
      </div>

      {/* Conflict banner */}
      {hasConflicts && (
        <div className="flex items-center gap-2 bg-red-50 border border-red-200 rounded-lg px-4 py-2.5 mb-4 text-red-700 text-xs">
          <AlertTriangle size={14} /> Scheduling conflicts detected for this teacher.
        </div>
      )}

      {/* Week grid */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm overflow-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className="bg-gray-50 border-b border-gray-200">
              <th className="w-16 px-3 py-3 text-right font-mono text-gray-400">Time</th>
              {DAYS.map(d => (
                <th key={d.key} className="px-2 py-3 font-syne font-semibold text-gray-700 text-center">{d.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TIME_SLOTS.map(slot => (
              <tr key={slot} className="border-b border-gray-100">
                <td className="px-3 py-1 text-right font-mono text-gray-400 text-xs w-16 align-top">{slot}</td>
                {DAYS.map(d => (
                  <td key={d.key} className="px-1 py-1 align-top">
                    <ScheduleCell cell={grid[d.key]?.[slot] as { type: string; lesson?: Record<string,unknown>; duty?: Record<string,unknown> }} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Legend */}
      <div className="flex items-center gap-6 mt-3 text-xs text-gray-500">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-primary-100 border-l-2 border-primary-400 inline-block" /> Lesson</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-amber-50 border-l-2 border-amber-400 inline-block" /> Duty</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-red-50 border-l-2 border-red-500 inline-block" /> Conflict</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-white border border-gray-200 inline-block" /> Free</span>
      </div>
    </div>
  )
}
