import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Teacher } from '@/lib/types'

const KEYS = { all: ['teachers'] as const, one: (id: string) => ['teachers', id] as const }

function normaliseTeacher(t: Record<string, unknown>): Teacher {
  return {
    id: t.id as string, name: t.name as string, initials: t.initials as string,
    department: t.department as string, email: t.email as string,
    phone: t.phone as string | undefined, status: t.status as Teacher['status'],
    maxDuties: (t.max_duties ?? t.maxDuties) as number,
    qualifications: (t.qualifications as string[]) ?? [],
    subjects: (t.subjects as string[]) ?? [],
    schoolLevel: ((t.school_level ?? t.schoolLevel) as Teacher['schoolLevel']) ?? 'ALL',
    dutyCount: (t.duty_count ?? t.dutyCount ?? 0) as number,
    workloadPct: (t.workload_pct ?? t.workloadPct ?? 0) as number,
    createdAt: t.created_at as string, updatedAt: t.updated_at as string | undefined,
  }
}

export function useTeachers() {
  return useQuery({
    queryKey: KEYS.all,
    queryFn: async () => {
      const { data } = await api.get('/api/teachers/')
      return (data.teachers as Record<string, unknown>[]).map(normaliseTeacher)
    },
  })
}

export function useTeacher(id: string) {
  return useQuery({
    queryKey: KEYS.one(id),
    queryFn: async () => {
      const { data } = await api.get(`/api/teachers/${id}`)
      return normaliseTeacher(data as Record<string, unknown>)
    },
    enabled: !!id,
  })
}

export function useCreateTeacher() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/api/teachers/', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: KEYS.all }); toast.success('Teacher created') },
    onError: () => toast.error('Failed to create teacher'),
  })
}

export function useUpdateTeacher() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) => api.put(`/api/teachers/${id}`, body),
    onSuccess: (_, { id }) => {
      qc.invalidateQueries({ queryKey: KEYS.all })
      qc.invalidateQueries({ queryKey: KEYS.one(id) })
      toast.success('Teacher updated')
    },
    onError: () => toast.error('Failed to update teacher'),
  })
}

export function useMarkAbsent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/api/teachers/${id}/absent`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: KEYS.all }); toast.success('Teacher marked absent') },
    onError: () => toast.error('Failed to mark absent'),
  })
}
