'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { ArrowLeft, CheckCircle, AlertTriangle } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Button, Input, Select, Card } from '@/components/ui'
import { useCreateDuty } from '@/lib/hooks/useDuties'
import { useTeachers } from '@/lib/hooks/useTeachers'
import { useTeacherSchedule } from '@/lib/hooks/useSchedule'
import { DAYS, DUTY_TYPE_CONFIG } from '@/lib/constants'
import { timesOverlap } from '@/lib/utils'

const schema = z.object({
  name: z.string().min(1, 'Name required'),
  type: z.string().min(1, 'Type required'),
  day: z.string().min(1, 'Day required'),
  start_time: z.string().min(1, 'Start time required'),
  end_time: z.string().min(1, 'End time required'),
  location: z.string().min(1, 'Location required'),
  teacher_id: z.string().optional(),
  notes: z.string().optional(),
})
type FormData = z.infer<typeof schema>

export default function NewDutyPage() {
  const router = useRouter()
  const create = useCreateDuty()
  const { data: teachers = [] } = useTeachers()
  const { register, handleSubmit, watch, formState: { errors } } = useForm<FormData>({ resolver: zodResolver(schema) })

  const watchedTeacher = watch('teacher_id')
  const watchedDay = watch('day')
  const watchedStart = watch('start_time')
  const watchedEnd = watch('end_time')
  const watchedName = watch('name')

  const { data: schedule } = useTeacherSchedule(watchedTeacher || '')
  const conflictDetected = !!(watchedTeacher && watchedDay && watchedStart && watchedEnd && schedule?.grid?.[watchedDay])

  async function onSubmit(data: FormData) {
    await create.mutateAsync(data)
    router.push('/duties')
  }

  const teacherOptions = teachers.map(t => ({
    value: t.id,
    label: `${t.name} — ${t.department} (${t.workloadPct}% load)`,
  }))

  const previewData = { name: watchedName, type: watch('type'), day: watchedDay, start_time: watchedStart, end_time: watchedEnd, location: watch('location') }

  return (
    <div>
      <PageHeader
        title="New Duty"
        breadcrumb={[{ label: 'Duties', href: '/duties' }, { label: 'New' }]}
        actions={<Button variant="ghost" size="sm" icon={<ArrowLeft size={14} />} onClick={() => router.push('/duties')}>Back</Button>}
      />

      <div className="grid grid-cols-2 gap-6">
        {/* Form */}
        <Card>
          <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
            <Input label="Duty Name *" error={errors.name?.message} {...register('name')} />
            <Select
              label="Type *"
              error={errors.type?.message}
              options={Object.entries(DUTY_TYPE_CONFIG).map(([v, c]) => ({ value: v, label: c.label }))}
              placeholder="Select type"
              {...register('type')}
            />
            <div className="grid grid-cols-2 gap-3">
              <Select
                label="Day *"
                error={errors.day?.message}
                options={DAYS.map(d => ({ value: d.key, label: d.label }))}
                placeholder="Select day"
                {...register('day')}
              />
              <Input label="Location *" error={errors.location?.message} {...register('location')} />
            </div>
            <div className="grid grid-cols-2 gap-3">
              <Input label="Start Time *" type="time" error={errors.start_time?.message} {...register('start_time')} />
              <Input label="End Time *" type="time" error={errors.end_time?.message} {...register('end_time')} />
            </div>
            <Select
              label="Assign Teacher"
              options={teacherOptions}
              placeholder="Unassigned"
              {...register('teacher_id')}
            />
            {watchedTeacher && watchedStart && watchedEnd && (
              <div className={`flex items-center gap-2 text-xs px-3 py-2 rounded-md ${conflictDetected ? 'bg-red-50 text-red-600' : 'bg-emerald-50 text-emerald-600'}`}>
                {conflictDetected ? <AlertTriangle size={12} /> : <CheckCircle size={12} />}
                {conflictDetected ? 'Possible conflict detected — check schedule' : 'No conflicts detected'}
              </div>
            )}
            <Input label="Notes" {...register('notes')} />
            <div className="flex gap-3 pt-2">
              <Button type="button" variant="secondary" onClick={() => router.push('/duties')} className="flex-1">Cancel</Button>
              <Button type="submit" variant="primary" loading={create.isPending} className="flex-1">Create Duty</Button>
            </div>
          </form>
        </Card>

        {/* Live preview */}
        <div className="space-y-4">
          <Card>
            <h3 className="text-sm font-syne font-semibold text-gray-800 mb-3">Preview</h3>
            <div className="bg-amber-50 border-l-2 border-amber-400 rounded-sm p-3">
              <p className="text-sm font-medium text-amber-700">{previewData.name || 'Duty Name'}</p>
              <p className="text-xs text-amber-600 mt-1">{previewData.type || 'Type'} · {previewData.location || 'Location'}</p>
              <p className="text-xs text-amber-500 font-mono mt-0.5">{previewData.day || 'Day'} {previewData.start_time || '—'}–{previewData.end_time || '—'}</p>
            </div>
          </Card>
        </div>
      </div>
    </div>
  )
}
