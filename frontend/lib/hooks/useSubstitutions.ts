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
      toast.success('Substitute assigned')
    },
    onError: () => toast.error('Failed to assign substitute'),
  })
}
