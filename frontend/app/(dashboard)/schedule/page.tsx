'use client'
import { useState, useRef } from 'react'
import { AlertTriangle, Upload, X, CheckCircle, FileText, ChevronDown, ChevronUp } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Button, Badge } from '@/components/ui'
import { useTeachers } from '@/lib/hooks/useTeachers'
import { useTeacherSchedule, useImportSchedule } from '@/lib/hooks/useSchedule'
import { DAYS, TIME_SLOTS } from '@/lib/constants'
import clsx from 'clsx'

const LEVEL_COLORS: Record<string, string> = {
  ELEMENTARY: 'text-green-600',
  MIDDLE:     'text-blue-600',
  HIGH:       'text-purple-600',
  ALL:        'text-gray-500',
}

const CSV_SAMPLE = `teacher_email,subject,class,room,day,start_time,end_time,school_level
sarah@eduschedule.com,Mathematics,10A,R101,MON,08:00,09:00,HIGH
fatima@eduschedule.com,Science,5B,Lab1,TUE,09:00,10:00,ELEMENTARY
james@eduschedule.com,English,7C,R202,WED,10:00,11:00,MIDDLE`

function ScheduleCell({ cell }: { cell: { type: string; lesson?: Record<string,unknown>; duty?: Record<string,unknown> } | undefined }) {
  if (!cell || cell.type === 'free') return <div className="h-full min-h-[52px] bg-white" />
  const isLesson = cell.type === 'lesson'
  const isConflict = cell.type === 'conflict'
  const item = isLesson ? cell.lesson : cell.duty
  const level = isLesson ? (item?.school_level as string) : null
  const dutyCategory = !isLesson ? (item?.duty_category as string) : null
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
      <p className="text-xs text-gray-500 truncate leading-tight">
        {isLesson
          ? `${item?.class as string} · ${item?.room as string}`
          : item?.location as string}
      </p>
      {level && level !== 'ALL' && (
        <p className={clsx('text-xs font-mono leading-tight truncate', LEVEL_COLORS[level] ?? 'text-gray-400')}>
          {level.charAt(0) + level.slice(1).toLowerCase()}
        </p>
      )}
      {dutyCategory && (
        <p className="text-xs font-mono text-amber-500 leading-tight truncate">
          {dutyCategory.replace('_', ' ').toLowerCase()}
        </p>
      )}
    </div>
  )
}

function ImportModal({ onClose }: { onClose: () => void }) {
  const fileRef = useRef<HTMLInputElement>(null)
  const [file, setFile] = useState<File | null>(null)
  const [result, setResult] = useState<{ imported: number; errors: string[] } | null>(null)
  const [showSample, setShowSample] = useState(false)
  const importSchedule = useImportSchedule()

  function handleFileChange(e: React.ChangeEvent<HTMLInputElement>) {
    const f = e.target.files?.[0]
    if (f) { setFile(f); setResult(null) }
  }

  function handleDrop(e: React.DragEvent) {
    e.preventDefault()
    const f = e.dataTransfer.files?.[0]
    if (f && f.name.endsWith('.csv')) { setFile(f); setResult(null) }
  }

  async function handleImport() {
    if (!file) return
    const res = await importSchedule.mutateAsync(file)
    setResult(res)
  }

  function downloadSample() {
    const blob = new Blob([CSV_SAMPLE], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'schedule_template.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200">
          <div>
            <h2 className="text-base font-syne font-semibold text-gray-900">Import Teacher Schedules</h2>
            <p className="text-xs text-gray-500 mt-0.5">Upload a CSV file with all teacher lessons</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
            <X size={18} />
          </button>
        </div>

        <div className="p-5 space-y-4">
          {/* Drop zone */}
          <div
            onDragOver={e => e.preventDefault()}
            onDrop={handleDrop}
            onClick={() => fileRef.current?.click()}
            className={clsx(
              'border-2 border-dashed rounded-lg p-6 text-center cursor-pointer transition-colors',
              file ? 'border-primary-400 bg-primary-50' : 'border-gray-300 hover:border-primary-300 hover:bg-gray-50',
            )}
          >
            <input ref={fileRef} type="file" accept=".csv" className="hidden" onChange={handleFileChange} />
            {file ? (
              <div className="flex flex-col items-center gap-2">
                <FileText size={28} className="text-primary-500" />
                <p className="text-sm font-medium text-primary-700">{file.name}</p>
                <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB · Click to change</p>
              </div>
            ) : (
              <div className="flex flex-col items-center gap-2">
                <Upload size={28} className="text-gray-400" />
                <p className="text-sm text-gray-600">Drop your CSV here or <span className="text-primary-600 font-medium">click to browse</span></p>
                <p className="text-xs text-gray-400">Only .csv files accepted</p>
              </div>
            )}
          </div>

          {/* Required columns */}
          <div className="bg-gray-50 rounded-lg p-3">
            <p className="text-xs font-mono font-semibold text-gray-600 mb-2">REQUIRED COLUMNS</p>
            <div className="flex flex-wrap gap-1.5">
              {['teacher_email','subject','class','room','day','start_time','end_time'].map(col => (
                <span key={col} className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs font-mono text-gray-700">{col}</span>
              ))}
              <span className="px-2 py-0.5 bg-white border border-dashed border-gray-300 rounded text-xs font-mono text-gray-400">school_level (optional)</span>
            </div>
            <p className="text-xs text-gray-500 mt-2">
              <strong>day</strong> values: MON, TUE, WED, THU, FRI &nbsp;·&nbsp;
              <strong>school_level</strong>: ELEMENTARY, MIDDLE, HIGH, ALL
            </p>
          </div>

          {/* Sample toggle */}
          <button
            onClick={() => setShowSample(v => !v)}
            className="flex items-center gap-1.5 text-xs text-primary-600 hover:text-primary-800 font-medium transition-colors"
          >
            {showSample ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            {showSample ? 'Hide' : 'Show'} sample CSV
          </button>

          {showSample && (
            <pre className="bg-gray-900 text-green-400 rounded-lg p-3 text-xs font-mono overflow-x-auto leading-relaxed">
              {CSV_SAMPLE}
            </pre>
          )}

          {/* Download template button */}
          <button
            onClick={downloadSample}
            className="text-xs text-gray-500 hover:text-gray-700 underline underline-offset-2 transition-colors"
          >
            Download blank template
          </button>

          {/* Result */}
          {result && (
            <div className={clsx('rounded-lg p-3 text-xs', result.errors.length === 0 ? 'bg-green-50 border border-green-200' : 'bg-amber-50 border border-amber-200')}>
              <div className="flex items-center gap-1.5 font-semibold mb-1">
                <CheckCircle size={13} className={result.errors.length === 0 ? 'text-green-600' : 'text-amber-600'} />
                <span className={result.errors.length === 0 ? 'text-green-700' : 'text-amber-700'}>
                  {result.imported} lesson{result.imported !== 1 ? 's' : ''} imported
                </span>
              </div>
              {result.errors.length > 0 && (
                <ul className="mt-2 space-y-0.5 text-amber-700 font-mono">
                  {result.errors.map((e, i) => <li key={i}>· {e}</li>)}
                </ul>
              )}
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="flex gap-3 px-5 pb-5">
          <Button variant="secondary" size="md" className="flex-1" onClick={onClose}>Close</Button>
          <Button
            variant="primary" size="md" className="flex-1"
            icon={<Upload size={14} />}
            disabled={!file}
            loading={importSchedule.isPending}
            onClick={handleImport}
          >
            Import
          </Button>
        </div>
      </div>
    </div>
  )
}

export default function SchedulePage() {
  const { data: teachers = [] } = useTeachers()
  const [selectedId, setSelectedId] = useState<string>('')
  const [showImport, setShowImport] = useState(false)
  const activeTeacherId = selectedId || teachers[0]?.id || ''
  const { data: schedule } = useTeacherSchedule(activeTeacherId)
  const grid = schedule?.grid ?? {}

  const hasConflicts = Object.values(grid).some(day =>
    Object.values(day).some(cell => cell.type === 'conflict')
  )

  return (
    <div>
      <PageHeader
        title="Schedule"
        description="Weekly schedule view — lessons and duties"
        actions={
          <Button variant="primary" size="md" icon={<Upload size={14} />} onClick={() => setShowImport(true)}>
            Import Schedule
          </Button>
        }
      />

      {showImport && <ImportModal onClose={() => setShowImport(false)} />}

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
              <th className="w-16 px-3 py-3 text-right font-mono text-gray-500">Time</th>
              {DAYS.map(d => (
                <th key={d.key} className="px-2 py-3 font-syne font-semibold text-gray-700 text-center">{d.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {TIME_SLOTS.map(slot => (
              <tr key={slot} className="border-b border-gray-100">
                <td className="px-3 py-1 text-right font-mono text-gray-500 text-xs w-16 align-top">{slot}</td>
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
      <div className="flex flex-wrap items-center gap-x-6 gap-y-2 mt-3 text-xs text-gray-500">
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-primary-100 border-l-2 border-primary-400 inline-block" /> Lesson</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-amber-50 border-l-2 border-amber-400 inline-block" /> Duty</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-red-50 border-l-2 border-red-500 inline-block" /> Conflict</span>
        <span className="flex items-center gap-1.5"><span className="w-3 h-3 rounded-sm bg-white border border-gray-200 inline-block" /> Free</span>
        <span className="text-gray-300">|</span>
        <span className="text-green-600">■ Elementary</span>
        <span className="text-blue-600">■ Middle</span>
        <span className="text-purple-600">■ High</span>
      </div>
    </div>
  )
}
