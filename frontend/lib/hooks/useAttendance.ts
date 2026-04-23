import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { TeacherAttendanceRow, AttendanceSummary, AttendanceStatus } from '@/lib/types'

const KEYS = {
  byDate: (date: string) => ['attendance', 'date', date] as const,
  summary: (date: string) => ['attendance', 'summary', date] as const,
  history: (teacherId: string) => ['attendance', 'teacher', teacherId] as const,
}

export function useAttendanceByDate(date: string) {
  return useQuery<TeacherAttendanceRow[]>({
    queryKey: KEYS.byDate(date),
    queryFn: async () => {
      const { data } = await api.get('/api/attendance/teachers', { params: { date } })
      return data as TeacherAttendanceRow[]
    },
    enabled: !!date,
  })
}

export function useAttendanceSummary(date: string) {
  return useQuery<AttendanceSummary>({
    queryKey: KEYS.summary(date),
    queryFn: async () => {
      const { data } = await api.get('/api/attendance/summary', { params: { date } })
      return data as AttendanceSummary
    },
    enabled: !!date,
  })
}

export function useTeacherAttendanceHistory(teacherId: string) {
  return useQuery({
    queryKey: KEYS.history(teacherId),
    queryFn: async () => {
      const { data } = await api.get(`/api/attendance/teachers/${teacherId}`)
      return data
    },
    enabled: !!teacherId,
  })
}

export function useMarkAttendance(date: string) {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: { teacher_id: string; date: string; status: AttendanceStatus; note?: string }) =>
      api.post('/api/attendance/teachers', body),
    onMutate: async (vars) => {
      await qc.cancelQueries({ queryKey: KEYS.byDate(date) })
      const prev = qc.getQueryData<TeacherAttendanceRow[]>(KEYS.byDate(date))

      qc.setQueryData<TeacherAttendanceRow[]>(KEYS.byDate(date), old =>
        (old ?? []).map(row =>
          row.teacher_id === vars.teacher_id
            ? { ...row, status: vars.status, note: vars.note ?? null }
            : row,
        ),
      )

      return { prev }
    },
    onError: (_err, _vars, ctx) => {
      if (ctx?.prev) qc.setQueryData(KEYS.byDate(date), ctx.prev)
      toast.error('Failed to save attendance')
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.summary(date) })
    },
  })
}
