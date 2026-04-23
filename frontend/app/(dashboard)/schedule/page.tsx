'use client'
import { useState, useRef, useEffect } from 'react'
import {
  AlertTriangle, Upload, X, CheckCircle, FileText,
  ChevronDown, ChevronUp, Download, Users, Calendar,
} from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Button, Badge } from '@/components/ui'
import { useTeachers } from '@/lib/hooks/useTeachers'
import {
  useTeacherSchedule, useImportTeachers, useImportSchedule,
  type TeacherImportResult, type ScheduleImportResult, type ImportError,
} from '@/lib/hooks/useSchedule'
import { DAYS, TIME_SLOTS } from '@/lib/constants'
import clsx from 'clsx'

const LEVEL_COLORS: Record<string, string> = {
  ELEMENTARY: 'text-green-600',
  MIDDLE:     'text-blue-600',
  HIGH:       'text-purple-600',
  ALL:        'text-gray-500',
}

const TEACHER_CSV_SAMPLE = `full_name,email,subject,phone,school_level
Dr. Sarah Al-Rashid,sarah@school.com,Mathematics,+966501234567,HIGH
Mr. James Thornton,james@school.com,English,,MIDDLE
Ms. Fatima Hassan,fatima@school.com,Science,+966501234569,ELEMENTARY`

const SCHEDULE_CSV_SAMPLE = `teacher_email,subject,class,room,day,start_time,end_time,school_level
sarah@eduschedule.com,Mathematics,10A,R101,SUN,08:00,09:00,HIGH
fatima@eduschedule.com,Science,5B,Lab1,MON,09:00,10:00,ELEMENTARY
james@eduschedule.com,English,7C,R202,TUE,10:00,11:00,MIDDLE`

// ─── CSV preview ────────────────────────────────────────────────────────────

type CSVPreview = { headers: string[]; rows: string[][]; total: number }

async function parseCSVPreview(file: File, limit = 5): Promise<CSVPreview> {
  const text = await file.text()
  const lines = text.trim().split(/\r?\n/)
  if (lines.length < 1) return { headers: [], rows: [], total: 0 }
  const headers = lines[0].split(',').map(h => h.trim().replace(/^"|"$/g, ''))
  const dataLines = lines.slice(1).filter(l => l.trim())
  const rows = dataLines.slice(0, limit).map(line =>
    line.split(',').map(c => c.trim().replace(/^"|"$/g, ''))
  )
  return { headers, rows, total: dataLines.length }
}

// ─── Shared sub-components ───────────────────────────────────────────────────

function FileDropZone({ file, onFile, accept = '.csv' }: {
  file: File | null
  onFile: (f: File) => void
  accept?: string
}) {
  const ref = useRef<HTMLInputElement>(null)
  return (
    <div
      onDragOver={e => e.preventDefault()}
      onDrop={e => { e.preventDefault(); const f = e.dataTransfer.files?.[0]; if (f) onFile(f) }}
      onClick={() => ref.current?.click()}
      className={clsx(
        'border-2 border-dashed rounded-lg p-5 text-center cursor-pointer transition-colors',
        file ? 'border-primary-400 bg-primary-50' : 'border-gray-300 hover:border-primary-300 hover:bg-gray-50',
      )}
    >
      <input ref={ref} type="file" accept={accept} className="hidden" onChange={e => { const f = e.target.files?.[0]; if (f) onFile(f) }} />
      {file ? (
        <div className="flex flex-col items-center gap-1.5">
          <FileText size={24} className="text-primary-500" />
          <p className="text-sm font-medium text-primary-700">{file.name}</p>
          <p className="text-xs text-gray-500">{(file.size / 1024).toFixed(1)} KB · click to change</p>
        </div>
      ) : (
        <div className="flex flex-col items-center gap-1.5">
          <Upload size={24} className="text-gray-400" />
          <p className="text-sm text-gray-600">Drop your CSV or <span className="text-primary-600 font-medium">click to browse</span></p>
          <p className="text-xs text-gray-400">Only .csv files accepted</p>
        </div>
      )}
    </div>
  )
}

function CSVPreviewTable({ preview }: { preview: CSVPreview }) {
  if (!preview.headers.length) return null
  return (
    <div className="overflow-x-auto rounded-lg border border-gray-200">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-gray-50 border-b border-gray-200">
            {preview.headers.map(h => (
              <th key={h} className="px-2.5 py-2 text-left font-mono text-gray-500 whitespace-nowrap">{h}</th>
            ))}
          </tr>
        </thead>
        <tbody className="divide-y divide-gray-100">
          {preview.rows.map((row, i) => (
            <tr key={i} className="hover:bg-gray-50">
              {row.map((cell, j) => (
                <td key={j} className="px-2.5 py-1.5 text-gray-700 truncate max-w-[140px]">{cell || <span className="text-gray-300">—</span>}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {preview.total > preview.rows.length && (
        <p className="px-3 py-2 text-xs text-gray-400 border-t border-gray-100">
          Showing {preview.rows.length} of {preview.total} rows
        </p>
      )}
    </div>
  )
}

function ImportResultBox({
  lines,
}: {
  lines: Array<{ label: string; value: number | string; tone: 'green' | 'yellow' | 'red' | 'gray' }>
  errors?: ImportError[]
}) {
  const toneClasses = {
    green:  { bg: 'bg-emerald-50 border-emerald-200', text: 'text-emerald-700', dot: 'bg-emerald-500' },
    yellow: { bg: 'bg-amber-50 border-amber-200',     text: 'text-amber-700',   dot: 'bg-amber-400'   },
    red:    { bg: 'bg-red-50 border-red-200',         text: 'text-red-700',     dot: 'bg-red-500'     },
    gray:   { bg: 'bg-gray-50 border-gray-200',       text: 'text-gray-600',    dot: 'bg-gray-400'    },
  }
  const hasBad = lines.some(l => l.tone === 'red' || l.tone === 'yellow')
  const bg = hasBad ? toneClasses.yellow.bg : toneClasses.green.bg

  return (
    <div className={clsx('rounded-lg border p-3 space-y-1', bg)}>
      {lines.map(({ label, value, tone }) => {
        const c = toneClasses[tone]
        return (
          <div key={label} className="flex items-center gap-2 text-xs">
            <span className={clsx('w-1.5 h-1.5 rounded-full shrink-0', c.dot)} />
            <span className={clsx('font-semibold', c.text)}>{value}</span>
            <span className={clsx('', c.text)}>{label}</span>
          </div>
        )
      })}
    </div>
  )
}

function ErrorList({ errors }: { errors: ImportError[] }) {
  const [expanded, setExpanded] = useState(false)
  if (!errors.length) return null
  const shown = expanded ? errors : errors.slice(0, 5)
  return (
    <div className="rounded-lg border border-red-100 bg-red-50 p-3">
      <p className="text-xs font-mono font-semibold text-red-600 mb-1.5">
        {errors.length} row{errors.length !== 1 ? 's' : ''} with issues
      </p>
      <ul className="space-y-0.5 font-mono text-xs text-red-700">
        {shown.map((e, i) => (
          <li key={i}>Row {e.row}: {e.reason}</li>
        ))}
      </ul>
      {errors.length > 5 && (
        <button
          onClick={() => setExpanded(v => !v)}
          className="mt-1.5 text-xs text-red-600 hover:text-red-800 flex items-center gap-1"
        >
          {expanded ? <ChevronUp size={11} /> : <ChevronDown size={11} />}
          {expanded ? 'Show less' : `Show ${errors.length - 5} more`}
        </button>
      )}
    </div>
  )
}

function StepIndicator({ step }: { step: 1 | 2 }) {
  return (
    <div className="flex items-center gap-2 text-xs">
      <div className={clsx('flex items-center gap-1.5 font-medium', step === 1 ? 'text-primary-600' : 'text-gray-400')}>
        <span className={clsx('w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold', step === 1 ? 'bg-primary-500 text-white' : 'bg-gray-200 text-gray-500')}>
          {step > 1 ? '✓' : '1'}
        </span>
        <Users size={12} /> Teachers
      </div>
      <div className="w-8 h-px bg-gray-300" />
      <div className={clsx('flex items-center gap-1.5 font-medium', step === 2 ? 'text-primary-600' : 'text-gray-400')}>
        <span className={clsx('w-5 h-5 rounded-full flex items-center justify-center text-xs font-bold', step === 2 ? 'bg-primary-500 text-white' : 'bg-gray-200 text-gray-500')}>2</span>
        <Calendar size={12} /> Schedule
      </div>
    </div>
  )
}

// ─── Step 1: Teacher import ──────────────────────────────────────────────────

function TeacherImportStep({ onNext }: { onNext: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [preview, setPreview] = useState<CSVPreview | null>(null)
  const [showSample, setShowSample] = useState(false)
  const [result, setResult] = useState<TeacherImportResult | null>(null)
  const importTeachers = useImportTeachers()

  useEffect(() => {
    if (!file) { setPreview(null); return }
    parseCSVPreview(file, 5).then(setPreview)
  }, [file])

  function downloadTemplate() {
    const blob = new Blob([TEACHER_CSV_SAMPLE], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'teacher_template.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  async function handleImport() {
    if (!file) return
    const res = await importTeachers.mutateAsync(file)
    setResult(res)
  }

  const didImport = result !== null

  return (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-3">
        <p className="text-xs font-mono font-semibold text-gray-600 mb-1.5">REQUIRED COLUMNS</p>
        <div className="flex flex-wrap gap-1.5">
          {['full_name', 'email', 'subject'].map(col => (
            <span key={col} className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs font-mono text-gray-700">{col}</span>
          ))}
          {['phone', 'school_level'].map(col => (
            <span key={col} className="px-2 py-0.5 bg-white border border-dashed border-gray-300 rounded text-xs font-mono text-gray-400">{col} (optional)</span>
          ))}
        </div>
        <p className="text-xs text-gray-500 mt-1.5">
          <strong>school_level</strong>: ELEMENTARY, MIDDLE, HIGH, ALL &nbsp;·&nbsp;
          Existing emails are silently skipped
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowSample(v => !v)}
          className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-800 font-medium"
        >
          {showSample ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showSample ? 'Hide' : 'Show'} sample CSV
        </button>
        <button
          onClick={downloadTemplate}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
        >
          <Download size={11} /> Download Teacher Template
        </button>
      </div>

      {showSample && (
        <pre className="bg-gray-900 text-green-400 rounded-lg p-3 text-xs font-mono overflow-x-auto leading-relaxed">
          {TEACHER_CSV_SAMPLE}
        </pre>
      )}

      {!didImport && (
        <FileDropZone file={file} onFile={f => { setFile(f); setResult(null) }} />
      )}

      {preview && !didImport && (
        <CSVPreviewTable preview={preview} />
      )}

      {result && (
        <div className="space-y-2">
          <ImportResultBox lines={[
            { label: 'teachers created', value: result.created, tone: 'green' },
            { label: 'already existed (skipped)', value: result.skipped, tone: 'gray' },
            ...(result.errors.length > 0 ? [{ label: 'rows with errors', value: result.errors.length, tone: 'red' as const }] : []),
          ]} />
          <ErrorList errors={result.errors} />
        </div>
      )}

      <div className="flex items-center justify-between pt-2 border-t border-gray-100">
        <button
          onClick={onNext}
          className="text-xs text-gray-400 hover:text-gray-600 transition-colors"
        >
          Skip this step →
        </button>
        {!didImport ? (
          <Button
            variant="primary" size="md"
            icon={<Upload size={13} />}
            disabled={!file}
            loading={importTeachers.isPending}
            onClick={handleImport}
          >
            Import Teachers
          </Button>
        ) : (
          <Button variant="success" size="md" onClick={onNext}>
            Next: Import Schedule →
          </Button>
        )}
      </div>
    </div>
  )
}

// ─── Step 2: Schedule import ─────────────────────────────────────────────────

function ScheduleImportStep({ onClose }: { onClose: () => void }) {
  const [file, setFile] = useState<File | null>(null)
  const [showSample, setShowSample] = useState(false)
  const [result, setResult] = useState<ScheduleImportResult | null>(null)
  const importSchedule = useImportSchedule()

  function downloadTemplate() {
    const blob = new Blob([SCHEDULE_CSV_SAMPLE], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url; a.download = 'schedule_template.csv'; a.click()
    URL.revokeObjectURL(url)
  }

  async function handleImport() {
    if (!file) return
    const res = await importSchedule.mutateAsync(file)
    setResult(res)
  }

  return (
    <div className="space-y-4">
      <div className="bg-gray-50 rounded-lg p-3">
        <p className="text-xs font-mono font-semibold text-gray-600 mb-1.5">REQUIRED COLUMNS</p>
        <div className="flex flex-wrap gap-1.5">
          {['teacher_email', 'subject', 'class', 'room', 'day', 'start_time', 'end_time'].map(col => (
            <span key={col} className="px-2 py-0.5 bg-white border border-gray-200 rounded text-xs font-mono text-gray-700">{col}</span>
          ))}
          <span className="px-2 py-0.5 bg-white border border-dashed border-gray-300 rounded text-xs font-mono text-gray-400">school_level (optional)</span>
        </div>
        <p className="text-xs text-gray-500 mt-1.5">
          <strong>day</strong>: SUN, MON, TUE, WED, THU &nbsp;·&nbsp;
          Rows with unknown teacher emails are skipped
        </p>
      </div>

      <div className="flex items-center gap-3">
        <button
          onClick={() => setShowSample(v => !v)}
          className="flex items-center gap-1 text-xs text-primary-600 hover:text-primary-800 font-medium"
        >
          {showSample ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
          {showSample ? 'Hide' : 'Show'} sample CSV
        </button>
        <button
          onClick={downloadTemplate}
          className="flex items-center gap-1 text-xs text-gray-500 hover:text-gray-700"
        >
          <Download size={11} /> Download Schedule Template
        </button>
      </div>

      {showSample && (
        <pre className="bg-gray-900 text-green-400 rounded-lg p-3 text-xs font-mono overflow-x-auto leading-relaxed">
          {SCHEDULE_CSV_SAMPLE}
        </pre>
      )}

      <FileDropZone file={file} onFile={f => { setFile(f); setResult(null) }} />

      {result && (
        <div className="space-y-2">
          <ImportResultBox lines={[
            { label: 'lessons imported', value: result.imported, tone: 'green' },
            { label: 'rows skipped (teacher not found)', value: result.skipped, tone: result.skipped > 0 ? 'yellow' : 'gray' },
            ...(result.errors.length - result.skipped > 0
              ? [{ label: 'other errors', value: result.errors.length - result.skipped, tone: 'red' as const }]
              : []),
          ]} />
          <ErrorList errors={result.errors} />
        </div>
      )}

      <div className="flex gap-3 pt-2 border-t border-gray-100">
        <Button variant="secondary" size="md" className="flex-1" onClick={onClose}>
          {result ? 'Done' : 'Close'}
        </Button>
        <Button
          variant="primary" size="md" className="flex-1"
          icon={<Upload size={13} />}
          disabled={!file}
          loading={importSchedule.isPending}
          onClick={handleImport}
        >
          Import Schedule
        </Button>
      </div>
    </div>
  )
}

// ─── Modal shell ─────────────────────────────────────────────────────────────

function ImportModal({ onClose }: { onClose: () => void }) {
  const [step, setStep] = useState<1 | 2>(1)

  return (
    <div className="fixed inset-0 bg-black/40 z-50 flex items-center justify-center p-4">
      <div className="bg-white rounded-xl shadow-xl w-full max-w-lg max-h-[90vh] flex flex-col">
        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-gray-200 shrink-0">
          <div>
            <h2 className="text-base font-syne font-semibold text-gray-900">
              {step === 1 ? 'Import Teachers' : 'Import Schedule'}
            </h2>
            <p className="text-xs text-gray-500 mt-0.5">
              {step === 1
                ? 'Step 1 of 2 — bulk-create teachers from CSV'
                : 'Step 2 of 2 — assign lessons to teachers'}
            </p>
          </div>
          <div className="flex items-center gap-4">
            <StepIndicator step={step} />
            <button onClick={onClose} className="text-gray-400 hover:text-gray-600 transition-colors">
              <X size={18} />
            </button>
          </div>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto p-5">
          {step === 1
            ? <TeacherImportStep onNext={() => setStep(2)} />
            : <ScheduleImportStep onClose={onClose} />
          }
        </div>
      </div>
    </div>
  )
}

// ─── Schedule cell ────────────────────────────────────────────────────────────

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

// ─── Page ────────────────────────────────────────────────────────────────────

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
