import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'

export type ImportError = { row: number; reason: string }

export type TeacherImportResult = {
  created: number
  skipped: number
  errors: ImportError[]
}

export type ScheduleImportResult = {
  imported: number
  skipped: number
  errors: ImportError[]
}

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

export function useImportTeachers() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File): Promise<TeacherImportResult> => {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post('/api/teachers/bulk-import', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data as TeacherImportResult
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['teachers'] })
      const msg = `${result.created} created · ${result.skipped} skipped`
      result.errors.length === 0
        ? toast.success(msg)
        : toast.success(`${msg} · ${result.errors.length} error(s)`)
    },
    onError: () => toast.error('Teacher import failed — check your CSV format'),
  })
}

export function useImportSchedule() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: async (file: File): Promise<ScheduleImportResult> => {
      const form = new FormData()
      form.append('file', file)
      const { data } = await api.post('/api/schedule/import', form, {
        headers: { 'Content-Type': 'multipart/form-data' },
      })
      return data as ScheduleImportResult
    },
    onSuccess: (result) => {
      qc.invalidateQueries({ queryKey: ['schedule'] })
      const msg = `${result.imported} lesson${result.imported !== 1 ? 's' : ''} imported`
      result.errors.length === 0
        ? toast.success(msg)
        : toast.success(`${msg} · ${result.errors.length} row(s) skipped`)
    },
    onError: () => toast.error('Import failed — check your CSV format'),
  })
}
