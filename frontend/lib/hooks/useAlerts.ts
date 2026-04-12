import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query'
import toast from 'react-hot-toast'
import api from '@/lib/api'
import type { Alert, AlertSummary } from '@/lib/types'

const KEYS = { all: ['alerts'] as const, summary: ['alerts', 'summary'] as const }

export function useAlerts(resolved = false) {
  return useQuery({
    queryKey: [...KEYS.all, { resolved }],
    queryFn: async () => {
      const { data } = await api.get(`/api/alerts/?resolved=${resolved}`)
      return data.alerts as Alert[]
    },
  })
}

export function useAlertSummary() {
  return useQuery({
    queryKey: KEYS.summary,
    queryFn: async () => {
      const { data } = await api.get('/api/alerts/summary')
      return data as AlertSummary
    },
  })
}

export function useResolveAlert() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (id: string) => api.post(`/api/alerts/${id}/resolve`),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: KEYS.all })
      qc.invalidateQueries({ queryKey: KEYS.summary })
      toast.success('Alert resolved')
    },
    onError: () => toast.error('Failed to resolve alert'),
  })
}
