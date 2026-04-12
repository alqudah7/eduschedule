import { useQuery } from '@tanstack/react-query'
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
