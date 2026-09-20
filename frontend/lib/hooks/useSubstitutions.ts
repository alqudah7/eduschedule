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

// ─── Whole-day suggest + atomic assign-day ──────────────────────────────────

export type DayPlanSuggestion = {
  teacher: {
    id: string
    name: string
    initials: string
    department: string
    school_level: string
    subjects: string[]
  }
  tier: number
  tier_label: string
  effective_tier: number
  subject_match: boolean
  level_match: boolean
  current_load: number
  continuity_bonus: boolean
}

export type DayPlanRow = {
  period_index: number
  lesson: {
    id: string
    subject: string
    class: string
    room: string
    day: string
    start_time: string
    end_time: string
    school_level: string
  }
  suggestions: DayPlanSuggestion[]
  uncovered: boolean
  existing_substitution_id?: string
  existing_status?: string
  existing_substitute_id?: string
}

export type DayPlan = {
  teacher_id: string
  teacher_name: string
  day: string
  total_lessons: number
  uncovered_count: number
  plan: DayPlanRow[]
}

export function useWholeDayPlan(teacherId: string, day: string) {
  return useQuery<DayPlan>({
    queryKey: ['whole-day-plan', teacherId, day],
    queryFn: async () => {
      const { data } = await api.get<DayPlan>(
        `/api/substitutions/suggest?teacher_id=${teacherId}&day=${day}`,
      )
      return data
    },
    enabled: !!teacherId && !!day,
  })
}

export function useAssignDay() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: {
      absent_teacher_id: string
      day: string
      assignments: Array<{ lesson_id: string; substitute_id: string }>
    }) => api.post('/api/substitutions/assign-day', body),
    onSuccess: (res, vars) => {
      qc.invalidateQueries({ queryKey: KEYS.all })
      qc.invalidateQueries({ queryKey: ['whole-day-plan', vars.absent_teacher_id, vars.day] })
      qc.invalidateQueries({ queryKey: ['absent-lessons'] })
      const count = (res.data as { total?: number })?.total ?? vars.assignments.length
      toast.success(`Assigned ${count} lesson${count === 1 ? '' : 's'}`)
    },
    onError: (e: unknown) => {
      const detail = (e as { response?: { data?: { detail?: unknown } } })?.response?.data?.detail
      const msg = typeof detail === 'string'
        ? detail
        : (detail as { reason?: string })?.reason ?? 'Failed to assign day'
      toast.error(msg)
    },
  })
}
