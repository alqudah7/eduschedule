import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Duty } from '@/lib/types'

const KEYS = { all: ['duties'] as const, filtered: (f: Record<string,string>) => ['duties', f] as const }

function normaliseDuty(d: Record<string, unknown>): Duty {
  return {
    id: d.id as string, name: d.name as string, type: d.type as Duty['type'],
    day: d.day as Duty['day'], startTime: (d.start_time ?? d.startTime) as string,
    endTime: (d.end_time ?? d.endTime) as string, location: d.location as string,
    teacherId: (d.teacher_id ?? d.teacherId) as string | undefined,
    teacher: d.teacher as Duty['teacher'], status: d.status as Duty['status'],
    dutyCategory: ((d.duty_category ?? d.dutyCategory) as Duty['dutyCategory']) ?? 'SUPERVISION',
    notes: d.notes as string | undefined, createdAt: d.created_at as string,
  }
}

export function useDuties(filters?: Record<string, string>) {
  return useQuery({
    queryKey: filters ? KEYS.filtered(filters) : KEYS.all,
    queryFn: async () => {
      const params = new URLSearchParams(filters)
      const { data } = await api.get(`/api/duties/?${params}`)
      return (data.duties as Record<string, unknown>[]).map(normaliseDuty)
    },
  })
}

export function useCreateDuty() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Record<string, unknown>) => api.post('/api/duties/', body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: KEYS.all }); toast.success('Duty created') },
    onError: (err: { response?: { data?: { detail?: string } } }) =>
      toast.error(err.response?.data?.detail || 'Failed to create duty'),
  })
}

export function useUpdateDuty() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ id, ...body }: { id: string } & Record<string, unknown>) => api.put(`/api/duties/${id}`, body),
    onSuccess: () => { qc.invalidateQueries({ queryKey: KEYS.all }); toast.success('Duty updated') },
    onError: () => toast.error('Failed to update duty'),
  })
}

export function useDeleteDuty() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.delete(`/api/duties/${id}`),
    onSuccess: () => { qc.invalidateQueries({ queryKey: KEYS.all }); toast.success('Duty deleted') },
    onError: () => toast.error('Failed to delete duty'),
  })
}
