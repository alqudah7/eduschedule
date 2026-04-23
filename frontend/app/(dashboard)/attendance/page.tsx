'use client'
import { useState, useCallback } from 'react'
import { CheckCircle2, Clock, XCircle, Users, CalendarDays } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Button } from '@/components/ui'
import { useAttendanceByDate, useAttendanceSummary, useMarkAttendance } from '@/lib/hooks/useAttendance'
import type { AttendanceStatus, TeacherAttendanceRow } from '@/lib/types'

function todayISO() {
  return new Date().toISOString().split('T')[0]
}

type StatusButtonProps = {
  value: AttendanceStatus
  current: AttendanceStatus | null
  onClick: () => void
  label: string
}

function StatusButton({ value, current, onClick, label }: StatusButtonProps) {
  const active = current === value
  const styles: Record<AttendanceStatus, string> = {
    present: active
      ? 'bg-emerald-500 text-white border-emerald-500'
      : 'bg-white text-emerald-700 border-emerald-200 hover:bg-emerald-50',
    late: active
      ? 'bg-amber-400 text-white border-amber-400'
      : 'bg-white text-amber-700 border-amber-200 hover:bg-amber-50',
    absent: active
      ? 'bg-red-500 text-white border-red-500'
      : 'bg-white text-red-600 border-red-200 hover:bg-red-50',
  }
  const icons: Record<AttendanceStatus, React.ReactNode> = {
    present: <CheckCircle2 size={12} />,
    late:    <Clock size={12} />,
    absent:  <XCircle size={12} />,
  }
  return (
    <button
      onClick={onClick}
      className={`inline-flex items-center gap-1 px-2.5 py-1 text-xs font-medium rounded border transition-all duration-100 ${styles[value]}`}
    >
      {icons[value]}
      {label}
    </button>
  )
}

function SummaryBar({ present, late, absent, unmarked }: { present: number; late: number; absent: number; unmarked: number }) {
  const items = [
    { label: 'Present', value: present, color: 'text-emerald-600', dot: 'bg-emerald-500' },
    { label: 'Late',    value: late,    color: 'text-amber-600',   dot: 'bg-amber-400'  },
    { label: 'Absent',  value: absent,  color: 'text-red-600',     dot: 'bg-red-500'    },
    { label: 'Unmarked',value: unmarked,color: 'text-gray-500',    dot: 'bg-gray-300'   },
  ]
  return (
    <div className="flex items-center gap-6 text-sm">
      {items.map(({ label, value, color, dot }) => (
        <span key={label} className={`flex items-center gap-1.5 font-medium ${color}`}>
          <span className={`w-2 h-2 rounded-full ${dot}`} />
          {value} {label}
        </span>
      ))}
    </div>
  )
}

function TeacherRow({ row, index, date, onMark }: {
  row: TeacherAttendanceRow
  index: number
  date: string
  onMark: (teacherId: string, status: AttendanceStatus) => void
}) {
  return (
    <div className="flex items-center gap-4 px-4 py-3 border-b border-gray-100 last:border-0 hover:bg-gray-50 transition-colors">
      <Avatar name={row.name} initials={row.initials} size="sm" index={index} />
      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{row.name}</p>
        <p className="text-xs text-gray-500 truncate">
          {row.department}
          {row.subjects.length > 0 && ` · ${row.subjects.slice(0, 2).join(', ')}`}
        </p>
      </div>
      <div className="flex items-center gap-2 shrink-0">
        <StatusButton value="present" current={row.status} label="Present" onClick={() => onMark(row.teacher_id, 'present')} />
        <StatusButton value="late"    current={row.status} label="Late"    onClick={() => onMark(row.teacher_id, 'late')}    />
        <StatusButton value="absent"  current={row.status} label="Absent"  onClick={() => onMark(row.teacher_id, 'absent')}  />
      </div>
      {!row.status && (
        <span className="w-2 h-2 rounded-full bg-gray-200 shrink-0" title="Unmarked" />
      )}
      {row.status && (
        <span className="w-2 h-2 rounded-full shrink-0"
          style={{ background: row.status === 'present' ? '#10b981' : row.status === 'late' ? '#f59e0b' : '#ef4444' }}
          title={row.status}
        />
      )}
    </div>
  )
}

export default function AttendancePage() {
  const [date, setDate] = useState(todayISO)

  const { data: rows = [], isLoading } = useAttendanceByDate(date)
  const { data: summary } = useAttendanceSummary(date)
  const markAttendance = useMarkAttendance(date)

  const handleMark = useCallback((teacherId: string, status: AttendanceStatus) => {
    markAttendance.mutate({ teacher_id: teacherId, date, status })
  }, [markAttendance, date])

  const handleMarkAllPresent = useCallback(() => {
    rows.forEach(row => {
      if (row.status !== 'present') {
        markAttendance.mutate({ teacher_id: row.teacher_id, date, status: 'present' })
      }
    })
  }, [rows, markAttendance, date])

  return (
    <div className="space-y-4">
      <PageHeader
        title="Attendance"
        description="Track daily teacher attendance"
        actions={
          <div className="flex items-center gap-3">
            <div className="flex items-center gap-2">
              <CalendarDays size={14} className="text-gray-500" />
              <input
                type="date"
                value={date}
                onChange={e => setDate(e.target.value)}
                className="text-sm border border-gray-200 rounded-md px-2.5 py-1.5 focus:outline-none focus:ring-2 focus:ring-primary-500"
              />
            </div>
            <Button
              variant="success"
              size="md"
              icon={<CheckCircle2 size={14} />}
              onClick={handleMarkAllPresent}
              disabled={isLoading || rows.length === 0}
            >
              Mark All Present
            </Button>
          </div>
        }
      />

      {/* Summary bar */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm px-4 py-3 flex items-center justify-between flex-wrap gap-3">
        <div className="flex items-center gap-2 text-sm text-gray-600">
          <Users size={14} />
          <span className="font-medium">{summary?.total ?? rows.length} teachers</span>
        </div>
        <SummaryBar
          present={summary?.present ?? 0}
          late={summary?.late ?? 0}
          absent={summary?.absent ?? 0}
          unmarked={summary?.unmarked ?? rows.length}
        />
      </div>

      {/* Teacher list */}
      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        <div className="px-4 py-3 border-b border-gray-200">
          <h2 className="text-sm font-syne font-semibold text-gray-900">
            {new Date(date + 'T00:00:00').toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' })}
          </h2>
        </div>

        {isLoading ? (
          <div className="divide-y divide-gray-100">
            {Array.from({ length: 5 }).map((_, i) => (
              <div key={i} className="flex items-center gap-4 px-4 py-3">
                <div className="w-8 h-8 rounded-full bg-gray-200 animate-pulse shrink-0" />
                <div className="flex-1 space-y-1.5">
                  <div className="h-3.5 bg-gray-200 rounded animate-pulse w-40" />
                  <div className="h-3 bg-gray-100 rounded animate-pulse w-24" />
                </div>
                <div className="flex gap-2">
                  {[0, 1, 2].map(j => <div key={j} className="h-7 w-16 bg-gray-100 rounded animate-pulse" />)}
                </div>
              </div>
            ))}
          </div>
        ) : rows.length === 0 ? (
          <div className="py-16 text-center text-sm text-gray-500">No active teachers found</div>
        ) : (
          <div>
            {rows.map((row, i) => (
              <TeacherRow
                key={row.teacher_id}
                row={row}
                index={i}
                date={date}
                onMark={handleMark}
              />
            ))}
          </div>
        )}
      </div>
    </div>
  )
}
