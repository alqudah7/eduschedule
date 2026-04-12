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
      return data.suggestions as Array<{ teacher: Record<string,unknown>; load_pct: number; score: number }>
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
