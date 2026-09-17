import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'

const KEYS = { all: ['substitutions'] as const }

export function useSubstitutions(status?: string) {
  return useQuery({
    queryKey: [...KEYS.all, { status }],
    queryFn: async () => {
      const url = status ? `/api/substitutions/?status=${status}` : '/api/substitutions/'
      const { data } = await api.get(url)
      return data.substitutions
    },
  })
}

export function useSubstituteSuggestions(subId: string) {
  return useQuery({
    queryKey: ['substitutions', subId, 'suggestions'],
    queryFn: async () => {
      const { data } = await api.get(`/api/substitutions/${subId}/suggestions`)
      return (data.suggestions as Array<Record<string, unknown>>).map(s => ({
        teacher: s.teacher as Record<string, unknown>,
        load_pct: s.load_pct as number,
        score: s.score as number,
        tier: s.tier as number,
        tier_label: s.tier_label as string,
        subject_match: s.subject_match as boolean,
        level_match: s.level_match as boolean,
      }))
    },
    enabled: !!subId,
  })
}

export function useAssignSubstitute() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ subId, substituteId }: { subId: string; substituteId: string }) =>
      api.post(`/api/substitutions/${subId}/assign?substitute_id=${substituteId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all })
      qc.invalidateQueries({ queryKey: ['absent-lessons'] })
      toast.success('Substitute assigned')
    },
    onError: () => toast.error('Failed to assign substitute'),
  })
}

export function useAbsentTeacherLessons(teacherId: string, day: string) {
  return useQuery({
    queryKey: ['absent-lessons', teacherId, day],
    queryFn: async () => {
      const { data } = await api.get(`/api/substitutions/absent-lessons?teacher_id=${teacherId}&day=${day}`)
      return data.lessons as Array<Record<string, unknown>>
    },
    enabled: !!teacherId && !!day,
  })
}

export function useCreateLessonSubstitution() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ lessonId, absentTeacherId }: { lessonId: string; absentTeacherId: string }) =>
      api.post(`/api/substitutions/lesson?lesson_id=${lessonId}&absent_teacher_id=${absentTeacherId}`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all })
      qc.invalidateQueries({ queryKey: ['absent-lessons'] })
      toast.success('Cover request created')
    },
    onError: (e: unknown) => {
      const msg = (e as { response?: { data?: { detail?: string } } })?.response?.data?.detail
      toast.error(msg ?? 'Failed to create cover request')
    },
  })
}

export function useLessonSubSuggestions(subId: string) {
  return useQuery({
    queryKey: ['substitutions', subId, 'lesson-suggestions'],
    queryFn: async () => {
      const { data } = await api.get(`/api/substitutions/${subId}/lesson-suggestions`)
      return (data.suggestions as Array<Record<string, unknown>>).map(s => ({
        teacher: s.teacher as Record<string, unknown>,
        load_pct: s.load_pct as number,
        score: s.score as number,
        tier: s.tier as number,
        tier_label: s.tier_label as string,
        subject_match: s.subject_match as boolean,
        level_match: s.level_match as boolean,
      }))
    },
    enabled: !!subId,
  })
}
