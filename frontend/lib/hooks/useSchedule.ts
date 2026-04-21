import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'

export function useTeacherSchedule(teacherId: string) {
  return useQuery({
    queryKey: ['schedule', 'teacher', teacherId],
    queryFn: async () => {
      const { data } = await api.get(`/api/schedule/teacher/${teacherId}/week`)
      return data as { teacher_id: string; grid: Record<string, Record<string, { type: string; lesson?: Record<string,unknown>; duty?: Record<string,unknown> }>> }
    },
    enabled: !!teacherId,
  })
}

export function useWeekSchedule() {
  return useQuery({
    queryKey: ['schedule', 'week'],
    queryFn: async () => {
      const { data } = await api.get('/api/schedule/week')
      return data
    },
  })
}

export function useImportSchedule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File) => {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post('/api/schedule/import', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data as { imported: number; errors: string[] }
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['schedule'] })
      if (result.errors.length === 0) {
        toast.success(`Imported ${result.imported} lessons successfully`)
      } else {
        toast.success(`Imported ${result.imported} lessons · ${result.errors.length} error(s)`)
      }
    },
    onError: () => toast.error('Import failed — check your CSV format'),
  })
}
