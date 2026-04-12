'use client'
import { useState } from 'react'
import { useRouter } from 'next/navigation'
import { useForm } from 'react-hook-form'
import { zodResolver } from '@hookform/resolvers/zod'
import { z } from 'zod'
import { UserPlus, Search } from 'lucide-react'
import { PageHeader } from '@/components/layout/PageHeader'
import { Avatar, Badge, Button, WorkloadBar, Drawer, Input, Select, EmptyState } from '@/components/ui'
import { useTeachers, useCreateTeacher } from '@/lib/hooks/useTeachers'
import { STATUS_BADGE, QUALIFICATIONS } from '@/lib/constants'
import type { Teacher } from '@/lib/types'

type BadgeVariant = 'teal' | 'green' | 'amber' | 'red' | 'blue' | 'gray' | 'purple' | 'orange'

const schema = z.object({
  name: z.string().min(2),
  department: z.string().min(1),
  email: z.string().email(),
  phone: z.string().optional(),
  subjects: z.string(),
  max_duties: z.number().min(1).max(30),
})
type FormData = z.infer<typeof schema>

function AddTeacherForm({ onClose }: { onClose: () => void }) {
  const create = useCreateTeacher()
  const { register, handleSubmit, formState: { errors } } = useForm<FormData>({
    resolver: zodResolver(schema),
    defaultValues: { max_duties: 16 },
  })

  async function onSubmit(data: FormData) {
    await create.mutateAsync({
      ...data,
      subjects: data.subjects.split(',').map(s => s.trim()).filter(Boolean),
      qualifications: ['general'],
    })
    onClose()
  }

  return (
    <form onSubmit={handleSubmit(onSubmit)} className="space-y-4">
      <Input label="Full Name *" error={errors.name?.message} {...register('name')} />
      <Select
        label="Department *"
        error={errors.department?.message}
        options={['Mathematics','Science','English','History','Computer Sci.','Physical Ed.'].map(v => ({ value: v, label: v }))}
        placeholder="Select department"
        {...register('department')}
      />
      <Input label="Email *" type="email" error={errors.email?.message} {...register('email')} />
      <Input label="Phone" type="tel" {...register('phone')} />
      <Input label="Subjects (comma-separated)" placeholder="Calculus, Algebra" error={errors.subjects?.message} {...register('subjects')} />
      <Input label="Max Duties" type="number" error={errors.max_duties?.message} {...register('max_duties', { valueAsNumber: true })} />
      <div className="flex gap-3 pt-4 border-t border-gray-100">
        <Button type="button" variant="secondary" size="md" onClick={onClose} className="flex-1">Cancel</Button>
        <Button type="submit" variant="primary" size="md" loading={create.isPending} className="flex-1">Add Teacher</Button>
      </div>
    </form>
  )
}

export default function TeachersPage() {
  const router = useRouter()
  const { data: teachers = [], isLoading } = useTeachers()
  const [search, setSearch] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [drawerOpen, setDrawerOpen] = useState(false)

  const filtered = teachers.filter(t => {
    const matchSearch = !search || t.name.toLowerCase().includes(search.toLowerCase()) || t.department.toLowerCase().includes(search.toLowerCase())
    const matchStatus = statusFilter === 'all' || t.status === statusFilter
    return matchSearch && matchStatus
  })

  const statusTabs = [
    { key: 'all', label: 'All' },
    { key: 'ACTIVE', label: 'Active' },
    { key: 'ABSENT', label: 'Absent' },
    { key: 'ON_LEAVE', label: 'On Leave' },
  ]

  return (
    <div>
      <PageHeader
        title="Teachers"
        description="Manage teacher profiles and duty assignments"
        actions={<Button variant="primary" size="md" icon={<UserPlus size={14} />} onClick={() => setDrawerOpen(true)}>Add Teacher</Button>}
      />

      <div className="bg-white rounded-lg border border-gray-200 shadow-sm">
        {/* Filters */}
        <div className="px-4 py-3 border-b border-gray-200 flex items-center gap-3 flex-wrap">
          <div className="relative flex-1 min-w-48 max-w-xs">
            <Search size={14} className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-400" />
            <input
              value={search} onChange={e => setSearch(e.target.value)}
              placeholder="Search teachers..."
              className="w-full pl-8 pr-3 py-1.5 text-sm border border-gray-200 rounded-md focus:outline-none focus:ring-2 focus:ring-primary-500"
            />
          </div>
          <div className="flex gap-1">
            {statusTabs.map(t => (
              <button
                key={t.key}
                onClick={() => setStatusFilter(t.key)}
                className={`px-3 py-1.5 text-xs rounded-md font-medium transition-colors ${statusFilter === t.key ? 'bg-primary-50 text-primary-700' : 'text-gray-500 hover:bg-gray-50'}`}
              >
                {t.label}
              </button>
            ))}
          </div>
        </div>

        {/* Table */}
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="bg-gray-50 border-b border-gray-200">
                {['Teacher', 'Department', 'Status', 'Subjects', 'Duty Load', 'Qualifications', ''].map(h => (
                  <th key={h} className="px-4 py-3 text-left text-xs font-mono text-gray-400 uppercase tracking-wide">{h}</th>
                ))}
              </tr>
            </thead>
            <tbody className="divide-y divide-gray-100">
              {isLoading ? (
                Array.from({ length: 5 }).map((_, i) => (
                  <tr key={i}>{Array.from({ length: 7 }).map((_, j) => <td key={j} className="px-4 py-3"><div className="h-4 bg-gray-200 rounded animate-pulse" /></td>)}</tr>
                ))
              ) : filtered.length === 0 ? (
                <tr><td colSpan={7}><EmptyState title="No teachers found" description="Try adjusting your search or filters" /></td></tr>
              ) : (
                filtered.map((teacher, i) => (
                  <tr key={teacher.id} onClick={() => router.push(`/teachers/${teacher.id}`)} className="hover:bg-gray-50 cursor-pointer">
                    <td className="px-4 py-3">
                      <div className="flex items-center gap-3">
                        <Avatar name={teacher.name} initials={teacher.initials} size="sm" index={i} />
                        <div>
                          <p className="font-medium text-gray-800">{teacher.name}</p>
                          <p className="text-xs text-gray-400">{teacher.email}</p>
                        </div>
                      </div>
                    </td>
                    <td className="px-4 py-3 text-gray-600 text-xs">{teacher.department}</td>
                    <td className="px-4 py-3">
                      <Badge variant={(STATUS_BADGE[teacher.status] ?? 'gray') as BadgeVariant} dot size="sm">{teacher.status.replace('_', ' ')}</Badge>
                    </td>
                    <td className="px-4 py-3 text-xs text-gray-500">{teacher.subjects.slice(0, 2).join(', ')}</td>
                    <td className="px-4 py-3 w-40"><WorkloadBar value={teacher.workloadPct} size="sm" /></td>
                    <td className="px-4 py-3">
                      <div className="flex flex-wrap gap-1">
                        {teacher.qualifications.slice(0, 2).map(q => (
                          <Badge key={q} variant="gray" size="sm">{q}</Badge>
                        ))}
                      </div>
                    </td>
                    <td className="px-4 py-3">
                      <button onClick={e => { e.stopPropagation(); router.push(`/teachers/${teacher.id}`) }} className="text-xs text-primary-600 hover:underline">View →</button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      <Drawer isOpen={drawerOpen} onClose={() => setDrawerOpen(false)} title="Add New Teacher">
        <AddTeacherForm onClose={() => setDrawerOpen(false)} />
      </Drawer>
    </div>
  )
}
